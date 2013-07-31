import ClientConstants as CC
import ClientGUIDialogs
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest
import wx

def HitButton( button ): wx.PostEvent( button, wx.CommandEvent( wx.EVT_BUTTON.typeId, button.GetId() ) )

def PressKey( window, key ):
    
    event = wx.KeyEvent( wx.EVT_KEY_DOWN.typeId )
    
    event.m_keyCode = key
    event.SetEventObject( window )
    event.SetId( window.GetId() )
    
    wx.PostEvent( window, event )
    
class TestDBDialogs( unittest.TestCase ):
    
    def test_dialog_select_booru( self ):
        
        HC.app.SetRead( 'boorus', CC.DEFAULT_BOORUS )
        
        with ClientGUIDialogs.DialogSelectBooru( None ) as dlg:
            
            HitButton( dlg._dialog_cancel_button )
            
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
            
            HitButton( dlg._dialog_cancel_button )
            
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
            
        
    
    def test_dialog_finish_rating_filtering( self ):
        
        with ClientGUIDialogs.DialogFinishRatingFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._back )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
        with ClientGUIDialogs.DialogFinishRatingFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._commit )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_YES )
            
        
        with ClientGUIDialogs.DialogFinishRatingFiltering( None, 3, 5 ) as dlg:
            
            HitButton( dlg._forget )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_NO )
            
        
    
    def test_dialog_first_start( self ):
        
        with ClientGUIDialogs.DialogFirstStart( None ) as dlg:
            
            HitButton( dlg._dialog_cancel_button )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
        with ClientGUIDialogs.DialogFirstStart( None ) as dlg:
            
            HitButton( dlg._ok )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_OK )
            
        
    
    def test_dialog_message( self ):
        
        with ClientGUIDialogs.DialogMessage( None, 'hello' ) as dlg:
            
            HitButton( dlg._ok )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
    
    def test_select_from_list_of_strings( self ):
        
        with ClientGUIDialogs.DialogSelectFromListOfStrings( None, 'select from a list of strings', [ 'a', 'b', 'c' ] ) as dlg:
            
            wx.CallAfter( dlg._strings.Select, 0 )
            PressKey( dlg._strings, wx.WXK_SPACE )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_OK )
            
            value = dlg.GetString()
            
            self.assertEqual( value, 'a' )
            
        
        with ClientGUIDialogs.DialogSelectFromListOfStrings( None, 'select from a list of strings', [ 'a', 'b', 'c' ] ) as dlg:
            
            HitButton( dlg._dialog_cancel_button )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_CANCEL )
            
        
        with ClientGUIDialogs.DialogSelectFromListOfStrings( None, 'select from a list of strings', [ 'a', 'b', 'c' ] ) as dlg:
            
            wx.CallAfter( dlg._strings.Select, 1 )
            
            HitButton( dlg._ok )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_OK )
            
            value = dlg.GetString()
            
            self.assertEqual( value, 'b' )
            
        
    
    def test_dialog_yes_no( self ):
        
        with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
            
            HitButton( dlg._yes )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_YES )
            
        
        with ClientGUIDialogs.DialogYesNo( None, 'hello' ) as dlg:
            
            HitButton( dlg._no )
            
            result = dlg.ShowModal()
            
            self.assertEqual( result, wx.ID_NO )
            
        
    