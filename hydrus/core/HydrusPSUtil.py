import traceback

PSUTIL_OK = True
PSUTIL_MODULE_NOT_FOUND = False
PSUTIL_IMPORT_ERROR = 'psutil seems fine!'

psutil_sdiskpart = None

try:
    
    import psutil
    
except Exception as e:
    
    print( 'psutil failed to import! The program will boot, but several important capabilities will be disabled!' )
    
    PSUTIL_OK = False
    PSUTIL_MODULE_NOT_FOUND = isinstance( e, ModuleNotFoundError )
    PSUTIL_IMPORT_ERROR = traceback.format_exc()
    
