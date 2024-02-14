import typing

from qtpy import QtWidgets as QW

from hydrus.core.interfaces import HydrusControllerInterface

from hydrus.client import ClientThreading

class ClientControllerInterface( HydrusControllerInterface.HydrusControllerInterface ):
    
    def CallBlockingToQt( self, win: QW.QWidget, func: typing.Callable, *args, **kwargs ) -> object:
        
        raise NotImplementedError()
        
    
    def CallAfterQtSafe( self, window: QW.QWidget, label: str, func: typing.Callable, *args, **kwargs ) -> ClientThreading.QtAwareJob:
        
        raise NotImplementedError()
        
    
    def CallLaterQtSafe( self, window: QW.QWidget, initial_delay: float, label: str, func: typing.Callable, *args, **kwargs ) -> ClientThreading.QtAwareJob:
        
        raise NotImplementedError()
        
    
    def CallRepeatingQtSafe( self, window: QW.QWidget, initial_delay: float, period: float, label: str, func: typing.Callable, *args, **kwargs ) -> ClientThreading.QtAwareRepeatingJob:
        
        raise NotImplementedError()
        
    
    def GetClipboardText( self ) -> str:
        
        raise  NotImplementedError()
        
    
