import ClientConstants as CC
import ClientDefaults
import ClientGUIDialogs
import ClientGUIScrolledPanelsManagement
import ClientGUITopLevelWindows
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest
import wx
import HydrusGlobals

def HitButton( button ): wx.PostEvent( button, wx.CommandEvent( wx.EVT_BUTTON.typeId, button.GetId() ) )

def HitCancelButton( window ): wx.PostEvent( window, wx.CommandEvent( wx.EVT_BUTTON.typeId, wx.ID_CANCEL ) )

def HitOKButton( window ): wx.PostEvent( window, wx.CommandEvent( wx.EVT_BUTTON.typeId, wx.ID_OK ) )

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
    
    event = wx.KeyEvent( wx.EVT_KEY_DOWN.typeId )
    
    event.m_keyCode = key
    event.SetEventObject( window )
    event.SetId( window.GetId() )
    
    wx.PostEvent( window, event )
    
class TestDBDialogs( unittest.TestCase ):
    
    def test_dialog_select_booru( self ):
        
        HydrusGlobals.test_controller.SetRead( 'remote_boorus', ClientDefaults.GetDefaultBoorus() )
        
        with ClientGUIDialogs.DialogSelectBooru( None ) as dlg:
            
            HitCancelButton( dlg )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
    
    def test_dialog_manage_subs( self ):
        
        HydrusGlobals.test_controller.SetRead( 'serialisable_named', [] )
        
        title = 'subs test'
        frame_key = 'regular_dialog'
        
        with ClientGUITopLevelWindows.DialogManage( None, title, frame_key ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageSubscriptionsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            wx.CallAfter( panel.Add )
            
            wx.CallLater( 2000, OKChildDialog, panel )
            
            wx.CallLater( 4000, HitCancelButton, dlg )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
    
class TestNonDBDialogs( unittest.TestCase ):
    
    def test_dialog_choose_new_service_method( self ):
        
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
            
        
    
    def test_dialog_finish_filtering( self ):
        
        with ClientGUIDialogs.DialogFinishFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._back )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
        with ClientGUIDialogs.DialogFinishFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._commit )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_YES )
            
        
        with ClientGUIDialogs.DialogFinishFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._forget )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_NO )
            
        
    
    def test_select_from_list_of_strings( self ):
        
        list_of_tuples = [ ( 'a', 123 ), ( 'b', 456 ), ( 'c', 789 ) ]
        
        with ClientGUIDialogs.DialogSelectFromList( None, 'select from a list of strings', list_of_tuples ) as dlg:
            
            wx.CallLater( 500, dlg._list.Select, 1 )
            wx.CallLater( 1000, PressKey, dlg._list, wx.WXK_RETURN )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_OK )
            
            value = dlg.GetChoice()
            
            self.assertEqual( value, 456 )
            
        
    
    def test_dialog_yes_no( self ):
        
        with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
            
            HitButton( dlg._yes )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_YES )
            
        
        with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
            
            HitButton( dlg._no )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_NO )
            
        
    
