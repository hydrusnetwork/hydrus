import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui.executables import ClientGUIExecutableActions

def OpenDocumentation( win: QW.QWidget, documentation_path: str ):
    
    local_path = os.path.join( HC.HELP_DIR, documentation_path )
    remote_url = "/".join( ( HC.REMOTE_HELP.rstrip( '/' ), documentation_path.lstrip( '/' ) ) ) 
    
    local_launch_path = local_path
    
    if "#" in local_path:
        
        local_path = local_path[ : local_path.find( '#' ) ]
        
    
    if os.path.isfile( local_path ):
        
        ClientGUIExecutableActions.OpenExternallyPathAsURL( win, local_launch_path )
        
    else:
        
        HydrusData.Print( f'Was asked to open "{documentation_path}", which appeared to be "{local_path}" locally, but it did not seem to exist!' )
        
        message = 'You do not have a local help! Are you running from source? Would you like to open the online help or see a guide on how to build your own?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'open online help', 0 ) )
        yes_tuples.append( ( 'open how to build guide', 1 ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( win, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if result == 0:
            
            url = remote_url
            
        else:
            
            url = '/'.join( ( HC.REMOTE_HELP.rstrip( '/' ), HC.DOCUMENTATION_ABOUT_DOCS.lstrip( '/' ) ) )
            
        
        ClientGUIExecutableActions.OpenExternallyURLDefault( win, url )
        
    
