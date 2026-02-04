import hashlib
import os
import signal
import sys
import threading
import time
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusController
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPSUtil
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking
from hydrus.core.processes import HydrusProcess
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientOptions
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.caches import ClientCaches
from hydrus.client.db import ClientDB
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.files import ClientFilesManager
from hydrus.client.gui import ClientGUICallAfter
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUISplash
from hydrus.client.gui import QtPorting as QP

if not HG.twisted_is_broke:
    
    from twisted.internet import threads, reactor, defer
    

callable_P = typing.ParamSpec( 'callable_P' )
callable_R = typing.TypeVar( 'callable_R' )

PubSubEventType = QP.registerEventType()

class PubSubEvent( QC.QEvent ):
    
    def __init__( self ):
        
        super().__init__( PubSubEventType )
        
    

class PubSubEventCatcher( QC.QObject ):
    
    def __init__( self, parent, pubsub ):
        
        super().__init__( parent )
        
        self._pubsub = pubsub
        
        self.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == PubSubEventType and isinstance( event, PubSubEvent ):
                
                if self._pubsub.WorkToDo():
                    
                    self._pubsub.Process()
                    
                
                event.accept()
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

def MessageHandler( msg_type, context, text ):
    
    if msg_type not in ( QC.QtMsgType.QtDebugMsg, QC.QtMsgType.QtInfoMsg ):
        
        # Set a breakpoint here to be able to see where the warnings originate from.
        HydrusData.Print( text )
        

