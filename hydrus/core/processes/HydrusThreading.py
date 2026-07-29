import bisect
import queue
import random
import threading
import time
import traceback

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusTime

NEXT_THREAD_CLEAROUT = 0

THREADS_TO_THREAD_INFO = {}
THREAD_INFO_LOCK = threading.Lock()

def CheckIfThreadShuttingDown()-> None:
    
    if IsThreadShuttingDown():
        
        raise HydrusExceptions.ShutdownException( 'Thread is shutting down!' )
        
    

def ClearOutDeadThreads() -> None:
    
    with THREAD_INFO_LOCK:
        
        all_threads = list( THREADS_TO_THREAD_INFO.keys() )
        
        for thread in all_threads:
            
            if not thread.is_alive():
                
                del THREADS_TO_THREAD_INFO[ thread ]
                
            
        
    
def GetThreadInfo( thread = None ):
    
    global NEXT_THREAD_CLEAROUT
    
    if HydrusTime.TimeHasPassed( NEXT_THREAD_CLEAROUT ):
        
        ClearOutDeadThreads()
        
        NEXT_THREAD_CLEAROUT = HydrusTime.GetNow() + 600
        
    
    if thread is None:
        
        thread = threading.current_thread()
        
    
    with THREAD_INFO_LOCK:
        
        if thread not in THREADS_TO_THREAD_INFO:
            
            thread_info = {}
            
            thread_info[ 'shutting_down' ] = False
            
            THREADS_TO_THREAD_INFO[ thread ] = thread_info
            
        
        return THREADS_TO_THREAD_INFO[ thread ]
        
    
def IsThreadShuttingDown() -> bool:
    
    if HG.controller.DoingFastExit():
        
        return True
        
    
    me = threading.current_thread()
    
    if isinstance( me, DAEMON ):
        
        if HG.started_shutdown:
            
            return True
            
        
    else:
        
        if HG.model_shutdown:
            
            return True
            
        
    
    thread_info = GetThreadInfo()
    
    return thread_info[ 'shutting_down' ]
    

def ShutdownThread( thread ) -> None:
    
    if HG.shutdown_report_mode:
        
        HydrusData.DebugPrint( f'Thread "{thread}" is getting an external shutdown call.' )
        
    
    thread_info = GetThreadInfo( thread )
    
    thread_info[ 'shutting_down' ] = True
    

class RegularJobChecker( object ):
    
    def __init__( self, period = 10 ):
        
        self._period = period
        
        self._next_check = HydrusTime.GetNowFloat()
        
    
    def Due( self ) -> bool:
        
        if HydrusTime.TimeHasPassedFloat( self._next_check ):
            
            self._next_check = HydrusTime.GetNowFloat() + self._period
            
            return True
            
        else:
            
            return False
            
        
    

class BigJobPauser( object ):
    
    def __init__( self, period = 10, wait_time = 0.1 ):
        
        self._period = period
        self._wait_time = wait_time
        
        self._next_pause = HydrusTime.GetNowFloat() + self._period
        
    
    def Pause( self ):
        
        if HydrusTime.TimeHasPassedFloat( self._next_pause ):
            
            time.sleep( self._wait_time )
            
            self._next_pause = HydrusTime.GetNowFloat() + self._period
            
        
    

class DAEMON( threading.Thread ):
    
    def __init__( self, controller: "HG.HydrusController.HydrusController", name: str ):
        
        super().__init__( name = name )
        
        self._controller = controller
        self._name = name
        
        self._event = threading.Event()
        
        self._controller.sub( self, 'wake', 'wake_daemons' )
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def _DoPreCall( self ):
        
        if HG.daemon_report_mode:
            
            HydrusData.ShowText( self._name + ' doing a job.' )
            
        
    
    def GetCurrentJobSummary( self ) -> str:
        
        return 'unknown job'
        
    
    def GetName( self ):
        
        return self._name
        
    
    def shutdown( self ):
        
        ShutdownThread( self )
        
        self.wake()
        
    
    def wake( self ) -> None:
        
        self._event.set()
        
    

