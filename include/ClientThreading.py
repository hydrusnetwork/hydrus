from . import HydrusExceptions
import queue
import threading
import time
import traceback
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusThreading
import os
import wx

class JobKey( object ):
    
    def __init__( self, pausable = False, cancellable = False, only_when_idle = False, only_start_if_unbusy = False, stop_time = None, cancel_on_shutdown = True ):
        
        self._key = HydrusData.GenerateKey()
        
        self._creation_time = HydrusData.GetNowFloat()
        
        self._pausable = pausable
        self._cancellable = cancellable
        self._only_when_idle = only_when_idle
        self._only_start_if_unbusy = only_start_if_unbusy
        self._stop_time = stop_time
        self._cancel_on_shutdown = cancel_on_shutdown
        
        self._start_time = HydrusData.GetNow()
        
        self._deleted = threading.Event()
        self._deletion_time = None
        self._begun = threading.Event()
        self._done = threading.Event()
        self._cancelled = threading.Event()
        self._paused = threading.Event()
        
        self._yield_pause_period = 10
        self._next_yield_pause = HydrusData.GetNow() + self._yield_pause_period
        
        self._bigger_pause_period = 100
        self._next_bigger_pause = HydrusData.GetNow() + self._bigger_pause_period
        
        self._longer_pause_period = 1000
        self._next_longer_pause = HydrusData.GetNow() + self._longer_pause_period
        
        self._urls = []
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def _CheckCancelTests( self ):
        
        if not self._cancelled.is_set():
            
            should_cancel = False
            
            if self._cancel_on_shutdown and HydrusThreading.IsThreadShuttingDown():
                
                should_cancel = True
                
            
            if self._only_when_idle and not HG.client_controller.CurrentlyIdle():
                
                should_cancel = True
                
            
            if self._stop_time is not None:
                
                if HydrusData.TimeHasPassed( self._stop_time ):
                    
                    should_cancel = True
                    
                
            
            if should_cancel:
                
                self.Cancel()
                
            
        
        if not self._deleted.is_set():
            
            if self._deletion_time is not None:
                
                if HydrusData.TimeHasPassed( self._deletion_time ):
                    
                    self.Finish()
                    
                    self._deleted.set()
                    
                
            
        
    
    def AddURL( self, url ):
        
        with self._variable_lock:
            
            self._urls.append( url )
            
        
    
    def Begin( self ): self._begun.set()
    
    def CanBegin( self ):
        
        self._CheckCancelTests()
        
        if self.IsCancelled():
            
            return False
            
        
        if self._only_start_if_unbusy and HG.client_controller.SystemBusy():
            
            return False
            
        
        return True
        
    
    def Cancel( self, seconds = None ):
        
        if seconds is None:
            
            self._cancelled.set()
            
            self.Finish()
            
        else:
            
            HG.client_controller.CallLater( seconds, self.Cancel )
            
        
    
    def Delete( self, seconds = None ):
        
        if seconds is None:
            
            self._deletion_time = HydrusData.GetNow()
            
        else:
            
            self._deletion_time = HydrusData.GetNow() + seconds
            
        
    
    def DeleteVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables: del self._variables[ name ]
            
        
        time.sleep( 0.00001 )
        
    
    def Finish( self, seconds = None ):
        
        if seconds is None:
            
            self._done.set()
            
        else:
            
            HG.client_controller.CallLater( seconds, self.Finish )
            
        
    
    def GetCreationTime( self ):
        
        return self._creation_time
        
    
    def GetIfHasVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables:
                
                return self._variables[ name ]
                
            else:
                
                return None
                
            
        
    
    def GetKey( self ):
        
        return self._key
        
    
    def GetURLs( self ):
        
        with self._variable_lock:
            
            return list( self._urls )
            
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
    def IsBegun( self ):
        
        self._CheckCancelTests()
        
        return self._begun.is_set()
        
    
    def IsCancellable( self ):
        
        self._CheckCancelTests()
        
        return self._cancellable and not self.IsDone()
        
    
    def IsCancelled( self ):
        
        self._CheckCancelTests()
        
        return self._cancelled.is_set()
        
    
    def IsDeleted( self ):
        
        self._CheckCancelTests()
        
        return self._deleted.is_set()
        
    
    def IsDone( self ):
        
        self._CheckCancelTests()
        
        return self._done.is_set()
        
    
    def IsPausable( self ):
        
        self._CheckCancelTests()
        
        return self._pausable and not self.IsDone()
        
    
    def IsPaused( self ):
        
        self._CheckCancelTests()
        
        return self._paused.is_set() and not self.IsDone()
        
    
    def IsWorking( self ):
        
        self._CheckCancelTests()
        
        return self.IsBegun() and not self.IsDone()
        
    
    def PausePlay( self ):
        
        if self._paused.is_set(): self._paused.clear()
        else: self._paused.set()
        
    
    def SetCancellable( self, value ): self._cancellable = value
    
    def SetPausable( self, value ): self._pausable = value
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
        time.sleep( 0.00001 )
        
    
    def TimeRunning( self ):
        
        return HydrusData.GetNow() - self._start_time
        
    
    def ToString( self ):
        
        stuff_to_print = []
        
        with self._variable_lock:
            
            if 'popup_title' in self._variables: stuff_to_print.append( self._variables[ 'popup_title' ] )
            
            if 'popup_text_1' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_1' ] )
            
            if 'popup_text_2' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_2' ] )
            
            if 'popup_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_traceback' ] )
            
        
        stuff_to_print = [ str( s ) for s in stuff_to_print ]
        
        try:
            
            return os.linesep.join( stuff_to_print )
            
        except:
            
            return repr( stuff_to_print )
            
        
    
    def WaitIfNeeded( self ):
        
        if HydrusData.TimeHasPassed( self._next_yield_pause ):
            
            time.sleep( 0.1 )
            
            self._next_yield_pause = HydrusData.GetNow() + self._yield_pause_period
            
            if HydrusData.TimeHasPassed( self._next_bigger_pause ):
                
                time.sleep( 1 )
                
                self._next_bigger_pause = HydrusData.GetNow() + self._bigger_pause_period
                
                if HydrusData.TimeHasPassed( self._longer_pause_period ):
                    
                    time.sleep( 10 )
                    
                    self._next_longer_pause = HydrusData.GetNow() + self._longer_pause_period
                    
                
            
        
        i_paused = False
        should_quit = False
        
        while self.IsPaused():
            
            i_paused = True
            
            time.sleep( 0.1 )
            
            if self.IsDone():
                
                break
                
            
        
        if self.IsCancelled():
            
            should_quit = True
            
        
        return ( i_paused, should_quit )
        
    
