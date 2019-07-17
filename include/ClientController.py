import os
import wx

wx_first_num = int( wx.__version__[0] )

if wx_first_num < 4:
    
    wx_error = 'Unfortunately, hydrus now requires the new Phoenix (4.x) version of wx.'
    wx_error += os.linesep * 2
    wx_error += 'Please check the \'running from source\' page in the html help for more details.'
    
    raise Exception( wx_error )
    
from . import ClientAPI
from . import ClientCaches
from . import ClientData
from . import ClientDaemons
from . import ClientDefaults
from . import ClientFiles
from . import ClientGUIMenus
from . import ClientGUIShortcuts
from . import ClientNetworking
from . import ClientNetworkingBandwidth
from . import ClientNetworkingDomain
from . import ClientNetworkingLogin
from . import ClientNetworkingSessions
from . import ClientOptions
from . import ClientPaths
from . import ClientThreading
import hashlib
from . import HydrusConstants as HC
from . import HydrusController
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
from . import HydrusVideoHandling
from . import ClientConstants as CC
from . import ClientDB
from . import ClientGUI
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIScrolledPanelsManagement
from . import ClientGUITopLevelWindows
import gc
import psutil
import threading
import time
import traceback

if not HG.twisted_is_broke:
    
    from twisted.internet import reactor, defer
    
