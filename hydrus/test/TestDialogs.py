import unittest

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUISubscriptions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP

from hydrus.test import TestGlobals as TG

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
    
    window.setFocus( QC.Qt.FocusReason.OtherFocusReason )
    
    uias = QP.UIActionSimulator()
    
    uias.Char( window, key )
    
class TestDBDialogs( unittest.TestCase ):
    
    def test_dialog_manage_subs( self ):
        
        def qt_code():
            
            title = 'subs test'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( None, title ) as dlg:
                
                panel = ClientGUISubscriptions.EditSubscriptionsPanel( dlg, [] )
                
                dlg.SetPanel( panel )
                
                TG.test_controller.CallLaterQtSafe( dlg, 2, 'test job', panel.Add )
                
                TG.test_controller.CallLaterQtSafe( dlg, 4, 'test job', OKChildDialog, panel )
                
                TG.test_controller.CallLaterQtSafe( dlg, 6, 'test job', HitCancelButton, dlg )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.DialogCode.Rejected )
                
            
        
        TG.test_controller.CallBlockingToQt( TG.test_controller.win, qt_code )
        
    
class TestNonDBDialogs( unittest.TestCase ):
    
    def test_dialog_choose_new_service_method( self ):
        
        def qt_code():
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                TG.test_controller.CallLaterQtSafe( dlg, 1, 'test job', HitButton, dlg._register )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.DialogCode.Accepted )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, True )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                TG.test_controller.CallLaterQtSafe( dlg, 1, 'test job', HitButton, dlg._setup )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.DialogCode.Accepted )
                
                register = dlg.GetRegister()
                
                self.assertEqual( register, False )
                
            
            with ClientGUIDialogs.DialogChooseNewServiceMethod( None ) as dlg:
                
                TG.test_controller.CallLaterQtSafe( dlg, 1, 'test job', HitCancelButton, dlg )
                
                result = dlg.exec()
                
                self.assertEqual( result, QW.QDialog.DialogCode.Rejected )
                
            
        
        TG.test_controller.CallBlockingToQt( TG.test_controller.win, qt_code )
        
    
