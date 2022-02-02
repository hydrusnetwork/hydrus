import os
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusThreading

from hydrus.client.gui import QtPorting as QP

class JobKey( object ):
    
    def __init__( self, pausable = False, cancellable = False, maintenance_mode = HC.MAINTENANCE_FORCED, only_start_if_unbusy = False, stop_time = None, cancel_on_shutdown = True ):
        
        self._key = HydrusData.GenerateKey()
        
        self._creation_time = HydrusData.GetNowFloat()
        
        self._pausable = pausable
        self._cancellable = cancellable
        self._maintenance_mode = maintenance_mode
        self._only_start_if_unbusy = only_start_if_unbusy
        self._stop_time = stop_time
        self._cancel_on_shutdown = cancel_on_shutdown and maintenance_mode != HC.MAINTENANCE_SHUTDOWN
        
        self._start_time = HydrusData.GetNow()
        
        self._deleted = threading.Event()
        self._deletion_time = None
        self._done = threading.Event()
        self._cancelled = threading.Event()
        self._paused = threading.Event()
        
        self._ui_update_pause_period = 0.1
        self._next_ui_update_pause = HydrusData.GetNowFloat() + self._ui_update_pause_period
        
        self._yield_pause_period = 10
        self._next_yield_pause = HydrusData.GetNow() + self._yield_pause_period
        
        self._bigger_pause_period = 100
        self._next_bigger_pause = HydrusData.GetNow() + self._bigger_pause_period
        
        self._longer_pause_period = 1000
        self._next_longer_pause = HydrusData.GetNow() + self._longer_pause_period
        
        self._exception = None
        
        self._urls = []
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, JobKey ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._key.__hash__()
        
    
    def _CheckCancelTests( self ):
        
        if not self._cancelled.is_set():
            
            should_cancel = False
            
            if self._cancel_on_shutdown and HydrusThreading.IsThreadShuttingDown():
                
                should_cancel = True
                
            
            if HG.client_controller.ShouldStopThisWork( self._maintenance_mode, self._stop_time ):
                
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
            
        
    
    def DeleteNetworkJob( self ):
        
        self.DeleteVariable( 'network_job' )
        
    
    def DeleteVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables: del self._variables[ name ]
            
        
        if HydrusData.TimeHasPassedFloat( self._next_ui_update_pause ):
            
            time.sleep( 0.00001 )
            
            self._next_ui_update_pause = HydrusData.GetNowFloat() + self._ui_update_pause_period
            
        
    
    def Finish( self, seconds = None ):
        
        if seconds is None:
            
            self._done.set()
            
        else:
            
            HG.client_controller.CallLater( seconds, self.Finish )
            
        
    
    def GetCreationTime( self ):
        
        return self._creation_time
        
    
    def GetErrorException( self ) -> Exception:
        
        if self._exception is None:
            
            raise Exception( 'No exception to return!' )
            
        else:
            
            return self._exception
            
        
    
    def GetIfHasVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables:
                
                return self._variables[ name ]
                
            else:
                
                return None
                
            
        
    
    def GetKey( self ):
        
        return self._key
        
    
    def GetNetworkJob( self ):
        
        return self.GetIfHasVariable( 'network_job' )
        
    
    def GetStatusTitle( self ) -> typing.Optional[ str ]:
        
        return self.GetIfHasVariable( 'status_title' )
        
    
    def GetTraceback( self ):
        
        return self.GetIfHasVariable( 'traceback' )
        
    
    def GetURLs( self ):
        
        with self._variable_lock:
            
            return list( self._urls )
            
        
    
    def GetUserCallable( self ) -> typing.Optional[ HydrusData.Call ]:
        
        return self.GetIfHasVariable( 'user_callable' )
        
    
    def HadError( self ):
        
        return self._exception is not None
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
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
        
        return not self.IsDone()
        
    
    def PausePlay( self ):
        
        if self._paused.is_set(): self._paused.clear()
        else: self._paused.set()
        
    
    def SetCancellable( self, value ):
        
        self._cancellable = value
        
    
    def SetErrorException( self, e: Exception ):
        
        self._exception = e
        
        self.Cancel()
        
    
    def SetNetworkJob( self, network_job ):
        
        self.SetVariable( 'network_job', network_job )
        
    
    def SetPausable( self, value ): self._pausable = value
    
    def SetStatusTitle( self, title: str ):
        
        self.SetVariable( 'status_title', title )
        
    
    def SetTraceback( self, trace: str ):
        
        self.SetVariable( 'traceback', trace )
        
    
    def SetUserCallable( self, call: HydrusData.Call ):
        
        self.SetVariable( 'user_callable', call )
        
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
        if HydrusData.TimeHasPassed( self._next_ui_update_pause ):
            
            time.sleep( 0.00001 )
            
            self._next_ui_update_pause = HydrusData.GetNow() + self._ui_update_pause_period
            
        
    
    def TimeRunning( self ):
        
        return HydrusData.GetNow() - self._start_time
        
    
    def ToString( self ):
        
        stuff_to_print = []
        
        status_title = self.GetStatusTitle()
        
        if status_title is not None:
            
            stuff_to_print.append( status_title )
            
        
        with self._variable_lock:
            
            if 'popup_text_1' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_1' ] )
            
            if 'popup_text_2' in self._variables: stuff_to_print.append( self._variables[ 'popup_text_2' ] )
            
        
        trace = self.GetTraceback()
        
        if trace is not None:
            
            stuff_to_print.append( trace )
            
        
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
        
    
class FileRWLock( object ):
    
    class RLock( object ):
        
        def __init__( self, parent ):
            
            self.parent = parent
            
        
        def __enter__( self ):
            
            while not HydrusThreading.IsThreadShuttingDown():
                
                with self.parent.lock:
                    
                    # if there are no writers, we can start reading
                    
                    if not self.parent.there_is_an_active_writer and self.parent.num_waiting_writers == 0:
                        
                        self.parent.num_readers += 1
                        
                        return
                        
                    
                
                # otherwise wait a bit
                
                self.parent.read_available_event.wait( 1 )
                
                self.parent.read_available_event.clear()
                
            
        
        def __exit__( self, exc_type, exc_val, exc_tb ):
            
            with self.parent.lock:
                
                self.parent.num_readers -= 1
                
                do_write_notify = self.parent.num_readers == 0 and self.parent.num_waiting_writers > 0
                
            
            if do_write_notify:
                
                self.parent.write_available_event.set()
                
            
        
    
    class WLock( object ):
        
        def __init__( self, parent ):
            
            self.parent = parent
            
        
        def __enter__( self ):
            
            # let all the readers know that we are bumping up to the front of the queue
            
            with self.parent.lock:
                
                self.parent.num_waiting_writers += 1
                
            
            while not HydrusThreading.IsThreadShuttingDown():
                
                with self.parent.lock:
                    
                    # if nothing reading or writing atm, sieze the opportunity
                    
                    if not self.parent.there_is_an_active_writer and self.parent.num_readers == 0:
                        
                        self.parent.num_waiting_writers -= 1
                        
                        self.parent.there_is_an_active_writer = True
                        
                        return
                        
                    
                
                # otherwise wait a bit
                
                self.parent.write_available_event.wait( 1 )
                
                self.parent.write_available_event.clear()
                
            
        
        def __exit__( self, exc_type, exc_val, exc_tb ):
            
            with self.parent.lock:
                
                self.parent.there_is_an_active_writer = False
                
                do_read_notify = self.parent.num_waiting_writers == 0 # reading is now available
                do_write_notify = self.parent.num_waiting_writers > 0 # another writer is waiting
                
            
            if do_read_notify:
                
                self.parent.read_available_event.set()
                
            
            if do_write_notify:
                
                self.parent.write_available_event.set()
                
            
        
    
    def __init__( self ):
        
        self.read = self.RLock( self )
        self.write = self.WLock( self )
        
        self.lock = threading.Lock()
        
        self.read_available_event = threading.Event()
        self.write_available_event = threading.Event()
        
        self.num_readers = 0
        self.num_waiting_writers = 0
        self.there_is_an_active_writer = False
        
    
    def IsLocked( self ):
        
        with self.lock:
            
            return self.num_waiting_writers > 0 or self.there_is_an_active_writer or self.num_readers > 0
            
        
    
    def ReadersAreWorking( self ):
        
        with self.lock:
            
            return self.num_readers > 0
            
        
    
    def WritersAreWaitingOrWorking( self ):
        
        with self.lock:
            
            return self.num_waiting_writers > 0 or self.there_is_an_active_writer
            
        
    
