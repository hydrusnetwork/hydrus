from hydrus.core import HydrusConstants as HC

PARAMETER_TYPE_FILE_PATH = 0
PARAMETER_TYPE_FILE_LOCAL_PATH_URI = 1
PARAMETER_TYPE_URL = 2
PARAMETER_TYPE_FILE_PATHS = 3
PARAMETER_TYPE_FILE_LOCAL_PATH_URIS = 4
PARAMETER_TYPE_FILE_HASH = 5
PARAMETER_TYPE_FILE_HASH_ID = 6

parameter_types_to_strs = {
    PARAMETER_TYPE_FILE_PATH: 'file path',
    PARAMETER_TYPE_FILE_PATHS: 'file paths',
    PARAMETER_TYPE_FILE_LOCAL_PATH_URI: 'file URI',
    PARAMETER_TYPE_FILE_LOCAL_PATH_URIS: 'file URIs',
    PARAMETER_TYPE_URL: 'URL',
    PARAMETER_TYPE_FILE_HASH : 'file hash (sha256)',
    PARAMETER_TYPE_FILE_HASH_ID : 'file id',
}

parameter_types_to_example_values = {
    PARAMETER_TYPE_URL : [ 'https://somebooru.org/post/123456' ],
    PARAMETER_TYPE_FILE_HASH : [ '896aba496da94160475f7ac956beace2083733b5a2972ffd3053dd3d0ad1d36b' ],
    PARAMETER_TYPE_FILE_HASH_ID : [ '117621484' ]
}

if HC.PLATFORM_WINDOWS:
    
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_PATH ] = [ 'E:\\Hydrus_Files\\f89\\89...jpg' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_PATHS ] = [ 'E:\\Hydrus_Files\\f88\\88...mp3', 'E:\\Hydrus_Files\\f12\\12...mp3', 'E:\\Hydrus_Files\\ffe\\fe...mp3' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_LOCAL_PATH_URI ] = [ 'file://E:/Hydrus_Files/f89/89...jpg' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_LOCAL_PATH_URIS ] = [ 'file://E:/Hydrus_Files/f88/88...mp3', 'file://E:/Hydrus_Files/f12/12...mp3', 'file://E:/Hydrus_Files/ffe/fe...mp3' ]
    
else:
    
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_PATH ] = [ '/home/me/hydrus_files/f89/89...jpg' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_PATHS ] = [ '/home/me/hydrus_files/f88/88...mp3', '/home/me/hydrus_files/f12/12...mp3', '/home/me/hydrus_files/ffe/fe...mp3' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_LOCAL_PATH_URI ] = [ 'file:///home/me/hydrus_files/f89/89...jpg' ]
    parameter_types_to_example_values[ PARAMETER_TYPE_FILE_LOCAL_PATH_URIS ] = [ 'file:///home/me/hydrus_files/f88/88...mp3', 'file:///home/me/hydrus_files/f12/12...mp3', 'file:///home/me/hydrus_files/ffe/fe...mp3' ]
    

parameter_types_to_default_token_names = {
    PARAMETER_TYPE_FILE_PATH: '%path%',
    PARAMETER_TYPE_FILE_PATHS: '%paths%',
    PARAMETER_TYPE_FILE_LOCAL_PATH_URI: '%path_uri%',
    PARAMETER_TYPE_FILE_LOCAL_PATH_URIS: '%paths_uri%',
    PARAMETER_TYPE_URL: '%url%',
    PARAMETER_TYPE_FILE_HASH: '%hash%',
    PARAMETER_TYPE_FILE_HASH_ID: '%file_id%',
}

EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE = 1
EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL = 2
EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES = 3

executable_pipeline_types_to_input_params = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : [
        PARAMETER_TYPE_FILE_PATH,
        PARAMETER_TYPE_FILE_LOCAL_PATH_URI,
        PARAMETER_TYPE_FILE_HASH,
        PARAMETER_TYPE_FILE_HASH_ID,
    ],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES : [
        PARAMETER_TYPE_FILE_PATHS,
        PARAMETER_TYPE_FILE_LOCAL_PATH_URIS,
    ],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : [
        PARAMETER_TYPE_URL,
    ],
}

executable_pipeline_types_to_output_params = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : [],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES : [],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : [],
}

executable_pipeline_types_to_strs = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : 'open externally (single file)',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES : 'open externally (multiple files)',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : 'open URL (single URL)',
}

executable_pipeline_types_to_desc_strs = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : 'This tells the client how to open a file in another program.',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES : 'This tells the client how to open a "playlist" of multiple files in another program.',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : 'This tells the client how to open a URL in another program.',
}
