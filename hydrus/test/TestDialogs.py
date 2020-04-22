from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsManagement
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client import ClientThreading
import collections
from hydrus.core import HydrusConstants as HC
import os
import unittest
from hydrus.core import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from hydrus.client.gui import QtPorting as QP

def HitButton( button ):
    
    button.click()
    
def HitCancelButton( window ):
    
    window.reject()
    
def HitOKButton( window ):
    
    window.accept()
    
def CancelChildDialog( window ):
    
    children = window.children()
    
    for child in children:
        
        if isinstance( child, QP.Dialog ):
            
            HitCancelButton( child )
            
        

def OKChildDialog( window ):
    
    children = window.children()
    
    for child in children:
        
        if isinstance( child, QP.Dialog ):
            
            HitOKButton( child )
            
        
    
def PressKey( window, key ):
    
    window.setFocus( QC.Qt.OtherFocusReason )
    
    uias = QP.UIActionSimulator()
    
    uias.Char( key )
    
class TestDBDialogs( unittest.TestCase ):
    
    def test_dialog_manage_subs( self ):
        
        def qt_code():
            
            title = 'subs test'
            
            with ClientGUITopLevelWindows.DialogEdit( None, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditSubscriptionsPanel( dlg, [] )
                
                dlg.SetPanel( panel )
                
                HG.test_controller.CallLaterQtSafe(dlg, 2, panel.Add)
                
                HG.test_controller.CallLaterQtSafe(dlg, 4, OKChildDialog, panel)
                
                HG.test_controller.CallLaterQtSafe(dlg, 6, HitCancelButton, dlg)
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.Rejected )
                
            
        
        HG.test_controller.CallBlockingToQt( HG.test_controller.win, qt_code )
        
    
class TestNonDBDialogs( unittest.TestCase ):
    
    def test_dialog_choose_new_service_method( self ):
        
        def qt_code():
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HG.test_controller.CallLaterQtSafe( dlg, 1, HitButton, dlg._register )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.Accepted )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, True )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HG.test_controller.CallLaterQtSafe( dlg, 1, HitButton, dlg._setup )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.Accepted )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, False )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                HG.test_controller.CallLaterQtSafe( dlg, 1, HitCancelButton, dlg )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.Rejected )
                
            
        
        HG.test_controller.CallBlockingToQt( HG.test_controller.win, qt_code )
        
    
