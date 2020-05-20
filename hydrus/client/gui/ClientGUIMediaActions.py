from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMedia
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

def EditFileNotes( win: QW.QWidget, media: ClientMedia.Media ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
