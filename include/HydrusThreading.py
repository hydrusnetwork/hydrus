import bisect
import collections
from . import HydrusExceptions
import queue
import random
import threading
import time
import traceback
from . import HydrusData
from . import HydrusGlobals as HG
import os

NEXT_THREAD_CLEAROUT = 0

THREADS_TO_THREAD_INFO = {}
THREAD_INFO_LOCK = threading.Lock()

def CheckIfThreadShuttingDown():
    
    if IsThreadShuttingDown():
        
        raise HydrusExceptions.ShutdownException( 'Thread is shutting down!' )
        
    
def ClearOutDeadThreads():
    
    with THREAD_INFO_LOCK:
        
        all_threads = list( THREADS_TO_THREAD_INFO.keys() )
        
        for thread in all_threads:
            
            if not thread.is_alive():
                
                del THREADS_TO_THREAD_INFO[ thread ]
                
            
        
    
def GetThreadInfo( thread = None ):
    
    global NEXT_THREAD_CLEAROUT
    
    if HydrusData.TimeHasPassed( NEXT_THREAD_CLEAROUT ):
        
        ClearOutDeadThreads()
        
        NEXT_THREAD_CLEAROUT = HydrusData.GetNow() + 600
        
    
    if thread is None:
        
        thread = threading.current_thread()
        
    
    with THREAD_INFO_LOCK:
        
        if thread not in THREADS_TO_THREAD_INFO:
            
            thread_info = {}
            
            thread_info[ 'shutting_down' ] = False
            
            THREADS_TO_THREAD_INFO[ thread ] = thread_info
            
        
        return THREADS_TO_THREAD_INFO[ thread ]
        
    
def IsThreadShuttingDown():
    
    me = threading.current_thread()
    
    if isinstance( me, DAEMON ):
        
        if HG.view_shutdown:
            
            return True
            
        
    else:
        
        if HG.model_shutdown:
            
            return True
            
        
    
    thread_info = GetThreadInfo()
    
    return thread_info[ 'shutting_down' ]
    
def ShutdownThread( thread ):
    
    thread_info = GetThreadInfo( thread )
    
    thread_info[ 'shutting_down' ] = True
    
class DAEMON( threading.Thread ):
    
    def __init__( self, controller, name ):
        
        threading.Thread.__init__( self, name = name )
        
        self._controller = controller
        self._name = name
        
        self._event = threading.Event()
        
        self._controller.sub( self, 'wake', 'wake_daemons' )
        self._controller.sub( self, 'shutdown', 'shutdown' )
        
    
    def _DoPreCall( self ):
        
        if HG.daemon_report_mode:
            
            HydrusData.ShowText( self._name + ' doing a job.' )
            
        
    
    def GetCurrentJobSummary( self ):
        
        return 'unknown job'
        
    
    def GetName( self ):
        
        return self._name
        
    
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
        
    
    def _CanStart( self ):
        
        return self._ControllerIsOKWithIt()
        
    
    def _ControllerIsOKWithIt( self ):
        
        return True
        
    
    def _DoAWait( self, wait_time, event_can_wake = True ):
        
        time_to_start = HydrusData.GetNow() + wait_time
        
        while not HydrusData.TimeHasPassed( time_to_start ):
            
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
        
    
    def run( self ):
        
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
                    
                    return
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Daemon ' + self._name + ' encountered an exception:' )
                    
                    HydrusData.ShowException( e )
                    
                
                self._DoAWait( self._period )
                
            
        except HydrusExceptions.ShutdownException:
            
            return
            
        
    
    def set( self, *args, **kwargs ):
        
        self._event.set()
        
    
# Big stuff like DB maintenance that we don't want to run while other important stuff is going on, like user interaction or vidya on another process
class DAEMONBackgroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ):
        
        return self._controller.GoodTimeToStartBackgroundWork()
        
    
# Big stuff that we want to run when the user sees, but not at the expense of something else, like laggy session load
class DAEMONForegroundWorker( DAEMONWorker ):
    
    def _ControllerIsOKWithIt( self ):
        
        return self._controller.GoodTimeToStartForegroundWork()
        
    
