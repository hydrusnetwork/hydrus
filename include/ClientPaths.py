import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusPaths
import webbrowser

def DeletePath( path ):
    
    if HC.options[ 'delete_to_recycle_bin' ] == True:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    
def GetCurrentTempDir():
    
    temp_path_override = HG.client_controller.new_options.GetNoneableString( 'temp_path_override' )
    
    if temp_path_override is None:
        
        return HydrusPaths.tempfile.gettempdir()
        
    else:
        
        return temp_path_override
        
    
def GetTempDir():
    
    temp_path_override = HG.client_controller.new_options.GetNoneableString( 'temp_path_override' )
    
    return HydrusPaths.GetTempDir( dir = temp_path_override ) # none means default
    
def GetTempPath( suffix = '' ):
    
    temp_path_override = HG.client_controller.new_options.GetNoneableString( 'temp_path_override' )
    
    return HydrusPaths.GetTempPath( suffix = suffix, dir = temp_path_override )
    
def LaunchPathInWebBrowser( path ):
    
    LaunchURLInWebBrowser( 'file:///' + path )
    
def LaunchURLInWebBrowser( url ):
    
    web_browser_path = HG.client_controller.new_options.GetNoneableString( 'web_browser_path' )
    
    if web_browser_path is None:
        
        webbrowser.open( url )
        
    else:
        
        HydrusPaths.LaunchFile( url, launch_path = web_browser_path )
        
    
