import collections.abc
import webbrowser

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusPaths

from hydrus.client import ClientGlobals as CG

try:
    
    from showinfm import show_in_file_manager
    
    SHOW_IN_FILE_MANAGER_OK = True
    
except Exception as e:
    
    SHOW_IN_FILE_MANAGER_OK = False
    

if HC.PLATFORM_WINDOWS:
    
    try:
        
        from hydrus.client import ClientWindowsIntegration
        
    except Exception as e:
        
        HydrusData.Print( 'Could not import ClientWindowsIntegration--maybe you need PyWin32 in your venv?' )
        HydrusData.PrintException( e, do_wait = False )
        
    

CAN_OPEN_FILE_LOCATION = HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS or ( HC.PLATFORM_LINUX and SHOW_IN_FILE_MANAGER_OK )

def DeletePath( path, always_delete_fully = False ):
    
    delete_to_recycle_bin = HC.options[ 'delete_to_recycle_bin' ]
    
    if delete_to_recycle_bin and not always_delete_fully:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    

def LaunchPathInWebBrowser( path ):
    
    LaunchURLInWebBrowser( 'file:///' + path )
    

def LaunchURLInWebBrowser( url ):
    
    web_browser_path = CG.client_controller.new_options.GetNoneableString( 'web_browser_path' )
    
    if web_browser_path is None:
        
        webbrowser.open( url )
        
    else:
        
        HydrusPaths.LaunchFile( url, launch_path = web_browser_path )
        
    

def OpenFileLocation( path: str ):
    
    if SHOW_IN_FILE_MANAGER_OK:
        
        show_in_file_manager( path )
                
    else:
        
        HydrusPaths.OpenFileLocation( path )
        
    

def OpenFileLocations( paths: collections.abc.Sequence[str] ):
    
    if SHOW_IN_FILE_MANAGER_OK:
        
        show_in_file_manager( paths )
        
    else:
        
        for path in paths:
        
            HydrusPaths.OpenFileLocation( path )
            
    

def OpenNativeFileProperties( path: str ):
    
    if HC.PLATFORM_WINDOWS:
        
        ClientWindowsIntegration.OpenFileProperties( path )
        
    

def OpenFileWithDialog( path: str ):
    
    if HC.PLATFORM_WINDOWS:
        
        ClientWindowsIntegration.OpenFileWith( path )
        
    
