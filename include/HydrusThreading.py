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
                
                if IsThreadShuttingDown(): return
                
                self._event.wait( self._period )
                
                self._event.clear()
                
            
            while not self._controller.GoodTimeToDoBackgroundWork():
                
                if IsThreadShuttingDown(): return
                
                time.sleep( 10 )
                
            
            items = []
            
            while not self._queue.empty(): items.append( self._queue.get() )
            
            try:
                
                self._callable( self._controller, items )
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, controller, name, callable, topics = None, period = 1200, init_wait = 3, pre_callable_wait = 3 ):
        
        if topics is None: topics = []
        
        DAEMON.__init__( self, controller, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_callable_wait = pre_callable_wait
        
        for topic in topics: self._controller.sub( self, 'set', topic )
        
        self.start()
        
    
    def run( self ):
        
        self._event.wait( self._init_wait )
        
        while True:
            
            if IsThreadShuttingDown(): return
            
            time_to_go = ( HydrusData.GetNow() - 1 ) + self._pre_callable_wait
            
            while not ( HydrusData.TimeHasPassed( time_to_go ) and self._controller.GoodTimeToDoBackgroundWork() ):
                
                time.sleep( 1 )
                
                if IsThreadShuttingDown(): return
                
            
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
    
class DAEMONCallToThread( DAEMON ):
    
    def __init__( self, controller ):
        
        DAEMON.__init__( self, controller, 'CallToThread' )
        
        self._queue = Queue.Queue()
        
        self.start()
        
    
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
                
                callable( *args, **kwargs )
                
                del callable
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    
class JobKey( object ):
    
    def __init__( self, pausable = False, cancellable = False ):
        
        self._key = HydrusData.GenerateKey()
        
        self._pausable = pausable
        self._cancellable = cancellable
        
        self._deleted = threading.Event()
        self._begun = threading.Event()
        self._done = threading.Event()
        self._cancelled = threading.Event()
        self._paused = threading.Event()
        
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def Begin( self ): self._begun.set()
    
    def Cancel( self ):
        
        self._cancelled.set()
        
        self.Finish()
        
    
    def Delete( self ):
        
        self.Finish()
        
        self._deleted.set()
        
    
    def DeleteVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables: del self._variables[ name ]
            
        
        time.sleep( 0.00001 )
        
    
    def Finish( self ): self._done.set()
    
    def GetKey( self ): return self._key
    
    def GetVariable( self, name ):
        
        with self._variable_lock: return self._variables[ name ]
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
    def IsBegun( self ):
        
        return self._begun.is_set()
        
    
    def IsCancellable( self ):
        
        return self._cancellable and not self.IsDone()
        
    
    def IsCancelled( self ):
        
        return IsThreadShuttingDown() or self._cancelled.is_set()
        
    
    def IsDeleted( self ):
        
        return IsThreadShuttingDown() or self._deleted.is_set()
        
    
    def IsDone( self ):
        
        return IsThreadShuttingDown() or self._done.is_set()
        
    
    def IsPausable( self ): return self._pausable and not self.IsDone()
    
    def IsPaused( self ): return self._paused.is_set() and not self.IsDone()
    
    def IsWorking( self ): return self.IsBegun() and not self.IsDone()
    
    def PausePlay( self ):
        
        if self._paused.is_set(): self._paused.clear()
        else: self._paused.set()
        
    
    def SetCancellable( self, value ): self._cancellable = value
    
    def SetPausable( self, value ): self._pausable = value
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
        time.sleep( 0.00001 )
        
    
    def ToString( self ):
        
        stuff_to_print = []
        
        with self._variable_lock:
            
            if 'popup_title' in self._variables: stuff_to_print.append( self._variables[ 'popup_title' ] )
            
            if 'popup_text_1' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_1' ] )
            
            if 'popup_text_2' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_2' ] )
            
            if 'popup_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_traceback' ] )
            
            if 'popup_caller_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_caller_traceback' ] )
            
            if 'popup_db_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_db_traceback' ] )
            
        
        stuff_to_print = [ HydrusData.ToUnicode( s ) for s in stuff_to_print ]
        
        try:
            
            return os.linesep.join( stuff_to_print )
            
        except:
            
            return repr( stuff_to_print )
            
        
    
    def WaitIfNeeded( self ):
        
        i_paused = False
        should_quit = False
        
        while self.IsPaused():
            
            i_paused = True
            
            time.sleep( 0.1 )
            
            if IsThreadShuttingDown() or self.IsDone(): break
            
        
        if IsThreadShuttingDown() or self.IsCancelled():
            
            should_quit = True
            
        
        return ( i_paused, should_quit )
        
    