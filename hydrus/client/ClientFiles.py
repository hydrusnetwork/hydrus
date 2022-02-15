import collections
import os
import queue
import random
import threading
import time

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPaths
from hydrus.core import HydrusThreading
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientImageHandling
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.gui import QtPorting as QP

REGENERATE_FILE_DATA_JOB_FILE_METADATA = 0
REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL = 1
REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL = 2
REGENERATE_FILE_DATA_JOB_OTHER_HASHES = 3
REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES = 4
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD = 5
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD = 6
REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS = 7
REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP = 8
REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA = 9
REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP = 10
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL = 11
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL = 12
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE = 13
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD = 14
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD = 15
REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE = 16
REGENERATE_FILE_DATA_JOB_PIXEL_HASH = 17

regen_file_enum_to_str_lookup = {}

regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_METADATA ] = 'regenerate file metadata'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = 'regenerate thumbnail'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = 'regenerate thumbnail if incorrect size'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = 'regenerate non-standard hashes'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = 'delete duplicate neighbours with incorrect file extension'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ] = 'if file is missing, remove record'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ] = 'if file is missing, then if has URL try to redownload'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD ] = 'if file is missing, then if has URL try to redownload, else remove record'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ] = 'if file is missing/incorrect, move file out and remove record'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ] = 'if file is missing/incorrect, then move file out, and if has URL try to redownload'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ] = 'if file is missing/incorrect, then move file out, and if has URL try to redownload, else remove record'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ] = 'if file is incorrect, move file out'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = 'fix file read/write permissions'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = 'check for membership in the similar files search system'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = 'regenerate similar files metadata'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP ] = 'regenerate file modified date'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE ] = 'determine if the file has an icc profile'
regen_file_enum_to_str_lookup[ REGENERATE_FILE_DATA_JOB_PIXEL_HASH ] = 'calculate file pixel hash'

regen_file_enum_to_description_lookup = {}

regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_METADATA ] = 'This regenerates file metadata like resolution and duration, or even filetype (such as mkv->webm), which may have been misparsed in a previous version.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = 'This forces a complete regeneration of the thumbnail from the source file.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = 'This looks for the existing thumbnail, and if it is not the correct resolution or is missing, will regenerate a new one for the source file.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = 'This regenerates hydrus\'s store of md5, sha1, and sha512 supplementary hashes, which it can use for various external (usually website) lookups.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = 'Sometimes, a file metadata regeneration will mean a new filetype and thus a new file extension. If the existing, incorrectly named file is in use, it must be copied rather than renamed, and so there is a spare duplicate left over after the operation. This jobs cleans up the duplicate at a later time.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ] = 'This checks to see if the file is present in the file system as expected. If it is not, the internal file record in the database is removed, just as if the file were deleted. Use this if you have manually deleted or otherwise lost a number of files from your file structure and need hydrus to re-sync with what it actually has. Missing files will have their known URLs exported to your database directory.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ] = 'This checks to see if the file is present in the file system as expected. If it is not, and it has known post/file URLs, the URLs will be automatically added to a new URL downloader. Missing files will also have their known URLs exported to your database directory.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD ] = 'THIS IS THE EASY AND QUICK ONE-SHOT WAY TO FIX A DATABASE WITH MISSING FILES. This checks to see if the file is present in the file system as expected. If it is not, then if it has known post/file URLs, the URLs will be automatically added to a new URL downloader. If it has no URLs, then the internal file record in the database is removed, just as if the file were deleted. Missing files will also have their known URLs exported to your database directory.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ] = 'This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect, it will be exported to your database directory along with their known URLs, and the file record deleted.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ] = 'This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect _and_ is has known post/file URLs, the URLs will be automatically added to a new URL downloader. Incorrect files will also have their known URLs exported to your database directory.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ] = 'This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect _and_ is has known post/file URLs, the URLs will be automatically added to a new URL downloader. If it has no URLs, then the internal file record in the database is removed, just as if the file were deleted. Incorrect files will also have their known URLs exported to your database directory.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ] = 'If the file is where it is expected, this ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect, it will be exported to your database directory along with its known URLs. The client\'s file record will not be deleted. This is useful if you have a valid backup and need to clear out invalid files from your live db so you can fill in gaps from your backup with a program like FreeFileSync.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = 'This ensures that files in the file system are readable and writeable. For Linux/macOS users, it specifically sets 644. If you wish to run this job on Linux/macOS, ensure you are first the file owner of all your files.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = 'This checks to see if files should be in the similar files system, and if they are falsely in or falsely out, it will remove their record or queue them up for a search as appropriate. It is useful to repair database damage.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = 'This forces a regeneration of the file\'s similar-files \'phashes\'. It is not useful unless you know there is missing data to repair.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP ] = 'This rechecks the file\'s modified timestamp and saves it to the database.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE ] = 'This loads the file to see if it has an ICC profile, which is used in "system:has icc profile" search.'
regen_file_enum_to_description_lookup[ REGENERATE_FILE_DATA_JOB_PIXEL_HASH ] = 'This generates a fast unique identifier for the pixels in a still image, which is used in duplicate pixel searches.'

