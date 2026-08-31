import collections.abc
import os
import shlex
import threading
import webbrowser

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core.processes import HydrusSubprocess

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
        
    

def GetDefaultLaunchPath():
    
    if HC.PLATFORM_WINDOWS:
        
        return 'windows is called directly'
        
    elif HC.PLATFORM_MACOS:
        
        return 'open "%path%"'
        
    elif HC.PLATFORM_LINUX:
        
        return 'xdg-open "%path%"'
        
    elif HC.PLATFORM_HAIKU:
        
        return 'open "%path%"'
        
    

def LaunchFileDefault( path, mime ):
    
    launch_paths = CG.client_controller.new_options.GetOpenExternallyLaunchPaths( mime )
    
    LaunchFile( path, launch_paths[0] )
    

def LaunchFile( path, open_externally_launch_path: str | None ):
    
    # TODO: This is temporary and will instead soon get an ExecutableCall, and/or the ExecutableManager will handle it itself
    
    def do_it( launch_path ):
        
        if HC.PLATFORM_WINDOWS and launch_path is None:
            
            os.startfile( path )
            
        else:
            
            if launch_path is None:
                
                launch_path = GetDefaultLaunchPath()
                
            
            complete_launch_path = launch_path.replace( '%path%', path )
            
            if HC.PLATFORM_WINDOWS:
                
                cmd = complete_launch_path
                
            else:
                
                cmd = shlex.split( complete_launch_path )
                
            
            if HG.subprocess_report_mode:
                
                message = 'Attempting to launch "' + path + '" using command ' + repr( cmd ) + '.'
                
                HydrusData.ShowText( message )
                
            
            try:
                
                HydrusData.CheckProgramIsNotShuttingDown()
                
                HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = True, hide_terminal = False )
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not launch a file! Command used was:' + '\n' + str( cmd ) )
                
                HydrusData.ShowException( e )
                
            
        
    
    thread = threading.Thread( target = do_it, args = ( open_externally_launch_path, ) )
    
    thread.daemon = True
    
    thread.start()
    

def LaunchPathInWebBrowser( path ):
    
    LaunchURLInDefaultWebBrowser( 'file:///' + path )
    

def LaunchURLInDefaultWebBrowser( url ):
    
    web_browser_launch_paths = CG.client_controller.new_options.GetWebBrowserLaunchPaths()
    
    LaunchURLInWebBrowser( url, web_browser_launch_paths[0] )
    

def LaunchURLInWebBrowser( url, web_browser_launch_path: str | None ):
    
    # TODO: This is temporary and will instead soon get an ExecutableCall, and/or the ExecutableManager will handle it itself
    
    def do_it():
        
        if web_browser_launch_path is None:
            
            webbrowser.open( url )
            
        else:
            
            complete_launch_path = web_browser_launch_path.replace( '%url%', url )
            
            if HC.PLATFORM_WINDOWS:
                
                cmd = complete_launch_path
                
            else:
                
                cmd = shlex.split( complete_launch_path )
                
            
            if HG.subprocess_report_mode:
                
                message = 'Attempting to launch "' + url + '" using command ' + repr( cmd ) + '.'
                
                HydrusData.ShowText( message )
                
            
            try:
                
                HydrusData.CheckProgramIsNotShuttingDown()
                
                HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = True, hide_terminal = False )
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not launch an URL! Command used was:' + '\n' + str( cmd ) )
                
                HydrusData.ShowException( e )
                
            
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    

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
        
    
