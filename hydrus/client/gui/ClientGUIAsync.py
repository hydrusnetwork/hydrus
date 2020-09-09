import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client.gui import QtPorting as QP

# this does one thing neatly
class AsyncQtJob( object ):
    
    def __init__( self, win, work_callable, publish_callable ):
        
        # ultimate improvement here is to move to QObject/QThread and do the notifications through signals and slots (which will disconnect on object deletion)
        
        self._win = win
        self._work_callable = work_callable
        self._publish_callable = publish_callable
        
    
    def _doWork( self ):
        
        def qt_deliver_result( result ):
            
            if not QP.isValid( self._win ):
                
                return
                
            
            self._publish_callable( result )
            
        
        result = self._work_callable()
        
        try:
            
            HG.client_controller.CallBlockingToQt( self._win, qt_deliver_result, result )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
            
            return
            
        
    
    def start( self ):
        
        HG.client_controller.CallToThread( self._doWork )
        
    
# this can refresh dirty stuff n times and won't spam work
class AsyncQtUpdater( object ):
    
    def __init__( self, win, loading_callable, work_callable, publish_callable ):
        
        # ultimate improvement here is to move to QObject/QThread and do the notifications through signals and slots (which will disconnect on object deletion)
        
        self._win = win
        
        self._loading_callable = loading_callable
        self._work_callable = work_callable
        self._publish_callable = publish_callable
        
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
            
            result = self._work_callable()
            
            try:
                
                HG.client_controller.CallBlockingToQt( self._win, qt_deliver_result, result )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
                
                self._win = None
                
                return
                
            
        finally:
            
            with self._lock:
                
                self._is_working = False
                
                if self._work_needs_to_restart and not self._calllater_waiting:
                    
                    QP.CallAfter( self.update )
                    
                
            
        
    
    def _startWork( self ):
        
        HG.client_controller.CallToThread( self._doWork )
        
    
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
                    
                    QP.CallAfter( self.QtDoIt )
                    
                
            
        
    
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
                
            elif not self._callafter_waiting:
                
                QP.CallAfter( self.QtDoIt )
                
            
        
    
