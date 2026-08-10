from hydrus.core import HydrusConstants as HC

PARAM_TYPE_FILE_PATH = 0
PARAM_TYPE_FILE_LOCAL_PATH_URI = 1
PARAM_TYPE_URL = 2
PARAM_TYPE_FILE_PATHS = 3
PARAM_TYPE_FILE_LOCAL_PATH_URIS = 4

param_types_to_strs = {
    PARAM_TYPE_FILE_PATH: 'file path',
    PARAM_TYPE_FILE_PATHS: 'file paths',
    PARAM_TYPE_FILE_LOCAL_PATH_URI: 'file URI',
    PARAM_TYPE_FILE_LOCAL_PATH_URIS: 'file URIs',
    PARAM_TYPE_URL: 'URL',
}

param_types_to_example_values = {
    PARAM_TYPE_URL : [ 'https://somebooru.org/post/123456' ]
}

if HC.PLATFORM_WINDOWS:
    
    param_types_to_example_values[ PARAM_TYPE_FILE_PATH ] = [ 'E:\\Hydrus_Files\\f89\\89...jpg' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_PATHS ] = [ 'E:\\Hydrus_Files\\f88\\88...mp3', 'E:\\Hydrus_Files\\f12\\12...mp3', 'E:\\Hydrus_Files\\ffe\\fe...mp3' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URI ] = [ 'file://E:/Hydrus_Files/f89/89...jpg' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URIS ] = [ 'file://E:/Hydrus_Files/f88/88...mp3', 'file://E:/Hydrus_Files/f12/12...mp3', 'file://E:/Hydrus_Files/ffe/fe...mp3' ]
    
else:
    
    param_types_to_example_values[ PARAM_TYPE_FILE_PATH ] = [ '/home/me/hydrus_files/f89/89...jpg' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_PATHS ] = [ '/home/me/hydrus_files/f88/88...mp3', '/home/me/hydrus_files/f12/12...mp3', '/home/me/hydrus_files/ffe/fe...mp3' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URI ] = [ 'file:///home/me/hydrus_files/f89/89...jpg' ]
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URIS ] = [ 'file:///home/me/hydrus_files/f88/88...mp3', 'file:///home/me/hydrus_files/f12/12...mp3', 'file:///home/me/hydrus_files/ffe/fe...mp3' ]
    

EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE = 1
EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL = 2
EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES = 1

executable_pipeline_types_to_input_params = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : [
        PARAM_TYPE_FILE_PATH,
        PARAM_TYPE_FILE_LOCAL_PATH_URI,
    ],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_MUPLITPLE_FILES : [
        PARAM_TYPE_FILE_PATHS,
        PARAM_TYPE_FILE_LOCAL_PATH_URIS,
    ],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : [
        PARAM_TYPE_URL,
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
