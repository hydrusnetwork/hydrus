from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITopLevelWindows
from . import HydrusExceptions
import wx

def SelectFromList( win, title, choice_tuples, value_to_select = None, sort_tuples = True ):
    
    with ClientGUITopLevelWindows.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditSelectFromListPanel( dlg, choice_tuples, value_to_select = value_to_select, sort_tuples = sort_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.ShowModal() == wx.ID_OK:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException()
            
        
    
