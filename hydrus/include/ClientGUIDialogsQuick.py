from . import ClientGUIScrolledPanelsButtonQuestions
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITopLevelWindows
from . import HydrusExceptions
from . import HydrusGlobals as HG
import wx

def GetDeleteFilesJobs( win, media, default_reason, suggested_file_service_key = None ):
    
    title = 'Delete files?'
    
    with ClientGUITopLevelWindows.DialogEdit( win, title, frame_key = 'regular_center_dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditDeleteFilesPanel( dlg, media, default_reason, suggested_file_service_key = suggested_file_service_key )
        
        dlg.SetPanel( panel )
        
        if panel.QuestionIsAlreadyResolved():
            
            ( involves_physical_delete, jobs ) = panel.GetValue()
            
            return ( involves_physical_delete, jobs )
            
        
        if dlg.ShowModal() == wx.ID_OK:
            
            ( involves_physical_delete, jobs ) = panel.GetValue()
            
            return ( involves_physical_delete, jobs )
            
        else:
            
            raise HydrusExceptions.CancelledException()
            
        
    
def GetFinishFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionFinishFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        return dlg.ShowModal()
        
    
def GetInterstitialFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionCommitInterstitialFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        return dlg.ShowModal()
        
    
def GetYesNo( win, message, title = 'Are you sure?', yes_label = 'yes', no_label = 'no', auto_yes_time = None ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionYesNoPanel( dlg, message, yes_label = yes_label, no_label = no_label )
        
        dlg.SetPanel( panel )
        
        if auto_yes_time is None:
            
            return dlg.ShowModal()
            
        else:
            
            job = HG.client_controller.CallLaterWXSafe( dlg, auto_yes_time, dlg.EndModal, wx.ID_YES )
            
            try:
                
                return dlg.ShowModal()
                
            finally:
                
                job.Cancel()
                
            
        
    
def SelectFromList( win, title, choice_tuples, value_to_select = None, sort_tuples = True ):
    
    with ClientGUITopLevelWindows.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditSelectFromListPanel( dlg, choice_tuples, value_to_select = value_to_select, sort_tuples = sort_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.ShowModal() == wx.ID_OK:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException()
            
        
    
def SelectFromListButtons( win, title, choice_tuples ):
    
    with ClientGUITopLevelWindows.DialogEdit( win, title, hide_buttons = True ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditSelectFromListButtonsPanel( dlg, choice_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.ShowModal() == wx.ID_OK:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException()
            
        
    
