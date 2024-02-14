import collections
import os
import random
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files.images import HydrusBlurhash
from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientFilesPhysical
from hydrus.client import ClientImageHandling
from hydrus.client import ClientPaths
from hydrus.client import ClientSVGHandling # important to keep this in, despite not being used, since there's initialisation stuff in here
from hydrus.client import ClientPDFHandling # important to keep this in, despite not being used, since there's initialisation stuff in here
from hydrus.client import ClientThreading
from hydrus.client import ClientVideoHandling
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

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
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY = 18
REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA = 19
REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF = 20
REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD = 21
REGENERATE_FILE_DATA_JOB_BLURHASH = 22
REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY = 23

regen_file_enum_to_str_lookup = {
    REGENERATE_FILE_DATA_JOB_FILE_METADATA : 'regenerate file metadata',
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL : 'regenerate thumbnail',
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL : 'regenerate thumbnail if incorrect size',
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES : 'regenerate non-standard hashes',
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES : 'delete duplicate neighbours with incorrect file extension',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD : 'if file is missing, remove record (leave no delete record)',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD : 'if file is missing, remove record (leave a delete record)',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL : 'if file is missing, then if has URL try to redownload',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD : 'if file is missing, then if has URL try to redownload, else remove record',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY : 'if file is missing, note it in log',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD : 'if file is missing/incorrect, move file out and remove record',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL : 'if file is missing/incorrect, then move file out, and if has URL try to redownload',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD : 'if file is missing/incorrect, then move file out, and if has URL try to redownload, else remove record',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE : 'if file is incorrect, move file out',
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS : 'fix file read/write permissions',
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP : 'check for membership in the similar files search system',
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA : 'regenerate perceptual hashes',
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP : 'regenerate file modified time',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY: 'determine if the file has transparency',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF : 'determine if the file has EXIF metadata',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : 'determine if the file has non-EXIF human-readable embedded metadata',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : 'determine if the file has an icc profile',
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : 'regenerate pixel hashes',
    REGENERATE_FILE_DATA_JOB_BLURHASH: 'regenerate blurhash'
}

