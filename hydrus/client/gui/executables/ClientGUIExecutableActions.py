from qtpy import QtWidgets as QW

from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableActions
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.media import ClientMediaResult

def OpenExternallySingleFileDefault( win: QW.QWidget, media_result: ClientMediaResult.MediaResult ) -> bool:
    
    mime = media_result.GetMime()
    
    ids_and_names = CG.client_controller.new_options.GetLaunchFileExecutableIdsAndNames( mime )
    
    if len( ids_and_names ) == 0:
        
        id_and_name = CG.client_controller.executable_manager.GetOSLaunchFileCallable().GetIdAndName()
        
    else:
        
        id_and_name = ids_and_names[0]
        
    
    return OpenExternallySingleFile( win, id_and_name, media_result )
    

def OpenExternallySingleFile( win: QW.QWidget, id_and_name: HydrusSerialisable.IdAndName, media_result: ClientMediaResult.MediaResult ) -> bool:
    
    try:
        
        ClientExecutableActions.OpenExternallySingleFile( CG.client_controller.executable_manager, id_and_name, media_result )
        
        return True
        
    except Exception as e:
        
        ClientGUIDialogsMessage.ShowInformation( win, f'Sorry, could not open that file: {e}' )
        
        return False
        
    

def OpenExternallyMediaAsURL( win: QW.QWidget, media_result: ClientMediaResult.MediaResult ) -> bool:
    
    if not media_result.GetLocationsManager().IsLocal():
        
        ClientGUIDialogsMessage.ShowInformation( win, f'That media is not local to your client!' )
        
        return False
        
    
    hash = media_result.GetHash()
    mime = media_result.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    return OpenExternallyPathAsURL( win, path )
    

def OpenExternallyPathAsURL( win: QW.QWidget, path: str ) -> bool:
    
    return OpenExternallyURLDefault( win, 'file:///' + path )
    

def OpenExternallyURLDefault( win: QW.QWidget, url: str ) -> bool:
    
    ids_and_names = CG.client_controller.new_options.GetLaunchURLExecutableIdsAndNames()
    
    if len( ids_and_names ) == 0:
        
        id_and_name = CG.client_controller.executable_manager.GetOSLaunchURLCallable().GetIdAndName()
        
    else:
        
        id_and_name = ids_and_names[0]
        
    
    return OpenExternallyURL( win, id_and_name, url )
    

def OpenExternallyURL( win: QW.QWidget, id_and_name: HydrusSerialisable.IdAndName, url: str ):
    
    try:
        
        ClientExecutableActions.OpenExternallyURL( CG.client_controller.executable_manager, id_and_name, url )
        
        return True
        
    except Exception as e:
        
        ClientGUIDialogsMessage.ShowInformation( win, f'Sorry, could not open that URL: {e}' )
        
        return False
        
    
