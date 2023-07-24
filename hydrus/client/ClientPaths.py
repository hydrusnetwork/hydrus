import webbrowser
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths

from hydrus.client.gui import ClientGUIDialogsQuick

def DeletePath( path, always_delete_fully = False ):
    
    delete_to_recycle_bin = HC.options[ 'delete_to_recycle_bin' ]
    
    if delete_to_recycle_bin and not always_delete_fully:
        
        HydrusPaths.RecyclePath( path )
        
    else:
        
        HydrusPaths.DeletePath( path )
        
    
def LaunchPathInWebBrowser( path ):
    
    LaunchURLInWebBrowser( 'file:///' + path )
    
def LaunchURLInWebBrowser( url ):
    
    web_browser_path = HG.client_controller.new_options.GetNoneableString( 'web_browser_path' )
    
    if web_browser_path is None:
        
        webbrowser.open( url )
        
    else:
        
        HydrusPaths.LaunchFile( url, launch_path = web_browser_path )
        
    
def OpenDocumentation( documentation_path : str ):

    local = os.path.join( HC.HELP_DIR, documentation_path )
    remote = "/".join((HC.REMOTE_HELP.rstrip("/"), documentation_path.lstrip("/"))) 

    local_open = local

    if "#" in local:

        local = local[ :local.find("#") ]

    if os.path.isfile( local ):

        LaunchPathInWebBrowser( local_open )

    else:

        remote = ClientGUIDialogsQuick.ConfirmOpenOnlineHelpIfLocalDoesntExist( None, remote )

        if remote is None:

            return

        LaunchURLInWebBrowser( remote )
