import collections
import gc
import HydrusConstants as HC
import HydrusDaemons
import HydrusData
import HydrusDB
import HydrusExceptions
import HydrusGlobals
import HydrusPubSub
import HydrusThreading
import random
import sys
import threading
import time
import traceback
import wx

class HydrusController( wx.App ):
    
    db_class = HydrusDB.HydrusDB
    pubsub_binding_errors_to_ignore = []
    
    def _Read( self, action, *args, **kwargs ):
        
        result = self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
        time.sleep( 0.00001 )
        
        return result
        
    
    def _Write( self, action, priority, synchronous, *args, **kwargs ):
        
        result = self._db.Write( action, priority, synchronous, *args, **kwargs )
        
        time.sleep( 0.00001 )
        
        return result
        
    
    def pub( self, topic, *args, **kwargs ):
        
        self._pubsub.pub( topic, *args, **kwargs )
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        call_to_thread = random.choice( self._call_to_threads )
        
        while call_to_thread == threading.current_thread: call_to_thread = random.choice( self._call_to_threads )
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def ClearCaches( self ):
        
        for cache in self._caches.values(): cache.Clear()
        
    
    def CurrentlyIdle( self ): return True
    
    def GetCache( self, name ): return self._caches[ name ]
    
    def GetDB( self ): return self._db
    
    def GetManager( self, name ): return self._managers[ name ]
    
    def GoodTimeToDoBackgroundWork( self ):
        
        return not ( self.JustWokeFromSleep() or self.SystemBusy() )
        
    
    def JustWokeFromSleep( self ):
        
        self.SleepCheck()
        
        return self._just_woke_from_sleep
        
    
    def InitDaemons( self ):
        
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'SleepCheck', HydrusDaemons.DAEMONSleepCheck, period = 120 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'MaintainDB', HydrusDaemons.DAEMONMaintainDB, period = 300 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'MaintainMemory', HydrusDaemons.DAEMONMaintainMemory, period = 300 ) )
        
    
    def InitData( self ):
        
        self.SetAssertMode( wx.PYAPP_ASSERT_SUPPRESS )
        
        HydrusGlobals.controller = self
        self._pubsub = HydrusPubSub.HydrusPubSub( self, self.pubsub_binding_errors_to_ignore )
        self._currently_doing_pubsub = False
        
        self._daemons = []
        self._caches = {}
        self._managers = {}
        
        self._call_to_threads = [ HydrusThreading.DAEMONCallToThread( self ) for i in range( 10 ) ]
        
        self._timestamps = collections.defaultdict( lambda: 0 )
        
        self._timestamps[ 'boot' ] = HydrusData.GetNow()
        
        self._just_woke_from_sleep = False
        self._system_busy = False
        
    
    def InitDB( self ):
        
        self._db = self.db_class( self )
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    def MaintainDB( self ):
        
        raise NotImplementedError()
        
    
    def MaintainMemory( self ):
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        gc.collect()
        
    
    def NotifyPubSubs( self ):
        
        raise NotImplementedError()
        
    
    def ProcessPubSub( self ):
        
        self._currently_doing_pubsub = True
        
        try: self._pubsub.Process()
        finally: self._currently_doing_pubsub = False
        
    
    def Read( self, action, *args, **kwargs ): return self._Read( action, *args, **kwargs )
    
    def ShutdownDB( self ):
        
        self._db.Shutdown()
        
        while not self._db.LoopIsFinished(): time.sleep( 0.1 )
        
    
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
        
    
    def WaitUntilPubSubsEmpty( self ):
        
        while True:
            
            if HydrusGlobals.view_shutdown: raise Exception( 'Application shutting down!' )
            elif self._pubsub.NoJobsQueued() and not self._currently_doing_pubsub: return
            else: time.sleep( 0.00001 )
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
    