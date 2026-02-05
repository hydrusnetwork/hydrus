import os
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files.images import HydrusBlurhash
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening
from hydrus.core.networking import HydrusNetworking
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client.files import ClientFiles
from hydrus.client.files.images import ClientImagePerceptualHashes

from hydrus.client import ClientThreading
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
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : 'determine if the file has non-EXIF embedded metadata',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : 'determine if the file has an icc profile',
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : 'regenerate pixel hashes',
    REGENERATE_FILE_DATA_JOB_BLURHASH: 'regenerate blurhash'
}

# wrapped in triple quotes so I don't have to backslash escape so much
regen_file_enum_to_description_lookup = {
    REGENERATE_FILE_DATA_JOB_FILE_METADATA : '''This regenerates file metadata like resolution and duration, or even filetype (such as mkv->webm), which may have been misparsed in a previous version.''',
    REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL : '''This forces a complete regeneration of the thumbnail from the source file.''',
    REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL : '''This looks for the existing thumbnail, and if it is not the correct resolution or is missing, will regenerate a new one for the source file.''',
    REGENERATE_FILE_DATA_JOB_OTHER_HASHES : '''This regenerates hydrus's store of md5, sha1, and sha512 supplementary hashes, which it can use for various external (usually website) lookups.''',
    REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES : '''Sometimes, a file metadata regeneration will mean a new filetype and thus a new file extension. If the existing, incorrectly named file is in use, it must be copied rather than renamed, and so there is a spare duplicate left over after the operation. This jobs cleans up the duplicate at a later time.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD : '''This checks to see if the file is present in the file system as expected. Use this if you have lost a number of files from your file structure, do not think you can recover them, and need hydrus to re-sync with what it actually has.

Missing files will have their internal file record in the database completely removed. This is just like a file delete except it does not leave a deletion record, so if a normal import ever sees the file again in future, it will not appear to be 'previously deleted', but completely new.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD : '''This checks to see if the file is present in the file system as expected. Use this if you have manually deleted a number of files from your file structure, do not want to get them again, and need hydrus to re-sync with what it actually has. Another example of this situation is restoring an old backed-up database to a newer client_files structure--to catch the database up, you want to teach it that any files missing in the newer structure should be deleted, with a record.

Missing files will have their internal file record processed just like a normal file delete. Normal imports that see these files again in future will consider them as 'previously deleted'.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL : '''This checks to see if the file is present in the file system as expected. If it is not, and it has known post/file URLs, the URLs will be automatically added to a new URL downloader.'

Note that if a files's URL(s) are now 404, or if they point to slightly different new duplicate files (let's say the server resized them or the CDN optimised their file cache), then hydrus will not recognise that the original file has not been 'filled in' and the broken file record will remain. In this case, you would want to run the alternate simpler 'if file is missing, remove record (leave no delete record)' job after this URL job has completely cleared and its downloader page finished, just to catch any lingering strays.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_TRY_URL_ELSE_REMOVE_RECORD : '''THIS IS THE EASY AND QUICK ONE-SHOT WAY TO REPAIR A DATABASE WITH MISSING FILES.

This checks to see if the file is present in the file system as expected. If it is not, and it has known post/file URLs, the URLs will be automatically added to a new URL downloader.

Note that if a files's URL(s) are now 404, or if they point to slightly different new duplicate files (let's say the server resized them or the CDN optimised their file cache), then hydrus will not recognise that the original file has not been 'filled in' and the broken file record will remain. In this case, you would want to run the alternate simpler 'if file is missing, remove record (leave no delete record)' job after this URL job has completely cleared and its downloader page finished, just to catch any lingering strays.

Missing files with no URLs will have their internal file record in the database completely removed. This is just like a file delete except it does not leave a deletion record, so if a normal import ever sees the file again in future, it will not appear to be 'previously deleted', but completely new.

All missing files will have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_LOG_ONLY : '''This checks to see if the file is present in the file system as expected. If it is not, it records the file's hash, tags, and URLs to your database directory, just like the other "missing file" jobs, but makes no other action.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD : '''This does the same check as the 'file is missing' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary.

