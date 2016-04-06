import HydrusExceptions
import Queue
import threading
import time
import traceback
import HydrusData
import HydrusGlobals
import HydrusThreading
import os

class JobKey( object ):
    
    def __init__( self, pausable = False, cancellable = False, only_when_idle = False, only_start_if_unbusy = False, stop_time = None ):
        
        self._key = HydrusData.GenerateKey()
        
        self._pausable = pausable
        self._cancellable = cancellable
        self._only_when_idle = only_when_idle
        self._only_start_if_unbusy = only_start_if_unbusy
        self._stop_time = stop_time
        
        self._deleted = threading.Event()
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
        
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def _CheckCancelTests( self ):
        
        if not self._cancelled.is_set():
            
            should_cancel = False
            
            if HydrusThreading.IsThreadShuttingDown():
                
                should_cancel = True
                
            
            if self._only_when_idle and not HydrusGlobals.client_controller.CurrentlyIdle():
                
                should_cancel = True
                
            
            if self._stop_time is not None:
                
                if HydrusData.TimeHasPassed( self._stop_time ):
                    
                    should_cancel = True
                    
                
            
            if should_cancel:
                
                self.Cancel()
                
            
        
    
    def Begin( self ): self._begun.set()
    
    def CanBegin( self ):
        
        if self.IsCancelled():
            
            return False
            
        
        if self._only_start_if_unbusy and HydrusGlobals.client_controller.SystemBusy():
            
            return False
            
        
        return True
        
    
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
        
        self._CheckCancelTests()
        
        return HydrusThreading.IsThreadShuttingDown() or self._cancelled.is_set()
        
    
    def IsDeleted( self ):
        
        self._CheckCancelTests()
        
        return HydrusThreading.IsThreadShuttingDown() or self._deleted.is_set()
        
    
    def IsDone( self ):
        
        return HydrusThreading.IsThreadShuttingDown() or self._done.is_set()
        
    
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
        
    