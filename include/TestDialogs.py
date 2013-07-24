import ClientConstants
import ClientGUIDialogs
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest
import wx

def HitButton( button ): wx.PostEvent( button, wx.CommandEvent( wx.EVT_BUTTON.typeId, button.GetId() ) )

class TestNonValidatorDialogs( unittest.TestCase ):
    
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
            
            HitButton( dlg._cancel )
            
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
            
            HitButton( dlg._cancel )
            
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
            
        
    