class DAEMONWorker( DAEMON ):
    
    def __init__( self, controller, name, callable, topics = None, period = 3600, init_wait = 3, pre_call_wait = 0 ):
        
        if topics is None:
            
            topics = []
            
        
        super().__init__( controller, name )
        
        self._callable = callable
        self._topics = topics
        self._period = period
        self._init_wait = init_wait
        self._pre_call_wait = pre_call_wait
        
        for topic in topics:
            
            self._controller.sub( self, 'set', topic )
            
        
        self.start()
        
    
    def _CanStart( self ) -> bool:
        
        return self._ControllerIsOKWithIt()
        
    
    def _ControllerIsOKWithIt( self ) -> bool:
        
        return True
        
    
    def _DoAWait( self, wait_time, event_can_wake = True )-> None:
        
        time_to_start = HydrusTime.GetNow() + wait_time
        
        while not HydrusTime.TimeHasPassed( time_to_start ):
            
            if event_can_wake:
                
                event_was_set = self._event.wait( 1.0 )
                
                if event_was_set:
                    
                    self._event.clear()
                    
                    return
                    
                
            else:
                
                time.sleep( 1.0 )
                
            
            CheckIfThreadShuttingDown()
            
        
    
    def _WaitUntilCanStart( self ):
        
        while not self._CanStart():
            
            time.sleep( 1.0 )
            
            CheckIfThreadShuttingDown()
            
        
    
    def GetCurrentJobSummary( self ):
        
        return self._callable
        
    
    def run( self ) -> None:
        
        try:
            
            self._DoAWait( self._init_wait )
            
            while True:
                
                CheckIfThreadShuttingDown()
                
                self._DoAWait( self._pre_call_wait, event_can_wake = False )
                
                CheckIfThreadShuttingDown()
                
                self._WaitUntilCanStart()
                
                CheckIfThreadShuttingDown()
                
                self._DoPreCall()
                
                try:
                    
                    self._callable( self._controller )
                    
                except HydrusExceptions.ShutdownException:
                    
                    if HG.shutdown_report_mode:
                        
                        HydrusData.DebugPrint( f'Daemon worker "{self._name}" encountered a Shutdown exception inside of the main callable.' )
                        
                    
                    return
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Daemon ' + self._name + ' encountered an exception:' )
                    
                    HydrusData.ShowException( e )
                    
                
                self._DoAWait( self._period )
                
            
        except HydrusExceptions.ShutdownException:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'Daemon worker "{self._name}" encountered a Shutdown exception outside of the main callable.' )
                
            
            return
            
        finally:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'Daemon CallToWorker "{self._name}" is shut down!' )
                
            
        
    
    def set( self, *args, **kwargs ):
        
        self._event.set()
        
    

# Big stuff like DB maintenance that we don't want to run while other important stuff is going on, like user interaction or vidya on another process
class DAEMONBackgroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ) -> bool:
        
        return self._controller.GoodTimeToStartBackgroundWork()
        
    
# Big stuff that we want to run when the user sees, but not at the expense of something else, like laggy session load
class DAEMONForegroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ) -> bool:
        
        return self._controller.GoodTimeToStartForegroundWork()
        
    

SHUTDOWN_SENTINEL = object()

