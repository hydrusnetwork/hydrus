import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import QtPorting as QP

class JobStatus( object ):
    
    def __init__( self, pausable = False, cancellable = False, maintenance_mode = HC.MAINTENANCE_FORCED, only_start_if_unbusy = False, stop_time = None, cancel_on_shutdown = True ):
        
        self._key = HydrusData.GenerateKey()
        
        self._creation_time = HydrusTime.GetNowFloat()
        
        self._pausable = pausable
        self._cancellable = cancellable
        self._maintenance_mode = maintenance_mode
        self._only_start_if_unbusy = only_start_if_unbusy
        self._stop_time = stop_time
        self._cancel_on_shutdown = cancel_on_shutdown and maintenance_mode != HC.MAINTENANCE_SHUTDOWN
        
        self._cancelled = False
        self._paused = False
        self._dismissed = False
        self._finish_and_dismiss_time = None
        
        self._i_am_an_ongoing_job = self._pausable or self._cancellable
        
        self._done_event = threading.Event()
        
        if self._i_am_an_ongoing_job:
            
            self._job_finish_time = None
            
        else:
            
            self._done_event.set()
            self._job_finish_time = HydrusTime.GetNowFloat()
            
        
        self._ui_update_pauser = HydrusThreading.BigJobPauser( 0.1, 0.00001 )
        
        self._yield_pauser = HydrusThreading.BigJobPauser()
        
        self._cancel_tests_regular_checker = HydrusThreading.RegularJobChecker( 1.0 )
        
        self._exception = None
        
        self._urls = []
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, JobStatus ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._key.__hash__()
        
    
    def _CheckCancelTests( self ):
        
        if self._cancel_tests_regular_checker.Due():
            
            if not self._done_event.is_set():
                
                if self._cancel_on_shutdown and HydrusThreading.IsThreadShuttingDown():
                    
                    self.Cancel()
                    
                    return
                    
                
                if CG.client_controller.ShouldStopThisWork( self._maintenance_mode, self._stop_time ):
                    
                    self.Cancel()
                    
                    return
                    
                
            
            if not self._dismissed:
                
                if self._finish_and_dismiss_time is not None:
                    
                    if HydrusTime.TimeHasPassed( self._finish_and_dismiss_time ):
                        
                        self.FinishAndDismiss()
                        
                    
                
            
        
    
    def AddURL( self, url ):
        
        with self._variable_lock:
            
            if url not in self._urls:
                
                self._urls.append( url )
                
            
        
    
    def Cancel( self ):
        
        self._cancelled = True
        
        self.Finish()
        
    
    def DeleteFiles( self ):
        
        self.DeleteVariable( 'attached_files' )
        
    
    def DeleteGauge( self, level = 1 ):
        
        self.DeleteVariable( f'popup_gauge_{level}' )
        
    
    def DeleteNetworkJob( self ):
        
        self.DeleteVariable( 'network_job' )
        
    
    def DeleteStatusText( self, level = 1 ):
        
        self.DeleteVariable( f'status_text_{level}' )
        
    
    def DeleteStatusTitle( self ):
        
        self.DeleteVariable( 'status_title' )
        

    def DeleteVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables:
                
                del self._variables[ name ]
                
            
        
        self._ui_update_pauser.Pause()
        
    
    def Finish( self ):
        
        self._job_finish_time = HydrusTime.GetNowFloat()
        
        self._paused = False
        
        self._pausable = False
        self._cancellable = False
        
        self._done_event.set()
        
    
    def FinishAndDismiss( self, seconds = None ):
        
        self.Finish()
        
        if seconds is None:
            
            self._dismissed = True
            
        else:
            
            self._finish_and_dismiss_time = HydrusTime.GetNow() + seconds
            
        
    
    def GetCreationTime( self ):
        
        return self._creation_time
        
    
    def GetDoneEvent( self ) -> threading.Event:
        
        return self._done_event
        
    
    def GetErrorException( self ) -> Exception:
        
        if self._exception is None:
            
            raise Exception( 'No exception to return!' )
            
        else:
            
            return self._exception
            
        
    
    def GetFiles( self ):
        
        return self.GetIfHasVariable( 'attached_files' )
        
    
    def GetIfHasVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables:
                
                return self._variables[ name ]
                
            else:
                
                return None
                
            
        
    
    def GetGauge( self, level = 1 ) -> tuple[ int | None, int | None ] | None:
        
        return self.GetIfHasVariable( f'popup_gauge_{level}' )
        
    
    def GetKey( self ):
        
        return self._key
        
    
    def GetNetworkJob( self ):
        
        return self.GetIfHasVariable( 'network_job' )
        
    
    def GetStatusText( self, level = 1 ) -> str | None:
        
        return self.GetIfHasVariable( 'status_text_{}'.format( level ) )
        
    
    def GetStatusTitle( self ) -> str | None:
        
        return self.GetIfHasVariable( 'status_title' )
        
    
    def GetTraceback( self ):
        
        return self.GetIfHasVariable( 'traceback' )
        
    
    def GetURLs( self ):
        
        with self._variable_lock:
            
            return list( self._urls )
            
        
    
    def GetUserCallable( self ) -> HydrusData.Call | None:
        
        return self.GetIfHasVariable( 'user_callable' )
        
    
    def HadError( self ):
        
        return self._exception is not None
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
    def IsCancellable( self ):
        
        return self._cancellable
        
    
    def IsCancelled( self ):
        
        self._CheckCancelTests()
        
        return self._cancelled
        
    
    def IsDismissed( self ):
        
        self._CheckCancelTests()
        
        return self._dismissed
        
    
    def IsDone( self ):
        
        self._CheckCancelTests()
        
        return self._done_event.is_set()
        
    
    def IsPausable( self ):
        
        return self._pausable
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def SetErrorException( self, e: Exception ):
        
        self._exception = e
        
        self.Cancel()
        
    
    def SetFiles( self, hashes: list[ bytes ], label: str ):
        
        if len( hashes ) == 0:
            
            self.DeleteFiles()
            
        else:
            
            hashes = HydrusLists.DedupeList( list( hashes ) )
            
            self.SetVariable( 'attached_files', ( hashes, label ) )
            
        
    
    def SetGauge( self, num_done: int | None, num_to_do: int | None, level = 1 ):
        
        self.SetVariable( f'popup_gauge_{level}', ( num_done, num_to_do ) )
        
    
    def SetNetworkJob( self, network_job ):
        
        self.SetVariable( 'network_job', network_job )
        
    
    def SetStatusText( self, text: str, level = 1 ):
        
        self.SetVariable( 'status_text_{}'.format( level ), text )
        
    
    def SetStatusTitle( self, title: str ):
        
        self.SetVariable( 'status_title', title )
        
    
    def SetTraceback( self, trace: str ):
        
        self.SetVariable( 'traceback', trace )
        
    
    def SetUserCallable( self, call: HydrusData.Call ):
        
        self.SetVariable( 'user_callable', call )
        
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
        self._ui_update_pauser.Pause()
        
    
    def TimeRunning( self ):
        
        if self._job_finish_time is None:
            
            return HydrusTime.GetNowFloat() - self._creation_time
            
        else:
            
            return self._job_finish_time - self._creation_time
            
        
    
    def ToString( self ):
        
        stuff_to_print = []
        
        status_title = self.GetStatusTitle()
        
        if status_title is not None:
            
            stuff_to_print.append( status_title )
            
        
        status_text_1 = self.GetStatusText()
        
        if status_text_1 is not None:
            
            stuff_to_print.append( status_text_1 )
            
        
        status_text_2 = self.GetStatusText( 2 )
        
        if status_text_2 is not None:
            
            stuff_to_print.append( status_text_2 )
            
        
        trace = self.GetTraceback()
        
        if trace is not None:
            
            stuff_to_print.append( trace )
            
        
        stuff_to_print = [ str( s ) for s in stuff_to_print ]
        
        try:
            
            return '\n'.join( stuff_to_print )
            
        except Exception as e:
            
            return repr( stuff_to_print )
            
        
    
    def WaitIfNeeded( self ):
        
        self._yield_pauser.Pause()
        
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
            
        
    

