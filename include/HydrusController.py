import collections
import gc
import HydrusConstants as HC
import HydrusData
import HydrusDB
import HydrusExceptions
import HydrusGlobals
import HydrusPubSub
import sys
import threading
import time
import traceback
import wx

ID_MAINTENANCE_EVENT_TIMER = wx.NewId()

MAINTENANCE_PERIOD = 5 * 60

class HydrusController( wx.App ):
    
    db_class = HydrusDB.HydrusDB
    
    def _CheckIfJustWokeFromSleep( self ):
        
        last_maintenance_time = self._timestamps[ 'last_maintenance_time' ]
        
        if last_maintenance_time == 0: return False
        
        if HydrusData.TimeHasPassed( last_maintenance_time + MAINTENANCE_PERIOD + ( 5 * 60 ) ): self._just_woke_from_sleep = True
        else: self._just_woke_from_sleep = False
        
    
    def _Read( self, action, *args, **kwargs ):
        
        result = self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
        time.sleep( 0.00001 )
        
        return result
        
    
    def _Write( self, action, priority, synchronous, *args, **kwargs ):
        
        result = self._db.Write( action, priority, synchronous, *args, **kwargs )
        
        time.sleep( 0.00001 )
        
        return result
        
    
    def ClearCaches( self ):
        
        for cache in self._caches.values(): cache.Clear()
        
    
    def CurrentlyIdle( self ): return True
    
    def EventPubSub( self, event ):
        
        self._currently_doing_pubsub = True
        
        try: HydrusGlobals.pubsub.WXProcessQueueItem()
        finally: self._currently_doing_pubsub = False
        
    
    def GetCache( self, name ): return self._caches[ name ]
    
    def GetDB( self ): return self._db
    
    def GetManager( self, name ): return self._managers[ name ]
    
    def JustWokeFromSleep( self ):
        
        if not self._just_woke_from_sleep: self._CheckIfJustWokeFromSleep()
        
        return self._just_woke_from_sleep
        
    
    def MaintainDB( self ):
        
        raise NotImplementedError()
        
    
    def OnInit( self ):
        
        self.SetAssertMode( wx.PYAPP_ASSERT_SUPPRESS )
        
        HydrusData.IsAlreadyRunning()
        
        self._currently_doing_pubsub = False
        
        self._caches = {}
        self._managers = {}
        
        self._timestamps = collections.defaultdict( lambda: 0 )
        
        self._timestamps[ 'boot' ] = HydrusData.GetNow()
        
        self._just_woke_from_sleep = False
        
        self.Bind( HydrusPubSub.EVT_PUBSUB, self.EventPubSub )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventMaintenance, id = ID_MAINTENANCE_EVENT_TIMER )
        
        self._maintenance_event_timer = wx.Timer( self, ID_MAINTENANCE_EVENT_TIMER )
        self._maintenance_event_timer.Start( MAINTENANCE_PERIOD * 1000, wx.TIMER_CONTINUOUS )
        
    
    def InitDB( self ):
        
        self._db = self.db_class()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    def Read( self, action, *args, **kwargs ): return self._Read( action, *args, **kwargs )
    
    def ShutdownDB( self ):
        
        self._db.Shutdown()
        
        while not self._db.LoopIsFinished(): time.sleep( 0.1 )
        
    
    def TIMEREventMaintenance( self, event ):
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        gc.collect()
        
        self._CheckIfJustWokeFromSleep()
        
        self._timestamps[ 'last_maintenance_time' ] = HydrusData.GetNow()
        
        if not self._just_woke_from_sleep and self.CurrentlyIdle() and not HydrusGlobals.currently_processing_updates: self.MaintainDB()
        
    
    def WaitUntilWXThreadIdle( self ):
        
        while True:
            
            if HydrusGlobals.shutdown: raise Exception( 'Application shutting down!' )
            elif HydrusGlobals.pubsub.NoJobsQueued() and not self._currently_doing_pubsub: return
            else: time.sleep( 0.00001 )
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
    