regen_file_enum_to_description_lookup = {
    REGENERATE_FILE_DATA_JOB_FILE_METADATA : 'This regenerates file metadata like resolution and duration, or even filetype (such as mkv->webm), which may have been misparsed in a previous version.',
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL : 'This forces a complete regeneration of the thumbnail from the source file.',
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL : 'This looks for the existing thumbnail, and if it is not the correct resolution or is missing, will regenerate a new one for the source file.',
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES : 'This regenerates hydrus\'s store of md5, sha1, and sha512 supplementary hashes, which it can use for various external (usually website) lookups.',
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES : 'Sometimes, a file metadata regeneration will mean a new filetype and thus a new file extension. If the existing, incorrectly named file is in use, it must be copied rather than renamed, and so there is a spare duplicate left over after the operation. This jobs cleans up the duplicate at a later time.',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD : '''This checks to see if the file is present in the file system as expected. Use this if you have lost a number of files from your file structure, do not think you can recover them, and need hydrus to re-sync with what it actually has.

Missing files will have their internal file record in the database removed. This is just like a file delete except it does not leave a deletion record, so if you ever find the file again in future, you can import it again easily.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD : '''This checks to see if the file is present in the file system as expected. Use this if you have manually deleted a number of files from your file structure, do not want to get them again, and need hydrus to re-sync with what it actually has. Another example of this situation is restoring an old backed-up database to a newer client_files structure--to catch the database up, you want to teach it that any files missing in the newer structure should be deleted, with a record.

Missing files will have their internal file record deleted just like a normal file delete. Normal imports that see these files again in future will ignore them as 'previously deleted'.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL : '''This checks to see if the file is present in the file system as expected. If it is not, and it has known post/file URLs, the URLs will be automatically added to a new URL downloader.'

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD : '''THIS IS THE EASY AND QUICK ONE-SHOT WAY TO REPAIR A DATABASE WITH MISSING FILES.

This checks to see if the file is present in the file system as expected. If it is not, and it has known post/file URLs, the URLs will be automatically added to a new URL downloader.

Missing files with no URLs will have their internal file record in the database removed. This is just like a file delete except it does not leave a deletion record, so if you ever find the file again in future, you can import it again easily.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY : 'This checks to see if the file is present in the file system as expected. If it is not, it records the file\'s hash, tags, and URLs to your database directory, just like the other "missing file" jobs, but makes no other action.',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD : '''This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary.

Missing/Incorrect files will have their internal file record in the database removed. This is just like a file delete except it does not leave a deletion record, so if you ever find the file again in future, you can import it again easily.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/Incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL : '''This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary. If the file is incorrect _and_ has known post/file URLs, the URLs will be automatically added to a new URL downloader.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/Incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD : '''This does the same check as the \'file is missing\' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary. If the file is incorrect _and_ has known post/file URLs, the URLs will be automatically added to a new URL downloader.

Missing/Incorrect files with no URLs will have their internal file record in the database removed. This is just like a file delete except it does not leave a deletion record, so if you ever find the file again in future, you can import it again easily.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/Incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE : 'If the file is where it is expected, this ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect, it will be exported to your database directory along with its known URLs. The client\'s file record will not be deleted. This is useful if you have a valid backup and need to clear out invalid files from your live db so you can fill in gaps from your backup with a program like FreeFileSync.',
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS : 'This ensures that files in the file system are readable and writeable. For Linux/macOS users, it specifically sets 644. If you wish to run this job on Linux/macOS, ensure you are first the file owner of all your files.',
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP : 'This checks to see if files should be in the similar files system, and if they are falsely in or falsely out, it will remove their record or queue them up for a search as appropriate. It is useful to repair database damage.',
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA : 'This forces a regeneration of the file\'s similar-files \'phashes\'. It is not useful unless you know there is missing data to repair.',
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP : 'This rechecks the file\'s modified timestamp and saves it to the database.',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY : 'This loads the file to see if it has an alpha channel with useful data (completely opaque/transparency alpha channels are discarded). Only works for images and animated gif.',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF : 'This loads the file to see if it has EXIF metadata, which can be shown in the media viewer and searched with "system:image has exif".',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : 'This loads the file to see if it has non-EXIF human-readable metadata, which can be shown in the media viewer and searched with "system:image has human-readable embedded metadata".',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : 'This loads the file to see if it has an ICC profile, which is used in "system:has icc profile" search.',
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : 'This generates a fast unique identifier for the pixels in a still image, which is used in duplicate pixel searches.',
    REGENERATE_FILE_DATA_JOB_BLURHASH: 'This generates a very small version of the file\'s thumbnail that can be used as a placeholder while the thumbnail loads.'
}

NORMALISED_BIG_JOB_WEIGHT = 100

regen_file_enum_to_job_weight_lookup = {
    REGENERATE_FILE_DATA_JOB_FILE_METADATA : 100,
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL : 50,
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL : 25,
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES : 100,
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES : 25,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD : 5,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD : 5,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL : 25,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD : 30,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY : 5,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD : 100,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL : 100,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD : 100,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE : 100,
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS : 25,
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP : 1,
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA : 100,
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP : 10,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY : 25,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF : 25,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : 25,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : 25,
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : 100,
    REGENERATE_FILE_DATA_JOB_BLURHASH: 15
}

regen_file_enum_to_overruled_jobs = {
    REGENERATE_FILE_DATA_JOB_FILE_METADATA : [],
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL : [ REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL ],
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL : [],
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES : [],
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES : [],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY : [],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD : [ REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD ],
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE : [],
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS : [],
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP : [],
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA : [ REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP ],
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP : [],
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY : [],
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF : [],
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : [],
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : [],
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : [],
    REGENERATE_FILE_DATA_JOB_BLURHASH: []
}

ALL_REGEN_JOBS_IN_RUN_ORDER = [
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY,
    REGENERATE_FILE_DATA_JOB_FILE_METADATA,
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL,
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL,
    REGENERATE_FILE_DATA_JOB_BLURHASH,
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA,
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP,
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS,
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP,
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE,
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH,
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES
]

ALL_REGEN_JOBS_IN_HUMAN_ORDER = [
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE,
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY,
    REGENERATE_FILE_DATA_JOB_FILE_METADATA,
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL,
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL,
    REGENERATE_FILE_DATA_JOB_BLURHASH,
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH,
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA,
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP,
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES,
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA,
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE,
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS,
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES
]

def GetAllFilePaths( raw_paths, do_human_sort = True, clear_out_sidecars = True ):
    
    file_paths = []
    
    paths_to_process = list( raw_paths )
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if HG.started_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
            if os.path.isdir( path ):
                
                try:
                    
                    # on Windows, some network file paths return True on isdir(). maybe something to do with path length or number of subdirs
                    path_listdir = os.listdir( path )
                    
                except NotADirectoryError:
                    
                    file_paths.append( path )
                    
                    continue
                    
                
                subpaths = [ os.path.join( path, filename ) for filename in path_listdir ]
                
                next_paths_to_process.extend( subpaths )
                
            else:
                
                file_paths.append( path )
                
            
        
        paths_to_process = next_paths_to_process
        
    
    if do_human_sort:
        
        HydrusData.HumanTextSort( file_paths )
        
    
    num_files_with_sidecars = len( file_paths )
    
    if clear_out_sidecars:
        
        exts = [ '.txt', '.json', '.xml' ]
        
        def has_sidecar_ext( p ):
            
            if True in ( p.endswith( ext ) for ext in exts ):
                
                return True
                
            
            return False
            
        
        def get_base_prefix_component( p ):
            
            base_prefix = os.path.basename( p )
            
            if '.' in base_prefix:
                
                base_prefix = base_prefix.split( '.', 1 )[0]
                
            
            return base_prefix
            
        
        # let's get all the 'Image123' in our 'path/to/Image123.jpg' list
        all_non_ext_prefix_components = { get_base_prefix_component( file_path ) for file_path in file_paths if not has_sidecar_ext( file_path ) }
        
        def looks_like_a_sidecar( p ):
            
            # if we have Image123.txt, that's probably a sidecar!
            return has_sidecar_ext( p ) and get_base_prefix_component( p ) in all_non_ext_prefix_components
            
        
        file_paths = [ path for path in file_paths if not looks_like_a_sidecar( path ) ]
        
    
    num_sidecars = num_files_with_sidecars - len( file_paths )
    
    return ( file_paths, num_sidecars )
    

class ClientFilesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._file_storage_rwlock = ClientThreading.FileRWLock()
        
        self._prefixes_to_client_files_subfolders = collections.defaultdict( list )
        self._smallest_prefix = 2
        self._largest_prefix = 2
        
        self._physical_file_delete_wait = threading.Event()
        
        self._locations_to_free_space = {}
        
        self._bad_error_occurred = False
        self._missing_subfolders = set()
        
        self._Reinit()
        
        self._controller.sub( self, 'Reinit', 'new_ideal_client_files_locations' )
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def _AddFile( self, hash, mime, source_path ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode or HG.file_import_report_mode:
            
            HydrusData.ShowText( 'Adding file to client file structure: from {} to {}'.format( source_path, dest_path ) )
            
        
        file_size = os.path.getsize( source_path )
        
        dest_free_space = self._GetFileStorageFreeSpace( hash )
        
        if dest_free_space < 100 * 1048576 or dest_free_space < file_size:
            
            message = 'The disk for path "{}" is almost full and cannot take the file "{}", which is {}! Shut the client down now and fix this!'.format( dest_path, hash.hex(), HydrusData.ToHumanBytes( file_size ) )
            
            HydrusData.ShowText( message )
            
            self._HandleCriticalDriveError()
            
            raise Exception( message )
            
        
        try:
            
            HydrusPaths.MirrorFile( source_path, dest_path )
            
        except Exception as e:
            
            message = f'Copying the file from "{source_path}" to "{dest_path}" failed! Details should be shown and other import queues should be paused. You should shut the client down now and fix this!'
            
            HydrusData.ShowText( message )
            
            self._HandleCriticalDriveError()
            
            raise Exception( message ) from e
            
        
    
    def _AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        dest_path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding thumbnail: ' + str( ( len( thumbnail_bytes ), dest_path ) ) )
            
        
        try:
            
            HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
            
            with open( dest_path, 'wb' ) as f:
                
                f.write( thumbnail_bytes )
                
            
        except Exception as e:
            
            subfolder = self._GetSubfolderForFile( hash, 't' )
            
            if not subfolder.PathExists():
                
                raise HydrusExceptions.DirectoryMissingException( f'The directory {subfolder} was not found! Reconnect the missing location or shut down the client immediately!' )
                
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file "{}" failed to write to path "{}". This event suggests that hydrus does not have permission to write to its thumbnail folder. Please check everything is ok.'.format( hash.hex(), dest_path ) )
            
        
        if not silent:
            
            self._controller.pub( 'clear_thumbnails', { hash } )
            self._controller.pub( 'new_thumbnails', { hash } )
            
        
    
    def _AttemptToHealMissingLocations( self ):
        
        # if a missing prefix folder seems to be in another location, lets update to that other location
        
        correct_rows = []
        some_are_unhealable = False
        
        fixes_counter = collections.Counter()
        
        known_base_locations = self._GetCurrentSubfolderBaseLocations()
        
        ( media_base_locations, thumbnail_override_base_location ) = self._controller.Read( 'ideal_client_files_locations' )
        
        known_base_locations.update( media_base_locations )
        
        if thumbnail_override_base_location is not None:
            
            known_base_locations.add( thumbnail_override_base_location )
            
        
        for missing_subfolder in self._missing_subfolders:
            
            missing_base_location = missing_subfolder.base_location
            prefix = missing_subfolder.prefix
            
            potential_correct_base_locations = []
            
            for known_base_location in known_base_locations:
                
                if known_base_location == missing_base_location:
                    
                    continue
                    
                
                potential_location_subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, known_base_location )
                
                if potential_location_subfolder.PathExists():
                    
                    potential_correct_base_locations.append( known_base_location )
                    
                
            
            if len( potential_correct_base_locations ) == 1:
                
                correct_base_location = potential_correct_base_locations[0]
                
                correct_subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, correct_base_location )
                
                correct_rows.append( ( missing_subfolder, correct_subfolder ) )
                
                fixes_counter[ ( missing_base_location, correct_base_location ) ] += 1
                
            else:
                
                some_are_unhealable = True
                
            
        
        if len( correct_rows ) > 0 and some_are_unhealable:
            
            message = 'Hydrus found multiple missing locations in your file storage. Some of these locations seemed to be fixable, others did not. The client will now inform you about both problems.'
            
            self._controller.BlockingSafeShowCriticalMessage( 'Multiple file location problems.', message )
            
        
        if len( correct_rows ) > 0:
            
            summaries = sorted( ( '{} folders seem to have moved from {} to {}'.format( HydrusData.ToHumanInt( count ), missing_base_location, correct_base_location ) for ( ( missing_base_location, correct_base_location ), count ) in fixes_counter.items() ) )
            
            summary_message = 'Some client file folders were missing, but they appear to be in other known locations! The folders are:'
            summary_message += os.linesep * 2
            summary_message += os.linesep.join( summaries )
            summary_message += os.linesep * 2
            summary_message += 'Assuming you did this on purpose, or hydrus recently inserted stub values after database corruption, Hydrus is ready to update its internal knowledge to reflect these new mappings as soon as this dialog closes. If you know these proposed fixes are incorrect, terminate the program now.'
            
            HydrusData.Print( summary_message )
            
            self._controller.BlockingSafeShowCriticalMessage( 'About to auto-heal client file folders.', summary_message )
            
            CG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
            
        
    
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
        
        subfolder = self._GetSubfolderForFile( hash, 'f' )
        
        hash_encoded = hash.hex()
        
        return subfolder.GetFilePath( f'{hash_encoded}{HC.mime_ext_lookup[ mime ]}' )
        
    
    def _GenerateExpectedThumbnailPath( self, hash ):
        
        self._WaitOnWakeup()
        
        subfolder = self._GetSubfolderForFile( hash, 't' )
        
        hash_encoded = hash.hex()
        
        return subfolder.GetFilePath( f'{hash_encoded}.thumbnail' )
        
    
    def _GenerateThumbnailBytes( self, file_path, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        ( width, height ) = media.GetResolution()
        duration = media.GetDurationMS()
        num_frames = media.GetNumFrames()
        
        bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
        thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
        thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
        
        target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
        
        percentage_in = self._controller.new_options.GetInteger( 'video_thumbnail_percentage_in' )
        
        try:
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( file_path, target_resolution, mime, duration, num_frames, percentage_in = percentage_in )
            
        except Exception as e:
            
            raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file for the above reason. This event could indicate hard drive corruption. Please check everything is ok.' )
            
        
        return thumbnail_bytes
        
    
    def _GetCurrentSubfolderBaseLocations( self, only_files = False ):
        
        known_base_locations = set()
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            if only_files and not prefix.startswith( 'f' ):
                
                continue
                
            
            for subfolder in subfolders:
                
                known_base_locations.add( subfolder.base_location )
                
            
        
        return known_base_locations
        
    
    def _GetFileStorageFreeSpace( self, hash: bytes ) -> int:
        
        subfolder = self._GetSubfolderForFile( hash, 'f' )
        
        base_location = subfolder.base_location
        
        if base_location in self._locations_to_free_space:
            
            ( free_space, time_fetched ) = self._locations_to_free_space[ base_location ]
            
            if free_space > 100 * ( 1024 ** 3 ):
                
                check_period = 3600
                
            elif free_space > 15 * ( 1024 ** 3 ):
                
                check_period = 600
                
            else:
                
                check_period = 60
                
            
            if HydrusTime.TimeHasPassed( time_fetched + check_period ):
                
                free_space = HydrusPaths.GetFreeSpace( base_location.path )
                
                self._locations_to_free_space[ base_location ] = ( free_space, HydrusTime.GetNow() )
                
            
        else:
            
            free_space = HydrusPaths.GetFreeSpace( base_location.path )
            
            self._locations_to_free_space[ base_location ] = ( free_space, HydrusTime.GetNow() )
            
        
        return free_space
        
    
    def _GetPossibleSubfoldersForFile( self, hash: bytes, prefix_type: str ) -> typing.List[ ClientFilesPhysical.FilesStorageSubfolder ]:
        
        hash_encoded = hash.hex()
        
        result = []
        
        for i in range( self._smallest_prefix, self._largest_prefix + 1 ):
            
            prefix = prefix_type + hash_encoded[ : i ]
            
            if prefix in self._prefixes_to_client_files_subfolders:
                
                result.extend( self._prefixes_to_client_files_subfolders[ prefix ] )
                
            
        
        return result
        
    
    def _GetAllSubfolders( self ) -> typing.List[ ClientFilesPhysical.FilesStorageSubfolder ]:
        
        result = []
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            result.extend( subfolders )
            
        
        return result
        
    
    def _GetRebalanceTuple( self ):
        
        # TODO: obviously this will change radically when we move to multiple folders for real and background migration. hacks for now
        # In general, I think this thing is going to determine the next migration destination and purge flag
        # the background file migrator will work on current purge flags and not talk to this guy until the current flags are clear 
        
        ( ideal_media_base_locations, ideal_thumbnail_override_base_location ) = self._controller.Read( 'ideal_client_files_locations' )
        
        service_info = CG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        total_ideal_weight = sum( ( base_location.ideal_weight for base_location in ideal_media_base_locations ) )
        
        smallest_subfolder_normalised_weight = 1
        largest_subfolder_normalised_weight = 0
        
        current_base_locations_to_normalised_weights = collections.Counter()
        current_base_locations_to_size_estimate = collections.Counter()
        
        file_prefixes = [ prefix for prefix in self._prefixes_to_client_files_subfolders.keys() if prefix.startswith( 'f' ) ]
        
        all_media_base_locations = set( ideal_media_base_locations )
        
        for file_prefix in file_prefixes:
            
            subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
            
            subfolder = subfolders[0]
            
            base_location = subfolder.base_location
            
            all_media_base_locations.add( base_location )
            
            normalised_weight = subfolder.GetNormalisedWeight()
            
            current_base_locations_to_normalised_weights[ base_location ] += normalised_weight
            current_base_locations_to_size_estimate[ base_location ] += normalised_weight * all_local_files_total_size
            
            if normalised_weight < smallest_subfolder_normalised_weight:
                
                smallest_subfolder_normalised_weight = normalised_weight
                
            
            if normalised_weight > largest_subfolder_normalised_weight:
                
                largest_subfolder_normalised_weight = normalised_weight
                
            
        
        smallest_subfolder_num_bytes = smallest_subfolder_normalised_weight * all_local_files_total_size
        
        #
        
        # ok so the problem here is that when a location blocks new subfolders because of max num bytes rules, the other guys have to take the slack and end up overweight
        # we want these overweight guys to nonetheless distribute their stuff according to relative weights
        # so, what we'll do is we'll play a game with a split-pot, where bust players can't get dosh from later rounds
        
        second_round_base_locations = []
        
        desperately_overweight_locations = []
        overweight_locations = []
        available_locations = []
        starving_locations = []
        
        # first round, we need to sort out who is bust
        
        total_normalised_weight_lost_in_first_round = 0
        
        for base_location in all_media_base_locations:
            
            current_num_bytes = current_base_locations_to_size_estimate[ base_location ]
            
            if not base_location.AbleToAcceptSubfolders( current_num_bytes, smallest_subfolder_num_bytes ):
                
                if base_location.max_num_bytes is None:
                    
                    total_normalised_weight_lost_in_first_round = base_location.ideal_weight / total_ideal_weight
                    
                else:
                    
                    total_normalised_weight_lost_in_first_round += base_location.max_num_bytes / all_local_files_total_size
                    
                
                if base_location.NeedsToRemoveSubfolders( current_num_bytes ):
                    
                    desperately_overweight_locations.append( base_location )
                    
                
            else:
                
                second_round_base_locations.append( base_location )
                
            
        
        random.shuffle( second_round_base_locations )
        
        # second round, let's distribute the remainder
        # I fixed some logic and it seems like everything here is now AbleToAccept, so maybe we want another quick pass on this
        # or just wait until I do the slow migration and we'll figure something out with the staticmethod on BaseLocation that just gets ideal weights
        # I also added this jank regarding / ( 1 - first_round_weight ), which makes sure we are distributing the remaining weight correctly
        
        second_round_total_ideal_weight = sum( ( base_location.ideal_weight for base_location in second_round_base_locations ) )
        
        for base_location in second_round_base_locations:
            
            current_normalised_weight = current_base_locations_to_normalised_weights[ base_location ]
            current_num_bytes = current_base_locations_to_size_estimate[ base_location ]
            
            # can be both overweight and able to eat more
            
            if base_location.WouldLikeToRemoveSubfolders( current_normalised_weight / ( 1 - total_normalised_weight_lost_in_first_round ), second_round_total_ideal_weight, largest_subfolder_normalised_weight ):
                
                overweight_locations.append( base_location )
                
            
            if base_location.EagerToAcceptSubfolders( current_normalised_weight / ( 1 - total_normalised_weight_lost_in_first_round ), second_round_total_ideal_weight, smallest_subfolder_normalised_weight, current_num_bytes, smallest_subfolder_num_bytes ):
                
                starving_locations.insert( 0, base_location )
                
            elif base_location.AbleToAcceptSubfolders( current_num_bytes, smallest_subfolder_num_bytes ):
                
                available_locations.append( base_location )
                
            
        
        #
        
        if len( desperately_overweight_locations ) > 0:
            
            potential_sources = desperately_overweight_locations
            potential_destinations = starving_locations + available_locations
            
        elif len( overweight_locations ) > 0:
            
            potential_sources = overweight_locations
            potential_destinations = starving_locations
            
        else:
            
            potential_sources = []
            potential_destinations = []
            
        
        if len( potential_sources ) > 0 and len( potential_destinations ) > 0:
            
            source_base_location = potential_sources.pop( 0 )
            destination_base_location = potential_destinations.pop( 0 )
            
            random.shuffle( file_prefixes )
            
            for file_prefix in file_prefixes:
                
                subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
                
                subfolder = subfolders[0]
                
                base_location = subfolder.base_location
                
                if base_location == source_base_location:
                    
                    overweight_subfolder = ClientFilesPhysical.FilesStorageSubfolder( file_prefix, source_base_location )
                    underweight_subfolder = ClientFilesPhysical.FilesStorageSubfolder( file_prefix, destination_base_location )
                    
                    return ( overweight_subfolder, underweight_subfolder )
                    
                
            
        else:
            
            thumbnail_prefixes = [ prefix for prefix in self._prefixes_to_client_files_subfolders.keys() if prefix.startswith( 't' ) ]
            
            for thumbnail_prefix in thumbnail_prefixes:
                
                if ideal_thumbnail_override_base_location is None:
                    
                    file_prefix = 'f' + thumbnail_prefix[1:]
                    
                    subfolders = None
                    
                    if file_prefix in self._prefixes_to_client_files_subfolders:
                        
                        subfolders = self._prefixes_to_client_files_subfolders[ file_prefix ]
                        
                    else:
                        
                        # TODO: Consider better that thumbs might not be split but files would.
                        # We need to better deal with t43 trying to find its place in f431, and t431 to f43, which means triggering splits or whatever (when we get to that code)
                        
                        for ( possible_file_prefix, possible_subfolders ) in self._prefixes_to_client_files_subfolders.items():
                            
                            if possible_file_prefix.startswith( file_prefix ) or file_prefix.startswith( possible_file_prefix ):
                                
                                subfolders = possible_subfolders
                                
                                break
                                
                            
                        
                    
                    if subfolders is None:
                        
                        # this shouldn't ever fire, and by the time I expect to split subfolders, all this code will work different anyway
                        # no way it could possibly go wrong
                        raise Exception( 'Had a problem trying to find a thumnail migration location due to split subfolders! Let hydev know!' )
                        
                    
                    subfolder = subfolders[0]
                    
                    correct_base_location = subfolder.base_location
                    
                else:
                    
                    correct_base_location = ideal_thumbnail_override_base_location
                    
                
                subfolders = self._prefixes_to_client_files_subfolders[ thumbnail_prefix ]
                
                subfolder = subfolders[0]
                
                current_thumbnails_base_location = subfolder.base_location
                
                if current_thumbnails_base_location != correct_base_location:
                    
                    current_subfolder = ClientFilesPhysical.FilesStorageSubfolder( thumbnail_prefix, current_thumbnails_base_location )
                    correct_subfolder = ClientFilesPhysical.FilesStorageSubfolder( thumbnail_prefix, correct_base_location )
                    
                    return ( current_subfolder, correct_subfolder )
                    
                
            
        
        return None
        
    
    def _GetSubfolderForFile( self, hash: bytes, prefix_type: str ) -> ClientFilesPhysical.FilesStorageSubfolder:
        
        # TODO: So this will be a crux of the more complicated system
        # might even want a media result eventually, for various 'ah, because it is archived, it should go here'
        # for now it is a patch to navigate multiples into our currently mutually exclusive storage dataset
        
        # we probably need to break this guy into variants of 'getpossiblepaths' vs 'getidealpath' for different callers
        # getideal would be testing purge states and client files locations max num bytes stuff
        # there should, in all circumstances, be a place to put a file, so there should always be at least one non-num_bytes'd location with weight to handle 100% coverage of the spillover
        # if we are over the limit on the place the directory is supposed to be, I think we are creating a stub subfolder in the spillover place and writing there, but that'll mean saving a new subfolder, so be careful
        # maybe the spillover should always have 100% coverage no matter what, and num_bytes'd locations should always just have extensions. something to think about
        
        return self._GetPossibleSubfoldersForFile( hash, prefix_type )[0]
        
    
    def _HandleCriticalDriveError( self ):
        
        self._controller.new_options.SetBoolean( 'pause_import_folders_sync', True )
        self._controller.new_options.SetBoolean( 'pause_subs_sync', True )
        self._controller.new_options.SetBoolean( 'pause_all_file_queues', True )
        
        HydrusData.ShowText( 'A critical drive error has occurred. All importers--subscriptions, import folders, and paged file import queues--have been paused. Once the issue is clear, restart the client and resume your imports after restart under the file and network menus!' )
        
        self._controller.pub( 'notify_refresh_network_menu' )
        
    
    def _IterateAllFilePaths( self ):
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            if prefix.startswith( 'f' ):
                
                for subfolder in subfolders:
                    
                    files_dir = subfolder.path
                    
                    filenames = list( os.listdir( files_dir ) )
                    
                    for filename in filenames:
                        
                        yield os.path.join( files_dir, filename )
                        
                    
                
            
        
    
    def _IterateAllThumbnailPaths( self ):
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            if prefix.startswith( 't' ):
                
                for subfolder in subfolders:
                    
                    files_dir = subfolder.path
                    
                    filenames = list( os.listdir( files_dir ) )
                    
                    for filename in filenames:
                        
                        yield os.path.join( files_dir, filename )
                        
                    
                
            
        
    
    def _LookForFilePath( self, hash ):
        
        for potential_mime in HC.ALLOWED_MIMES:
            
            potential_path = self._GenerateExpectedFilePath( hash, potential_mime )
            
            if os.path.exists( potential_path ):
                
                return ( potential_path, potential_mime )
                
            
        
        subfolders = self._GetPossibleSubfoldersForFile( hash, 'f' )
        
        for subfolder in subfolders:
            
            if not subfolder.PathExists():
                
                raise HydrusExceptions.DirectoryMissingException( f'The directory {subfolder.path} was not found! Reconnect the missing location or shut down the client immediately!' )
                
            
        
        raise HydrusExceptions.FileMissingException( 'File for ' + hash.hex() + ' not found!' )
        
    
    def _Reinit( self ):
        
        self._ReinitSubfolders()
        
        if CG.client_controller.IsFirstStart():
            
            try:
                
                dirs_to_test = set()
                
                for subfolder in self._GetAllSubfolders():
                    
                    dirs_to_test.add( subfolder.base_location.path )
                    dirs_to_test.add( subfolder.path )
                    
                
                for dir_to_test in dirs_to_test:
                    
                    try:
                        
                        HydrusPaths.MakeSureDirectoryExists( dir_to_test )
                        
                    except:
                        
                        text = 'Attempting to create the database\'s client_files folder structure in {} failed!'.format( dir_to_test )
                        
                        self._controller.BlockingSafeShowCriticalMessage( 'unable to create file structure', text )
                        
                        raise
                        
                    
                
            except:
                
                text = 'Attempting to create the database\'s client_files folder structure failed!'
                
                self._controller.BlockingSafeShowCriticalMessage( 'unable to create file structure', text )
                
                raise
                
            
        else:
            
            self._ReinitMissingLocations()
            
            if len( self._missing_subfolders ) > 0:
                
                self._AttemptToHealMissingLocations()
                
                self._ReinitSubfolders()
                
                self._ReinitMissingLocations()
                
            
            if len( self._missing_subfolders ) > 0:
                
                self._bad_error_occurred = True
                
                #
                
                missing_dict = HydrusData.BuildKeyToListDict( [ ( subfolder.base_location, subfolder.prefix ) for subfolder in self._missing_subfolders ] )
                
                missing_base_locations = sorted( missing_dict.keys(), key = lambda b_l: b_l.path )
                
                missing_string = ''
                
                for missing_base_location in missing_base_locations:
                    
                    missing_prefixes = sorted( missing_dict[ missing_base_location ] )
                    
                    missing_prefixes_string = '    ' + os.linesep.join( ( ', '.join( block ) for block in HydrusLists.SplitListIntoChunks( missing_prefixes, 32 ) ) )
                    
                    missing_string += os.linesep
                    missing_string += str( missing_base_location )
                    missing_string += os.linesep
                    missing_string += missing_prefixes_string
                    
                
                #
                
                if len( self._missing_subfolders ) > 4:
                    
                    text = 'When initialising the client files manager, some file locations did not exist! They have all been written to the log!'
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'missing locations', text )
                    
                    HydrusData.DebugPrint( 'Missing locations follow:' )
                    HydrusData.DebugPrint( missing_string )
                    
                else:
                    
                    text = 'When initialising the client files manager, these file locations did not exist:'
                    text += os.linesep * 2
                    text += missing_string
                    text += os.linesep * 2
                    text += 'If this is happening on client boot, you should now be presented with a dialog to correct this manually!'
                    
                    self._controller.BlockingSafeShowCriticalMessage( 'missing locations', text )
                    
                
            
        
    
    def _ReinitSubfolders( self ):
        
        subfolders = self._controller.Read( 'client_files_subfolders' )
        
        self._prefixes_to_client_files_subfolders = collections.defaultdict( list )
        
        for subfolder in subfolders:
            
            self._prefixes_to_client_files_subfolders[ subfolder.prefix ].append( subfolder )
            
        
        self._smallest_prefix = min( ( len( prefix ) for prefix in self._prefixes_to_client_files_subfolders.keys() ) ) - 1
        self._largest_prefix = max( ( len( prefix ) for prefix in self._prefixes_to_client_files_subfolders.keys() ) ) - 1
        
    
    def _ReinitMissingLocations( self ):
        
        self._missing_subfolders = set()
        
        for ( prefix, subfolders ) in self._prefixes_to_client_files_subfolders.items():
            
            for subfolder in subfolders:
                
                if not subfolder.PathExists():
                    
                    self._missing_subfolders.add( subfolder )
                    
                
            
        
    
    def _WaitOnWakeup( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'file_system_waits_on_wakeup' ):
            
            while CG.client_controller.JustWokeFromSleep():
                
                HydrusThreading.CheckIfThreadShuttingDown()
                
                time.sleep( 1.0 )
                
            
        
    
    def AllLocationsAreDefault( self ):
        
        with self._file_storage_rwlock.read:
            
            db_dir = self._controller.GetDBDir()
            
            client_files_default = os.path.join( db_dir, 'client_files' )
            
            all_base_locations = self._GetCurrentSubfolderBaseLocations()
            
            return False not in ( location.path.startswith( client_files_default ) for location in all_base_locations )
            
        
    
    def LocklessAddFileFromBytes( self, hash, mime, file_bytes ):
        
        dest_path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Adding file from string: ' + str( ( len( file_bytes ), dest_path ) ) )
            
        
        HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
        
        with open( dest_path, 'wb' ) as f:
            
            f.write( file_bytes )
            
        
    
    def AddFile( self, hash, mime, source_path, thumbnail_bytes = None ):
        
        with self._file_storage_rwlock.write:
            
            self._AddFile( hash, mime, source_path )
            
            if thumbnail_bytes is not None:
                
                self._AddThumbnailFromBytes( hash, thumbnail_bytes )
                
            
        
    
    def AddThumbnailFromBytes( self, hash, thumbnail_bytes, silent = False ):
        
        with self._file_storage_rwlock.write:
            
            self._AddThumbnailFromBytes( hash, thumbnail_bytes, silent = silent )
            
        
    
    def ChangeFileExt( self, hash, old_mime, mime ):
        
        if old_mime == mime:
            
            return False
            
        
        with self._file_storage_rwlock.write:
            
            return self._ChangeFileExt( hash, old_mime, mime )
            
        
    
    def ClearOrphans( self, move_location = None ):
        
        with self._file_storage_rwlock.write:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'clearing orphans' )
            job_status.SetStatusText( 'preparing' )
            
            self._controller.pub( 'message', job_status )
            
            orphan_paths = []
            orphan_thumbnails = []
            
            for ( i, path ) in enumerate( self._IterateAllFilePaths() ):
                
                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    status = 'reviewed ' + HydrusData.ToHumanInt( i ) + ' files, found ' + HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphans'
                    
                    job_status.SetStatusText( status )
                    
                
                try:
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = bytes.fromhex( should_be_a_hex_hash )
                    
                    is_an_orphan = CG.client_controller.Read( 'is_an_orphan', 'file', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    if move_location is not None:
                        
                        ( source_dir, filename ) = os.path.split( path )
                        
                        dest = os.path.join( move_location, filename )
                        
                        dest = HydrusPaths.AppendPathUntilNoConflicts( dest )
                        
                        HydrusData.Print( 'Moving the orphan ' + path + ' to ' + dest )
                        
                        try:
                            
                            HydrusPaths.MergeFile( path, dest )
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( f'Had trouble moving orphan from {path} to {dest}! Abandoning job!' )
                            
                            HydrusData.ShowException( e, do_wait = False )
                            
                            job_status.Cancel()
                            
                            return
                            
                        
                    
                    orphan_paths.append( path )
                    
                
            
            time.sleep( 2 )
            
            for ( i, path ) in enumerate( self._IterateAllThumbnailPaths() ):
                
                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    status = 'reviewed ' + HydrusData.ToHumanInt( i ) + ' thumbnails, found ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphans'
                    
                    job_status.SetStatusText( status )
                    
                
                try:
                    
                    is_an_orphan = False
                    
                    ( directory, filename ) = os.path.split( path )
                    
                    should_be_a_hex_hash = filename[:64]
                    
                    hash = bytes.fromhex( should_be_a_hex_hash )
                    
                    is_an_orphan = CG.client_controller.Read( 'is_an_orphan', 'thumbnail', hash )
                    
                except:
                    
                    is_an_orphan = True
                    
                
                if is_an_orphan:
                    
                    orphan_thumbnails.append( path )
                    
                
            
            time.sleep( 2 )
            
            if move_location is None and len( orphan_paths ) > 0:
                
                status = 'found ' + HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphans, now deleting'
                
                job_status.SetStatusText( status )
                
                time.sleep( 5 )
                
                for ( i, path ) in enumerate( orphan_paths ):
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    HydrusData.Print( 'Deleting the orphan ' + path )
                    
                    status = 'deleting orphan files: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_paths ) )
                    
                    job_status.SetStatusText( status )
                    
                    ClientPaths.DeletePath( path )
                    
                
            
            if len( orphan_thumbnails ) > 0:
                
                status = 'found ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails, now deleting'
                
                job_status.SetStatusText( status )
                
                time.sleep( 5 )
                
                for ( i, path ) in enumerate( orphan_thumbnails ):
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    status = 'deleting orphan thumbnails: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( orphan_thumbnails ) )
                    
                    job_status.SetStatusText( status )
                    
                    HydrusData.Print( 'Deleting the orphan ' + path )
                    
                    ClientPaths.DeletePath( path, always_delete_fully = True )
                    
                
            
            if len( orphan_paths ) == 0 and len( orphan_thumbnails ) == 0:
                
                final_text = 'no orphans found!'
                
            else:
                
                final_text = HydrusData.ToHumanInt( len( orphan_paths ) ) + ' orphan files and ' + HydrusData.ToHumanInt( len( orphan_thumbnails ) ) + ' orphan thumbnails cleared!'
                
            
            job_status.SetStatusText( final_text )
            
            HydrusData.Print( job_status.ToString() )
            
            job_status.Finish()
            
        
    
    def DeleteNeighbourDupes( self, hash, true_mime ):
        
        with self._file_storage_rwlock.write:
            
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
                    
                    delete_ok = HydrusPaths.DeletePath( incorrect_path )
                    
                    if not delete_ok and random.randint( 1, 52 ) != 52:
                        
                        self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusTime.GetNow() + ( 7 * 86400 ) )
                        
                    
                
            
        
    
    def DoDeferredPhysicalDeletes( self ):
        
        wait_period = self._controller.new_options.GetInteger( 'ms_to_wait_between_physical_file_deletes' ) / 1000
        
        num_files_deleted = 0
        num_thumbnails_deleted = 0
        
        while not HG.started_shutdown:
            
            with self._file_storage_rwlock.write:
                
                ( file_hash, thumbnail_hash ) = self._controller.Read( 'deferred_physical_delete' )
                
                if file_hash is None and thumbnail_hash is None:
                    
                    break
                    
                
                if file_hash is not None:
                    
                    media_result = self._controller.Read( 'media_result', file_hash )
                    
                    expected_mime = media_result.GetMime()
                    
                    try:
                        
                        path = self._GenerateExpectedFilePath( file_hash, expected_mime )
                        
                        if not os.path.exists( path ):
                            
                            ( path, actual_mime ) = self._LookForFilePath( file_hash )
                            
                        
                        ClientPaths.DeletePath( path )
                        
                        num_files_deleted += 1
                        
                    except HydrusExceptions.FileMissingException:
                        
                        HydrusData.Print( 'Wanted to physically delete the "{}" file, with expected mime "{}", but it was not found!'.format( file_hash.hex(), HC.mime_string_lookup[ expected_mime ] ) )
                        
                    
                
                if thumbnail_hash is not None:
                    
                    path = self._GenerateExpectedThumbnailPath( thumbnail_hash )
                    
                    if os.path.exists( path ):
                        
                        ClientPaths.DeletePath( path, always_delete_fully = True )
                        
                        num_thumbnails_deleted += 1
                        
                    
                
                self._controller.WriteSynchronous( 'clear_deferred_physical_delete', file_hash = file_hash, thumbnail_hash = thumbnail_hash )
                
                if num_files_deleted % 10 == 0 or num_thumbnails_deleted % 10 == 0:
                    
                    self._controller.pub( 'notify_new_physical_file_delete_numbers' )
                    
                
            
            self._physical_file_delete_wait.wait( wait_period )
            
            self._physical_file_delete_wait.clear()
            
        
        if num_files_deleted > 0 or num_thumbnails_deleted > 0:
            
            self._controller.pub( 'notify_new_physical_file_delete_numbers' )
            
            HydrusData.Print( 'Physically deleted {} files and {} thumbnails from file storage.'.format( HydrusData.ToHumanInt( num_files_deleted ), HydrusData.ToHumanInt( num_files_deleted ) ) )
            
        
    
    def GetCurrentFileBaseLocations( self ):
        
        with self._file_storage_rwlock.read:
            
            return self._GetCurrentSubfolderBaseLocations( only_files = True )
            
        
    
    def GetFilePath( self, hash, mime = None, check_file_exists = True ):
        
        with self._file_storage_rwlock.read:
            
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
            
        
    
    def GetMissingSubfolders( self ):
        
        return self._missing_subfolders
        
    
    def GetThumbnailPath( self, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path request: ' + str( ( hash, mime ) ) )
            
        
        with self._file_storage_rwlock.read:
            
            path = self._GenerateExpectedThumbnailPath( hash )
            
            thumb_missing = not os.path.exists( path )
            
        
        if thumb_missing:
            
            self.RegenerateThumbnail( media )
            
        
        return path
        
    
    def LocklessHasFile( self, hash, mime ):
        
        path = self._GenerateExpectedFilePath( hash, mime )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'File path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def LocklessHasThumbnail( self, hash ):
        
        path = self._GenerateExpectedThumbnailPath( hash )
        
        if HG.file_report_mode:
            
            HydrusData.ShowText( 'Thumbnail path test: ' + path )
            
        
        return os.path.exists( path )
        
    
    def Rebalance( self, job_status ):
        
        try:
            
            if self._bad_error_occurred:
                
                HydrusData.ShowText( 'A serious file error has previously occurred during this session, so further file moving will not be reattempted. Please restart the client before trying again.' )
                
                return
                
            
            with self._file_storage_rwlock.write:
                
                rebalance_tuple = self._GetRebalanceTuple()
                
                while rebalance_tuple is not None:
                    
                    if job_status.IsCancelled():
                        
                        break
                        
                    
                    ( source_subfolder, dest_subfolder ) = rebalance_tuple
                    
                    text = f'Moving "{source_subfolder}" to "{dest_subfolder}".'
                    
                    HydrusData.Print( text )
                    
                    job_status.SetStatusText( text )
                    
                    # these two lines can cause a deadlock because the db sometimes calls stuff in here.
                    self._controller.WriteSynchronous( 'relocate_client_files', source_subfolder, dest_subfolder )
                    
                    self._Reinit()
                    
                    rebalance_tuple = self._GetRebalanceTuple()
                    
                    time.sleep( 0.01 )
                    
                
            
        finally:
            
            job_status.SetStatusText( 'done!' )
            
            job_status.FinishAndDismiss()
            
        
    
    def RebalanceWorkToDo( self ):
        
        with self._file_storage_rwlock.read:
            
            return self._GetRebalanceTuple() is not None
            
        
    
    def RegenerateThumbnail( self, media ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            return
            
        
        with self._file_storage_rwlock.read:
            
            file_path = self._GenerateExpectedFilePath( hash, mime )
            
            if not os.path.exists( file_path ):
                
                raise HydrusExceptions.FileMissingException( 'The thumbnail for file ' + hash.hex() + ' could not be regenerated from the original file because the original file is missing! This event could indicate hard drive corruption. Please check everything is ok.')
                
            
            thumbnail_bytes = self._GenerateThumbnailBytes( file_path, media )
            
        
        with self._file_storage_rwlock.write:
            
            self._AddThumbnailFromBytes( hash, thumbnail_bytes )
            
        return True
    
    
    def RegenerateThumbnailIfWrongSize( self, media ):
        
        do_it = False
        
        try:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if mime not in HC.MIMES_WITH_THUMBNAILS:
                
                return
                
            
            ( media_width, media_height ) = media.GetResolution()
            
            path = self._GenerateExpectedThumbnailPath( hash )
            
            if not os.path.exists( path ):
                
                raise Exception()
                
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( path )
            
            numpy_image = ClientImageHandling.GenerateNumPyImage( path, thumbnail_mime )
            
            ( current_width, current_height ) = HydrusImageHandling.GetResolutionNumPy( numpy_image )
            
            bounding_dimensions = self._controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = self._controller.new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            ( expected_width, expected_height ) = HydrusImageHandling.GetThumbnailResolution( (media_width, media_height), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
            
            if current_width != expected_width or current_height != expected_height:
                
                do_it = True
                
            
        except:
            
            do_it = True
            
        
        if do_it:
            
            self.RegenerateThumbnail( media )
            
        
        return do_it
        
    
    def Reinit( self ):
        
        # this is still useful to hit on ideals changing, since subfolders bring the weight and stuff of those settings. we'd rather it was generally synced
        self._Reinit()
        
    
    def UpdateFileModifiedTimestampMS( self, media, modified_timestamp_ms: int ):
        
        hash = media.GetHash()
        mime = media.GetMime()
        
        path = self._GenerateExpectedFilePath( hash, mime )
        
        with self._file_storage_rwlock.write:
            
            if os.path.exists( path ):
                
                existing_access_time = os.path.getatime( path )
                existing_modified_time = os.path.getmtime( path )
                
                # floats are ok here!
                modified_timestamp = modified_timestamp_ms / 1000
                
                try:
                    
                    os.utime( path, ( existing_access_time, modified_timestamp ) )
                    
                    HydrusData.Print( 'Successfully changed modified time of "{}" from {} to {}.'.format( path, HydrusTime.TimestampToPrettyTime( existing_modified_time ), HydrusTime.TimestampToPrettyTime( modified_timestamp ) ))
                    
                except PermissionError:
                    
                    HydrusData.Print( 'Tried to set modified time of {} to file "{}", but did not have permission!'.format( HydrusTime.TimestampToPrettyTime( modified_timestamp ), path ) )
                    
                
            
        
    
    def shutdown( self ):
        
        self._physical_file_delete_wait.set()
        
    

def HasHumanReadableEmbeddedMetadata( path, mime ):
    
    if mime not in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
        
        return False
        
    
    if mime == HC.APPLICATION_PDF:
        
        has_human_readable_embedded_metadata = ClientPDFHandling.HasHumanReadableEmbeddedMetadata( path )
        
    else:
        
        try:
            
            pil_image = HydrusImageOpening.RawOpenPILImage( path )
            
        except:
            
            return False
            
        
        has_human_readable_embedded_metadata = HydrusImageMetadata.HasHumanReadableEmbeddedMetadata( pil_image )
        
    
    return has_human_readable_embedded_metadata
    

def HasTransparency( path, mime, duration = None, num_frames = None, resolution = None ):
    
    if mime not in HC.MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY:
        
        return False
        
    
    try:
        
        if mime in HC.IMAGES:
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( path, mime )
            
            return HydrusImageColours.NumPyImageHasUsefulAlphaChannel( numpy_image )
            
        elif mime in ( HC.ANIMATION_GIF, HC.ANIMATION_APNG ):
            
            if num_frames is None or resolution is None:
                
                return False # something crazy going on, so let's bail out
                
            
            we_checked_alpha_channel = False
            
            if mime == HC.ANIMATION_GIF:
                
                renderer = ClientVideoHandling.GIFRenderer( path, num_frames, resolution )
                
            else: # HC.ANIMATION_APNG
                
                renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration, num_frames, resolution )
                
            
            for i in range( num_frames ):
                
                numpy_image = renderer.read_frame()
                
                if not we_checked_alpha_channel:
                    
                    if not HydrusImageColours.NumPyImageHasAlphaChannel( numpy_image ):
                        
                        return False
                        
                    
                    we_checked_alpha_channel = True
                    
                
                if HydrusImageColours.NumPyImageHasUsefulAlphaChannel( numpy_image ):
                    
                    return True
                    
                
            
        
    except HydrusExceptions.DamagedOrUnusualFileException as e:
        
        HydrusData.Print( 'Problem determining transparency for "{}":'.format( path ) )
        HydrusData.PrintException( e )
        
        return False
        
    
    return False
    

def add_extra_comments_to_job_status( job_status: ClientThreading.JobStatus ):
    
    extra_comments = []
    
    num_thumb_refits = job_status.GetIfHasVariable( 'num_thumb_refits' )
    num_bad_files = job_status.GetIfHasVariable( 'num_bad_files' )
    
    if num_thumb_refits is not None:
        
        extra_comments.append( 'thumbs needing regen: {}'.format( HydrusData.ToHumanInt( num_thumb_refits ) ) )
        
    
    if num_bad_files is not None:
        
        extra_comments.append( 'missing or invalid files: {}'.format( HydrusData.ToHumanInt( num_bad_files ) ) )
        
    
    sub_status_message = '\n'.join( extra_comments )
    
    if len( sub_status_message ) > 0:
        
        job_status.SetStatusText( sub_status_message, 2 )
        
    

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
        
        self._serious_error_encountered = False
        
        self._wake_background_event = threading.Event()
        self._reset_background_event = threading.Event()
        self._shutdown = False
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'Wake', 'checkbox_manager_inverted' )
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        
    
    def _AbleToDoBackgroundMaintenance( self ):
        
        CG.client_controller.WaitUntilViewFree()
        
        if CG.client_controller.CurrentlyIdle():
            
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
        
        file_is_missing = False
        file_is_invalid = False
        
        path = ''
        
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
            
            error_dir = os.path.join( self._controller.GetDBDir(), 'missing_and_invalid_files' )
            
            HydrusPaths.MakeSureDirectoryExists( error_dir )
            
            pretty_timestamp = time.strftime( '%Y-%m-%d %H-%M-%S', time.localtime( HydrusTime.SecondiseMS( self._controller.GetBootTimestampMS() ) ) )
            
            missing_hashes_filename = '{} missing hashes.txt'.format( pretty_timestamp )
            
            missing_hashes_path = os.path.join( error_dir, missing_hashes_filename )
            
            with open( missing_hashes_path, 'a', encoding = 'utf-8' ) as f:
                
                f.write( hash.hex() )
                f.write( '\n' )
                
            
            tags = media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE )
            
            if len( tags ) > 0:
                
                try:
                    
                    with open( os.path.join( error_dir, '{}.tags.txt'.format( hash.hex() ) ), 'w', encoding = 'utf-8' ) as f:
                        
                        for tag in sorted( tags ):
                            
                            f.write( tag )
                            f.write( '\n' )
                        
                    
                except Exception as e:
                    
                    HydrusData.Print( 'Tried to export tags for missing file {}, but encountered this error:'.format( hash.hex() ) )
                    HydrusData.PrintException( e, do_wait = False )
                    
                
            
            urls = media_result.GetLocationsManager().GetURLs()
            
            if len( urls ) > 0:
                
                try:
                    
                    with open( os.path.join( error_dir, '{}.urls.txt'.format( hash.hex() ) ), 'w', encoding = 'utf-8' ) as f:
                        
                        for url in urls:
                            
                            f.write( url )
                            f.write( '\n' )
                            
                        
                    
                    with open( os.path.join( error_dir, 'all_urls.txt' ), 'a', encoding = 'utf-8' ) as f:
                        
                        for url in urls:
                            
                            f.write( url )
                            f.write( '\n' )
                            
                        
                    
                except Exception as e:
                    
                    HydrusData.Print( 'Tried to export URLs for missing file {}, but encountered this error:'.format( hash.hex() ) )
                    HydrusData.PrintException( e, do_wait = False )
                    
                
            
            useful_urls = []
            
            for url in urls:
                
                add_it = False
                
                try:
                    
                    url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None:
                    
                    add_it = True
                    
                else:
                    
                    if url_class.GetURLType() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                        
                        add_it = True
                        
                    
                
                if add_it:
                    
                    useful_urls.append( url )
                    
                
            
            if job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY:
                
                try_redownload = False
                delete_record = False
                
            elif job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD ):
                
                try_redownload = len( useful_urls ) > 0
                delete_record = not try_redownload
                
            else:
                
                try_redownload = job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL ) and len( useful_urls ) > 0
                delete_record = job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                
            
            do_export = file_is_invalid and ( job_type in ( REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE ) or ( job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL and try_redownload ) )
            
            if do_export:
                
                HydrusPaths.MakeSureDirectoryExists( error_dir )
                
                dest_path = os.path.join( error_dir, os.path.basename( path ) )
                
                try:
                    
                    HydrusPaths.MergeFile( path, dest_path )
                    
                except Exception as e:
                    
                    raise Exception( f'Could not move the damaged file "{path}" to "{dest_path}"!' ) from e
                    
                
                if not self._pubbed_message_about_invalid_file_export:
                    
                    self._pubbed_message_about_invalid_file_export = True
                    
                    message = 'During file maintenance, a file was found to be invalid. It and any known URLs have been moved to "{}".'.format( error_dir )
                    message += os.linesep * 2
                    message += 'More files may be invalid, but this message will not appear again during this boot.'
                    
                    HydrusData.ShowText( message )
                    
                
            
            if try_redownload:
                
                def qt_add_url( url ):
                    
                    CG.client_controller.gui.ImportURL( url, 'missing files redownloader' )
                    
                
                for url in useful_urls:
                    
                    CG.client_controller.CallBlockingToQt( CG.client_controller.gui, qt_add_url, url )
                    
                
            
            if delete_record:
                
                leave_deletion_record = job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'Record deleted during File Integrity check.' )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
                self._controller.WriteSynchronous( 'content_updates', content_update_package )
                
                if not leave_deletion_record:
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, ( hash, ) )
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                    
                    self._controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                
                if not self._pubbed_message_about_bad_file_record_delete:
                    
                    self._pubbed_message_about_bad_file_record_delete = True
                    
                    if leave_deletion_record:
                        
                        m = 'Its file record has been deleted from the database, leaving a deletion record (so it cannot be easily reimported).'
                        
                    else:
                        
                        m = 'Its file record has been removed from the database without leaving a deletion record (so it can be easily reimported).'
                        
                    
                    message = 'During file maintenance, a file was found to be missing or invalid. {} Its file hash and any known URLs have been written to "{}".'.format( m, error_dir )
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
            
        
    
    def _HasEXIF( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_EXIF:
            
            return False
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            try:
                
                raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                
                has_exif = HydrusImageMetadata.HasEXIF( path )
                
            except:
                
                has_exif = False
                
            
            additional_data = has_exif
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _HasHumanReadableEmbeddedMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
            
            return False
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            has_human_readable_embedded_metadata = HasHumanReadableEmbeddedMetadata( path, mime )
            
            additional_data = has_human_readable_embedded_metadata
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _HasICCProfile( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_ICC_PROFILE:
            
            return False
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            if mime == HC.APPLICATION_PSD:
            
                try:
                    
                    has_icc_profile = HydrusPSDHandling.PSDHasICCProfile( path )
                    
                except:
                    
                    return None
                    
            else:
                
                try:
                    
                    raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                    
                except:
                    
                    return None
                    
                
                has_icc_profile = HydrusImageMetadata.HasICCProfile( raw_pil_image )
                
            
            additional_data = has_icc_profile
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _HasTransparency( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY:
            
            return False
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            has_transparency = HasTransparency( path, mime, duration = media_result.GetDurationMS(), num_frames = media_result.GetNumFrames(), resolution = media_result.GetResolution() )
            
            additional_data = has_transparency
            
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
            
            if mime != original_mime and not media_result.GetFileInfoManager().FiletypeIsForced():
                
                if not HydrusPaths.PathIsFree( path ):
                    
                    time.sleep( 0.5 )
                    
                
                needed_to_dupe_the_file = self._controller.client_files_manager.ChangeFileExt( hash, original_mime, mime )
                
                if needed_to_dupe_the_file:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusTime.GetNow() + 3600 )
                    
                
            
            return additional_data
            
        except HydrusExceptions.UnsupportedFileException:
            
            self._CheckFileIntegrity( media_result, REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD )
            
            return None
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileModifiedTimestampMS( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime in HC.HYDRUS_UPDATE_FILES:
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            file_modified_timestamp_ms = HydrusFileHandling.GetFileModifiedTimestampMS( path )
            
            additional_data = file_modified_timestamp_ms
            
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
            
            return self._controller.client_files_manager.RegenerateThumbnail( media_result )
            
        except HydrusExceptions.FileMissingException:
            
            pass
            
        
    
    def _RegenFileThumbnailRefit( self, media_result ):
        
        good_to_go = self._CanRegenThumbForMediaResult( media_result )
        
        if not good_to_go:
            
            return False
            
        
        try:
            
            was_regenerated = self._controller.client_files_manager.RegenerateThumbnailIfWrongSize( media_result )
            
            return was_regenerated
            
        except HydrusExceptions.FileMissingException:
            
            return False
            
        
    
    def _RegenPixelHash( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH:
            
            return None
            
        
        duration = media_result.GetDurationMS()
        
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
            
        
    def _RegenBlurhash( self, media ):
        
        if media.GetMime() not in HC.MIMES_WITH_THUMBNAILS:
            
            return None
            
        
        try:
            
            thumbnail_path = self._controller.client_files_manager.GetThumbnailPath( media )
            
        except HydrusExceptions.FileMissingException as e:
            
            return None
            
        
        try:
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( thumbnail_path )
            
            numpy_image = ClientImageHandling.GenerateNumPyImage( thumbnail_path, thumbnail_mime )
            
            return HydrusBlurhash.GetBlurhashFromNumPy( numpy_image )
            
        except:
            
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
        
    
    def _RunJob( self, media_results_to_job_types, job_status, job_done_hook = None ):
        
        if self._serious_error_encountered:
            
            return
            
        
        cleared_jobs = []
        
        try:
            
            big_pauser = HydrusThreading.BigJobPauser( wait_time = 0.8 )
            
            last_time_jobs_were_cleared = HydrusTime.GetNow()
            
            for ( media_result, job_types ) in media_results_to_job_types.items():
                
                big_pauser.Pause()
                
                hash = media_result.GetHash()
                
                if job_status.IsCancelled() or self._shutdown:
                    
                    return
                    
                
                for job_type in job_types:
                    
                    if HG.file_report_mode:
                        
                        HydrusData.ShowText( 'file maintenance: {} for {}'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() ) )
                        
                    
                    if job_done_hook is not None:
                        
                        job_done_hook()
                        
                    
                    clear_job = True
                    
                    additional_data = None
                    
                    try:
                        
                        if job_type == REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                            
                            additional_data = self._RegenFileMetadata( media_result )
                            
                            # media_result has just changed
                            break
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP:
                            
                            additional_data = self._RegenFileModifiedTimestampMS( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_OTHER_HASHES:
                            
                            additional_data = self._RegenFileOtherHashes( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY:
                            
                            additional_data = self._HasTransparency( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF:
                            
                            additional_data = self._HasEXIF( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
                            
                            additional_data = self._HasHumanReadableEmbeddedMetadata( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE:
                            
                            additional_data = self._HasICCProfile( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_PIXEL_HASH:
                            
                            additional_data = self._RegenPixelHash( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                            
                            additional_data = self._RegenFileThumbnailForce( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                            
                            was_regenerated = self._RegenFileThumbnailRefit( media_result )
                            
                            additional_data = was_regenerated
                            
                            if was_regenerated:
                                
                                num_thumb_refits = job_status.GetIfHasVariable( 'num_thumb_refits' )
                                
                                if num_thumb_refits is None:
                                    
                                    num_thumb_refits = 0
                                    
                                
                                num_thumb_refits += 1
                                
                                job_status.SetVariable( 'num_thumb_refits', num_thumb_refits )
                                
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES:
                            
                            self._DeleteNeighbourDupes( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP:
                            
                            additional_data = self._CheckSimilarFilesMembership( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA:
                            
                            additional_data = self._RegenSimilarFilesMetadata( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS:
                            
                            self._FixFilePermissions( media_result )
                            
                        elif job_type == REGENERATE_FILE_DATA_JOB_BLURHASH:
                            
                            additional_data = self._RegenBlurhash( media_result )
                            
                        elif job_type in (
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE,
                            REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY
                        ):
                            
                            file_was_bad = self._CheckFileIntegrity( media_result, job_type )
                            
                            if file_was_bad:
                                
                                num_bad_files = job_status.GetIfHasVariable( 'num_bad_files' )
                                
                                if num_bad_files is None:
                                    
                                    num_bad_files = 0
                                    
                                
                                num_bad_files += 1
                                
                                job_status.SetVariable( 'num_bad_files', num_bad_files + 1 )
                                
                            
                        
                    except HydrusExceptions.ShutdownException:
                        
                        # no worries
                        
                        clear_job = False
                        
                        return
                        
                    except IOError as e:
                        
                        HydrusData.PrintException( e )
                        
                        job_status = ClientThreading.JobStatus()
                        
                        message = 'Hey, while performing file maintenance task "{}" on file {}, the client ran into an I/O Error! This could be just some media library moaning about a weird (probably truncated) file, but it could also be a significant hard drive problem. Look at the error yourself. If it looks serious, you should shut the client down and check your hard drive health immediately. Just to be safe, no more file maintenance jobs will be run this boot, and a full traceback has been written to the log.'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() )
                        message += os.linesep * 2
                        message += str( e )
                        
                        job_status.SetStatusText( message )
                        
                        job_status.SetFiles( [ hash ], 'I/O error file' )
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        self._serious_error_encountered = True
                        self._shutdown = True
                        
                        return
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        job_status = ClientThreading.JobStatus()
                        
                        message = 'There was an unexpected problem performing maintenance task "{}" on file {}! The job will not be reattempted. A full traceback of this error should be written to the log.'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() )
                        message += os.linesep * 2
                        message += str( e )
                        
                        job_status.SetStatusText( message )
                        
                        job_status.SetFiles( [ hash ], 'failed file' )
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                    finally:
                        
                        self._work_tracker.ReportRequestUsed( num_requests = regen_file_enum_to_job_weight_lookup[ job_type ] )
                        
                        if clear_job:
                            
                            cleared_jobs.append( ( hash, job_type, additional_data ) )
                            
                        
                    
                
                if HydrusTime.TimeHasPassed( last_time_jobs_were_cleared + 10 ) or len( cleared_jobs ) > 256:
                    
                    self._controller.WriteSynchronous( 'file_maintenance_clear_jobs', cleared_jobs )
                    
                    last_time_jobs_were_cleared = HydrusTime.GetNow()
                    
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
        
        if self._serious_error_encountered:
            
            return
            
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        job_types_to_counts = CG.client_controller.Read( 'file_maintenance_get_job_counts' )
        
        # in a dict so the hook has scope to alter it
        vr_status = {}
        
        vr_status[ 'num_jobs_done' ] = 0
        
        total_num_jobs_to_do = sum( ( count_due for ( key, ( count_due, count_not_due ) ) in job_types_to_counts.items() if mandated_job_types is None or key in mandated_job_types ) )
        
        def job_done_hook():
            
            vr_status[ 'num_jobs_done' ] += 1
            
            num_jobs_done = vr_status[ 'num_jobs_done' ]
            
            status_text = '{}'.format( HydrusData.ConvertValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do ) )
            
            job_status.SetStatusText( status_text )
            
            job_status.SetVariable( 'popup_gauge_1', ( num_jobs_done, total_num_jobs_to_do ) )
            
            add_extra_comments_to_job_status( job_status )
            
        
        job_status.SetStatusTitle( 'file maintenance' )
        
        message_pubbed = False
        work_done = False
        
        # tell mainloop to step out a sec
        self._reset_background_event.set()
        
        with self._maintenance_lock:
            
            try:
                
                while True:
                    
                    hashes_to_job_types = self._controller.Read( 'file_maintenance_get_jobs', mandated_job_types )
                    
                    if len( hashes_to_job_types ) == 0:
                        
                        break
                        
                    
                    work_done = True
                    
                    if not message_pubbed:
                        
                        self._controller.pub( 'message', job_status )
                        
                        message_pubbed = True
                        
                    
                    if job_status.IsCancelled():
                        
                        return
                        
                    
                    hashes = set( hashes_to_job_types.keys() )
                    
                    media_results = self._controller.Read( 'media_results', hashes )
                    
                    hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                    
                    media_results_to_job_types = { hashes_to_media_results[ hash ] : job_types for ( hash, job_types ) in hashes_to_job_types.items() }
                    
                    with self._lock:
                        
                        self._RunJob( media_results_to_job_types, job_status, job_done_hook = job_done_hook )
                        
                    
                    time.sleep( 0.0001 )
                    
                
            finally:
                
                job_status.SetStatusText( 'done!' )
                
                job_status.DeleteVariable( 'popup_gauge_1' )
                
                job_status.FinishAndDismiss( 5 )
                
                if not work_done:
                    
                    HydrusData.ShowText( 'No file maintenance due!' )
                    
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def MainLoopBackgroundWork( self ):
        
        def check_shutdown():
            
            if HydrusThreading.IsThreadShuttingDown() or self._shutdown or self._serious_error_encountered:
                
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
            
            time_to_start = HydrusTime.GetNow() + 15
            
            while not HydrusTime.TimeHasPassed( time_to_start ):
                
                check_shutdown()
                
                time.sleep( 1 )
                
            
            while True:
                
                check_shutdown()
                
                did_work = False
                
                with self._maintenance_lock:
                    
                    hashes_to_job_types = self._controller.Read( 'file_maintenance_get_jobs' )
                    
                    if len( hashes_to_job_types ) > 0:
                        
                        did_work = True
                        
                        job_status = ClientThreading.JobStatus()
                        
                        i = 0
                        
                        try:
                            
                            hashes = set( hashes_to_job_types.keys() )
                            
                            media_results = self._controller.Read( 'media_results', hashes )
                            
                            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
                            
                            media_results_to_job_types = { hashes_to_media_results[ hash ] : job_types for ( hash, job_types ) in hashes_to_job_types.items() }
                            
                            for ( media_result, job_types ) in media_results_to_job_types.items():
                                
                                wait_on_maintenance()
                                
                                if should_reset():
                                    
                                    break
                                    
                                
                                with self._lock:
                                    
                                    self._RunJob( { media_result : job_types }, job_status )
                                    
                                
                            
                            time.sleep( 0.0001 )
                            
                            i += 1
                            
                            if i % 100 == 0:
                                
                                self._controller.pub( 'notify_files_maintenance_done' )
                                
                            
                            check_shutdown()
                            
                        finally:
                            
                            self._controller.pub( 'notify_files_maintenance_done' )
                            
                        
                    
                
                if not did_work:
                    
                    self._wake_background_event.wait( 600 )
                    
                    self._wake_background_event.clear()
                    
                
                # a small delay here is helpful for the forcemaintenance guy to have a chance to step in on reset
                time.sleep( 1 )
                
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        
    
    def NotifyNewOptions( self ):
        
        with self._lock:
            
            self._ReInitialiseWorkRules()
            
        
    
    def RunJobImmediately( self, media_results, job_type, pub_job_status = True ):
        
        if self._serious_error_encountered and pub_job_status:
            
            HydrusData.ShowText( 'Sorry, the file maintenance system has encountered a serious error and will perform no more jobs this boot. Please shut down and check your hard drive health immediately.' )
            
            return
            
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        total_num_jobs_to_do = len( media_results )
        
        # in a dict so the hook has scope to alter it
        vr_status = {}
        
        vr_status[ 'num_jobs_done' ] = 0
        
        def job_done_hook():
            
            vr_status[ 'num_jobs_done' ] += 1
            
            num_jobs_done = vr_status[ 'num_jobs_done' ]
            
            status_text = '{} - {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do ), regen_file_enum_to_str_lookup[ job_type ] )
            
            job_status.SetStatusText( status_text )
            
            job_status.SetVariable( 'popup_gauge_1', ( num_jobs_done, total_num_jobs_to_do ) )
            
            add_extra_comments_to_job_status( job_status )
            
        
        job_status.SetStatusTitle( 'regenerating file data' )
        
        if pub_job_status:
            
            self._controller.pub( 'message', job_status )
            
        
        self._reset_background_event.set()
        
        try:
            
            media_results_to_job_types = { media_result : ( job_type, ) for media_result in media_results }
            
            with self._lock:
                
                self._RunJob( media_results_to_job_types, job_status, job_done_hook = job_done_hook )
                
            
        finally:
            
            job_status.SetStatusText( 'done!' )
            
            job_status.DeleteVariable( 'popup_gauge_1' )
            
            job_status.FinishAndDismiss( 5 )
            
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
        
    
    def Wake( self ):
        
        self._wake_background_event.set()
        
    