class THREADCallToThread( DAEMON ):
    
    def __init__( self, controller, name ):
        
        DAEMON.__init__( self, controller, name )
        
        self._callable = None
        
        self._queue = queue.Queue()
        
        self._currently_working = True # start off true so new threads aren't used twice by two quick successive calls
        
    
    def CurrentlyWorking( self ):
        
        return self._currently_working
        
    
    def GetCurrentJobSummary( self ):
        
        return self._callable
        
    
    def put( self, callable, *args, **kwargs ):
        
        self._currently_working = True
        
        self._queue.put( ( callable, args, kwargs ) )
        
        self._event.set()
        
    
    def run( self ):
        
        try:
            
            while True:
                
                while self._queue.empty():
                    
                    CheckIfThreadShuttingDown()
                    
                    self._event.wait( 10.0 )
                    
                    self._event.clear()
                    
                
                CheckIfThreadShuttingDown()
                
                self._DoPreCall()
                
                try:
                    
                    ( callable, args, kwargs ) = self._queue.get()
                    
                    self._callable = ( callable, args, kwargs )
                    
                    callable( *args, **kwargs )
                    
                    self._callable = None
                    
                    del callable
                    
                except HydrusExceptions.ShutdownException:
                    
                    return
                    
                except Exception as e:
                    
                    HydrusData.Print( traceback.format_exc() )
                    
                    HydrusData.ShowException( e )
                    
                finally:
                    
                    self._currently_working = False
                    
                
                time.sleep( 0.00001 )
                
            
        except HydrusExceptions.ShutdownException:
            
            return
            
        
    
class JobScheduler( threading.Thread ):
    
    def __init__( self, controller ):
        
        threading.Thread.__init__( self, name = 'Job Scheduler' )
        
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
        
    
    def _NoWorkToStart( self ):
        
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
            
        
    
    def _StartWork( self ):
        
        jobs_started = 0
        
        while True:
            
            with self._waiting_lock:
                
                if len( self._waiting ) == 0:
                    
                    break
                    
                
                if jobs_started >= 10: # try to avoid spikes
                    
                    break
                    
                
                next_job = self._waiting[0]
                
                if next_job.IsDue():
                    
                    next_job = self._waiting.pop( 0 )
                    
                    if next_job.IsCancelled():
                        
                        continue
                        
                    
                    if next_job.SlotOK():
                        
                        next_job.StartWork()
                        
                        jobs_started += 1
                        
                    else:
                        
                        # delay is automatically set by SlotOK
                        
                        bisect.insort( self._waiting, next_job )
                        
                    
                else:
                    
                    break # all the rest in the queue are not due
                    
                
            
        
    
    def AddJob( self, job ):
        
        with self._waiting_lock:
            
            bisect.insort( self._waiting, job )
            
        
        self._new_job_arrived.set()
        
    
    def ClearOutDead( self ):
        
        with self._waiting_lock:
            
            self._waiting = [ job for job in self._waiting if not job.IsDead() ]
            
        
    
    def GetName( self ):
        
        return 'Job Scheduler'
        
    
    def GetCurrentJobSummary( self ):
        
        with self._waiting_lock:
            
            return HydrusData.ToHumanInt( len( self._waiting ) ) + ' jobs'
            
        
    
    def GetPrettyJobSummary( self ):
        
        with self._waiting_lock:
            
            num_jobs = len( self._waiting )
            
            job_lines = [ repr( job ) for job in self._waiting ]
            
            lines = [ HydrusData.ToHumanInt( num_jobs ) + ' jobs:' ] + job_lines
            
            text = os.linesep.join( lines )
            
            return text
            
        
    
    def JobCancelled( self ):
        
        self._cancel_filter_needed.set()
        
    
    def shutdown( self ):
        
        ShutdownThread( self )
        
    
    def WorkTimesHaveChanged( self ):
        
        self._sort_needed.set()
        
    
    def run( self ):
        
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
                
                return
                
            except Exception as e:
                
                HydrusData.Print( traceback.format_exc() )
                
                HydrusData.ShowException( e )
                
            
            time.sleep( 0.00001 )
            
        
    
