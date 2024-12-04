from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsSelectFromList

def OpenListButtons( win, title, choice_tuples, message = '' ):
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, title, frame_key = 'regular_center_dialog' )
    
    panel = ClientGUIScrolledPanelsSelectFromList.ReviewSelectFromListButtonsPanel( frame, choice_tuples, message = message )
    
    frame.SetPanel( panel )
    
