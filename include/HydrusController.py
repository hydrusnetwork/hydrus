import collections
import gc
import HydrusConstants as HC
import HydrusDaemons
import HydrusData
import HydrusDB
import HydrusExceptions
import HydrusGlobals as HG
import HydrusPaths
import HydrusPubSub
import HydrusThreading
import os
import random
import sys
import threading
import time
import traceback

class HydrusController( object ):
    
    def __init__( self, db_dir, no_daemons, no_wal ):
        
        HG.controller = self
        
        self._name = 'hydrus'
        
        self.db_dir = db_dir
        self._no_daemons = no_daemons
        self._no_wal = no_wal
        
        self._no_wal_path = os.path.join( self.db_dir, 'no-wal' )
        
        if os.path.exists( self._no_wal_path ):
            
            self._no_wal = True
            
        
        self.db = None
        
        self._model_shutdown = False
        self._view_shutdown = False
        
        self._pubsub = HydrusPubSub.HydrusPubSub( self )
        self._daemons = []
        self._caches = {}
        self._managers = {}
        
        self._job_scheduler = None
        
        self._call_to_threads = []
        self._long_running_call_to_threads = []
        
        self._call_to_thread_lock = threading.Lock()
        
        self._timestamps = collections.defaultdict( lambda: 0 )
        
        self._timestamps[ 'boot' ] = HydrusData.GetNow()
        
        self._just_woke_from_sleep = False
        self._system_busy = False
        
        self.CallToThreadLongRunning( self.DAEMONPubSub )
        
    
    def _GetCallToThread( self ):
        
        with self._call_to_thread_lock:
            
            for call_to_thread in self._call_to_threads:
                
                if not call_to_thread.CurrentlyWorking():
                    
                    return call_to_thread
                    
                
            
            # all the threads in the pool are currently busy
            
            calling_from_the_thread_pool = threading.current_thread() in self._call_to_threads
            
            if calling_from_the_thread_pool or len( self._call_to_threads ) < 10:
                
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
            
        
    
    def _InitDB( self ):
        
        raise NotImplementedError()
        
    
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
                    
                
            
            self._call_to_threads = filter( filter_call_to_threads, self._call_to_threads )
            
            self._long_running_call_to_threads = filter( filter_call_to_threads, self._long_running_call_to_threads )
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        result = self.db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
        return result
        
    
    def _ReportShutdownDaemonsStatus( self ):
        
        pass
        
    
    def _ShutdownDaemons( self ):
        
        for daemon in self._daemons:
            
            daemon.shutdown()
            
        
        while True in ( daemon.is_alive() for daemon in self._daemons ):
            
            self._ReportShutdownDaemonsStatus()
            
            time.sleep( 0.1 )
            
        
        self._daemons = []
        
    
    def _Write( self, action, priority, synchronous, *args, **kwargs ):
        
        result = self.db.Write( action, priority, synchronous, *args, **kwargs )
        
        return result
        
    
    def pub( self, topic, *args, **kwargs ):
        
        if self._model_shutdown:
            
            self._pubsub.pubimmediate( topic, *args, **kwargs )
            
        else:
            
            self._pubsub.pub( topic, *args, **kwargs )
            
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def CallLater( self, delay, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.SchedulableJob( self, self._job_scheduler, call, initial_delay = delay )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeating( self, period, delay, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.RepeatingJob( self, self._job_scheduler, call, period, initial_delay = delay )
        
        self._job_scheduler.AddJob( job )
        
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
        
    
    def ClearCaches( self ):
        
        for cache in self._caches.values(): cache.Clear()
        
    
    def CreateNoWALFile( self ):
        
        with open( self._no_wal_path, 'wb' ) as f:
            
            f.write( 'This file was created because the database failed to set WAL journalling. It will not reattempt WAL as long as this file exists.' )
            
        
    
    def CurrentlyIdle( self ):
        
        return True
        
    
    def DBCurrentlyDoingJob( self ):
        
        if self.db is None:
            
            return False
            
        else:
            
            return self.db.CurrentlyDoingJob()
            
        
    
    def DebugShowScheduledJobs( self ):
        
        summary = self._job_scheduler.GetPrettyJobSummary()
        
        HydrusData.ShowText( summary )
        
    
    def GetBootTime( self ):
        
        return self._timestamps[ 'boot' ]
        
    
    def GetDBDir( self ):
        
        return self.db_dir
        
    
    def GetDBStatus( self ):
        
        return self.db.GetStatus()
        
    
    def GetCache( self, name ):
        
        return self._caches[ name ]
        
    
    def GetManager( self, name ):
        
        return self._managers[ name ]
        
    
    def GoodTimeToDoBackgroundWork( self ):
        
        return self.CurrentlyIdle() and not ( self.JustWokeFromSleep() or self.SystemBusy() )
        
    
    def GoodTimeToDoForegroundWork( self ):
        
        return True
        
    
    def JustWokeFromSleep( self ):
        
        self.SleepCheck()
        
        return self._just_woke_from_sleep
        
    
    def InitModel( self ):
        
        self.temp_dir = HydrusPaths.GetTempDir()
        
        self._job_scheduler = HydrusThreading.JobScheduler( self )
        
        self._job_scheduler.start()
        
        self.db = self._InitDB()
        
    
    def InitView( self ):
        
        if not self._no_daemons:
            
            self._daemons.append( HydrusThreading.DAEMONBackgroundWorker( self, 'MaintainDB', HydrusDaemons.DAEMONMaintainDB, period = 300, init_wait = 60 ) )
            
        
        self.CallRepeating( 120.0, 10.0, self.SleepCheck )
        self.CallRepeating( 60.0, 10.0, self.MaintainMemoryFast )
        self.CallRepeating( 300.0, 10.0, self.MaintainMemorySlow )
        
    
    def IsFirstStart( self ):
        
        if self.db is None:
            
            return False
            
        else:
            
            return self.db.IsFirstStart()
            
        
    
    def MaintainDB( self, stop_time = None ):
        
        pass
        
    
    def MaintainMemoryFast( self ):
        
        self.pub( 'memory_maintenance_pulse' )
        
        self._job_scheduler.ClearOutDead()
        
    
    def MaintainMemorySlow( self ):
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        gc.collect()
        
        HydrusPaths.CleanUpOldTempPaths()
        
        self._MaintainCallToThreads()
        
    
    def ModelIsShutdown( self ):
        
        return self._model_shutdown
        
    
    def PrintProfile( self, summary, profile_text ):
        
        boot_pretty_timestamp = time.strftime( '%Y-%m-%d %H-%M-%S', time.localtime( self._timestamps[ 'boot' ] ) )
        
        profile_log_filename = self._name + ' profile - ' + boot_pretty_timestamp + '.log'
        
        profile_log_path = os.path.join( self.db_dir, profile_log_filename )
        
        with open( profile_log_path, 'a' ) as f:
            
            prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ' )
            
            f.write( prefix + summary )
            f.write( os.linesep * 2 )
            f.write( profile_text )
            
        
    
    def ProcessPubSub( self ):
        
        self._pubsub.Process()
        
    
    def Read( self, action, *args, **kwargs ):
        
        return self._Read( action, *args, **kwargs )
        
    
    def ReportDataUsed( self, num_bytes ):
        
        pass
        
    
    def ReportRequestUsed( self ):
        
        pass
        
    
    def ShutdownModel( self ):
        
        self._model_shutdown = True
        HG.model_shutdown = True
        
        if self.db is not None:
            
            while not self.db.LoopIsFinished():
                
                time.sleep( 0.1 )
                
            
        
        if self._job_scheduler is not None:
            
            self._job_scheduler.shutdown()
            
            self._job_scheduler = None
            
        
        if hasattr( self, 'temp_dir' ):
            
            HydrusPaths.DeletePath( self.temp_dir )
            
        
    
    def ShutdownView( self ):
        
        self._view_shutdown = True
        HG.view_shutdown = True
        
        self._ShutdownDaemons()
        
    
    def ShutdownFromServer( self ):
        
        raise Exception( 'This hydrus application cannot be shut down from the server!' )
        
    
    def SleepCheck( self ):
        
        if HydrusData.TimeHasPassed( self._timestamps[ 'now_awake' ] ):
            
            last_sleep_check = self._timestamps[ 'last_sleep_check' ]
            
            if last_sleep_check == 0:
                
                self._just_woke_from_sleep = False
                
            else:
                
                if HydrusData.TimeHasPassed( last_sleep_check + 600 ):
                    
                    self._just_woke_from_sleep = True
                    
                    self._timestamps[ 'now_awake' ] = HydrusData.GetNow() + 180
                    
                else:
                    
                    self._just_woke_from_sleep = False
                    
                
            
        
        self._timestamps[ 'last_sleep_check' ] = HydrusData.GetNow()
        
    
    def SystemBusy( self ):
        
        return self._system_busy
        
    
    def ViewIsShutdown( self ):
        
        return self._view_shutdown
        
    
    def WaitUntilDBEmpty( self ):
        
        while True:
            
            if self._model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif self.db.JobsQueueEmpty() and not self.db.CurrentlyDoingJob():
                
                return
                
            else:
                
                time.sleep( 0.00001 )
                
            
        
    
    def WaitUntilModelFree( self ):
        
        self.WaitUntilPubSubsEmpty()
        
        self.WaitUntilDBEmpty()
        
    
    def WaitUntilPubSubsEmpty( self ):
        
        while True:
            
            if self._model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif not self._pubsub.WorkToDo() and not self._pubsub.DoingWork():
                
                return
                
            else:
                
                time.sleep( 0.00001 )
                
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def WriteInterruptable( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.INTERRUPTABLE_PRIORITY, True, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
    
    def DAEMONPubSub( self ):
        
        while not HG.model_shutdown:
            
            if self._pubsub.WorkToDo():
                
                try:
                    
                    self.ProcessPubSub()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e, do_wait = True )
                    
                
            else:
                
                self._pubsub.WaitOnPub()
                
            
        
    
