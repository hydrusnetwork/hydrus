import ClientDefaults
import ClientDownloading
import ClientNetworking
import ClientRendering
import ClientSearch
import ClientThreading
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusPaths
import HydrusSessions
import itertools
import json
import os
import random
import requests
import threading
import time
import urllib
import wx
import HydrusData
import ClientData
import ClientConstants as CC
import HydrusGlobals
import collections
import HydrusTags
import itertools
import traceback

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
    
    for ( service_key, simple_children_to_parents ) in service_keys_to_simple_children_to_parents.items():
        
        children_to_parents = service_keys_to_children_to_parents[ service_key ]
        
        for ( child, parents ) in simple_children_to_parents.items():
            
            AddParents( simple_children_to_parents, children_to_parents, child, parents )
            
        
    
    return service_keys_to_children_to_parents
    
def BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat ):
    
    service_keys_to_simple_children_to_parents = collections.defaultdict( HydrusData.default_dict_set )
    
    for ( service_key, pairs ) in service_keys_to_pairs_flat.items():
        
        service_keys_to_simple_children_to_parents[ service_key ] = BuildSimpleChildrenToParents( pairs )
        
    
    return service_keys_to_simple_children_to_parents
    
def BuildSimpleChildrenToParents( pairs ):
    
    simple_children_to_parents = HydrusData.default_dict_set()
    
    for ( child, parent ) in pairs:
        
        if child == parent: continue
        
        if LoopInSimpleChildrenToParents( simple_children_to_parents, child, parent ): continue
        
        simple_children_to_parents[ child ].add( parent )
        
    
    return simple_children_to_parents
    
def CollapseTagSiblingPairs( pairs ):
    
    # a pair is invalid if:
    # it causes a loop (a->b, b->c, c->a)
    # there is already a relationship for the 'bad' sibling (a->b, a->c)
    
    valid_chains = {}
    
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
    
    for ( bad, good ) in valid_chains.items():
        
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
    
    while len( potential_loop_paths.intersection( simple_children_to_parents.keys() ) ) > 0:
        
        new_potential_loop_paths = set()
        
        for potential_loop_path in potential_loop_paths.intersection( simple_children_to_parents.keys() ):
            
            new_potential_loop_paths.update( simple_children_to_parents[ potential_loop_path ] )
            
        
        potential_loop_paths = new_potential_loop_paths
        
        if child in potential_loop_paths: return True
        
    
    return False
    
class ClientFilesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._prefixes_to_locations = {}
        
        self._bad_error_occured = False
        
        self._Reinit()
        
    
    def _GenerateExpectedFilePath( self, hash, mime ):
        
        hash_encoded = hash.encode( 'hex' )
        
        prefix = 'f' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded + HC.mime_ext_lookup[ mime ] )
        
        return path
        
    
    def _GenerateExpectedFullSizeThumbnailPath( self, hash ):
        
        hash_encoded = hash.encode( 'hex' )
        
        prefix = 't' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded ) + '.thumbnail'
        
        return path
        
    
    def _GenerateExpectedResizedThumbnailPath( self, hash ):
        
        hash_encoded = hash.encode( 'hex' )
        
        prefix = 'r' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded ) + '.thumbnail.resized'
        
        return path
        
    
    def _GenerateFullSizeThumbnail( self, hash ):
        
        try:
            
            file_path = self._LookForFilePath( hash )
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was missing. It could not be regenerated because the original file was also missing. This event could indicate hard drive corruption or an unplugged external drive. Please check everything is ok.' )
            
        
        try:
            
            thumbnail = HydrusFileHandling.GenerateThumbnail( file_path )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was missing. It could not be regenerated from the original file for the above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
            
        
        full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        try:
            
            with open( full_size_path, 'wb' ) as f:
                
                f.write( thumbnail )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was missing. It was regenerated from the original file, but hydrus could not write it to the location ' + full_size_path + ' for the above reason. This event could indicate hard drive corruption, and it also suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
            
        
    
    def _GenerateResizedThumbnail( self, hash ):
        
        full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        options = self._controller.GetOptions()
        
        thumbnail_dimensions = options[ 'thumbnail_dimensions' ]
        
        try:
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( full_size_path, thumbnail_dimensions )
            
        except:
            
            try:
                
                HydrusPaths.DeletePath( full_size_path )
                
            except:
                
                raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was found, but it would not render. An attempt to delete it was made, but that failed as well. This event could indicate hard drive corruption, and it also suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
                
            
            self._GenerateFullSizeThumbnail( hash )
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( full_size_path, thumbnail_dimensions )
            
        
        resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
        
        try:
            
            with open( resized_path, 'wb' ) as f:
                
                f.write( thumbnail_resized )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was found, but the resized version would not save to disk. This event suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.' )
            
        
    
    def _GetRecoverTuple( self ):
        
        all_locations = { location for location in self._prefixes_to_locations.values() }
        
        all_prefixes = self._prefixes_to_locations.keys()
        
        for possible_location in all_locations:
            
            for prefix in all_prefixes:
                
                correct_location = self._prefixes_to_locations[ prefix ]
                
                if possible_location != correct_location and os.path.exists( os.path.join( possible_location, prefix ) ):
                    
                    recoverable_location = possible_location
                    
                    return ( prefix, recoverable_location, correct_location )
                    
                
            
        
        return None
        
    
    def _GetRebalanceTuple( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._controller.GetNewOptions().GetClientFilesLocationsToIdealWeights()
        
        total_weight = sum( locations_to_ideal_weights.values() )
        
        ideal_locations_to_normalised_weights = { location : weight / total_weight for ( location, weight ) in locations_to_ideal_weights.items() }
        
        current_locations_to_normalised_weights = collections.defaultdict( lambda: 0 )
        
        file_prefixes = [ prefix for prefix in self._prefixes_to_locations if prefix.startswith( 'f' ) ]
        
        for file_prefix in file_prefixes:
            
            location = self._prefixes_to_locations[ file_prefix ]
            
            current_locations_to_normalised_weights[ location ] += 1.0 / 256
            
        
        for location in current_locations_to_normalised_weights.keys():
            
            if location not in ideal_locations_to_normalised_weights:
                
                ideal_locations_to_normalised_weights[ location ] = 0.0
                
            
        
        #
        
        overweight_locations = []
        underweight_locations = []
        
        for ( location, ideal_weight ) in ideal_locations_to_normalised_weights.items():
            
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
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
            if prefix.startswith( 'f' ):
                
                dir = os.path.join( location, prefix )
                
                filenames = os.listdir( dir )
                
                for filename in filenames:
                    
                    yield os.path.join( dir, filename )
                    
                
            
        
    
    def _IterateAllThumbnailPaths( self ):
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
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
                
            
        
        raise HydrusExceptions.FileMissingException( 'File for ' + hash.encode( 'hex' ) + ' not found!' )
        
    
    def _Reinit( self ):
        
        self._prefixes_to_locations = self._controller.Read( 'client_files_locations' )
        
        missing = set()
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
            if os.path.exists( location ):
                
                dir = os.path.join( location, prefix )
                
                if not os.path.exists( dir ):
                    
                    missing.add( dir )
                    
                    HydrusPaths.MakeSureDirectoryExists( dir )
                    
                
            else:
                
                missing.add( location )
                
            
        
        if len( missing ) > 0 and not HydrusGlobals.client_controller.IsFirstStart():
            
            self._bad_error_occured = True
            
            text = 'The external locations:'
            text += os.linesep * 2
            text += ', '.join( missing )
            text += os.linesep * 2
            text += 'Did not exist on boot! Please check your external storage options and locations and restart the client.'
            
            HydrusData.DebugPrint( text )
            wx.MessageBox( text )
            
        
    
    def LocklessAddFileFromString( self, hash, mime, data ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( data )
            
        
    
    def LocklessAddFile( self, hash, mime, source_path ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if not os.path.exists( dest_path ):
            
            HydrusPaths.MirrorFile( source_path, dest_path )
            
        
    
    def AddFullSizeThumbnail( self, hash, thumbnail ):
        
        with self._lock:
            
            self.LocklessAddFullSizeThumbnail( hash, thumbnail )
            
        
    
    def LocklessAddFullSizeThumbnail( self, hash, thumbnail ):
        
        path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        with open( path, 'wb' ) as f:
            
            f.write( thumbnail )
            
        
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
                    
                    status = 'reviewed ' + HydrusData.ConvertIntToPrettyString( i ) + ' files, found ' + HydrusData.ConvertIntToPrettyString( len( orphan_paths ) ) + ' orphans'
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                
                try:
                    
                    is_an_orphan = False
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = should_be_a_hex_hash.decode( 'hex' )
                    
                    is_an_orphan = HydrusGlobals.client_controller.Read( 'is_an_orphan', 'file', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    orphan_paths.append( path )
                    
                
            
            time.sleep( 2 )
            
            for ( i, path ) in enumerate( self._IterateAllThumbnailPaths() ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    status = 'reviewed ' + HydrusData.ConvertIntToPrettyString( i ) + ' thumbnails, found ' + HydrusData.ConvertIntToPrettyString( len( orphan_thumbnails ) ) + ' orphans'
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                
                try:
                    
                    is_an_orphan = False
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = should_be_a_hex_hash.decode( 'hex' )
                    
                    is_an_orphan = HydrusGlobals.client_controller.Read( 'is_an_orphan', 'thumbnail', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    orphan_thumbnails.append( path )
                    
                
            
            time.sleep( 2 )
            
            if len( orphan_paths ) > 0:
                
                if move_location is None:
                    
                    status = 'found ' + HydrusData.ConvertIntToPrettyString( len( orphan_paths ) ) + ' orphans, now deleting'
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                    time.sleep( 5 )
                    
                    for path in orphan_paths:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        HydrusData.Print( 'Deleting the orphan ' + path )
                        
                        status = 'deleting orphan files: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_paths ) )
                        
                        job_key.SetVariable( 'popup_text_1', status )
                        
                        HydrusPaths.DeletePath( path )
                        
                    
                else:
                    
                    status = 'found ' + HydrusData.ConvertIntToPrettyString( len( orphan_paths ) ) + ' orphans, now moving to ' + move_location
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                    time.sleep( 5 )
                    
                    for path in orphan_paths:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        ( source_dir, filename ) = os.path.split( path )
                        
                        dest = os.path.join( move_location, filename )
                        
                        dest = HydrusPaths.AppendPathUntilNoConflicts( dest )
                        
                        HydrusData.Print( 'Moving the orphan ' + path + ' to ' + dest )
                        
                        status = 'moving orphan files: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_paths ) )
                        
                        job_key.SetVariable( 'popup_text_1', status )
                        
                        HydrusPaths.MergeFile( path, dest )
                        
                    
                
            
            if len( orphan_thumbnails ) > 0:
                
                status = 'found ' + HydrusData.ConvertIntToPrettyString( len( orphan_thumbnails ) ) + ' orphan thumbnails, now deleting'
                
                job_key.SetVariable( 'popup_text_1', status )
                
                time.sleep( 5 )
                
                for ( i, path ) in enumerate( orphan_thumbnails ):
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    status = 'deleting orphan thumbnails: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_thumbnails ) )
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    
                    HydrusData.Print( 'Deleting the orphan ' + path )
                    
                    HydrusPaths.DeletePath( path )
                    
                
            
            if len( orphan_paths ) == 0 and len( orphan_thumbnails ) == 0:
                
                final_text = 'no orphans found!'
                
            else:
                
                final_text = HydrusData.ConvertIntToPrettyString( len( orphan_paths ) ) + ' orphan files and ' + HydrusData.ConvertIntToPrettyString( len( orphan_thumbnails ) ) + ' orphan thumbnails cleared!'
                
            
            job_key.SetVariable( 'popup_text_1', final_text )
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Finish()
            
        
    
    def DelayedDeleteFiles( self, hashes, time_to_delete ):
        
        while not HydrusData.TimeHasPassed( time_to_delete ):
            
            time.sleep( 0.5 )
            
        
        with self._lock:
            
            for hash in hashes:
                
                try:
                    
                    path = self._LookForFilePath( hash )
                    
                except HydrusExceptions.FileMissingException:
                    
                    continue
                    
                
                ClientData.DeletePath( path )
                
            
    
    def DelayedDeleteThumbnails( self, hashes, time_to_delete ):
        
        while not HydrusData.TimeHasPassed( time_to_delete ):
            
            time.sleep( 0.5 )
            
        
        with self._lock:
            
            for hash in hashes:
                
                path = self._GenerateExpectedFullSizeThumbnailPath( hash )
                resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
                
                HydrusPaths.DeletePath( path )
                HydrusPaths.DeletePath( resized_path )
                
            
        
    
    def GetFilePath( self, hash, mime = None ):
        
        with self._lock:
            
            return self.LocklessGetFilePath( hash, mime )
            
        
    
    def ImportFile( self, *args, **kwargs ):
        
        with self._lock:
            
            return self._controller.WriteSynchronous( 'import_file', *args, **kwargs )
            
        
    
    def LocklessGetFilePath( self, hash, mime = None ):
        
        if mime is None:
            
            path = self._LookForFilePath( hash )
            
        else:
            
            path = self._GenerateExpectedFilePath( hash, mime )
            
        
        if not os.path.exists( path ):
            
            raise HydrusExceptions.FileMissingException( 'No file found at path + ' + path + '!' )
            
        
        return path
        
    
    def GetFullSizeThumbnailPath( self, hash ):
        
        with self._lock:
            
            path = self._GenerateExpectedFullSizeThumbnailPath( hash )
            
            if not os.path.exists( path ):
                
                self._GenerateFullSizeThumbnail( hash )
                
                if not self._bad_error_occured:
                    
                    self._bad_error_occured = True
                    
                    HydrusData.ShowText( 'A thumbnail for a file, ' + hash.encode( 'hex' ) + ', was missing. It has been regenerated from the original file, but this event could indicate hard drive corruption. Please check everything is ok. This error may be occuring for many files, but this message will only display once per boot. If you are recovering from a fractured database, you may wish to run \'database->maintenance->regenerate thumbnails\'.' )
                    
                
            
            return path
            
        
    
    def GetResizedThumbnailPath( self, hash ):
        
        with self._lock:
            
            path = self._GenerateExpectedResizedThumbnailPath( hash )
            
            if not os.path.exists( path ):
                
                self._GenerateResizedThumbnail( hash )
                
            
            return path
            
        
    
    def LocklessHasFullSizeThumbnail( self, hash ):
        
        path = self._GenerateExpectedFullSizeThumbnailPath( hash )
        
        return os.path.exists( path )
        
    
    def Rebalance( self, partial = True, stop_time = None ):
        
        if self._bad_error_occured:
            
            return
            
        
        with self._lock:
            
            rebalance_tuple = self._GetRebalanceTuple()
            
            while rebalance_tuple is not None:
                
                ( prefix, overweight_location, underweight_location ) = rebalance_tuple
                
                text = 'Moving \'' + prefix + '\' from ' + overweight_location + ' to ' + underweight_location
                
                if partial:
                    
                    HydrusData.Print( text )
                    
                else:
                    
                    self._controller.pub( 'splash_set_status_text', text )
                    HydrusData.ShowText( text )
                    
                
                # these two lines can cause a deadlock because the db sometimes calls stuff in here.
                self._controller.Write( 'relocate_client_files', prefix, overweight_location, underweight_location )
                
                self._Reinit()
                
                if partial:
                    
                    break
                    
                
                if stop_time is not None and HydrusData.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                rebalance_tuple = self._GetRebalanceTuple()
                
            
            recover_tuple = self._GetRecoverTuple()
            
            while recover_tuple is not None:
                
                ( prefix, recoverable_location, correct_location ) = recover_tuple
                
                text = 'Recovering \'' + prefix + '\' from ' + recoverable_location + ' to ' + correct_location
                
                if partial:
                    
                    HydrusData.Print( text )
                    
                else:
                    
                    self._controller.pub( 'splash_set_status_text', text )
                    HydrusData.ShowText( text )
                    
                
                recoverable_path = os.path.join( recoverable_location, prefix )
                correct_path = os.path.join( correct_location, prefix )
                
                HydrusPaths.MergeTree( recoverable_path, correct_path )
                
                if partial:
                    
                    break
                    
                
                if stop_time is not None and HydrusData.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                recover_tuple = self._GetRecoverTuple()
                
            
        
        if not partial:
            
            HydrusData.ShowText( 'All folders balanced!' )
            
        
    
    def RegenerateResizedThumbnail( self, hash ):
        
        with self._lock:
            
            self._GenerateResizedThumbnail( hash )
            
        
    
    def RegenerateThumbnails( self, only_do_missing = False ):
        
        with self._lock:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'regenerating thumbnails' )
            job_key.SetVariable( 'popup_text_1', 'creating directories' )
            
            self._controller.pub( 'message', job_key )
            
            num_broken = 0
            
            for ( i, path ) in enumerate( self._IterateAllFilePaths() ):
                
                try:
                    
                    while job_key.IsPaused() or job_key.IsCancelled():
                        
                        time.sleep( 0.1 )
                        
                        if job_key.IsCancelled():
                            
                            job_key.SetVariable( 'popup_text_1', 'cancelled' )
                            
                            HydrusData.Print( job_key.ToString() )
                            
                            return
                            
                        
                    
                    job_key.SetVariable( 'popup_text_1', HydrusData.ConvertIntToPrettyString( i ) + ' done' )
                    
                    ( base, filename ) = os.path.split( path )
                    
                    if '.' in filename:
                        
                        ( hash_encoded, ext ) = filename.split( '.', 1 )
                        
                    else:
                        
                        continue # it is an update file, so let's save us some ffmpeg lag and logspam
                        
                    
                    hash = hash_encoded.decode( 'hex' )
                    
                    full_size_path = self._GenerateExpectedFullSizeThumbnailPath( hash )
                    
                    if only_do_missing and os.path.exists( full_size_path ):
                        
                        continue
                        
                    
                    mime = HydrusFileHandling.GetMime( path )
                    
                    if mime in HC.MIMES_WITH_THUMBNAILS:
                        
                        self._GenerateFullSizeThumbnail( hash )
                        
                        thumbnail_resized_path = self._GenerateExpectedResizedThumbnailPath( hash )
                        
                        if os.path.exists( thumbnail_resized_path ):
                            
                            HydrusPaths.DeletePath( thumbnail_resized_path )
                            
                        
                    
                except:
                    
                    HydrusData.Print( path )
                    HydrusData.Print( traceback.format_exc() )
                    
                    num_broken += 1
                    
                
            
            if num_broken > 0:
                
                job_key.SetVariable( 'popup_text_1', 'done! ' + HydrusData.ConvertIntToPrettyString( num_broken ) + ' files caused errors, which have been written to the log.' )
                
            else:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Finish()
            
        
    
class DataCache( object ):
    
    def __init__( self, controller, cache_size ):
        
        self._controller = controller
        self._cache_size = cache_size
        
        self._keys_to_data = {}
        self._keys_fifo = []
        
        self._total_estimated_memory_footprint = 0
        
        self._lock = threading.Lock()
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
    def _DeleteItem( self ):
        
        ( deletee_key, last_access_time ) = self._keys_fifo.pop( 0 )
        
        deletee_data = self._keys_to_data[ deletee_key ]
        
        del self._keys_to_data[ deletee_key ]
        
        self._RecalcMemoryUsage()
        
    
    def _RecalcMemoryUsage( self ):
        
        self._total_estimated_memory_footprint = sum( ( data.GetEstimatedMemoryFootprint() for data in self._keys_to_data.values() ) )
        
    
    def _TouchKey( self, key ):
    
        for ( i, ( fifo_key, last_access_time ) ) in enumerate( self._keys_fifo ):
            
            if fifo_key == key:
                
                del self._keys_fifo[ i ]
                
                break
                
            
        
        self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._keys_to_data = {}
            self._keys_fifo = []
            
            self._total_estimated_memory_footprint = 0
            
        
    
    def AddData( self, key, data ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                options = self._controller.GetOptions()
                
                while self._total_estimated_memory_footprint > self._cache_size:
                    
                    self._DeleteItem()
                    
                
                self._keys_to_data[ key ] = data
                
                self._keys_fifo.append( ( key, HydrusData.GetNow() ) )
                
                self._RecalcMemoryUsage()
                
            
        
    
    def GetData( self, key ):
        
        with self._lock:
            
            if key not in self._keys_to_data:
                
                raise Exception( 'Cache error! Looking for ' + HydrusData.ToUnicode( key ) + ', but it was missing.' )
                
            
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
                    
                    ( key, last_access_time ) = self._keys_fifo[ 0 ]
                    
                    if HydrusData.TimeHasPassed( last_access_time + 1200 ):
                        
                        self._DeleteItem()
                        
                    else:
                        
                        break
                        
                    
                
            
        
        wx.CallLater( 60 * 1000, self.MaintainCache )
        
    
class LocalBooruCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._RefreshShares()
        
        self._controller.sub( self, 'RefreshShares', 'refresh_local_booru_shares' )
        self._controller.sub( self, 'RefreshShares', 'restart_booru' )
        
    
    def _CheckDataUsage( self ):
        
        if not self._local_booru_service.BandwidthOk():
            
            raise HydrusExceptions.ForbiddenException( 'This booru has used all its monthly data. Please try again next month.' )
            
        
    
    def _CheckFileAuthorised( self, share_key, hash ):
        
        self._CheckShareAuthorised( share_key )
        
        info = self._GetInfo( share_key )
        
        if hash not in info[ 'hashes_set' ]: raise HydrusExceptions.NotFoundException( 'That file was not found in that share.' )
        
    
    def _CheckShareAuthorised( self, share_key ):
        
        self._CheckDataUsage()
        
        info = self._GetInfo( share_key )
        
        timeout = info[ 'timeout' ]
        
        if timeout is not None and HydrusData.TimeHasPassed( timeout ): raise HydrusExceptions.ForbiddenException( 'This share has expired.' )
        
    
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
        
        self._local_booru_service = self._controller.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
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
            
        
    
class HydrusSessionManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        existing_sessions = self._controller.Read( 'hydrus_sessions' )
        
        self._service_keys_to_sessions = { service_key : ( session_key, expires ) for ( service_key, session_key, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_key ):
        
        with self._lock:
            
            self._controller.Write( 'delete_hydrus_session_key', service_key )
            
            if service_key in self._service_keys_to_sessions:
                
                del self._service_keys_to_sessions[ service_key ]
                
            
        
    
    def GetSessionKey( self, service_key ):
        
        now = HydrusData.GetNow()
        
        with self._lock:
            
            if service_key in self._service_keys_to_sessions:
                
                ( session_key, expires ) = self._service_keys_to_sessions[ service_key ]
                
                if now + 600 > expires: del self._service_keys_to_sessions[ service_key ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = self._controller.GetServicesManager().GetService( service_key )
            
            ( response_gumpf, cookies ) = service.Request( HC.GET, 'session_key', return_cookies = True )
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expires = now + HydrusSessions.HYDRUS_SESSION_LIFETIME
            
            self._service_keys_to_sessions[ service_key ] = ( session_key, expires )
            
            self._controller.Write( 'hydrus_session', service_key, session_key, expires )
            
            return session_key
            
        
    
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

class RenderedImageCache( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        options = self._controller.GetOptions()
        
        cache_size = options[ 'fullscreen_cache_size' ]
        
        self._data_cache = DataCache( self._controller, cache_size )
        
    
    def Clear( self ): self._data_cache.Clear()
    
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
        
        options = self._controller.GetOptions()
        
        cache_size = options[ 'thumbnail_cache_size' ]
        
        self._data_cache = DataCache( self._controller, cache_size )
        self._client_files_manager = self._controller.GetClientFilesManager()
        
        self._lock = threading.Lock()
        
        self._waterfall_queue_quick = set()
        self._waterfall_queue_random = []
        
        self._waterfall_event = threading.Event()
        
        self._special_thumbs = {}
        
        self.Clear()
        
        threading.Thread( target = self.DAEMONWaterfall, name = 'Waterfall Daemon' ).start()
        
        self._controller.sub( self, 'Clear', 'thumbnail_resize' )
        
    
    def _GetResizedHydrusBitmapFromHardDrive( self, display_media ):
        
        options = self._controller.GetOptions()
        
        thumbnail_dimensions = options[ 'thumbnail_dimensions' ]
        
        if tuple( thumbnail_dimensions ) == HC.UNSCALED_THUMBNAIL_DIMENSIONS:
            
            full_size = True
            
        else:
            
            full_size = False
            
        
        hash = display_media.GetHash()
        
        locations_manager = display_media.GetLocationsManager()
        
        if locations_manager.IsLocal():
            
            try:
                
                if full_size:
                    
                    path = self._client_files_manager.GetFullSizeThumbnailPath( hash )
                    
                else:
                    
                    path = self._client_files_manager.GetResizedThumbnailPath( hash )
                    
                
            except HydrusExceptions.FileMissingException as e:
                
                HydrusData.ShowException( e )
                
                return self._special_thumbs[ 'hydrus' ]
                
            
        else:
            
            try:
                
                if full_size:
                    
                    path = self._client_files_manager.GetFullSizeThumbnailPath( hash )
                    
                else:
                    
                    path = self._client_files_manager.GetResizedThumbnailPath( hash )
                    
                
            except HydrusExceptions.FileMissingException:
                
                return self._special_thumbs[ 'hydrus' ]
                
            
        
        try:
            
            hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            try:
                
                self._client_files_manager.RegenerateResizedThumbnail( hash )
                
                try:
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.encode( 'hex' ) + ' was broken. It was regenerated, but the new file would not render for the above reason. Please inform the hydrus developer what has happened.' )
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return self._special_thumbs[ 'hydrus' ]
                
            
        
        options = HydrusGlobals.client_controller.GetOptions()
        
        ( media_x, media_y ) = display_media.GetResolution()
        ( actual_x, actual_y ) = hydrus_bitmap.GetSize()
        ( desired_x, desired_y ) = options[ 'thumbnail_dimensions' ]
        
        too_large = actual_x > desired_x or actual_y > desired_y
        
        small_original_image = actual_x == media_x and actual_y == media_y
        
        too_small = actual_x < desired_x and actual_y < desired_y
        
        if too_large or ( too_small and not small_original_image ):
            
            self._client_files_manager.RegenerateResizedThumbnail( hash )
            
            hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( path )
            
        
        return hydrus_bitmap
        
    
    def _RecalcWaterfallQueueRandom( self ):
    
        self._waterfall_queue_random = list( self._waterfall_queue_quick )
        
        random.shuffle( self._waterfall_queue_random )
        
    
    def CancelWaterfall( self, page_key, medias ):
        
        with self._lock:
            
            self._waterfall_queue_quick.difference_update( ( ( page_key, media ) for media in medias ) )
            
            self._RecalcWaterfallQueueRandom()
            
        
    
    def Clear( self ):
        
        with self._lock:
            
            self._data_cache.Clear()
            
            self._special_thumbs = {}
            
            names = [ 'hydrus', 'flash', 'pdf', 'audio', 'video' ]
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                for name in names:
                    
                    path = os.path.join( HC.STATIC_DIR, name + '.png' )
                    
                    options = self._controller.GetOptions()
                    
                    thumbnail = HydrusFileHandling.GenerateThumbnail( path, options[ 'thumbnail_dimensions' ] )
                    
                    with open( temp_path, 'wb' ) as f: f.write( thumbnail )
                    
                    hydrus_bitmap = ClientRendering.GenerateHydrusBitmap( temp_path )
                    
                    self._special_thumbs[ name ] = hydrus_bitmap
                    
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
        
    
    def GetThumbnail( self, media ):
        
        display_media = media.GetDisplayMedia()
        
        if display_media.GetLocationsManager().ShouldHaveThumbnail():
            
            mime = display_media.GetMime()
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                hash = display_media.GetHash()
                
                result = self._data_cache.GetIfHasData( hash )
                
                if result is None:
                    
                    hydrus_bitmap = self._GetResizedHydrusBitmapFromHardDrive( display_media )
                    
                    self._data_cache.AddData( hash, hydrus_bitmap )
                    
                else:
                    
                    hydrus_bitmap = result
                    
                
                return hydrus_bitmap
                
            elif mime in HC.AUDIO: return self._special_thumbs[ 'audio' ]
            elif mime in HC.VIDEO: return self._special_thumbs[ 'video' ]
            elif mime == HC.APPLICATION_FLASH: return self._special_thumbs[ 'flash' ]
            elif mime == HC.APPLICATION_PDF: return self._special_thumbs[ 'pdf' ]
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
        
        while not HydrusGlobals.view_shutdown:
            
            with self._lock:
                
                do_wait = len( self._waterfall_queue_random ) == 0
                
            
            if do_wait:
                
                self._waterfall_event.wait( 1 )
                
                self._waterfall_event.clear()
                
                last_paused = HydrusData.GetNowPrecise()
                
            
            with self._lock:
                
                if len( self._waterfall_queue_random ) == 0:
                    
                    continue
                    
                else:
                    
                    result = self._waterfall_queue_random.pop( 0 )
                    
                    self._waterfall_queue_quick.discard( result )
                    
                    ( page_key, media ) = result
                    
                
            
            try:
                
                self.GetThumbnail( media ) # to load it
                
                self._controller.pub( 'waterfall_thumbnail', page_key, media )
                
                if HydrusData.GetNowPrecise() - last_paused > 0.005:
                    
                    time.sleep( 0.00001 )
                    
                    last_paused = HydrusData.GetNowPrecise()
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
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
        
        def compare_function( a, b ):
            
            return cmp( a.GetName(), b.GetName() )
            
        
        self._services_sorted = list( services )
        self._services_sorted.sort( cmp = compare_function )
        
    
    def Filter( self, service_keys, desired_types ):
        
        with self._lock:
            
            def func( service_key ):
                
                return self._keys_to_services[ service_key ].GetServiceType() in desired_types
                
            
            filtered_service_keys = filter( func, service_keys )
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys ):
        
        with self._lock:
            
            def func( service_key ):
                
                return service_key in self._keys_to_services
                
            
            filtered_service_keys = filter( func, service_keys )
            
            return filtered_service_keys
            
        
    
    def GetName( self, service_key ):
        
        with self._lock:
            
            service = self._GetService( service_key )
            
            return service.GetName()
            
        
    
    def GetService( self, service_key ):
        
        with self._lock:
            
            return self._GetService( service_key )
            
        
    
    def GetServiceKeys( self, desired_types = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for ( service_key, service ) in self._keys_to_services.items() if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types = HC.ALL_SERVICES, randomised = True ):
        
        with self._lock:
            
            def func( service ):
                
                return service.GetServiceType() in desired_types
                
            
            services = filter( func, self._services_sorted )
            
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
                
                for ( status, pairs ) in statuses_to_pairs.items():
                    
                    new_statuses_to_pairs[ status ] = { ( one, two ) for ( one, two ) in pairs if self._CensorshipMatches( one, blacklist, censorships ) and self._CensorshipMatches( two, blacklist, censorships ) }
                    
                
                statuses_to_pairs = new_statuses_to_pairs
                
            
        
        return statuses_to_pairs
        
    
    def FilterServiceKeysToStatusesToTags( self, service_keys_to_statuses_to_tags ):
        
        if CC.COMBINED_TAG_SERVICE_KEY in self._service_keys_to_info:
            
            ( blacklist, censorships ) = self._service_keys_to_info[ CC.COMBINED_TAG_SERVICE_KEY ]
            
            service_keys = service_keys_to_statuses_to_tags.keys()
            
            for service_key in service_keys:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = statuses_to_tags.keys()
                
                for status in statuses:
                    
                    tags = statuses_to_tags[ status ]
                    
                    statuses_to_tags[ status ] = { tag for tag in tags if self._CensorshipMatches( tag, blacklist, censorships ) }
                    
                
            
        
        for ( service_key, ( blacklist, censorships ) ) in self._service_keys_to_info.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                continue
                
            
            if service_key in service_keys_to_statuses_to_tags:
                
                statuses_to_tags = service_keys_to_statuses_to_tags[ service_key ]
                
                statuses = statuses_to_tags.keys()
                
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
        
        self._service_keys_to_children_to_parents = collections.defaultdict( HydrusData.default_dict_list )
        
        self._RefreshParents()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'RefreshParents', 'notify_new_parents' )
        
    
    def _RefreshParents( self ):
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_parents' )
        
        # first collapse siblings
        
        sibling_manager = self._controller.GetManager( 'tag_siblings' )
        
        collapsed_service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY: continue
            
            for ( status, pairs ) in statuses_to_pairs.items():
                
                pairs = sibling_manager.CollapsePairs( service_key, pairs )
                
                collapsed_service_keys_to_statuses_to_pairs[ service_key ][ status ] = pairs
                
            
        
        # now collapse current and pending
        
        service_keys_to_pairs_flat = HydrusData.default_dict_set()
        
        for ( service_key, statuses_to_pairs ) in collapsed_service_keys_to_statuses_to_pairs.items():
            
            pairs_flat = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            service_keys_to_pairs_flat[ service_key ] = pairs_flat
            
        
        # now create the combined tag service
        
        combined_pairs_flat = set()
        
        for pairs_flat in service_keys_to_pairs_flat.values():
            
            combined_pairs_flat.update( pairs_flat )
            
        
        service_keys_to_pairs_flat[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_pairs_flat
        
        #
        
        service_keys_to_simple_children_to_parents = BuildServiceKeysToSimpleChildrenToParents( service_keys_to_pairs_flat )
        
        self._service_keys_to_children_to_parents = BuildServiceKeysToChildrenToParents( service_keys_to_simple_children_to_parents )
        
    
    def ExpandPredicates( self, service_key, predicates ):
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
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
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            tags_results = set( tags )
            
            for tag in tags:
                
                tags_results.update( self._service_keys_to_children_to_parents[ service_key ][ tag ] )
                
            
            return tags_results
            
        
    
    def GetParents( self, service_key, tag ):
        
        new_options = self._controller.GetNewOptions()
        
        if new_options.GetBoolean( 'apply_all_parents_to_all_services' ):
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        with self._lock:
            
            return self._service_keys_to_children_to_parents[ service_key ][ tag ]
            
        
    
    def RefreshParents( self ):
        
        with self._lock:
            
            self._RefreshParents()
            
        
    
class TagSiblingsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        self._RefreshSiblings()
        
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'RefreshSiblings', 'notify_new_siblings_data' )
        
    
    def _CollapseTags( self, service_key, tags ):
    
        siblings = self._service_keys_to_siblings[ service_key ]
        
        return { siblings[ tag ] if tag in siblings else tag for tag in tags }
        
    
    def _RefreshSiblings( self ):
        
        self._service_keys_to_siblings = collections.defaultdict( dict )
        self._service_keys_to_reverse_lookup = collections.defaultdict( dict )
        
        combined_pairs = set()
        
        service_keys_to_statuses_to_pairs = self._controller.Read( 'tag_siblings' )
        
        for ( service_key, statuses_to_pairs ) in service_keys_to_statuses_to_pairs.items():
            
            all_pairs = statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
            
            combined_pairs.update( all_pairs )
            
            siblings = CollapseTagSiblingPairs( all_pairs )
            
            self._service_keys_to_siblings[ service_key ] = siblings
            
            reverse_lookup = collections.defaultdict( list )
            
            for ( bad, good ) in siblings.items():
                
                reverse_lookup[ good ].append( bad )
                
            
            self._service_keys_to_reverse_lookup[ service_key ] = reverse_lookup
            
        
        combined_siblings = CollapseTagSiblingPairs( combined_pairs )
        
        self._service_keys_to_siblings[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_siblings
        
        combined_reverse_lookup = collections.defaultdict( list )
        
        for ( bad, good ) in combined_siblings.items():
            
            combined_reverse_lookup[ good ].append( bad )
            
        
        self._service_keys_to_reverse_lookup[ CC.COMBINED_TAG_SERVICE_KEY ] = combined_reverse_lookup
        
        self._controller.pub( 'new_siblings_gui' )
        
    
    def GetAutocompleteSiblings( self, service_key, search_text, exact_match = False ):
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            reverse_lookup = self._service_keys_to_reverse_lookup[ service_key ]
            
            if exact_match:
                
                key_based_matching_values = set()
                
                if search_text in siblings:
                    
                    key_based_matching_values = { siblings[ search_text ] }
                    
                else:
                    
                    key_based_matching_values = set()
                    
                
                value_based_matching_values = { value for value in siblings.values() if value == search_text }
                
            else:
                
                matching_keys = ClientSearch.FilterTagsBySearchText( service_key, search_text, siblings.keys(), search_siblings = False )
                
                key_based_matching_values = { siblings[ key ] for key in matching_keys }
                
                value_based_matching_values = ClientSearch.FilterTagsBySearchText( service_key, search_text, siblings.values(), search_siblings = False )
                
            
            matching_values = key_based_matching_values.union( value_based_matching_values )
            
            # all the matching values have a matching sibling somewhere in their network
            # so now fetch the networks
            
            lists_of_matching_keys = [ reverse_lookup[ value ] for value in matching_values ]
            
            matching_keys = itertools.chain.from_iterable( lists_of_matching_keys )
            
            matches = matching_values.union( matching_keys )
            
            return matches
            
        
    
    def GetSibling( self, service_key, tag ):
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return None
                
            
        
    
    def GetAllSiblings( self, service_key, tag ):
        
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
            
        
    
    def RefreshSiblings( self ):
        
        with self._lock:
            
            self._RefreshSiblings()
            
        
    
    def CollapsePredicates( self, service_key, predicates ):
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = [ predicate for predicate in predicates if predicate.GetType() != HC.PREDICATE_TYPE_TAG ]
            
            tag_predicates = [ predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
            
            tags_to_predicates = { predicate.GetValue() : predicate for predicate in predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG }
            
            tags = tags_to_predicates.keys()
            
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
        
        with self._lock:
            
            statuses = statuses_to_tags.keys()
            
            new_statuses_to_tags = HydrusData.default_dict_set()
            
            for status in statuses:
                
                new_statuses_to_tags[ status ] = self._CollapseTags( service_key, statuses_to_tags[ status ] )
                
            
            return new_statuses_to_tags
            
        
    
    def CollapseTag( self, service_key, tag ):
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            if tag in siblings:
                
                return siblings[ tag ]
                
            else:
                
                return tag
                
            
        
    
    def CollapseTags( self, service_key, tags ):
        
        with self._lock:
            
            return self._CollapseTags( service_key, tags )
            
        
    
    def CollapseTagsToCount( self, service_key, tags_to_count ):
        
        with self._lock:
            
            siblings = self._service_keys_to_siblings[ service_key ]
            
            results = collections.Counter()
            
            for ( tag, count ) in tags_to_count.items():
                
                if tag in siblings:
                    
                    tag = siblings[ tag ]
                    
                
                results[ tag ] += count
                
            
            return results
            
        
    
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
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
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
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
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
            
        
    
class WebSessionManagerClient( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        existing_sessions = self._controller.Read( 'web_sessions' )
        
        self._names_to_sessions = { name : ( cookies, expires ) for ( name, cookies, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def GetCookies( self, name ):
        
        now = HydrusData.GetNow()
        
        with self._lock:
            
            if name in self._names_to_sessions:
                
                ( cookies, expires ) = self._names_to_sessions[ name ]
                
                if HydrusData.TimeHasPassed( expires - 300 ): del self._names_to_sessions[ name ]
                else: return cookies
                
            
            # name not found, or expired
            
            if name == 'deviant art':
                
                ( response_gumpf, cookies ) = self._controller.DoHTTP( HC.GET, 'http://www.deviantart.com/', return_cookies = True )
                
                expires = now + 30 * 86400
                
            if name == 'hentai foundry':
                
                ( response_gumpf, cookies ) = self._controller.DoHTTP( HC.GET, 'http://www.hentai-foundry.com/?enterAgree=1', return_cookies = True )
                
                raw_csrf = cookies[ 'YII_CSRF_TOKEN' ] # 19b05b536885ec60b8b37650a32f8deb11c08cd1s%3A40%3A%222917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32%22%3B
                
                processed_csrf = urllib.unquote( raw_csrf ) # 19b05b536885ec60b8b37650a32f8deb11c08cd1s:40:"2917dcfbfbf2eda2c1fbe43f4d4c4ec4b6902b32";
                
                csrf_token = processed_csrf.split( '"' )[1] # the 2917... bit
                
                hentai_foundry_form_info = ClientDefaults.GetDefaultHentaiFoundryInfo()
                
                hentai_foundry_form_info[ 'YII_CSRF_TOKEN' ] = csrf_token
                
                body = urllib.urlencode( hentai_foundry_form_info )
                
                request_headers = {}
                ClientNetworking.AddCookiesToHeaders( cookies, request_headers )
                request_headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                self._controller.DoHTTP( HC.POST, 'http://www.hentai-foundry.com/site/filters', request_headers = request_headers, body = body )
                
                expires = now + 60 * 60
                
            elif name == 'pixiv':
                
                result = self._controller.Read( 'serialisable_simple', 'pixiv_account' )
                
                if result is None:
                    
                    raise HydrusExceptions.DataMissing( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                ( pixiv_id, password ) = result
                
                cookies = self.GetPixivCookies( pixiv_id, password )
                
                expires = now + 30 * 86400
                
            
            self._names_to_sessions[ name ] = ( cookies, expires )
            
            self._controller.Write( 'web_session', name, cookies, expires )
            
            return cookies
            
        
    
    # This updated login form is cobbled together from the example in PixivUtil2
    # it is breddy shid because I'm not using mechanize or similar browser emulation (like requests's sessions) yet
    # Pixiv 400s if cookies and referrers aren't passed correctly
    # I am leaving this as a mess with the hope the eventual login engine will replace it
    def GetPixivCookies( self, pixiv_id, password ):
        
        ( response, cookies ) = self._controller.DoHTTP( HC.GET, 'https://accounts.pixiv.net/login', return_cookies = True )
        
        soup = ClientDownloading.GetSoup( response )
        
        # some whocking 20kb bit of json tucked inside a hidden form input wew lad
        i = soup.find( 'input', id = 'init-config' )
        
        raw_json = i['value']
        
        j = json.loads( raw_json )
        
        if 'pixivAccount.postKey' not in j:
            
            raise HydrusExceptions.ForbiddenException( 'When trying to log into Pixiv, I could not find the POST key!' )
            
        
        post_key = j[ 'pixivAccount.postKey' ]
        
        form_fields = {}
        
        form_fields[ 'pixiv_id' ] = pixiv_id
        form_fields[ 'password' ] = password
        form_fields[ 'captcha' ] = ''
        form_fields[ 'g_recaptcha_response' ] = ''
        form_fields[ 'return_to' ] = 'http://www.pixiv.net'
        form_fields[ 'lang' ] = 'en'
        form_fields[ 'post_key' ] = post_key
        form_fields[ 'source' ] = 'pc'
        
        headers = {}
        
        headers[ 'referer' ] = "https://accounts.pixiv.net/login?lang=en^source=pc&view_type=page&ref=wwwtop_accounts_index"
        headers[ 'origin' ] = "https://accounts.pixiv.net"
        ClientNetworking.AddCookiesToHeaders( cookies, headers )
        
        r = requests.post( 'https://accounts.pixiv.net/api/login?lang=en', data = form_fields, headers = headers )
        
        # doesn't work
        #( response_gumpf, cookies ) = self._controller.DoHTTP( HC.POST, 'https://accounts.pixiv.net/api/login?lang=en', request_headers = headers, body = body, return_cookies = True )
        
        cookies = dict( r.cookies )
        
        # _ only given to logged-in php sessions
        if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]:
            
            raise HydrusExceptions.ForbiddenException( 'Pixiv login credentials not accepted!' )
            
        
        return cookies
        
    
