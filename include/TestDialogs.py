from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientGUIDialogs
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsManagement
from . import ClientGUITopLevelWindows
from . import ClientThreading
import collections
from . import HydrusConstants as HC
import os
import unittest
import wx
from . import HydrusGlobals as HG

def HitButton( button ):
    
    wx.QueueEvent( button, wx.CommandEvent( commandEventType = wx.EVT_BUTTON.typeId, id = button.GetId() ) )
    
def HitCancelButton( window ):
    
    wx.QueueEvent( window, wx.CommandEvent( commandEventType = wx.EVT_BUTTON.typeId, id = wx.ID_CANCEL ) )
    
def HitOKButton( window ):
    
    wx.QueueEvent( window, wx.CommandEvent( commandEventType = wx.EVT_BUTTON.typeId, id = wx.ID_OK ) )
    
def CancelChildDialog( window ):
    
    children = window.GetChildren()
    
    for child in children:
        
        if isinstance( child, wx.Dialog ):
            
            HitCancelButton( child )
            
        

def OKChildDialog( window ):
    
    children = window.GetChildren()
    
    for child in children:
        
        if isinstance( child, wx.Dialog ):
            
            HitOKButton( child )
            
        
    
def PressKey( window, key ):
    
    window.SetFocus()
    
    uias = wx.UIActionSimulator()
    
    uias.Char( key )
    
class TestDBDialogs( unittest.TestCase ):
    
    def test_dialog_manage_subs( self ):
        
        def wx_code():
            
            title = 'subs test'
            
            with ClientGUITopLevelWindows.DialogEdit( None, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditSubscriptionsPanel( dlg, [] )
                
                dlg.SetPanel( panel )
                
                HG.test_controller.CallLaterWXSafe( dlg, 2, panel.Add )
                
                HG.test_controller.CallLaterWXSafe( dlg, 4, OKChildDialog, panel )
                
                HG.test_controller.CallLaterWXSafe( dlg, 6, HitCancelButton, dlg )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_CANCEL )
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
class TestNonDBDialogs( unittest.TestCase ):
    
    def test_dialog_choose_new_service_method( self ):
        
        def wx_code():
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HitButton( dlg._register )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_OK )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, True )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HitButton( dlg._setup )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_OK )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, False )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HitCancelButton( dlg )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_CANCEL )
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
    def test_dialog_finish_filtering( self ):
        
        def wx_code():
            
            with ClientGUIDialogs.DialogFinishFiltering( None, 'keep 3 files and delete 5 files?' ) as dlg:
                
                HitButton( dlg._back )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_CANCEL )
                
            
            with ClientGUIDialogs.DialogFinishFiltering( None, 'keep 3 files and delete 5 files?' ) as dlg:
                
                HitButton( dlg._commit )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_YES )
                
            
            with ClientGUIDialogs.DialogFinishFiltering( None, 'keep 3 files and delete 5 files?' ) as dlg:
                
                HitButton( dlg._forget )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_NO )
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
    def test_dialog_yes_no( self ):
        
        def wx_code():
            
            with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
                
                HitButton( dlg._yes )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_YES )
                
            
            with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
                
                HitButton( dlg._no )
                
                result = dlg.ShowModal()
                
                self.assertEqual( result, wx.ID_NO )
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
