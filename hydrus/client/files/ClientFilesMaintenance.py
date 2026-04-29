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
