import collections
import collections.abc
import os
import random
import sys
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLogger
from hydrus.core import HydrusPaths
from hydrus.core import HydrusPubSub
from hydrus.core import HydrusTemp
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNATPunch
from hydrus.core.processes import HydrusProcess
from hydrus.core.processes import HydrusSubprocess
from hydrus.core.processes import HydrusThreading

class HydrusController( object ):
    
    def __init__( self, db_dir: str, logger: HydrusLogger.HydrusLogger ):
        
        super().__init__()
        
        HG.controller = self
        
        self._name = 'hydrus'
        
        self._last_shutdown_was_bad = False
        self._i_own_running_file = False
        
        self.db_dir = db_dir
        self.logger = logger
        
        self.db = None
        
        pubsub_valid_callable = self._GetPubsubValidCallable()
        
        self._pubsub = HydrusPubSub.HydrusPubSub( pubsub_valid_callable )
        self._daemon_jobs = {}
        self._managers = {}
        
        self._fast_job_scheduler = None
        self._slow_job_scheduler = None
        
        self._thread_slots = {}
        
        self._thread_slots[ 'misc' ] = ( 0, 10 )
        
        self._thread_slot_lock = threading.Lock()
        
        self._call_to_threads = []
        self._long_running_call_to_threads = []
        
        self._thread_pool_busy_status_text = ''
        self._thread_pool_busy_status_text_new_check_time = 0
        
        self._call_to_thread_lock = threading.Lock()
        
        self._timestamps_lock = threading.Lock()
        
        self._timestamps_ms = collections.defaultdict( lambda: 0 )
        
        self._sleep_lock = threading.Lock()
        
        self._just_woke_from_sleep = False
        
        self._system_busy = False
        
        self._doing_fast_exit = False
        
        self.TouchTime( 'boot' )
        self.TouchTime( 'last_sleep_check' )
        
    
    def _GetCallToThread( self ):
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            # all the threads in the pool are currently busy
            
            ok_to_make_one = len( self._call_to_threads ) < 200
            
            if not ok_to_make_one:
                
                my_thread = threading.current_thread()
                
                calling_from_the_thread_pool = my_thread in self._call_to_threads or my_thread in self._long_running_call_to_threads
                
                ok_to_make_one = calling_from_the_thread_pool
                
            
            if ok_to_make_one:
                
                call_to_thread = HydrusThreading.THREADCallToThread( self, 'CallToThread' )
                
                self._call_to_threads.append( call_to_thread )
                
                call_to_thread.start()
                
            else:
                
                call_to_thread = random.choice( self._call_to_threads )
                
            
            return call_to_thread
            
        
    
    def _GetCallToThreadLongRunning( self ):
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._long_running_call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            call_to_thread = HydrusThreading.THREADCallToThread( self, 'CallToThreadLongRunning' )
            
            self._long_running_call_to_threads.append( call_to_thread )
            
            call_to_thread.start()
            
            return call_to_thread
            
        
    
    def _GetPubsubValidCallable( self ):
        
        return lambda o: True
        
    
    def _GetAppropriateJobScheduler( self, time_delta ):
        
        if time_delta <= 1.0:
            
            return self._fast_job_scheduler
            
        else:
            
            return self._slow_job_scheduler
            
        
    
    def _GetUPnPServices( self ):
        
        return []
        
    
    def _GetWakeDelayPeriodMS( self ):
        
        return 15 * 1000
        
    
    def _InitDB( self ):
        
        raise NotImplementedError()
        
    
    def _InitHydrusTempDir( self ):
        
        self._hydrus_temp_dir = HydrusTemp.InitialiseHydrusTempDir()
        
    
    def _MaintainCallToThreads( self ):
        
        # we don't really want to hang on to threads that are done as event.wait() has a bit of idle cpu
        # so, any that are in the pools that aren't doing anything can be killed and sent to garbage
        
        with self._call_to_thread_lock:
            
            def filter_call_to_threads( t ):
                
                if t.CurrentlyWorking():
                    
                    return True
                    
                else:
                    
                    t.shutdown()
                    
                    return False
                    
                
            
            self._call_to_threads = list( filter( filter_call_to_threads, self._call_to_threads ) )
            
            self._long_running_call_to_threads = list( filter( filter_call_to_threads, self._long_running_call_to_threads ) )
            
        
    
    def _PublishShutdownSubtext( self, text ):
        
        pass
        
    
    def _Read( self, action, *args, **kwargs ):
        
        result = self.db.Read( action, *args, **kwargs )
        
        return result
        
    
    def _ReportShutdownDaemonsStatus( self ):
        
        pass
        
    
    def _ShowJustWokeToUser( self ) -> None:
        
        HydrusData.Print( 'Just woke from sleep.' )
        
    
    def _ShutdownDaemons( self ):
        
        for job in self._daemon_jobs.values():
            
            job.Cancel()
            
        
        if not self._doing_fast_exit:
            
            started = HydrusTime.GetNow()
            
            while True in ( daemon_job.CurrentlyWorking() for daemon_job in self._daemon_jobs.values() ):
                
                self._ReportShutdownDaemonsStatus()
                
                time.sleep( 0.1 )
                
                if HydrusTime.TimeHasPassed( started + 30 ):
                    
                    break
                    
                
            
        
        self._daemon_jobs = {}
        
    
    def _Write( self, action, synchronous, *args, **kwargs ):
        
        result = self.db.Write( action, synchronous, *args, **kwargs )
        
        return result
        
    
    def pub( self, topic, *args, **kwargs ) -> None:
        
        if HG.model_shutdown:
            
            self._pubsub.pubimmediate( topic, *args, **kwargs )
            
        else:
            
            self._pubsub.pub( topic, *args, **kwargs )
            
        
    
    def pubimmediate( self, topic, *args, **kwargs ) -> None:
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ) -> None:
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def AcquireThreadSlot( self, thread_type ) -> bool:
        
        with self._thread_slot_lock:
            
            if thread_type not in self._thread_slots:
                
                return True # assume no max if no max set
                
            
            ( current_threads, max_threads ) = self._thread_slots[ thread_type ]
            
            if current_threads < max_threads:
                
                self._thread_slots[ thread_type ] = ( current_threads + 1, max_threads )
                
                return True
                
            else:
                
                return False
                
            
        
    
    def BlockingSafeShowCriticalMessage( self, title: str, message: str ):
        
        HydrusData.DebugPrint( title )
        HydrusData.DebugPrint( message )
        
        input( 'Press Enter to continue.' )
        
    
    def BlockingSafeShowMessage( self, message: str ):
        
        HydrusData.DebugPrint( message )
        
        input( 'Press Enter to continue.' )
        
    
    def ThreadSlotsAreAvailable( self, thread_type ) -> bool:
        
        with self._thread_slot_lock:
            
            if thread_type not in self._thread_slots:
                
                return True # assume no max if no max set
                
            
            ( current_threads, max_threads ) = self._thread_slots[ thread_type ]
            
            return current_threads < max_threads
            
        
    
    def CallLater( self, initial_delay, func, *args, **kwargs ) -> HydrusThreading.SingleJob:
        
        job_scheduler = self._GetAppropriateJobScheduler( initial_delay )
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.SingleJob( self, job_scheduler, initial_delay, call )
        
        job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeating( self, initial_delay, period, func, *args, **kwargs ) -> HydrusThreading.RepeatingJob:
        
        job_scheduler = self._GetAppropriateJobScheduler( period )
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.RepeatingJob( self, job_scheduler, initial_delay, period, call )
        
        job_scheduler.AddJob( job )
        
        return job
        
    
    def CallToThread( self, callable, *args, **kwargs ) -> None:
        
        if HG.callto_report_mode:
            
            what_to_report = [ callable ]
            
            if len( args ) > 0:
                
                what_to_report.append( args )
                
            
            if len( kwargs ) > 0:
                
                what_to_report.append( kwargs )
                
            
            HydrusData.ShowText( tuple( what_to_report ) )
            
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def CallToThreadLongRunning( self, callable, *args, **kwargs ) -> None:
        
        if HG.callto_report_mode:
            
            what_to_report = [ callable ]
            
            if len( args ) > 0:
                
                what_to_report.append( args )
                
            
            if len( kwargs ) > 0:
                
                what_to_report.append( kwargs )
                
            
            HydrusData.ShowText( tuple( what_to_report ) )
            
        
        call_to_thread = self._GetCallToThreadLongRunning()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def CleanRunningFile( self ) -> None:
        
        if self._i_own_running_file:
            
            HydrusData.CleanRunningFile( self.db_dir, self._name )
            
        
    
    def ClearCaches( self ) -> None:
        
        pass
        
    
    def CurrentlyIdle( self ) -> bool:
        
        return True
        
    
    def CurrentlyPubSubbing( self ) -> bool:
        
        return self._pubsub.WorkToDo() or self._pubsub.DoingWork()
        
    
    def DBCurrentlyDoingJob( self ) -> bool:
        
        if self.db is None:
            
            return False
            
        else:
            
            return self.db.CurrentlyDoingJob()
            
        
    
    def DebugShowScheduledJobs( self ):
        
        summary = self._fast_job_scheduler.GetPrettyJobSummary()
        
        HydrusData.ShowText( 'fast scheduler:' )
        HydrusData.ShowText( summary )
        
        summary = self._slow_job_scheduler.GetPrettyJobSummary()
        
        HydrusData.ShowText( 'slow scheduler:' )
        HydrusData.ShowText( summary )
        
    
    def DoingFastExit( self ) -> bool:
        
        return self._doing_fast_exit
        
    
    def ForceDatabaseCommit( self ):
        
        if self.db is None:
            
            raise Exception( 'Sorry, database does not seem to be alive at the moment!' )
            
        
        self.db.ForceACommit()
        
    
    def GetBootTimestampMS( self ):
        
        return self.GetTimestampMS( 'boot' )
        
    
    def GetDBDir( self ):
        
        return self.db_dir
        
    
    def GetDBStatus( self ):
        
        return self.db.GetStatus()
        
    
    def GetHydrusTempDir( self ):
        
        if not os.path.exists( self._hydrus_temp_dir ):
            
            self._InitHydrusTempDir()
            
        
        return self._hydrus_temp_dir
        
    
    def GetJobSchedulerSnapshot( self, scheduler_name ):
        
        if scheduler_name == 'fast':
            
            scheduler = self._fast_job_scheduler
            
        else:
            
            scheduler = self._slow_job_scheduler
            
        
        return scheduler.GetJobs()
        
    
    def GetManager( self, name ):
        
        return self._managers[ name ]
        
    
    def GetName( self ):
        
        return self._name
        
    
    def GetThreadPoolBusyStatus( self ):
        
        if HydrusTime.TimeHasPassed( self._thread_pool_busy_status_text_new_check_time ):
            
            with self._call_to_thread_lock:
                
                num_threads = sum( ( 1 for t in self._call_to_threads if t.CurrentlyWorking() ) )
                
            
            if num_threads < 4:
                
                self._thread_pool_busy_status_text = ''
                
            elif num_threads < 10:
                
                self._thread_pool_busy_status_text = 'working'
                
            elif num_threads < 20:
                
                self._thread_pool_busy_status_text = 'busy'
                
            else:
                
                self._thread_pool_busy_status_text = 'very busy!'
                
            
            self._thread_pool_busy_status_text_new_check_time = HydrusTime.GetNow() + 10
            
        
        return self._thread_pool_busy_status_text
        
    
    def GetThreadsSnapshot( self ):
        
        threads = []
        
        threads.extend( self._call_to_threads )
        threads.extend( self._long_running_call_to_threads )
        
        threads.append( self._slow_job_scheduler )
        threads.append( self._fast_job_scheduler )
        
        return threads
        
    
    def GetTimestampMS( self, name: str ) -> int:
        
        with self._timestamps_lock:
            
            return self._timestamps_ms[ name ]
            
        
    
    def GoodTimeToStartBackgroundWork( self ) -> bool:
        
        return self.CurrentlyIdle() and not ( self.JustWokeFromSleep() or self.SystemBusy() )
        
    
    def GoodTimeToStartForegroundWork( self ) -> bool:
        
        return not self.JustWokeFromSleep()
        
    
    def JustWokeFromSleep( self ):
        
        self.SleepCheck()
        
        return self._just_woke_from_sleep
        
    
    def InitModel( self ) -> None:
        
        try:
            
            self._InitHydrusTempDir()
            
        except Exception as e:
            
            HydrusData.Print( 'Failed to initialise temp folder.' )
            
        
        from hydrus.core.files import HydrusFileHandling
        
        HydrusFileHandling.InitialiseMimesToDefaultThumbnailPaths()
        
        self._fast_job_scheduler = HydrusThreading.JobScheduler( self )
        self._slow_job_scheduler = HydrusThreading.JobScheduler( self )
        
        self._fast_job_scheduler.start()
        self._slow_job_scheduler.start()
        
        self._InitDB()
        
        # reset after a long db update
        self.TouchTime( 'last_sleep_check' )
        
    
    def InitView( self ):
        
        job = self.CallRepeating( 60.0, 300.0, self.MaintainDB, maintenance_mode = HC.MAINTENANCE_IDLE )
        
        job.WakeOnPubSub( 'wake_idle_workers' )
        job.ShouldDelayOnWakeup( True )
        
        self._daemon_jobs[ 'maintain_db' ] = job
        
        job = self.CallRepeating( 0.0, 15.0, self.SleepCheck )
        
        self._daemon_jobs[ 'sleep_check' ] = job
        
        job = self.CallRepeating( 10.0, 60.0, self.MaintainMemoryFast )
        
        self._daemon_jobs[ 'maintain_memory_fast' ] = job
        
        job = self.CallRepeating( 10.0, 300.0, self.MaintainMemorySlow )
        
        self._daemon_jobs[ 'maintain_memory_slow' ] = job
        
        upnp_services = self._GetUPnPServices()
        
        self.services_upnp_manager = HydrusNATPunch.ServicesUPnPManager( upnp_services )
        
        job = self.CallRepeating( 10.0, 43200.0, self.services_upnp_manager.RefreshUPnP )
        
        self._daemon_jobs[ 'services_upnp' ] = job
        
    
    def IsFirstStart( self ):
        
        if self.db is None:
            
            return False
            
        else:
            
            return self.db.IsFirstStart()
            
        
    
    def LastShutdownWasBad( self ):
        
        return self._last_shutdown_was_bad
        
    
    def MaintainDB( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        pass
        
    
    def MaintainMemoryFast( self ):
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        self.pub( 'memory_maintenance_pulse' )
        
        self._fast_job_scheduler.ClearOutDead()
        self._slow_job_scheduler.ClearOutDead()
        
        HydrusSubprocess.ReapDeadLongLivedExternalProcesses()
        
    
    def MaintainMemorySlow( self ):
        
        HydrusTemp.CleanUpOldTempPaths()
        
        self._MaintainCallToThreads()
        
    
    def Read( self, action, *args, **kwargs ):
        
        return self._Read( action, *args, **kwargs )
        
    
    def RecordRunningStart( self ):
        
        self._last_shutdown_was_bad = HydrusData.LastShutdownWasBad( self.db_dir, self._name )
        
        self._i_own_running_file = True
        
        HydrusProcess.RecordRunningStart( self.db_dir, self._name )
        
    
    def ReleaseThreadSlot( self, thread_type ):
        
        with self._thread_slot_lock:
            
            if thread_type not in self._thread_slots:
                
                return
                
            
            ( current_threads, max_threads ) = self._thread_slots[ thread_type ]
            
            self._thread_slots[ thread_type ] = ( current_threads - 1, max_threads )
            
        
    
    def ReportDataUsed( self, num_bytes ):
        
        pass
        
    
    def ReportRequestUsed( self ):
        
        pass
        
    
    def ResetIdleTimer( self ) -> None:
        
        self.TouchTime( 'last_user_action' )
        
    
    def SetTimestampMS( self, name: str, timestamp_ms: int ) -> None:
        
        with self._timestamps_lock:
            
            self._timestamps_ms[ name ] = timestamp_ms
            
        
    
    def ShouldStopThisWork( self, maintenance_mode, stop_time = None ) -> bool:
        
        if maintenance_mode == HC.MAINTENANCE_IDLE:
            
            if not self.CurrentlyIdle():
                
                return True
                
            
        elif maintenance_mode == HC.MAINTENANCE_SHUTDOWN:
            
            if not HG.do_idle_shutdown_work:
                
                return True
                
            
        
        if stop_time is not None:
            
            if HydrusTime.TimeHasPassed( stop_time ):
                
                return True
                
            
        
        return False
        
    
    def ShutdownModel( self ) -> None:
        
        if self.db is not None:
            
            self.db.Shutdown()
            
            if not self._doing_fast_exit:
                
                while not self.db.LoopIsFinished():
                    
                    self._PublishShutdownSubtext( 'waiting for db to finish up' + HC.UNICODE_ELLIPSIS )
                    
                    time.sleep( 0.1 )
                    
                
            
        
        if self._fast_job_scheduler is not None:
            
            self._fast_job_scheduler.shutdown()
            
            self._fast_job_scheduler = None
            
        
        if self._slow_job_scheduler is not None:
            
            self._slow_job_scheduler.shutdown()
            
            self._slow_job_scheduler = None
            
        
        HydrusTemp.CleanUpOldTempPaths()
        
        if hasattr( self, '_hydrus_temp_dir' ):
            
            HydrusPaths.DeletePath( self._hydrus_temp_dir )
            
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._call_to_threads:
                
                call_to_thread.shutdown()
                
            
            for long_running_call_to_thread in self._long_running_call_to_threads:
                
                long_running_call_to_thread.shutdown()
                
            
        
        HG.model_shutdown = True
        
        self._pubsub.Wake()
        
    
    def ShutdownView( self ) -> None:
        
        HG.view_shutdown = True
        
        self._ShutdownDaemons()
        
    
    def ShutdownFromServer( self ):
        
        raise Exception( 'This hydrus application cannot be shut down from the server!' )
        
    
    def SleepCheck( self ) -> None:
        
        with self._sleep_lock:
            
            if HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_sleep_check' ) + 60000 ): # it has been way too long since this method last fired, so we've prob been asleep
                
                self._just_woke_from_sleep = True
                
                self.ResetIdleTimer() # this will stop the background jobs from kicking in as soon as the grace period is over
                
                wake_delay_period_ms = self._GetWakeDelayPeriodMS()
                
                self.SetTimestampMS( 'now_awake', HydrusTime.GetNowMS() + wake_delay_period_ms ) # enough time for ethernet to get back online and all that
                
                self._ShowJustWokeToUser()
                
            elif self._just_woke_from_sleep and HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'now_awake' ) ):
                
                self._just_woke_from_sleep = False
                
            
            self.TouchTime( 'last_sleep_check' )
            
        
    
    def SimulateWakeFromSleepEvent( self ) -> None:
        
        with self._sleep_lock:
            
            self.SetTimestampMS( 'last_sleep_check', HydrusTime.GetNowMS() - ( 3600 * 1000 ) )
            
        
        self.SleepCheck()
        
    
    def SystemBusy( self ):
        
        return self._system_busy
        
    
    def TouchTime( self, name: str ) -> None:
        
        with self._timestamps_lock:
            
            self._timestamps_ms[ name ] = HydrusTime.GetNowMS()
            
        
    
    def WaitUntilDBEmpty( self ) -> None:
        
        self.db.WaitUntilFree()
        
    
    def WaitUntilModelFree( self ) -> None:
        
        self.WaitUntilPubSubsEmpty()
        
        self.WaitUntilDBEmpty()
        
    
    def WaitUntilPubSubsEmpty( self ):
        
        self._pubsub.WaitUntilFree()
        
    
    def WakeDaemon( self, name ):
        
        if name in self._daemon_jobs:
            
            self._daemon_jobs[ name ].Wake()
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        return self._Write( action, True, *args, **kwargs )
        
    