class WXAwareJob( HydrusThreading.SchedulableJob ):
    
    def __init__( self, controller, scheduler, window, initial_delay, work_callable ):
        
        HydrusThreading.SchedulableJob.__init__( self, controller, scheduler, initial_delay, work_callable )
        
        self._window = window
        
    
    def _BootWorker( self ):
        
        def wx_code():
            
            if not self._window:
                
                return
                
            
            self.Work()
            
        
        wx.CallAfter( wx_code )
        
    
    def _MyWindowDead( self ):
        
        return not self._window
        
    
    def IsCancelled( self ):
        
        my_window_dead = self._MyWindowDead()
        
        if my_window_dead:
            
            self._is_cancelled.set()
            
        
        return HydrusThreading.SchedulableJob.IsCancelled( self )
        
    
    def IsDead( self ):
        
        return self._MyWindowDead()
        
    
class WXAwareRepeatingJob( HydrusThreading.RepeatingJob ):
    
    def __init__( self, controller, scheduler, window, initial_delay, period, work_callable ):
        
        HydrusThreading.RepeatingJob.__init__( self, controller, scheduler, initial_delay, period, work_callable )
        
        self._window = window
        
    
    def _BootWorker( self ):
        
        def wx_code():
            
            if not self._window:
                
                return
                
            
            self.Work()
            
        
        wx.CallAfter( wx_code )
        
    
    def _MyWindowDead( self ):
        
        return not self._window
        
    
    def IsCancelled( self ):
        
        my_window_dead = self._MyWindowDead()
        
        if my_window_dead:
            
            self._is_cancelled.set()
            
        
        return HydrusThreading.SchedulableJob.IsCancelled( self )
        
    
    def IsDead( self ):
        
        return self._MyWindowDead()
        
    