# TODO: a FileSystemRWLock, which will offer locks on a prefix basis. I had a think and some playing around, and I think best answer is to copy the FileRWLock here and just make it more complicated
# The RLock and WLock will be asked for either global or prefix based lock
# if grabbing global lock, work as normal
# if grabbing a prefix lock, they first get the global read lock, to block global writes
# only track the 'largest' (i.e. shortest) prefix we have in the file system. access to 'f333' will need '33' lock, if we are in transition and 'f33' (or, say, 'f27') still exists
# think and plan more, write some good unit tests, make sure we aren't deadlocking by being stupid somehow

class QtAwareJob( HydrusThreading.SingleJob ):
    
    PRETTY_CLASS_NAME = 'single UI job'
    
    def __init__( self, controller, scheduler, window, initial_delay, work_callable ):
        
        super().__init__( controller, scheduler, initial_delay, work_callable )
        
        self._window = window
        
    
    def _BootWorker( self ):
        
        def qt_code():
            
            if self._window is None or not QP.isValid( self._window ):
                
                return
                
            
            self.Work()
            
        
        # yo if you change this, alter how profile_mode (ui) works
        CG.client_controller.CallAfterQtSafe( self._window, qt_code )
        
    
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
        
        super().__init__( controller, scheduler, initial_delay, period, work_callable )
        
        self._window = window
        
    
    def _QTWork( self ):
        
        if self._window is None or not QP.isValid( self._window ):
            
            self._window = None
            
            return
            
        
        self.Work()
        
    
    def _BootWorker( self ):
        
        # yo if you change this, alter how profile_mode (ui) works
        CG.client_controller.CallAfterQtSafe( self._window, self._QTWork )
        
    
    def _MyWindowDead( self ):
        
        return self._window is None or not QP.isValid( self._window )
        
    
    def IsCancelled( self ):
        
        my_window_dead = self._MyWindowDead()
        
        if my_window_dead:
            
            self._is_cancelled.set()
            
        
        return HydrusThreading.SingleJob.IsCancelled( self )
        
    
    def IsDead( self ):
        
        return self._MyWindowDead()
        
    