class Controller( HydrusController.HydrusController ):
    
    def __init__( self, db_dir ):
        
        self._last_shutdown_was_bad = False
        
        self._is_booted = False
        
        self._splash = None
        
        HydrusController.HydrusController.__init__( self, db_dir )
        
        self._name = 'client'
        
        HG.client_controller = self
        
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
        
        self._last_mouse_position = None
        self._menu_open = False
        self._previously_idle = False
        self._idle_started = None
        
        self.client_files_manager = None
        self.services_manager = None
        
    
    def _InitDB( self ):
        
        return ClientDB.DB( self, self.db_dir, 'client' )
        
    
    def _InitTempDir( self ):
        
        self.temp_dir = HydrusPaths.GetTempDir()
        
    
    def _DestroySplash( self ):
        
        def wx_code( splash ):
            
            if splash:
                
                splash.Hide()
                
                splash.DestroyLater()
                
            
        
        if self._splash is not None:
            
            splash = self._splash
            
            self._splash = None
            
            wx.CallAfter( wx_code, splash )
            
        
    
    def _GetUPnPServices( self ):
        
        return self.services_manager.GetServices( ( HC.LOCAL_BOORU, HC.CLIENT_API_SERVICE ) )
        
    
    def _ReportShutdownDaemonsStatus( self ):
        
        names = { daemon.name for daemon in self._daemons if daemon.is_alive() }
        
        names = list( names )
        
        names.sort()
        
        self.pub( 'splash_set_status_subtext', ', '.join( names ) )
        
    
    def AcquirePageKey( self ):
        
        with self._page_key_lock:
            
            page_key = HydrusData.GenerateKey()
            
            self._alive_page_keys.add( page_key )
            
            return page_key
            
        
    
    def CallBlockingToWX( self, win, func, *args, **kwargs ):
        
        def wx_code( win, job_key ):
            
            try:
                
                if win is not None and not win:
                    
                    raise HydrusExceptions.WXDeadWindowException( 'Parent Window was destroyed before wx command was called!' )
                    
                
                result = func( *args, **kwargs )
                
                job_key.SetVariable( 'result', result )
                
            except ( HydrusExceptions.WXDeadWindowException, HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ShutdownException ) as e:
                
                job_key.SetVariable( 'error', e )
                
            except Exception as e:
                
                job_key.SetVariable( 'error', e )
                
                HydrusData.Print( 'CallBlockingToWX just caught this error:' )
                HydrusData.DebugPrint( traceback.format_exc() )
                
            finally:
                
                job_key.Finish()
                
            
        
        job_key = ClientThreading.JobKey( cancel_on_shutdown = False )
        
        job_key.Begin()
        
        wx.CallAfter( wx_code, win, job_key )
        
        while not job_key.IsDone():
            
            if self._model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                
            
            time.sleep( 0.05 )
            
        
        if job_key.HasVariable( 'result' ):
            
            # result can be None, for wx_code that has no return variable
            
            result = job_key.GetIfHasVariable( 'result' )
            
            return result
            
        
        error = job_key.GetIfHasVariable( 'error' )
        
        if error is not None:
            
            raise error
            
        
        raise HydrusExceptions.ShutdownException()
        
    
    def CallLaterWXSafe( self, window, initial_delay, func, *args, **kwargs ):
        
        job_scheduler = self._GetAppropriateJobScheduler( initial_delay )
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = ClientThreading.WXAwareJob( self, job_scheduler, window, initial_delay, call )
        
        if job_scheduler is not None:
            
            job_scheduler.AddJob( job )
            
        
        return job
        
    
    def CallRepeatingWXSafe( self, window, initial_delay, period, func, *args, **kwargs ):
        
        job_scheduler = self._GetAppropriateJobScheduler( period )
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = ClientThreading.WXAwareRepeatingJob( self, job_scheduler, window, initial_delay, period, call )
        
        if job_scheduler is not None:
            
            job_scheduler.AddJob( job )
            
        
        return job
        
    
    def CheckAlreadyRunning( self ):
        
        while HydrusData.IsAlreadyRunning( self.db_dir, 'client' ):
            
            self.pub( 'splash_set_status_text', 'client already running' )
            
            def wx_code():
                
                message = 'It looks like another instance of this client is already running, so this instance cannot start.'
                message += os.linesep * 2
                message += 'If the old instance is closing and does not quit for a _very_ long time, it is usually safe to force-close it from task manager.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self._splash, message, title = 'The client is already running.', yes_label = 'wait a bit, then try again', no_label = 'forget it' )
                
                if result != wx.ID_YES:
                    
                    HG.shutting_down_due_to_already_running = True
                    
                    raise HydrusExceptions.ShutdownException()
                    
                
            
            self.CallBlockingToWX( self._splash, wx_code )
            
            for i in range( 10, 0, -1 ):
                
                if not HydrusData.IsAlreadyRunning( self.db_dir, 'client' ):
                    
                    break
                    
                
                self.pub( 'splash_set_status_text', 'waiting ' + str( i ) + ' seconds' )
                
                time.sleep( 1 )
                
            
        
    
    def CheckMouseIdle( self ):
        
        mouse_position = wx.GetMousePosition()
        
        if self._last_mouse_position is None:
            
            self._last_mouse_position = mouse_position
            
        elif mouse_position != self._last_mouse_position:
            
            idle_before_position_update = self.CurrentlyIdle()
            
            self._timestamps[ 'last_mouse_action' ] = HydrusData.GetNow()
            
            self._last_mouse_position = mouse_position
            
            idle_after_position_update = self.CurrentlyIdle()
            
            move_knocked_us_out_of_idle = ( not idle_before_position_update ) and idle_after_position_update
            
            if move_knocked_us_out_of_idle:
                
                self.pub( 'set_status_bar_dirty' )
                
            
        
    
    def ClosePageKeys( self, page_keys ):
        
        with self._page_key_lock:
            
            self._closed_page_keys.update( page_keys )
            
        
    
    def CreateSplash( self ):
        
        try:
            
            self._splash = ClientGUI.FrameSplash( self )
            
        except:
            
            HydrusData.Print( 'There was an error trying to start the splash screen!' )
            
            HydrusData.Print( traceback.format_exc() )
            
            raise
            
        
    
    def CurrentlyIdle( self ):
        
        if HG.force_idle_mode:
            
            self._idle_started = 0
            
            return True
            
        
        if not HydrusData.TimeHasPassed( self._timestamps[ 'boot' ] + 120 ):
            
            return False
            
        
        idle_normal = self.options[ 'idle_normal' ]
        idle_period = self.options[ 'idle_period' ]
        idle_mouse_period = self.options[ 'idle_mouse_period' ]
        
        if idle_normal:
            
            currently_idle = True
            
            if idle_period is not None:
                
                if not HydrusData.TimeHasPassed( self._timestamps[ 'last_user_action' ] + idle_period ):
                    
                    currently_idle = False
                    
                
            
            if idle_mouse_period is not None:
                
                if not HydrusData.TimeHasPassed( self._timestamps[ 'last_mouse_action' ] + idle_mouse_period ):
                    
                    currently_idle = False
                    
                
            
        else:
            
            currently_idle = False
            
        
        turning_idle = currently_idle and not self._previously_idle
        
        self._previously_idle = currently_idle
        
        if turning_idle:
            
            self._idle_started = HydrusData.GetNow()
            
            self.pub( 'wake_daemons' )
            
        
        if not currently_idle:
            
            self._idle_started = None
            
        
        return currently_idle
        
    
    def CurrentlyVeryIdle( self ):
        
        if self._idle_started is not None and HydrusData.TimeHasPassed( self._idle_started + 3600 ):
            
            return True
            
        
        return False
        
    
    def DoIdleShutdownWork( self ):
        
        stop_time = HydrusData.GetNow() + ( self.options[ 'idle_shutdown_max_minutes' ] * 60 )
        
        self.MaintainDB( maintenance_mode = HC.MAINTENANCE_SHUTDOWN, stop_time = stop_time )
        
        if not self.options[ 'pause_repo_sync' ]:
            
            services = self.services_manager.GetServices( HC.REPOSITORIES )
            
            for service in services:
                
                if HydrusData.TimeHasPassed( stop_time ):
                    
                    return
                    
                
                service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_SHUTDOWN, stop_time = stop_time )
                
            
        
        if self.new_options.GetBoolean( 'file_maintenance_on_shutdown' ):
            
            self.files_maintenance_manager.DoMaintenance( maintenance_mode = HC.MAINTENANCE_SHUTDOWN, stop_time = stop_time )
            
        
        self.Write( 'last_shutdown_work_time', HydrusData.GetNow() )
        
    
    def Exit( self ):
        
        if HG.emergency_exit:
            
            self.ShutdownView()
            self.ShutdownModel()
            
            if not HG.shutting_down_due_to_already_running:
                
                HydrusData.CleanRunningFile( self.db_dir, 'client' )
                
            
        else:
            
            try:
                
                last_shutdown_work_time = self.Read( 'last_shutdown_work_time' )
                
                idle_shutdown_action = self.options[ 'idle_shutdown' ]
                
                auto_shutdown_work_ok_by_user = idle_shutdown_action in ( CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST )
                
                shutdown_work_period = self.new_options.GetInteger( 'shutdown_work_period' )
                
                auto_shutdown_work_due = HydrusData.TimeHasPassed( last_shutdown_work_time + shutdown_work_period )
                
                manual_shutdown_work_not_already_set = not HG.do_idle_shutdown_work
                
                we_can_turn_on_auto_shutdown_work = auto_shutdown_work_ok_by_user and auto_shutdown_work_due and manual_shutdown_work_not_already_set
                
                if we_can_turn_on_auto_shutdown_work:
                    
                    idle_shutdown_max_minutes = self.options[ 'idle_shutdown_max_minutes' ]
                    
                    time_to_stop = HydrusData.GetNow() + ( idle_shutdown_max_minutes * 60 )
                    
                    work_to_do = self.GetIdleShutdownWorkDue( time_to_stop )
                    
                    if len( work_to_do ) > 0:
                        
                        if idle_shutdown_action == CC.IDLE_ON_SHUTDOWN_ASK_FIRST:
                            
                            text = 'Is now a good time for the client to do up to ' + HydrusData.ToHumanInt( idle_shutdown_max_minutes ) + ' minutes\' maintenance work? (Will auto-no in 15 seconds)'
                            text += os.linesep * 2
                            text += 'The outstanding jobs appear to be:'
                            text += os.linesep * 2
                            text += os.linesep.join( work_to_do )
                            
                            with ClientGUIDialogs.DialogYesNo( self._splash, text, title = 'Maintenance is due' ) as dlg_yn:
                                
                                job = self.CallLaterWXSafe( dlg_yn, 15, dlg_yn.EndModal, wx.ID_NO )
                                
                                try:
                                    
                                    if dlg_yn.ShowModal() == wx.ID_YES:
                                        
                                        HG.do_idle_shutdown_work = True
                                        
                                    else:
                                        
                                        # if they said no, don't keep asking
                                        self.Write( 'last_shutdown_work_time', HydrusData.GetNow() )
                                        
                                    
                                finally:
                                    
                                    job.Cancel()
                                    
                                
                            
                        else:
                            
                            HG.do_idle_shutdown_work = True
                            
                        
                    
                
                if HG.do_idle_shutdown_work:
                    
                    self._splash.MakeCancelShutdownButton()
                    
                
                self.CallToThreadLongRunning( self.THREADExitEverything )
                
            except:
                
                self._DestroySplash()
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
                HG.emergency_exit = True
                
                self.Exit()
                
            
        
    
    def GetApp( self ):
        
        return self._app
        
    
    def GetClipboardText( self ):
        
        if wx.TheClipboard.Open():
            
            try:
                
                if not wx.TheClipboard.IsSupported( wx.DataFormat( wx.DF_TEXT ) ):
                    
                    raise HydrusExceptions.DataMissing( 'No text on the clipboard!' )
                    
                
                data = wx.TextDataObject()
                
                success = wx.TheClipboard.GetData( data )
                
            finally:
                
                wx.TheClipboard.Close()
                
            
            if not success:
                
                raise HydrusExceptions.DataMissing( 'No text on the clipboard!' )
                
            
            text = data.GetText()
            
            return text
            
        else:
            
            raise HydrusExceptions.DataMissing( 'I could not get permission to access the clipboard.' )
            
        
    
    def GetCommandFromShortcut( self, shortcut_names, shortcut ):
        
        return self.shortcuts_manager.GetCommand( shortcut_names, shortcut )
        
    
    def GetGUI( self ):
        
        return self.gui
        
    
    def GetIdleShutdownWorkDue( self, time_to_stop ):
        
        work_to_do = []
        
        work_to_do.extend( self.Read( 'maintenance_due', time_to_stop ) )
        
        services = self.services_manager.GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            if service.CanDoIdleShutdownWork():
                
                work_to_do.append( service.GetName() + ' repository processing' )
                
            
        
        if self.new_options.GetBoolean( 'file_maintenance_on_shutdown' ):
            
            work_to_do.extend( self.files_maintenance_manager.GetIdleShutdownWorkDue() )
            
        
        return work_to_do
        
    
    def GetNewOptions( self ):
        
        return self.new_options
        
    
    def InitClientFilesManager( self ):
        
        def wx_code( missing_locations ):
            
            with ClientGUITopLevelWindows.DialogManage( None, 'repair file system' ) as dlg:
                
                panel = ClientGUIScrolledPanelsManagement.RepairFileSystemPanel( dlg, missing_locations )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    self.client_files_manager = ClientFiles.ClientFilesManager( self )
                    
                    missing_locations = self.client_files_manager.GetMissing()
                    
                else:
                    
                    raise HydrusExceptions.ShutdownException( 'File system failed, user chose to quit.' )
                    
                
            
            return missing_locations
            
        
        self.client_files_manager = ClientFiles.ClientFilesManager( self )
        
        self.files_maintenance_manager = ClientFiles.FilesMaintenanceManager( self )
        
        missing_locations = self.client_files_manager.GetMissing()
        
        while len( missing_locations ) > 0:
            
            missing_locations = self.CallBlockingToWX( self._splash, wx_code, missing_locations )
            
        
    
    def InitModel( self ):
        
        self.pub( 'splash_set_title_text', 'booting db\u2026' )
        
        HydrusController.HydrusController.InitModel( self )
        
        self.pub( 'splash_set_status_text', 'initialising managers' )
        
        self.pub( 'splash_set_status_subtext', 'services' )
        
        self.services_manager = ClientCaches.ServicesManager( self )
        
        self.pub( 'splash_set_status_subtext', 'options' )
        
        self.options = self.Read( 'options' )
        self.new_options = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
        
        HC.options = self.options
        
        if self.new_options.GetBoolean( 'use_system_ffmpeg' ):
            
            if HydrusVideoHandling.FFMPEG_PATH.startswith( HC.BIN_DIR ):
                
                HydrusVideoHandling.FFMPEG_PATH = os.path.basename( HydrusVideoHandling.FFMPEG_PATH )
                
            
        
        self.pub( 'splash_set_status_subtext', 'client files' )
        
        self.InitClientFilesManager()
        
        #
        
        self.pub( 'splash_set_status_subtext', 'network' )
        
        self.parsing_cache = ClientCaches.ParsingCache()
        
        client_api_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_API_MANAGER )
        
        if client_api_manager is None:
            
            client_api_manager = ClientAPI.APIManager()
            
            client_api_manager._dirty = True
            
            wx.SafeShowMessage( 'Problem loading object', 'Your client api manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        self.client_api_manager = client_api_manager
        
        bandwidth_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER )
        
        if bandwidth_manager is None:
            
            bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
            
            ClientDefaults.SetDefaultBandwidthManagerRules( bandwidth_manager )
            
            bandwidth_manager._dirty = True
            
            wx.SafeShowMessage( 'Problem loading object', 'Your bandwidth manager was missing on boot! I have recreated a new empty one with default rules. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        session_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER )
        
        if session_manager is None:
            
            session_manager = ClientNetworkingSessions.NetworkSessionManager()
            
            session_manager._dirty = True
            
            wx.SafeShowMessage( 'Problem loading object', 'Your session manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        domain_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER )
        
        if domain_manager is None:
            
            domain_manager = ClientNetworkingDomain.NetworkDomainManager()
            
            ClientDefaults.SetDefaultDomainManagerData( domain_manager )
            
            domain_manager._dirty = True
            
            wx.SafeShowMessage( 'Problem loading object', 'Your domain manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        domain_manager.Initialise()
        
        login_manager = self.Read( 'serialisable', HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER )
        
        if login_manager is None:
            
            login_manager = ClientNetworkingLogin.NetworkLoginManager()
            
            ClientDefaults.SetDefaultLoginManagerScripts( login_manager )
            
            login_manager._dirty = True
            
            wx.SafeShowMessage( 'Problem loading object', 'Your login manager was missing on boot! I have recreated a new empty one. Please check that your hard drive and client are ok and let the hydrus dev know the details if there is a mystery.' )
            
        
        login_manager.Initialise()
        
        self.network_engine = ClientNetworking.NetworkEngine( self, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.CallToThreadLongRunning( self.network_engine.MainLoop )
        
        #
        
        self.shortcuts_manager = ClientGUIShortcuts.ShortcutsManager( self )
        
        self.local_booru_manager = ClientCaches.LocalBooruCache( self )
        
        self.file_viewing_stats_manager = ClientCaches.FileViewingStatsManager( self )
        
        self.pub( 'splash_set_status_subtext', 'tag censorship' )
        
        self.tag_censorship_manager = ClientCaches.TagCensorshipManager( self )
        
        self.pub( 'splash_set_status_subtext', 'tag siblings' )
        
        self.tag_siblings_manager = ClientCaches.TagSiblingsManager( self )
        
        self.pub( 'splash_set_status_subtext', 'tag parents' )
        
        self.tag_parents_manager = ClientCaches.TagParentsManager( self )
        self._managers[ 'undo' ] = ClientCaches.UndoManager( self )
        
        def wx_code():
            
            self._caches[ 'images' ] = ClientCaches.RenderedImageCache( self )
            self._caches[ 'thumbnail' ] = ClientCaches.ThumbnailCache( self )
            self.bitmap_manager = ClientCaches.BitmapManager( self )
            
            CC.GlobalBMPs.STATICInitialise()
            
        
        self.pub( 'splash_set_status_subtext', 'image caches' )
        
        self.CallBlockingToWX( self._splash, wx_code )
        
        self.sub( self, 'ToClipboard', 'clipboard' )
        self.sub( self, 'RestartClientServerService', 'restart_client_server_service' )
        
    
    def InitView( self ):
        
        if self.options[ 'password' ] is not None:
            
            self.pub( 'splash_set_status_text', 'waiting for password' )
            
            def wx_code_password():
                
                while True:
                    
                    with wx.PasswordEntryDialog( self._splash, 'Enter your password', 'Enter password' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            password_bytes = bytes( dlg.GetValue(), 'utf-8' )
                            
                            if hashlib.sha256( password_bytes ).digest() == self.options[ 'password' ]:
                                
                                break
                                
                            
                        else:
                            
                            raise HydrusExceptions.InsufficientCredentialsException( 'Bad password check' )
                            
                        
                    
                
            
            self.CallBlockingToWX( self._splash, wx_code_password )
            
        
        self.pub( 'splash_set_title_text', 'booting gui\u2026' )
        
        def wx_code_gui():
            
            self.gui = ClientGUI.FrameGUI( self )
            
            self.ResetIdleTimer()
            
        
        self.CallBlockingToWX( self._splash, wx_code_gui )
        
        # ShowText will now popup as a message, as popup message manager has overwritten the hooks
        
        HydrusController.HydrusController.InitView( self )
        
        self._listening_services = {}
        
        self.RestartClientServerService( CC.LOCAL_BOORU_SERVICE_KEY )
        self.RestartClientServerService( CC.CLIENT_API_SERVICE_KEY )
        
        if not HG.no_daemons:
            
            self._daemons.append( HydrusThreading.DAEMONForegroundWorker( self, 'DownloadFiles', ClientDaemons.DAEMONDownloadFiles, ( 'notify_new_downloads', 'notify_new_permissions' ) ) )
            self._daemons.append( HydrusThreading.DAEMONForegroundWorker( self, 'SynchroniseSubscriptions', ClientDaemons.DAEMONSynchroniseSubscriptions, ( 'notify_restart_subs_sync_daemon', 'notify_new_subscriptions' ), period = 4 * 3600, init_wait = 60, pre_call_wait = 3 ) )
            self._daemons.append( HydrusThreading.DAEMONForegroundWorker( self, 'MaintainTrash', ClientDaemons.DAEMONMaintainTrash, init_wait = 120 ) )
            self._daemons.append( HydrusThreading.DAEMONForegroundWorker( self, 'SynchroniseRepositories', ClientDaemons.DAEMONSynchroniseRepositories, ( 'notify_restart_repo_sync_daemon', 'notify_new_permissions', 'wake_idle_workers' ), period = 4 * 3600, pre_call_wait = 1 ) )
            
        
        job = self.CallRepeating( 5.0, 180.0, ClientDaemons.DAEMONCheckImportFolders )
        job.WakeOnPubSub( 'notify_restart_import_folders_daemon' )
        job.WakeOnPubSub( 'notify_new_import_folders' )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'import_folders' ] = job
        
        job = self.CallRepeating( 60.0, 300.0, self.files_maintenance_manager.DoMaintenance, maintenance_mode = HC.MAINTENANCE_IDLE )
        job.ShouldDelayOnWakeup( True )
        job.WakeOnPubSub( 'wake_idle_workers' )
        self._daemon_jobs[ 'maintain_files' ] = job
        
        job = self.CallRepeating( 5.0, 180.0, ClientDaemons.DAEMONCheckExportFolders )
        job.WakeOnPubSub( 'notify_restart_export_folders_daemon' )
        job.WakeOnPubSub( 'notify_new_export_folders' )
        job.ShouldDelayOnWakeup( True )
        self._daemon_jobs[ 'export_folders' ] = job
        
        job = self.CallRepeating( 0.0, 30.0, self.SaveDirtyObjects )
        job.WakeOnPubSub( 'important_dirt_to_clean' )
        self._daemon_jobs[ 'save_dirty_objects' ] = job
        
        job = self.CallRepeating( 5.0, 3600.0, self.SynchroniseAccounts )
        job.ShouldDelayOnWakeup( True )
        job.WakeOnPubSub( 'notify_unknown_accounts' )
        self._daemon_jobs[ 'synchronise_accounts' ] = job
        
        job = self.CallRepeatingWXSafe( self, 10.0, 10.0, self.CheckMouseIdle )
        self._daemon_jobs[ 'check_mouse_idle' ] = job
        
        if self.db.IsFirstStart():
            
            message = 'Hi, this looks like the first time you have started the hydrus client.'
            message += os.linesep * 2
            message += 'Don\'t forget to check out the help if you haven\'t already--it has an extensive \'getting started\' section.'
            message += os.linesep * 2
            message += 'To dismiss popup messages like this, right-click them.'
            
            HydrusData.ShowText( message )
            
        
        if self.db.IsDBUpdated():
            
            HydrusData.ShowText( 'The client has updated to version ' + str( HC.SOFTWARE_VERSION ) + '!' )
            
        
        for message in self.db.GetInitialMessages():
            
            HydrusData.ShowText( message )
            
        
    
    def IsBooted( self ):
        
        return self._is_booted
        
    
    def LastShutdownWasBad( self ):
        
        return self._last_shutdown_was_bad
        
    
    def MaintainDB( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        if maintenance_mode == HC.MAINTENANCE_IDLE and not self.GoodTimeToStartBackgroundWork():
            
            return
            
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        if self.new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ):
            
            tree_stop_time = stop_time
            
            if tree_stop_time is None:
                
                tree_stop_time = HydrusData.GetNow() + 30
                
            
            self.WriteSynchronous( 'maintain_similar_files_tree', stop_time = tree_stop_time )
            
            if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
                
                return
                
            
            search_distance = self.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            search_stop_time = stop_time
            
            if search_stop_time is None:
                
                search_stop_time = HydrusData.GetNow() + 60
                
            
            self.WriteSynchronous( 'maintain_similar_files_search_for_potential_duplicates', search_distance, stop_time = search_stop_time, abandon_if_other_work_to_do = True )
            
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        self.WriteSynchronous( 'vacuum', maintenance_mode = maintenance_mode, stop_time = stop_time )
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        self.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
        
        if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        if HydrusData.TimeHasPassed( self._timestamps[ 'last_service_info_cache_fatten' ] + ( 60 * 20 ) ):
            
            self.pub( 'splash_set_status_text', 'fattening service info' )
            
            services = self.services_manager.GetServices()
            
            for service in services:
                
                self.pub( 'splash_set_status_subtext', service.GetName() )
                
                try: self.Read( 'service_info', service.GetServiceKey() )
                except: pass # sometimes this breaks when a service has just been removed and the client is closing, so ignore the error
                
                if self.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
                    
                    return
                    
                
            
            self._timestamps[ 'last_service_info_cache_fatten' ] = HydrusData.GetNow()
            
        
    
    def MaintainMemoryFast( self ):
        
        HydrusController.HydrusController.MaintainMemoryFast( self )
        
        self.parsing_cache.CleanCache()
        
    
    def MaintainMemorySlow( self ):
        
        HydrusController.HydrusController.MaintainMemorySlow( self )
        
        if HydrusData.TimeHasPassed( self._timestamps[ 'last_page_change' ] + 30 * 60 ):
            
            self.pub( 'delete_old_closed_pages' )
            
            self._timestamps[ 'last_page_change' ] = HydrusData.GetNow()
            
        
        disk_cache_maintenance_mb = self.new_options.GetNoneableInteger( 'disk_cache_maintenance_mb' )
        
        if disk_cache_maintenance_mb is not None and not self._view_shutdown:
            
            cache_period = 3600
            disk_cache_stop_time = HydrusData.GetNow() + 2
            
            if HydrusData.TimeHasPassed( self._timestamps[ 'last_disk_cache_population' ] + cache_period ):
                
                self.Read( 'load_into_disk_cache', stop_time = disk_cache_stop_time, caller_limit = disk_cache_maintenance_mb * 1024 * 1024 )
                
                self._timestamps[ 'last_disk_cache_population' ] = HydrusData.GetNow()
                
            
        
    
    def MenubarMenuIsOpen( self ):
        
        self._menu_open = True
        
    
    def MenubarMenuIsClosed( self ):
        
        self._menu_open = False
        
    
    def MenuIsOpen( self ):
        
        return self._menu_open
        
    
    def PageAlive( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key in self._alive_page_keys
            
        
    
    def PageClosedButNotDestroyed( self, page_key ):
        
        with self._page_key_lock:
            
            return page_key in self._closed_page_keys
            
        
    
    def PopupMenu( self, window, menu ):
        
        if menu.GetMenuItemCount() > 0:
            
            self._menu_open = True
            
            window.PopupMenu( menu )
            
            self._menu_open = False
            
        
        ClientGUIMenus.DestroyMenu( window, menu )
        
    
    def PrepStringForDisplay( self, text ):
        
        return text.lower()
        
    
    def ProcessPubSub( self ):
        
        self.CallBlockingToWX( None, self._pubsub.Process )
        
    
    def RefreshServices( self ):
        
        self.services_manager.RefreshServices()
        
    
    def ReleasePageKey( self, page_key ):
        
        with self._page_key_lock:
            
            self._alive_page_keys.discard( page_key )
            self._closed_page_keys.discard( page_key )
            
        
    
    def ResetPageChangeTimer( self ):
        
        self._timestamps[ 'last_page_change' ] = HydrusData.GetNow()
        
    
    def RestartClientServerService( self, service_key ):
        
        service = self.services_manager.GetService( service_key )
        service_type = service.GetServiceType()
        
        name = service.GetName()
        
        port = service.GetPort()
        allow_non_local_connections = service.AllowsNonLocalConnections()
        
        def TWISTEDRestartServer():
            
            def StartServer( *args, **kwargs ):
                
                try:
                    
                    time.sleep( 1 )
                    
                    if HydrusNetworking.LocalPortInUse( port ):
                    
                        text = 'The client\'s {} could not start because something was already bound to port {}.'.format( name, port )
                        text += os.linesep * 2
                        text += 'This usually means another hydrus client is already running and occupying that port. It could be a previous instantiation of this client that has yet to completely shut itself down.'
                        text += os.linesep * 2
                        text += 'You can change the port this service tries to host on under services->manage services.'
                        
                        HydrusData.ShowText( text )
                        
                        return
                        
                    
                    from . import ClientLocalServer
                    
                    if service_type == HC.LOCAL_BOORU:
                        
                        twisted_server = ClientLocalServer.HydrusServiceBooru( service, allow_non_local_connections = allow_non_local_connections )
                        
                    elif service_type == HC.CLIENT_API_SERVICE:
                        
                        twisted_server = ClientLocalServer.HydrusServiceClientAPI( service, allow_non_local_connections = allow_non_local_connections )
                        
                    
                    listening_connection = reactor.listenTCP( port, twisted_server )
                    
                    self._listening_services[ service_key ] = listening_connection
                    
                    if not HydrusNetworking.LocalPortInUse( port ):
                        
                        text = 'Tried to bind port ' + str( port ) + ' for the local booru, but it appeared to fail. It could be a firewall or permissions issue, or perhaps another program was quietly already using it.'
                        
                        HydrusData.ShowText( text )
                        
                    
                except Exception as e:
                    
                    wx.CallAfter( HydrusData.ShowException, e )
                    
                
            
            if service_key in self._listening_services:
                
                listening_connection = self._listening_services[ service_key ]
                
                del self._listening_services[ service_key ]
                
                deferred = defer.maybeDeferred( listening_connection.stopListening )
                
                if port is not None:
                    
                    deferred.addCallback( StartServer )
                    
                
            else:
                
                if port is not None:
                    
                    StartServer()
                    
                
            
        
        if HG.twisted_is_broke:
            
            HydrusData.ShowText( 'Twisted failed to import, so could not start the {}! Please contact hydrus dev!'.format( name ) )
            
        else:
            
            reactor.callFromThread( TWISTEDRestartServer )
            
        
    
    def RestoreDatabase( self ):
        
        restore_intro = ''
        
        with wx.DirDialog( self.gui, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                text = 'Are you sure you want to restore a backup from "' + path + '"?'
                text += os.linesep * 2
                text += 'Everything in your current database will be deleted!'
                text += os.linesep * 2
                text += 'The gui will shut down, and then it will take a while to complete the restore. Once it is done, the client will restart.'
                
                with ClientGUIDialogs.DialogYesNo( self.gui, text ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        def THREADRestart():
                            
                            while not self.db.LoopIsFinished():
                                
                                time.sleep( 0.1 )
                                
                            
                            self.db.RestoreBackup( path )
                            
                            while not HG.shutdown_complete:
                                
                                time.sleep( 0.1 )
                                
                            
                            HydrusData.RestartProcess()
                            
                        
                        self.CallToThreadLongRunning( THREADRestart )
                        
                        wx.CallAfter( self.gui.Exit )
                        
                    
                
            
        
    
    def Run( self ):
        
        self._app = wx.App()
        
        self._app.locale = wx.Locale( wx.LANGUAGE_DEFAULT ) # Very important to init this here and keep it non garbage collected
        
        # do not import locale here and try anything clever--assume that bad locale formatting is due to OS-level mess-up, not mine
        # wx locale is supposed to set it all up nice, so if someone's doesn't, explore that and find the external solution
        
        HydrusData.Print( 'booting controller\u2026' )
        
        self.frame_icon = wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus_32_non-transparent.png' ), wx.BITMAP_TYPE_PNG )
        
        self.CreateSplash()
        
        self.CallToThreadLongRunning( self.THREADBootEverything )
        
        self._app.MainLoop()
        
        HydrusData.DebugPrint( 'shutting down controller\u2026' )
        
    
    def SaveDirtyObjects( self ):
        
        with HG.dirty_object_lock:
            
            dirty_services = [ service for service in self.services_manager.GetServices() if service.IsDirty() ]
            
            if len( dirty_services ) > 0:
                
                self.WriteSynchronous( 'dirty_services', dirty_services )
                
            
            if self.client_api_manager.IsDirty():
                
                self.WriteSynchronous( 'serialisable', self.client_api_manager )
                
                self.client_api_manager.SetClean()
                
            
            if self.network_engine.bandwidth_manager.IsDirty():
                
                self.WriteSynchronous( 'serialisable', self.network_engine.bandwidth_manager )
                
                self.network_engine.bandwidth_manager.SetClean()
                
            
            if self.network_engine.domain_manager.IsDirty():
                
                self.WriteSynchronous( 'serialisable', self.network_engine.domain_manager )
                
                self.network_engine.domain_manager.SetClean()
                
            
            if self.network_engine.login_manager.IsDirty():
                
                self.WriteSynchronous( 'serialisable', self.network_engine.login_manager )
                
                self.network_engine.login_manager.SetClean()
                
            
            if self.network_engine.session_manager.IsDirty():
                
                self.WriteSynchronous( 'serialisable', self.network_engine.session_manager )
                
                self.network_engine.session_manager.SetClean()
                
            
        
    
    def SetServices( self, services ):
        
        with HG.dirty_object_lock:
            
            upnp_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_BOORU, HC.CLIENT_API_SERVICE ) ]
            
            self.CallToThread( self.services_upnp_manager.SetServices, upnp_services )
            
            self.WriteSynchronous( 'update_services', services )
            
            self.services_manager.RefreshServices()
            
        
    
    def ShutdownModel( self ):
        
        if not HG.emergency_exit:
            
            self.file_viewing_stats_manager.Flush()
            
            self.SaveDirtyObjects()
            
        
        HydrusController.HydrusController.ShutdownModel( self )
        
    
    def ShutdownView( self ):
        
        if not HG.emergency_exit:
            
            self.pub( 'splash_set_status_text', 'waiting for daemons to exit' )
            
            self._ShutdownDaemons()
            
            if HG.do_idle_shutdown_work:
                
                try:
                    
                    self.DoIdleShutdownWork()
                    
                except:
                    
                    ClientData.ReportShutdownException()
                    
                
            
        
        HydrusController.HydrusController.ShutdownView( self )
        
    
    def SynchroniseAccounts( self ):
        
        services = self.services_manager.GetServices( HC.RESTRICTED_SERVICES )
        
        for service in services:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            service.SyncAccount()
            
        
    
    def SystemBusy( self ):
        
        if HG.force_idle_mode:
            
            return False
            
        
        max_cpu = self.options[ 'idle_cpu_max' ]
        
        if max_cpu is None:
            
            self._system_busy = False
            
        else:
            
            if HydrusData.TimeHasPassed( self._timestamps[ 'last_cpu_check' ] + 60 ):
                
                cpu_times = psutil.cpu_percent( percpu = True )
                
                if True in ( cpu_time > max_cpu for cpu_time in cpu_times ):
                    
                    self._system_busy = True
                    
                else:
                    
                    self._system_busy = False
                    
                
                self._timestamps[ 'last_cpu_check' ] = HydrusData.GetNow()
                
            
        
        return self._system_busy
        
    
    def THREADBootEverything( self ):
        
        try:
            
            self.CheckAlreadyRunning()
            
            self._last_shutdown_was_bad = HydrusData.LastShutdownWasBad( self.db_dir, 'client' )
            
            HydrusData.RecordRunningStart( self.db_dir, 'client' )
            
            self.InitModel()
            
            self.InitView()
            
            self._is_booted = True
            
        except ( HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ShutdownException ) as e:
            
            HydrusData.Print( e )
            
            HG.emergency_exit = True
            
            self.Exit()
            
        except Exception as e:
            
            text = 'A serious error occurred while trying to start the program. The error will be shown next in a window. More information may have been written to client.log.'
            
            HydrusData.DebugPrint( 'If the db crashed, another error may be written just above ^.' )
            HydrusData.DebugPrint( text )
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
            wx.SafeShowMessage( 'boot error', text )
            wx.SafeShowMessage( 'boot error', traceback.format_exc() )
            
            HG.emergency_exit = True
            
            self.Exit()
            
        finally:
            
            self._DestroySplash()
            
        
    
    def THREADExitEverything( self ):
        
        try:
            
            gc.collect()
            
            self.pub( 'splash_set_title_text', 'shutting down gui\u2026' )
            
            self.ShutdownView()
            
            self.pub( 'splash_set_title_text', 'shutting down db\u2026' )
            
            self.ShutdownModel()
            
            self.pub( 'splash_set_title_text', 'cleaning up\u2026' )
            
            if not HG.shutting_down_due_to_already_running:
                
                HydrusData.CleanRunningFile( self.db_dir, 'client' )
                
            
        except ( HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ShutdownException ):
            
            pass
            
        except:
            
            ClientData.ReportShutdownException()
            
        finally:
            
            self._DestroySplash()
            
        
    
    def ToClipboard( self, data_type, data ):
        
        # need this cause can't do it in a non-gui thread
        
        if data_type == 'paths':
            
            paths = data
            
            if wx.TheClipboard.Open():
                
                try:
                    
                    data = wx.DataObjectComposite()
                    
                    file_data = wx.FileDataObject()
                    
                    for path in paths: file_data.AddFile( path )
                    
                    text_data = wx.TextDataObject( os.linesep.join( paths ) )
                    
                    data.Add( file_data, True )
                    data.Add( text_data, False )
                    
                    wx.TheClipboard.SetData( data )
                    
                finally:
                    
                    wx.TheClipboard.Close()
                    
                
            else:
                
                wx.MessageBox( 'Could not get permission to access the clipboard!' )
                
            
        elif data_type == 'text':
            
            text = data
            
            if wx.TheClipboard.Open():
                
                try:
                    
                    data = wx.TextDataObject( text )
                    
                    wx.TheClipboard.SetData( data )
                    
                finally:
                    
                    wx.TheClipboard.Close()
                    
                
            else:
                
                wx.MessageBox( 'I could not get permission to access the clipboard.' )
                
            
        elif data_type == 'bmp':
            
            media = data
            
            image_renderer = self.GetCache( 'images' ).GetImageRenderer( media )
            
            def CopyToClipboard():
                
                if wx.TheClipboard.Open():
                    
                    try:
                        
                        wx_bmp = image_renderer.GetWXBitmap()
                        
                        data = wx.BitmapDataObject( wx_bmp )
                        
                        wx.TheClipboard.SetData( data )
                        
                    finally:
                        
                        wx.TheClipboard.Close()
                        
                    
                else:
                    
                    wx.MessageBox( 'I could not get permission to access the clipboard.' )
                    
                
            
            def THREADWait():
                
                # have to do this in thread, because the image needs the wx event queue to render
                
                start_time = time.time()
                
                while not image_renderer.IsReady():
                    
                    if HydrusData.TimeHasPassed( start_time + 15 ):
                        
                        raise Exception( 'The image did not render in fifteen seconds, so the attempt to copy it to the clipboard was abandoned.' )
                        
                    
                    time.sleep( 0.1 )
                    
                
                wx.CallAfter( CopyToClipboard )
                
            
            self.CallToThread( THREADWait )
            
        
    
    def UnclosePageKeys( self, page_keys ):
        
        with self._page_key_lock:
            
            self._closed_page_keys.difference_update( page_keys )
            
        
    
    def WaitUntilViewFree( self ):
        
        self.WaitUntilModelFree()
        
        self.WaitUntilThumbnailsFree()
        
    
    def WaitUntilThumbnailsFree( self ):
        
        while True:
            
            if self._view_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application shutting down!' )
                
            elif not self._caches[ 'thumbnail' ].DoingWork():
                
                return
                
            else:
                
                time.sleep( 0.00001 )
                
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        if action == 'content_updates':
            
            self._managers[ 'undo' ].AddCommand( 'content_updates', *args, **kwargs )
            
        
        return HydrusController.HydrusController.Write( self, action, *args, **kwargs )
        
    
