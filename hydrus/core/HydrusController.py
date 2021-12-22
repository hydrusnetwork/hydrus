import collections
import os
import random
import sys
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusPubSub
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTemp
from hydrus.core.networking import HydrusNATPunch

class HydrusController( object ):
    
    def __init__( self, db_dir ):
        
        HG.controller = self
        
        self._name = 'hydrus'
        
        self._last_shutdown_was_bad = False
        self._i_own_running_file = False
        
        self.db_dir = db_dir
        
        self.db = None
        
        pubsub_valid_callable = self._GetPubsubValidCallable()
        
        self._pubsub = HydrusPubSub.HydrusPubSub( self, pubsub_valid_callable )
        self._daemon_jobs = {}
        self._caches = {}
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
        
        self._timestamps = collections.defaultdict( lambda: 0 )
        
        self._timestamps[ 'boot' ] = HydrusData.GetNow()
        
        self._timestamps[ 'last_sleep_check' ] = HydrusData.GetNow()
        
        self._sleep_lock = threading.Lock()
        
        self._just_woke_from_sleep = False
        
        self._system_busy = False
        
        self._doing_fast_exit = False
        
    
    def _GetCallToThread( self ):
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            # all the threads in the pool are currently busy
            
            calling_from_the_thread_pool = threading.current_thread() in self._call_to_threads
            
            if calling_from_the_thread_pool or len( self._call_to_threads ) < 200:
                
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
        
    
    def _GetWakeDelayPeriod( self ):
        
        return 15
        
    
    def _InitDB( self ):
        
        raise NotImplementedError()
        
    
    def _InitTempDir( self ):
        
        self.temp_dir = HydrusTemp.GetTempDir()
        
    
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
        
    
    def _ShowJustWokeToUser( self ):
        
        HydrusData.Print( 'Just woke from sleep.' )
        
    
    def _ShutdownDaemons( self ):
        
        for job in self._daemon_jobs.values():
            
            job.Cancel()
            
        
        started = HydrusData.GetNow()
        
        while True in ( daemon_job.CurrentlyWorking() for daemon_job in self._daemon_jobs.values() ):
            
            self._ReportShutdownDaemonsStatus()
            
            time.sleep( 0.1 )
            
            if HydrusData.TimeHasPassed( started + 30 ):
                
                break
                
            
        
        self._daemon_jobs = {}
        
    
    def _Write( self, action, synchronous, *args, **kwargs ):
        
        result = self.db.Write( action, synchronous, *args, **kwargs )
        
        return result
        
    
    def pub( self, topic, *args, **kwargs ):
        
        if HG.model_shutdown:
            
            self._pubsub.pubimmediate( topic, *args, **kwargs )
            
        else:
            
            self._pubsub.pub( topic, *args, **kwargs )
            
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def AcquireThreadSlot( self, thread_type ):
        
        with self._thread_slot_lock:
            
            if thread_type not in self._thread_slots:
                
                return True # assume no max if no max set
                
            
            ( current_threads, max_threads ) = self._thread_slots[ thread_type ]
            
            if current_threads < max_threads:
                
                self._thread_slots[ thread_type ] = ( current_threads + 1, max_threads )
                
                return True
                
            else:
                
                return False
                
            
        
    
    def CallLater( self, initial_delay, func, *args, **kwargs ):
        
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
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        if HG.callto_report_mode:
            
            what_to_report = [ callable ]
            
            if len( args ) > 0:
                
                what_to_report.append( args )
                
            
            if len( kwargs ) > 0:
                
                what_to_report.append( kwargs )
                
            
            HydrusData.ShowText( tuple( what_to_report ) )
            
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def CallToThreadLongRunning( self, callable, *args, **kwargs ):
        
        if HG.callto_report_mode:
            
            what_to_report = [ callable ]
            
            if len( args ) > 0:
                
                what_to_report.append( args )
                
            
            if len( kwargs ) > 0:
                
                what_to_report.append( kwargs )
                
            
            HydrusData.ShowText( tuple( what_to_report ) )
            
        
        call_to_thread = self._GetCallToThreadLongRunning()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def CleanRunningFile( self ):
        
        if self._i_own_running_file:
            
            HydrusData.CleanRunningFile( self.db_dir, self._name )
            
        
    
    def ClearCaches( self ):
        
        for cache in list(self._caches.values()): cache.Clear()
        
    
    def CurrentlyIdle( self ):
        
        return True
        
    
    def CurrentlyPubSubbing( self ):
        
        return self._pubsub.WorkToDo() or self._pubsub.DoingWork()
        
    
    def DBCurrentlyDoingJob( self ):
        
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
        
    
    def GetBootTime( self ):
        
        return self.GetTimestamp( 'boot' )
        
    
    def GetDBDir( self ):
        
        return self.db_dir
        
    
    def GetDBStatus( self ):
        
        return self.db.GetStatus()
        
    
    def GetCache( self, name ):
        
        return self._caches[ name ]
        
    
    def GetJobSchedulerSnapshot( self, scheduler_name ):
        
        if scheduler_name == 'fast':
            
            scheduler = self._fast_job_scheduler
            
        else:
            
            scheduler = self._slow_job_scheduler
            
        
        return scheduler.GetJobs()
        
    
    def GetManager( self, name ):
        
        return self._managers[ name ]
        
    
    def GetThreadPoolBusyStatus( self ):
        
        if HydrusData.TimeHasPassed( self._thread_pool_busy_status_text_new_check_time ):
            
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
                
            
            self._thread_pool_busy_status_text_new_check_time = HydrusData.GetNow() + 10
            
        
        return self._thread_pool_busy_status_text
        
    
    def GetThreadsSnapshot( self ):
        
        threads = []
        
        threads.extend( self._call_to_threads )
        threads.extend( self._long_running_call_to_threads )
        
        threads.append( self._slow_job_scheduler )
        threads.append( self._fast_job_scheduler )
        
        return threads
        
    
    def GetTimestamp( self, name: str ) -> str:
        
        with self._timestamps_lock:
            
            return self._timestamps[ name ]
            
        
    
    def GoodTimeToStartBackgroundWork( self ):
        
        return self.CurrentlyIdle() and not ( self.JustWokeFromSleep() or self.SystemBusy() )
        
    
    def GoodTimeToStartForegroundWork( self ):
        
        return not self.JustWokeFromSleep()
        
    
    def JustWokeFromSleep( self ):
        
        self.SleepCheck()
        
        return self._just_woke_from_sleep
        
    
    def InitModel( self ):
        
        try:
            
            self._InitTempDir()
            
        except:
            
            HydrusData.Print( 'Failed to initialise temp folder.' )
            
        
        self._fast_job_scheduler = HydrusThreading.JobScheduler( self )
        self._slow_job_scheduler = HydrusThreading.JobScheduler( self )
        
        self._fast_job_scheduler.start()
        self._slow_job_scheduler.start()
        
        self.db = self._InitDB()
        
    
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
        
    
    def MaintainMemorySlow( self ):
        
        HydrusTemp.CleanUpOldTempPaths()
        
        self._MaintainCallToThreads()
        
    
    def PrintProfile( self, summary, profile_text = None ):
        
        pretty_timestamp = time.strftime( '%Y-%m-%d %H-%M-%S', time.localtime( HG.profile_start_time ) )
        
        profile_log_filename = '{} profile - {}.log'.format( self._name, pretty_timestamp )
        
        profile_log_path = os.path.join( self.db_dir, profile_log_filename )
        
        with open( profile_log_path, 'a', encoding = 'utf-8' ) as f:
            
            prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ' )
            
            f.write( prefix + summary )
            
            if profile_text is not None:
                
                f.write( os.linesep * 2 )
                f.write( profile_text )
                
            
        
    
    def PrintQueryPlan( self, query, plan_lines ):
        
        if query in HG.queries_planned:
            
            return
            
        
        HG.queries_planned.add( query )
        
        pretty_timestamp = time.strftime( '%Y-%m-%d %H-%M-%S', time.localtime( HG.query_planner_start_time ) )
        
        query_planner_log_filename = '{} query planner - {}.log'.format( self._name, pretty_timestamp )
        
        query_planner_log_path = os.path.join( self.db_dir, query_planner_log_filename )
        
        with open( query_planner_log_path, 'a', encoding = 'utf-8' ) as f:
            
            prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ' )
            
            if ' ' in query:
                
                first_word = query.split( ' ', 1 )[0]
                
            else:
                
                first_word = 'unknown'
                
            
            f.write( prefix + first_word )
            f.write( os.linesep )
            f.write( query )
            
            if len( plan_lines ) > 0:
                
                f.write( os.linesep )
                f.write( os.linesep.join( ( str( p ) for p in plan_lines ) ) )
                
            
            f.write( os.linesep * 2 )
            
        
    
    def Read( self, action, *args, **kwargs ):
        
        return self._Read( action, *args, **kwargs )
        
    
    def RecordRunningStart( self ):
        
        self._last_shutdown_was_bad = HydrusData.LastShutdownWasBad( self.db_dir, self._name )
        
        self._i_own_running_file = True
        
        HydrusData.RecordRunningStart( self.db_dir, self._name )
        
    
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
        
    
    def ResetIdleTimer( self ):
        
        self.TouchTimestamp( 'last_user_action' )
        
    
    def SetDoingFastExit( self, value: bool ):
        
        self._doing_fast_exit = value
        
    
    def SetTimestamp( self, name: str, value: int ):
        
        with self._timestamps_lock:
            
            self._timestamps[ name ] = value
            
        
    
    def ShouldStopThisWork( self, maintenance_mode, stop_time = None ):
        
        if maintenance_mode == HC.MAINTENANCE_IDLE:
            
            if not self.CurrentlyIdle():
                
                return True
                
            
        elif maintenance_mode == HC.MAINTENANCE_SHUTDOWN:
            
            if not HG.do_idle_shutdown_work:
                
                return True
                
            
        
        if stop_time is not None:
            
            if HydrusData.TimeHasPassed( stop_time ):
                
                return True
                
            
        
        return False
        
    
    def ShutdownModel( self ):
        
        if self.db is not None:
            
            self.db.Shutdown()
            
            while not self.db.LoopIsFinished():
                
                self._PublishShutdownSubtext( 'waiting for db to finish up\u2026' )
                
                time.sleep( 0.1 )
                
            
        
        if self._fast_job_scheduler is not None:
            
            self._fast_job_scheduler.shutdown()
            
            self._fast_job_scheduler = None
            
        
        if self._slow_job_scheduler is not None:
            
            self._slow_job_scheduler.shutdown()
            
            self._slow_job_scheduler = None
            
        
        if hasattr( self, 'temp_dir' ):
            
            HydrusPaths.DeletePath( self.temp_dir )
            
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._call_to_threads:
                
                call_to_thread.shutdown()
                
            
            for long_running_call_to_thread in self._long_running_call_to_threads:
                
                long_running_call_to_thread.shutdown()
                
            
        
        HG.model_shutdown = True
        
        self._pubsub.Wake()
        
    
    def ShutdownView( self ):
        
        HG.view_shutdown = True
        
        self._ShutdownDaemons()
        
    
    def ShutdownFromServer( self ):
        
        raise Exception( 'This hydrus application cannot be shut down from the server!' )
        
    
    def SleepCheck( self ):
        
        with self._sleep_lock:
            
            if HydrusData.TimeHasPassed( self.GetTimestamp( 'last_sleep_check' ) + 60 ): # it has been way too long since this method last fired, so we've prob been asleep
                
                self._just_woke_from_sleep = True
                
                self.ResetIdleTimer() # this will stop the background jobs from kicking in as soon as the grace period is over
                
                wake_delay_period = self._GetWakeDelayPeriod()
                
                self.SetTimestamp( 'now_awake', HydrusData.GetNow() + wake_delay_period ) # enough time for ethernet to get back online and all that
                
                self._ShowJustWokeToUser()
                
            elif self._just_woke_from_sleep and HydrusData.TimeHasPassed( self.GetTimestamp( 'now_awake' ) ):
                
                self._just_woke_from_sleep = False
                
            
            self.TouchTimestamp( 'last_sleep_check' )
            
        
    
    def SimulateWakeFromSleepEvent( self ):
        
        with self._sleep_lock:
            
            self.SetTimestamp( 'last_sleep_check', HydrusData.GetNow() - 3600 )
            
        
        self.SleepCheck()
        
    
    def SystemBusy( self ):
        
        return self._system_busy
        
    
    def TouchTimestamp( self, name: str ):
        
        with self._timestamps_lock:
            
            self._timestamps[ name ] = HydrusData.GetNow()
            
        
    
    def WaitUntilDBEmpty( self ):
        
        while True:
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif self.db.JobsQueueEmpty() and not self.db.CurrentlyDoingJob():
                
                return
                
            else:
                
                time.sleep( 0.00001 )
                
            
        
    
    def WaitUntilModelFree( self ):
        
        self.WaitUntilPubSubsEmpty()
        
        self.WaitUntilDBEmpty()
        
    
    def WaitUntilPubSubsEmpty( self ):
        
        while self.CurrentlyPubSubbing():
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            else:
                
                time.sleep( 0.00001 )
                
            
        
    
    def WakeDaemon( self, name ):
        
        if name in self._daemon_jobs:
            
            self._daemon_jobs[ name ].Wake()
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        return self._Write( action, True, *args, **kwargs )
        
    
