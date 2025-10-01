import os

from hydrus.core import HydrusConstants as HC

#

try:
    
    # obviously change this if we ever drop yaml from the requirements lol
    import yaml
    
except Exception as e:
    
    message = 'Hey, hydrus could not see one of the third-party libraries it needs. If you have a venv, this usually means the venv did not install correctly or was not activated before program start. It can also happen if the OS updates and a new python version is introduced (invalidating the existing venv). If you are running from source with a venv, please try rebuilding it (just run the "setup_venv" script again).'
    message += '\n\n'
    message += 'If you are running from source but not with my "setup_venv" venv, then your python environment did not get everything it needed from the hydrus requirements.txt. You or the respective hydrus package manager needs to fix something.'
    message += '\n\n'
    message += 'If you are running a built release, not from source, then the build did not include everything it needed or you have a dll problem. If it is not a crazy anti-virus problem, hydev probably needs to know about this.'
    
    raise Exception( message ) from e
    

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
        
    