class QtAwareJob( HydrusThreading.SingleJob ):
    
    PRETTY_CLASS_NAME = 'single UI job'
    
    def __init__( self, controller, scheduler, window, initial_delay, work_callable ):
        
        HydrusThreading.SingleJob.__init__( self, controller, scheduler, initial_delay, work_callable )
        
        self._window = window
        
    
    def _BootWorker( self ):
        
        def qt_code():
            
            if self._window is None or not QP.isValid( self._window ):
                
                return
                
            
            self.Work()
            
        
        QP.CallAfter( qt_code )
        
    
    def _MyWindowDead( self ):
        
        return self._window is None or not QP.isValid( self._window )
        
    
    def IsCancelled( self ):
        
        my_window_dead = self._MyWindowDead()
        
        if my_window_dead:
            
            self._is_cancelled.set()
            
        
        return HydrusThreading.SingleJob.IsCancelled( self )
        
    
    def IsDead( self ):
        
        return self._MyWindowDead()
        
    
class QtAwareRepeatingJob( HydrusThreading.RepeatingJob ):
    
    PRETTY_CLASS_NAME = 'repeating UI job'
    
    def __init__( self, controller, scheduler, window, initial_delay, period, work_callable ):
        
        HydrusThreading.RepeatingJob.__init__( self, controller, scheduler, initial_delay, period, work_callable )
        
        self._window = window
        
    
    def _QTWork( self ):
        
        if self._window is None or not QP.isValid( self._window ):
            
            self._window = None
            
            return
            
        
        self.Work()
        
    
    def _BootWorker( self ):
        
        QP.CallAfter( self._QTWork )
        
    
    def _MyWindowDead( self ):
        
        return self._window is None or not QP.isValid( self._window )
        
    
    def IsCancelled( self ):
        
        my_window_dead = self._MyWindowDead()
        
        if my_window_dead:
            
            self._is_cancelled.set()
            
        
        return HydrusThreading.SingleJob.IsCancelled( self )
        
    
    def IsDead( self ):
        
        return self._MyWindowDead()
        
    