Missing/Incorrect files will have their internal file record in the database completely removed. This is just like a file delete except it does not leave a deletion record, so if a normal import ever sees the file again in future, it will not appear to be 'previously deleted', but completely new.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL : '''This does the same check as the 'file is missing' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary. If the file is missing/incorrect _and_ has known post/file URLs, the URLs will be automatically added to a new URL downloader.

Note that if a files's URL(s) are now 404, or if they point to slightly different new duplicate files (let's say the server resized them or the CDN optimised their file cache), then hydrus will not recognise that the original file has not been 'filled in' and the broken file record will remain. In this case, you would want to run the alternate simpler 'if file is missing, remove record (leave no delete record)' job after this URL job has completely cleared and its downloader page finished, just to catch any lingering strays.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD : '''This does the same check as the 'file is missing' job, and if the file is where it is expected, it ensures its file content, byte-for-byte, is as expected. This discovers hard drive damage or other external interference. This is a heavy job, so be wary. If the file is missing/incorrect _and_ has known post/file URLs, the URLs will be automatically added to a new URL downloader.

Missing/Incorrect files with no URLs will have their internal file record in the database completely removed. This is just like a file delete except it does not leave a deletion record, so if a normal import ever sees the file again in future, it will not appear to be 'previously deleted', but completely new.

Note that if a files's URL(s) are now 404, or if they point to slightly different new duplicate files (let's say the server resized them or the CDN optimised their file cache), then hydrus will not recognise that the original file has not been 'filled in' and the broken file record will remain. In this case, you would want to run the alternate simpler 'if file is missing, remove record (leave no delete record)' job after this URL job has completely cleared and its downloader page finished, just to catch any lingering strays.

All incorrect files will be exported to a new folder in your database directory for later manual examination if you wish.

All missing/incorrect files will also have their hashes, tags, and URLs exported to a new folder in your database directory for later manual recovery attempts if you wish.''',
    REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_SILENT_DELETE : '''If the file is where it is expected, this ensures its file content, byte-for-byte, is correct. This is a heavy job, so be wary. If the file is incorrect, it will be exported to your database directory along with its known URLs. The client's file record will not be deleted. This is useful if you have a valid backup and need to clear out invalid files from your live db so you can fill in gaps from your backup with a program like FreeFileSync.''',
    REGENERATE_FILE_DATA_JOB_FIX_PERMISSIONS : '''This ensures that files in the file system are readable and writeable. For Linux/macOS users, it specifically sets 644. If you wish to run this job on Linux/macOS, ensure you are first the file owner of all your files.''',
    REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP : '''This checks to see if files should be in the similar files system, and if they are falsely in or falsely out, it will remove their record or queue them up for a search as appropriate. It is useful to repair database damage.''',
    REGENERATE_FILE_DATA_JOB_SIMILAR_FILES_METADATA : '''This forces a regeneration of the file's similar-files 'phashes'. It is not useful unless you know there is missing data to repair.''',
    REGENERATE_FILE_DATA_JOB_FILE_MODIFIED_TIMESTAMP : '''This rechecks the file's modified timestamp and saves it to the database.''',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_TRANSPARENCY : '''This loads the file to see if it has an alpha channel with useful data (the strictness of this test is determined in the options). Only works for images and some animations.''',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_EXIF : '''This loads the file to see if it has EXIF metadata, which can be shown in the media viewer and searched with "system:image has exif".''',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_HUMAN_READABLE_EMBEDDED_METADATA : '''This loads the file to see if it has non-EXIF human-readable embedded metadata, which can be shown in the media viewer and searched with "system:image has human-readable embedded metadata".''',
    REGENERATE_FILE_DATA_JOB_FILE_HAS_ICC_PROFILE : '''This loads the file to see if it has an ICC profile, which is used in "system:has icc profile" search.''',
    REGENERATE_FILE_DATA_JOB_PIXEL_HASH : '''This generates a fast unique identifier for the pixels in a still image, which is used in duplicate pixel searches.''',
    REGENERATE_FILE_DATA_JOB_BLURHASH : '''This generates a very small version of the file's thumbnail that can be used as a placeholder while the thumbnail loads.'''
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

