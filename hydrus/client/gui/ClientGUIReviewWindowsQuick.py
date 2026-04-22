from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsSelectFromList

def OpenListButtons( win, title, choice_tuples, message = '' ):
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, title, frame_key = 'quick_select_dialog' )
    
    panel = ClientGUIScrolledPanelsSelectFromList.ReviewSelectFromListButtonsPanel( frame, choice_tuples, message = message )
    
    frame.SetPanel( panel )
    
