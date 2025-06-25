import os

from hydrus.core import HydrusConstants as HC

ORIGINAL_PATH = None

def AddBaseDirToEnvPath():
    
    # doing it separate and early here is a thing to get mpv (and others) working with a frozen build, helping load the dll/so from the base dir using ctypes
    
    if 'PATH' in os.environ:
        
        global ORIGINAL_PATH
        
        ORIGINAL_PATH = os.environ[ 'PATH' ]
        
        os.environ[ 'PATH' ] = HC.BASE_DIR + os.pathsep + os.environ[ 'PATH' ]
        
    

def DoPreImportEnvWork():
    
    try:
        
        # we need to do this before the first import cv2, so we'll stick it here
        
        import os
        
        os.environ[ 'OPENCV_LOG_LEVEL' ] = 'ERROR'
        os.environ[ 'OPENCV_FFMPEG_LEVEL' ] = '16' # AV_LOG_ERROR
        
    except:
        
        print( 'Could not set OpenCV logging envs.' )
        
    

