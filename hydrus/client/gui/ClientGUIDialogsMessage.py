import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

from hydrus.client import ClientGlobals as CG

# This holds common calls for the various QMessageBox dialogs
# a thread can call these safely and they'll block

def ShowDialog( dialog_call: collections.abc.Callable, win: QW.QWidget | None, title: str, message: str ):
    
    if not isinstance( message, str ):
        
        try:
            
            message = str( message )
            
        except Exception as e:
            
            message = f'Could not determine the text for this dialog message! Please let hydev know. My best attempt at rendering what I was given is:\n\n{repr( message )}'
            
            HydrusData.DebugPrint( message )
            
            HydrusData.PrintException( e )
            
        
    
    if QC.QThread.currentThread() == QW.QApplication.instance().thread():
        
        dialog_call( win, title, message )
        
    else:
        
        qt_obj = CG.client_controller.app if win is None else win
        
        CG.client_controller.CallBlockingToQtFireAndForgetNoResponse( qt_obj, dialog_call, win, title, message )
        
    

def ShowCritical( win: QW.QWidget | None, title: str, message: str ):
    
    HydrusData.DebugPrint( title )
    HydrusData.DebugPrint( message )
    
    ShowDialog( QW.QMessageBox.critical, win, title, message )
    

def ShowInformation( win: QW.QWidget | None, message: str ):
    
    ShowDialog( QW.QMessageBox.information, win, 'Information', message )
    

def ShowWarning( win: QW.QWidget | None, message: str ):
    
    ShowDialog( QW.QMessageBox.warning, win, 'Warning', message )
    
