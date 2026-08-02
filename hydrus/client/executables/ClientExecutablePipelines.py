from hydrus.core import HydrusConstants as HC

PARAM_TYPE_FILE_PATH = 0
PARAM_TYPE_FILE_LOCAL_PATH_URI = 1
PARAM_TYPE_URL = 2

param_types_to_strs = {
    PARAM_TYPE_FILE_PATH: 'file path',
    PARAM_TYPE_FILE_LOCAL_PATH_URI: 'file URI',
    PARAM_TYPE_URL: 'URL',
}

param_types_to_example_values = {
    PARAM_TYPE_URL : 'https://somebooru.org/post/123456'
}

if HC.PLATFORM_WINDOWS:
    
    param_types_to_example_values[ PARAM_TYPE_FILE_PATH ] = 'E:\\Hydrus_Files\\f89\\89...jpg'
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URI ] = 'file://E:/Hydrus_Files/f89/89...jpg'
    
else:
    
    param_types_to_example_values[ PARAM_TYPE_FILE_PATH ] = '/home/me/hydrus_files/f89/89...jpg'
    param_types_to_example_values[ PARAM_TYPE_FILE_LOCAL_PATH_URI ] = 'file:///home/me/hydrus_files/f89/89...jpg'
    

EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE = 1
EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL = 2

executable_pipeline_types_to_input_params = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : [
        PARAM_TYPE_FILE_PATH,
        PARAM_TYPE_FILE_LOCAL_PATH_URI,
    ],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : [
        PARAM_TYPE_URL,
    ],
}

executable_pipeline_types_to_output_params = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : [],
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : [],
}

executable_pipeline_types_to_strs = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : 'open externally (single file)',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : 'open URL (single URL)',
}

executable_pipeline_types_to_desc_strs = {
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE : 'This tells the client how to open a file in another program.',
    EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL : 'This tells the client how to open a URL in another program.',
}