class THREADCallToThread( DAEMON ):
    
    def __init__( self, controller, name ):
        
        super().__init__( controller, name )
        
        self._callable = None
        
        self._queue = queue.Queue()
        
        self._currently_working = True # start off true so new threads aren't used twice by two quick successive calls
        
    
    def CurrentlyWorking( self ) -> bool:
        
        return self._currently_working
        
    
    def GetCurrentJobSummary( self ):
        
        return self._callable
        
    
    def put( self, callable, *args, **kwargs ) -> None:
        
        # TODO: maybe put a 'if shutdown, raise shutdown exception' here
        
        self._currently_working = True
        
        self._queue.put( ( callable, args, kwargs ) )
        
        self._event.set()
        
    
    def run( self ) -> None:
        
        try:
            
            while True:
                
                CheckIfThreadShuttingDown()
                
                try:
                    
                    result = self._queue.get()
                    
                    if result is SHUTDOWN_SENTINEL:
                        
                        raise HydrusExceptions.ShutdownException()
                        
                    
                    ( callable, args, kwargs ) = result
                    
                    self._DoPreCall()
                    
                    self._callable = ( callable, args, kwargs )
                    
                    if HydrusProfiling.IsProfileMode( 'threads' ):
                        
                        summary = 'Profiling CallTo Job: {}'.format( callable )
                        
                        HydrusProfiling.Profile( summary, HydrusData.Call( callable, *args, **kwargs ), min_duration_ms = HG.callto_profile_min_job_time_ms )
                        
                    else:
                        
                        callable( *args, **kwargs )
                        
                    
                    self._callable = None
                    
                    del callable
                    
                except HydrusExceptions.ShutdownException:
                    
                    if HG.shutdown_report_mode:
                        
                        HydrusData.DebugPrint( f'Daemon CallToWorker "{self._name}" encountered a Shutdown exception while processing a job.' )
                        
                    
                    return
                    
                except Exception as e:
                    
                    HydrusData.Print( traceback.format_exc() )
                    
                    HydrusData.ShowException( e )
                    
                finally:
                    
                    self._currently_working = False
                    
                
                time.sleep( 0.00001 )
                
            
        except HydrusExceptions.ShutdownException:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'Daemon CallToWorker "{self._name}" encountered a Shutdown exception while waiting on its job queue.' )
                
            
            return
            
        finally:
            
            if HG.shutdown_report_mode:
                
                HydrusData.DebugPrint( f'Daemon CallToWorker "{self._name}" is shut down!' )
                
            
        
    
    def shutdown( self ):
        
        super().shutdown()
        
        self._queue.put( SHUTDOWN_SENTINEL )
        
    