class App( QW.QApplication ):
    
    def __init__( self, pubsub, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
        self._pubsub = pubsub
        
        self.setApplicationName( 'Hydrus Client' )
        
        if HC.PLATFORM_LINUX:
            
            self.setDesktopFileName( 'io.github.hydrusnetwork.hydrus' )
            
        
        self.setApplicationVersion( str( HC.SOFTWARE_VERSION ) )
        
        QC.qInstallMessageHandler( MessageHandler )
        
        self.setQuitOnLastWindowClosed( False )
        
        self.setQuitLockEnabled( False )
        
        self.pubsub_catcher = PubSubEventCatcher( self, self._pubsub )
        
        self.aboutToQuit.connect( self.EventAboutToQuit )
        
    
    def EventAboutToQuit( self ):
        
        # If a user log-off causes the OS to call the Qt Application's quit/exit func, we still want to save and close nicely
        # once this lad is done, we are OUT of the mainloop, so if this is called and we are actually waiting on THREADExitEverything, let's wait a bit more
        
        # on Windows, the logoff routine kills the process once all top level windows are dead, so we have no chance to do post-app work lmaooooooooo
        # since splash screen may not appear in some cases, I now keep main gui alive but hidden until the quit call. it is never deleteLater'd
        
        # this is also called explicitly right at the end of the program. I set setQuitonLastWindowClosed False and then call quit explicitly, so it needs to be idempotent on the exit calls
        
        if CG.client_controller is not None:
            
            if CG.client_controller.ProgramIsShuttingDown():
                
                screw_it_time = HydrusTime.GetNow() + 15
                
                while not CG.client_controller.ProgramIsShutDown():
                    
                    time.sleep( 0.25 )
                    
                    if HydrusTime.TimeHasPassed( screw_it_time ):
                        
                        return
                        
                    
                
            else:
                
                CG.client_controller.ExitFast()
                
            
        
    

class Controller( HydrusController.HydrusController ):
    
    my_instance = None
    
    def __init__( self, db_dir, logger ):
        
        self._qt_app_running = False
        self._is_booted = False
        self._program_is_shutting_down = False
        self._program_is_shut_down = False
        self._restore_backup_path = None
        
        self._splash = None
        
        self.gui = None
        
        super().__init__( db_dir, logger )
        
        self._name = 'client'
        
        CG.client_controller = self
        
        # just to set up some defaults, in case some db update expects something for an odd yaml-loading reason
        self.options = ClientDefaults.GetClientDefaultOptions()
        self.new_options = ClientOptions.ClientOptions()
        
        HC.options = self.options
        
        self._page_key_lock = threading.Lock()
        
        self._thread_slots[ 'watcher_files' ] = ( 0, 15 )
        self._thread_slots[ 'watcher_check' ] = ( 0, 5 )
        self._thread_slots[ 'gallery_files' ] = ( 0, 15 )
        self._thread_slots[ 'gallery_search' ] = ( 0, 5 )
        
        self._alive_page_keys = set()
        self._closed_page_keys = set()
        
        self._last_last_session_hash = None
        
        self._managers_with_mainloops: list[ ClientDaemons.ManagerWithMainLoop ] = []
        
        self._last_mouse_position = None
        self._previously_idle = False
        self._idle_started = None
        
        self.call_after_catcher = ClientGUICallAfter.CallAfterEventCatcher( QW.QApplication.instance() )
        
        self.thumbnails_cache: ClientCaches.ThumbnailCache | None = None
        
        self.client_files_manager: ClientFilesManager.ClientFilesManager | None = None
        self.services_manager: ClientServices.ServicesManager | None = None
        
        Controller.my_instance = self
        
    
    def _InitDB( self ):
        
        self.db = ClientDB.DB( self, self.db_dir, 'client' )
        
    
    def _DestroySplash( self ):
        
        def qt_code( splash ):
            
            splash.hide()
            
            splash.close()
            
            self.frame_splash_status.Reset()
            
        
        if self._splash is not None:
            
            splash = self._splash
            
            self._splash = None
            
            self.CallAfterQtSafe( splash, qt_code, splash )
            
        
    
    def _GetPubsubValidCallable( self ):
        
        return QP.isValid
        
    
    def _GetUPnPServices( self ):
        
        return self.services_manager.GetServices( ( HC.CLIENT_API_SERVICE, ) )
        
    
    def _GetWakeDelayPeriodMS( self ):
        
        return HydrusTime.MillisecondiseS( self.new_options.GetInteger( 'wake_delay_period' ) )
        
    
    def _PublishShutdownSubtext( self, text ):
        
        self.frame_splash_status.SetSubtext( text )
        
    
    def _ReportShutdownDaemonsStatus( self ):
        
        names = sorted( ( name for ( name, job ) in self._daemon_jobs.items() if job.CurrentlyWorking() ) )
        
        self.frame_splash_status.SetSubtext( ', '.join( names ) )
        
    
    def _ReportShutdownException( self ):
        
        text = 'A serious error occurred while trying to exit the program. Its traceback may be shown next. It should have also been written to client.log. You may need to quit the program from task manager.'
        
        HydrusData.DebugPrint( text )
        
        HydrusData.DebugPrint( traceback.format_exc() )
        
        if not self._doing_fast_exit:
            
            self.BlockingSafeShowCriticalMessage( 'shutdown error', text )
            self.BlockingSafeShowCriticalMessage( 'shutdown error', traceback.format_exc() )
            
        
        self._doing_fast_exit = True
        
    
    def _ReportShutdownManagersStatus( self ):
        
        names = sorted( ( manager.GetName() for manager in self._managers_with_mainloops if not manager.IsShutdown() ) )
        
        self.frame_splash_status.SetSubtext( ', '.join( names ) )
        
    
    def _ShowJustWokeToUser( self ):
        
        def do_it( job_status: ClientThreading.JobStatus ):
            
            while not HG.started_shutdown:
                
                with self._sleep_lock:
                    
                    if job_status.IsCancelled():
                        
                        self.TouchTime( 'now_awake' )
                        
                        job_status.SetStatusText( 'enabling I/O now' )
                        
                        job_status.FinishAndDismiss()
                        
                        return
                        
                    
                    wake_time_ms = self.GetTimestampMS( 'now_awake' )
                    
                
                if HydrusTime.TimeHasPassedMS( wake_time_ms ):
                    
                    job_status.FinishAndDismiss()
                    
                    return
                    
                else:
                    
                    wake_time = HydrusTime.SecondiseMS( wake_time_ms )
                    
                    job_status.SetStatusText( 'enabling I/O {}'.format( HydrusTime.TimestampToPrettyTimeDelta( wake_time, just_now_threshold = 0 ) ) )
                    
                
                time.sleep( 0.5 )
                
            
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        job_status.SetStatusTitle( 'just woke up from sleep' )
        
        self.pub( 'message', job_status )
        
        self.CallToThread( do_it, job_status )
        
    
    def _ShutdownManagers( self ):
        
        for manager in self._managers_with_mainloops:
            
            manager.Shutdown()
            
        
        if not self._doing_fast_exit:
            
            started = HydrusTime.GetNow()
            
            while False in ( manager.IsShutdown() for manager in self._managers_with_mainloops ):
                
                self._ReportShutdownManagersStatus()
                
                time.sleep( 0.1 )
                
                if HydrusTime.TimeHasPassed( started + 30 ):
                    
                    break
                    
                
            
        
    
    @staticmethod
    def instance() -> 'Controller':
        
        if Controller.my_instance is None:
            
            raise Exception( 'Controller is not yet initialised!' )
            
        else:
            
            return Controller.my_instance
            
        
    
    def AcquirePageKey( self ):
        
        with self._page_key_lock:
            
            page_key = HydrusData.GenerateKey()
            
            self._alive_page_keys.add( page_key )
            
            return page_key
            
        
    
    def AmInTheMainQtThread( self ) -> bool:
        
        return QC.QThread.currentThread() == self.main_qt_thread
        
    
    def BlockingSafeShowCriticalMessage( self, title: str, message: str ):
        
        ClientGUIDialogsMessage.ShowCritical( self.gui, title, message )
        
    
    def BlockingSafeShowMessage( self, message: str ):
        
        ClientGUIDialogsMessage.ShowInformation( self.gui, message )
        
    
    def CallBlockingToQt( self, win, func: typing.Callable[ callable_P, callable_R ], *args: callable_P.args, **kwargs: callable_P.kwargs ) -> callable_R:
        
        def qt_code( job_status: ClientThreading.JobStatus ):
            
            try:
                
                result = func( *args, **kwargs )
                
                job_status.SetVariable( 'result', result )
                
            except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.DBCredentialsException, HydrusExceptions.ShutdownException, HydrusExceptions.CancelledException ) as e:
                
                job_status.SetErrorException( e )
                
            except Exception as e:
                
                job_status.SetErrorException( e )
                
            finally:
                
                job_status.Finish()
                
            
        
        if self.AmInTheMainQtThread():
            
            return func( *args, **kwargs )
            
        
        job_status = ClientThreading.JobStatus( cancellable = True, cancel_on_shutdown = False )
        
        self.CallAfterQtSafe( win, qt_code, job_status )
        
        # I think in some cases with the splash screen we may actually be pushing stuff here after model shutdown
        # but I also don't want a hang, as we have seen with some GUI async job that got fired on shutdown and it seems some event queue was halted or deadlocked
        # so, we'll give it 16ms to work, then we'll start testing for shutdown hang
        
        done_event = job_status.GetDoneEvent()
        
        while not job_status.IsDone():
            
            if not QP.isValid( win ):
                
                raise HydrusExceptions.QtDeadWindowException( 'Window died before job returned!' )
                
            
            if HG.model_shutdown or not self._qt_app_running:
                
                raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                
            
            done_event.wait( 1.0 )
            
        
        if job_status.HasVariable( 'result' ):
            
            # result can be None, for qt_code that has no return variable
            
            result = job_status.GetIfHasVariable( 'result' )
            
            return result
            
        
        if job_status.HadError():
            
            e = job_status.GetErrorException()
            
            raise e
            
        
        raise HydrusExceptions.ShutdownException()
        
    
    def CallBlockingToQtFireAndForgetNoResponse( self, win, func, *args, **kwargs ) -> None:
        
        try:
            
            self.CallBlockingToQt( win, func, *args, **kwargs )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
            
            pass
            
        
    
    def CallBlockingToQtTLW( self, func: typing.Callable[ callable_P, callable_R ], *args: callable_P.args, **kwargs: callable_P.kwargs ) -> callable_R:
        
        main_tlw = self.GetMainTLW()
        
        if main_tlw is None:
            
            raise HydrusExceptions.ShutdownException( 'Could not find a TLW! I think the program is shutting down or has not yet created a splash!' )
            
        
        try:
            
            return self.CallBlockingToQt( main_tlw, func, *args, **kwargs )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
            
            raise HydrusExceptions.ShutdownException( 'Program is shutting down!' )
            
        
    
    def CallAfterQtSafe( self, qobject: QC.QObject, func, *args, **kwargs ) -> None:
        
        ClientGUICallAfter.CallAfter( self.call_after_catcher, qobject, func, *args, **kwargs )
        
    
    def CallLaterQtSafe( self, window, initial_delay, label, func, *args, **kwargs ) -> ClientThreading.QtAwareJob:
        
        job_scheduler = self._GetAppropriateJobScheduler( initial_delay )
        
        # we set a label so the call won't have to look at Qt objects for a label in the wrong place
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        call.SetLabel( label )
        
        job = ClientThreading.QtAwareJob( self, job_scheduler, window, initial_delay, call )
        
        if job_scheduler is not None:
            
            job_scheduler.AddJob( job )
            
        
        return job
        
    
    def CallRepeatingQtSafe( self, window, initial_delay, period, label, func, *args, **kwargs ) -> ClientThreading.QtAwareRepeatingJob:
        
        job_scheduler = self._GetAppropriateJobScheduler( period )
        
        # we set a label so the call won't have to look at Qt objects for a label in the wrong place
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        call.SetLabel( label )
        
        job = ClientThreading.QtAwareRepeatingJob( self, job_scheduler, window, initial_delay, period, call )
        
        if job_scheduler is not None:
            
            job_scheduler.AddJob( job )
            
        
        return job
        
    
    def CatchSignal( self, sig, frame ):
        
        # yo just to remind here, Windows supports SIGINT (e.g. Ctrl+C from cmd) but not SIGTERM (which it fakes, whenever asked explicitly, by just insta-killing the process) 
        
        if self._program_is_shutting_down:
            
            return
            
        
        if sig == signal.SIGINT:
            
            if self.gui is not None and QP.isValid( self.gui ):
                
                event = QG.QCloseEvent()
                
                QW.QApplication.postEvent( self.gui, event )
                
            else:
                
                self.ExitFast()
                
            
        elif sig == signal.SIGTERM:
            
            self.ExitFast()
            
        
    
    def CheckAlreadyRunning( self ):
        
        while HydrusProcess.IsAlreadyRunning( self.db_dir, 'client' ):
            
            self.frame_splash_status.SetText( 'client already running' )
            
            def qt_code():
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                message = 'It looks like another instance of this client is already running, so this instance cannot start.'
                message += '\n' * 2
                message += 'If the old instance is closing and does not quit for a _very_ long time, it is usually safe to force-close it from task manager.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self._splash, message, title = 'The client is already running.', yes_label = 'wait a bit, then try again', no_label = 'forget it' )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    raise HydrusExceptions.ShutdownException()
                    
                
            
            self.CallBlockingToQtTLW( qt_code )
            
            for i in range( 10, 0, -1 ):
                
                if not HydrusProcess.IsAlreadyRunning( self.db_dir, 'client' ):
                    
                    break
                    
                
                self.frame_splash_status.SetText( 'waiting {} seconds'.format( i ) )
                
                time.sleep( 1 )
                
            
        
    
    def CheckMouseIdle( self ):
        
        mouse_position = QG.QCursor.pos()
        
        if self._last_mouse_position is None:
            
            self._last_mouse_position = mouse_position
            
        elif mouse_position != self._last_mouse_position:
            
            idle_before_position_update = self.CurrentlyIdle()
            
            self.TouchTime( 'last_mouse_action' )
            
            self._last_mouse_position = mouse_position
            
            idle_after_position_update = self.CurrentlyIdle()
            
            move_knocked_us_out_of_idle = ( not idle_before_position_update ) and idle_after_position_update
            
            if move_knocked_us_out_of_idle:
                
                self.pub( 'set_status_bar_dirty' )
                
            
        
    
    def ClearCaches( self ) -> None:
        
        self.images_cache.Clear()
        self.image_tiles_cache.Clear()
        self.thumbnails_cache.Clear()
        
    
    def ClipboardHasImage( self ):
        
        try:
            
            self.GetClipboardImage()
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def ClipboardHasLocalPaths( self ):
        
        try:
            
            self.GetClipboardLocalPaths()
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def ClosePageKeys( self, page_keys ):
        
        with self._page_key_lock:
            
            self._closed_page_keys.update( page_keys )
            
        
    
    def CreateSplash( self, title ):
        
        if self._splash is not None:
            
            self._DestroySplash()
            
        
        try:
            
            self.frame_splash_status.Reset()
            
            self._splash = ClientGUISplash.FrameSplash( self, title, self.frame_splash_status )
            
        except Exception as e:
            
            HydrusData.Print( 'There was an error trying to start the splash screen!' )
            
            HydrusData.Print( traceback.format_exc() )
            
            raise
            
        
    
    def CurrentlyIdle( self ):
        
        if self._program_is_shutting_down:
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( 'IDLE MODE - Blocked: Program shutting down.' )
                
            
            return False
            
        
        if HG.force_idle_mode:
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( 'IDLE MODE - Forced via debug menu' )
                
            
            self._idle_started = 0
            
            return True
            
        
        if not HydrusTime.TimeHasPassedMS( self.GetBootTimestampMS() + ( 120 * 1000 ) ):
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( 'IDLE MODE - Blocked: Program has not been on for 120s yet.' )
                
            
            return False
            
        
        idle_normal = self.options[ 'idle_normal' ]
        
        if idle_normal:
            
            currently_idle = True
            
            idle_period_ms = HydrusTime.MillisecondiseS( self.options[ 'idle_period' ] )
            
            if idle_period_ms is not None:
                
                if not HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_user_action' ) + idle_period_ms ):
                    
                    if HG.idle_report_mode:
                        
                        HydrusData.ShowText( f'IDLE MODE - Blocked: Last user action was {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( self.GetTimestampMS( "last_user_action" ) ) )}.' )
                        
                    
                    currently_idle = False
                    
                
            
            idle_mouse_period_ms = HydrusTime.MillisecondiseS( self.options[ 'idle_mouse_period' ] )
            
            if idle_mouse_period_ms is not None:
                
                if not HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_mouse_action' ) + idle_mouse_period_ms ):
                    
                    if HG.idle_report_mode:
                        
                        HydrusData.ShowText( f'IDLE MODE - Blocked: Last mouse move was {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( self.GetTimestampMS( "last_mouse_action" ) ) )}.' )
                        
                    
                    currently_idle = False
                    
                
            
            idle_mode_client_api_timeout_ms = HydrusTime.MillisecondiseS( self.new_options.GetNoneableInteger( 'idle_mode_client_api_timeout' ) )
            
            if idle_mode_client_api_timeout_ms is not None:
                
                if not HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_client_api_action' ) + idle_mode_client_api_timeout_ms ):
                    
                    if HG.idle_report_mode:
                        
                        HydrusData.ShowText( f'IDLE MODE - Blocked: Last Client API action was {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( self.GetTimestampMS( "last_client_api_action" ) ) )}.' )
                        
                    
                    currently_idle = False
                    
                
            
        else:
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( 'IDLE MODE - Blocked: Options have disabled normal idle work.' )
                
            
            currently_idle = False
            
        
        turning_idle = currently_idle and not self._previously_idle
        turning_active = self._previously_idle and not currently_idle
        
        self._previously_idle = currently_idle
        
        if turning_idle:
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( f'IDLE MODE - Turning ON' )
                
            
            self._idle_started = HydrusTime.GetNow()
            
            self.pub( 'wake_daemons' )
            
        
        if turning_active:
            
            if HG.idle_report_mode:
                
                HydrusData.ShowText( f'IDLE MODE - Turning OFF' )
                
            
        
        if not currently_idle:
            
            self._idle_started = None
            
        
        return currently_idle
        
    
    def CurrentlyVeryIdle( self ):
        
        if self._program_is_shutting_down:
            
            return False
            
        
        if self._idle_started is not None and HydrusTime.TimeHasPassed( self._idle_started + 3600 ):
            
            return True
            
        
        return False
        
    
    def DoIdleShutdownWork( self ):
        
        self.frame_splash_status.SetSubtext( 'db' )
        
        stop_time = HydrusTime.GetNow() + ( self.options[ 'idle_shutdown_max_minutes' ] * 60 )
        
        self.MaintainDB( maintenance_mode = HC.MAINTENANCE_SHUTDOWN, stop_time = stop_time )
        
        if not self.new_options.GetBoolean( 'pause_repo_sync' ):
            
            services = self.services_manager.GetServices( HC.REPOSITORIES, randomised = True )
            
            for service in services:
                
                if HydrusTime.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                service = typing.cast( ClientServices.ServiceRepository, service )
                
                self.frame_splash_status.SetSubtext( '{} processing'.format( service.GetName() ) )
                
                service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_SHUTDOWN, stop_time = stop_time )
                
            
        
        self.Write( 'register_shutdown_work' )
        
    
    def DoSelfSigterm( self ):
        
        def do_it():
            
            pid = os.getpid()
            
            os.kill( pid, signal.SIGTERM )
            
        
        thread = threading.Thread( target = do_it )
        
        thread.start()
        
    
    def DoSelfSigtermFake( self ):
        
        # Windows doesn't support sigterm, it just kills the process, so this will fake it for us
        
        def do_it():
            
            self._doing_fast_exit = True
            
            self.Exit()
            
        
        thread = threading.Thread( target = do_it )
        
        thread.start()
        
    
    def Exit( self ):
        
        # this is idempotent and does not stop. we are shutting down now or in the very near future
        
        def prep_gui():
            
            try:
                
                if not self._doing_fast_exit:
                    
                    self.CreateSplash( 'hydrus client exiting' )
                    
                    if HG.do_idle_shutdown_work:
                        
                        self._splash.ShowCancelShutdownButton()
                        
                    
                
                if self.gui is not None and QP.isValid( self.gui ):
                    
                    self.frame_splash_status.SetTitleText( 'saving and hiding gui' + HC.UNICODE_ELLIPSIS )
                    
                    self.gui.SaveAndHide()
                    
                
            except Exception:
                
                self._ReportShutdownException()
                
            
        
        def save_objects():
            
            try:
                
                HG.started_shutdown = True
                
                self.frame_splash_status.SetTitleText( 'shutting down gui' + HC.UNICODE_ELLIPSIS )
                
                self.ShutdownView()
                
                self.frame_splash_status.SetTitleText( 'shutting down db' + HC.UNICODE_ELLIPSIS )
                
                self.ShutdownModel()
                
                if self._restore_backup_path is not None:
                    
                    self.frame_splash_status.SetTitleText( 'restoring backup' + HC.UNICODE_ELLIPSIS )
                    
                    self.db.RestoreBackup( self._restore_backup_path )
                    
                
                self.frame_splash_status.SetTitleText( 'cleaning up' + HC.UNICODE_ELLIPSIS )
                
                self.CleanRunningFile()
                
            except ( HydrusExceptions.DBCredentialsException, HydrusExceptions.ShutdownException ):
                
                pass
                
            except Exception as e:
                
                self._ReportShutdownException()
                
            finally:
                
                qapp = QW.QApplication.instance()
                
                qapp.setProperty( 'exit_complete', True )
                
                self._DestroySplash()
                
                self._program_is_shut_down = True
                
                self.CallAfterQtSafe( qapp, QW.QApplication.exit )
                
            
        
        if self._program_is_shutting_down:
            
            return
            
        
        self._program_is_shutting_down = True
        
        if not self._is_booted:
            
            self._doing_fast_exit = True
            
        
        if self.AmInTheMainQtThread():
            
            prep_gui()
            
        else:
            
            if self.gui is not None and QP.isValid( self.gui ):
                
                self.CallBlockingToQtFireAndForgetNoResponse( self.gui, prep_gui )
                
            
        
        if self._doing_fast_exit:
            
            HydrusData.DebugPrint( 'doing fast shutdown' + HC.UNICODE_ELLIPSIS )
            
            save_objects()
            
        else:
            
            self.CallToThreadLongRunning( save_objects )
            
        
    
    def ExitFast( self ):
        
        self._doing_fast_exit = True
        
        self.Exit()
        
    
    def FlipQueryPlannerMode( self ):
        
        from hydrus.core import HydrusProfiling
        
        HydrusProfiling.FlipQueryPlannerMode()
        
    
    def GetClipboardImage( self ):
        
        clipboard_image = QW.QApplication.clipboard().image()
        
        if clipboard_image is None or clipboard_image.isNull():
            
            raise HydrusExceptions.DataMissing( 'No bitmap on the clipboard!' )
            
        
        return clipboard_image
        
    
    def GetClipboardLocalPaths( self ):
        
        mime_data = QW.QApplication.clipboard().mimeData()
        
        if mime_data.hasUrls():
            
            urls = mime_data.urls()
            
            local_paths = [ url.toLocalFile() for url in urls if url.isLocalFile() ]
            
            if len( local_paths ) > 0:
                
                return local_paths
                
            
        
        raise HydrusExceptions.DataMissing( 'No local paths on clipboard!' )
        
    
    def GetClipboardText( self ):
        
        clipboard_text = QW.QApplication.clipboard().text()
        
        if clipboard_text is None:
            
            raise HydrusExceptions.DataMissing( 'No text on the clipboard!' )
            
        
        clipboard_text = HydrusText.CleanseImportText( clipboard_text )
        
        return clipboard_text
        
    
    def GetDefaultMPVConfPath( self ):
        
        return HydrusStaticDir.GetStaticPath( os.path.join( 'mpv-conf', 'default_mpv.conf' ) )
        
    
    def GetIdleShutdownWorkDue( self, time_to_stop ):
        
        work_to_do = []
        
        work_to_do.extend( self.Read( 'maintenance_due', time_to_stop ) )
        
        services = self.services_manager.GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            service = typing.cast( ClientServices.ServiceRepository, service )
            
            if service.CanDoIdleShutdownWork():
                
                work_to_do.append( service.GetName() + ' repository processing' )
                
            
        
        return work_to_do
        
    
    def GetMainGUI( self ):
        
        if self.gui is not None:
            
            return self.gui
            
        else:
            
            return None
            
        
    
    def GetMainTLW( self ):
        
        if self.gui is not None:
            
            return self.gui
            
        elif self._splash is not None:
            
            return self._splash
            
        else:
            
            return None
            
        
    
    def GetMPVConfPath( self ):
        
        return os.path.join( self.db_dir, 'mpv.conf' )
        
    
    def GetNewOptions( self ):
        
        return self.new_options
        
    
    def GetImportSensitiveDirectories( self ):
        
        dirs_that_allow_internal_work = [ HC.BASE_DIR, self.db_dir ]
        
        dirs_that_cannot_be_touched = self.client_files_manager.GetAllDirectoriesInUse()
        
        return ( dirs_that_allow_internal_work, dirs_that_cannot_be_touched )
        
    
    def GetSplash( self ):
        
        return self._splash
        
    
    def InitClientFilesManager( self ):
        
        def qt_code( missing_subfolders ):
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            
            with ClientGUITopLevelWindowsPanels.DialogManage( None, 'repair file system' ) as dlg:
                
                from hydrus.client.gui.panels import ClientGUIRepairFileSystemPanel
                
                panel = ClientGUIRepairFileSystemPanel.RepairFileSystemPanel( dlg, missing_subfolders )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    self.client_files_manager = ClientFilesManager.ClientFilesManager( self )
                    
                    missing_subfolders = self.client_files_manager.GetMissingSubfolders()
                    
                else:
                    
                    raise HydrusExceptions.ShutdownException( 'File system failed, user chose to quit.' )
                    
                
            
            return missing_subfolders
            
        
        self.client_files_manager = ClientFilesManager.ClientFilesManager( self )
        
        missing_subfolders = self.client_files_manager.GetMissingSubfolders()
        
        while len( missing_subfolders ) > 0:
            
            missing_subfolders = self.CallBlockingToQtTLW( qt_code, missing_subfolders )
            
        
    
    def ReinitGlobalSettings( self ):
        
        from hydrus.core.files.images import HydrusImageHandling
        from hydrus.core.files.images import HydrusImageNormalisation
        from hydrus.core.files.images import HydrusImageColours
        
        HydrusImageHandling.SetEnableLoadTruncatedImages( self.new_options.GetBoolean( 'enable_truncated_images_pil' ) )
        HydrusImageNormalisation.SetDoICCProfileNormalisation( self.new_options.GetBoolean( 'do_icc_profile_normalisation' ) )
        HydrusImageColours.SetHasTransparencyStrictnessLevel( self.new_options.GetInteger( 'file_has_transparency_strictness' ) )
        
        HydrusImageHandling.FORCE_PIL_ALWAYS = self.new_options.GetBoolean( 'load_images_with_pil' )
        
        from hydrus.core import HydrusTime
        
        HydrusTime.ALWAYS_SHOW_ISO_TIME_ON_DELTA_CALL = self.new_options.GetBoolean( 'always_show_iso_time' )
        
        from hydrus.core import HydrusPaths
        
        HydrusPaths.DO_NOT_DO_CHMOD_MODE = self.new_options.GetBoolean( 'do_not_do_chmod_mode' )
        
    
    def InitModel( self ):
        
        from hydrus.client import ClientManagers
        
        self.frame_splash_status.SetTitleText( 'booting db' + HC.UNICODE_ELLIPSIS )
        
        # important this happens early mate, do not slide it down
        HydrusController.HydrusController.InitModel( self )
        
        self.frame_splash_status.SetSubtext( 'options' )
        
        self.options = self.Read( 'options' )
        self.new_options = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
        
        HC.options = self.options
        
        if self.new_options.GetBoolean( 'use_system_ffmpeg' ):
            
            from hydrus.core.files import HydrusFFMPEG
            
            if HydrusFFMPEG.FFMPEG_PATH.startswith( HC.BIN_DIR ):
                
                HydrusFFMPEG.FFMPEG_PATH = os.path.basename( HydrusFFMPEG.FFMPEG_PATH )
                
            
        
        self.frame_splash_status.SetSubtext( 'image caches' )
        
        self.images_cache = ClientCaches.ImageRendererCache( self )
        self.image_tiles_cache = ClientCaches.ImageTileCache( self )
        self.thumbnails_cache = ClientCaches.ThumbnailCache( self )
        
        self.frame_splash_status.SetText( 'initialising managers' )
        
        # careful: outside of qt since they don't need qt for init, seems ok _for now_
        
        self.bitmap_manager = ClientManagers.BitmapManager( self )
        
        self.frame_splash_status.SetSubtext( 'services' )
        
        self.services_manager = ClientServices.ServicesManager( self )
        
        # important this happens before repair, as repair dialog has a column list lmao
        
        from hydrus.client.gui.lists import ClientGUIListManager
        
        column_list_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_COLUMN_LIST_MANAGER )
        
        if column_list_manager is None:
            
            column_list_manager = ClientGUIListManager.ColumnListManager()
            
            column_list_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your list manager was missing on boot! I have recreated a new empty one with default settings. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        self.column_list_manager = column_list_manager
        
        self.frame_splash_status.SetSubtext( 'client files' )
        
        self.InitClientFilesManager()
        
        #
        
        self.frame_splash_status.SetSubtext( 'network' )
        
        if self.new_options.GetBoolean( 'set_requests_ca_bundle_env' ):
            
            from hydrus.client import ClientEnvironment
            
            ClientEnvironment.SetRequestsCABundleEnv()
            
        
        if self.new_options.GetBoolean( 'boot_with_network_traffic_paused' ) or HG.boot_with_network_traffic_paused_command_line:
            
            CG.client_controller.new_options.SetBoolean( 'pause_all_new_network_traffic', True )
            
        
        self.parsing_cache = ClientCaches.ParsingCache()
        
        from hydrus.client import ClientAPI
        
        client_api_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_MANAGER )
        
        if client_api_manager is None:
            
            client_api_manager = ClientAPI.APIManager()
            
            client_api_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your client api manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        self.client_api_manager = client_api_manager
        
        from hydrus.client.networking import ClientNetworkingBandwidth
        
        bandwidth_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER )
        
        if bandwidth_manager is None:
            
            bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
            
            tracker_containers = self.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER )
            
            bandwidth_manager.SetTrackerContainers( tracker_containers )
            
            ClientDefaults.SetDefaultBandwidthManagerRules( bandwidth_manager )
            
            bandwidth_manager.SetDirty()
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your bandwidth manager was missing on boot! I have recreated a new one. It may have your bandwidth record, but some/all may be missing. Your rules have been reset to default. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        from hydrus.client.networking import ClientNetworkingSessions
        
        session_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER )
        
        if session_manager is None:
            
            session_manager = ClientNetworkingSessions.NetworkSessionManager()
            
            session_containers = self.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER )
            
            session_manager.SetSessionContainers( session_containers )
            
            session_manager.SetDirty()
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your session manager was missing on boot! I have recreated a new one. It may have your sessions, or some/all may be missing. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        from hydrus.client.networking import ClientNetworkingDomain
        
        domain_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
        
        if domain_manager is None:
            
            domain_manager = ClientNetworkingDomain.NetworkDomainManager()
            
            ClientDefaults.SetDefaultDomainManagerData( domain_manager )
            
            domain_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your domain manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        domain_manager.Initialise()
        
        from hydrus.client.networking import ClientNetworkingLogin
        
        login_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER )
        
        if login_manager is None:
            
            login_manager = ClientNetworkingLogin.NetworkLoginManager()
            
            ClientDefaults.SetDefaultLoginManagerScripts( login_manager )
            
            login_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your login manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        login_manager.Initialise()
        
        from hydrus.client.networking import ClientNetworking
        
        self.network_engine = ClientNetworking.NetworkEngine( self, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.CallToThreadLongRunning( self.network_engine.MainLoop )
        
        #
        
        from hydrus.client import ClientDownloading
        
        self.quick_download_manager = ClientDownloading.QuickDownloadManager( self )
        
        self._managers_with_mainloops.append( self.quick_download_manager )
        
        self.CallToThreadLongRunning( self.quick_download_manager.MainLoop )
        
        #
        
        self.file_viewing_stats_manager = ClientManagers.FileViewingStatsManager( self )
        
        #
        
        self.frame_splash_status.SetSubtext( 'tag display' )
        
        # note that this has to be made before siblings/parents managers, as they rely on it
        
        from hydrus.client.metadata import ClientTagsHandling
        
        tag_display_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER )
        
        if tag_display_manager is None:
            
            tag_display_manager = ClientTagsHandling.TagDisplayManager()
            
            tag_display_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your tag display manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        self.tag_display_manager = tag_display_manager
        
        self.tag_display_maintenance_manager = ClientTagsHandling.TagDisplayMaintenanceManager( self )
        
        self._managers_with_mainloops.append( self.tag_display_maintenance_manager )
        
        self.tag_display_maintenance_manager.Start()
        
        from hydrus.client.duplicates import ClientPotentialDuplicatesManager
        
        self.potential_duplicates_manager = ClientPotentialDuplicatesManager.PotentialDuplicatesMaintenanceManager( self )
        
        self._managers_with_mainloops.append( self.potential_duplicates_manager )
        
        self.potential_duplicates_manager.Start()
        
        #
        
        self.frame_splash_status.SetSubtext( 'favourite searches' )
        
        from hydrus.client.search import ClientSearchFavouriteSearches
        
        favourite_search_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER )
        
        if favourite_search_manager is None:
            
            favourite_search_manager = ClientSearchFavouriteSearches.FavouriteSearchManager()
            
            ClientDefaults.SetDefaultFavouriteSearchManagerData( favourite_search_manager )
            
            favourite_search_manager._dirty = True
            
            self.BlockingSafeShowCriticalMessage( 'Problem loading object', 'Your favourite searches manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        self.favourite_search_manager = favourite_search_manager
        
        #
        
        self._managers[ 'undo' ] = ClientManagers.UndoManager( self )
        
        self.sub( self, 'ToClipboard', 'clipboard' )
        
    
    def InitView( self ):
        
        if self.options[ 'password' ] is not None:
            
            self.frame_splash_status.SetText( 'waiting for password' )
            
            def qt_code_password():
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                while True:
                    
                    try:
                        
                        password_str = ClientGUIDialogsQuick.EnterText( self._splash, 'Enter your password.', allow_blank = False, password_entry = True, min_char_width = 36 )
                        
                    except HydrusExceptions.CancelledException:
                        
                        raise HydrusExceptions.DBCredentialsException( 'Bad password check' )
                        
                    
                    password_bytes = bytes( password_str, 'utf-8' )
                    
                    if hashlib.sha256( password_bytes ).digest() == self.options[ 'password' ]:
                        
                        break
                        
                    
                
            
            self.CallBlockingToQtTLW( qt_code_password )
            
        
        self.frame_splash_status.SetTitleText( 'booting gui' + HC.UNICODE_ELLIPSIS )
        
        self.files_maintenance_manager = ClientFilesMaintenance.FilesMaintenanceManager( self )
        
        self._managers_with_mainloops.append( self.files_maintenance_manager )
        
        from hydrus.client import ClientDBMaintenanceManager
        
        self.database_maintenance_manager = ClientDBMaintenanceManager.DatabaseMaintenanceManager( self )
        
        self._managers_with_mainloops.append( self.database_maintenance_manager )
        
        from hydrus.client.duplicates import ClientDuplicatesAutoResolution
        
        self.duplicates_auto_resolution_manager = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager( self )
        
        self._managers_with_mainloops.append( self.duplicates_auto_resolution_manager )
        
        from hydrus.client.importing import ClientImportLocal
        
        self.import_folders_manager = ClientImportLocal.ImportFoldersManager( self )
        
        self._managers_with_mainloops.append( self.import_folders_manager )
        
        from hydrus.client.importing import ClientImportSubscriptions
        
        subscriptions = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
        
        self.subscriptions_manager = ClientImportSubscriptions.SubscriptionsManager( self, subscriptions )
        
        self._managers_with_mainloops.append( self.subscriptions_manager )
        
        def qt_code_style():
            
            from hydrus.client.gui import ClientGUIStyle
            
            ClientGUIStyle.InitialiseDefaults()
            
            qt_style_name = self.new_options.GetNoneableString( 'qt_style_name' )
            
            if qt_style_name is not None:
                
                try:
                    
                    ClientGUIStyle.SetStyleFromName( qt_style_name )
                    
                except Exception as e:
                    
                    HydrusData.Print( 'Could not load Qt style: {}'.format( repr( e ) ) )
                    
                
            
            qt_stylesheet_name = self.new_options.GetNoneableString( 'qt_stylesheet_name' )
            
            if qt_stylesheet_name is None:
                
                ClientGUIStyle.ClearStyleSheet()
                
            else:
                
                try:
                    
                    ClientGUIStyle.SetStyleSheetFromPath( qt_stylesheet_name )
                    
                except Exception as e:
                    
                    HydrusData.Print( 'Could not load Qt stylesheet: {}'.format( repr( e ) ) )
                    
                
            
        
        self.CallBlockingToQtTLW( qt_code_style )
        
        self.ReinitGlobalSettings()
        
        def qt_code_pregui():
            
            shortcut_sets = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            from hydrus.client.gui import ClientGUIShortcuts
            
            # initialises singleton
            ClientGUIShortcuts.ShortcutsManager( shortcut_sets = shortcut_sets )
            
        
        self.CallBlockingToQtTLW( qt_code_pregui )
        
        from hydrus.client.gui import ClientGUIPopupMessages
        
        # got to keep this before gui instantiation, since it uses it
        self.job_status_popup_queue = ClientGUIPopupMessages.JobStatusPopupQueue()
        
        def qt_code_gui():
            
            from hydrus.client.gui import ClientGUI
            
            self.gui = ClientGUI.FrameGUI( self )
            
            self.ResetIdleTimer()
            
        
        self.CallBlockingToQtTLW( qt_code_gui )
        
        # ShowText will hereafter popup as a message, as the GUI's popup message manager has overwritten the hooks
        
        HydrusController.HydrusController.InitView( self )
        
        self._service_keys_to_connected_ports = {}
        
        self.RestartClientServerServices()
        
        job = self.CallRepeatingQtSafe( self.gui, 10.0, 10.0, 'repeating mouse idle check', self.CheckMouseIdle )
        self._daemon_jobs[ 'check_mouse_idle' ] = job
        
        if self.db.IsFirstStart():
            
            message = 'Hi, this looks like the first time you have started the hydrus client. If this is not the first time you have run this client install, please check the help documentation under "install_dir/db".'
            message += '\n' * 2
            message += 'Don\'t forget to check out the help if you haven\'t already, by clicking help->help--it has an extensive \'getting started\' section, including how to update and the importance of backing up your database.'
            message += '\n' * 2
            message += 'To dismiss popup messages like this, right-click them.'
            
            HydrusData.ShowText( message )
            
            if HC.WE_SWITCHED_TO_USERPATH:
                
                message = f'Hey, it also looks like the default database location at "{HC.DEFAULT_DB_DIR}" was not writable-to, so the client has fallen back to using your userpath at "{HC.USERPATH_DB_DIR}"'
                message += '\n' * 2
                message += 'If that is fine with you, no problem. But if you were expecting to load an existing database and the above "first start" popup is a surprise, then your old db path is probably read-only. Fix that and try again. If it helps, hit up help->about to see the directories hydrus is currently using.'
                
                HydrusData.ShowText( message )
                
            
        
        if self.db.IsDBUpdated():
            
            HydrusData.ShowText( 'The client has updated to version {}!'.format( HC.SOFTWARE_VERSION ) )
            
        
        for message in self.db.GetInitialMessages():
            
            HydrusData.ShowText( message )
            
        
    
    def IsBooted( self ):
        
        return self._is_booted
        
    
    def MaintainDB( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        if maintenance_mode == HC.MAINTENANCE_IDLE and not self.GoodTimeToStartBackgroundWork():
            
            return
            
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        self.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
    
    def MaintainHashedSerialisables( self ):
        
        self.WriteSynchronous( 'maintain_hashed_serialisables' )
        
    
    def MaintainMemoryFast( self ):
        
        HydrusController.HydrusController.MaintainMemoryFast( self )
        
        self.parsing_cache.CleanCache()
        
    
    def MaintainMemorySlow( self ):
        
        HydrusController.HydrusController.MaintainMemorySlow( self )
        
        if HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_page_change' ) + 30 * 60000 ):
            
            self.pub( 'delete_old_closed_pages' )
            
            self.TouchTime( 'last_page_change' )
            
        
        def do_gui_refs( gui ):
            
            self.gui.MaintainCanvasFrameReferences()
            
        
        if self.gui is not None:
            
            self.CallAfterQtSafe( self.gui, do_gui_refs, self.gui )
            
        
    
    def PageAlive( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key in self._alive_page_keys
            
        
    
    def PageAliveAndNotClosed( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key in self._alive_page_keys and page_key not in self._closed_page_keys
            
        
    
    def PageClosedButNotDestroyed( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key in self._closed_page_keys
            
        
    
    def PageDestroyed( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key not in self._alive_page_keys and page_key not in self._closed_page_keys
            
        
    
    def PrepStringForDisplay( self, text ):
        
        return text.lower()
        
    
    def ProgramIsShutDown( self ):
        
        return self._program_is_shut_down
        
    
    def ProgramIsShuttingDown( self ):
        
        return self._program_is_shutting_down
        
    
    def pub( self, *args, **kwargs ):
        
        HydrusController.HydrusController.pub( self, *args, **kwargs )
        
        app = typing.cast( App, QW.QApplication.instance() )
        
        QW.QApplication.postEvent( app.pubsub_catcher, PubSubEvent() )
        
    
    def RefreshServices( self ):
        
        self.services_manager.RefreshServices()
        
    
    def ReleasePageKey( self, page_key ):
        
        with self._page_key_lock:
            
            self._alive_page_keys.discard( page_key )
            self._closed_page_keys.discard( page_key )
            
        
    
    def ReportLastSessionLoaded( self, gui_session ):
        
        if self._last_last_session_hash is None:
            
            self._last_last_session_hash = gui_session.GetSerialisedHash()
            
        
    
    def ReportFirstSessionInitialised( self ):
        
        job = self.CallRepeating( 5.0, 3600.0, self.SynchroniseAccounts )
        job.ShouldDelayOnWakeup( True )
        job.WakeOnPubSub( 'notify_account_sync_due' )
        job.WakeOnPubSub( 'notify_network_traffic_unpaused' )
        self._daemon_jobs[ 'synchronise_accounts' ] = job
        
        from hydrus.core.networking import HydrusNetwork
        
        job = self.CallRepeating( 5.0, HydrusNetwork.UPDATE_CHECKING_PERIOD, self.SynchroniseRepositories )
        job.ShouldDelayOnWakeup( True )
        job.WakeOnPubSub( 'notify_restart_repo_sync' )
        job.WakeOnPubSub( 'notify_new_permissions' )
        job.WakeOnPubSub( 'wake_idle_workers' )
        job.WakeOnPubSub( 'notify_network_traffic_unpaused' )
        self._daemon_jobs[ 'synchronise_repositories' ] = job
        '''
        job = self.CallRepeating( 5.0, 180.0, ClientDaemons.DAEMONCheckImportFolders )
        job.WakeOnPubSub( 'notify_restart_import_folders_daemon' )
        job.WakeOnPubSub( 'notify_new_import_folders' )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'import_folders' ] = job
        '''
        job = self.CallRepeating( 5.0, 180.0, ClientDaemons.DAEMONCheckExportFolders )
        job.WakeOnPubSub( 'notify_restart_export_folders_daemon' )
        job.WakeOnPubSub( 'notify_new_export_folders' )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'export_folders' ] = job
        
        job = self.CallRepeating( 30.0, 3600.0, ClientDaemons.DAEMONMaintainTrash )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'maintain_trash' ] = job
        
        job = self.CallRepeating( 0.0, 30.0, self.SaveDirtyObjectsImportant )
        job.WakeOnPubSub( 'important_dirt_to_clean' )
        self._daemon_jobs[ 'save_dirty_objects_important' ] = job
        
        job = self.CallRepeating( 0.0, 300.0, self.SaveDirtyObjectsInfrequent )
        self._daemon_jobs[ 'save_dirty_objects_infrequent' ] = job
        
        job = self.CallRepeating( 30.0, 86400.0, self.client_files_manager.DoDeferredPhysicalDeletes )
        job.WakeOnPubSub( 'notify_new_physical_file_deletes' )
        self._daemon_jobs[ 'deferred_physical_deletes' ] = job
        
        job = self.CallRepeating( 30.0, 600.0, self.MaintainHashedSerialisables )
        job.WakeOnPubSub( 'maintain_hashed_serialisables' )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'maintain_hashed_serialisables' ] = job
        
        self.files_maintenance_manager.Start()
        self.database_maintenance_manager.Start()
        self.duplicates_auto_resolution_manager.Start()
        self.import_folders_manager.Start()
        self.subscriptions_manager.Start()
        
    
    def ResetIdleTimerFromClientAPI( self ):
        
        self.TouchTime( 'last_client_api_action' )
        
    
    def ResetPageChangeTimer( self ):
        
        self.TouchTime( 'last_page_change' )
        
    
    def RestartClientServerServices( self ):
        
        services = [ self.services_manager.GetService( service_key ) for service_key in ( CC.CLIENT_API_SERVICE_KEY, ) ]
        
        services = [ service for service in services if service.GetPort() is not None ]
        
        self.CallToThreadLongRunning( self.SetRunningTwistedServices, services )
        
    
    def RestoreDatabase( self ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        try:
            
            path = ClientGUIDialogsQuick.PickDirectory( self.gui, 'Select backup location.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        text = 'Are you sure you want to restore a backup from "{}"?'.format( path )
        text += '\n' * 2
        text += 'Everything in your current database will be deleted!'
        text += '\n' * 2
        text += 'The gui will shut down, and then it will take a while to complete the restore. Once it is done, the client will restart.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self.gui, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._restore_backup_path = path
            self._doing_fast_exit = False
            HG.do_idle_shutdown_work = False
            HG.restart = True
            
            self.Exit()
            
        
    
    def Run( self ):
        
        from hydrus.client.gui import QtInit
        
        QtInit.MonkeyPatchMissingMethods()
        
        from hydrus.client.gui import ClientGUICore
        
        ClientGUICore.GUICore()
        
        if HC.PLATFORM_WINDOWS and HC.RUNNING_FROM_SOURCE:
            
            try:
                
                # this makes the 'application user model' of the program unique, allowing instantiations to group on their own taskbar icon
                # also allows the window icon to go to the taskbar icon, instead of python if you are running from source
                
                import ctypes
                
                # noinspection PyUnresolvedReferences
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID( 'hydrus network client' )
                
            except Exception as e:
                
                pass
                
            
        
        self.app = App( self._pubsub, sys.argv )
        
        self.main_qt_thread = self.app.thread()
        
        HydrusData.Print( 'booting controller' + HC.UNICODE_ELLIPSIS )
        
        self.frame_splash_status = ClientGUISplash.FrameSplashStatus()
        
        self.CreateSplash( 'hydrus client booting' )
        
        # Ok so this stuff may or may not be caught correctly depending on how Qt wants to intercept it
        # it seems Qt _may_ in some cases catch SIGTERM and just call app.quit, which leads to aboutToQuit
        # so I've made both ways go to the same fast exit
        signal.signal( signal.SIGINT, self.CatchSignal )
        signal.signal( signal.SIGTERM, self.CatchSignal )
        
        self.CallToThreadLongRunning( self.THREADBootEverything )
        
        self._qt_app_running = True
        
        try:
            
            self.app.exec_()
            
        finally:
            
            self._qt_app_running = False
            
        
        HydrusData.DebugPrint( 'shutting down controller' + HC.UNICODE_ELLIPSIS )
        
    
    def SaveDirtyObjectsImportant( self ):
        
        with HG.dirty_object_lock:
            
            dirty_services = [ service for service in self.services_manager.GetServices() if service.IsDirty() ]
            
            if len( dirty_services ) > 0:
                
                self.frame_splash_status.SetSubtext( 'services' )
                
                self.WriteSynchronous( 'dirty_services', dirty_services )
                
            
            if self.client_api_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'client api manager' )
                
                self.WriteSynchronous( 'serialisable', self.client_api_manager )
                
                self.client_api_manager.SetClean()
                
            
            if self.network_engine.domain_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'domain manager' )
                
                self.WriteSynchronous( 'serialisable', self.network_engine.domain_manager )
                
                self.network_engine.domain_manager.SetClean()
                
            
            if self.network_engine.login_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'login manager' )
                
                self.WriteSynchronous( 'serialisable', self.network_engine.login_manager )
                
                self.network_engine.login_manager.SetClean()
                
            
            if self.favourite_search_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'favourite searches manager' )
                
                self.WriteSynchronous( 'serialisable', self.favourite_search_manager )
                
                self.favourite_search_manager.SetClean()
                
            
            if self.tag_display_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'tag display manager' )
                
                self.WriteSynchronous( 'serialisable', self.tag_display_manager )
                
                self.tag_display_manager.SetClean()
                
            
        
    
    def SaveDirtyObjectsInfrequent( self ):
        
        with HG.dirty_object_lock:
            
            if self.column_list_manager.IsDirty():
                
                self.frame_splash_status.SetSubtext( 'column list manager' )
                
                self.WriteSynchronous( 'serialisable', self.column_list_manager )
                
                self.column_list_manager.SetClean()
                
            
            if self.network_engine.bandwidth_manager.IsDirty() or self.network_engine.bandwidth_manager.HasDirtyTrackerContainers():
                
                self.frame_splash_status.SetSubtext( 'bandwidth manager' )
                
                self.WriteSynchronous( 'serialisable', self.network_engine.bandwidth_manager )
                
                self.network_engine.bandwidth_manager.SetClean()
                
            
            if self.network_engine.session_manager.IsDirty() or self.network_engine.session_manager.HasDirtySessionContainers():
                
                self.frame_splash_status.SetSubtext( 'session manager' )
                
                self.WriteSynchronous( 'serialisable', self.network_engine.session_manager )
                
                self.network_engine.session_manager.SetClean()
                
            
        
    
    def SaveGUISession( self, session ):
        
        name = session.GetName()
        
        if name == CC.LAST_SESSION_SESSION_NAME:
            
            session_hash = session.GetSerialisedHash()
            
            # keep this in. we still don't want to overwrite backups if no changes have occurred
            if session_hash == self._last_last_session_hash:
                
                return
                
            
            self._last_last_session_hash = session_hash
            
        
        self.WriteSynchronous( 'serialisable', session )
        
        self.pub( 'notify_new_sessions' )
        
    
    def SetRunningTwistedServices( self, services ):
        
        def TWISTEDDoIt():
            
            def StartServices( *args, **kwargs ):
                
                HydrusData.Print( 'starting services' + HC.UNICODE_ELLIPSIS )
                
                for service in services:
                    
                    service_key = service.GetServiceKey()
                    service_type = service.GetServiceType()
                    
                    name = service.GetName()
                    
                    port = service.GetPort()
                    allow_non_local_connections = service.AllowsNonLocalConnections()
                    use_https = service.UseHTTPS()
                    
                    if port is None:
                        
                        continue
                        
                    
                    if allow_non_local_connections:
                        
                        ipv6_interface = '::'
                        ipv4_interface = ''
                        
                    else:
                        
                        ipv6_interface = '::1'
                        ipv4_interface = '127.0.0.1'
                        
                    
                    try:
                        
                        from hydrus.client.networking.api import ClientLocalServer
                        
                        if service_type == HC.CLIENT_API_SERVICE:
                            
                            http_factory = ClientLocalServer.HydrusServiceClientAPI( service, allow_non_local_connections = allow_non_local_connections )
                            
                        else:
                            
                            raise NotImplementedError( 'Unknown service type!' )
                            
                        
                        context_factory = None
                        
                        if use_https:
                            
                            from hydrus.core.networking import HydrusServerContextFactory
                            
                            ( ssl_cert_path, ssl_key_path ) = self.db.GetSSLPaths()
                            
                            context_factory = HydrusServerContextFactory.GenerateSSLContextFactory( ssl_cert_path, ssl_key_path )
                            
                        
                        ipv6_port = None
                        
                        try:
                            
                            if use_https:
                                
                                ipv6_port = reactor.listenSSL( port, http_factory, context_factory, interface = ipv6_interface )
                                
                            else:
                                
                                ipv6_port = reactor.listenTCP( port, http_factory, interface = ipv6_interface )
                                
                            
                        except Exception as e:
                            
                            HydrusData.Print( 'Could not bind to IPv6:' )
                            
                            HydrusData.Print( str( e ) )
                            
                        
                        ipv4_port = None
                        
                        try:
                            
                            if use_https:
                                
                                ipv4_port = reactor.listenSSL( port, http_factory, context_factory, interface = ipv4_interface )
                                
                            else:
                                
                                ipv4_port = reactor.listenTCP( port, http_factory, interface = ipv4_interface )
                                
                            
                        except Exception as e:
                            
                            if ipv6_port is None:
                                
                                raise
                                
                            
                        
                        self._service_keys_to_connected_ports[ service_key ] = ( ipv4_port, ipv6_port )
                        
                        if HydrusNetworking.LocalPortInUse( port ):
                            
                            HydrusData.Print( 'Running "{}" on port {}.'.format( name, port ) )
                            
                        else:
                            
                            HydrusData.ShowText( 'Tried to bind port {} for "{}" but it failed.'.format( port, name ) )
                            
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Could not start "{}":'.format( name ) )
                        HydrusData.ShowException( e )
                        
                    
                
                HydrusData.Print( 'services started' )
                
            
            if len( self._service_keys_to_connected_ports ) > 0:
                
                HydrusData.Print( 'stopping services' + HC.UNICODE_ELLIPSIS )
                
                deferreds = []
                
                for ( existing_ipv4_port, existing_ipv6_port ) in self._service_keys_to_connected_ports.values():
                    
                    if existing_ipv4_port is not None:
                        
                        deferred = defer.maybeDeferred( existing_ipv4_port.stopListening )
                        
                        deferreds.append( deferred )
                        
                    
                    if existing_ipv6_port is not None:
                        
                        deferred = defer.maybeDeferred( existing_ipv6_port.stopListening )
                        
                        deferreds.append( deferred )
                        
                    
                
                self._service_keys_to_connected_ports = {}
                
                deferred = defer.DeferredList( deferreds )
                
                if len( services ) > 0:
                    
                    deferred.addCallback( StartServices )
                    
                
            elif len( services ) > 0:
                
                StartServices()
                
            
        
        if HG.twisted_is_broke:
            
            if True in ( service.GetPort() is not None for service in services ):
                
                HydrusData.ShowText( 'Twisted failed to import, so could not start the local booru/client api! Specific error has been printed to log. Please contact hydrus dev!' )
                
                HydrusData.Print( HG.twisted_is_broke_exception )
                
            
        else:
            
            threads.blockingCallFromThread( reactor, TWISTEDDoIt )
            
        
    
    def SetServices( self, services ):
        
        with HG.dirty_object_lock:
            
            previous_services = self.services_manager.GetServices()
            
            upnp_services = [ service for service in services if service.GetServiceType() in ( HC.CLIENT_API_SERVICE, ) ]
            
            self.CallToThreadLongRunning( self.services_upnp_manager.SetServices, upnp_services )
            
            self.WriteSynchronous( 'update_services', services )
            
            self.services_manager.RefreshServices()
            
        
        self.RestartClientServerServices()
        
    
    def ShutdownModel( self ):
        
        self.frame_splash_status.SetText( 'saving and exiting objects' )
        
        if self._is_booted:
            
            self.frame_splash_status.SetSubtext( 'file viewing stats flush' )
            
            self.file_viewing_stats_manager.Flush()
            
            self.frame_splash_status.SetSubtext( '' )
            
            self.SaveDirtyObjectsImportant()
            self.SaveDirtyObjectsInfrequent()
            
        
        HydrusController.HydrusController.ShutdownModel( self )
        
    
    def ShutdownView( self ):
        
        if not self._doing_fast_exit:
            
            self.frame_splash_status.SetText( 'waiting for managers to exit' )
            
        
        self._ShutdownManagers()
        
        if not self._doing_fast_exit:
            
            self.frame_splash_status.SetText( 'waiting for workers to exit' )
            
        
        self._ShutdownDaemons()
        
        self.frame_splash_status.SetSubtext( '' )
        
        if not self._doing_fast_exit:
            
            if HG.do_idle_shutdown_work:
                
                self.frame_splash_status.SetText( 'waiting for idle shutdown work' )
                
                try:
                    
                    self.DoIdleShutdownWork()
                    
                    self.frame_splash_status.SetSubtext( '' )
                    
                except Exception as e:
                    
                    self._ReportShutdownException()
                    
                
            
            self.frame_splash_status.SetSubtext( '' )
            
            try:
                
                self.frame_splash_status.SetText( 'waiting for services to exit' )
                
                self.SetRunningTwistedServices( [] )
                
            except Exception as e:
                
                pass # sometimes this throws a wobbler, screw it
                
            
        
        HydrusController.HydrusController.ShutdownView( self )
        
    
    def SleepCheck( self ) -> None:
        
        if not self.new_options.GetBoolean( 'do_sleep_check' ):
            
            self._just_woke_from_sleep = False
            
            return
            
        
        HydrusController.HydrusController.SleepCheck( self )
        
    
    def SynchroniseAccounts( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ):
            
            return
            
        
        services = self.services_manager.GetServices( HC.RESTRICTED_SERVICES, randomised = True )
        
        for service in services:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            service = typing.cast( ClientServices.ServiceRestricted, service )
            
            service.SyncAccount()
            
        
    
    def SynchroniseRepositories( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ):
            
            return
            
        
        if not self.new_options.GetBoolean( 'pause_repo_sync' ):
            
            services = self.services_manager.GetServices( HC.REPOSITORIES, randomised = True )
            
            for service in services:
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                if self.new_options.GetBoolean( 'pause_repo_sync' ):
                    
                    return
                    
                
                service = typing.cast( ClientServices.ServiceRepository, service )
                
                service.SyncRemote()
                
                service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_IDLE )
                
            
        
    
    def SystemBusy( self ):
        
        if HG.force_idle_mode:
            
            return False
            
        
        system_busy_cpu_percent = self.new_options.GetInteger( 'system_busy_cpu_percent' )
        system_busy_cpu_count = self.new_options.GetNoneableInteger( 'system_busy_cpu_count' )
        
        if system_busy_cpu_count is None:
            
            self._system_busy = False
            
        else:
            
            if HydrusTime.TimeHasPassedMS( self.GetTimestampMS( 'last_cpu_check' ) + 60000 ):
                
                if HydrusPSUtil.PSUTIL_OK:
                    
                    cpu_times = HydrusPSUtil.psutil.cpu_percent( percpu = True )
                    
                    if len( [ 1 for cpu_time in cpu_times if cpu_time > system_busy_cpu_percent ] ) >= system_busy_cpu_count:
                        
                        self._system_busy = True
                        
                    else:
                        
                        self._system_busy = False
                        
                    
                
                self.TouchTime( 'last_cpu_check' )
                
            
        
        return self._system_busy
        
    
    def THREADBootEverything( self ):
        
        qapp = QW.QApplication.instance()
        
        try:
            
            self.CheckAlreadyRunning()
            
        except HydrusExceptions.ShutdownException:
            
            self._DestroySplash()
            
            self.CallAfterQtSafe( qapp, QW.QApplication.exit )
            
            return
            
        
        try:
            
            self.RecordRunningStart()
            
            self.InitModel()
            
            self.InitView()
            
            self._is_booted = True
            
        except ( HydrusExceptions.DBCredentialsException, HydrusExceptions.ShutdownException ) as e:
            
            HydrusData.Print( e )
            
            self.CleanRunningFile()
            
            self.CallAfterQtSafe( qapp, QW.QApplication.exit )
            
        except HydrusExceptions.DBVersionException as e:
            
            self.BlockingSafeShowCriticalMessage( 'database version error', str( e ) )
            
            self.CallAfterQtSafe( qapp, QW.QApplication.exit, 1 )
            
        except HydrusExceptions.DBAccessException as e:
            
            trace = traceback.format_exc()
            
            HydrusData.DebugPrint( trace )
            
            text = 'A serious problem occurred while trying to start the program. Full details have been written to the log. The error is:'
            text += '\n' * 2
            text += str( e )
            
            self.BlockingSafeShowCriticalMessage( 'boot error', text )
            
            self.CallAfterQtSafe( qapp, QW.QApplication.exit, 1 )
            
        except Exception as e:
            
            text = 'A serious error occurred while trying to start the program. The error will be shown next in a window. More information may have been written to client.log.'
            
            HydrusData.DebugPrint( 'If the db crashed, another error may be written just above ^.' )
            HydrusData.DebugPrint( text )
            
            trace = traceback.format_exc()
            
            HydrusData.DebugPrint( trace )
            
            self.BlockingSafeShowCriticalMessage( 'boot error', text )
            
            if 'malformed' in trace:
                
                hell_message = 'Looking at it, it looks like your database may be malformed! This is a serious error. Please check "/install_dir/db/help my db is broke.txt" as soon as you can for the next steps. The specific error will now follow.'
                
                HydrusData.DebugPrint( hell_message )
                
                self.BlockingSafeShowCriticalMessage( 'boot error', hell_message )
                
            
            self.BlockingSafeShowCriticalMessage( 'boot error', trace )
            
            self.CallAfterQtSafe( qapp, QW.QApplication.exit, 1 )
            
        finally:
            
            self._DestroySplash()
            
        
    
    def ToClipboard( self, data_type, data ):
        
        # need this cause can't do it in a non-gui thread
        
        if data_type == 'paths':
            
            paths = []
            
            for path in data:
                
                paths.append( QC.QUrl.fromLocalFile( path ) )
                
            
            mime_data = QC.QMimeData()
            
            mime_data.setUrls( paths )
            
            QW.QApplication.clipboard().setMimeData( mime_data )
            
        elif data_type == 'text':
            
            text = data
            
            QW.QApplication.clipboard().setText( text )
            
        elif data_type == 'bmp':
            
            ( media, optional_target_resolution_tuple ) = data
            
            display_media = media.GetDisplayMedia()
            
            if display_media is None:
                
                return
                
            
            image_renderer = self.images_cache.GetImageRenderer( display_media.GetMediaResult() )
            
            def CopyToClipboard():
                
                if optional_target_resolution_tuple is None:
                    
                    target_resolution = None
                    
                else:
                    
                    target_resolution = QC.QSize( optional_target_resolution_tuple[0], optional_target_resolution_tuple[1] )
                    
                
                # this is faster than qpixmap, which converts to a qimage anyway
                qt_image = image_renderer.GetQtImage( target_resolution = target_resolution ).copy()
                
                QW.QApplication.clipboard().setImage( qt_image )
                
            
            def THREADWait():
                
                start_time = time.time()
                
                while not image_renderer.IsReady():
                    
                    if HydrusTime.TimeHasPassed( start_time + 15 ):
                        
                        HydrusData.ShowText( 'The image did not render in fifteen seconds, so the attempt to copy it to the clipboard was abandoned.' )
                        
                        return
                        
                    
                    time.sleep( 0.1 )
                    
                
                self.CallAfterQtSafe( self.gui, CopyToClipboard )
                
            
            self.CallToThreadLongRunning( THREADWait )
            
        elif data_type == 'thumbnail_bmp':
            
            media = data
            
            if media.GetMime() not in HC.MIMES_WITH_THUMBNAILS:
                
                return
                
            
            thumbnail = self.thumbnails_cache.GetThumbnail( media.GetDisplayMedia().GetMediaResult() )
            
            qt_image = thumbnail.GetQtImage().copy()
            
            QW.QApplication.clipboard().setImage( qt_image )
            
        
    
    def UnclosePageKeys( self, page_keys ):
        
        with self._page_key_lock:
            
            self._closed_page_keys.difference_update( page_keys )
            
        
    
    def WaitUntilViewFree( self ):
        
        self.WaitUntilModelFree()
        
        self.WaitUntilThumbnailsFree()
        
    
    def WaitUntilThumbnailsFree( self ):
        
        if self.thumbnails_cache is not None:
            
            self.thumbnails_cache.WaitUntilFree()
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        if action == 'content_updates':
            
            if 'undo' in self._managers:
                
                self._managers[ 'undo' ].AddCommand( 'content_updates', *args, **kwargs )
                
            
        
        return HydrusController.HydrusController.Write( self, action, *args, **kwargs )
        
    
