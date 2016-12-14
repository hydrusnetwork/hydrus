import HydrusExceptions
import Queue
import threading
import time
import traceback
import HydrusData
import HydrusGlobals
import os

THREADS_TO_THREAD_INFO = {}
THREAD_INFO_LOCK = threading.Lock()

def GetThreadInfo( thread = None ):
    
    if thread is None:
        
        thread = threading.current_thread()
        
    
    with THREAD_INFO_LOCK:
        
        if thread not in THREADS_TO_THREAD_INFO:
            
            thread_info = {}
            
            thread_info[ 'shutting_down' ] = False
            
            THREADS_TO_THREAD_INFO[ thread ] = thread_info
            
        
        return THREADS_TO_THREAD_INFO[ thread ]
        
    
def IsThreadShuttingDown():
    
    if HydrusGlobals.view_shutdown:
        
        return True
        
    
    thread_info = GetThreadInfo()
    
    return thread_info[ 'shutting_down' ]
    
def ShutdownThread( thread ):
    
    thread_info = GetThreadInfo( thread )
    
    thread_info[ 'shutting_down' ] = True
    
class DAEMON( threading.Thread ):
    
    def __init__( self, controller, name, period = 1200 ):
        
        threading.Thread.__init__( self, name = name )
        
        self._controller = controller
        self._name = name
        
        self._event = threading.Event()
        
        self._controller.sub( self, 'wake', 'wake_daemons' )
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def shutdown( self ):
        
        ShutdownThread( self )
        
        self.wake()
        
    
    def wake( self ):
        
        self._event.set()
        
    
class DAEMONQueue( DAEMON ):
    
    def __init__( self, controller, name, callable, queue_topic, period = 10 ):
        
        DAEMON.__init__( self, controller, name )
        
        self._callable = callable
        self._queue = Queue.Queue()
        self._queue_topic = queue_topic
        self._period = period
        
        self._controller.sub( self, 'put', queue_topic )
        
        self.start()
        
    
    def put( self, data ): self._queue.put( data )
    
    def run( self ):
        
        time.sleep( 3 )
        
        while True:
            
            while self._queue.empty():
                
                if IsThreadShuttingDown():
                    
                    return
                    
                
                self._event.wait( self._period )
                
                self._event.clear()
                
            
            items = []
            
            while not self._queue.empty(): items.append( self._queue.get() )
            
            try:
                
                self._callable( self._controller, items )
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, controller, name, callable, topics = None, period = 3600, init_wait = 3, pre_call_wait = 0 ):
        
        if topics is None: topics = []
        
        DAEMON.__init__( self, controller, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_call_wait = pre_call_wait
        
        for topic in topics: self._controller.sub( self, 'set', topic )
        
        self.start()
        
    
    def _CanStart( self, time_started_waiting ):
        
        return self._PreCallWaitIsDone( time_started_waiting ) and self._ControllerIsOKWithIt()
        
    
    def _ControllerIsOKWithIt( self ):
        
        return True
        
    
    def _PreCallWaitIsDone( self, time_started_waiting ):
        
        # just shave a bit off so things that don't have any wait won't somehow have to wait a single accidentaly cycle
        time_to_start = ( float( time_started_waiting ) - 0.1 ) + self._pre_call_wait
        
        return HydrusData.TimeHasPassed( time_to_start )
        
    
    def run( self ):
        
        self._event.wait( self._init_wait )
        
        while True:
            
            if IsThreadShuttingDown():
                
                return
                
            
            time_started_waiting = HydrusData.GetNow()
            
            while not self._CanStart( time_started_waiting ):
                
                time.sleep( 1 )
                
                if IsThreadShuttingDown():
                    
                    return
                    
                
            
            try:
                
                self._callable( self._controller )
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.ShowText( 'Daemon ' + self._name + ' encountered an exception:' )
                
                HydrusData.ShowException( e )
                
            
            if IsThreadShuttingDown(): return
            
            self._event.wait( self._period )
            
            self._event.clear()
            
        
    
    def set( self, *args, **kwargs ): self._event.set()
    
# Big stuff like DB maintenance that we don't want to run while other important stuff is going on, like user interaction or vidya on another process
class DAEMONBackgroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ):
        
        return self._controller.GoodTimeToDoBackgroundWork()
        
    
# Big stuff that we want to run when the user sees, but not at the expense of something else, like laggy session load
class DAEMONForegroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ):
        
        return self._controller.GoodTimeToDoForegroundWork()
        
    
class THREADCallToThread( DAEMON ):
    
    def __init__( self, controller ):
        
        DAEMON.__init__( self, controller, 'CallToThread' )
        
        self._queue = Queue.Queue()
        
        self._currently_working = False
        
    
    def CurrentlyWorking( self ):
        
        return self._currently_working
        
    
    def put( self, callable, *args, **kwargs ):
        
        self._queue.put( ( callable, args, kwargs ) )
        
        self._event.set()
        
    
    def run( self ):
        
        while True:
            
            while self._queue.empty():
                
                if self._controller.ModelIsShutdown(): return
                
                self._event.wait( 1200 )
                
                self._event.clear()
                
            
            try:
                
                ( callable, args, kwargs ) = self._queue.get()
                
                self._currently_working = True
                
                callable( *args, **kwargs )
                
                del callable
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            finally:
                
                self._currently_working = False
                
            
            time.sleep( 0.00001 )
            
        
    