class ThreadWorkerPool( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        self._lock = threading.Lock()
        
        self._thread_pool_busy_status_text = ''
        self._thread_pool_busy_status_tooltip = ''
        self._thread_pool_busy_status_text_last_check_time = 0
        
        self._call_to_threads = []
        self._long_running_call_to_threads = []
        
    
    def GetCallToThread( self ):
        
        with self._lock:
            
            for call_to_thread in self._call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            # all the threads in the pool are currently busy
            
            ok_to_make_one = len( self._call_to_threads ) < 250
            
            if not ok_to_make_one:
                
                my_thread = threading.current_thread()
                
                calling_from_the_thread_pool = my_thread in self._call_to_threads or my_thread in self._long_running_call_to_threads
                
                # we gotta make a new one bro, we are calling from inside the pool. try and avoid a deadlock
                ok_to_make_one = calling_from_the_thread_pool
                
            
            if ok_to_make_one:
                
                call_to_thread = THREADCallToThread( self._controller, 'CallToThread' )
                
                self._call_to_threads.append( call_to_thread )
                
                call_to_thread.start()
                
            else:
                
                call_to_thread = random.choice( self._call_to_threads )
                
            
            return call_to_thread
            
        
    
    def GetCallToThreadLongRunning( self ):
        
        with self._lock:
            
            for call_to_thread in self._long_running_call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            call_to_thread = THREADCallToThread( self._controller, 'CallToThreadLongRunning' )
            
            self._long_running_call_to_threads.append( call_to_thread )
            
            call_to_thread.start()
            
            return call_to_thread
            
        
    
    def GetThreadPoolBusyStatus( self ):
        
        if HydrusTime.TimeHasPassed( self._thread_pool_busy_status_text_last_check_time + 10 ):
            
            with self._lock:
                
                num_threads = sum( ( 1 for t in self._call_to_threads if t.CurrentlyWorking() ) )
                
                if num_threads <= 3:
                    
                    self._thread_pool_busy_status_text = ''
                    
                elif num_threads <= 8:
                    
                    self._thread_pool_busy_status_text = 'working'
                    
                else:
                    
                    self._thread_pool_busy_status_text = 'busy'
                    
                
                self._thread_pool_busy_status_tooltip = f'There were {HydrusNumbers.ToHumanInt( num_threads )} threads doing jobs at last check.'
                
                self._thread_pool_busy_status_text_last_check_time = HydrusTime.GetNow()
                
            
        
        return ( self._thread_pool_busy_status_text, self._thread_pool_busy_status_tooltip )
        
    
    def GetThreadsSnapshot( self ):
        
        with self._lock:
            
            return ( list( self._call_to_threads ), self._long_running_call_to_threads )
            
        
    
    def MaintainCallToThreads( self ):
        
        # we don't really want to hang on to threads that are done as event.wait() has a bit of idle cpu
        # so, any that are in the pools that aren't doing anything can be killed and sent to garbage
        
        with self._lock:
            
            def filter_call_to_threads( t ):
                
                if t.CurrentlyWorking():
                    
                    return True
                    
                else:
                    
                    t.shutdown()
                    
                    return False
                    
                
            
            self._call_to_threads = list( filter( filter_call_to_threads, self._call_to_threads ) )
            
            self._long_running_call_to_threads = list( filter( filter_call_to_threads, self._long_running_call_to_threads ) )
            
        
    
    def shutdown( self ):
        
        with self._lock:
            
            for call_to_thread in self._call_to_threads:
                
                call_to_thread.shutdown()
                
            
            for long_running_call_to_thread in self._long_running_call_to_threads:
                
                long_running_call_to_thread.shutdown()
                
            
        
    

class JobScheduler( threading.Thread ):
    
    def __init__( self, controller: "HG.HydrusController.HydrusController" ):
        
        super().__init__( name = 'Job Scheduler' )
        
        self._controller = controller
        
        self._waiting = []
        
        self._waiting_lock = threading.Lock()
        
        self._new_job_arrived = threading.Event()
        
        self._current_job = None
        
        self._cancel_filter_needed = threading.Event()
        self._sort_needed = threading.Event()
        
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def _FilterCancelled( self ):
        
        with self._waiting_lock:
            
            self._waiting = [ job for job in self._waiting if not job.IsCancelled() ]
            
        
    
    def _GetLoopWaitTime( self ):
        
        with self._waiting_lock:
            
            if len( self._waiting ) == 0:
                
                return 0.2
                
            
            next_job = self._waiting[0]
            
        
        time_delta_until_due = next_job.GetTimeDeltaUntilDue()
        
        return min( 1.0, time_delta_until_due )
        
    
    def _NoWorkToStart( self ) -> bool:
        
        with self._waiting_lock:
            
            if len( self._waiting ) == 0:
                
                return True
                
            
            next_job = self._waiting[0]
            
        
        if next_job.IsDue():
            
            return False
            
        else:
            
            return True
            
        
    
    def _SortWaiting( self ):
        
        # sort the waiting jobs in ascending order of expected work time
        
        with self._waiting_lock: # this uses __lt__ to sort
            
            self._waiting.sort()
            
        
    
    def _StartWork( self ) -> None:
        
        jobs_started = 0
        
        while True:
            
            with self._waiting_lock:
                
                if len( self._waiting ) == 0:
                    
                    break
                    
                
                if jobs_started >= 10: # try to avoid spikes
                    
                    break
                    
                
                next_job = self._waiting[0]
                
                if not next_job.IsDue():
                    
                    # front is not due, so nor is the rest of the list
                    break
                    
                
                next_job = self._waiting.pop( 0 )
                
            
            if next_job.IsCancelled():
                
                continue
                
            
            if next_job.SlotOK():
                
                # important this happens outside of the waiting lock lmao!
                next_job.StartWork()
                
                jobs_started += 1
                
            else:
                
                # delay is automatically set by SlotOK
                
                with self._waiting_lock:
                    
                    bisect.insort( self._waiting, next_job )
                    
                
            
        
    
    def AddJob( self, job ) -> None:
        
        with self._waiting_lock:
            
            bisect.insort( self._waiting, job )
            
        
        self._new_job_arrived.set()
        
    
    def ClearOutDead( self ) -> None:
        
        with self._waiting_lock:
            
            self._waiting = [ job for job in self._waiting if not job.IsDead() ]
            
        
    
    def GetName( self ) -> str:
        
        return 'Job Scheduler'
        
    
    def GetCurrentJobSummary( self ) -> str:
        
        with self._waiting_lock:
            
            return HydrusNumbers.ToHumanInt( len( self._waiting ) ) + ' jobs'
            
        
    
    def GetJobs( self ):
        
        with self._waiting_lock:
            
            return list( self._waiting )
            
        
    
    def GetPrettyJobSummary( self ) -> str:
        
        with self._waiting_lock:
            
            num_jobs = len( self._waiting )
            
            job_lines = [ repr( job ) for job in self._waiting ]
            
            lines = [ HydrusNumbers.ToHumanInt( num_jobs ) + ' jobs:' ] + job_lines
            
            text = '\n'.join( lines )
            
            return text
            
        
    
    def JobCancelled( self ) -> None:
        
        self._cancel_filter_needed.set()
        
    
    def shutdown( self ) -> None:
        
        ShutdownThread( self )
        
        self._new_job_arrived.set()
        
    
    def WorkTimesHaveChanged( self ) -> None:
        
        self._sort_needed.set()
        
    
    def run( self ) -> None:
        
        while True:
            
            try:
                
                while self._NoWorkToStart():
                    
                    if IsThreadShuttingDown():
                        
                        return
                        
                    
                    #
                    
                    if self._cancel_filter_needed.is_set():
                        
                        self._FilterCancelled()
                        
                        self._cancel_filter_needed.clear()
                        
                    
                    if self._sort_needed.is_set():
                        
                        self._SortWaiting()
                        
                        self._sort_needed.clear()
                        
                        continue # if some work is now due, let's do it!
                        
                    
                    #
                    
                    wait_time = self._GetLoopWaitTime()
                    
                    self._new_job_arrived.wait( wait_time )
                    
                    self._new_job_arrived.clear()
                    
                
                self._StartWork()
                
            except HydrusExceptions.ShutdownException:
                
                if HG.shutdown_report_mode:
                    
                    HydrusData.DebugPrint( f'Job Scheduler encountered a Shutdown exception in its mainloop.' )
                    
                
                return
                
            except Exception as e:
                
                HydrusData.Print( traceback.format_exc() )
                
                HydrusData.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    

class SchedulableJob( object ):
    
    PRETTY_CLASS_NAME = 'job base'
    
    def __init__( self, controller: "HG.HydrusController.HydrusController", scheduler: JobScheduler, initial_delay, work_callable ):
        
        super().__init__()
        
        self._controller = controller
        self._scheduler = scheduler
        self._work_callable = work_callable
        
        self._should_delay_on_wakeup = False
        
        self._next_work_time = HydrusTime.GetNowFloat() + initial_delay
        
        self._thread_slot_type = None
        
        self._work_lock = threading.Lock()
        
        self._currently_working = threading.Event()
        self._actual_work_started = threading.Event()
        self._is_cancelled = threading.Event()
        
    
    def __lt__( self, other ): # for the scheduler to do bisect.insort noice
        
        return self._next_work_time < other._next_work_time
        
    
    def __repr__( self ):
        
        return '{}: {} {}'.format( self.PRETTY_CLASS_NAME, self.GetPrettyJob(), self.GetDueString() )
        
    
    def _BootWorker( self ):
        
        self._controller.CallToThread( self.Work )
        
    
    def Cancel( self ) -> None:
        
        self._is_cancelled.set()
        
        self._scheduler.JobCancelled()
        
    
    def CurrentlyWorking( self ) -> bool:
        
        if self._is_cancelled.is_set() and not self._actual_work_started.is_set():
            
            return False
            
        
        return self._currently_working.is_set()
        
    
    def Delay( self, delay ) -> None:
        
        self._next_work_time = HydrusTime.GetNowFloat() + delay
        
        self._scheduler.WorkTimesHaveChanged()
        
    
    def GetDueString( self ) -> str:
        
        due_delta = self._next_work_time - HydrusTime.GetNowFloat()
        
        due_string = HydrusTime.TimeDeltaToPrettyTimeDelta( due_delta )
        
        if due_delta < 0:
            
            due_string = 'was due {} ago'.format( due_string )
            
        else:
            
            due_string = 'due in {}'.format( due_string )
            
        
        return due_string
        
    
    def GetNextWorkTime( self ):
        
        return self._next_work_time
        
    
    def GetPrettyJob( self ):
        
        return repr( self._work_callable )
        
    
    def GetTimeDeltaUntilDue( self ):
        
        return HydrusTime.GetTimeDeltaUntilTimeFloat( self._next_work_time )
        
    
    def IsCancelled( self ) -> bool:
        
        return self._is_cancelled.is_set()
        
    
    def IsDead( self ) -> bool:
        
        return False
        
    
    def IsDue( self ) -> bool:
        
        return HydrusTime.TimeHasPassedFloat( self._next_work_time )
        
    
    def PubSubWake( self, *args, **kwargs ) -> None:
        
        self.Wake()
        
    
    def SetThreadSlotType( self, thread_type ) -> None:
        
        self._thread_slot_type = thread_type
        
    
    def ShouldDelayOnWakeup( self, value ) -> None:
        
        self._should_delay_on_wakeup = value
        
    
    def SlotOK( self ) -> bool:
        
        if self._thread_slot_type is not None:
            
            if HG.controller.AcquireThreadSlot( self._thread_slot_type ):
                
                return True
                
            else:
                
                self._next_work_time = HydrusTime.GetNowFloat() + 10 + random.random()
                
                return False
                
            
        
        return True
        
    
    def StartWork( self ) -> None:
        
        if self._is_cancelled.is_set():
            
            return
            
        
        self._currently_working.set()
        
        self._BootWorker()
        
    
    def Wake( self, next_work_time = None ) -> None:
        
        if next_work_time is None:
            
            next_work_time = HydrusTime.GetNowFloat()
            
        
        self._next_work_time = next_work_time
        
        self._scheduler.WorkTimesHaveChanged()
        
    
    def WakeOnPubSub( self, topic ) -> None:
        
        HG.controller.sub( self, 'PubSubWake', topic )
        
    
    def WaitingOnWorkSlot( self ):
        
        if self._thread_slot_type is not None:
            
            if not self._currently_working.set() and self.IsDue() and not HG.controller.ThreadSlotsAreAvailable( self._thread_slot_type ):
                
                return True
                
            
        
        return False
        
    
    def Work( self ) -> None:
        
        try:
            
            if self._should_delay_on_wakeup:
                
                while HG.controller.JustWokeFromSleep():
                    
                    if IsThreadShuttingDown():
                        
                        return
                        
                    
                    time.sleep( 1 )
                    
                
            
            with self._work_lock:
                
                self._actual_work_started.set()
                
                self._work_callable()
                
            
        finally:
            
            if self._thread_slot_type is not None:
                
                HG.controller.ReleaseThreadSlot( self._thread_slot_type )
                
            
            self._actual_work_started.clear()
            self._currently_working.clear()
            
        
    

class SingleJob( SchedulableJob ):
    
    PRETTY_CLASS_NAME = 'single job'
    
    def __init__( self, controller, scheduler: JobScheduler, initial_delay, work_callable ):
        
        super().__init__( controller, scheduler, initial_delay, work_callable )
        
        self._work_complete = threading.Event()
        
    
    def IsWorkComplete( self ) -> bool:
        
        return self._work_complete.is_set()
        
    
    def Work( self ) -> None:
        
        SchedulableJob.Work( self )
        
        self._work_complete.set()
        
    

class RepeatingJob( SchedulableJob ):
    
    PRETTY_CLASS_NAME = 'repeating job'
    
    def __init__( self, controller, scheduler: JobScheduler, initial_delay, period, work_callable ):
        
        super().__init__( controller, scheduler, initial_delay, work_callable )
        
        self._period = period
        
        self._stop_repeating = threading.Event()
        
    
    def Cancel( self ) -> None:
        
        SchedulableJob.Cancel( self )
        
        self._stop_repeating.set()
        
    
    def StartWork( self ) -> None:
        
        if self._stop_repeating.is_set():
            
            return
            
        
        SchedulableJob.StartWork( self )
        
    
    def Work( self ) -> None:
        
        SchedulableJob.Work( self )
        
        if not self._stop_repeating.is_set():
            
            self._next_work_time = HydrusTime.GetNowFloat() + self._period
            
            self._scheduler.AddJob( self )
            
        
    