NORMALISED_BIG_JOB_WEIGHT = 100

regen_file_enum_to_job_weight_lookup = {}

regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_METADATA ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = 50
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = 25
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = 25
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ] = 5
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ] = 50
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD ] = 55
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = 25
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = 50
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP ] = 10
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE ] = 100
regen_file_enum_to_job_weight_lookup[ REGENERATE_FILE_DATA_JOB_PIXEL_HASH ] = 100

regen_file_enum_to_overruled_jobs = {}

regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_METADATA ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL ] = [ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_OTHER_HASHES ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD ] = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ] = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ] = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ] = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA ] = [ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ]
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE ] = []
regen_file_enum_to_overruled_jobs[ REGENERATE_FILE_DATA_JOB_PIXEL_HASH ] = []

ALL_REGEN_JOBS_IN_PREFERRED_ORDER = [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE, REGENERATE_FILE_DATA_JOB_FILE_METADATA, REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL, REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL, REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA, REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP, REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS, REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP, REGENERATE_FILE_DATA_JOB_OTHER_HASHES, REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE, REGENERATE_FILE_DATA_JOB_PIXEL_HASH, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES ]

def GetAllFilePaths( raw_paths, do_human_sort = True ):
    
    file_paths = []
    
    paths_to_process = list( raw_paths )
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if HG.started_shutdown:
                
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
        
        self._new_physical_file_deletes = threading.Event()
        
        self._bad_error_occurred = False
        self._missing_locations = set()
        
        self._Reinit()
        
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
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
            
            HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
            
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
                
                correct_rows.append( ( prefix, correct_location ) )
                
                fixes_counter[ ( missing_location, correct_location ) ] += 1
                
            else:
                
                some_are_unhealable = True
                
            
        
        if len( correct_rows ) > 0 and some_are_unhealable:
            
            message = 'Hydrus found multiple missing locations in your file storage. Some of these locations seemed to be fixable, others did not. The client will now inform you about both problems.'
            
            self._controller.SafeShowCriticalMessage( 'Multiple file location problems.', message )
            
        
        if len( correct_rows ) > 0:
            
            summaries = sorted( ( '{} moved from {} to {}'.format( HydrusData.ToHumanInt( count ), missing_location, correct_location ) for ( ( missing_location, correct_location ), count ) in fixes_counter.items() ) )
            
            summary_message = 'Some client file folders were missing, but they seem to be in other known locations! The folders are:'
            summary_message += os.linesep * 2
            summary_message += os.linesep.join( summaries )
            summary_message += os.linesep * 2
            summary_message += 'Assuming you did this on purpose, Hydrus is ready to update its internal knowledge to reflect these new mappings as soon as this dialog closes. If you know these proposed fixes are incorrect, terminate the program now.'
            
            HydrusData.Print( summary_message )
            
            self._controller.SafeShowCriticalMessage( 'About to auto-heal client file folders.', summary_message )
            
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
        
        bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
        
        ( clip_rect, target_resolution ) = HydrusImageHandling.GetThumbnailResolutionAndClipRegion( ( width, height ), bounding_dimensions, thumbnail_scale_type )
        
        percentage_in = self._controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
        
        try:
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( file_path, target_resolution, mime, duration, num_frames, clip_rect = clip_rect, percentage_in = percentage_in )
            
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
                
                filenames = list( os.listdir( dir ) )
                
                for filename in filenames:
                    
                    yield os.path.join( dir, filename )
                    
                
            
        
    
    def _IterateAllThumbnailPaths( self ):
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if prefix.startswith( 't' ):
                
                dir = os.path.join( location, prefix )
                
                filenames = list( os.listdir( dir ) )
                
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
                
                self._controller.SafeShowCriticalMessage( 'unable to create file structure', text )
                
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
                
                missing_locations = sorted( missing_dict.keys() )
                
                missing_string = ''
                
                for missing_location in missing_locations:
                    
                    missing_prefixes = sorted( missing_dict[ missing_location ] )
                    
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
                    
                    self._controller.SafeShowCriticalMessage( 'missing locations', text )
                    
                    HydrusData.DebugPrint( 'Missing locations follow:' )
                    HydrusData.DebugPrint( missing_string )
                    
                else:
                    
                    text = 'When initialising the client files manager, these file locations did not exist:'
                    text += os.linesep * 2
                    text += missing_string
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    self._controller.SafeShowCriticalMessage( 'missing locations', text )
                    
                
            
        
    
    def _ReinitMissingLocations( self ):
        
        self._missing_locations = set()
        
        for ( prefix, location ) in self._prefixes_to_locations.items():
            
            if os.path.exists( location ):
                
                if os.path.exists( os.path.join( location, prefix ) ):
                    
                    continue
                    
                
            
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
            
        
        HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
        
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
            
            job_key.SetStatusTitle( 'clearing orphans' )
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
                
                for ( i, path ) in enumerate( orphan_paths ):
                    
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
                    
                
            
        
    
    def DoDeferredPhysicalDeletes( self ):
        
        num_files_deleted = 0
        num_thumbnails_deleted = 0
        
        pauser = HydrusData.BigJobPauser()
        
        while not HG.started_shutdown:
            
            with self._rwlock.write:
                
                ( file_hash, thumbnail_hash ) = self._controller.Read( 'deferred_physical_delete' )
                
                if file_hash is None and thumbnail_hash is None:
                    
                    break
                    
                
                if file_hash is not None:
                    
                    try:
                        
                        ( path, mime ) = self._LookForFilePath( file_hash )
                        
                        ClientPaths.DeletePath( path )
                        
                        num_files_deleted += 1
                        
                    except HydrusExceptions.FileMissingException:
                        
                        pass
                        
                    
                
                if thumbnail_hash is not None:
                    
                    path = self._GenerateExpectedThumbnailPath( thumbnail_hash )
                    
                    if os.path.exists( path ):
                        
                        ClientPaths.DeletePath( path, always_delete_fully = True )
                        
                        num_thumbnails_deleted += 1
                        
                    
                
                self._controller.WriteSynchronous( 'clear_deferred_physical_delete', file_hash = file_hash, thumbnail_hash = thumbnail_hash )
                
                if num_files_deleted % 10 == 0 or num_thumbnails_deleted % 10 == 0:
                    
                    self._controller.pub( 'notify_new_physical_file_delete_numbers' )
                    
                
            
            pauser.Pause()
            
        
        if num_files_deleted > 0 or num_thumbnails_deleted > 0:
            
            self._controller.pub( 'notify_new_physical_file_delete_numbers' )
            
            HydrusData.Print( 'Physically deleted {} files and {} thumbnails from file storage.'.format( HydrusData.ToHumanInt( num_files_deleted ), HydrusData.ToHumanInt( num_files_deleted ) ) )
            
        
    
    def GetCurrentFileLocations( self ):
        
        with self._rwlock.read:
            
            locations = set()
            
            for ( prefix, location ) in self._prefixes_to_locations.items():
                
                if prefix.startswith( 'f' ):
                    
                    locations.add( location )
                    
                
            
            return locations
            
        
    
    def GetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        with self._rwlock.read:
            
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
            
        
    
    def GetMissing( self ):
        
        return self._missing_locations
        
    
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
        
    
    def NotifyNewPhysicalFileDeletes( self ):
        
        self._new_physical_file_deletes.set()
        
    
    def Rebalance( self, job_key ):
        
        try:
            
            if self._bad_error_occurred:
                
                QW.QMessageBox.warning( None, 'Warning', 'A serious file error has previously occurred during this session, so further file moving will not be reattempted. Please restart the client before trying again.' )
                
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
                    self._controller.WriteSynchronous( 'relocate_client_files', prefix, overweight_location, underweight_location )
                    
                    self._Reinit()
                    
                    rebalance_tuple = self._GetRebalanceTuple()
                    
                    time.sleep( 0.01 )
                    
                
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
                    
                    time.sleep( 0.01 )
                    
                
            
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
            thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
            
            ( clip_rect, ( expected_width, expected_height ) ) = HydrusImageHandling.GetThumbnailResolutionAndClipRegion( ( media_width, media_height ), bounding_dimensions, thumbnail_scale_type )
            
            if current_width != expected_width or current_height != expected_height:
                
                do_it = True
                
            
        except:
            
            do_it = True
            
        
        if do_it:
            
            self.RegenerateThumbnail( media )
            
        
        return do_it
        
    
    def shutdown( self ):
        
        self._new_physical_file_deletes.set()
        
    
class FilesMaintenanceManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._pubbed_message_about_bad_file_record_delete = False
        self._pubbed_message_about_invalid_file_export = False
        
        self._work_tracker = HydrusNetworking.BandwidthTracker()
        
        self._idle_work_rules = HydrusNetworking.BandwidthRules()
        self._active_work_rules = HydrusNetworking.BandwidthRules()
        
        self._ReInitialiseWorkRules()
        
        self._maintenance_lock = threading.Lock()
        self._lock = threading.Lock()
        
        self._wake_background_event = threading.Event()
        self._reset_background_event = threading.Event()
        self._shutdown = False
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        
    
    def _AbleToDoBackgroundMaintenance( self ):
        
        HG.client_controller.WaitUntilViewFree()
        
        if HG.client_controller.CurrentlyIdle():
            
            if not self._controller.new_options.GetBoolean( 'file_maintenance_during_idle' ):
                
                return False
                
            
            if not self._controller.GoodTimeToStartBackgroundWork():
                
                return False
                
            
            return self._idle_work_rules.CanStartRequest( self._work_tracker )
            
        else:
            
            if not self._controller.new_options.GetBoolean( 'file_maintenance_during_active' ):
                
                return False
                
            
            return self._active_work_rules.CanStartRequest( self._work_tracker )
            
        
    
    def _CanRegenThumbForMediaResult( self, media_result ):
        
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return False
            
        
        ( width, height ) = media_result.GetResolution()
        
        if width is None or height is None:
            
            # this guy is probably pending a metadata regen but the user forced thumbnail regen now
            # we'll wait for metadata regen to notice the new dimensions and schedule this job again
            
            return False
            
        
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
            
        
        if not file_is_missing and job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ):
            
            actual_hash = HydrusFileHandling.GetHashFromPath( path )
            
            if hash != actual_hash:
                
                file_is_invalid = True
                
                HydrusData.DebugPrint( 'Invalid file: {} actually had hash {}!'.format( hash.hex(), actual_hash.hex() ) )
                
            
        
        file_was_bad = file_is_missing or file_is_invalid
        
        if file_was_bad:
            
            urls = media_result.GetLocationsManager().GetURLs()
            
            if len( urls ) > 0:
                
                HydrusPaths.MakeSureDirectoryExists( error_dir )
                
                with open( os.path.join( error_dir, '{}.urls.txt'.format( hash.hex() ) ), 'w', encoding = 'utf-8' ) as f:
                    
                    for url in urls:
                        
                        f.write( url )
                        f.write( os.linesep )
                        
                    
                
                with open( os.path.join( error_dir, 'all_urls.txt' ), 'a', encoding = 'utf-8' ) as f:
                    
                    for url in urls:
                        
                        f.write( url )
                        f.write( os.linesep )
                        
                    
                
            
            useful_urls = []
            
            for url in urls:
                
                add_it = False
                
                try:
                    
                    url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None:
                    
                    add_it = True
                    
                else:
                    
                    if url_class.GetURLType() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                        
                        add_it = True
                        
                    
                
                if add_it:
                    
                    useful_urls.append( url )
                    
                
            
            if job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ):
                
                try_redownload = len( useful_urls ) > 0
                delete_record = not try_redownload
                
            else:
                
                try_redownload = job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ) and len( useful_urls ) > 0
                delete_record = job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                
            
            do_export = file_is_invalid and ( job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ) or ( job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL and try_redownload ) )
            
            if do_export:
                
                HydrusPaths.MakeSureDirectoryExists( error_dir )
                
                dest_path = os.path.join( error_dir, os.path.basename( path ) )
                
                HydrusPaths.MergeFile( path, dest_path )
                
                if not self._pubbed_message_about_invalid_file_export:
                    
                    self._pubbed_message_about_invalid_file_export = True
                    
                    message = 'During file maintenance, a file was found to be invalid. It and any known URLs have been moved to "{}".'.format( error_dir )
                    message += os.linesep * 2
                    message += 'More files may be invalid, but this message will not appear again during this boot.'
                    
                    HydrusData.ShowText( message )
                    
                
            
            if try_redownload:
                
                def qt_add_url( url ):
                    
                    if QP.isValid( HG.client_controller.gui ):
                        
                        HG.client_controller.gui.ImportURL( url, 'missing files redownloader' )
                        
                    
                
                for url in useful_urls:
                    
                    QP.CallAfter( qt_add_url, url )
                    
                
            
            if delete_record:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'Record deleted during File Integrity check.' )
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
                
                self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', ( hash, ) ) )
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
                
                self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
                if not self._pubbed_message_about_bad_file_record_delete:
                    
                    self._pubbed_message_about_bad_file_record_delete = True
                    
                    message = 'During file maintenance, a file was found to be missing or invalid. Its file record has been removed from the database without leaving a deletion record (so it can be easily reimported). Any known URLs for the file have been written to "{}".'.format( error_dir )
                    message += os.linesep * 2
                    message += 'This may happen to more files in the near future, but this message will not appear again during this boot.'
                    
                    HydrusData.ShowText( message )
                    
                
            
        
        return file_was_bad
        
    
    def _CheckSimilarFilesMembership( self, media_result ):
        
        mime = media_result.GetMime()
        
        return mime in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH
        
    
    def _ClearJobs( self, hashes, job_type ):
        
        if len( hashes ) > 0:
            
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
            
            HydrusPaths.TryToGiveFileNicePermissionBits( path )
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _HasICCProfile( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_ICC_PROFILE:
            
            return False
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            try:
                
                pil_image = HydrusImageHandling.RawOpenPILImage( path )
                
            except:
                
                return None
                
            
            has_icc_profile = HydrusImageHandling.HasICCProfile( pil_image )
            
            additional_data = has_icc_profile
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        original_mime = media_result.GetMime()
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, original_mime )
            
            ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = HydrusFileHandling.GetFileInfo( path, ok_to_look_for_hydrus_updates = True )
            
            additional_data = ( size, mime, width, height, duration, num_frames, has_audio, num_words )
            
            if mime != original_mime:
                
                needed_to_dupe_the_file = self._controller.client_files_manager.ChangeFileExt( hash, original_mime, mime )
                
                if needed_to_dupe_the_file:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusData.GetNow() + ( 7 * 86400 ) )
                    
                
            
            return additional_data
            
        except HydrusExceptions.UnsupportedFileException:
            
            self._CheckFileIntegrity( media_result, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD )
            
            return None
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileModifiedTimestamp( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime in HC.HYDRUS_UPDATE_FILES:
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            file_modified_timestamp = HydrusFileHandling.GetFileModifiedTimestamp( path )
            
            additional_data = file_modified_timestamp
            
            return additional_data
            
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
            
        
    
    def _RegenFileThumbnailForce( self, media_result ):
        
        good_to_go = self._CanRegenThumbForMediaResult( media_result )
        
        if not good_to_go:
            
            return
            
        
        try:
            
            self._controller.client_files_manager.RegenerateThumbnail( media_result )
            
        except HydrusExceptions.FileMissingException:
            
            pass
            
        
    
    def _RegenFileThumbnailRefit( self, media_result ):
        
        good_to_go = self._CanRegenThumbForMediaResult( media_result )
        
        if not good_to_go:
            
            return
            
        
        try:
            
            was_regenerated = self._controller.client_files_manager.RegenerateThumbnailIfWrongSize( media_result )
            
            return was_regenerated
            
        except HydrusExceptions.FileMissingException:
            
            pass
            
        
    
    def _RegenPixelHash( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH:
            
            return None
            
        
        duration = media_result.GetDuration()
        
        if duration is not None:
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            try:
                
                pixel_hash = HydrusImageHandling.GetImagePixelHash( path, mime )
                
            except:
                
                return None
                
            
            additional_data = pixel_hash
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenSimilarFilesMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
            
            self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP )
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
        perceptual_hashes = ClientImageHandling.GenerateShapePerceptualHashes( path, mime )
        
        return perceptual_hashes
        
    
    def _ReInitialiseWorkRules( self ):
        
        file_maintenance_idle_throttle_files = self._controller.new_options.GetInteger( 'file_maintenance_idle_throttle_files' )
        file_maintenance_idle_throttle_time_delta = self._controller.new_options.GetInteger( 'file_maintenance_idle_throttle_time_delta' )
        
        self._idle_work_rules = HydrusNetworking.BandwidthRules()
        
        self._idle_work_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, file_maintenance_idle_throttle_time_delta, file_maintenance_idle_throttle_files * NORMALISED_BIG_JOB_WEIGHT )
        
        file_maintenance_active_throttle_files = self._controller.new_options.GetInteger( 'file_maintenance_active_throttle_files' )
        file_maintenance_active_throttle_time_delta = self._controller.new_options.GetInteger( 'file_maintenance_active_throttle_time_delta' )
        
        self._active_work_rules = HydrusNetworking.BandwidthRules()
        
        self._active_work_rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, file_maintenance_active_throttle_time_delta, file_maintenance_active_throttle_files * NORMALISED_BIG_JOB_WEIGHT )
        
    
    def _RunJob( self, media_results, job_type, job_key, job_done_hook = None ):
        
        next_gc_collect = HydrusData.GetNow() + 10
        
        try:
            
            big_pauser = HydrusData.BigJobPauser( wait_time = 0.8 )
            
            last_time_jobs_were_cleared = HydrusData.GetNow()
            cleared_jobs = []
            
            num_to_do = len( media_results )
            
            if HG.file_report_mode:
                
                HydrusData.ShowText( 'file maintenance: {} for {} files'.format( regen_file_enum_to_str_lookup[ job_type ], HydrusData.ToHumanInt( num_to_do ) ) )
                
            
            for ( i, media_result ) in enumerate( media_results ):
                
                big_pauser.Pause()
                
                hash = media_result.GetHash()
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                if job_done_hook is not None:
                    
                    job_done_hook( job_type )
                    
                
                additional_data = None
                
                try:
                    
                    if job_type == REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                        
                        additional_data = self._RegenFileMetadata( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP:
                        
                        additional_data = self._RegenFileModifiedTimestamp( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                        
                        additional_data = self._RegenFileOtherHashes( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE:
                        
                        additional_data = self._HasICCProfile( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_PIXEL_HASH:
                        
                        additional_data = self._RegenPixelHash( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                        
                        self._RegenFileThumbnailForce( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                        
                        if not job_key.HasVariable( 'num_thumb_refits' ):
                            
                            job_key.SetVariable( 'num_thumb_refits', 0 ) 
                            
                        
                        num_thumb_refits = job_key.GetIfHasVariable( 'num_thumb_refits' )
                        
                        was_regenerated = self._RegenFileThumbnailRefit( media_result )
                        
                        if was_regenerated:
                            
                            num_thumb_refits += 1
                            
                            job_key.SetVariable( 'num_thumb_refits', num_thumb_refits )
                            
                        
                        job_key.SetVariable( 'popup_text_2', 'thumbs needing regen: {}'.format( HydrusData.ToHumanInt( num_thumb_refits ) ) )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES:
                        
                        self._DeleteNeighbourDupes( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                        
                        additional_data = self._CheckSimilarFilesMembership( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                        
                        additional_data = self._RegenSimilarFilesMetadata( media_result )
                        
                    elif job_type == REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS:
                        
                        self._FixFilePermissions( media_result )
                        
                    elif job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ):
                        
                        if not job_key.HasVariable( 'num_bad_files' ):
                            
                            job_key.SetVariable( 'num_bad_files', 0 ) 
                            
                        
                        num_bad_files = job_key.GetIfHasVariable( 'num_bad_files' )
                        
                        file_was_bad = self._CheckFileIntegrity( media_result, job_type )
                        
                        if file_was_bad:
                            
                            num_bad_files += 1
                            
                            job_key.SetVariable( 'num_bad_files', num_bad_files ) 
                            
                        
                        job_key.SetVariable( 'popup_text_2', 'missing or invalid files: {}'.format( HydrusData.ToHumanInt( num_bad_files ) ) )
                        
                    
                except HydrusExceptions.ShutdownException:
                    
                    # no worries
                    
                    pass
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    message = 'There was a problem performing maintenance task "{}" on file {}! The job will not be reattempted. A full traceback of this error should be written to the log.'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() )
                    message += os.linesep * 2
                    message += str( e )
                    
                    HydrusData.ShowText( message )
                    
                finally:
                    
                    self._work_tracker.ReportRequestUsed( num_requests = regen_file_enum_to_job_weight_lookup[ job_type ] )
                    
                    cleared_jobs.append( ( hash, job_type, additional_data ) )
                    
                
                if HydrusData.TimeHasPassed( last_time_jobs_were_cleared + 10 ) or len( cleared_jobs ) > 256:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_clear_jobs', cleared_jobs )
                    
                    cleared_jobs = []
                    
                
            
        finally:
            
            if len( cleared_jobs ) > 0:
                
                self._controller.Write( 'file_maintenance_clear_jobs', cleared_jobs )
                
            
        
    
    def CancelJobs( self, job_type ):
        
        with self._lock:
            
            self._controller.WriteSynchronous( 'file_maintenance_cancel_jobs', job_type )
            
            self._reset_background_event.set()
            
        
    
    def ClearJobs( self, hashes, job_type ):
        
        with self._lock:
            
            self._ClearJobs( hashes, job_type )
            
            self._reset_background_event.set()
            
        
    
    def ForceMaintenance( self, mandated_job_types = None ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_types_to_counts = HG.client_controller.Read( 'file_maintenance_get_job_counts' )
        
        # in a dict so the hook has scope to alter it
        vr_status = {}
        
        vr_status[ 'num_jobs_done' ] = 0
        total_num_jobs_to_do = sum( ( value for ( key, value ) in job_types_to_counts.items() if mandated_job_types is None or key in mandated_job_types ) )
        
        def job_done_hook( job_type ):
            
            vr_status[ 'num_jobs_done' ] += 1
            
            num_jobs_done = vr_status[ 'num_jobs_done' ]
            
            status_text = '{} - {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do ), regen_file_enum_to_str_lookup[ job_type ] )
            
            job_key.SetVariable( 'popup_text_1', status_text )
            
            job_key.SetVariable( 'popup_gauge_1', ( num_jobs_done, total_num_jobs_to_do ) )
            
        
        self._reset_background_event.set()
        
        job_key.SetStatusTitle( 'regenerating file data' )
        
        message_pubbed = False
        work_done = False
        
        with self._maintenance_lock:
            
            try:
                
                while True:
                    
                    job = self._controller.Read( 'file_maintenance_get_job', mandated_job_types )
                    
                    if job is None:
                        
                        break
                        
                    
                    work_done = True
                    
                    if not message_pubbed:
                        
                        self._controller.pub( 'message', job_key )
                        
                        message_pubbed = True
                        
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                    ( hashes, job_type ) = job
                    
                    media_results = self._controller.Read( 'media_results', hashes )
                    
                    hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                    
                    missing_hashes = [ hash for hash in hashes if hash not in hashes_to_media_results ]
                    
                    self._ClearJobs( missing_hashes, job_type )
                    
                    with self._lock:
                        
                        self._RunJob( media_results, job_type, job_key, job_done_hook = job_done_hook )
                        
                    
                    time.sleep( 0.0001 )
                    
                
            finally:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
                job_key.Finish()
                
                job_key.Delete( 5 )
                
                if not work_done:
                    
                    HydrusData.ShowText( 'No file maintenance due!' )
                    
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def MainLoopBackgroundWork( self ):
        
        def check_shutdown():
            
            if HydrusThreading.IsThreadShuttingDown() or self._shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        def wait_on_maintenance():
            
            while True:
                
                check_shutdown()
                
                if self._AbleToDoBackgroundMaintenance() or self._reset_background_event.is_set():
                    
                    break
                    
                
                time.sleep( 1 )
                
            
        
        def should_reset():
            
            if self._reset_background_event.is_set():
                
                self._reset_background_event.clear()
                
                return True
                
            else:
                
                return False
                
            
        
        try:
            
            time_to_start = HydrusData.GetNow() + 15
            
            while not HydrusData.TimeHasPassed( time_to_start ):
                
                check_shutdown()
                
                time.sleep( 1 )
                
            
            while True:
                
                check_shutdown()
                
                did_work = False
                
                with self._maintenance_lock:
                    
                    job = self._controller.Read( 'file_maintenance_get_job' )
                    
                    if job is not None:
                        
                        did_work = True
                        
                        job_key = ClientThreading.JobKey()
                        
                        i = 0
                        
                        try:
                            
                            ( hashes, job_type ) = job
                            
                            media_results = self._controller.Read( 'media_results', hashes )
                            
                            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                            
                            missing_hashes = [ hash for hash in hashes if hash not in hashes_to_media_results ]
                            
                            self._ClearJobs( missing_hashes, job_type )
                            
                            for media_result in media_results:
                                
                                wait_on_maintenance()
                                
                                if should_reset():
                                    
                                    break
                                    
                                
                                with self._lock:
                                    
                                    self._RunJob( ( media_result, ), job_type, job_key )
                                    
                                
                                time.sleep( 0.0001 )
                                
                                i += 1
                                
                                if i % 100 == 0:
                                    
                                    self._controller.pub( 'notify_files_maintenance_done' )
                                    
                                
                            
                        finally:
                            
                            self._controller.pub( 'notify_files_maintenance_done' )
                            
                        
                    
                
                if not did_work:
                    
                    self._wake_background_event.wait( 600 )
                    
                    self._wake_background_event.clear()
                    
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        
    
    def NotifyNewOptions( self ):
        
        with self._lock:
            
            self._ReInitialiseWorkRules()
            
        
    
    def RunJobImmediately( self, media_results, job_type, pub_job_key = True ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        total_num_jobs_to_do = len( media_results )
        
        # in a dict so the hook has scope to alter it
        vr_status = {}
        
        vr_status[ 'num_jobs_done' ] = 0
        
        def job_done_hook( job_type ):
            
            vr_status[ 'num_jobs_done' ] += 1
            
            num_jobs_done = vr_status[ 'num_jobs_done' ]
            
            status_text = '{} - {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do ), regen_file_enum_to_str_lookup[ job_type ] )
            
            job_key.SetVariable( 'popup_text_1', status_text )
            
            job_key.SetVariable( 'popup_gauge_1', ( num_jobs_done, total_num_jobs_to_do ) )
            
        
        job_key.SetStatusTitle( 'regenerating file data' )
        
        if pub_job_key:
            
            self._controller.pub( 'message', job_key )
            
        
        self._reset_background_event.set()
        
        with self._lock:
            
            try:
                
                self._RunJob( media_results, job_type, job_key, job_done_hook = job_done_hook )
                
            finally:
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
                job_key.Finish()
                
                job_key.Delete( 5 )
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def ScheduleJob( self, hashes, job_type, time_can_start = 0 ):
        
        with self._lock:
            
            self._controller.Write( 'file_maintenance_add_jobs_hashes', hashes, job_type, time_can_start )
            
            self._wake_background_event.set()
            
        
    
    def ScheduleJobHashIds( self, hash_ids, job_type, time_can_start = 0 ):
        
        with self._lock:
            
            self._controller.Write( 'file_maintenance_add_jobs', hash_ids, job_type, time_can_start )
            
            self._wake_background_event.set()
            
        
    
    def Shutdown( self ):
        
        self._shutdown = True
        
        self._wake_background_event.set()
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoopBackgroundWork )
        
    