class SchedulableJob( object ):
    
    def __init__( self, controller, scheduler, initial_delay, work_callable ):
        
        self._controller = controller
        self._scheduler = scheduler
        self._work_callable = work_callable
        
        self._should_delay_on_wakeup = False
        
        self._next_work_time = HydrusData.GetNowFloat() + initial_delay
        
        self._thread_slot_type = None
        
        self._work_lock = threading.Lock()
        
        self._currently_working = threading.Event()
        self._is_cancelled = threading.Event()
        
    
    def __lt__( self, other ): # for the scheduler to do bisect.insort noice
        
        return self._next_work_time < other._next_work_time
        
    
    def __repr__( self ):
        
        return repr( self.__class__ ) + ': ' + repr( self._work_callable ) + ' next in ' + HydrusData.TimeDeltaToPrettyTimeDelta( self._next_work_time - HydrusData.GetNowFloat() )
        
    
    def _BootWorker( self ):
        
        self._controller.CallToThread( self.Work )
        
    
    def Cancel( self ):
        
        self._is_cancelled.set()
        
        self._scheduler.JobCancelled()
        
    
    def CurrentlyWorking( self ):
        
        return self._currently_working.is_set()
        
    
    def GetTimeDeltaUntilDue( self ):
        
        return HydrusData.GetTimeDeltaUntilTimeFloat( self._next_work_time )
        
    
    def IsCancelled( self ):
        
        return self._is_cancelled.is_set()
        
    
    def IsDead( self ):
        
        return False
        
    
    def IsDue( self ):
        
        return HydrusData.TimeHasPassedFloat( self._next_work_time )
        
    
    def PubSubWake( self, *args, **kwargs ):
        
        self.Wake()
        
    
    def SetThreadSlotType( self, thread_type ):
        
        self._thread_slot_type = thread_type
        
    
    def ShouldDelayOnWakeup( self, value ):
        
        self._should_delay_on_wakeup = value
        
    
    def SlotOK( self ):
        
        if self._thread_slot_type is not None:
            
            if HG.controller.AcquireThreadSlot( self._thread_slot_type ):
                
                return True
                
            else:
                
                self._next_work_time = HydrusData.GetNowFloat() + 10 + random.random()
                
                return False
                
            
        
        return True
        
    
    def StartWork( self ):
        
        if self._is_cancelled.is_set():
            
            return
            
        
        self._currently_working.set()
        
        self._BootWorker()
        
    
    def Wake( self, next_work_time = None ):
        
        if next_work_time is None:
            
            next_work_time = HydrusData.GetNowFloat()
            
        
        self._next_work_time = next_work_time
        
        self._scheduler.WorkTimesHaveChanged()
        
    
    def WakeOnPubSub( self, topic ):
        
        HG.controller.sub( self, 'PubSubWake', topic )
        
    
    def Work( self ):
        
        try:
            
            if self._should_delay_on_wakeup:
                
                while HG.controller.JustWokeFromSleep():
                    
                    if IsThreadShuttingDown():
                        
                        return
                        
                    
                    time.sleep( 1 )
                    
                
            
            with self._work_lock:
                
                self._work_callable()
                
            
        finally:
            
            if self._thread_slot_type is not None:
                
                HG.controller.ReleaseThreadSlot( self._thread_slot_type )
                
            
            self._currently_working.clear()
            
        
    
class RepeatingJob( SchedulableJob ):
    
    def __init__( self, controller, scheduler, initial_delay, period, work_callable ):
        
        SchedulableJob.__init__( self, controller, scheduler, initial_delay, work_callable )
        
        self._period = period
        
        self._stop_repeating = threading.Event()
        
    
    def Cancel( self ):
        
        SchedulableJob.Cancel( self )
        
        self._stop_repeating.set()
        
    
    def Delay( self, delay ):
        
        self._next_work_time = HydrusData.GetNowFloat() + delay
        
        self._scheduler.WorkTimesHaveChanged()
        
    
    def IsFinishedWorking( self ):
        
        return self._stop_repeating.is_set()
        
    
    def SetPeriod( self, period ):
        
        if period > 10.0:
            
            period += random.random() # smooth out future spikes if ten of these all fire at the same time
            
        
        self._period = period
        
    
    def StartWork( self ):
        
        if self._stop_repeating.is_set():
            
            return
            
        
        SchedulableJob.StartWork( self )
        
    
    def Work( self ):
        
        SchedulableJob.Work( self )
        
        if not self._stop_repeating.is_set():
            
            self._next_work_time = HydrusData.GetNowFloat() + self._period
            
            self._scheduler.AddJob( self )
            
        
    
