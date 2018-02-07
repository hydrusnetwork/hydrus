import collections
import HydrusExceptions
import Queue
import threading
import time
import traceback
import HydrusData
import HydrusGlobals as HG
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
    
    if HG.view_shutdown:
        
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
        
    
    def _DoPreCall( self ):
        
        if HG.daemon_report_mode:
            
            HydrusData.ShowText( self._name + ' doing a job.' )
            
        
    
    def shutdown( self ):
        
        ShutdownThread( self )
        
        self.wake()
        
    
    def wake( self ):
        
        self._event.set()
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, controller, name, callable, topics = None, period = 3600, init_wait = 3, pre_call_wait = 0 ):
        
        if topics is None:
            
            topics = []
            
        
        DAEMON.__init__( self, controller, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_call_wait = pre_call_wait
        
        for topic in topics:
            
            self._controller.sub( self, 'set', topic )
            
        
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
                    
                
            
            self._DoPreCall()
            
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
        
    
class JobScheduler( DAEMON ):
    
    def __init__( self, controller ):
        
        DAEMON.__init__( self, controller, 'JobScheduler' )
        
        self._currently_working = []
        
        self._waiting = []
        
        self._waiting_lock = threading.Lock()
        
        self._new_action = threading.Event()
        
        self._sort_needed = threading.Event()
        
    
    def _InsertJob( self, job ):
        
        # write __lt__, __gt__, stuff and do a bisect insort_left here
        
        with self._waiting_lock:
            
            self._waiting.append( job )
            
        
        self._sort_needed.set()
        
    
    def _NoWorkToStart( self ):
        
        with self._waiting_lock:
            
            if len( self._waiting ) == 0:
                
                return True
                
            
            next_job = self._waiting[0]
            
        
        if HydrusData.TimeHasPassed( next_job.GetNextWorkTime() ):
            
            return False
            
        else:
            
            return True
            
        
    
    def _RescheduleFinishedJobs( self ):
        
        def reschedule_finished_job( job ):
            
            if job.CurrentlyWorking():
                
                return True
                
            else:
                
                self._InsertJob( job )
                
                return False
                
            
        
        self._currently_working = filter( reschedule_finished_job, self._currently_working )
        
    
    def _SortWaiting( self ):
        
        # sort the waiting jobs in ascending order of expected work time
        
        def key( job ):
            
            return job.GetNextWorkTime()
            
        
        with self._waiting_lock:
            
            self._waiting.sort( key = key )
            
        
    
    def _StartWork( self ):
        
        while True:
            
            with self._waiting_lock:
                
                if len( self._waiting ) == 0:
                    
                    break
                    
                
                next_job = self._waiting[0]
                
                if HydrusData.TimeHasPassed( next_job.GetNextWorkTime() ):
                    
                    next_job = self._waiting.pop( 0 )
                    
                    if not next_job.IsDead():
                        
                        next_job.StartWork()
                        
                        self._currently_working.append( next_job )
                        
                    
                else:
                    
                    break # all the rest in the queue are not due
                    
                
            
        
    
    def RegisterJob( self, job ):
        
        job.SetScheduler( self )
        
        self._InsertJob( job )
        
    
    def WorkTimesHaveChanged( self ):
        
        self._sort_needed.set()
        
    
    def run( self ):
        
        while True:
            
            try:
                
                while self._NoWorkToStart():
                    
                    if self._controller.ModelIsShutdown():
                        
                        return
                        
                    
                    #
                    
                    self._RescheduleFinishedJobs()
                    
                    #
                    
                    self._sort_needed.wait( 0.2 )
                    
                    if self._sort_needed.is_set():
                        
                        self._SortWaiting()
                        
                        self._sort_needed.clear()
                        
                    
                
                self._StartWork()
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.Print( traceback.format_exc() )
                
                HydrusData.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    
class RepeatingJob( object ):
    
    def __init__( self, controller, work_callable, period, initial_delay = 0 ):
        
        self._controller = controller
        self._work_callable = work_callable
        self._period = period
        
        self._is_dead = threading.Event()
        
        self._work_lock = threading.Lock()
        
        self._currently_working = threading.Event()
        
        self._next_work_time = HydrusData.GetNow() + initial_delay
        
        self._scheduler = None
        
        # registers itself with controller here
        
    
    def CurrentlyWorking( self ):
        
        return self._currently_working.is_set()
        
    
    def GetNextWorkTime( self ):
        
        return self._next_work_time
        
    
    def IsDead( self ):
        
        return self._is_dead.is_set()
        
    
    def Kill( self ):
        
        self._is_dead.set()
        
    
    def SetScheduler( self, scheduler ):
        
        self._scheduler = scheduler
        
    
    def StartWork( self ):
        
        self._currently_working.set()
        
        self._controller.CallToThread( self.Work )
        
    
    def WakeAndWork( self ):
        
        self._next_work_time = HydrusData.GetNow()
        
        if self._scheduler is not None:
            
            self._scheduler.WorkTimesHaveChanged()
            
        
    
    def Work( self ):
        
        with self._work_lock:
            
            try:
                
                self._work_callable()
                
            finally:
                
                self._next_work_time = HydrusData.GetNow() + self._period
                
                self._currently_working.clear()
                
            
        
    
class THREADCallToThread( DAEMON ):
    
    def __init__( self, controller ):
        
        DAEMON.__init__( self, controller, 'CallToThread' )
        
        self._queue = Queue.Queue()
        
        self._currently_working = True # start off true so new threads aren't used twice by two quick successive calls
        
    
    def CurrentlyWorking( self ):
        
        return self._currently_working
        
    
    def put( self, callable, *args, **kwargs ):
        
        self._currently_working = True
        
        self._queue.put( ( callable, args, kwargs ) )
        
        self._event.set()
        
    
    def run( self ):
        
        while True:
            
            try:
                
                while self._queue.empty():
                    
                    if self._controller.ModelIsShutdown():
                        
                        return
                        
                    
                    self._event.wait( 1200 )
                    
                    self._event.clear()
                    
                
                self._DoPreCall()
                
                ( callable, args, kwargs ) = self._queue.get()
                
                callable( *args, **kwargs )
                
                del callable
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception as e:
                
                HydrusData.Print( traceback.format_exc() )
                
                HydrusData.ShowException( e )
                
            finally:
                
                self._currently_working = False
                
            
            time.sleep( 0.00001 )
            
        
    
