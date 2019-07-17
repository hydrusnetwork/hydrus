from . import ClientConstants as CC
from . import ClientImageHandling
from . import ClientPaths
from . import ClientThreading
import collections
import gc
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusGlobals as HG
from . import HydrusImageHandling
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusThreading
import os
import random
import threading
import time
import wx

REGENERATE_FILE_DATA_JOB_COMPLETE = 0
REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL = 1
REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL = 2
REGENERATE_FILE_DATA_JOB_OTHER_HASHES = 3
REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES = 4
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE = 5
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA = 6
REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS = 7
REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP = 8
REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA = 9

regen_file_enum_to_str_lookup = {}

regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_COMPLETE ] = 'complete reparse and thumbnail regen'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = 'regenerate thumbnail'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = 'regenerate thumbnail if incorrect size'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = 'regenerate non-standard hashes'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = 'delete duplicate neighbours with incorrect file extension'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE ] = 'check if file is present in file system'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA ] = 'check full file data integrity'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = 'fix file read/write permissions'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = 'check for membership in the similar files search system'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = 'regenerate similar files metadata'

regen_file_enum_to_ideal_job_size_lookup = {}

regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_COMPLETE ] = 100
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = 250
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = 1000
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = 25
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = 100
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE ] = 10000
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA ] = 100
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = 250
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = 100
regen_file_enum_to_ideal_job_size_lookup[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = 100

regen_file_enum_to_overruled_jobs = {}

regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_COMPLETE ] = [ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = [ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA ] = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = [ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ]

ALL_REGEN_JOBS_IN_PREFERRED_ORDER = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA, REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL, REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, REGENERATE_FILE_DATA_JOB_COMPLETE, REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA, REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP, REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS, REGENERATE_FILE_DATA_JOB_OTHER_HASHES, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ]

def GetAllFilePaths( raw_paths, do_human_sort = True ):
    
    file_paths = []
    
    paths_to_process = list( raw_paths )
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if HG.view_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
            if os.path.isdir( path ):
                
                subpaths = [ os.path.join( path, filename ) for filename in os.listdir( path ) ]
                
                next_paths_to_process.extend( subpaths )
                
            else:
                
                file_paths.append( path )
                
            
        
        paths_to_process = next_paths_to_process
        
    
    if do_human_sort:
        
        HydrusData.HumanTextSort( file_paths )
        
    
    return file_paths
    
class ClientFilesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._rwlock = ClientThreading.FileRWLock()
        
        self._prefixes_to_locations = {}
        
        self._bad_error_occurred = False
        self._missing_locations = set()
        
        self._Reinit()
        
    
    def _AddFile( self, hash, mime, source_path ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode or HG.file_import_report_mode:
            
            HydrusData.ShowText( 'Adding file to client file structure: from {} to {}'.format( source_path, dest_path ) )
            
        
        successful = HydrusPaths.MirrorFile( source_path, dest_path )
        
        if not successful:
            
            raise Exception( 'There was a problem copying the file from ' + source_path + ' to ' + dest_path + '!' )
            
        
    
    def _AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        dest_path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding thumbnail: ' + str( ( len( thumbnail_bytes ), dest_path ) ) )
            
        
        try:
            
            HydrusPaths.MakeFileWritable( dest_path )
            
            with open( dest_path, 'wb' ) as f:
                
                f.write( thumbnail_bytes )
                
            
        except Exception as e:
            
            hash_encoded = hash.hex()
            
            prefix = 't' + hash_encoded[:2]
            
            location = self._prefixes_to_locations[ prefix ]    
            
            thumb_dir = os.path.join( location, prefix )
            
            if not os.path.exists( thumb_dir ):
                
                raise HydrusExceptions.DirectoryMissingException( 'The directory {} was not found! Reconnect the missing location or shut down the client immediately!'.format( thumb_dir ) )
                
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file "{}" failed to write to path "{}". This event suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.'.format( hash.hex(), dest_path ) )
            
        
        if not silent:
            
            self._controller.pub( 'clear_thumbnails', { hash } )
            self._controller.pub( 'new_thumbnails', { hash } )
            
        
    
    def _AttemptToHealMissingLocations( self ):
        
        # if a missing prefix folder seems to be in another location, lets update to that other location
        
        correct_rows = []
        some_are_unhealable = False
        
        fixes_counter = collections.Counter()
        
        known_locations = set()
        
        known_locations.update( self._prefixes_to_locations.values() )
        
        ( locations_to_ideal_weights, thumbnail_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        known_locations.update( locations_to_ideal_weights.keys() )
        
        if thumbnail_override is not None:
            
            known_locations.add( thumbnail_override )
            
        
        for ( missing_location, prefix ) in self._missing_locations:
            
            potential_correct_locations = []
            
            for known_location in known_locations:
                
                if known_location == missing_location:
                    
                    continue
                    
                
                dir_path = os.path.join( known_location, prefix )
                
                if os.path.exists( dir_path ) and os.path.isdir( dir_path ):
                    
                    potential_correct_locations.append( known_location )
                    
                
            
            if len( potential_correct_locations ) == 1:
                
                correct_location = potential_correct_locations[0]
                
                correct_rows.append( ( missing_location, prefix, correct_location ) )
                
                fixes_counter[ ( missing_location, correct_location ) ] += 1
                
            else:
                
                some_are_unhealable = True
                
            
        
        if len( correct_rows ) > 0 and some_are_unhealable:
            
            message = 'Hydrus found multiple missing locations in your file storage. Some of these locations seemed to be fixable, others did not. The client will now inform you about both problems.'
            
            wx.SafeShowMessage( 'Multiple file location problems.', message )
            
        
        if len( correct_rows ) > 0:
            
            summaries = [ '{} moved from {} to {}'.format( HydrusData.ToHumanInt( count ), missing_location, correct_location ) for ( ( missing_location, correct_location ), count ) in fixes_counter.items() ]
            
            summaries.sort()
            
            summary_message = 'Some client file folders were missing, but they seem to be in other known locations! The folders are:'
            summary_message += os.linesep * 2
            summary_message += os.linesep.join( summaries )
            summary_message += os.linesep * 2
            summary_message += 'Assuming you did this on purpose, Hydrus is ready to update its internal knowledge to reflect these new mappings as soon as this dialog closes. If you know these proposed fixes are incorrect, terminate the program now.'
            
            HydrusData.Print( summary_message )
            
            wx.SafeShowMessage( 'About to auto-heal client file folders.', summary_message )
            
            HG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
            
        
    
    def _ChangeFileExt( self, hash, old_mime, mime ):
        
        old_path = self._GenerateExpectedFilePath( hash, old_mime )
        new_path = self._GenerateExpectedFilePath( hash, mime )
        
        if old_path == new_path:
            
            # some diff mimes have the same ext
            
            return
            
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Changing file ext: ' + str( ( old_path, new_path ) ) )
            
        
        if HydrusPaths.PathIsFree( old_path ):
            
            try:
                
                HydrusPaths.MergeFile( old_path, new_path )
                
                needed_to_copy_file = False
                
            except:
                
                HydrusPaths.MirrorFile( old_path, new_path )
                
                needed_to_copy_file = True
                
            
        else:
            
            HydrusPaths.MirrorFile( old_path, new_path )
            
            needed_to_copy_file = True
            
        
        return needed_to_copy_file
        
    
    def _GenerateExpectedFilePath( self, hash, mime ):
        
        self._WaitOnWakeup()
        
        hash_encoded = hash.hex()
        
        prefix = 'f' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded + HC.mime_ext_lookup[ mime ] )
        
        return path
        
    
    def _GenerateExpectedThumbnailPath( self, hash ):
        
        self._WaitOnWakeup()
        
        hash_encoded = hash.hex()
        
        prefix = 't' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        path = os.path.join( location, prefix, hash_encoded ) + '.thumbnail'
        
        return path
        
    
    def _GenerateThumbnailBytes( self, file_path, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        ( width, height ) = media.GetResolution()
        duration = media.GetDuration()
        num_frames = media.GetNumFrames()
        
        bounding_dimensions = HG.client_controller.options[ 'thumbnail_dimensions' ]
        
        target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions )
        
        percentage_in = self._controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
        
        try:
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( file_path, target_resolution, mime, duration, num_frames, percentage_in = percentage_in )
            
        except Exception as e:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file for the above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
            
        
        return thumbnail_bytes
        
    
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
        
        ( locations_to_ideal_weights, thumbnail_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
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
            
            for hex_prefix in HydrusData.IterateHexPrefixes():
                
                thumbnail_prefix = 't' + hex_prefix
                
                if thumbnail_override is None:
                    
                    file_prefix = 'f' + hex_prefix
                    
                    correct_location = self._prefixes_to_locations[ file_prefix ]
                    
                else:
                    
                    correct_location = thumbnail_override
                    
                
                current_thumbnails_location = self._prefixes_to_locations[ thumbnail_prefix ]
                
                if current_thumbnails_location != correct_location:
                    
                    return ( thumbnail_prefix, current_thumbnails_location, correct_location )
                    
                
            
        
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
            
            if prefix.startswith( 't' ):
                
                dir = os.path.join( location, prefix )
                
                filenames = os.listdir( dir )
                
                for filename in filenames:
                    
                    yield os.path.join( dir, filename )
                    
                
            
        
    
    def _LookForFilePath( self, hash ):
        
        for potential_mime in HC.ALLOWED_MIMES:
            
            potential_path = self._GenerateExpectedFilePath( hash, potential_mime )
            
            if os.path.exists( potential_path ):
                
                return ( potential_path, potential_mime )
                
            
        
        hash_encoded = hash.hex()
        
        prefix = 'f' + hash_encoded[:2]
        
        location = self._prefixes_to_locations[ prefix ]
        
        subdir = os.path.join( location, prefix )
        
        if not os.path.exists( subdir ):
            
            raise HydrusExceptions.DirectoryMissingException( 'The directory {} was not found! Reconnect the missing location or shut down the client immediately!'.format( subdir ) )
            
        
        raise HydrusExceptions.FileMissingException( 'File for ' + hash.hex() + ' not found!' )
        
    
    def _Reinit( self ):
        
        self._prefixes_to_locations = self._controller.Read( 'client_files_locations' )
        
        if HG.client_controller.IsFirstStart():
            
            try:
                
                for ( prefix, location ) in list( self._prefixes_to_locations.items() ):
                    
                    HydrusPaths.MakeSureDirectoryExists( location )
                    
                    subdir = os.path.join( location, prefix )
                    
                    HydrusPaths.MakeSureDirectoryExists( subdir )
                    
                
            except:
                
                text = 'Attempting to create the database\'s client_files folder structure in {} failed!'.format( location )
                
                wx.SafeShowMessage( 'unable to create file structure', text )
                
                raise
                
            
        else:
            
            self._ReinitMissingLocations()
            
            if len( self._missing_locations ) > 0:
                
                self._AttemptToHealMissingLocations()
                
                self._prefixes_to_locations = self._controller.Read( 'client_files_locations' )
                
                self._ReinitMissingLocations()
                
            
            if len( self._missing_locations ) > 0:
                
                self._bad_error_occurred = True
                
                #
                
                missing_dict = HydrusData.BuildKeyToListDict( self._missing_locations )
                
                missing_locations = list( missing_dict.keys() )
                
                missing_locations.sort()
                
                missing_string = ''
                
                for missing_location in missing_locations:
                    
                    missing_prefixes = list( missing_dict[ missing_location ] )
                    
                    missing_prefixes.sort()
                    
                    missing_prefixes_string = '    ' + os.linesep.join( ( ', '.join( block ) for block in HydrusData.SplitListIntoChunks( missing_prefixes, 32 ) ) )
                    
                    missing_string += os.linesep
                    missing_string += missing_location
                    missing_string += os.linesep
                    missing_string += missing_prefixes_string
                    
                
                #
                
                if len( self._missing_locations ) > 4:
                    
                    text = 'When initialising the client files manager, some file locations did not exist! They have all been written to the log!'
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    wx.SafeShowMessage( 'missing locations', text )
                    
                    HydrusData.DebugPrint( text )
                    HydrusData.DebugPrint( 'Missing locations follow:' )
                    HydrusData.DebugPrint( missing_string )
                    
                else:
                    
                    text = 'When initialising the client files manager, these file locations did not exist:'
                    text += os.linesep * 2
                    text += missing_string
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    wx.SafeShowMessage( 'missing locations', text )
                    HydrusData.DebugPrint( text )
                    
                
            
        
    
    def _ReinitMissingLocations( self ):
        
        self._missing_locations = set()
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if os.path.exists( location ):
                
                subdir = os.path.join( location, prefix )
                
                if not os.path.exists( subdir ):
                    
                    self._missing_locations.add( ( location, prefix ) )
                    
                
            else:
                
                self._missing_locations.add( ( location, prefix ) )
                
            
        
    
    def _WaitOnWakeup( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'file_system_waits_on_wakeup' ):
            
            while HG.client_controller.JustWokeFromSleep():
                
                HydrusThreading.CheckIfThreadShuttingDown()
                
                time.sleep( 1.0 )
                
            
        
    
    def AllLocationsAreDefault( self ):
        
        with self._rwlock.read:
            
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
            
        
    
    def AddFile( self, hash, mime, source_path, thumbnail_bytes = None ):
        
        with self._rwlock.write:
            
            self._AddFile( hash, mime, source_path )
            
            if thumbnail_bytes is not None:
                
                self._AddThumbnailFromBytes( hash, thumbnail_bytes )
                
            
        
    
    def AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        with self._rwlock.write:
            
            self._AddThumbnailFromBytes( hash, thumbnail_bytes, silent = silent )
            
        
    
    def ChangeFileExt( self, hash, old_mime, mime ):
        
        with self._rwlock.write:
            
            return self._ChangeFileExt( hash, old_mime, mime )
            
        
    
    def ClearOrphans( self, move_location = None ):
        
        with self._rwlock.write:
            
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
            
            with self._rwlock.write:
                
                for hash in hashes_chunk:
                    
                    try:
                        
                        ( path, mime ) = self._LookForFilePath( hash )
                        
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
            
            with self._rwlock.write:
                
                for hash in hashes_chunk:
                    
                    path = self._GenerateExpectedThumbnailPath( hash )
                    
                    ClientPaths.DeletePath( path, always_delete_fully = True )
                    
                
            
            big_pauser.Pause()
            
        
    
    def DeleteNeighbourDupes( self, hash, true_mime ):
        
        with self._rwlock.write:
            
            correct_path = self._GenerateExpectedFilePath( hash, true_mime )
            
            if not os.path.exists( correct_path ):
                
                return # misfire, let's not actually delete the right one
                
            
            for mime in HC.ALLOWED_MIMES:
                
                if mime == true_mime:
                    
                    continue
                    
                
                incorrect_path = self._GenerateExpectedFilePath( hash, mime )
                
                if incorrect_path == correct_path:
                    
                    # some diff mimes have the same ext
                    
                    continue
                    
                
                if os.path.exists( incorrect_path ):
                    
                    HydrusPaths.DeletePath( incorrect_path )
                    
                
            
        
    
    def GetCurrentFileLocations( self ):
        
        with self._rwlock.read:
            
            locations = set()
            
            for ( prefix, location ) in self._prefixes_to_locations.items():
                
                if prefix.startswith( 'f' ):
                    
                    locations.add( location )
                    
                
            
            return locations
            
        
    
    def GetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        with self._rwlock.read:
            
            return self.LocklessGetFilePath( hash, mime = mime, check_file_exists = check_file_exists )
            
        
    
    def GetMissing( self ):
        
        return self._missing_locations
        
    
    def LocklessGetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'File path request: ' + str( ( hash, mime ) ) )
            
        
        if mime is None:
            
            ( path, mime ) = self._LookForFilePath( hash )
            
        else:
            
            path = self._GenerateExpectedFilePath( hash, mime )
            
            if check_file_exists and not os.path.exists( path ):
                
                try:
                    
                    # let's see if the file exists, but with the wrong ext!
                    
                    ( actual_path, old_mime ) = self._LookForFilePath( hash )
                    
                except HydrusExceptions.FileMissingException:
                    
                    raise HydrusExceptions.FileMissingException( 'No file found at path {}!'.format( path ) )
                    
                
                self._ChangeFileExt( hash, old_mime, mime )
                
                # we have now fixed the path, it is good to return
                
            
        
        return path
        
    
    def GetThumbnailPath( self, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path request: ' + str( ( hash, mime ) ) )
            
        
        with self._rwlock.read:
            
            path = self._GenerateExpectedThumbnailPath( hash )
            
            thumb_missing = not os.path.exists( path )
            
        
        if thumb_missing:
            
            self.RegenerateThumbnail( media )
            
        
        return path
        
    
    def LocklessHasThumbnail( self, hash ):
        
        path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def Rebalance( self, job_key ):
        
        try:
            
            if self._bad_error_occurred:
                
                wx.MessageBox( 'A serious file error has previously occurred during this session, so further file moving will not be reattempted. Please restart the client before trying again.' )
                
                return
                
            
            with self._rwlock.write:
                
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
        
        with self._rwlock.read:
            
            return self._GetRebalanceTuple() is not None
            
        
    
    def RegenerateThumbnail( self, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        with self._rwlock.read:
            
            file_path = self._GenerateExpectedFilePath( hash, mime )
            
            if not os.path.exists( file_path ):
                
                raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file because the original file is missing! This event could indicate hard drive corruption. Please check everything is ok.')
                
            
            thumbnail_bytes = self._GenerateThumbnailBytes( file_path, media )
            
        
        with self._rwlock.write:
            
            self._AddThumbnailFromBytes( hash, thumbnail_bytes )
            
        
    
    def RegenerateThumbnailIfWrongSize( self, media ):
        
        do_it = False
        
        try:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if mime not in HC.MIMES_WITH_THUMBNAILS:
                
                return
                
            
            ( media_width, media_height ) = media.GetResolution()
            
            path = self._GenerateExpectedThumbnailPath( hash )
            
            numpy_image = ClientImageHandling.GenerateNumPyImage( path, mime )
            
            ( current_width, current_height ) = HydrusImageHandling.GetResolutionNumPy( numpy_image )
            
            bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
            
            ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( ( media_width, media_height ), bounding_dimensions )
            
            if current_width != expected_width or current_height != expected_height:
                
                do_it = True
                
            
        except:
            
            do_it = True
            
        
        if do_it:
            
            self.RegenerateThumbnail( media )
            
        
        return do_it
        
    
class FilesMaintenanceManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._pubbed_message_about_missing_files = False
        self._pubbed_message_about_damaged_files = False
        
        self._work_tracker = HydrusNetworking.BandwidthTracker()
        
        self._work_rules = HydrusNetworking.BandwidthRules()
        
        self._ReInitialiseWorkRules()
        
        self._maintenance_lock = threading.Lock()
        self._lock = threading.Lock()
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        
    
    def _AbleToDoMaintenance( self ):
        
        if self._controller.new_options.GetBoolean( 'file_maintenance_throttle_enable' ):
            
            return self._work_rules.CanStartRequest( self._work_tracker )
            
        
        return True
        
    
    def _CheckFileIntegrity( self, media_result, job_type ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        error_dir = os.path.join( self._controller.GetDBDir(), 'missing_and_invalid_files' )
        
        file_is_missing = False
        file_is_invalid = False
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            file_is_missing = True
            
            HydrusData.DebugPrint( 'Missing file: {}!'.format( hash.hex() ) )
            
        
        if not file_is_missing and job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA:
            
            actual_hash = HydrusFileHandling.GetHashFromPath( path )
            
            if hash != actual_hash:
                
                file_is_invalid = True
                
                HydrusData.DebugPrint( 'Invalid file: {} actually had hash {}!'.format( hash.hex(), actual_hash.hex() ) )
                
                HydrusPaths.MakeSureDirectoryExists( error_dir )
                
                dest_path = os.path.join( error_dir, os.path.basename( path ) )
                
                HydrusPaths.MergeFile( path, dest_path )
                
                if not self._pubbed_message_about_damaged_files:
                    
                    self._pubbed_message_about_damaged_files = True
                    
                    message = 'During file maintenance, a file was found to be invalid. It has been moved to {}.'.format( error_dir )
                    message += os.linesep * 2
                    message += 'More files may be invalid, but this message will not appear again during this boot.'
                    
                    HydrusData.ShowText( message )
                    
                
            
        
        file_was_bad = file_is_missing or file_is_invalid
        
        if file_was_bad:
            
            urls = media_result.GetLocationsManager().GetURLs()
            
            if len( urls ) > 0:
                
                HydrusPaths.MakeSureDirectoryExists( error_dir )
                
                with open( os.path.join( error_dir, hash.hex() + '.urls.txt' ), 'w', encoding = 'utf-8' ) as f:
                    
                    for url in urls:
                        
                        f.write( url )
                        f.write( os.linesep )
                        
                    
                
                with open( os.path.join( error_dir, 'all_urls.txt' ), 'a', encoding = 'utf-8' ) as f:
                    
                    for url in urls:
                        
                        f.write( url )
                        f.write( os.linesep )
                        
                    
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'Record deleted during File Integrity check.' )
            
            for service_key in [ CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY, CC.TRASH_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ]:
                
                service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
                
                self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            
            if not self._pubbed_message_about_missing_files:
                
                self._pubbed_message_about_missing_files = True
                
                message = 'During file maintenance, a file was found to be missing or invalid. Its record has been removed from the database. More information has been been written to the log, and any known URLs for the file have been written to {}.'.format( error_dir )
                message += os.linesep * 2
                message += 'More files may be missing or invalid, but this message will not appear again during this boot.'
                
                HydrusData.ShowText( message )
                
            
        
        return file_was_bad
        
    
    def _CheckSimilarFilesMembership( self, media_result ):
        
        mime = media_result.GetMime()
        
        return mime in HC.MIMES_WE_CAN_PHASH
        
    
    def _ClearJobs( self, hashes, job_type ):
        
        cleared_jobs = [ ( hash, job_type, None ) for hash in hashes ]
        
        self._controller.WriteSynchronous( 'file_maintenance_clear_jobs', cleared_jobs )
        
    
    def _DeleteNeighbourDupes( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        self._controller.client_files_manager.DeleteNeighbourDupes( hash, mime )
        
    
    def _FixFilePermissions( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            HydrusPaths.MakeFileWritable( path )
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileData( self, media_result ):
        
        hash = media_result.GetHash()
        original_mime = media_result.GetMime()
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, original_mime )
            
            ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path, ok_to_look_for_hydrus_updates = True )
            
            additional_data = ( size, mime, width, height, duration, num_frames, num_words )
            
            if mime != original_mime:
                
                needed_to_dupe_the_file = self._controller.client_files_manager.ChangeFileExt( hash, original_mime, mime )
                
                if needed_to_dupe_the_file:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusData.GetNow() + ( 7 * 86400 ) )
                    
                
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                self._RegenFileThumbnailForce( media_result )
                
            
            return additional_data
            
        except HydrusExceptions.MimeException:
            
            self._CheckFileIntegrity( media_result, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA )
            
            return None
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileOtherHashes( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime in HC.HYDRUS_UPDATE_FILES:
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            ( md5, sha1, sha512 ) = HydrusFileHandling.GetExtraHashesFromPath( path )
            
            additional_data = ( md5, sha1, sha512 )
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenSimilarFilesMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_WE_CAN_PHASH:
            
            self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP )
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( path, mime )
        
        return phashes
        
    
    def _RegenFileThumbnailForce( self, media_result ):
        
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        try:
            
            self._controller.client_files_manager.RegenerateThumbnail( media_result )
            
        except HydrusExceptions.FileMissingException:
            
            pass
            
        
    
    def _RegenFileThumbnailRefit( self, media_result ):
        
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        try:
            
            was_regenerated = self._controller.client_files_manager.RegenerateThumbnailIfWrongSize( media_result )
            
            return was_regenerated
            
        except HydrusExceptions.FileMissingException:
            
            pass
            
        
    
    def _ReInitialiseWorkRules( self ):
        
        file_maintenance_throttle_files = self._controller.new_options.GetInteger( 'file_maintenance_throttle_files' )
        file_maintenance_throttle_time_delta = self._controller.new_options.GetInteger( 'file_maintenance_throttle_time_delta' )
        
        self._work_rules = HydrusNetworking.BandwidthRules()
        
        self._work_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, file_maintenance_throttle_time_delta, file_maintenance_throttle_files )
        
    
    def _RunJob( self, media_results, job_type, job_key, doing_background_maintenance = False ):
        
        num_bad_files = 0
        num_thumb_refits = 0
        
        try:
            
            cleared_jobs = []
            
            num_to_do = len( media_results )
            
            for ( i, media_result ) in enumerate( media_results ):
                
                hash = media_result.GetHash()
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                if doing_background_maintenance and not self._AbleToDoMaintenance():
                    
                    return
                    
                
                status_text = '{}: {}'.format( regen_file_enum_to_str_lookup[ job_type ], HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                
                if i % 10 == 0:
                    
                    self._controller.pub( 'splash_set_status_text', status_text )
                    
                
                job_key.SetVariable( 'popup_text_1', status_text )
                job_key.SetVariable( 'popup_gauge_1', ( i + 1, num_to_do ) )
                
                additional_data = None
                
                try:
                    
                    if job_type == REGENERATE_FILE_DATA_JOB_COMPLETE:
                        
                        additional_data = self._RegenFileData( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                        
                        additional_data = self._RegenFileOtherHashes( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                        
                        self._RegenFileThumbnailForce( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                        
                        was_regenerated = self._RegenFileThumbnailRefit( media_result )
                        
                        if was_regenerated:
                            
                            num_thumb_refits += 1
                            
                        
                        job_key.SetVariable( 'popup_text_2', 'thumbs needing regen: {}'.format( HydrusData.ToHumanInt( num_thumb_refits ) ) )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES:
                        
                        self._DeleteNeighbourDupes( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                        
                        additional_data = self._CheckSimilarFilesMembership( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                        
                        additional_data = self._RegenSimilarFilesMetadata( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS:
                        
                        self._FixFilePermissions( media_result )
                        
                    elif job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA ):
                        
                        file_was_bad = self._CheckFileIntegrity( media_result, job_type )
                        
                        if file_was_bad:
                            
                            num_bad_files += 1
                            
                        
                        job_key.SetVariable( 'popup_text_2', 'missing or invalid files: {}'.format( HydrusData.ToHumanInt( num_bad_files ) ) )
                        
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    message = 'There was a problem performing maintenance task {} on file {}! The job will not be reattempted. A full traceback of this error should be written to the log.'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() )
                    message += os.linesep * 2
                    message += str( e )
                    
                    HydrusData.ShowText( message )
                    
                finally:
                    
                    self._work_tracker.ReportRequestUsed()
                    
                    cleared_jobs.append( ( hash, job_type, additional_data ) )
                    
                
                if len( cleared_jobs ) > 100:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_clear_jobs', cleared_jobs )
                    
                    cleared_jobs = []
                    
                
            
        finally:
            
            if len( cleared_jobs ) > 0:
                
                self._controller.Write( 'file_maintenance_clear_jobs', cleared_jobs )
                
            
        
    
    def ClearJobs( self, hashes, job_type ):
        
        with self._lock:
            
            self._ClearJobs( hashes, job_type )
            
        
    
    def DoMaintenance( self, mandated_job_types = None, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        if maintenance_mode == HC.MAINTENANCE_IDLE:
            
            if not self._controller.new_options.GetBoolean( 'file_maintenance_during_idle' ):
                
                return
                
            
            if not self._controller.GoodTimeToStartBackgroundWork():
                
                return
                
            
        
        doing_background_maintenance = maintenance_mode != HC.MAINTENANCE_FORCED
        
        with self._lock:
            
            if doing_background_maintenance and not self._AbleToDoMaintenance():
                
                return
                
            
        
        job_key = ClientThreading.JobKey( cancellable = True, maintenance_mode = maintenance_mode, stop_time = stop_time )
        
        job_key.SetVariable( 'popup_title', 'regenerating file data' )
        
        message_pubbed = False
        
        with self._maintenance_lock:
            
            try:
                
                while True:
                    
                    job = self._controller.Read( 'file_maintenance_get_job', mandated_job_types )
                    
                    if job is None:
                        
                        break
                        
                    
                    if not message_pubbed:
                        
                        self._controller.pub( 'message', job_key )
                        
                        message_pubbed = True
                        
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                    ( hashes, job_type ) = job
                    
                    media_results = self._controller.Read( 'media_results', hashes )
                    
                    hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                    
                    missing_hashes = [ hash for hash in hashes if hash not in hashes_to_media_results ]
                    
                    with self._lock:
                        
                        self._RunJob( media_results, job_type, job_key, doing_background_maintenance = doing_background_maintenance )
                        
                        self._ClearJobs( missing_hashes, job_type )
                        
                        if doing_background_maintenance and not self._AbleToDoMaintenance():
                            
                            return
                            
                        
                    
                    time.sleep( 0.0001 )
                    
                
            finally:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
                job_key.Finish()
                
                job_key.Delete( 5 )
                
                if not message_pubbed and maintenance_mode == HC.MAINTENANCE_FORCED:
                    
                    HydrusData.ShowText( 'No file maintenance due!' )
                    
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def GetIdleShutdownWorkDue( self ):
        
        with self._lock:
            
            if not self._AbleToDoMaintenance():
                
                return []
                
            
            job_types_to_counts = self._controller.Read( 'file_maintenance_get_job_counts' )
            
            statements = []
            
            for job_type in ALL_REGEN_JOBS_IN_PREFERRED_ORDER:
                
                if job_type in job_types_to_counts:
                    
                    statement = '{}: {} files'.format( regen_file_enum_to_str_lookup[ job_type ], HydrusData.ToHumanInt( job_types_to_counts[ job_type ] ) )
                    
                    statements.append( statement )
                    
                
            
            return statements
            
        
    
    def NotifyNewOptions( self ):
        
        with self._lock:
            
            self._ReInitialiseWorkRules()
            
        
    
    def RunJobImmediately( self, media_results, job_type, pub_job_key = True ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'regenerating file data' )
        
        if pub_job_key:
            
            self._controller.pub( 'message', job_key )
            
        
        with self._lock:
            
            try:
                
                self._RunJob( media_results, job_type, job_key, doing_background_maintenance = False )
                
            finally:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
                job_key.Finish()
                
                job_key.Delete( 5 )
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def ScheduleJob( self, hashes, job_type, time_can_start = 0 ):
        
        with self._lock:
            
            self._controller.Write( 'file_maintenance_add_jobs_hashes', hashes, job_type, time_can_start )
            
        
    
