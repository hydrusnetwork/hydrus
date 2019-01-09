from . import ClientParsing
from . import ClientPaths
from . import ClientRendering
from . import ClientSearch
from . import ClientServices
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
import json
import os
import random
import threading
import time
import wx
from . import HydrusData
from . import ClientData
from . import ClientConstants as CC
from . import HydrusGlobals as HG
import collections
from . import HydrusTags
import traceback
import weakref

# important thing here, and reason why it is recursive, is because we want to preserve the parent-grandparent interleaving
def BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents ):
    
    def AddParents( simple_children_to_parents, children_to_parents, child, parents ):
        
        for parent in parents:
            
            if parent not in children_to_parents[ child ]:
                
                children_to_parents[ child ].append( parent )
                
            
            if parent in simple_children_to_parents:
                
                grandparents = simple_children_to_parents[ parent ]
                
                AddParents( simple_children_to_parents, children_to_parents, child, grandparents )
                
            
        
    
    service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
    
    for ( service_key, simple_children_to_parents ) in list(service_keys_to_simple_children_to_parents.items()):
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in list(simple_children_to_parents.items()):
            
            AddParents( simple_children_to_parents, children_to_parents, child, parents )
            
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in list(service_keys_to_pairs_flat.items()):
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HydrusData.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent:
            
            continue
            
        
        if LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ): continue
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CollapseTagSiblingPairs( groups_of_pairs ):
    
    # This now takes 'groups' of pairs in descending order of precedence
    
    # This allows us to mandate that local tags take precedence
    
    # a pair is invalid if:
    # it causes a loop (a->b, b->c, c->a)
    # there is already a relationship for the 'bad' sibling (a->b, a->c)
    
    valid_chains = {}
    
    for pairs in groups_of_pairs:
        
        pairs = list( pairs )
        
        pairs.sort()
        
        for ( bad, good ) in pairs:
            
            if bad == good:
                
                # a->a is a loop!
                
                continue
                
            
            if bad not in valid_chains:
                
                we_have_a_loop = False
                
                current_best = good
                
                while current_best in valid_chains:
                    
                    current_best = valid_chains[ current_best ]
                    
                    if current_best == bad:
                        
                        we_have_a_loop = True
                        
                        break
                        
                    
                
                if not we_have_a_loop:
                    
                    valid_chains[ bad ] = good
                    
                
            
        
    
    # now we collapse the chains, turning:
    # a->b, b->c ... e->f
    # into
    # a->f, b->f ... e->f
    
    siblings = {}
    
    for ( bad, good ) in list(valid_chains.items()):
        
        # given a->b, want to find f
        
        if good in siblings:
            
            # f already calculated and added
            
            best = siblings[ good ]
            
        else:
            
            # we don't know f for this chain, so let's figure it out
            
            current_best = good
            
            while current_best in valid_chains:
                
                current_best = valid_chains[ current_best ] # pursue endpoint f
                
            
            best = current_best
            
        
        # add a->f
        siblings[ bad ] = best
        
    
    return siblings
    
def LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ):
    
    potential_loop_paths = { parent }
    
    while len( potential_loop_paths.intersection( list(simple_children_to_parents.keys()) ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( list(simple_children_to_parents.keys()) ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
class BitmapManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._media_background_bmp_path = None
        self._media_background_bmp = None
        
    
    def _DestroyBmp( self, bmp ):
        
        wx.CallAfter( self._media_background_bmp.Destroy )
        
    
    def GetMediaBackgroundBitmap( self ):
        
        bmp_path = self._controller.new_options.GetNoneableString( 'media_background_bmp_path' )
        
        if bmp_path != self._media_background_bmp_path:
            
            self._media_background_bmp_path = bmp_path
            
            if self._media_background_bmp is not None:
                
                self._DestroyBmp( self._media_background_bmp )
                
            
            try:
                
                bmp = wx.Bitmap( self._media_background_bmp_path )
                
                self._media_background_bmp = bmp
                
            except Exception as e:
                
                self._media_background_bmp = None
                
                HydrusData.ShowText( 'Loading a bmp caused an error!' )
                
                HydrusData.ShowException( e )
                
                return None
                
            
        
        return self._media_background_bmp
        
    
class ClientFilesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._prefixes_to_locations = {}
        
        self._bad_error_occurred = False
        self._missing_locations = set()
        
        self._Reinit()
        
    
    def _GenerateExpectedFilePath( self, hash, mime ):
        
        hash_encoded = hash.hex()
        
        prefix = 'f' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded + HC.mime_ext_lookup[ mime ] )
        
        return path
        
    
    def _GenerateExpectedFullSizeThumbnailPath( self, hash ):
        
        hash_encoded = hash.hex()
        
        prefix = 't' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded ) + '.thumbnail'
        
        return path
        
    
    def _GenerateExpectedResizedThumbnailPath( self, hash ):
        
        hash_encoded = hash.hex()
        
        prefix = 'r' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded ) + '.thumbnail.resized'
        
        return path
        
    
    def _GenerateFullSizeThumbnail( self, hash, mime = None ):
        
        if mime is None:
            
            try:
                
                file_path = self._LookForFilePath( hash )
                
            except HydrusExceptions.FileMissingException:
                
                raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was missing. It could not be regenerated because the original file was also missing. This event could indicate hard drive corruption or an unplugged external drive. Please check everything is ok.' )
                
            
            mime = HydrusFileHandling.GetMime( file_path )
            
        else:
            
            file_path = self._GenerateExpectedFilePath( hash, mime )
            
        
        try:
            
            percentage_in = self._controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
            
            thumbnail = HydrusFileHandling.GenerateThumbnail( file_path, mime, percentage_in = percentage_in )
            
        except Exception as e:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was missing. It could not be regenerated from the original file for the above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
            
        
        full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        try:
            
            HydrusPaths.MakeFileWritable( full_size_path )
            
            with open( full_size_path, 'wb' ) as f:
                
                f.write( thumbnail )
                
            
        except Exception as e:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was missing. It was regenerated from the original file, but hydrus could not write it to the location ' + full_size_path + ' for the above reason. This event could indicate hard drive corruption, and it also suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
            
        
    
    def _GenerateResizedThumbnail( self, hash, mime ):
        
        full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        thumbnail_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        
        if mime in ( HC.IMAGE_GIF, HC.IMAGE_PNG ):
            
            fullsize_thumbnail_mime = HC.IMAGE_PNG
            
        else:
            
            fullsize_thumbnail_mime = HC.IMAGE_JPEG
            
        
        try:
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnailFromStaticImage( full_size_path, thumbnail_dimensions, fullsize_thumbnail_mime )
            
        except:
            
            try:
                
                ClientPaths.DeletePath( full_size_path, always_delete_fully = True )
                
            except:
                
                raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was found, but it would not render. An attempt to delete it was made, but that failed as well. This event could indicate hard drive corruption, and it also suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
                
            
            self._GenerateFullSizeThumbnail( hash, mime )
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnailFromStaticImage( full_size_path, thumbnail_dimensions, fullsize_thumbnail_mime )
            
        
        resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
        
        try:
            
            HydrusPaths.MakeFileWritable( resized_path )
            
            with open( resized_path, 'wb' ) as f:
                
                f.write( thumbnail_resized )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was found, but the resized version would not save to disk. This event suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
            
        
    
    def _GetRecoverTuple( self ):
        
        all_locations = { location for location in list(self._prefixes_to_locations.values()) }
        
        all_prefixes = list(self._prefixes_to_locations.keys())
        
        for possible_location in all_locations:
            
            for prefix in all_prefixes:
                
                correct_location = self._prefixes_to_locations[ prefix ]
                
                if possible_location != correct_location and os.path.exists( os.path.join( possible_location, prefix ) ):
                    
                    recoverable_location = possible_location
                    
                    return ( prefix, recoverable_location, correct_location )
                    
                
            
        
        return None
        
    
    def _GetRebalanceTuple( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._controller.new_options.GetClientFilesLocationsToIdealWeights()
        
        total_weight = sum( locations_to_ideal_weights.values() )
        
        ideal_locations_to_normalised_weights = { location : weight / total_weight for ( location, weight ) in list(locations_to_ideal_weights.items()) }
        
        current_locations_to_normalised_weights = collections.defaultdict( lambda: 0 )
        
        file_prefixes = [ prefix for prefix in self._prefixes_to_locations if prefix.startswith( 'f' ) ]
        
        for file_prefix in file_prefixes:
            
            location = self._prefixes_to_locations[ file_prefix ]
            
            current_locations_to_normalised_weights[ location ] += 1.0 / 256
            
        
        for location in list(current_locations_to_normalised_weights.keys()):
            
            if location not in ideal_locations_to_normalised_weights:
                
                ideal_locations_to_normalised_weights[ location ] = 0.0
                
            
        
        #
        
        overweight_locations = []
        underweight_locations = []
        
        for ( location, ideal_weight ) in list(ideal_locations_to_normalised_weights.items()):
            
            if location in current_locations_to_normalised_weights:
                
                current_weight = current_locations_to_normalised_weights[ location ]
                
                if current_weight < ideal_weight:
                    
                    underweight_locations.append( location )
                    
                elif current_weight >= ideal_weight + 1.0 / 256:
                    
                    overweight_locations.append( location )
                    
                
            else:
                
                underweight_locations.append( location )
                
            
        
        #
        
        if len( underweight_locations ) > 0 and len( overweight_locations ) > 0:
            
            overweight_location = overweight_locations.pop( 0 )
            underweight_location = underweight_locations.pop( 0 )
            
            random.shuffle( file_prefixes )
            
            for file_prefix in file_prefixes:
                
                location = self._prefixes_to_locations[ file_prefix ]
                
                if location == overweight_location:
                    
                    return ( file_prefix, overweight_location, underweight_location )
                    
                
            
        else:
            
            if full_size_thumbnail_override is None:
                
                for hex_prefix in HydrusData.IterateHexPrefixes():
                    
                    full_size_prefix = 't' + hex_prefix
                    file_prefix = 'f' + hex_prefix
                    
                    full_size_location = self._prefixes_to_locations[ full_size_prefix ]
                    file_location = self._prefixes_to_locations[ file_prefix ]
                    
                    if full_size_location != file_location:
                        
                        return ( full_size_prefix, full_size_location, file_location )
                        
                    
                
            else:
                
                for hex_prefix in HydrusData.IterateHexPrefixes():
                    
                    full_size_prefix = 't' + hex_prefix
                    
                    full_size_location = self._prefixes_to_locations[ full_size_prefix ]
                    
                    if full_size_location != full_size_thumbnail_override:
                        
                        return ( full_size_prefix, full_size_location, full_size_thumbnail_override )
                        
                    
                
            
            if resized_thumbnail_override is None:
                
                for hex_prefix in HydrusData.IterateHexPrefixes():
                    
                    resized_prefix = 'r' + hex_prefix
                    file_prefix = 'f' + hex_prefix
                    
                    resized_location = self._prefixes_to_locations[ resized_prefix ]
                    file_location = self._prefixes_to_locations[ file_prefix ]
                    
                    if resized_location != file_location:
                        
                        return ( resized_prefix, resized_location, file_location )
                        
                    
                
            else:
                
                for hex_prefix in HydrusData.IterateHexPrefixes():
                    
                    resized_prefix = 'r' + hex_prefix
                    
                    resized_location = self._prefixes_to_locations[ resized_prefix ]
                    
                    if resized_location != resized_thumbnail_override:
                        
                        return ( resized_prefix, resized_location, resized_thumbnail_override )
                        
                    
                
            
        
        return None
        
    
    def _IterateAllFilePaths( self ):
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if prefix.startswith( 'f' ):
                
                dir = os.path.join( location, prefix )
                
                filenames = os.listdir( dir )
                
                for filename in filenames:
                    
                    yield os.path.join( dir, filename )
                    
                
            
        
    
    def _IterateAllThumbnailPaths( self ):
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if prefix.startswith( 't' ) or prefix.startswith( 'r' ):
                
                dir = os.path.join( location, prefix )
                
                filenames = os.listdir( dir )
                
                for filename in filenames:
                    
                    yield os.path.join( dir, filename )
                    
                
            
        
    
    def _LookForFilePath( self, hash ):
        
        for potential_mime in HC.ALLOWED_MIMES:
            
            potential_path = self._GenerateExpectedFilePath( hash, potential_mime )
            
            if os.path.exists( potential_path ):
                
                return potential_path
                
            
        
        raise HydrusExceptions.FileMissingException( 'File for ' + hash.hex() + ' not found!' )
        
    
    def _Reinit( self ):
        
        self._prefixes_to_locations = self._controller.Read( 'client_files_locations' )
        
        if HG.client_controller.IsFirstStart():
            
            try:
                
                for ( prefix, location ) in list(self._prefixes_to_locations.items()):
                    
                    HydrusPaths.MakeSureDirectoryExists( location )
                    
                    subdir = os.path.join( location, prefix )
                    
                    HydrusPaths.MakeSureDirectoryExists( subdir )
                    
                
            except:
                
                text = 'Attempting to create the database\'s client_files folder structure failed!'
                
                wx.MessageBox( text )
                
                raise
                
            
        else:
            
            self._missing_locations = set()
            
            for ( prefix, location ) in list(self._prefixes_to_locations.items()):
                
                if os.path.exists( location ):
                    
                    subdir = os.path.join( location, prefix )
                    
                    if not os.path.exists( subdir ):
                        
                        self._missing_locations.add( ( location, prefix ) )
                        
                    
                else:
                    
                    self._missing_locations.add( ( location, prefix ) )
                    
                
            
            if len( self._missing_locations ) > 0:
                
                self._bad_error_occurred = True
                
                #
                
                missing_dict = HydrusData.BuildKeyToListDict( self._missing_locations )
                
                missing_locations = list( missing_dict.keys() )
                
                missing_locations.sort()
                
                missing_string = ''
                
                for l in missing_locations:
                    
                    missing_prefixes = list( missing_dict[ l ] )
                    
                    missing_prefixes.sort()
                    
                    missing_prefixes_string = '    ' + os.linesep.join( ( ', '.join( block ) for block in HydrusData.SplitListIntoChunks( missing_prefixes, 32 ) ) )
                    
                    missing_string += os.linesep
                    missing_string += l
                    missing_string += os.linesep
                    missing_string += missing_prefixes_string
                    
                
                #
                
                if len( self._missing_locations ) > 4:
                    
                    text = 'When initialising the client files manager, some file locations did not exist! They have all been written to the log!'
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    wx.MessageBox( text )
                    
                    HydrusData.DebugPrint( text )
                    HydrusData.DebugPrint( 'Missing locations follow:' )
                    HydrusData.DebugPrint( missing_string )
                    
                else:
                    
                    text = 'When initialising the client files manager, these file locations did not exist:'
                    text += os.linesep * 2
                    text += missing_string
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    wx.MessageBox( text )
                    HydrusData.DebugPrint( text )
                    
                
            
        
    
    def AllLocationsAreDefault( self ):
        
        with self._lock:
            
            db_dir = self._controller.GetDBDir()
            
            client_files_default = os.path.join( db_dir, 'client_files' )
            
            all_locations = set( self._prefixes_to_locations.values() )
            
            return False not in ( location.startswith( client_files_default ) for location in all_locations )
            
        
    
    def LocklessAddFileFromBytes( self, hash, mime, file_bytes ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding file from string: ' + str( ( len( file_bytes ), dest_path ) ) )
            
        
        HydrusPaths.MakeFileWritable( dest_path )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( file_bytes )
            
        
    
    def LocklessAddFile( self, hash, mime, source_path ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding file from path: ' + str( ( source_path, dest_path ) ) )
            
        
        if not os.path.exists( dest_path ):
            
            successful = HydrusPaths.MirrorFile( source_path, dest_path )
            
            if not successful:
                
                raise Exception( 'There was a problem copying the file from ' + source_path + ' to ' + dest_path + '!' )
                
            
        
    
    def AddFullSizeThumbnailFromBytes( self, hash, thumbnail ):
        
        with self._lock:
            
            self.LocklessAddFullSizeThumbnailFromBytes( hash, thumbnail )
            
        
    
    def LocklessAddFullSizeThumbnailFromBytes( self, hash, thumbnail ):
        
        dest_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding full-size thumbnail: ' + str( ( len( thumbnail ), dest_path ) ) )
            
        
        HydrusPaths.MakeFileWritable( dest_path )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( thumbnail )
            
        
        resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
        
        if os.path.exists( resized_path ):
            
            ClientPaths.DeletePath( resized_path, always_delete_fully = True )
            
        
        self._controller.pub( 'clear_thumbnails', { hash } )
        self._controller.pub( 'new_thumbnails', { hash } )
        
    
    def CheckFileIntegrity( self, *args, **kwargs ):
        
        with self._lock:
            
            self._controller.WriteSynchronous( 'file_integrity', *args, **kwargs )
            
        
    
    def ClearOrphans( self, move_location = None ):
        
        with self._lock:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'clearing orphans' )
            job_key.SetVariable( 'popup_text_1', 'preparing' )
            
            self._controller.pub( 'message', job_key )
            
            orphan_paths = []
            orphan_thumbnails = []
            
            for ( i, path ) in enumerate( self._IterateAllFilePaths() ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    status = 'reviewed ' + HydrusData.ToHumanInt( i ) + ' files, found ' + HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphans'
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                
                try:
                    
                    is_an_orphan = False
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = bytes.fromhex( should_be_a_hex_hash )
                    
                    is_an_orphan = HG.client_controller.Read( 'is_an_orphan', 'file', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    if move_location is not None:
                        
                        ( source_dir, filename ) = os.path.split( path )
                        
                        dest = os.path.join( move_location, filename )
                        
                        dest = HydrusPaths.AppendPathUntilNoConflicts( dest )
                        
                        HydrusData.Print( 'Moving the orphan ' + path + ' to ' + dest )
                        
                        HydrusPaths.MergeFile( path, dest )
                        
                    
                    orphan_paths.append( path )
                    
                
            
            time.sleep( 2 )
            
            for ( i, path ) in enumerate( self._IterateAllThumbnailPaths() ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    status = 'reviewed ' + HydrusData.ToHumanInt( i ) + ' thumbnails, found ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphans'
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                
                try:
                    
                    is_an_orphan = False
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = bytes.fromhex( should_be_a_hex_hash )
                    
                    is_an_orphan = HG.client_controller.Read( 'is_an_orphan', 'thumbnail', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    orphan_thumbnails.append( path )
                    
                
            
            time.sleep( 2 )
            
            if move_location is None and len( orphan_paths ) > 0:
                
                status = 'found ' + HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphans, now deleting'
                
                job_key.SetVariable( 'popup_text_1', status )
                
                time.sleep( 5 )
                
                for path in orphan_paths:
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    HydrusData.Print( 'Deleting the orphan ' + path )
                    
                    status = 'deleting orphan files: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_paths ) )
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                    ClientPaths.DeletePath( path )
                    
                
            
            if len( orphan_thumbnails ) > 0:
                
                status = 'found ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails, now deleting'
                
                job_key.SetVariable( 'popup_text_1', status )
                
                time.sleep( 5 )
                
                for ( i, path ) in enumerate( orphan_thumbnails ):
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    status = 'deleting orphan thumbnails: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_thumbnails ) )
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                    HydrusData.Print( 'Deleting the orphan ' + path )
                    
                    ClientPaths.DeletePath( path, always_delete_fully = True )
                    
                
            
            if len( orphan_paths ) == 0 and len( orphan_thumbnails ) == 0:
                
                final_text = 'no orphans found!'
                
            else:
                
                final_text = HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphan files and ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails cleared!'
                
            
            job_key.SetVariable( 'popup_text_1', final_text )
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Finish()
            
        
    
    def DelayedDeleteFiles( self, hashes ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Delayed delete files call: ' + str( len( hashes ) ) )
            
        
        time.sleep( 2 )
        
        big_pauser = HydrusData.BigJobPauser( period = 1 )
        
        for hashes_chunk in HydrusData.SplitIteratorIntoChunks( hashes, 10 ):
            
            with self._lock:
                
                for hash in hashes_chunk:
                    
                    try:
                        
                        path = self._LookForFilePath( hash )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        continue
                        
                    
                    ClientPaths.DeletePath( path )
                    
                
            
            big_pauser.Pause()
            
        
    
    def DelayedDeleteThumbnails( self, hashes ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Delayed delete thumbs call: ' + str( len( hashes ) ) )
            
        
        time.sleep( 2 )
        
        big_pauser = HydrusData.BigJobPauser( period = 1 )
        
        for hashes_chunk in HydrusData.SplitIteratorIntoChunks( hashes, 20 ):
            
            with self._lock:
                
                for hash in hashes_chunk:
                    
                    path = self._GenerateExpectedFullSizeThumbnailPath( hash )
                    resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
                    
                    ClientPaths.DeletePath( path, always_delete_fully = True )
                    ClientPaths.DeletePath( resized_path, always_delete_fully = True )
                    
                
            
            big_pauser.Pause()
            
        
    
    def GetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        with self._lock:
            
            return self.LocklessGetFilePath( hash, mime = mime, check_file_exists = check_file_exists )
            
        
    
    def GetMissing( self ):
        
        return self._missing_locations
        
    
    def ImportFile( self, file_import_job ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'New file import job!' )
            
        
        ( pre_import_status, hash, note ) = file_import_job.GenerateHashAndStatus()
        
        if file_import_job.IsNewToDB():
            
            file_import_job.GenerateInfo()
            
            file_import_job.CheckIsGoodToImport()
            
            ( temp_path, thumbnail ) = file_import_job.GetTempPathAndThumbnail()
            
            mime = file_import_job.GetMime()
            
            with self._lock:
                
                self.LocklessAddFile( hash, mime, temp_path )
                
                if thumbnail is not None:
                    
                    self.LocklessAddFullSizeThumbnailFromBytes( hash, thumbnail )
                    
                
                ( import_status, note ) = self._controller.WriteSynchronous( 'import_file', file_import_job )
                
            
        else:
            
            import_status = pre_import_status
            
        
        file_import_job.PubsubContentUpdates()
        
        return ( import_status, hash, note )
        
    
    def LocklessGetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'File path request: ' + str( ( hash, mime ) ) )
            
        
        if mime is None:
            
            path = self._LookForFilePath( hash )
            
        else:
            
            path = self._GenerateExpectedFilePath( hash, mime )
            
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'File path request success: ' + path )
            
        
        if check_file_exists and not os.path.exists( path ):
            
            raise HydrusExceptions.FileMissingException( 'No file found at path + ' + path + '!' )
            
        
        return path
        
    
    def GetFullSizeThumbnailPath( self, hash, mime = None ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Full-size thumbnail path request: ' + str( ( hash, mime ) ) )
            
        
        with self._lock:
            
            path = self._GenerateExpectedFullSizeThumbnailPath( hash )
            
            if not os.path.exists( path ):
                
                self._GenerateFullSizeThumbnail( hash, mime )
                
                if not self._bad_error_occurred:
                    
                    self._bad_error_occurred = True
                    
                    HydrusData.ShowText( 'A thumbnail for a file, ' + hash.hex() + ', was missing. It has been regenerated from the original file, but this event could indicate hard drive corruption. Please check everything is ok. This error may be occuring for many files, but this message will only display once per boot. If you are recovering from a fractured database, you may wish to run \'database->regenerate->all thumbnails\'.' )
                    
                
            
            if HG.file_report_mode:
                
                HydrusData.ShowText( 'Full-size thumbnail path request success: ' + path )
                
            
            return path
            
        
    
    def GetResizedThumbnailPath( self, hash, mime ):
        
        with self._lock:
            
            path = self._GenerateExpectedResizedThumbnailPath( hash )
            
            if HG.file_report_mode:
                
                HydrusData.ShowText( 'Resized thumbnail path request: ' + path )
                
            
            if not os.path.exists( path ):
                
                self._GenerateResizedThumbnail( hash, mime )
                
            
            return path
            
        
    
    def LocklessHasFullSizeThumbnail( self, hash ):
        
        path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Full-size thumbnail path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def Rebalance( self, job_key ):
        
        try:
            
            if self._bad_error_occurred:
                
                wx.MessageBox( 'A serious file error has previously occurred during this session, so further file moving will not be reattempted. Please restart the client before trying again.' )
                
                return
                
            
            with self._lock:
                
                rebalance_tuple = self._GetRebalanceTuple()
                
                while rebalance_tuple is not None:
                    
                    if job_key.IsCancelled():
                        
                        break
                        
                    
                    ( prefix, overweight_location, underweight_location ) = rebalance_tuple
                    
                    text = 'Moving \'' + prefix + '\' from ' + overweight_location + ' to ' + underweight_location
                    
                    HydrusData.Print( text )
                    
                    job_key.SetVariable( 'popup_text_1', text )
                    
                    # these two lines can cause a deadlock because the db sometimes calls stuff in here.
                    self._controller.Write( 'relocate_client_files', prefix, overweight_location, underweight_location )
                    
                    self._Reinit()
                    
                    rebalance_tuple = self._GetRebalanceTuple()
                    
                
                recover_tuple = self._GetRecoverTuple()
                
                while recover_tuple is not None:
                    
                    if job_key.IsCancelled():
                        
                        break
                        
                    
                    ( prefix, recoverable_location, correct_location ) = recover_tuple
                    
                    text = 'Recovering \'' + prefix + '\' from ' + recoverable_location + ' to ' + correct_location
                    
                    HydrusData.Print( text )
                    
                    job_key.SetVariable( 'popup_text_1', text )
                    
                    recoverable_path = os.path.join( recoverable_location, prefix )
                    correct_path = os.path.join( correct_location, prefix )
                    
                    HydrusPaths.MergeTree( recoverable_path, correct_path )
                    
                    recover_tuple = self._GetRecoverTuple()
                    
                
            
        finally:
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            
            job_key.Finish()
            
            job_key.Delete()
            
        
    
    def RebalanceWorkToDo( self ):
        
        with self._lock:
            
            return self._GetRebalanceTuple() is not None
            
        
    
    def RegenerateResizedThumbnail( self, hash, mime ):
        
        with self._lock:
            
            self.LocklessRegenerateResizedThumbnail( hash, mime )
            
        
    
    def LocklessRegenerateResizedThumbnail( self, hash, mime ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail regen request: ' + str( ( hash, mime ) ) )
            
        
        self._GenerateResizedThumbnail( hash, mime )
        
    
    def RegenerateThumbnails( self, only_do_missing = False ):
        
        with self._lock:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'regenerating thumbnails' )
            job_key.SetVariable( 'popup_text_1', 'creating directories' )
            
            self._controller.pub( 'modal_message', job_key )
            
            num_broken = 0
            
            for ( i, path ) in enumerate( self._IterateAllFilePaths() ):
                
                try:
                    
                    while job_key.IsPaused() or job_key.IsCancelled():
                        
                        time.sleep( 0.1 )
                        
                        if job_key.IsCancelled():
                            
                            job_key.SetVariable( 'popup_text_1', 'cancelled' )
                            
                            HydrusData.Print( job_key.ToString() )
                            
                            return
                            
                        
                    
                    job_key.SetVariable( 'popup_text_1', HydrusData.ToHumanInt( i ) + ' done' )
                    
                    ( base, filename ) = os.path.split( path )
                    
                    if '.' in filename:
                        
                        ( hash_encoded, ext ) = filename.split( '.', 1 )
                        
                    else:
                        
                        continue # it is an update file, so let's save us some ffmpeg lag and logspam
                        
                    
                    hash = bytes.fromhex( hash_encoded )
                    
                    full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
                    
                    if only_do_missing and os.path.exists( full_size_path ):
                        
                        continue
                        
                    
                    mime = HydrusFileHandling.GetMime( path )
                    
                    if mime in HC.MIMES_WITH_THUMBNAILS:
                        
                        self._GenerateFullSizeThumbnail( hash, mime )
                        
                        thumbnail_resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
                        
                        if os.path.exists( thumbnail_resized_path ):
                            
                            ClientPaths.DeletePath( thumbnail_resized_path, always_delete_fully = True )
                            
                        
                    
                except:
                    
                    HydrusData.Print( path )
                    HydrusData.Print( traceback.format_exc() )
                    
                    num_broken += 1
                    
                
            
            if num_broken > 0:
                
                job_key.SetVariable( 'popup_text_1', 'done! ' + HydrusData.ToHumanInt( num_broken ) + ' files caused errors, which have been written to the log.' )
                
            else:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Finish()
            
        
    
class DataCache( object ):
    
    def __init__( self, controller, cache_size, timeout = 1200 ):
        
        self._controller = controller
        self._cache_size = cache_size
        self._timeout = timeout
        
        self._keys_to_data = {}
        self._keys_fifo = collections.OrderedDict()
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'MaintainCache', 'memory_maintenance_pulse' )
        
    
    def _Delete( self, key ):
        
        if key not in self._keys_to_data:
            
            return
            
        
        deletee_data = self._keys_to_data[ key ]
        
        del self._keys_to_data[ key ]
        
        self._RecalcMemoryUsage()
        
    
    def _DeleteItem( self ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.popitem( last = False )
        
        self._Delete( deletee_key )
        
    
    def _RecalcMemoryUsage( self ):
        
        self._total_estimated_memory_footprint = sum( ( data.GetEstimatedMemoryFootprint() for data in list(self._keys_to_data.values()) ) )
        
    
    def _TouchKey( self, key ):
        
        # have to delete first, rather than overwriting, so the ordereddict updates its internal order
        if key in self._keys_fifo:
            
            del self._keys_fifo[ key ]
            
        
        self._keys_fifo[ key ] = HydrusData.GetNow()
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = collections.OrderedDict()
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                while self._total_estimated_memory_footprint > self._cache_size:
                    
                    self._DeleteItem()
                    
                
                self._keys_to_data[ key ] = data
                
                self._TouchKey( key )
                
                self._RecalcMemoryUsage()
                
            
        
    
    def DeleteData( self, key ):
        
        with self._lock:
            
            self._Delete( key )
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                raise Exception( 'Cache error! Looking for ' + str( key ) + ', but it was missing.' )
                
            
            self._TouchKey( key )
            
            return self._keys_to_data[ key ]
            
        
    
    def GetIfHasData( self, key ):
        
        with self._lock:
            
            if key in self._keys_to_data:
                
                self._TouchKey( key )
                
                return self._keys_to_data[ key ]
                
            else:
                
                return None
                
            
        
    
    def HasData( self, key ):
        
        with self._lock:
            
            return key in self._keys_to_data
            
        
    
    def MaintainCache( self ):
        
        with self._lock:
            
            while True:
                
                if len( self._keys_fifo ) == 0:
                    
                    break
                    
                else:
                    
                    ( key, last_access_time ) = next( iter(self._keys_fifo.items()) )
                    
                    if HydrusData.TimeHasPassed( last_access_time + self._timeout ):
                        
                        self._DeleteItem()
                        
                    else:
                        
                        break
                        
                    
                
            
        
    
class FileViewingStatsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._pending_updates = {}
        
        self._last_update = HydrusData.GetNow()
        
        self._my_flush_job = self._controller.CallRepeating( 5, 60, self.REPEATINGFlush )
        
    
    def REPEATINGFlush( self ):
        
        self.Flush()
        
    
    def Flush( self ):
        
        with self._lock:
            
            if len( self._pending_updates ) > 0:
                
                content_updates = []
                
                for ( hash, ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) ) in list(self._pending_updates.items()):
                    
                    row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, row )
                    
                    content_updates.append( content_update )
                    
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
                
                # non-synchronous
                self._controller.Write( 'content_updates', service_keys_to_content_updates, do_pubsubs = False )
                
                self._pending_updates = {}
                
            
        
    
    def Update( self, viewtype, hash, views_delta, viewtime_delta ):
        
        if not HG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            return
            
        
        with self._lock:
            
            preview_views_delta = 0
            preview_viewtime_delta = 0
            media_views_delta = 0
            media_viewtime_delta = 0
            
            if viewtype == 'preview':
                
                preview_views_delta = views_delta
                preview_viewtime_delta = viewtime_delta
                
            elif viewtype == 'media':
                
                media_views_delta = views_delta
                media_viewtime_delta = viewtime_delta
                
            
            if hash not in self._pending_updates:
                
                self._pending_updates[ hash ] = ( preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
                
            else:
                
                ( existing_preview_views_delta, existing_preview_viewtime_delta, existing_media_views_delta, existing_media_viewtime_delta ) = self._pending_updates[ hash ]
                
                self._pending_updates[ hash ] = ( existing_preview_views_delta + preview_views_delta, existing_preview_viewtime_delta + preview_viewtime_delta, existing_media_views_delta + media_views_delta, existing_media_viewtime_delta + media_viewtime_delta )
                
            
        
        row = ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, row )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        HG.client_controller.pub( 'content_updates_data', service_keys_to_content_updates )
        HG.client_controller.pub( 'content_updates_gui', service_keys_to_content_updates )
        

class LocalBooruCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        self._controller.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        self._controller.sub( self, 'RefreshShares', 'restart_booru' )
        
    
    def _CheckDataUsage( self ):
        
        if not self._local_booru_service.BandwidthOK():
            
            raise HydrusExceptions.ForbiddenException( 'This booru has used all its monthly data. Please try again next month.' )
            
        
    
    def _CheckFileAuthorised( self, share_key, hash ):
        
        self._CheckShareAuthorised( share_key )
        
        info = self._GetInfo( share_key )
        
        if hash not in info[ 'hashes_set' ]:
            
            raise HydrusExceptions.NotFoundException( 'That file was not found in that share.' )
            
        
    
    def _CheckShareAuthorised( self, share_key ):
        
        self._CheckDataUsage()
        
        info = self._GetInfo( share_key )
        
        timeout = info[ 'timeout' ]
        
        if timeout is not None and HydrusData.TimeHasPassed( timeout ):
            
            raise HydrusExceptions.ForbiddenException( 'This share has expired.' )
            
        
    
    def _GetInfo( self, share_key ):
        
        try: info = self._keys_to_infos[ share_key ]
        except: raise HydrusExceptions.NotFoundException( 'Did not find that share on this booru.' )
        
        if info is None:
            
            info = self._controller.Read( 'local_booru_share', share_key )
            
            hashes = info[ 'hashes' ]
            
            info[ 'hashes_set' ] = set( hashes )
            
            media_results = self._controller.Read( 'media_results', hashes )
            
            info[ 'media_results' ] = media_results
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            info[ 'hashes_to_media_results' ] = hashes_to_media_results
            
            self._keys_to_infos[ share_key ] = info
            
        
        return info
        
    
    def _RefreshShares( self ):
        
        self._local_booru_service = self._controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        self._keys_to_infos = {}
        
        share_keys = self._controller.Read( 'local_booru_share_keys' )
        
        for share_key in share_keys: self._keys_to_infos[ share_key ] = None
        
    
    def CheckShareAuthorised( self, share_key ):
        
        with self._lock: self._CheckShareAuthorised( share_key )
        
    
    def CheckFileAuthorised( self, share_key, hash ):
        
        with self._lock: self._CheckFileAuthorised( share_key, hash )
        
    
    def GetGalleryInfo( self, share_key ):
        
        with self._lock:
            
            self._CheckShareAuthorised( share_key )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_results = info[ 'media_results' ]
            
            return ( name, text, timeout, media_results )
            
        
    
    def GetMediaResult( self, share_key, hash ):
        
        with self._lock:
            
            info = self._GetInfo( share_key )
            
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return media_result
            
        
    
    def GetPageInfo( self, share_key, hash ):
        
        with self._lock:
            
            self._CheckFileAuthorised( share_key, hash )
            
            info = self._GetInfo( share_key )
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            media_result = info[ 'hashes_to_media_results' ][ hash ]
            
            return ( name, text, timeout, media_result )
            
        
    
    def RefreshShares( self ):
        
        with self._lock:
            
            self._RefreshShares()
            
        
    
class MediaResultCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._hash_ids_to_media_results = weakref.WeakValueDictionary()
        self._hashes_to_media_results = weakref.WeakValueDictionary()
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        HG.client_controller.sub( self, 'NewForceRefreshTags', 'notify_new_force_refresh_tags_data' )
        HG.client_controller.sub( self, 'NewSiblings', 'notify_new_siblings_data' )
        
    
    def AddMediaResults( self, media_results ):
        
        with self._lock:
            
            for media_result in media_results:
                
                hash_id = media_result.GetHashId()
                hash = media_result.GetHash()
                
                self._hash_ids_to_media_results[ hash_id ] = media_result
                self._hashes_to_media_results[ hash ] = media_result
                
            
        
    
    def GetMediaResultsAndMissing( self, hash_ids ):
        
        with self._lock:
            
            media_results = []
            missing_hash_ids = []
            
            for hash_id in hash_ids:
                
                if hash_id in self._hash_ids_to_media_results:
                    
                    media_results.append( self._hash_ids_to_media_results[ hash_id ] )
                    
                else:
                    
                    missing_hash_ids.append( hash_id )
                    
                
            
            return ( media_results, missing_hash_ids )
            
        
    
    def NewForceRefreshTags( self ):
        
        # repo sync or advanced content update occurred, so we need complete refresh
        
        with self._lock:
            
            if len( self._hash_ids_to_media_results ) < 10000:
                
                hash_ids = list( self._hash_ids_to_media_results.keys() )
                
                for group_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 256 ):
                    
                    hash_ids_to_tags_managers = HG.client_controller.Read( 'force_refresh_tags_managers', group_of_hash_ids )
                    
                    for ( hash_id, tags_manager ) in list(hash_ids_to_tags_managers.items()):
                        
                        if hash_id in self._hash_ids_to_media_results:
                            
                            self._hash_ids_to_media_results[ hash_id ].SetTagsManager( tags_manager )
                            
                        
                    
                
                HG.client_controller.pub( 'notify_new_force_refresh_tags_gui' )
                
            
        
    
    def NewSiblings( self ):
        
        with self._lock:
            
            for media_result in list(self._hash_ids_to_media_results.values()):
                
                media_result.GetTagsManager().NewSiblings()
                
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        with self._lock:
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    for hash in hashes:
                        
                        if hash in self._hashes_to_media_results:
                            
                            self._hashes_to_media_results[ hash ].ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        with self._lock:
            
            for ( service_key, service_updates ) in list(service_keys_to_service_updates.items()):
                
                for service_update in service_updates:
                    
                    ( action, row ) = service_update.ToTuple()
                    
                    if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                        
                        for media_result in list(self._hash_ids_to_media_results.values()):
                            
                            if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                                
                                media_result.DeletePending( service_key )
                                
                            elif action == HC.SERVICE_UPDATE_RESET:
                                
                                media_result.ResetService( service_key )
                                
                            
                        
                    
                
            
        
    
    
class MenuEventIdToActionCache( object ):
    
    def __init__( self ):
        
        self._ids_to_actions = {}
        self._actions_to_ids = {}
        
        self._temporary_ids = set()
        self._free_temporary_ids = set()
        
    
    def _ClearTemporaries( self ):
        
        for temporary_id in self._temporary_ids.difference( self._free_temporary_ids ):
            
            temporary_action = self._ids_to_actions[ temporary_id ]
            
            del self._ids_to_actions[ temporary_id ]
            del self._actions_to_ids[ temporary_action ]
            
        
        self._free_temporary_ids = set( self._temporary_ids )
        
    
    def _GetNewId( self, temporary ):
        
        if temporary:
            
            if len( self._free_temporary_ids ) == 0:
                
                new_id = wx.NewId()
                
                self._temporary_ids.add( new_id )
                self._free_temporary_ids.add( new_id )
                
                
            
            return self._free_temporary_ids.pop()
            
        else:
            
            return wx.NewId()
            
        
    
    def GetAction( self, event_id ):
        
        action = None
        
        if event_id in self._ids_to_actions:
            
            action = self._ids_to_actions[ event_id ]
            
            if event_id in self._temporary_ids:
                
                self._ClearTemporaries()
                
            
        
        return action
        
    
    def GetId( self, command, data = None, temporary = False ):
        
        action = ( command, data )
        
        if action not in self._actions_to_ids:
            
            event_id = self._GetNewId( temporary )
            
            self._ids_to_actions[ event_id ] = action
            self._actions_to_ids[ action ] = event_id
            
        
        return self._actions_to_ids[ action ]
        
    
    def GetPermanentId( self, command, data = None ):
        
        return self.GetId( command, data, False )
        
    
    def GetTemporaryId( self, command, data = None ):
        
        temporary = True
        
        if data is None:
            
            temporary = False
            
        
        return self.GetId( command, data, temporary )
        
    
MENU_EVENT_ID_TO_ACTION_CACHE = MenuEventIdToActionCache()

class ParsingCache( object ):
    
    def __init__( self ):
        
        self._next_clean_cache_time = HydrusData.GetNow()
        
        self._html_to_soups = {}
        self._json_to_jsons = {}
        
        self._lock = threading.Lock()
        
    
    def _CleanCache( self ):
        
        if HydrusData.TimeHasPassed( self._next_clean_cache_time ):
            
            for cache in ( self._html_to_soups, self._json_to_jsons ):
                
                dead_datas = set()
                
                for ( data, ( last_accessed, parsed_object ) ) in list(cache.items()):
                    
                    if HydrusData.TimeHasPassed( last_accessed + 10 ):
                        
                        dead_datas.add( data )
                        
                    
                
                for dead_data in dead_datas:
                    
                    del cache[ dead_data ]
                    
                
            
            self._next_clean_cache_time = HydrusData.GetNow() + 5
            
        
    
    def CleanCache( self ):
        
        with self._lock:
            
            self._CleanCache()
            
        
    
    def GetJSON( self, json_text ):
        
        with self._lock:
            
            now = HydrusData.GetNow()
            
            if json_text not in self._json_to_jsons:
                
                json_object = json.loads( json_text )
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            ( last_accessed, json_object ) = self._json_to_jsons[ json_text ]
            
            if last_accessed != now:
                
                self._json_to_jsons[ json_text ] = ( now, json_object )
                
            
            if len( self._json_to_jsons ) > 10:
                
                self._CleanCache()
                
            
            return json_object
            
        
    
    def GetSoup( self, html ):
        
        with self._lock:
            
            now = HydrusData.GetNow()
            
            if html not in self._html_to_soups:
                
                soup = ClientParsing.GetSoup( html )
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            ( last_accessed, soup ) = self._html_to_soups[ html ]
            
            if last_accessed != now:
                
                self._html_to_soups[ html ] = ( now, soup )
                
            
            if len( self._html_to_soups ) > 10:
                
                self._CleanCache()
                
            
            return soup
            
        
    
class RenderedImageCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        cache_size = self._controller.options[ 'fullscreen_cache_size' ]
        cache_timeout = self._controller.new_options.GetInteger( 'image_cache_timeout' )
        
        self._data_cache = DataCache( self._controller, cache_size, timeout = cache_timeout )
        
    
    def Clear( self ):
        
        self._data_cache.Clear()
        
    
    def GetImageRenderer( self, media ):
        
        hash = media.GetHash()
        
        key = hash
        
        result = self._data_cache.GetIfHasData( key )
        
        if result is None:
            
            image_renderer = ClientRendering.ImageRenderer( media )
            
            self._data_cache.AddData( key, image_renderer )
            
        else:
            
            image_renderer = result
            
        
        return image_renderer
        
    
    def HasImageRenderer( self, hash ):
        
        key = hash
        
        return self._data_cache.HasData( key )
        
    
class ThumbnailCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        cache_size = self._controller.options[ 'thumbnail_cache_size' ]
        cache_timeout = self._controller.new_options.GetInteger( 'thumbnail_cache_timeout' )
        
        self._data_cache = DataCache( self._controller, cache_size, timeout = cache_timeout )
        
        self._lock = threading.Lock()
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue_random = []
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        self._controller.CallToThreadLongRunning( self.DAEMONWaterfall )
        
        self._controller.sub( self, 'Clear', 'thumbnail_resize' )
        self._controller.sub( self, 'ClearThumbnails', 'clear_thumbnails' )
        
    
    def _GetResizedHydrusBitmapFromHardDrive( self, display_media ):
        
        thumbnail_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        
        if tuple( thumbnail_dimensions ) == HC.UNSCALED_THUMBNAIL_DIMENSIONS:
            
            full_size = True
            
        else:
            
            full_size = False
            
        
        hash = display_media.GetHash()
        mime = display_media.GetMime()
        
        locations_manager = display_media.GetLocationsManager()
        
        try:
            
            if full_size:
                
                path = self._controller.client_files_manager.GetFullSizeThumbnailPath( hash, mime )
                
            else:
                
                path = self._controller.client_files_manager.GetResizedThumbnailPath( hash, mime )
                
            
        except HydrusExceptions.FileMissingException as e:
            
            if locations_manager.IsLocal():
                
                HydrusData.ShowException( e )
                
            
            return self._special_thumbs[ 'hydrus' ]
            
        
        mime = display_media.GetMime()
        
        try:
            
            hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path, mime )
            
        except Exception as e:
            
            try:
                
                self._controller.client_files_manager.RegenerateResizedThumbnail( hash, mime )
                
                try:
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path, mime )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' was broken. It was regenerated, but the new file would not render for the above reason. Please inform the hydrus developer what has happened.' )
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return self._special_thumbs[ 'hydrus' ]
                
            
        
        ( media_x, media_y ) = display_media.GetResolution()
        ( actual_x, actual_y ) = hydrus_bitmap.GetSize()
        ( desired_x, desired_y ) = self._controller.options[ 'thumbnail_dimensions' ]
        
        too_large = actual_x > desired_x or actual_y > desired_y
        
        small_original_image = actual_x == media_x and actual_y == media_y
        
        too_small = actual_x < desired_x and actual_y < desired_y
        
        if too_large or ( too_small and not small_original_image ):
            
            self._controller.client_files_manager.RegenerateResizedThumbnail( hash, mime )
            
            hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path, mime )
            
        
        return hydrus_bitmap
        
    
    def _RecalcWaterfallQueueRandom( self ):
        
        # here we sort by the hash since this is both breddy random and more likely to access faster on a well defragged hard drive!
        
        def sort_by_hash_key( item ):
            
            ( page_key, media ) = item
            
            return media.GetDisplayMedia().GetHash()
            
        
        self._waterfall_queue_random = list( self._waterfall_queue_quick )
        
        self._waterfall_queue_random.sort( key = sort_by_hash_key )
        
    
    def CancelWaterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._data_cache.Clear()
            
            self._special_thumbs = {}
            
            names = [ 'hydrus', 'pdf', 'audio', 'video', 'zip' ]
            
            ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
            
            try:
                
                for name in names:
                    
                    path = os.path.join( HC.STATIC_DIR, name + '.png' )
                    
                    thumbnail_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
                    
                    thumbnail_bytes = HydrusFileHandling.GenerateThumbnailFromStaticImage( path, thumbnail_dimensions, HC.IMAGE_PNG )
                    
                    with open( temp_path, 'wb' ) as f:
                        
                        f.write( thumbnail_bytes )
                        
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( temp_path, HC.IMAGE_PNG )
                    
                    self._special_thumbs[ name ] = hydrus_bitmap
                    
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
        
    
    def ClearThumbnails( self, hashes ):
        
        with self._lock:
            
            for hash in hashes:
                
                self._data_cache.DeleteData( hash )
                
            
        
    
    def DoingWork( self ):
        
        with self._lock:
            
            return len( self._waterfall_queue_random ) > 0
            
        
    
    def GetThumbnail( self, media ):
        
        try:
            
            display_media = media.GetDisplayMedia()
            
        except:
            
            # sometimes media can get switched around during a collect event, and if this happens during waterfall, we have a problem here
            # just return for now, we'll see how it goes
            
            return self._special_thumbs[ 'hydrus' ]
            
        
        locations_manager = display_media.GetLocationsManager()
        
        if locations_manager.ShouldIdeallyHaveThumbnail():
            
            mime = display_media.GetMime()
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                hash = display_media.GetHash()
                
                result = self._data_cache.GetIfHasData( hash )
                
                if result is None:
                    
                    if locations_manager.ShouldDefinitelyHaveThumbnail():
                        
                        # local file, should be able to regen if needed
                        
                        hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media )
                        
                    else:
                        
                        # repository file, maybe not actually available yet
                        
                        try:
                            
                            hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media )
                            
                        except:
                            
                            hydrus_bitmap = self._special_thumbs[ 'hydrus' ]
                            
                        
                    
                    self._data_cache.AddData( hash, hydrus_bitmap )
                    
                else:
                    
                    hydrus_bitmap = result
                    
                
                return hydrus_bitmap
                
            elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
            elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
            elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
            elif mime in HC.ARCHIVES: return self._special_thumbs[ 'zip' ]
            else: return self._special_thumbs[ 'hydrus' ]
            
        else:
            
            return self._special_thumbs[ 'hydrus' ]
            
        
    
    def HasThumbnailCached( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        mime = display_media.GetMime()
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            hash = display_media.GetHash()
            
            return self._data_cache.HasData( hash )
            
        else:
            
            return True
            
        
    
    def Waterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
        self._waterfall_event.set()
        
    
    def DAEMONWaterfall( self ):
        
        last_paused = HydrusData.GetNowPrecise()
        
        while not HydrusThreading.IsThreadShuttingDown():
            
            with self._lock:
                
                do_wait = len( self._waterfall_queue_random ) == 0
                
            
            if do_wait:
                
                self._waterfall_event.wait( 1 )
                
                self._waterfall_event.clear()
                
                last_paused = HydrusData.GetNowPrecise()
                
            
            start_time = HydrusData.GetNowPrecise()
            stop_time = start_time + 0.005 # a bit of a typical frame
            
            page_keys_to_rendered_medias = collections.defaultdict( list )
            
            while not HydrusData.TimeHasPassedPrecise( stop_time ):
                
                with self._lock:
                    
                    if len( self._waterfall_queue_random ) == 0:
                        
                        break
                        
                    
                    result = self._waterfall_queue_random.pop()
                    
                    self._waterfall_queue_quick.discard( result )
                    
                
                ( page_key, media ) = result
                
                try:
                    
                    self.GetThumbnail( media ) # to load it
                    
                    page_keys_to_rendered_medias[ page_key ].append( media )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            
            for ( page_key, rendered_medias ) in list(page_keys_to_rendered_medias.items()):
                
                self._controller.pub( 'waterfall_thumbnails', page_key, rendered_medias )
                
            
            time.sleep( 0.00001 )
            
        
    
class ServicesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def _GetService( self, service_key ):
        
        try:
            
            return self._keys_to_services[ service_key ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'That service was not found!' )
            
        
    
    def _SetServices( self, services ):
        
        self._keys_to_services = { service.GetServiceKey() : service for service in services }
        
        self._keys_to_services[ CC.TEST_SERVICE_KEY ] = ClientServices.GenerateService( CC.TEST_SERVICE_KEY, HC.TEST_SERVICE, 'test service' )
        
        key = lambda s: s.GetName()
        
        self._services_sorted = list( services )
        self._services_sorted.sort( key = key )
        
    
    def Filter( self, service_keys, desired_types ):
        
        with self._lock:
            
            def func( service_key ):
                
                return self._keys_to_services[ service_key ].GetServiceType() in desired_types
                
            
            filtered_service_keys = list(filter( func, service_keys ))
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys ):
        
        with self._lock:
            
            def func( service_key ):
                
                return service_key in self._keys_to_services
                
            
            filtered_service_keys = list(filter( func, service_keys ))
            
            return filtered_service_keys
            
        
    
    def GetName( self, service_key ):
        
        with self._lock:
            
            service = self._GetService( service_key )
            
            return service.GetName()
            
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            return self._GetService( service_key )
            
        
    
    def GetServiceType( self, service_key ):
        
        with self._lock:
            
            return self._GetService( service_key ).GetServiceType()
            
        
    
    def GetServiceKeys( self, desired_types = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for ( service_key, service ) in list(self._keys_to_services.items()) if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types = HC.ALL_SERVICES, randomised = True ):
        
        with self._lock:
            
            def func( service ):
                
                return service.GetServiceType() in desired_types
                
            
            services = list(filter( func, self._services_sorted ))
            
            if randomised:
                
                random.shuffle( services )
                
            
            return services
            
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = self._controller.Read( 'services' )
            
            self._SetServices( services )
            
        
    
    def ServiceExists( self, service_key ):
        
        with self._lock:
            
            return service_key in self._keys_to_services
            
        
    
class ShortcutsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._shortcuts = {}
        
        self.RefreshShortcuts()
        
        self._controller.sub( self, 'RefreshShortcuts', 'new_shortcuts' )
        
    
    def GetCommand( self, shortcuts_names, shortcut ):
        
        for name in shortcuts_names:
            
            if name in self._shortcuts:
                
                command = self._shortcuts[ name ].GetCommand( shortcut )
                
                if command is not None:
                    
                    if HG.gui_report_mode:
                        
                        HydrusData.ShowText( 'command matched: ' + repr( command ) )
                        
                    
                    return command
                    
                
            
        
        return None
        
    
    def RefreshShortcuts( self ):
        
        self._shortcuts = {}
        
        all_shortcuts = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS )
        
        for shortcuts in all_shortcuts:
            
            self._shortcuts[ shortcuts.GetName() ] = shortcuts
            
        
    
class TagCensorshipManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self.RefreshData()
        
        self._controller.sub( self, 'RefreshData', 'notify_new_tag_censorship' )
        
    
    def _CensorshipMatches( self, tag, blacklist, censorships ):
        
        if blacklist:
            
            return not HydrusTags.CensorshipMatch( tag, censorships )
            
        else:
            
            return HydrusTags.CensorshipMatch( tag, censorships )
            
        
    
    def GetInfo( self, service_key ):
        
        if service_key in self._service_keys_to_info: return self._service_keys_to_info[ service_key ]
        else: return ( True, set() )
        
    
    def RefreshData( self ):
        
        rows = self._controller.Read( 'tag_censorship' )
        
        self._service_keys_to_info = { service_key : ( blacklist, censorships ) for ( service_key, blacklist, censorships ) in rows }
        
    
    def FilterPredicates( self, service_key, predicates ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                predicates = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG or self._CensorshipMatches( predicate.GetValue(), blacklist, censorships ) ]
                
            
        
        return predicates
        
    
    def FilterStatusesToPairs( self, service_key, statuses_to_pairs ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                new_statuses_to_pairs = HydrusData.default_dict_set()
                
                for ( status, pairs ) in list(statuses_to_pairs.items()):
                    
                    new_statuses_to_pairs[ status ] = { ( one, two ) for ( one, two ) in pairs if self._CensorshipMatches( one, blacklist, censorships ) and self._CensorshipMatches( two, blacklist, censorships ) }
                    
                
                statuses_to_pairs = new_statuses_to_pairs
                
            
        
        return statuses_to_pairs
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        if CC.COMBINED_TAG_SERVICE_KEY in self._service_keys_to_info:
            
            ( blacklist, censorships ) = self._service_keys_to_info[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            service_keys = list(service_keys_to_statuses_to_tags.keys())
            
            for service_key in service_keys:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = list(statuses_to_tags.keys())
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        for ( service_key, ( blacklist, censorships ) ) in list(self._service_keys_to_info.items()):
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            if service_key in service_keys_to_statuses_to_tags:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = list(statuses_to_tags.keys())
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        return service_keys_to_statuses_to_tags
        
    
    def FilterTags( self, service_key, tags ):
        
        for service_key_lookup in ( CC.COMBINED_TAG_SERVICE_KEY, service_key ):
            
            if service_key_lookup in self._service_keys_to_info:
                
                ( blacklist, censorships ) = self._service_keys_to_info[ service_key_lookup ]
                
                tags = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                
            
        
        return tags
        
    
class TagParentsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        sibling_manager = self._controller.GetManager( 'tag_siblings' )
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in list(service_keys_to_statuses_to_pairs.items()):
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY: continue
            
            for ( status, pairs ) in list(statuses_to_pairs.items()):
                
                pairs = sibling_manager.CollapsePairs( service_key, pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HydrusData.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in list(collapsed_service_keys_to_statuses_to_pairs.items()):
            
            pairs_flat = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in list(service_keys_to_pairs_flat.values()):
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        results = []
        
        with self._lock:
            
            for predicate in predicates:
                
                results.append( predicate )
                
                if predicate.GetType() == HC.PREDICATE_TYPE_TAG:
                    
                    tag = predicate.GetValue()
                    
                    parents = self._service_keys_to_children_to_parents[ service_key ][ tag ]
                    
                    for parent in parents:
                        
                        parent_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, parent )
                        
                        results.append( parent_predicate )
                        
                    
                
            
            return results
            
        
    
    def ExpandTags( self, service_key, tags ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def NotifyNewParents( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshParentsIfDirty )
            
        
    
    def RefreshParentsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshParents()
                
                self._dirty = False
                
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._dirty = False
        self._refresh_job = None
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewSiblings', 'notify_new_siblings_data' )
        
    
    def _CollapseTags( self, service_key, tags ):
    
        siblings = self._service_keys_to_siblings[ service_key ]
        
        return { siblings[ tag ] if tag in siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        local_tags_pairs = set()
        
        tag_repo_pairs = set()
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_siblings' )
        
        for ( service_key, statuses_to_pairs ) in list(service_keys_to_statuses_to_pairs.items()):
            
            all_pairs = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            if service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                local_tags_pairs = set( all_pairs )
                
            else:
                
                tag_repo_pairs.update( all_pairs )
                
            
            siblings = CollapseTagSiblingPairs( [ all_pairs ] )
            
            self._service_keys_to_siblings[ service_key ] = siblings
            
            reverse_lookup = collections.defaultdict( list )
            
            for ( bad, good ) in list(siblings.items()):
                
                reverse_lookup[ good ].append( bad )
                
            
            self._service_keys_to_reverse_lookup[ service_key ] = reverse_lookup
            
        
        combined_siblings = CollapseTagSiblingPairs( [ local_tags_pairs, tag_repo_pairs ] )
        
        self._service_keys_to_siblings[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_siblings
        
        combined_reverse_lookup = collections.defaultdict( list )
        
        for ( bad, good ) in list(combined_siblings.items()):
            
            combined_reverse_lookup[ good ].append( bad )
            
        
        self._service_keys_to_reverse_lookup[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_reverse_lookup
        
        self._controller.pub( 'new_siblings_gui' )
        
    
    def CollapsePredicates( self, service_key, predicates ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = { predicate.GetValue() : predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG }
            
            tags = list(tags_to_predicates.keys())
            
            tags_to_include_in_results = set()
            
            for tag in tags:
                
                if tag in siblings:
                    
                    old_tag = tag
                    old_predicate = tags_to_predicates[ old_tag ]
                    
                    new_tag = siblings[ old_tag ]
                    
                    if new_tag not in tags_to_predicates:
                        
                        ( old_pred_type, old_value, old_inclusive ) = old_predicate.GetInfo()
                        
                        new_predicate = ClientSearch.Predicate( old_pred_type, new_tag, old_inclusive )
                        
                        tags_to_predicates[ new_tag ] = new_predicate
                        
                        tags_to_include_in_results.add( new_tag )
                        
                    
                    new_predicate = tags_to_predicates[ new_tag ]
                    
                    new_predicate.AddCounts( old_predicate )
                    
                else:
                    
                    tags_to_include_in_results.add( tag )
                    
                
            
            results.extend( [ tags_to_predicates[ tag ] for tag in tags_to_include_in_results ] )
            
            return results
            
        
    
    def CollapsePairs( self, service_key, pairs ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            result = set()
            
            for ( a, b ) in pairs:
                
                if a in siblings:
                    
                    a = siblings[ a ]
                    
                
                if b in siblings:
                    
                    b = siblings[ b ]
                    
                
                result.add( ( a, b ) )
                
            
            return result
            
        
    
    def CollapseStatusesToTags( self, service_key, statuses_to_tags ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            statuses = list(statuses_to_tags.keys())
            
            new_statuses_to_tags = HydrusData.default_dict_set()
            
            for status in statuses:
                
                new_statuses_to_tags[ status ] = self._CollapseTags( service_key, statuses_to_tags[ status ] )
                
            
            return new_statuses_to_tags
            
        
    
    def CollapseTag( self, service_key, tag ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return tag
                
            
        
    
    def CollapseTags( self, service_key, tags ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._CollapseTags( service_key, tags )
            
        
    
    def CollapseTagsToCount( self, service_key, tags_to_count ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = collections.Counter()
            
            for ( tag, count ) in list(tags_to_count.items()):
                
                if tag in siblings:
                    
                    tag = siblings[ tag ]
                    
                
                results[ tag ] += count
                
            
            return results
            
        
    
    def GetSibling( self, service_key, tag ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return None
                
            
        
    
    def GetAllSiblings( self, service_key, tag ):
        
        if self._controller.new_options.GetBoolean( 'apply_all_siblings_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            reverse_lookup = self._service_keys_to_reverse_lookup[ service_key ]
            
            if tag in siblings:
                
                best_tag = siblings[ tag ]
                
            elif tag in reverse_lookup:
                
                best_tag = tag
                
            else:
                
                return [ tag ]
                
            
            all_siblings = list( reverse_lookup[ best_tag ] )
            
            all_siblings.append( best_tag )
            
            return all_siblings
            
        
    
    def NotifyNewSiblings( self ):
        
        with self._lock:
            
            self._dirty = True
            
            if self._refresh_job is not None:
                
                self._refresh_job.Cancel()
                
            
            self._refresh_job = self._controller.CallLater( 8.0, self.RefreshSiblingsIfDirty )
            
        
    
    def RefreshSiblingsIfDirty( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._RefreshSiblings()
                
                self._dirty = False
                
                self._controller.pub( 'notify_new_siblings_gui' )
                
            
        
    
class UndoManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._commands = []
        self._inverted_commands = []
        self._current_index = 0
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'Undo', 'undo' )
        self._controller.sub( self, 'Redo', 'redo' )
        
    
    def _FilterServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        filtered_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
            
            filtered_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_RESCIND_PETITION, HC.CONTENT_UPDATE_ADVANCED ):
                        
                        continue
                        
                    
                else:
                    
                    continue
                    
                
                filtered_content_update = HydrusData.ContentUpdate( data_type, action, row )
                
                filtered_content_updates.append( filtered_content_update )
                
            
            if len( filtered_content_updates ) > 0:
                
                filtered_service_keys_to_content_updates[ service_key ] = filtered_content_updates
                
            
        
        return filtered_service_keys_to_content_updates
        
    
    def _InvertServiceKeysToContentUpdates( self, service_keys_to_content_updates ):
        
        inverted_service_keys_to_content_updates = {}
        
        for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
            
            inverted_content_updates = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                inverted_row = row
                
                if data_type == HC.CONTENT_TYPE_FILES:
                    
                    if action == HC.CONTENT_UPDATE_ARCHIVE: inverted_action = HC.CONTENT_UPDATE_INBOX
                    elif action == HC.CONTENT_UPDATE_INBOX: inverted_action = HC.CONTENT_UPDATE_ARCHIVE
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( hashes, reason ) = row
                        
                        inverted_row = hashes
                        
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    if action == HC.CONTENT_UPDATE_ADD: inverted_action = HC.CONTENT_UPDATE_DELETE
                    elif action == HC.CONTENT_UPDATE_DELETE: inverted_action = HC.CONTENT_UPDATE_ADD
                    elif action == HC.CONTENT_UPDATE_PEND: inverted_action = HC.CONTENT_UPDATE_RESCIND_PEND
                    elif action == HC.CONTENT_UPDATE_RESCIND_PEND: inverted_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_PETITION:
                        
                        inverted_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                        
                        ( tag, hashes, reason ) = row
                        
                        inverted_row = ( tag, hashes )
                        
                    
                
                inverted_content_update = HydrusData.ContentUpdate( data_type, inverted_action, inverted_row )
                
                inverted_content_updates.append( inverted_content_update )
                
            
            inverted_service_keys_to_content_updates[ service_key ] = inverted_content_updates
            
        
        return inverted_service_keys_to_content_updates
        
    
    def AddCommand( self, action, *args, **kwargs ):
        
        with self._lock:
            
            inverted_action = action
            inverted_args = args
            inverted_kwargs = kwargs
            
            if action == 'content_updates':
                
                ( service_keys_to_content_updates, ) = args
                
                service_keys_to_content_updates = self._FilterServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( service_keys_to_content_updates ) == 0: return
                
                inverted_service_keys_to_content_updates = self._InvertServiceKeysToContentUpdates( service_keys_to_content_updates )
                
                if len( inverted_service_keys_to_content_updates ) == 0: return
                
                inverted_args = ( inverted_service_keys_to_content_updates, )
                
            else: return
            
            self._commands = self._commands[ : self._current_index ]
            self._inverted_commands = self._inverted_commands[ : self._current_index ]
            
            self._commands.append( ( action, args, kwargs ) )
            
            self._inverted_commands.append( ( inverted_action, inverted_args, inverted_kwargs ) )
            
            self._current_index += 1
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def GetUndoRedoStrings( self ):
        
        with self._lock:
            
            ( undo_string, redo_string ) = ( None, None )
            
            if self._current_index > 0:
                
                undo_index = self._current_index - 1
                
                ( action, args, kwargs ) = self._commands[ undo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    undo_string = 'undo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                redo_index = self._current_index
                
                ( action, args, kwargs ) = self._commands[ redo_index ]
                
                if action == 'content_updates':
                    
                    ( service_keys_to_content_updates, ) = args
                    
                    redo_string = 'redo ' + ClientData.ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates )
                    
                
            
            return ( undo_string, redo_string )
            
        
    
    def Undo( self ):
        
        action = None
        
        with self._lock:
            
            if self._current_index > 0:
                
                self._current_index -= 1
                
                ( action, args, kwargs ) = self._inverted_commands[ self._current_index ]
                
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def Redo( self ):
        
        action = None
        
        with self._lock:
            
            if len( self._commands ) > 0 and self._current_index < len( self._commands ):
                
                ( action, args, kwargs ) = self._commands[ self._current_index ]
                
                self._current_index += 1
                
            
        
        if action is not None:
            
            self._controller.WriteSynchronous( action, *args, **kwargs )
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
