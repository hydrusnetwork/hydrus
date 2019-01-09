from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths
import os
import webbrowser

def DeletePath( path, always_delete_fully = False ):
    
    if HC.options[ 'delete_to_recycle_bin' ] == True and not always_delete_fully:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    
def GetCurrentTempDir():
    
    temp_path_override = GetTempPathOverride()
    
    if temp_path_override is None:
        
        return HydrusPaths.tempfile.gettempdir()
        
    else:
        
        return temp_path_override
        
    
def GetTempDir():
    
    temp_path_override = GetTempPathOverride()
    
    return HydrusPaths.GetTempDir( dir = temp_path_override ) # none means default
    
def GetTempPath( suffix = '' ):
    
    temp_path_override = GetTempPathOverride()
    
    return HydrusPaths.GetTempPath( suffix = suffix, dir = temp_path_override )
    
def LaunchPathInWebBrowser( path ):
    
    LaunchURLInWebBrowser( 'file:///' + path )
    
def LaunchURLInWebBrowser( url ):
    
    web_browser_path = HG.client_controller.new_options.GetNoneableString( 'web_browser_path' )
    
    if web_browser_path is None:
        
        webbrowser.open( url )
        
    else:
        
        HydrusPaths.LaunchFile( url, launch_path = web_browser_path )
        
    
def GetTempPathOverride():
    
    temp_path_override = HG.client_controller.new_options.GetNoneableString( 'temp_path_override' )
    
    if temp_path_override is not None and not os.path.exists( temp_path_override ):
        
        HydrusData.ShowText( 'The temp path ' + temp_path_override + ' does not exist! Please either create it or change the option!' )
        
        return None
        
    
    return temp_path_override
    
