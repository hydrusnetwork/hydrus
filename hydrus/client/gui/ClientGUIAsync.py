import sys
import threading

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import QtPorting as QP

# this does one thing neatly
class AsyncQtJob( object ):
    
    def __init__( self, win, work_callable, publish_callable, errback_callable = None, errback_ui_cleanup_callable = None ):
        
        # ultimate improvement here is to move to QObject/QThread and do the notifications through signals and slots (which will disconnect on object deletion)
        
        self._win = win
        self._work_callable = work_callable
        self._publish_callable = publish_callable
        self._errback_callable = errback_callable
        self._errback_ui_cleanup_callable = errback_ui_cleanup_callable
        
    
    def _DefaultErrback( self, etype, value, tb ):
        
        HydrusData.ShowExceptionTuple( etype, value, tb )
        
        message = 'An error occured in a background task. If you had UI waiting on a fetch job, the dialog/panel may need to be closed and re-opened.'
        message += '\n' * 2
        message += 'The error info will show as a popup and also be printed to log. Hydev may want to know about this error, at least to improve error handling.'
        message += '\n' * 2
        message += 'Error summary: {}'.format( value )
        
        ClientGUIDialogsMessage.ShowCritical( self._win, 'Error', message )
        
        if self._errback_ui_cleanup_callable is not None:
            
            self._errback_ui_cleanup_callable()
            
        
    
    def _doWork( self ):
        
        def qt_deliver_result( result ):
            
            if not QP.isValid( self._win ):
                
                return
                
            
            self._publish_callable( result )
            
        
        try:
            
            result = self._work_callable()
            
        except Exception as e:
            
            ( etype, value, tb ) = sys.exc_info()
            
            if self._errback_callable is None:
                
                c = self._DefaultErrback
                
            else:
                
                c = self._errback_callable
                
            
            try:
                
                CG.client_controller.CallBlockingToQt( self._win, c, etype, value, tb )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                
                return
                
            
            return
            
        
        try:
            
            CG.client_controller.CallBlockingToQt( self._win, qt_deliver_result, result )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
            
            return
            
        except Exception as e:
            
            ( etype, value, tb ) = sys.exc_info()
            
            if self._errback_callable is None:
                
                c = self._DefaultErrback
                
            else:
                
                c = self._errback_callable
                
            
            try:
                
                CG.client_controller.CallBlockingToQt( self._win, c, etype, value, tb )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                
                return
                
            
        
    
    def start( self ):
        
        CG.client_controller.CallToThread( self._doWork )
        
    
# this can refresh dirty stuff n times and won't spam work
class AsyncQtUpdater( object ):
    
    def __init__( self, win, loading_callable, work_callable, publish_callable, pre_work_callable = None ):
        
        # ultimate improvement here is to move to QObject/QThread and do the notifications through signals and slots (which will disconnect on object deletion)
        
        self._win = win
        
        self._loading_callable = loading_callable
        self._work_callable = work_callable
        self._publish_callable = publish_callable
        self._pre_work_callable = pre_work_callable
        
        self._calllater_waiting = False
        self._work_needs_to_restart = False
        self._is_working = False
        
        self._lock = threading.Lock()
        
    
    def _doWork( self ):
        
        def qt_deliver_result( result ):
            
            if self._win is None or not QP.isValid( self._win ):
                
                self._win = None
                
                return
                
            
            self._publish_callable( result )
            
        
        with self._lock:
            
            self._calllater_waiting = False
            self._work_needs_to_restart = False
            self._is_working = True
            
        
        try:
            
            if self._pre_work_callable is None:
                
                pre_work_args = 1
                
            else:
                
                try:
                    
                    pre_work_args = CG.client_controller.CallBlockingToQt( self._win, self._pre_work_callable )
                    
                except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                    
                    self._win = None
                    
                    return
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
            try:
                
                result = self._work_callable( pre_work_args )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            try:
                
                CG.client_controller.CallBlockingToQt( self._win, qt_deliver_result, result )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                
                self._win = None
                
                return
                
            
        finally:
            
            with self._lock:
                
                self._is_working = False
                
                if self._work_needs_to_restart and not self._calllater_waiting:
                    
                    if self._win is not None:
                        
                        CG.client_controller.CallAfter( self._win, self.update )
                        
                    
                
            
        
    
    def _startWork( self ):
        
        CG.client_controller.CallToThread( self._doWork )
        
    
    def update( self ):
        
        if self._win is None or not QP.isValid( self._win ):
            
            self._win = None
            
            return
            
        
        with self._lock:
            
            if self._is_working:
                
                self._work_needs_to_restart = True
                
            elif not self._calllater_waiting:
                
                self._loading_callable()
                
                self._calllater_waiting = True
                
                self._startWork()
                
            
        
    
class FastThreadToGUIUpdater( object ):
    
    def __init__( self, win, func ):
        
        self._win = win
        self._func = func
        
        self._lock = threading.Lock()
        
        self._args = None
        self._kwargs = None
        
        self._callafter_waiting = False
        self._work_needs_to_restart = False
        self._is_working = False
        
    
    def QtDoIt( self ):
        
        if self._win is None or not QP.isValid( self._win ):
            
            self._win = None
            
            return
            
        
        with self._lock:
            
            self._callafter_waiting = False
            self._work_needs_to_restart = False
            self._is_working = True
            
            args = self._args
            kwargs = self._kwargs
            
        
        try:
            
            self._func( *args, **kwargs )
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        finally:
            
            with self._lock:
                
                self._is_working = False
                
                if self._work_needs_to_restart and not self._callafter_waiting:
                    
                    self._callafter_waiting = True
                    
                    CG.client_controller.CallAfter( self._win, self.QtDoIt )
                    
                
            
        
    
    # the point here is that we can spam this a hundred times a second, updating the args and kwargs, and Qt will catch up to it when it can
    # if Qt feels like running fast, it'll update at 60fps
    # if not, we won't get bungled up with 10,000+ pubsub events in the event queue
    def Update( self, *args, **kwargs ):
        
        if self._win is None:
            
            return
            
        
        with self._lock:
            
            self._args = args
            self._kwargs = kwargs
            
            if self._is_working:
                
                self._work_needs_to_restart = True
                
            elif not ( self._callafter_waiting or HG.view_shutdown ):
                
                CG.client_controller.CallAfter( self._win, self.QtDoIt )
                
            
        
    