def add_extra_comments_to_job_status( job_status: ClientThreading.JobStatus ):
    
    extra_comments = []
    
    num_thumb_refits = job_status.GetIfHasVariable( 'num_thumb_refits' )
    num_bad_files = job_status.GetIfHasVariable( 'num_bad_files' )
    
    if num_thumb_refits is not None:
        
        extra_comments.append( 'thumbs needing regen: {}'.format( HydrusNumbers.ToHumanInt( num_thumb_refits ) ) )
        
    
    if num_bad_files is not None:
        
        extra_comments.append( 'missing or invalid files: {}'.format( HydrusNumbers.ToHumanInt( num_bad_files ) ) )
        
    
    sub_status_message = '\n'.join( extra_comments )
    
    if len( sub_status_message ) > 0:
        
        job_status.SetStatusText( sub_status_message, 2 )
        
    

class FilesMaintenanceManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller ):
        
        super().__init__( controller, 15 )
        
        self._pubbed_message_about_archive_delete_lock = False
        self._pubbed_message_about_bad_file_record_delete = False
        self._pubbed_message_about_invalid_file_export = False
        
        self._work_tracker = HydrusNetworking.BandwidthTracker()
        
        self._idle_work_rules = HydrusNetworking.BandwidthRules()
        self._active_work_rules = HydrusNetworking.BandwidthRules()
        
        self._ReInitialiseWorkRules()
        
        self._maintenance_lock = threading.Lock()
        
        self._reset_background_event = threading.Event()
        
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'Wake', 'checkbox_manager_inverted' )
        
    
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
        
        if mime in HC.MIMES_THAT_ALWAYS_HAVE_GOOD_RESOLUTION and ( width is None or height is None )    :
            
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
                    
                    if url_class.GetURLType() == HC.URL_TYPE_FILE:
                        
                        add_it = True
                        
                    elif url_class.GetURLType() == HC.URL_TYPE_POST:
                        
                        try:
                            
                            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( url )
                            
                            add_it = can_parse
                            
                        except Exception as e:
                            
                            continue
                            
                        
                    
                
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
                    message += '\n' * 2
                    message += 'To stop spam, this message will only show one time per program boot. The error may happen again, silently.'
                    
                    HydrusData.ShowText( message )
                    
                
            
            if try_redownload:
                
                def qt_add_url( url ):
                    
                    CG.client_controller.gui.ImportURL( url, 'missing files redownloader' )
                    
                
                for url in useful_urls:
                    
                    CG.client_controller.CallBlockingToQtTLW( qt_add_url, url )
                    
                
            
            if delete_record:
                
                leave_deletion_record = job_type == REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_DELETE_RECORD
                
                if media_result.IsPhysicalDeleteLocked():
                    
                    # just send to trash instead
                    # it is KISS to not budge on this. don't try to inbox files and then delete 
                    
                    reason = 'Wanted to delete record during File Integrity check, but file was physical delete locked.'
                    
                    if leave_deletion_record:
                        
                        reason += ' Wanted to leave a deletion record.'
                        
                    else:
                        
                        reason += ' Wanted to leave no deletion record.'
                        
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = reason )
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, content_update )
                    
                    self._controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                    message = f'During file maintenance, failed to physically delete {media_result.GetHash().hex()}!'
                    
                    if leave_deletion_record:
                        
                        message += ' Wanted to leave a deletion record.'
                        
                    else:
                        
                        message += ' Wanted to leave no deletion record.'
                        
                    
                    HydrusData.Print( message )
                    
                    if not self._pubbed_message_about_archive_delete_lock:
                        
                        message = 'During file maintenance, a file was found to be missing or invalid. Unfortunately, it appears to be archived and the archived file delete lock is on, so I cannot fully delete the file record. I have simply sent the file to the trash instead. You should search up recently trashed files and inbox & physically delete them yourself.'
                        message += '\n' * 2
                        message += 'To stop spam, this message will only show one time per program boot. The error may happen again, silently.'
                        
                        HydrusData.ShowText( message )
                        
                        self._pubbed_message_about_archive_delete_lock = True
                        
                    
                else:
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'Record deleted during File Integrity check.' )
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                    
                    self._controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                    HydrusData.Print( f'During file maintenance, physically deleted {media_result.GetHash().hex()}!' )
                    
                    if not leave_deletion_record:
                        
                        HydrusData.Print( f'Clearing delete record for {media_result.GetHash().hex()}!' )
                        
                        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, ( hash, ) )
                        
                        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
                        
                        self._controller.WriteSynchronous( 'content_updates', content_update_package )
                        
                    
                    if not self._pubbed_message_about_bad_file_record_delete:
                        
                        self._pubbed_message_about_bad_file_record_delete = True
                        
                        if leave_deletion_record:
                            
                            m = 'Its file record has been deleted from the database, leaving a deletion record (so it cannot be easily reimported).'
                            
                        else:
                            
                            m = 'Its file record has been removed from the database without leaving a deletion record (so it can be easily reimported).'
                            
                        
                        message = 'During file maintenance, a file was found to be missing or invalid. {} Its file hash and any known URLs have been written to "{}".'.format( m, error_dir )
                        message += '\n' * 2
                        message += 'To stop spam, this message will only show one time per program boot. The error may happen again, silently.'
                        
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
                
                has_exif = HydrusImageMetadata.HasEXIF( raw_pil_image )
                
            except Exception as e:
                
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
            
            has_human_readable_embedded_metadata = ClientFiles.HasHumanReadableEmbeddedMetadata( path, mime )
            
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
                    
                except Exception as e:
                    
                    return None
                    
            else:
                
                try:
                    
                    raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
                    
                except Exception as e:
                    
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
            
            has_transparency = ClientFiles.HasTransparency( path, mime, duration_ms = media_result.GetDurationMS(), num_frames = media_result.GetNumFrames(), resolution = media_result.GetResolution() )
            
            additional_data = has_transparency
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenFileMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        original_mime = media_result.GetMime()
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, original_mime )
            
            ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = HydrusFileHandling.GetFileInfo( path, ok_to_look_for_hydrus_updates = True )
            
            additional_data = ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words )
            
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
            
        
        duration_ms = media_result.GetDurationMS()
        
        if duration_ms is not None:
            
            return None
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
            try:
                
                pixel_hash = HydrusImageHandling.GetImagePixelHash( path, mime )
                
            except Exception as e:
                
                return None
                
            
            additional_data = pixel_hash
            
            return additional_data
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
    
    def _RegenBlurhash( self, media_result ):
        
        if media_result.GetMime() not in HC.MIMES_WITH_THUMBNAILS:
            
            return None
            
        
        try:
            
            thumbnail_path = self._controller.client_files_manager.GetThumbnailPath( media_result )
            
        except HydrusExceptions.FileMissingException as e:
            
            return None
            
        
        try:
            
            thumbnail_mime = HydrusFileHandling.GetThumbnailMime( thumbnail_path )
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( thumbnail_path, thumbnail_mime )
            
            return HydrusBlurhash.GetBlurhashFromNumPy( numpy_image )
            
        except Exception as e:
            
            return None
            
        
    
    
    def _RegenSimilarFilesMetadata( self, media_result ):
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if mime not in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
            
            self._controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', { hash }, REGENERATE_FILE_DATA_JOB_CHECK_SIMILAR_FILES_MEMBERSHIP )
            
            return []
            
        
        try:
            
            path = self._controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            return None
            
        
        perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashes( path, mime )
        
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
                                
                                job_status.SetVariable( 'num_bad_files', num_bad_files )
                                
                            
                        
                    except HydrusExceptions.ShutdownException:
                        
                        # no worries
                        
                        clear_job = False
                        
                        return
                        
                    except IOError as e:
                        
                        HydrusData.PrintException( e )
                        
                        job_status = ClientThreading.JobStatus()
                        
                        message = 'Hey, while performing file maintenance task "{}" on file {}, the client ran into an I/O Error! This could be just some media library moaning about a weird (probably truncated) file, but it could also be a significant hard drive problem. Look at the error yourself. If it looks serious, you should shut the client down and check your hard drive health immediately. Just to be safe, no more file maintenance jobs will be run this program boot, and a full traceback has been written to the log.'.format( regen_file_enum_to_str_lookup[ job_type ], hash.hex() )
                        message += '\n' * 2
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
                        message += '\n' * 2
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
        
        # TODO: When you are feeling good, rework this guy into a set of simpler 'work hard' flags and fold it all into a throttle in the mainloop
        # we can figure out a popup in that mode, but w/e tbh
        
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
            
            status_text = HydrusNumbers.ValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do )
            
            job_status.SetStatusText( status_text )
            
            job_status.SetGauge( num_jobs_done, total_num_jobs_to_do )
            
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
                    
                    try:
                        
                        media_results_to_job_types = { hashes_to_media_results[ hash ] : job_types for ( hash, job_types ) in hashes_to_job_types.items() }
                        
                    except KeyError:
                        
                        message = 'There appears to be a problem with your file metadata store. Some files that were supposed to be undergoing maintenance did not return the correct metadata. Extra information has been printed to the log; please let hydev know.'
                        
                        HydrusData.Print( message )
                        HydrusData.Print( 'Desired hashes:' )
                        HydrusData.Print( '\n'.join( sorted( [ h.hex() for h in hashes ] ) ) )
                        HydrusData.Print( 'Received hashes:' )
                        HydrusData.Print( '\n'.join( sorted( [ h.hex() for h in hashes_to_media_results.keys() ] ) ) )
                        
                        raise Exception( message )
                        
                    
                    with self._lock:
                        
                        self._RunJob( media_results_to_job_types, job_status, job_done_hook = job_done_hook )
                        
                    
                    time.sleep( 0.0001 )
                    
                
            finally:
                
                job_status.SetStatusText( 'done!' )
                
                job_status.DeleteGauge()
                
                job_status.FinishAndDismiss( 5 )
                
                if not work_done:
                    
                    HydrusData.ShowText( 'No file maintenance due!' )
                    
                
                self._controller.pub( 'notify_files_maintenance_done' )
                
            
        
    
    def GetName( self ) -> str:
        
        return 'file maintenance'
        
    
    def _DoMainLoop( self ):
        
        # TODO: locking on CheckShutdown is lax, let's be good and smooth it all out
        
        def wait_on_maintenance():
            
            while True:
                
                self._CheckShutdown()
                
                if self._AbleToDoBackgroundMaintenance() or self._reset_background_event.is_set():
                    
                    break
                    
                
                time.sleep( 1 )
                
            
        
        def should_reset():
            
            if self._reset_background_event.is_set():
                
                self._reset_background_event.clear()
                
                return True
                
            else:
                
                return False
                
            
        
        while True:
            
            self._CheckShutdown()
            
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
                            
                        
                        self._CheckShutdown()
                        
                    finally:
                        
                        self._controller.pub( 'notify_files_maintenance_done' )
                        
                    
                
            
            if did_work:
                
                wake_event = self._wake_from_work_sleep_event
                wait_time = 0.5
                
            else:
                
                wake_event = self._wake_from_idle_sleep_event
                wait_time = 600
                
            
            wake_event.wait( wait_time )
            
            self._wake_from_work_sleep_event.clear()
            self._wake_from_idle_sleep_event.clear()
            
        
    
    def NotifyNewOptions( self ):
        
        with self._lock:
            
            self._ReInitialiseWorkRules()
            
        
    
    def RunJobImmediately( self, media_results, job_type, pub_job_status = True ):
        
        if self._serious_error_encountered and pub_job_status:
            
            HydrusData.ShowText( 'Sorry, the file maintenance system has encountered a serious error and will perform no more jobs this program boot. Please shut the client down and check your hard drive health immediately.' )
            
            return
            
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        total_num_jobs_to_do = len( media_results )
        
        # in a dict so the hook has scope to alter it
        vr_status = {}
        
        vr_status[ 'num_jobs_done' ] = 0
        
        def job_done_hook():
            
            vr_status[ 'num_jobs_done' ] += 1
            
            num_jobs_done = vr_status[ 'num_jobs_done' ]
            
            status_text = '{} - {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_jobs_done, total_num_jobs_to_do ), regen_file_enum_to_str_lookup[ job_type ] )
            
            job_status.SetStatusText( status_text )
            
            job_status.SetGauge( num_jobs_done, total_num_jobs_to_do )
            
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
            
            job_status.DeleteGauge()
            
            job_status.FinishAndDismiss( 5 )
            
            self._controller.pub( 'notify_files_maintenance_done' )
            
        
    
    def ScheduleJob( self, hashes, job_type, time_can_start = 0 ):
        
        with self._lock:
            
            self._controller.Write( 'file_maintenance_add_jobs_hashes', hashes, job_type, time_can_start )
            
        
        self.WakeIfNotWorking()
        
    
    def ScheduleJobHashIds( self, hash_ids, job_type, time_can_start = 0 ):
        
        with self._lock:
            
            self._controller.Write( 'file_maintenance_add_jobs', hash_ids, job_type, time_can_start )
            
        
        self.WakeIfNotWorking()
        
    
