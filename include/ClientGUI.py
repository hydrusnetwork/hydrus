from . import HydrusConstants as HC
from . import ClientConstants as CC
from . import ClientCaches
from . import ClientData
from . import ClientDragDrop
from . import ClientExporting
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIDialogsManage
from . import ClientGUIDialogsQuick
from . import ClientGUIExport
from . import ClientGUIFrames
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUILogin
from . import ClientGUIManagement
from . import ClientGUIMenus
from . import ClientGUIPages
from . import ClientGUIParsing
from . import ClientGUIPopupMessages
from . import ClientGUIPredicates
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsManagement
from . import ClientGUIScrolledPanelsReview
from . import ClientGUIShortcuts
from . import ClientGUITags
from . import ClientGUITopLevelWindows
from . import ClientDownloading
from . import ClientMedia
from . import ClientNetworkingContexts
from . import ClientNetworkingJobs
from . import ClientParsing
from . import ClientPaths
from . import ClientRendering
from . import ClientSearch
from . import ClientServices
from . import ClientTags
from . import ClientThreading
import collections
import cv2
import gc
import hashlib
from . import HydrusData
from . import HydrusExceptions
from . import HydrusPaths
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusNetworking
from . import HydrusSerialisable
from . import HydrusTagArchive
from . import HydrusText
from . import HydrusVideoHandling
import os
import PIL
import re
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
import traceback
import types
import wx
import wx.adv

ID_TIMER_UI_UPDATE = wx.NewId()
ID_TIMER_ANIMATION_UPDATE = wx.NewId()

# Sizer Flags

MENU_ORDER = [ 'file', 'undo', 'pages', 'database', 'pending', 'network', 'services', 'help' ]

def THREADUploadPending( service_key ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        service_name = service.GetName()
        service_type = service.GetServiceType()
        
        nums_pending = HG.client_controller.Read( 'nums_pending' )
        
        info = nums_pending[ service_key ]
        
        initial_num_pending = sum( info.values() )
        
        result = HG.client_controller.Read( 'pending', service_key )
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'uploading pending to ' + service_name )
        
        HG.client_controller.pub( 'message', job_key )
        
        while result is not None:
            
            nums_pending = HG.client_controller.Read( 'nums_pending' )
            
            info = nums_pending[ service_key ]
            
            remaining_num_pending = sum( info.values() )
            
            # sometimes more come in while we are pending, -754/1,234 ha ha
            num_to_do = max( initial_num_pending, remaining_num_pending )
            
            done_num_pending = num_to_do - remaining_num_pending
            
            job_key.SetVariable( 'popup_text_1', 'uploading to ' + service_name + ': ' + HydrusData.ConvertValueRangeToPrettyString( done_num_pending, num_to_do ) )
            job_key.SetVariable( 'popup_gauge_1', ( done_num_pending, num_to_do ) )
            
            while job_key.IsPaused() or job_key.IsCancelled():
                
                time.sleep( 0.1 )
                
                if job_key.IsCancelled():
                    
                    job_key.DeleteVariable( 'popup_gauge_1' )
                    job_key.SetVariable( 'popup_text_1', 'cancelled' )
                    
                    HydrusData.Print( job_key.ToString() )
                    
                    job_key.Delete( 5 )
                    
                    return
                    
                
            
            try:
                
                if service_type in HC.REPOSITORIES:
                    
                    if isinstance( result, ClientMedia.MediaResult ):
                        
                        media_result = result
                        
                        client_files_manager = HG.client_controller.client_files_manager
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        path = client_files_manager.GetFilePath( hash, mime )
                        
                        with open( path, 'rb' ) as f:
                            
                            file_bytes = f.read()
                            
                        
                        service.Request( HC.POST, 'file', { 'file' : file_bytes } )
                        
                        file_info_manager = media_result.GetFileInfoManager()
                        
                        timestamp = HydrusData.GetNow()
                        
                        content_update_row = ( file_info_manager, timestamp )
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                        
                    else:
                        
                        client_to_server_update = result
                        
                        service.Request( HC.POST, 'update', { 'client_to_server_update' : client_to_server_update } )
                        
                        content_updates = client_to_server_update.GetClientsideContentUpdates()
                        
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                    
                elif service_type == HC.IPFS:
                    
                    if isinstance( result, ClientMedia.MediaResult ):
                        
                        media_result = result
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        service.PinFile( hash, mime )
                        
                    else:
                        
                        ( hash, multihash ) = result
                        
                        service.UnpinFile( hash, multihash )
                        
                    
                
            except HydrusExceptions.ServerBusyException:
                
                job_key.SetVariable( 'popup_text_1', service.GetName() + ' was busy. please try again in a few minutes' )
                
                job_key.Cancel()
                
                return
                
            
            HG.client_controller.pub( 'notify_new_pending' )
            
            time.sleep( 0.1 )
            
            HG.client_controller.WaitUntilViewFree()
            
            result = HG.client_controller.Read( 'pending', service_key )
            
        
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.SetVariable( 'popup_text_1', 'upload done!' )
        
        HydrusData.Print( job_key.ToString() )
        
        job_key.Finish()
        job_key.Delete( 5 )
        
    except Exception as e:
        
        r = re.search( '[a-fA-F0-9]{64}', str( e ) )
        
        if r is not None:
            
            possible_hash = bytes.fromhex( r.group() )
            
            HydrusData.ShowText( 'Found a possible hash in that error message--trying to show it in a new page.' )
            
            HG.client_controller.pub( 'imported_files_to_page', [ possible_hash ], 'files that did not upload right' )
            
        
        job_key.SetVariable( 'popup_text_1', service.GetName() + ' error' )
        
        job_key.Cancel()
        
        raise
        
    finally:
        
        HG.currently_uploading_pending = False
        HG.client_controller.pub( 'notify_new_pending' )
        
    
class FrameGUI( ClientGUITopLevelWindows.FrameThatResizes ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        title = self._controller.new_options.GetString( 'main_gui_title' )
        
        if title is None or title == '':
            
            title = 'hydrus client'
            
        
        ClientGUITopLevelWindows.FrameThatResizes.__init__( self, None, title, 'main_gui', float_on_parent = False )
        
        bandwidth_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 17 )
        idle_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 6 )
        hydrus_busy_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 11 )
        system_busy_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 13 )
        db_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 14 )
        
        stb_style = wx.STB_SIZEGRIP | wx.STB_ELLIPSIZE_END | wx.FULL_REPAINT_ON_RESIZE
        
        self._statusbar = self.CreateStatusBar( 6, stb_style )
        self._statusbar.SetStatusWidths( [ -1, bandwidth_width, idle_width, hydrus_busy_width, system_busy_width, db_width ] )
        
        self._statusbar_thread_updater = ClientGUICommon.ThreadToGUIUpdater( self._statusbar, self.RefreshStatusBar )
        
        self._closed_pages = []
        
        self._lock = threading.Lock()
        
        self._delayed_dialog_lock = threading.Lock()
        
        self._notebook = ClientGUIPages.PagesNotebook( self, self._controller, 'top page notebook' )
        
        self._last_clipboard_watched_text = ''
        self._clipboard_watcher_destination_page_watcher = None
        self._clipboard_watcher_destination_page_urls = None
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self, self.ImportFiles, self.ImportURLFromDragAndDrop, self._notebook.MediaDragAndDropDropped, self._notebook.PageDragAndDropDropped ) )
        
        wx.GetApp().SetTopWindow( self )
        
        self._message_manager = ClientGUIPopupMessages.PopupMessageManager( self )
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventFrameNewPage )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventFrameNewPage )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventFrameNotebookMenu )
        self.Bind( wx.EVT_CLOSE, self.EventClose )
        self.Bind( wx.EVT_SET_FOCUS, self.EventFocus )
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimationUpdate, id = ID_TIMER_ANIMATION_UPDATE )
        
        self.Bind( wx.EVT_MOVE, self.EventMove )
        self._last_move_pub = 0.0
        
        self._controller.sub( self, 'AddModalMessage', 'modal_message' )
        self._controller.sub( self, 'DeleteOldClosedPages', 'delete_old_closed_pages' )
        self._controller.sub( self, 'NewPageImportHDD', 'new_hdd_import' )
        self._controller.sub( self, 'NewPageQuery', 'new_page_query' )
        self._controller.sub( self, 'NotifyClosedPage', 'notify_closed_page' )
        self._controller.sub( self, 'NotifyDeletedPage', 'notify_deleted_page' )
        self._controller.sub( self, 'NotifyNewExportFolders', 'notify_new_export_folders' )
        self._controller.sub( self, 'NotifyNewImportFolders', 'notify_new_import_folders' )
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'NotifyNewPages', 'notify_new_pages' )
        self._controller.sub( self, 'NotifyNewPending', 'notify_new_pending' )
        self._controller.sub( self, 'NotifyNewPermissions', 'notify_new_permissions' )
        self._controller.sub( self, 'NotifyNewServices', 'notify_new_services_gui' )
        self._controller.sub( self, 'NotifyNewSessions', 'notify_new_sessions' )
        self._controller.sub( self, 'NotifyNewUndo', 'notify_new_undo' )
        self._controller.sub( self, 'PresentImportedFilesToPage', 'imported_files_to_page' )
        self._controller.sub( self, 'SetDBLockedStatus', 'db_locked_status' )
        self._controller.sub( self, 'SetMediaFocus', 'set_media_focus' )
        self._controller.sub( self, 'SetStatusBarDirty', 'set_status_bar_dirty' )
        self._controller.sub( self, 'SetTitle', 'main_gui_title' )
        self._controller.sub( self, 'SyncToTagArchive', 'sync_to_tag_archive' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        self._InitialiseMenubar()
        
        self._menubar_open_menu_stack = []
        
        # tfw in OSX wxCocoa every time you open a new unrelated menu the next button press causes every menu and submenu in the menubar to send a 'window open' event
        # https://trac.wxwidgets.org/ticket/14333
        
        # In Linux behaviour is unreliable, receiving closes but not opens etc...
        
        if HC.PLATFORM_WINDOWS:
            
            self.Bind( wx.EVT_MENU_CLOSE, self.EventMenuClose )
            self.Bind( wx.EVT_MENU_OPEN, self.EventMenuOpen )
            
        
        self._RefreshStatusBar()
        
        self._bandwidth_repeating_job = self._controller.CallRepeatingWXSafe( self, 1.0, 1.0, self.REPEATINGBandwidth )
        
        self._page_update_repeating_job = self._controller.CallRepeatingWXSafe( self, 0.25, 0.25, self.REPEATINGPageUpdate )
        
        self._clipboard_watcher_repeating_job = None
        
        self._ui_update_repeating_job = None
        
        self._ui_update_windows = set()
        
        self._animation_update_timer = wx.Timer( self, id = ID_TIMER_ANIMATION_UPDATE )
        
        self._animation_update_windows = set()
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'main_gui' ] )
        
        self._controller.CallLaterWXSafe( self, 0.5, self._InitialiseSession ) # do this in callafter as some pages want to talk to controller.gui, which doesn't exist yet!
        
    
    def _AboutWindow( self ):
        
        aboutinfo = wx.adv.AboutDialogInfo()
        
        aboutinfo.SetIcon( self._controller.frame_icon )
        aboutinfo.SetName( 'hydrus client' )
        aboutinfo.SetVersion( str( HC.SOFTWARE_VERSION ) + ', using network version ' + str( HC.NETWORK_VERSION ) )
        
        library_versions = []
        
        library_versions.append( ( 'FFMPEG', HydrusVideoHandling.GetFFMPEGVersion() ) )
        library_versions.append( ( 'OpenCV', cv2.__version__ ) )
        library_versions.append( ( 'openssl', ssl.OPENSSL_VERSION ) )
        library_versions.append( ( 'Pillow', PIL.__version__ ) )
        library_versions.append( ( 'html5lib present: ', str( ClientParsing.HTML5LIB_IS_OK ) ) )
        library_versions.append( ( 'lxml present: ', str( ClientParsing.LXML_IS_OK ) ) )
        library_versions.append( ( 'lz4 present: ', str( ClientRendering.LZ4_OK ) ) )
        
        # 2.7.12 (v2.7.12:d33e0cf91556, Jun 27 2016, 15:24:40) [MSC v.1500 64 bit (AMD64)]
        v = sys.version
        
        if ' ' in v:
            
            v = v.split( ' ' )[0]
            
        
        library_versions.append( ( 'python', v ) )
        
        library_versions.append( ( 'sqlite', sqlite3.sqlite_version ) )
        library_versions.append( ( 'wx', wx.version() ) )
        library_versions.append( ( 'temp dir', HydrusPaths.GetCurrentTempDir() ) )
        
        import locale
        
        l_string = locale.getlocale()[0]
        wxl_string = self._controller._app.locale.GetCanonicalName()
        
        library_versions.append( ( 'locale strings', str( ( l_string, wxl_string ) ) ) )
        
        description = 'This client is the media management application of the hydrus software suite.'
        
        description += os.linesep * 2 + os.linesep.join( ( lib + ': ' + version for ( lib, version ) in library_versions ) )
        
        aboutinfo.SetDescription( description )
        
        with open( HC.LICENSE_PATH, 'r', encoding = 'utf-8' ) as f:
            
            license = f.read()
            
        
        aboutinfo.SetLicense( license )
        
        aboutinfo.SetDevelopers( [ 'Anonymous' ] )
        aboutinfo.SetWebSite( 'https://hydrusnetwork.github.io/hydrus/' )
        
        wx.adv.AboutBox( aboutinfo )
        
    
    def _AccountInfo( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account\'s account key.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                subject_account_key = bytes.fromhex( dlg.GetValue() )
                
                service = self._controller.services_manager.GetService( service_key )
                
                response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : subject_account_key } )
                
                account_info = response[ 'account_info' ]
                
                wx.MessageBox( str( account_info ) )
                
            
        
    
    def _AnalyzeDatabase( self ):
        
        message = 'This will gather statistical information on the database\'s indices, helping the query planner perform efficiently. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        message += os.linesep * 2
        message += 'A \'soft\' analyze will only reanalyze those indices that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        message += os.linesep * 2
        message += 'A \'full\' analyze will force a run over every index in the database. This can take substantially longer. If you do not have a specific reason to select this, it is probably pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose how thorough your analyze will be.', yes_label = 'soft', no_label = 'full' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                stop_time = HydrusData.GetNow() + 120
                
                self._controller.Write( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = stop_time )
                
            elif result == wx.ID_NO:
                
                self._controller.Write( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, force_reanalyze = True )
                
            
        
    
    def _AutoRepoSetup( self ):
        
        def do_it():
            
            edit_log = []
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.TAG_REPOSITORY
            name = 'public tag repository'
            
            tag_repo = ClientServices.GenerateService( service_key, service_type, name )
            
            host = 'hydrus.no-ip.org'
            port = 45871
            access_key = bytes.fromhex( '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f' )
            
            credentials = HydrusNetwork.Credentials( host, port, access_key )
            
            tag_repo.SetCredentials( credentials )
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.FILE_REPOSITORY
            name = 'read-only art file repository'
            
            file_repo = ClientServices.GenerateService( service_key, service_type, name )
            
            host = 'hydrus.no-ip.org'
            port = 45872
            access_key = bytes.fromhex( '8f8a3685abc19e78a92ba61d84a0482b1cfac176fd853f46d93fe437a95e40a5' )
            
            credentials = HydrusNetwork.Credentials( host, port, access_key )
            
            file_repo.SetCredentials( credentials )
            
            all_services = list( self._controller.services_manager.GetServices() )
            
            all_services.append( tag_repo )
            all_services.append( file_repo )
            
            self._controller.SetServices( all_services )
            
            message = 'Auto repo setup done! Check services->review services to see your new services.'
            message += os.linesep * 2
            message += 'The PTR has a lot of tags and will sync a little bit at a time when you are not using the client. Expect it to take a few weeks to sync fully.'
            
            HydrusData.ShowText( message )
            
        
        text = 'This will attempt to set up your client with my repositories\' credentials, letting you tag on the public tag repository and see some files.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _AutoServerSetup( self ):
        
        def do_it():
            
            host = '127.0.0.1'
            port = HC.DEFAULT_SERVER_ADMIN_PORT
            
            if HydrusNetworking.LocalPortInUse( port ):
                
                HydrusData.ShowText( 'The server appears to be already running. Either that, or something else is using port ' + str( HC.DEFAULT_SERVER_ADMIN_PORT ) + '.' )
                
                return
                
            else:
                
                try:
                    
                    HydrusData.ShowText( 'Starting server\u2026' )
                    
                    db_param = '-d=' + self._controller.GetDBDir()
                    
                    if HC.PLATFORM_WINDOWS:
                        
                        server_frozen_path = os.path.join( HC.BASE_DIR, 'server.exe' )
                        
                    else:
                        
                        server_frozen_path = os.path.join( HC.BASE_DIR, 'server' )
                        
                    
                    if os.path.exists( server_frozen_path ):
                        
                        cmd = [ server_frozen_path, db_param ]
                        
                    else:
                        
                        python_executable = sys.executable
                        
                        if python_executable.endswith( 'client.exe' ) or python_executable.endswith( 'client' ):
                            
                            raise Exception( 'Could not automatically set up the server--could not find server executable or python executable.' )
                            
                        
                        if 'pythonw' in python_executable:
                            
                            python_executable = python_executable.replace( 'pythonw', 'python' )
                            
                        
                        server_script_path = os.path.join( HC.BASE_DIR, 'server.py' )
                        
                        cmd = [ python_executable, server_script_path, db_param ]
                        
                    
                    sbp_kwargs = HydrusData.GetSubprocessKWArgs( hide_terminal = False )
                    
                    subprocess.Popen( cmd, **sbp_kwargs )
                    
                    time_waited = 0
                    
                    while not HydrusNetworking.LocalPortInUse( port ):
                        
                        time.sleep( 3 )
                        
                        time_waited += 3
                        
                        if time_waited > 30:
                            
                            raise Exception( 'The server\'s port did not appear!' )
                            
                        
                    
                except:
                    
                    HydrusData.ShowText( 'I tried to start the server, but something failed!' + os.linesep + traceback.format_exc() )
                    
                    return
                    
                
            
            time.sleep( 5 )
            
            HydrusData.ShowText( 'Creating admin service\u2026' )
            
            admin_service_key = HydrusData.GenerateKey()
            service_type = HC.SERVER_ADMIN
            name = 'local server admin'
            
            admin_service = ClientServices.GenerateService( admin_service_key, service_type, name )
            
            all_services = list( self._controller.services_manager.GetServices() )
            
            all_services.append( admin_service )
            
            self._controller.SetServices( all_services )
            
            time.sleep( 1 )
            
            admin_service = self._controller.services_manager.GetService( admin_service_key ) # let's refresh it
            
            credentials = HydrusNetwork.Credentials( host, port )
            
            admin_service.SetCredentials( credentials )
            
            time.sleep( 1 )
            
            response = admin_service.Request( HC.GET, 'access_key', { 'registration_key' : b'init' } )
            
            access_key = response[ 'access_key' ]
            
            credentials = HydrusNetwork.Credentials( host, port, access_key )
            
            admin_service.SetCredentials( credentials )
            
            #
            
            HydrusData.ShowText( 'Admin service initialised.' )
            
            wx.CallAfter( ClientGUIFrames.ShowKeys, 'access', ( access_key, ) )
            
            #
            
            time.sleep( 5 )
            
            HydrusData.ShowText( 'Creating tag and file services\u2026' )
            
            response = admin_service.Request( HC.GET, 'services' )
            
            serverside_services = response[ 'services' ]
            
            service_key = HydrusData.GenerateKey()
            
            tag_service = HydrusNetwork.GenerateService( service_key, HC.TAG_REPOSITORY, 'tag service', HC.DEFAULT_SERVICE_PORT )
            
            serverside_services.append( tag_service )
            
            service_key = HydrusData.GenerateKey()
            
            file_service = HydrusNetwork.GenerateService( service_key, HC.FILE_REPOSITORY, 'file service', HC.DEFAULT_SERVICE_PORT + 1 )
            
            serverside_services.append( file_service )
            
            response = admin_service.Request( HC.POST, 'services', { 'services' : serverside_services } )
            
            service_keys_to_access_keys = response[ 'service_keys_to_access_keys' ]
            
            deletee_service_keys = []
            
            with HG.dirty_object_lock:
                
                self._controller.WriteSynchronous( 'update_server_services', admin_service_key, serverside_services, service_keys_to_access_keys, deletee_service_keys )
                
                self._controller.RefreshServices()
                
            
            HydrusData.ShowText( 'Done! Check services->review services to see your new server and its services.' )
            
        
        text = 'This will attempt to start the server in the same install directory as this client, initialise it, and store the resultant admin accounts in the client.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _BackupDatabase( self ):
        
        path = self._new_options.GetNoneableString( 'backup_path' )
        
        if path is None:
            
            wx.MessageBox( 'No backup path is set!' )
            
            return
            
        
        if not os.path.exists( path ):
            
            wx.MessageBox( 'The backup path does not exist--creating it now.' )
            
            HydrusPaths.MakeSureDirectoryExists( path )
            
        
        client_db_path = os.path.join( path, 'client.db' )
        
        if os.path.exists( client_db_path ):
            
            action = 'Update the existing'
            
        else:
            
            action = 'Create a new'
            
        
        text = action + ' backup at "' + path + '"?'
        text += os.linesep * 2
        text += 'The database will be locked while the backup occurs, which may lock up your gui as well.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg_yn:
            
            if dlg_yn.ShowModal() == wx.ID_YES:
                
                self._notebook.SaveGUISession( 'last session' )
                self._notebook.SaveGUISession( 'exit session' )
                
                # session save causes a db read in the menu refresh, so let's put this off just a bit
                self._controller.CallLater( 1.5, self._controller.Write, 'backup', path )
                
            
        
    
    def _BackupService( self, service_key ):
        
        def do_it():
            
            started = HydrusData.GetNow()
            
            service = self._controller.services_manager.GetService( service_key )
            
            service.Request( HC.POST, 'backup' )
            
            HydrusData.ShowText( 'Server backup started!' )
            
            time.sleep( 10 )
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            while result_bytes == b'1':
                
                if self._controller.ViewIsShutdown():
                    
                    return
                    
                
                time.sleep( 10 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusData.GetNow() - started
            
            HydrusData.ShowText( 'Server backup done in ' + HydrusData.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and copy its database files. It will probably take a few minutes to complete, during which time it will not be able to serve any requests.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _CheckDBIntegrity( self ):
        
        message = 'This will check the database for missing and invalid entries. It may take several minutes to complete.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Run integrity check?', yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'db_integrity' )
                
            
        
    
    def _CheckImportFolder( self, name = None ):
        
        if self._controller.options[ 'pause_import_folders_sync' ]:
            
            HydrusData.ShowText( 'Import folders are currently paused under the \'file\' menu. Please unpause them and try this again.' )
            
        
        if name is None:
            
            import_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
        else:
            
            import_folder = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
            
            import_folders = [ import_folder ]
            
        
        for import_folder in import_folders:
            
            import_folder.CheckNow()
            
            self._controller.WriteSynchronous( 'serialisable', import_folder )
            
        
        self._controller.pub( 'notify_new_import_folders' )
        
    
    def _ClearFileViewingStats( self ):
        
        text = 'Are you sure you want to delete _all_ file viewing records? This cannot be undone.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADVANCED, 'clear' )
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
                
                self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
                wx.MessageBox( 'Delete done! Please restart the client to see the changes in the UI.')
                
            
        
    
    def _ClearOrphanFiles( self ):
        
        text = 'This will iterate through every file in your database\'s file storage, removing any it does not expect to be there. It may take some time.'
        text += os.linesep * 2
        text += 'Files and thumbnails will be inaccessible while this occurs, so it is best to leave the client alone until it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                text = 'What would you like to do with the orphaned files? Note that all orphaned thumbnails will be deleted.'
                
                client_files_manager = self._controller.client_files_manager
                
                with ClientGUIDialogs.DialogYesNo( self, text, title = 'Choose what do to with the orphans.', yes_label = 'move them somewhere', no_label = 'delete them' ) as dlg_2:
                    
                    result = dlg_2.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        with wx.DirDialog( self, 'Select location.' ) as dlg_3:
                            
                            if dlg_3.ShowModal() == wx.ID_OK:
                                
                                path = dlg_3.GetPath()
                                
                                self._controller.CallToThread( client_files_manager.ClearOrphans, path )
                                
                            
                        
                    elif result == wx.ID_NO:
                        
                        self._controller.CallToThread( client_files_manager.ClearOrphans )
                        
                    
                
            
        
    
    def _ClearOrphanFileRecords( self ):
        
        text = 'This will instruct the database to review its file records and delete any orphans. You typically do not ever see these files and they are basically harmless, but they can offset some file counts confusingly. You probably only need to run this if you can\'t process the apparent last handful of duplicate filter pairs or hydrus dev otherwise told you to try it.'
        text += os.linesep * 2
        text += 'It will create a popup message while it works and inform you of the number of orphan records found.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'clear_orphan_file_records' )
                
            
        
    
    def _ClearOrphanTables( self ):
        
        text = 'This will instruct the database to review its service tables and delete any orphans. This will typically do nothing, but hydrus dev may tell you to run this, just to check. Be sure you have a semi-recent backup before you run this.'
        text += os.linesep * 2
        text += 'It will create popups if it finds anything to delete.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'clear_orphan_tables' )
                
            
        
    
    def _CullFileViewingStats( self ):
        
        text = 'If your file viewing statistics have some erroneous values due to many short views or accidental long views, this routine will cull your current numbers to compensate. For instance:'
        text += os.linesep * 2
        text += 'If you have a file with 100 views over 100 seconds and a minimum view time of 2 seconds, this will cull the views to 50.'
        text += os.linesep * 2
        text += 'If you have a file with 10 views over 100000 seconds and a maximum view time of 60 seconds, this will cull the total viewtime to 600 seconds.'
        text += os.linesep * 2
        text += 'It will work for both preview and media views based on their separate rules.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.WriteSynchronous( 'cull_file_viewing_statistics' )
                
                wx.MessageBox( 'Cull done! Please restart the client to see the changes in the UI.')
                
            
        
    
    def _DebugFetchAURL( self ):
        
        def wx_code( network_job ):
            
            if not self:
                
                return
                
            
            content = network_job.GetContentBytes()
            
            text = 'Request complete. Length of response is ' + HydrusData.ToHumanBytes( len( content ) ) + '.'
            
            yes_tuples = []
            
            yes_tuples.append( ( 'save to file', 'file' ) )
            yes_tuples.append( ( 'copy to clipboard', 'clipboard' ) )
            
            with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    value = dlg.GetValue()
                    
                    if value == 'file':
                        
                        with wx.FileDialog( self, 'select where to save content', defaultFile = 'result.html', style = wx.FD_SAVE ) as f_dlg:
                            
                            if f_dlg.ShowModal() == wx.ID_OK:
                                
                                path = f_dlg.GetPath()
                                
                                with open( path, 'wb' ) as f:
                                    
                                    f.write( content )
                                    
                                
                            
                        
                    elif value == 'clipboard':
                        
                        text = network_job.GetContentText()
                        
                        self._controller.pub( 'clipboard', 'text', text )
                        
                    
                
            
        
        def thread_wait( url ):
            
            from . import ClientNetworkingJobs
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_title', 'debug network job' )
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
            self._controller.pub( 'message', job_key )
            
            self._controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
            finally:
                
                job_key.Delete( seconds = 3 )
                
            
            wx.CallAfter( wx_code, network_job )
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the URL.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url = dlg.GetValue()
                
                self._controller.CallToThread( thread_wait, url )
                
            
        
    
    def _DebugMakeDelayedModalPopup( self ):
        
        def do_it( controller ):
            
            time.sleep( 5 )
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'debug modal job' )
            
            controller.pub( 'modal_message', job_key )
            
            for i in range( 5 ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                job_key.SetVariable( 'popup_text_1', 'Will auto-dismiss in ' + HydrusData.TimeDeltaToPrettyTimeDelta( 5 - i ) + '.' )
                job_key.SetVariable( 'popup_gauge_1', ( i, 5 ) )
                
                time.sleep( 1 )
                
            
            job_key.Delete()
            
        
        self._controller.CallToThread( do_it, self._controller )
        
    
    def _DebugMakeParentlessTextCtrl( self ):
        
        with wx.Dialog( None, title = 'parentless debug dialog' ) as dlg:
            
            control = wx.TextCtrl( dlg )
            
            control.SetValue( 'debug test input' )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( control, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dlg.SetSizer( vbox )
            
            dlg.ShowModal()
            
        
    
    def _DebugMakeSomePopups( self ):
        
        for i in range( 1, 7 ):
            
            HydrusData.ShowText( 'This is a test popup message -- ' + str( i ) )
            
        
        brother_classem_pinniped = '''++++What the fuck did you just fucking say about me, you worthless heretic? I'll have you know I graduated top of my aspirant tournament in the Heralds of Ultramar, and I've led an endless crusade of secret raids against the forces of The Great Enemy, and I have over 30 million confirmed purgings. I am trained in armored warfare and I'm the top brother in all the thousand Divine Chapters of the Adeptus Astartes. You are nothing to me but just another heretic. I will wipe you the fuck out with precision the likes of which has never been seen before in this universe, mark my fucking words. You think you can get away with saying that shit to me over the Warp? Think again, traitor. As we speak I am contacting my secret network of inquisitors across the galaxy and your malign powers are being traced right now so you better prepare for the holy storm, maggot. The storm that wipes out the pathetic little thing you call your soul. You're fucking dead, kid. I can warp anywhere, anytime, and I can kill you in over seven hundred ways, and that's just with my bolter. Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the Departmento Munitorum and I will use it to its full extent to wipe your miserable ass off the face of the galaxy, you little shit. If only you could have known what holy retribution your little "clever" comment was about to bring down upon you, maybe you would have held your fucking impure tongue. But you couldn't, you didn't, and now you're paying the price, you Emperor-damned heretic.++++\n\n++++Better crippled in body than corrupt in mind++++\n\n++++The Emperor Protects++++'''
        
        HydrusData.ShowText( 'This is a very long message:  \n\n' + brother_classem_pinniped )
        
        #
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', '\u24c9\u24d7\u24d8\u24e2 \u24d8\u24e2 \u24d0 \u24e3\u24d4\u24e2\u24e3 \u24e4\u24dd\u24d8\u24d2\u24de\u24d3\u24d4 \u24dc\u24d4\u24e2\u24e2\u24d0\u24d6\u24d4' )
        
        job_key.SetVariable( 'popup_text_1', '\u24b2\u24a0\u24b2 \u24a7\u249c\u249f' )
        job_key.SetVariable( 'popup_text_2', 'p\u0250\u05df \u028d\u01dd\u028d' )
        
        self._controller.pub( 'message', job_key )
        
        #
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'test job' )
        
        job_key.SetVariable( 'popup_text_1', 'Currently processing test job 5/8' )
        job_key.SetVariable( 'popup_gauge_1', ( 5, 8 ) )
        
        self._controller.pub( 'message', job_key )
        
        self._controller.CallLater( 2.0, job_key.SetVariable, 'popup_text_2', 'Pulsing subjob' )
        
        self._controller.CallLater( 2.0, job_key.SetVariable, 'popup_gauge_2', ( 0, None ) )
        
        #
        
        e = HydrusExceptions.DataMissing( 'This is a test exception' )
        
        HydrusData.ShowException( e )
        
        #
        
        for i in range( 1, 4 ):
            
            self._controller.CallLater( 0.5 * i, HydrusData.ShowText, 'This is a delayed popup message -- ' + str( i ) )
            
        
    
    def _DebugPrintGarbage( self ):
        
        HydrusData.ShowText( 'Printing garbage to log' )
        
        HydrusData.Print( 'uncollectable gc.garbage:' )
        
        count = collections.Counter()
        
        for o in gc.garbage:
            
            count[ type( o ) ] += 1
            
        
        to_print = list( count.items() )
        
        to_print.sort( key = lambda pair: -pair[1] )
        
        for ( k, v ) in to_print:
            
            HydrusData.Print( ( k, v ) )
            
        
        del gc.garbage[:]
        
        old_debug = gc.get_debug()
        
        HydrusData.Print( 'running a collect with stats on:' )
        
        gc.set_debug( gc.DEBUG_LEAK | gc.DEBUG_STATS )
        
        gc.collect()
        
        del gc.garbage[:]
        
        gc.set_debug( old_debug )
        
        #
        
        count = collections.Counter()
        
        for o in gc.get_objects():
            
            count[ type( o ) ] += 1
            
        
        HydrusData.Print( 'currently tracked types:' )
        
        to_print = list( count.items() )
        
        to_print.sort( key = lambda pair: -pair[1] )
        
        for ( k, v ) in to_print:
            
            if v > 25:
                
                HydrusData.Print( ( k, v ) )
                
            
        
        HydrusData.DebugPrint( 'garbage printing finished' )
        
    
    def _DebugShowScheduledJobs( self ):
        
        self._controller.DebugShowScheduledJobs()
        
    
    def _DeleteGUISession( self, name ):
        
        message = 'Delete session "' + name + '"?'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Delete session?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
                
                self._controller.pub( 'notify_new_sessions' )
                
            
        
    
    def _DeletePending( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete the pending data for ' + service.GetName() + '?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'delete_pending', service_key )
                
            
        
    
    def _DeleteServiceInfo( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to clear the cached service info? Rebuilding it may slow some GUI elements for a little while.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: self._controller.Write( 'delete_service_info' )
            
        
    
    def _DestroyPages( self, pages ):
        
        for page in pages:
            
            page.CleanBeforeDestroy()
            
            page.DestroyLater()
            
        
    
    def _DestroyTimers( self ):
        
        if self._animation_update_timer is not None:
            
            self._animation_update_timer.Stop()
            
            self._animation_update_timer = None
            
        
    
    def _DirtyMenu( self, name ):
        
        if name not in self._dirty_menus:
            
            menu_index = self._FindMenuBarIndex( name )
            
            if menu_index != wx.NOT_FOUND:
                
                self._menubar.EnableTop( menu_index, False )
                
            
            self._dirty_menus.add( name )
            
        
    
    def _ExportDownloader( self ):
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'export downloaders' ) as dlg:
            
            panel = ClientGUIParsing.DownloaderExportPanel( dlg, self._controller.network_engine )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _FetchIP( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the file\'s hash.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                hash = bytes.fromhex( dlg.GetValue() )
                
                service = self._controller.services_manager.GetService( service_key )
                
                with wx.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash } )
                
                ip = response[ 'ip' ]
                timestamp = response[ 'timestamp' ]
                
                gmt_time = HydrusData.ConvertTimestampToPrettyTime( timestamp, in_gmt = True )
                local_time = HydrusData.ConvertTimestampToPrettyTime( timestamp )
                
                text = 'File Hash: ' + hash.hex()
                text += os.linesep
                text += 'Uploader\'s IP: ' + ip
                text += 'Upload Time (GMT): ' + gmt_time
                text += 'Upload Time (Your time): ' + local_time
                
                HydrusData.Print( text )
                
                wx.MessageBox( text + os.linesep * 2 + 'This has been written to the log.' )
                
            
        
    
    def _FindMenuBarIndex( self, name ):
        
        for index in range( self._menubar.GetMenuCount() ):
            
            if self._menubar.GetMenu( index ).hydrus_menubar_name == name:
                
                return index
                
            
        
        return wx.NOT_FOUND
        
    
    def _FlipClipboardWatcher( self, option_name ):
        
        self._controller.new_options.FlipBoolean( option_name )
        
        self._last_clipboard_watched_text = ''
        
        if self._clipboard_watcher_repeating_job is None:
            
            self._clipboard_watcher_repeating_job = self._controller.CallRepeatingWXSafe( self, 1.0, 1.0, self.REPEATINGClipboardWatcher )
            
        
    
    def _ForceFitAllNonGUITLWs( self ):
        
        tlws = wx.GetTopLevelWindows()
        
        for tlw in tlws:
            
            if isinstance( tlw, FrameGUI ):
                
                continue
                
            
            size = tlw.GetSize()
            
            HydrusData.ShowText( 'TLW ' + repr( tlw ) + ': pre size/pos - ' + repr( tuple( tlw.GetSize() ) ) + ' ' + repr( tuple( tlw.GetPosition() ) ) )
            
            tlw.Fit()
            
            tlw.SetSize( size )
            
            tlw.Layout()
            
            HydrusData.ShowText( 'TLW ' + repr( tlw ) + ': post size/pos - ' + repr( tuple( tlw.GetSize() ) ) + ' ' + repr( tuple( tlw.GetPosition() ) ) )
            
        
    
    def _ForceLayoutAllNonGUITLWs( self ):
        
        tlws = wx.GetTopLevelWindows()
        
        for tlw in tlws:
            
            if isinstance( tlw, FrameGUI ):
                
                continue
                
            
            HydrusData.ShowText( 'TLW ' + repr( tlw ) + ': pre size/pos - ' + repr( tuple( tlw.GetSize() ) ) + ' ' + repr( tuple( tlw.GetPosition() ) ) )
            
            tlw.Layout()
            
            HydrusData.ShowText( 'TLW ' + repr( tlw ) + ': post size/pos - ' + repr( tuple( tlw.GetSize() ) ) + ' ' + repr( tuple( tlw.GetPosition() ) ) )
            
        
    
    def _GenerateMenuInfo( self, name ):
        
        def file():
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'import files', 'Add new files to the database.', self._ImportFiles )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            #
            
            i_and_e_submenu = wx.Menu()
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'import folders', 'Pause the client\'s import folders.', HC.options[ 'pause_import_folders_sync' ], self._PauseSync, 'import_folders' )
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'export folders', 'Pause the client\'s export folders.', HC.options[ 'pause_export_folders_sync' ], self._PauseSync, 'export_folders' )
            
            ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'pause' )
            
            ClientGUIMenus.AppendSeparator( i_and_e_submenu )
            
            import_folder_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            if len( import_folder_names ) > 0:
                
                submenu = wx.Menu()
                
                if len( import_folder_names ) > 1:
                    
                    ClientGUIMenus.AppendMenuItem( self, submenu, 'check all', 'Check all import folders.', self._CheckImportFolder )
                    
                    ClientGUIMenus.AppendSeparator( submenu )
                    
                
                for name in import_folder_names:
                    
                    ClientGUIMenus.AppendMenuItem( self, submenu, name, 'Check this import folder now.', self._CheckImportFolder, name )
                    
                
                ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'check import folder now' )
                
            
            export_folder_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            if len( export_folder_names ) > 0:
                
                submenu = wx.Menu()
                
                if len( export_folder_names ) > 1:
                    
                    ClientGUIMenus.AppendMenuItem( self, submenu, 'run all', 'Run all export folders.', self._RunExportFolder )
                    
                    ClientGUIMenus.AppendSeparator( submenu )
                    
                
                for name in export_folder_names:
                    
                    ClientGUIMenus.AppendMenuItem( self, submenu, name, 'Check this export folder now.', self._RunExportFolder, name )
                    
                
                ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'check export folder now' )
                
            
            ClientGUIMenus.AppendSeparator( i_and_e_submenu )
            
            ClientGUIMenus.AppendMenuItem( self, i_and_e_submenu, 'manage import folders', 'Manage folders from which the client can automatically import.', self._ManageImportFolders )
            ClientGUIMenus.AppendMenuItem( self, i_and_e_submenu, 'manage export folders', 'Manage folders to which the client can automatically export.', self._ManageExportFolders )
            
            ClientGUIMenus.AppendMenu( menu, i_and_e_submenu, 'import and export folders' )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            open = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, open, 'installation directory', 'Open the installation directory for this client.', self._OpenInstallFolder )
            ClientGUIMenus.AppendMenuItem( self, open, 'database directory', 'Open the database directory for this instance of the client.', self._OpenDBFolder )
            ClientGUIMenus.AppendMenuItem( self, open, 'quick export directory', 'Open the export directory so you can easily access the files you have exported.', self._OpenExportFolder )
            
            ClientGUIMenus.AppendMenu( menu, open, 'open' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'options', 'Change how the client operates.', self._ManageOptions )
            ClientGUIMenus.AppendMenuItem( self, menu, 'shortcuts', 'Edit the shortcuts your client responds to.', self._ManageShortcuts )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            we_borked_linux_pyinstaller = HC.PLATFORM_LINUX and not HC.RUNNING_FROM_SOURCE
            
            if not we_borked_linux_pyinstaller:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'restart', 'Shut the client down and then start it up again.', self.Exit, restart = True )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'exit and force shutdown maintenance', 'Shut the client down and force any outstanding shutdown maintenance to run.', self.Exit, force_shutdown_maintenance = True )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'exit', 'Shut the client down.', self.Exit )
            
            return ( menu, '&file' )
            
        
        def undo():
            
            have_closed_pages = len( self._closed_pages ) > 0
            
            undo_manager = self._controller.GetManager( 'undo' )
            
            ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
            
            have_undo_stuff = undo_string is not None or redo_string is not None
            
            if have_closed_pages or have_undo_stuff:
                
                menu = wx.Menu()
                
                if undo_string is not None:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, undo_string, 'Undo last operation.', self._controller.pub, 'undo' )
                    
                
                if redo_string is not None:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, redo_string, 'Redo last operation.', self._controller.pub, 'redo' )
                    
                
                if have_closed_pages:
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                    undo_pages = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, undo_pages, 'clear all', 'Remove all closed pages from memory.', self.DeleteAllClosedPages )
                    
                    undo_pages.AppendSeparator()
                    
                    args = []
                    
                    for ( i, ( time_closed, page ) ) in enumerate( self._closed_pages ):
                        
                        name = page.GetName()
                        
                        args.append( ( i, name + ' - ' + page.GetPrettyStatus() ) )
                        
                    
                    args.reverse() # so that recently closed are at the top
                    
                    for ( index, name ) in args:
                        
                        ClientGUIMenus.AppendMenuItem( self, undo_pages, name, 'Restore this page.', self._UnclosePage, index )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, undo_pages, 'closed pages' )
                    
                
            else:
                
                menu = None
                
            
            return ( menu, '&undo' )
            
        
        def pages():
            
            menu = wx.Menu()
            
            if self._controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ( total_active_page_count, total_closed_page_count ) = self.GetTotalPageCounts()
                
                ClientGUIMenus.AppendMenuLabel( menu, HydrusData.ToHumanInt( total_active_page_count ) + ' pages open', 'You have this many pages open.' )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'refresh', 'If the current page has a search, refresh it.', self._Refresh )
            
            splitter_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, splitter_menu, 'show/hide', 'Show or hide the panels on the left.', self._ShowHideSplitters )
            
            ClientGUIMenus.AppendSeparator( splitter_menu )
            
            ClientGUIMenus.AppendMenuCheckItem( self, splitter_menu, 'save current page\'s sash positions on client exit', 'Set whether sash position should be saved over on client exit.', self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ), self._new_options.FlipBoolean, 'saving_sash_positions_on_exit' )
            
            ClientGUIMenus.AppendSeparator( splitter_menu )
            
            ClientGUIMenus.AppendMenuItem( self, splitter_menu, 'save current page\'s sash positions now', 'Save the current page\'s sash positions.', self._SaveSplitterPositions )
            
            ClientGUIMenus.AppendSeparator( splitter_menu )
            
            ClientGUIMenus.AppendMenuItem( self, splitter_menu, 'restore all pages\' sash positions to saved value', 'Restore the current sash positions for all pages to the values that are saved.', self._RestoreSplitterPositions )
            
            ClientGUIMenus.AppendMenu( menu, splitter_menu, 'management and preview panels' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            gui_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            sessions = wx.Menu()
            
            if len( gui_session_names ) > 0:
                
                load = wx.Menu()
                
                for name in gui_session_names:
                    
                    ClientGUIMenus.AppendMenuItem( self, load, name, 'Close all other pages and load this session.', self._notebook.LoadGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( sessions, load, 'clear and load' )
                
                append = wx.Menu()
                
                for name in gui_session_names:
                    
                    ClientGUIMenus.AppendMenuItem( self, append, name, 'Append this session to whatever pages are already open.', self._notebook.AppendGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( sessions, append, 'append' )
                
                gui_session_names_to_backup_timestamps = self._controller.Read( 'serialisable_names_to_backup_timestamps', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
                
                if len( gui_session_names_to_backup_timestamps ) > 0:
                    
                    append_backup = wx.Menu()
                    
                    rows = list( gui_session_names_to_backup_timestamps.items() )
                    
                    rows.sort()
                    
                    for ( name, timestamps ) in rows:
                        
                        submenu = wx.Menu()
                        
                        for timestamp in timestamps:
                            
                            ClientGUIMenus.AppendMenuItem( self, submenu, HydrusData.ConvertTimestampToPrettyTime( timestamp ), 'Append this backup session to whatever pages are already open.', self._notebook.AppendGUISessionBackup, name, timestamp )
                            
                        
                        ClientGUIMenus.AppendMenu( append_backup, submenu, name )
                        
                    
                    ClientGUIMenus.AppendMenu( sessions, append_backup, 'append session backup' )
                    
                
            
            save = wx.Menu()
            
            for name in gui_session_names:
                
                if name in ClientGUIPages.RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( self, save, name, 'Save the existing open pages as a session.', self._notebook.SaveGUISession, name )
                
            
            ClientGUIMenus.AppendMenuItem( self, save, 'as new session', 'Save the existing open pages as a session.', self._notebook.SaveGUISession )
            
            ClientGUIMenus.AppendMenu( sessions, save, 'save' )
            
            if len( set( gui_session_names ).difference( ClientGUIPages.RESERVED_SESSION_NAMES ) ) > 0:
                
                delete = wx.Menu()
                
                for name in gui_session_names:
                    
                    if name in ClientGUIPages.RESERVED_SESSION_NAMES:
                        
                        continue
                        
                    
                    ClientGUIMenus.AppendMenuItem( self, delete, name, 'Delete this session.', self._DeleteGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( sessions, delete, 'delete' )
                
            
            ClientGUIMenus.AppendMenu( menu, sessions, 'sessions' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'pick a new page', 'Choose a new page to open.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page' ) )
            
            #
            
            search_menu = wx.Menu()
            
            services = self._controller.services_manager.GetServices()
            
            petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ]
            
            repositories = [ service for service in services if service.GetServiceType() in HC.REPOSITORIES ]
            
            file_repositories = [ service for service in repositories if service.GetServiceType() == HC.FILE_REPOSITORY ]
            
            petition_resolvable_repositories = [ repository for repository in repositories if True in ( repository.HasPermission( content_type, action ) for ( content_type, action ) in petition_permissions ) ]
            
            ClientGUIMenus.AppendMenuItem( self, search_menu, 'my files', 'Open a new search tab for your files.', self._notebook.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, on_deepest_notebook = True )
            ClientGUIMenus.AppendMenuItem( self, search_menu, 'trash', 'Open a new search tab for your recently deleted files.', self._notebook.NewPageQuery, CC.TRASH_SERVICE_KEY, on_deepest_notebook = True )
            
            for service in file_repositories:
                
                ClientGUIMenus.AppendMenuItem( self, search_menu, service.GetName(), 'Open a new search tab for ' + service.GetName() + '.', self._notebook.NewPageQuery, service.GetServiceKey(), on_deepest_notebook = True )
                
            
            ClientGUIMenus.AppendMenu( menu, search_menu, 'new search page' )
            
            #
            
            if len( petition_resolvable_repositories ) > 0:
                
                petition_menu = wx.Menu()
                
                for service in petition_resolvable_repositories:
                    
                    ClientGUIMenus.AppendMenuItem( self, petition_menu, service.GetName(), 'Open a new petition page for ' + service.GetName() + '.', self._notebook.NewPagePetitions, service.GetServiceKey(), on_deepest_notebook = True )
                    
                
                ClientGUIMenus.AppendMenu( menu, petition_menu, 'new petition page' )
                
            
            #
            
            download_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, download_menu, 'url download', 'Open a new tab to download some separate urls.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_url_downloader_page' ) )
            ClientGUIMenus.AppendMenuItem( self, download_menu, 'watcher', 'Open a new tab to watch threads or other updating locations.',  self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_watcher_downloader_page' ) )
            ClientGUIMenus.AppendMenuItem( self, download_menu, 'gallery', 'Open a new tab to download from gallery sites.',  self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_gallery_downloader_page' ) )
            ClientGUIMenus.AppendMenuItem( self, download_menu, 'simple downloader', 'Open a new tab to download files from generic galleries or threads.',  self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_simple_downloader_page' ) )
            
            ClientGUIMenus.AppendMenu( menu, download_menu, 'new download page' )
            
            #
            
            has_ipfs = len( [ service for service in services if service.GetServiceType() == HC.IPFS ] )
            
            if has_ipfs:
                
                download_popup_menu = wx.Menu()
                
                ClientGUIMenus.AppendMenuItem( self, download_popup_menu, 'an ipfs multihash', 'Enter an IPFS multihash and attempt to import whatever is returned.', self._StartIPFSDownload )
                
                ClientGUIMenus.AppendMenu( menu, download_popup_menu, 'new download popup' )
                
            
            #
            
            special_menu = wx.Menu()
            
            
            ClientGUIMenus.AppendMenuItem( self, special_menu, 'page of pages', 'Open a new tab that can hold more tabs.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page_of_pages' ) )
            ClientGUIMenus.AppendMenuItem( self, special_menu, 'duplicates processing', 'Open a new tab to discover and filter duplicate files.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_duplicate_filter_page' ) )
            
            ClientGUIMenus.AppendMenu( menu, special_menu, 'new special page' )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            special_command_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, special_command_menu, 'clear all multiwatcher highlights', 'Command all multiwatcher pages to clear their highlighted watchers.', HG.client_controller.pub, 'clear_multiwatcher_highlights' )
            
            ClientGUIMenus.AppendMenu( menu, special_command_menu, 'special commands' )
            
            #
            
            return ( menu, '&pages' )
            
        
        def database():
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'set a password', 'Set a simple password for the database so only you can open it in the client.', self._SetPassword )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if HG.client_controller.client_files_manager.AllLocationsAreDefault():
                
                backup_path = self._new_options.GetNoneableString( 'backup_path' )
                
                if backup_path is None:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'set up a database backup location', 'Choose a path to back the database up to.', self._SetupBackupPath )
                    
                else:
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, 'update database backup', 'Back the database up to an external location.', self._BackupDatabase )
                    ClientGUIMenus.AppendMenuItem( self, menu, 'change database backup location', 'Choose a path to back the database up to.', self._SetupBackupPath )
                    
                
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'restore from a database backup', 'Restore the database from an external location.', self._controller.RestoreDatabase )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'migrate database', 'Review and manage the locations your database is stored.', self._MigrateDatabase )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'review scheduled file maintenance', 'Review outstanding jobs, and schedule new ones.', self._ReviewFileMaintenance )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'vacuum', 'Defrag the database by completely rebuilding it.', self._VacuumDatabase )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'analyze', 'Optimise slow queries by running statistical analyses on the database.', self._AnalyzeDatabase )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'clear orphan files', 'Clear out surplus files that have found their way into the file structure.', self._ClearOrphanFiles )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'clear orphan file records', 'Clear out surplus file records that have not been deleted correctly.', self._ClearOrphanFileRecords )
            
            if self._controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( self, submenu, 'clear orphan tables', 'Clear out surplus db tables that have not been deleted correctly.', self._ClearOrphanTables )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'maintain' )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'database integrity', 'Have the database examine all its records for internal consistency.', self._CheckDBIntegrity )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'check' )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'autocomplete cache', 'Delete and recreate the tag autocomplete cache, fixing any miscounts.', self._RegenerateACCache )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'similar files search metadata', 'Delete and recreate the similar files search phashes.', self._RegenerateSimilarFilesPhashes )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'similar files search tree', 'Delete and recreate the similar files search tree.', self._RegenerateSimilarFilesTree )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'regenerate' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'clear all file viewing statistics', 'Delete all file viewing records from the database.', self._ClearFileViewingStats )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'cull file viewing statistics based on current min/max values', 'Cull your file viewing statistics based on minimum and maximum permitted time deltas.', self._CullFileViewingStats )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file viewing statistics' )
            
            return ( menu, '&database' )
            
        
        def pending():
            
            nums_pending = self._controller.Read( 'nums_pending' )
            
            total_num_pending = 0
            
            menu = None
            
            can_do_a_menu = not HG.currently_uploading_pending
            
            for ( service_key, info ) in nums_pending.items():
                
                service = self._controller.services_manager.GetService( service_key )
                
                service_type = service.GetServiceType()
                name = service.GetName()
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    pending_phrase = 'tag data to upload'
                    petitioned_phrase = 'tag data to petition'
                    
                elif service_type == HC.FILE_REPOSITORY:
                    
                    pending_phrase = 'files to upload'
                    petitioned_phrase = 'files to petition'
                    
                elif service_type == HC.IPFS:
                    
                    pending_phrase = 'files to pin'
                    petitioned_phrase = 'files to unpin'
                    
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ]
                    
                elif service_type in ( HC.FILE_REPOSITORY, HC.IPFS ):
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_FILES ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ]
                    
                
                if can_do_a_menu and num_pending + num_petitioned > 0:
                    
                    if menu is None:
                        
                        menu = wx.Menu()
                        
                    
                    submenu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, submenu, 'commit', 'Upload ' + name + '\'s pending content.', self._UploadPending, service_key )
                    ClientGUIMenus.AppendMenuItem( self, submenu, 'forget', 'Clear ' + name + '\'s pending content.', self._DeletePending, service_key )
                    
                    submessages = []
                    
                    if num_pending > 0:
                        
                        submessages.append( HydrusData.ToHumanInt( num_pending ) + ' ' + pending_phrase )
                        
                    
                    if num_petitioned > 0:
                        
                        submessages.append( HydrusData.ToHumanInt( num_petitioned ) + ' ' + petitioned_phrase )
                        
                    
                    message = name + ': ' + ', '.join( submessages )
                    
                    ClientGUIMenus.AppendMenu( menu, submenu, message )
                    
                
                total_num_pending += num_pending + num_petitioned
                
            
            return ( menu, '&pending (' + HydrusData.ToHumanInt( total_num_pending ) + ')' )
            
        
        def network():
            
            menu = wx.Menu()
            
            submenu = wx.Menu()
            
            pause_all_new_network_traffic = self._controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
            
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'subscriptions', 'Pause the client\'s synchronisation with website subscriptions.', HC.options[ 'pause_subs_sync' ], self._PauseSync, 'subs' )
            ClientGUIMenus.AppendSeparator( submenu )
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'all new network traffic', 'Stop any new network jobs from sending data.', pause_all_new_network_traffic, self._controller.network_engine.PausePlayNewJobs )
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'paged file import queues', 'Pause all file import queues.', self._controller.new_options.GetBoolean( 'pause_all_file_queues' ), self._controller.new_options.FlipBoolean, 'pause_all_file_queues' )
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'gallery searches', 'Pause all gallery imports\' searching.', self._controller.new_options.GetBoolean( 'pause_all_gallery_searches' ), self._controller.new_options.FlipBoolean, 'pause_all_gallery_searches' )
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'watcher checkers', 'Pause all watchers\' checking.', self._controller.new_options.GetBoolean( 'pause_all_watcher_checkers' ), self._controller.new_options.FlipBoolean, 'pause_all_watcher_checkers' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            #
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'review bandwidth usage', 'See where you are consuming data.', self._ReviewBandwidth )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'review current network jobs', 'Review the jobs currently running in the network engine.', self._ReviewNetworkJobs )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'review session cookies', 'Review and edit which cookies you have for which network contexts.', self._ReviewNetworkSessions )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage http headers', 'Configure how the client talks to the network.', self._ManageNetworkHeaders )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage upnp', 'If your router supports it, see and edit your current UPnP NAT traversal mappings.', self._ManageUPnP )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'data' )
            
            #
            
            submenu = wx.Menu()
            
            if not ClientParsing.HTML5LIB_IS_OK:
                
                message = 'The client was unable to import html5lib on boot. This is an important parsing library that performs better than the usual backup, lxml. Without it, some downloaders will not work well and you will miss tags and files.'
                message += os.linesep * 2
                message += 'You are likely running from source, so I recommend you close the client, run \'pip install html5lib\' (or whatever is appropriate for your environment) and try again. You can double-check what imported ok under help->about.'
                
                ClientGUIMenus.AppendMenuItem( self, submenu, '*** html5lib not found! ***', 'Your client does not have an important library.', wx.MessageBox, message )
                
                ClientGUIMenus.AppendSeparator( submenu )
                
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage subscriptions', 'Change the queries you want the client to regularly import from.', self._ManageSubscriptions )
            
            if self._controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( self, submenu, 'nudge subscriptions awake', 'Tell the subs daemon to wake up, just in case any subs are due.', self._controller.pub, 'notify_restart_subs_sync_daemon' )
                
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            clipboard_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, clipboard_menu, 'watcher urls', 'Automatically import watcher URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_watcher_urls' )
            ClientGUIMenus.AppendMenuCheckItem( self, clipboard_menu, 'other recognised urls', 'Automatically import recognised URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_other_recognised_urls' )
            
            ClientGUIMenus.AppendMenu( submenu, clipboard_menu, 'watch clipboard for urls' )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'import downloaders', 'Import new download capability through encoded pngs from other users.', self._ImportDownloaders )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage default tag import options', 'Change the default tag import options for each of your linked url matches.', self._ManageDefaultTagImportOptions )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage downloader and url display', 'Configure how downloader objects present across the client.', self._ManageDownloaderDisplay )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage logins', 'Edit which domains you wish to log in to.', self._ManageLogins )
            
            debug_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, debug_menu, 'do tumblr GDPR click-through', 'Do a manual click-through for the tumblr GDPR page.', self._controller.CallLater, 0.0, self._controller.network_engine.login_manager.LoginTumblrGDPR )
            
            ClientGUIMenus.AppendMenu( submenu, debug_menu, 'DEBUG' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'downloaders' )
            
            #
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage gallery url generators', 'Manage the client\'s GUGs, which convert search terms into URLs.', self._ManageGUGs )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage url classes', 'Configure which URLs the client can recognise.', self._ManageURLClasses )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage parsers', 'Manage the client\'s parsers, which convert URL content into hydrus metadata.', self._ManageParsers )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage login scripts', 'Manage the client\'s login scripts, which define how to log in to different sites.', self._ManageLoginScripts )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'manage url class links', 'Configure how URLs present across the client.', self._ManageURLClassLinks )
            ClientGUIMenus.AppendMenuItem( self, submenu, 'export downloaders', 'Export downloader components to easy-import pngs.', self._ExportDownloader )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( self, submenu, 'SEMI-LEGACY: manage file lookup scripts', 'Manage how the client parses different types of web content.', self._ManageParsingScripts )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'downloader definitions' )
            
            #
            
            return ( menu, '&network' )
            
        
        def services():
            
            menu = wx.Menu()
            
            tag_services = self._controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
            file_services = self._controller.services_manager.GetServices( ( HC.FILE_REPOSITORY, ) )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, submenu, 'repositories synchronisation', 'Pause the client\'s synchronisation with hydrus repositories.', HC.options[ 'pause_repo_sync' ], self._PauseSync, 'repo' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'review services', 'Look at the services your client connects to.', self._ReviewServices )
            ClientGUIMenus.AppendMenuItem( self, menu, 'manage services', 'Edit the services your client connects to.', self._ManageServices )
            
            repository_admin_permissions = [ ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE ), ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ), ( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE ) ]
            
            repositories = self._controller.services_manager.GetServices( HC.REPOSITORIES )
            admin_repositories = [ service for service in repositories if True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_admin_permissions ) ]
            
            servers_admin = self._controller.services_manager.GetServices( ( HC.SERVER_ADMIN, ) )
            server_admins = [ service for service in servers_admin if service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE ) ]
            
            if len( admin_repositories ) > 0 or len( server_admins ) > 0:
                
                admin_menu = wx.Menu()
                
                for service in admin_repositories:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    can_create_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
                    can_overrule_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
                    can_overrule_account_types = service.HasPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_create_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'create new accounts', 'Create new account keys for this service.', self._GenerateNewAccounts, service_key )
                        
                    
                    if can_overrule_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'modify an account', 'Modify a specific account\'s type and expiration.', self._ModifyAccount, service_key )
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'get an account\'s info', 'Fetch information about an account from the service.', self._AccountInfo, service_key )
                        
                    
                    if can_overrule_accounts and service.GetServiceType() == HC.FILE_REPOSITORY:
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'get an uploader\'s ip address', 'Fetch the ip address that uploaded a specific file, if the service knows it.', self._FetchIP, service_key )
                        
                    
                    if can_overrule_account_types:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'manage account types', 'Add, edit and delete account types for this service.', self._ManageAccountTypes, service_key )
                        
                    
                    ClientGUIMenus.AppendMenu( admin_menu, submenu, service.GetName() )
                    
                
                for service in server_admins:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    can_create_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
                    can_overrule_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
                    can_overrule_account_types = service.HasPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_create_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'create new accounts', 'Create new account keys for this service.', self._GenerateNewAccounts, service_key )
                        
                    
                    if can_overrule_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'modify an account', 'Modify a specific account\'s type and expiration.', self._ModifyAccount, service_key )
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'get an account\'s info', 'Fetch information about an account from the service.', self._AccountInfo, service_key )
                        
                    
                    if can_overrule_account_types:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'manage account types', 'Add, edit and delete account types for this service.', self._ManageAccountTypes, service_key )
                        
                    
                    can_overrule_services = service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_overrule_services:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'manage services', 'Add, edit, and delete this server\'s services.', self._ManageServer, service_key )
                        ClientGUIMenus.AppendMenuItem( self, submenu, 'make a backup', 'Command the server to temporarily pause and back up its database.', self._BackupService, service_key )
                        
                    
                    ClientGUIMenus.AppendMenu( admin_menu, submenu, service.GetName() )
                    
                
                ClientGUIMenus.AppendMenu( menu, admin_menu, 'administrate services' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'import repository update files', 'Add repository update files to the database.', self._ImportUpdateFiles )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'manage tag censorship', 'Set which tags you want to see from which services.', self._ManageTagCensorship )
            ClientGUIMenus.AppendMenuItem( self, menu, 'manage tag siblings', 'Set certain tags to be automatically replaced with other tags.', self._ManageTagSiblings )
            ClientGUIMenus.AppendMenuItem( self, menu, 'manage tag parents', 'Set certain tags to be automatically added with other tags.', self._ManageTagParents )
            
            return ( menu, '&services' )
            
        
        def help():
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'help and getting started guide', 'Open hydrus\'s local help in your web browser.', ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'index.html' ) )
            
            links = wx.Menu()
            
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, 'site', 'Open hydrus\'s website, which is mostly a mirror of the local help.', CC.GlobalBMPs.file_repository, ClientPaths.LaunchURLInWebBrowser, 'https://hydrusnetwork.github.io/hydrus/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, '8chan board', 'Open hydrus dev\'s 8chan board, where he makes release posts and other status updates. Much other discussion also occurs.', CC.GlobalBMPs.eight_chan, ClientPaths.LaunchURLInWebBrowser, 'https://8ch.net/hydrus/index.html' )
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, 'twitter', 'Open hydrus dev\'s twitter, where he makes general progress updates and emergency notifications.', CC.GlobalBMPs.twitter, ClientPaths.LaunchURLInWebBrowser, 'https://twitter.com/hydrusnetwork' )
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, 'tumblr', 'Open hydrus dev\'s tumblr, where he makes release posts and other status updates.', CC.GlobalBMPs.tumblr, ClientPaths.LaunchURLInWebBrowser, 'http://hydrus.tumblr.com/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, 'discord', 'Open a discord channel where many hydrus users congregate. Hydrus dev visits regularly.', CC.GlobalBMPs.discord, ClientPaths.LaunchURLInWebBrowser, 'https://discord.gg/vy8CUB4' )
            site = ClientGUIMenus.AppendMenuBitmapItem( self, links, 'patreon', 'Open hydrus dev\'s patreon, which lets you support development.', CC.GlobalBMPs.patreon, ClientPaths.LaunchURLInWebBrowser, 'https://www.patreon.com/hydrus_dev' )
            
            ClientGUIMenus.AppendMenu( menu, links, 'links' )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'changelog', 'Open hydrus\'s local changelog in your web browser.', ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'changelog.html' ) )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            dont_know = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, dont_know, 'just set up some repositories for me, please', 'This will add the hydrus dev\'s two repositories to your client.', self._AutoRepoSetup )
            
            ClientGUIMenus.AppendMenu( menu, dont_know, 'I don\'t know what I am doing' )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'how boned am I?', 'Check for a summary of your ride so far.', self._HowBonedAmI )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            currently_darkmode = self._new_options.GetString( 'current_colourset' ) == 'darkmode'
            
            ClientGUIMenus.AppendMenuCheckItem( self, menu, 'darkmode', 'Set the \'darkmode\' colourset on and off.', currently_darkmode, self.FlipDarkmode )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'advanced_mode' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( self, menu, 'advanced mode', 'Turn on advanced menu options and buttons.', current_value, func )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            debug = wx.Menu()
            
            debug_modes = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, debug_modes, 'force idle mode', 'Make the client consider itself idle and fire all maintenance routines right now. This may hang the gui for a while.', HG.force_idle_mode, self._SwitchBoolean, 'force_idle_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, debug_modes, 'no page limit mode', 'Let the user create as many pages as they want with no warnings or prohibitions.', HG.no_page_limit_mode, self._SwitchBoolean, 'no_page_limit_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, debug_modes, 'thumbnail debug mode', 'Show some thumbnail debug info.', HG.thumbnail_debug_mode, self._SwitchBoolean, 'thumbnail_debug_mode' )
            ClientGUIMenus.AppendMenuItem( self, debug_modes, 'simulate a wake from sleep', 'Tell the controller to pretend that it just woke up from sleep.', self._controller.SimulateWakeFromSleepEvent )
            
            ClientGUIMenus.AppendMenu( debug, debug_modes, 'debug modes' )
            
            profile_modes = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, profile_modes, 'db profile mode', 'Run detailed \'profiles\' on every database query and dump this information to the log (this is very useful for hydrus dev to have, if something is running slow for you!).', HG.db_profile_mode, self._SwitchBoolean, 'db_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, profile_modes, 'menu profile mode', 'Run detailed \'profiles\' on menu actions.', HG.menu_profile_mode, self._SwitchBoolean, 'menu_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, profile_modes, 'pubsub report mode', 'Report info about every pubsub processed.', HG.pubsub_report_mode, self._SwitchBoolean, 'pubsub_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, profile_modes, 'pubsub profile mode', 'Run detailed \'profiles\' on every internal publisher/subscriber message and dump this information to the log. This can hammer your log with dozens of large dumps every second. Don\'t run it unless you know you need to.', HG.pubsub_profile_mode, self._SwitchBoolean, 'pubsub_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, profile_modes, 'ui timer profile mode', 'Run detailed \'profiles\' on every ui timer update. This will likely spam you!', HG.ui_timer_profile_mode, self._SwitchBoolean, 'ui_timer_profile_mode' )
            
            ClientGUIMenus.AppendMenu( debug, profile_modes, 'profile modes' )
            
            report_modes = wx.Menu()
            
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'callto report mode', 'Report whenever the thread pool is given a task.', HG.callto_report_mode, self._SwitchBoolean, 'callto_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'daemon report mode', 'Have the daemons report whenever they fire their jobs.', HG.daemon_report_mode, self._SwitchBoolean, 'daemon_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'db report mode', 'Have the db report query information, where supported.', HG.db_report_mode, self._SwitchBoolean, 'db_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'file import report mode', 'Have the db and file manager report file import progress.', HG.file_import_report_mode, self._SwitchBoolean, 'file_import_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'file report mode', 'Have the file manager report file request information, where supported.', HG.file_report_mode, self._SwitchBoolean, 'file_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'gui report mode', 'Have the gui report inside information, where supported.', HG.gui_report_mode, self._SwitchBoolean, 'gui_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'hover window report mode', 'Have the hover windows report their show/hide logic.', HG.hover_window_report_mode, self._SwitchBoolean, 'hover_window_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'media load report mode', 'Have the client report media load information, where supported.', HG.media_load_report_mode, self._SwitchBoolean, 'media_load_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'network report mode', 'Have the network engine report new jobs.', HG.network_report_mode, self._SwitchBoolean, 'network_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'similar files metadata generation report mode', 'Have the phash generation routine report its progress.', HG.phash_generation_report_mode, self._SwitchBoolean, 'phash_generation_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'shortcut report mode', 'Have the new shortcut system report what shortcuts it catches and whether it matches an action.', HG.shortcut_report_mode, self._SwitchBoolean, 'shortcut_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'subprocess report mode', 'Report whenever an external process is called.', HG.subprocess_report_mode, self._SwitchBoolean, 'subprocess_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( self, report_modes, 'subscription report mode', 'Have the subscription system report what it is doing.', HG.subscription_report_mode, self._SwitchBoolean, 'subscription_report_mode' )
            
            ClientGUIMenus.AppendMenu( debug, report_modes, 'report modes' )
            
            gui_actions = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'make some popups', 'Throw some varied popups at the message manager, just to check it is working.', self._DebugMakeSomePopups )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'make a popup in five seconds', 'Throw a delayed popup at the message manager, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, HydrusData.ShowText, 'This is a delayed popup message.' )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'make a modal popup in five seconds', 'Throw up a delayed modal popup to test with. It will stay alive for five seconds.', self._DebugMakeDelayedModalPopup )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'make a new page in five seconds', 'Throw a delayed page at the main notebook, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, self._controller.pub, 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'make a parentless text ctrl dialog', 'Make a parentless text control in a dialog to test some character event catching.', self._DebugMakeParentlessTextCtrl )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'force a main gui layout now', 'Tell the gui to relayout--useful to test some gui bootup layout issues.', self.Layout )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'force a layout for all non-main-gui tlws now', 'Tell all sub-frames to relayout--useful to test some layout issues.', self._ForceLayoutAllNonGUITLWs )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'force a fit for all non-gui tlws now', 'Tell all sub-frames to refit--useful to test some layout issues.', self._ForceFitAllNonGUITLWs )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'save \'last session\' gui session', 'Make an immediate save of the \'last session\' gui session. Mostly for testing crashes, where last session is not saved correctly.', self._notebook.SaveGUISession, 'last session' )
            ClientGUIMenus.AppendMenuItem( self, gui_actions, 'run the ui test', 'Run hydrus_dev\'s weekly UI Test. Guaranteed to work and not mess up your session, ha ha.', self._RunUITest )
            
            ClientGUIMenus.AppendMenu( debug, gui_actions, 'gui actions' )
            
            data_actions = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'run fast memory maintenance', 'Tell all the fast caches to maintain themselves.', self._controller.MaintainMemoryFast )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'run slow memory maintenance', 'Tell all the slow caches to maintain themselves.', self._controller.MaintainMemorySlow )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'review threads', 'Show current threads and what they are doing.', self._ReviewThreads )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'show scheduled jobs', 'Print some information about the currently scheduled jobs log.', self._DebugShowScheduledJobs )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'flush log', 'Command the log to write any buffered contents to hard drive.', HydrusData.DebugPrint, 'Flushing log' )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'print garbage', 'Print some information about the python garbage to the log.', self._DebugPrintGarbage )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'clear image rendering cache', 'Tell the image rendering system to forget all current images. This will often free up a bunch of memory immediately.', self._controller.ClearCaches )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'clear thumbnail cache', 'Tell the thumbnail cache to forget everything and redraw all current thumbs.', self._controller.pub, 'clear_all_thumbnails' )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'clear db service info cache', 'Delete all cached service info like total number of mappings or files, in case it has become desynchronised. Some parts of the gui may be laggy immediately after this as these numbers are recalculated.', self._DeleteServiceInfo )
            ClientGUIMenus.AppendMenuItem( self, data_actions, 'load whole db in disk cache', 'Contiguously read as much of the db as will fit into memory. This will massively speed up any subsequent big job.', self._controller.CallToThread, self._controller.Read, 'load_into_disk_cache' )
            
            ClientGUIMenus.AppendMenu( debug, data_actions, 'data actions' )
            
            network_actions = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, network_actions, 'fetch a url', 'Fetch a URL using the network engine as per normal.', self._DebugFetchAURL )
            
            ClientGUIMenus.AppendMenu( debug, network_actions, 'network actions' )
            
            ClientGUIMenus.AppendMenuItem( self, debug, 'run and initialise server for testing', 'This will try to boot the server in your install folder and initialise it. This is mostly here for testing purposes.', self._AutoServerSetup )
            
            ClientGUIMenus.AppendMenu( menu, debug, 'debug' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'hardcoded shortcuts', 'Review some currently hardcoded shortcuts.', wx.MessageBox, CC.SHORTCUT_HELP )
            ClientGUIMenus.AppendMenuItem( self, menu, 'about', 'See this client\'s version and other information.', self._AboutWindow )
            
            return ( menu, '&help' )
            
        
        if name == 'file': result = file()
        elif name == 'undo': result = undo()
        elif name == 'pages': result = pages()
        elif name == 'database': result = database()
        elif name == 'network': result = network()
        elif name == 'pending': result = pending()
        elif name == 'services': result = services()
        elif name == 'help': result = help()
        
        # hackery dackery doo
        ( menu_or_none, label ) = result
        
        if menu_or_none is not None:
            
            menu = menu_or_none
            
            menu.hydrus_menubar_name = name
            
            if HC.PLATFORM_OSX:
                
                menu.SetTitle( label ) # causes bugs in os x if this is not here
                
            
        
        return ( menu_or_none, label )
        
    
    def _GenerateNewAccounts( self, service_key ):
        
        with ClientGUIDialogs.DialogGenerateNewAccounts( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _HowBonedAmI( self ):
        
        self._controller.file_viewing_stats_manager.Flush()
        
        boned_stats = self._controller.Read( 'boned_stats' )
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'review your fate' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewHowBonedAmI( frame, boned_stats )
        
        frame.SetPanel( panel )
        
    
    def _ImportDownloaders( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'import downloaders' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewDownloaderImport( frame, self._controller.network_engine )
        
        frame.SetPanel( panel )
        
    
    def _ImportFiles( self, paths = None ):
        
        if paths is None:
            
            paths = []
            
        
        ClientGUIDialogs.FrameInputLocalFiles( self, paths )
        
    
    def _ImportUpdateFiles( self ):
        
        def do_it( external_update_dir ):
            
            num_errors = 0
            
            filenames = os.listdir( external_update_dir )
            
            update_paths = [ os.path.join( external_update_dir, filename ) for filename in filenames ]
            
            update_paths = list(filter( os.path.isfile, update_paths ))
            
            num_to_do = len( update_paths )
            
            if num_to_do == 0:
                
                wx.CallAfter( wx.MessageBox, 'No files in that directory!' )
                
                return
                
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            try:
                
                job_key.SetVariable( 'popup_title', 'importing updates' )
                HG.client_controller.pub( 'message', job_key )
                
                for ( i, update_path ) in enumerate( update_paths ):
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        job_key.SetVariable( 'popup_text_1', 'Cancelled!' )
                        
                        return
                        
                    
                    try:
                        
                        with open( update_path, 'rb' ) as f:
                            
                            update_network_bytes = f.read()
                            
                        
                        update_network_string_hash = hashlib.sha256( update_network_bytes ).digest()
                        
                        try:
                            
                            update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
                            
                        except:
                            
                            num_errors += 1
                            
                            HydrusData.Print( update_path + ' did not load correctly!' )
                            
                            continue
                            
                        
                        if isinstance( update, HydrusNetwork.DefinitionsUpdate ):
                            
                            mime = HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS
                            
                        elif isinstance( update, HydrusNetwork.ContentUpdate ):
                            
                            mime = HC.APPLICATION_HYDRUS_UPDATE_CONTENT
                            
                        else:
                            
                            num_errors += 1
                            
                            HydrusData.Print( update_path + ' was not an update!' )
                            
                            continue
                            
                        
                        self._controller.WriteSynchronous( 'import_update', update_network_bytes, update_network_string_hash, mime )
                        
                    finally:
                        
                        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                        job_key.SetVariable( 'popup_gauge_1', ( i, num_to_do ) )
                        
                    
                
                if num_errors == 0:
                    
                    job_key.SetVariable( 'popup_text_1', 'Done!' )
                    
                else:
                    
                    job_key.SetVariable( 'popup_text_1', 'Done with ' + HydrusData.ToHumanInt( num_errors ) + ' errors (written to the log).' )
                    
                
            finally:
                
                job_key.DeleteVariable( 'popup_gauge_1' )
                
                job_key.Finish()
                
            
        
        message = 'This lets you manually import a directory of update files for your repositories. Any update files that match what your repositories are looking for will be automatically linked so they do not have to be downloaded.'
        
        wx.MessageBox( message )
        
        with wx.DirDialog( self, 'Select location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._controller.CallToThread( do_it, path )
                
            
        
    
    def _ImportURL( self, url, service_keys_to_tags = None, destination_page_name = None, destination_page_key = None, show_destination_page = True, allow_watchers = True, allow_other_recognised_urls = True, allow_unrecognised_urls = True ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        ( url_type, match_name, can_parse ) = self._controller.network_engine.domain_manager.GetURLParseCapability( url )
        
        if url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and not can_parse:
            
            message = 'This URL was recognised as a "{}" but this URL class does not yet have a parsing script linked to it!'.format( match_name )
            message += os.linesep * 2
            message += 'Since this URL cannot be parsed, a downloader cannot be created for it! Please check your url class links under the \'networking\' menu.'
            
            raise HydrusExceptions.URLClassException( message )
            
        
        url_caught = False
        
        if ( url_type == HC.URL_TYPE_UNKNOWN and allow_unrecognised_urls ) or ( url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY ) and allow_other_recognised_urls ):
            
            url_caught = True
            
            if not self._notebook.HasURLImportPage() and self.IsIconized():
                
                self._controller.CallLaterWXSafe( self, 10, self._ImportURL, url, service_keys_to_tags = service_keys_to_tags, destination_page_name = destination_page_name, destination_page_key = destination_page_key, show_destination_page = show_destination_page, allow_watchers = allow_watchers, allow_other_recognised_urls = allow_other_recognised_urls, allow_unrecognised_urls = allow_unrecognised_urls )
                
                return ( url, '"{}" URL was accepted, but it needed a new page and the client is currently minimized. It is queued to be added once the client is restored.' )
                
            
            page = self._notebook.GetOrMakeURLImportPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                management_panel = page.GetManagementPanel()
                
                management_panel.PendURL( url, service_keys_to_tags = service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        elif url_type == HC.URL_TYPE_WATCHABLE and allow_watchers:
            
            url_caught = True
            
            if not self._notebook.HasMultipleWatcherPage() and self.IsIconized():
                
                self._controller.CallLaterWXSafe( self, 10, self._ImportURL, url, service_keys_to_tags = service_keys_to_tags, destination_page_name = destination_page_name, destination_page_key = destination_page_key, show_destination_page = show_destination_page, allow_watchers = allow_watchers, allow_other_recognised_urls = allow_other_recognised_urls, allow_unrecognised_urls = allow_unrecognised_urls )
                
                return ( url, '"{}" URL was accepted, but it needed a new page and the client is current minimized. It is queued to be added once the client is restored.' )
                
            
            page = self._notebook.GetOrMakeMultipleWatcherPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                management_panel = page.GetManagementPanel()
                
                management_panel.PendURL( url, service_keys_to_tags = service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        
        if url_caught:
            
            raise HydrusExceptions.DataMissing( '"{}" URL was accepted but not added successfully--could not find/generate a new downloader page for it.'.format( match_name ) )
            
        
    
    def _InitialiseMenubar( self ):
        
        self._menubar = wx.MenuBar()
        
        self._menu_updater = ClientGUICommon.ThreadToGUIUpdater( self._menubar, self.RefreshMenu )
        self._dirty_menus = set()
        
        self.SetMenuBar( self._menubar )
        
        for name in MENU_ORDER:
            
            ( menu_or_none, label ) = self._GenerateMenuInfo( name )
            
            if menu_or_none is not None:
                
                menu = menu_or_none
                
                self._menubar.Append( menu, label )
                
            
        
    
    def _InitialiseSession( self ):
        
        default_gui_session = HC.options[ 'default_gui_session' ]
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
        
        cannot_load_from_db = default_gui_session not in existing_session_names
        
        load_a_blank_page = HC.options[ 'default_gui_session' ] == 'just a blank page' or cannot_load_from_db
        
        if not load_a_blank_page:
            
            if self._controller.LastShutdownWasBad():
                
                # this can be upgraded to a nicer checkboxlist dialog to select pages or w/e
                
                message = 'It looks like the last instance of the client did not shut down cleanly.'
                message += os.linesep * 2
                message += 'Would you like to try loading your default session "' + default_gui_session + '", or just a blank page?'
                
                with ClientGUIDialogs.DialogYesNo( self, message, title = 'Previous shutdown was bad', yes_label = 'try to load "' + default_gui_session + '"', no_label = 'just load a blank page' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_NO:
                        
                        load_a_blank_page = True
                        
                    
                
            
        
        if load_a_blank_page:
            
            self._controller.CallLaterWXSafe( self, 0.25, self._notebook.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, on_deepest_notebook = True )
            
        else:
            
            self._controller.CallLaterWXSafe( self, 0.25, self._notebook.LoadGUISession, default_gui_session )
            
        
        last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
        
        self._controller.CallLaterWXSafe( self, 1.0, self.Layout ) # some i3 thing--doesn't layout main gui on init for some reason
        
        self._controller.CallLaterWXSafe( self, last_session_save_period_minutes * 60, self.SaveLastSession )
        
        self._clipboard_watcher_repeating_job = self._controller.CallRepeatingWXSafe( self, 1.0, 1.0, self.REPEATINGClipboardWatcher )
        
    
    def _ManageAccountTypes( self, service_key ):
        
        title = 'manage account types'
        
        with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageAccountTypesPanel( dlg, service_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageDefaultTagImportOptions( self ):
        
        title = 'manage default tag import options'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ) = domain_manager.GetDefaultTagImportOptions()
            
            url_classes = domain_manager.GetURLClasses()
            parsers = domain_manager.GetParsers()
            
            url_class_keys_to_parser_keys = domain_manager.GetURLClassKeysToParserKeys()
            
            panel = ClientGUIScrolledPanelsEdit.EditDefaultTagImportOptionsPanel( dlg, url_classes, parsers, url_class_keys_to_parser_keys, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ) = panel.GetValue()
                
                domain_manager.SetDefaultTagImportOptions( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options )
                
            
        
    
    def _ManageDownloaderDisplay( self ):
        
        title = 'manage downloader display'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            gug_keys_to_display = domain_manager.GetGUGKeysToDisplay()
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_display = domain_manager.GetURLClassKeysToDisplay()
            
            panel = ClientGUIScrolledPanelsEdit.EditDownloaderDisplayPanel( dlg, self._controller.network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( gug_keys_to_display, url_class_keys_to_display ) = panel.GetValue()
                
                domain_manager.SetGUGKeysToDisplay( gug_keys_to_display )
                domain_manager.SetURLClassKeysToDisplay( url_class_keys_to_display )
                
            
        
    
    def _ManageExportFolders( self ):
        
        def wx_do_it():
            
            export_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit export folders' ) as dlg:
                
                panel = ClientGUIExport.EditExportFoldersPanel( dlg, export_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    export_folders = panel.GetValue()
                    
                    existing_db_names = set( self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER ) )
                    
                    good_names = set()
                    
                    for export_folder in export_folders:
                        
                        self._controller.Write( 'serialisable', export_folder )
                        
                        good_names.add( export_folder.GetName() )
                        
                    
                    names_to_delete = existing_db_names - good_names
                    
                    for name in names_to_delete:
                        
                        self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
                        
                    
                    self._controller.pub( 'notify_new_export_folders' )
                    
                
            
        
        def THREAD_do_it( controller ):
            
            with self._delayed_dialog_lock:
                
                original_pause_status = controller.options[ 'pause_export_folders_sync' ]
                
                controller.options[ 'pause_export_folders_sync' ] = True
                
                try:
                    
                    if HG.export_folders_running:
                        
                        job_key = ClientThreading.JobKey()
                        
                        try:
                            
                            job_key.SetVariable( 'popup_text_1', 'Waiting for import folders to finish.' )
                            
                            controller.pub( 'message', job_key )
                            
                            while HG.export_folders_running:
                                
                                time.sleep( 0.1 )
                                
                                if HG.view_shutdown:
                                    
                                    return
                                    
                                
                            
                        finally:
                            
                            job_key.Delete()
                            
                        
                    
                    try:
                        
                        controller.CallBlockingToWX( self, wx_do_it )
                        
                    except HydrusExceptions.WXDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.options[ 'pause_export_folders_sync' ] = original_pause_status
                    
                    controller.pub( 'notify_new_export_folders' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageGUGs( self ):
        
        title = 'manage gallery url generators'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            panel = ClientGUIScrolledPanelsEdit.EditGUGsPanel( dlg, gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                gugs = panel.GetValue()
                
                domain_manager.SetGUGs( gugs )
                
            
        
    
    def _ManageImportFolders( self ):
        
        def wx_do_it():
            
            import_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit import folders' ) as dlg:
                
                panel = ClientGUIImport.EditImportFoldersPanel( dlg, import_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    import_folders = panel.GetValue()
                    
                    existing_db_names = set( self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER ) )
                    
                    good_names = set()
                    
                    for import_folder in import_folders:
                        
                        good_names.add( import_folder.GetName() )
                        
                        self._controller.Write( 'serialisable', import_folder )
                        
                    
                    names_to_delete = existing_db_names.difference( good_names )
                    
                    for name in names_to_delete:
                        
                        self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
                        
                    
                    self._controller.pub( 'notify_new_import_folders' )
                    
                
            
        
        def THREAD_do_it( controller ):
            
            with self._delayed_dialog_lock:
                
                original_pause_status = controller.options[ 'pause_import_folders_sync' ]
                
                controller.options[ 'pause_import_folders_sync' ] = True
                
                try:
                    
                    if HG.import_folders_running:
                        
                        job_key = ClientThreading.JobKey()
                        
                        try:
                            
                            job_key.SetVariable( 'popup_text_1', 'Waiting for import folders to finish.' )
                            
                            controller.pub( 'message', job_key )
                            
                            while HG.import_folders_running:
                                
                                time.sleep( 0.1 )
                                
                                if HG.view_shutdown:
                                    
                                    return
                                    
                                
                            
                        finally:
                            
                            job_key.Delete()
                            
                        
                    
                    try:
                        
                        controller.CallBlockingToWX( self, wx_do_it )
                        
                    except HydrusExceptions.WXDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.options[ 'pause_import_folders_sync' ] = original_pause_status
                    
                    controller.pub( 'notify_new_import_folders' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageLogins( self ):
        
        title = 'manage logins'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            login_manager = self._controller.network_engine.login_manager
            
            login_scripts = login_manager.GetLoginScripts()
            domains_to_login_info = login_manager.GetDomainsToLoginInfo()
            
            panel = ClientGUILogin.EditLoginsPanel( dlg, self._controller.network_engine, login_scripts, domains_to_login_info )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                domains_to_login_info = panel.GetValue()
                
                login_manager.SetDomainsToLoginInfo( domains_to_login_info )
                
                domains_to_login = panel.GetDomainsToLoginAfterOK()
                
                if len( domains_to_login ) > 0:
                    
                    self._controller.network_engine.ForceLogins( domains_to_login )
                    
                
            
        
    
    def _ManageLoginScripts( self ):
        
        title = 'manage login scripts'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            login_manager = self._controller.network_engine.login_manager
            
            login_scripts = login_manager.GetLoginScripts()
            
            panel = ClientGUILogin.EditLoginScriptsPanel( dlg, login_scripts )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                login_scripts = panel.GetValue()
                
                login_manager.SetLoginScripts( login_scripts )
                
            
        
    
    def _ManageNetworkHeaders( self ):
        
        title = 'manage network headers'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            network_contexts_to_custom_header_dicts = domain_manager.GetNetworkContextsToCustomHeaderDicts()
            
            panel = ClientGUIScrolledPanelsEdit.EditNetworkContextCustomHeadersPanel( dlg, network_contexts_to_custom_header_dicts )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                network_contexts_to_custom_header_dicts = panel.GetValue()
                
                domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
                
            
        
    
    def _ManageOptions( self ):
        
        title = 'manage options'
        frame_key = 'manage_options_dialog'
        
        with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageOptionsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        self._controller.pub( 'wake_daemons' )
        self.SetStatusBarDirty()
        self._controller.pub( 'refresh_page_name' )
        self._controller.pub( 'notify_new_colourset' )
        self._controller.pub( 'notify_new_favourite_tags' )
        
    
    def _ManageParsers( self ):
        
        title = 'manage parsers'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            parsers = domain_manager.GetParsers()
            
            panel = ClientGUIParsing.EditParsersPanel( dlg, parsers )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                parsers = panel.GetValue()
                
                domain_manager.SetParsers( parsers )
                
            
        
    
    def _ManageParsingScripts( self ):
        
        title = 'manage parsing scripts'
        
        with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIParsing.ManageParsingScriptsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageServer( self, service_key ):
        
        title = 'manage server services'
        
        with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageServerServicesPanel( dlg, service_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageServices( self ):
        
        original_pause_status = HC.options[ 'pause_repo_sync' ]
        
        HC.options[ 'pause_repo_sync' ] = True
        
        try:
            
            title = 'manage services'
            
            with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsManagement.ManageClientServicesPanel( dlg )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        finally:
            
            HC.options[ 'pause_repo_sync' ] = original_pause_status
            
        
    
    def _ManageShortcuts( self ):
        
        with ClientGUITopLevelWindows.DialogManage( self, 'manage shortcuts' ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageShortcutsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageSubscriptions( self ):
        
        def wx_do_it( subscriptions, original_pause_status ):
            
            title = 'manage subscriptions'
            frame_key = 'manage_subscriptions_dialog'
            
            with ClientGUITopLevelWindows.DialogEdit( self, title, frame_key ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditSubscriptionsPanel( dlg, subscriptions, original_pause_status )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    subscriptions = panel.GetValue()
                    
                    HG.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ], subscriptions )
                    
                
            
        
        def THREAD_do_it( controller ):
            
            with self._delayed_dialog_lock:
                
                original_pause_status = controller.options[ 'pause_subs_sync' ]
                
                controller.options[ 'pause_subs_sync' ] = True
                
                try:
                    
                    if HG.subscriptions_running:
                        
                        job_key = ClientThreading.JobKey()
                        
                        try:
                            
                            job_key.SetVariable( 'popup_text_1', 'Waiting for subs to finish.' )
                            
                            controller.pub( 'message', job_key )
                            
                            while HG.subscriptions_running:
                                
                                time.sleep( 0.1 )
                                
                                if HG.view_shutdown:
                                    
                                    return
                                    
                                
                            
                        finally:
                            
                            job_key.Delete()
                            
                        
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    job_key.SetVariable( 'popup_title', 'loading subscriptions' )
                    
                    controller.CallLater( 1.0, controller.pub, 'message', job_key )
                    
                    subscription_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
                    
                    num_to_do = len( subscription_names )
                    
                    subscriptions = []
                    
                    for ( i, name ) in enumerate( subscription_names ):
                        
                        if job_key.IsCancelled():
                            
                            job_key.Delete()
                            
                            return
                            
                        
                        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) + ': ' + name )
                        job_key.SetVariable( 'popup_gauge_1', ( i + 1, num_to_do ) )
                        
                        subscription = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, name )
                        
                        subscriptions.append( subscription )
                        
                    
                    job_key.Delete()
                    
                    try:
                        
                        controller.CallBlockingToWX( self, wx_do_it, subscriptions, original_pause_status )
                        
                    except HydrusExceptions.WXDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.options[ 'pause_subs_sync' ] = original_pause_status
                    
                    controller.pub( 'notify_new_subscriptions' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageTagCensorship( self ):
        
        with ClientGUITopLevelWindows.DialogManage( self, 'manage tag censorship' ) as dlg:
            
            panel = ClientGUITags.ManageTagCensorshipPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageTagParents( self ):
        
        with ClientGUITopLevelWindows.DialogManage( self, 'manage tag parents' ) as dlg:
            
            panel = ClientGUITags.ManageTagParents( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUITopLevelWindows.DialogManage( self, 'manage tag siblings' ) as dlg:
            
            panel = ClientGUITags.ManageTagSiblings( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _ManageURLClasses( self ):
        
        title = 'manage url classes'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            url_classes = domain_manager.GetURLClasses()
            
            panel = ClientGUIScrolledPanelsEdit.EditURLClassesPanel( dlg, url_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url_classes = panel.GetValue()
                
                domain_manager.SetURLClasses( url_classes )
                
            
        
    
    def _ManageURLClassLinks( self ):
        
        title = 'manage url class links'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            url_classes = domain_manager.GetURLClasses()
            parsers = domain_manager.GetParsers()
            
            url_class_keys_to_parser_keys = domain_manager.GetURLClassKeysToParserKeys()
            
            panel = ClientGUIScrolledPanelsEdit.EditURLClassLinksPanel( dlg, self._controller.network_engine, url_classes, parsers, url_class_keys_to_parser_keys )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url_class_keys_to_parser_keys = panel.GetValue()
                
                domain_manager.SetURLClassKeysToParserKeys( url_class_keys_to_parser_keys )
                
            
        
    
    def _ManageUPnP( self ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self ) as dlg: dlg.ShowModal()
        
    
    def _MigrateDatabase( self ):
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'migrate database' ) as dlg:
            
            panel = ClientGUIScrolledPanelsReview.MigrateDatabasePanel( dlg, self._controller )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        self._DirtyMenu( 'database' )
        
        self._menu_updater.Update()
        
    
    def _ModifyAccount( self, service_key ):
        
        wx.MessageBox( 'this does not work yet!' )
        
        return
        
        service = self._controller.services_manager.GetService( service_key )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account key for the account to be modified.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    account_key = bytes.fromhex( dlg.GetValue() )
                    
                except:
                    
                    wx.MessageBox( 'Could not parse that account key' )
                    
                    return
                    
                
                subject_account = 'blah' # fetch account from service
                
                with ClientGUIDialogs.DialogModifyAccounts( self, service_key, [ subject_account ] ) as dlg2: dlg2.ShowModal()
                
            
        
    
    def _OpenDBFolder( self ):
        
        HydrusPaths.LaunchDirectory( self._controller.GetDBDir() )
        
    
    def _OpenExportFolder( self ):
        
        export_path = ClientExporting.GetExportPath()
        
        HydrusPaths.LaunchDirectory( export_path )
        
    
    def _OpenInstallFolder( self ):
        
        HydrusPaths.LaunchDirectory( HC.BASE_DIR )
        
    
    def _PauseSync( self, sync_type ):
        
        if sync_type == 'repo':
            
            HC.options[ 'pause_repo_sync' ] = not HC.options[ 'pause_repo_sync' ]
            
            self._controller.pub( 'notify_restart_repo_sync_daemon' )
            
        elif sync_type == 'subs':
            
            HC.options[ 'pause_subs_sync' ] = not HC.options[ 'pause_subs_sync' ]
            
            self._controller.pub( 'notify_restart_subs_sync_daemon' )
            
        elif sync_type == 'export_folders':
            
            HC.options[ 'pause_export_folders_sync' ] = not HC.options[ 'pause_export_folders_sync' ]
            
            self._controller.pub( 'notify_restart_export_folders_daemon' )
            
        elif sync_type == 'import_folders':
            
            HC.options[ 'pause_import_folders_sync' ] = not HC.options[ 'pause_import_folders_sync' ]
            
            self._controller.pub( 'notify_restart_import_folders_daemon' )
            
        
        self._controller.Write( 'save_options', HC.options )
        
    
    def _Refresh( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.RefreshQuery()
            
        
    
    def _RefreshStatusBar( self ):
        
        if not self._notebook or not self._statusbar:
            
            return
            
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is None:
            
            media_status = ''
            
        else:
            
            media_status = page.GetPrettyStatus()
            
        
        if self._controller.CurrentlyIdle():
            
            idle_status = 'idle'
            
        else:
            
            idle_status = ''
            
        
        hydrus_busy_status = self._controller.GetThreadPoolBusyStatus()
        
        if self._controller.SystemBusy():
            
            busy_status = 'CPU busy'
            
        else:
            
            busy_status = ''
            
        
        ( db_status, job_name ) = HG.client_controller.GetDBStatus()
        
        self._statusbar.SetToolTip( job_name )
        
        self._statusbar.SetStatusText( media_status, 0 )
        self._statusbar.SetStatusText( idle_status, 2 )
        self._statusbar.SetStatusText( hydrus_busy_status, 3 )
        self._statusbar.SetStatusText( busy_status, 4 )
        self._statusbar.SetStatusText( db_status, 5 )
        
    
    def _RegenerateACCache( self ):
        
        message = 'This will delete and then recreate the entire autocomplete cache. This is useful if miscounting has somehow occurred.'
        message += os.linesep * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'regenerate_ac_cache' )
                
            
        
    
    def _RegenerateSimilarFilesPhashes( self ):
        
        message = 'This will schedule all similar files \'phash\' metadata to be regenerated. This is a very expensive operation that will occur in future idle time.'
        message += os.linesep * 2
        message += 'This ultimately requires a full read for all valid files. It is a large investment of CPU and HDD time.'
        message += os.linesep * 2
        message += 'Do not run this unless you know your phashes need to be regenerated.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'schedule_full_phash_regen' )
                
            
        
    
    def _RegenerateSimilarFilesTree( self ):
        
        message = 'This will delete and then recreate the similar files search tree. This is useful if it has somehow become unbalanced and similar files searches are running slow.'
        message += os.linesep * 2
        message += 'If you have a lot of files, it can take a little while, during which the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'regenerate_similar_files' )
                
            
        
    
    def _RestoreSplitterPositions( self ):
        
        self._controller.pub( 'set_splitter_positions', HC.options[ 'hpos' ], HC.options[ 'vpos' ] )
        
    
    def _ReviewBandwidth( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'review bandwidth' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewAllBandwidthPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewFileMaintenance( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'file maintenance' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewFileMaintenance( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewNetworkJobs( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'review network jobs' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewNetworkJobs( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewNetworkSessions( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'review session cookies' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewNetworkSessionsPanel( frame, self._controller.network_engine.session_manager )
        
        frame.SetPanel( panel )
        
    
    def _ReviewServices( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, self._controller.PrepStringForDisplay( 'Review Services' ), 'review_services' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewServicesPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewThreads( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'review threads' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewThreads( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _RunExportFolder( self, name = None ):
        
        if self._controller.options[ 'pause_export_folders_sync' ]:
            
            HydrusData.ShowText( 'Export folders are currently paused under the \'file\' menu. Please unpause them and try this again.' )
            
        
        if name is None:
            
            export_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
        else:
            
            export_folder = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
            
            export_folders = [ export_folder ]
            
        
        for export_folder in export_folders:
            
            export_folder.RunNow()
            
            self._controller.WriteSynchronous( 'serialisable', export_folder )
            
        
        self._controller.pub( 'notify_new_export_folders' )
        
    
    def _RunUITest( self ):
        
        def wx_open_pages():
            
            page_of_pages = self._notebook.NewPagesNotebook( on_deepest_notebook = False, select_page = True )
            
            t = 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self._notebook.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, page_name = 'test', on_deepest_notebook = True )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page_of_pages' ) )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, page_of_pages.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, page_name = 'test', on_deepest_notebook = False )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_duplicate_filter_page' ) )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_gallery_downloader_page' ) )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_simple_downloader_page' ) )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_url_downloader_page' ) )
            
            t += 0.25
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_watcher_downloader_page' ) )
            
            return page_of_pages
            
        
        def wx_close_unclose_one_page():
            
            self._notebook.CloseCurrentPage()
            
            HG.client_controller.CallLaterWXSafe( self, 0.5, self._UnclosePage )
            
        
        def wx_close_pages( page_of_pages ):
            
            indices = list( range( page_of_pages.GetPageCount() ) )
            
            indices.reverse()
            
            t = 0.0
            
            for i in indices:
                
                HG.client_controller.CallLaterWXSafe( self, t, page_of_pages._ClosePage, i )
                
                t += 0.25
                
            
            t += 1
            
            HG.client_controller.CallLaterWXSafe( self, t, self._notebook.CloseCurrentPage )
            
            t += 1
            
            HG.client_controller.CallLaterWXSafe( self, t, self.DeleteAllClosedPages )
            
        
        def wx_test_ac():
            
            page = self._notebook.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, page_name = 'test', select_page = True )
            
            t = 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, page.SetSearchFocus )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_media_focus' ) )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_search_focus' ) )
            
            t += 0.5
            
            uias = wx.UIActionSimulator()
            
            for c in 'the colour of her hair':
                
                HG.client_controller.CallLaterWXSafe( self, t, uias.Char, ord( c ) )
                
                t += 0.02
                
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_DOWN )
            
            t += 0.05
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_DOWN )
            
            t += 0.05
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            t += 0.5
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            for i in range( 16 ):
                
                t += 2.0
                
                for j in range( i + 1 ):
                    
                    HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_DOWN )
                    
                    t += 0.1
                    
                
                HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
                
                t += 2.0
                
                HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
                
            
            t += 1.0
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_DOWN )
            
            t += 0.05
            
            HG.client_controller.CallLaterWXSafe( self, t, uias.Char, wx.WXK_RETURN )
            
            t += 1.0
            
            HG.client_controller.CallLaterWXSafe( self, t, self._notebook.CloseCurrentPage )
            
        
        def wx_dialog_choose_page():
            
            #self._notebook.ChooseNewPageForDeepestNotebook()
            pass
            
        
        def wx_dialog_options():
            
            pass
            
        
        def wx_dialog_import_folders():
            
            pass
            
        
        def wx_dialog_export_folders():
            
            pass
            
        
        def wx_dialog_manage_services():
            
            pass
            
        
        def wx_dialog_review_services():
            
            pass
            
        
        def do_it():
            
            # pages
            
            page_of_pages = HG.client_controller.CallBlockingToWX( self, wx_open_pages )
            
            time.sleep( 4 )
            
            HG.client_controller.CallBlockingToWX( self, wx_close_unclose_one_page )
            
            time.sleep( 1.5 )
            
            HG.client_controller.CallBlockingToWX( self, wx_close_pages, page_of_pages )
            
            time.sleep( 5 )
            
            del page_of_pages
            
            # a/c
            
            HG.client_controller.CallBlockingToWX( self, wx_test_ac )
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _SaveSplitterPositions( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
            
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof by any means, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or recompile from source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = True ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                password = dlg.GetValue()
                
                if password == '':
                    
                    password = None
                    
                
                self._controller.Write( 'set_password', password )
                
            
        
    
    def _SetMediaFocus( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetMediaFocus()
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetSearchFocus()
            
        
    
    def _SetSynchronisedWait( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetSynchronisedWait()
            
        
    
    def _SetupBackupPath( self ):
        
        backup_intro = 'Everything in your client is stored in the database, which consists of a handful of .db files and a single subdirectory that contains all your media files. It is a very good idea to maintain a regular backup schedule--to save from hard drive failure, serious software fault, accidental deletion, or any other unexpected problem. It sucks to lose all your work, so make sure it can\'t happen!'
        backup_intro += os.linesep * 2
        backup_intro += 'If you prefer to create a manual backup with an external program like FreeFileSync, then please cancel out of the dialog after this and set up whatever you like, but if you would rather a simple solution, simply select a directory and the client will remember it as the designated backup location. Creating or updating your backup can be triggered at any time from the database menu.'
        backup_intro += os.linesep * 2
        backup_intro += 'An ideal backup location is initially empty and on a different hard drive.'
        backup_intro += os.linesep * 2
        backup_intro += 'If you have a large database (100,000+ files) or a slow hard drive, creating the initial backup may take a long time--perhaps an hour or more--but updating an existing backup should only take a couple of minutes (since the client only has to copy new or modified files). Try to update your backup every week!'
        backup_intro += os.linesep * 2
        backup_intro += 'If you would like some more info on making or restoring backups, please consult the help\'s \'installing and updating\' page.'
        
        wx.MessageBox( backup_intro )
        
        with wx.DirDialog( self, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                if path == '':
                    
                    path = None
                    
                
                if path == self._controller.GetDBDir():
                    
                    wx.MessageBox( 'That directory is your current database directory! You cannot backup to the same location you are backing up from!' )
                    
                    return
                    
                
                if os.path.exists( path ):
                    
                    filenames = os.listdir( path )
                    
                    num_files = len( filenames )
                    
                    if num_files == 0:
                        
                        extra_info = 'It looks currently empty, which is great--there is no danger of anything being overwritten.'
                        
                    elif 'client.db' in filenames:
                        
                        extra_info = 'It looks like a client database already exists in the location--be certain that it is ok to overwrite it.'
                        
                    else:
                        
                        extra_info = 'It seems to have some files already in it--be careful and make sure you chose the correct location.'
                        
                    
                else:
                    
                    extra_info = 'The path does not exist yet--it will be created when you make your first backup.'
                    
                
                text = 'You chose "' + path + '". Here is what I understand about it:'
                text += os.linesep * 2
                text += extra_info
                text += os.linesep * 2
                text += 'Are you sure this is the correct directory?'
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        self._new_options.SetNoneableString( 'backup_path', path )
                        
                        text = 'Would you like to create your backup now?'
                        
                        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg_yn_2:
                            
                            if dlg_yn_2.ShowModal() == wx.ID_YES:
                                
                                self._BackupDatabase()
                                
                            
                        
                    
                
            
        
    
    def _ShowHideSplitters( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.ShowHideSplit()
            
        
    
    def _StartIPFSDownload( self ):
        
        ipfs_services = self._controller.services_manager.GetServices( ( HC.IPFS, ) )
        
        if len( ipfs_services ) > 0:
            
            if len( ipfs_services ) == 1:
                
                ( service, ) = ipfs_services
                
            else:
                
                choice_tuples = [ ( service.GetName(), service ) for service in ipfs_services ]
                
                try:
                    
                    service = ClientGUIDialogsQuick.SelectFromList( self, 'Select which IPFS Daemon', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter multihash to download.' ) as dlg:
                
                result = dlg.ShowModal()
                
                if result == wx.ID_OK:
                    
                    multihash = dlg.GetValue()
                    
                    service.ImportFile( multihash )
                    
                
            
        
    
    def _SwitchBoolean( self, name ):
        
        if name == 'callto_report_mode':
            
            HG.callto_report_mode = not HG.callto_report_mode
            
        elif name == 'daemon_report_mode':
            
            HG.daemon_report_mode = not HG.daemon_report_mode
            
        elif name == 'db_report_mode':
            
            HG.db_report_mode = not HG.db_report_mode
            
        elif name == 'db_profile_mode':
            
            HG.db_profile_mode = not HG.db_profile_mode
            
        elif name == 'file_import_report_mode':
            
            HG.file_import_report_mode = not HG.file_import_report_mode
            
        elif name == 'file_report_mode':
            
            HG.file_report_mode = not HG.file_report_mode
            
        elif name == 'gui_report_mode':
            
            HG.gui_report_mode = not HG.gui_report_mode
            
        elif name == 'hover_window_report_mode':
            
            HG.hover_window_report_mode = not HG.hover_window_report_mode
            
        elif name == 'media_load_report_mode':
            
            HG.media_load_report_mode = not HG.media_load_report_mode
            
        elif name == 'menu_profile_mode':
            
            HG.menu_profile_mode = not HG.menu_profile_mode
            
        elif name == 'network_report_mode':
            
            HG.network_report_mode = not HG.network_report_mode
            
        elif name == 'phash_generation_report_mode':
            
            HG.phash_generation_report_mode = not HG.phash_generation_report_mode
            
        elif name == 'pubsub_report_mode':
            
            HG.pubsub_report_mode = not HG.pubsub_report_mode
            
        elif name == 'pubsub_profile_mode':
            
            HG.pubsub_profile_mode = not HG.pubsub_profile_mode
            
        elif name == 'shortcut_report_mode':
            
            HG.shortcut_report_mode = not HG.shortcut_report_mode
            
        elif name == 'subprocess_report_mode':
            
            HG.subprocess_report_mode = not HG.subprocess_report_mode
            
        elif name == 'subscription_report_mode':
            
            HG.subscription_report_mode = not HG.subscription_report_mode
            
        elif name == 'thumbnail_debug_mode':
            
            HG.thumbnail_debug_mode = not HG.thumbnail_debug_mode
            
        elif name == 'ui_timer_profile_mode':
            
            HG.ui_timer_profile_mode = not HG.ui_timer_profile_mode
            
            if HG.ui_timer_profile_mode:
                
                HydrusData.ShowText( 'ui timer profile mode activated' )
                
            else:
                
                HydrusData.ShowText( 'ui timer profile mode deactivated' )
                
            
        elif name == 'force_idle_mode':
            
            HG.force_idle_mode = not HG.force_idle_mode
            
            self._controller.pub( 'wake_idle_workers' )
            self.SetStatusBarDirty()
            
        elif name == 'no_page_limit_mode':
            
            HG.no_page_limit_mode = not HG.no_page_limit_mode
            
        
    
    def _UnclosePage( self, closed_page_index = None ):
        
        if closed_page_index is None:
            
            if len( self._closed_pages ) == 0:
                
                return
                
            
            closed_page_index = len( self._closed_pages ) - 1
            
        
        ( time_closed, page ) = self._closed_pages.pop( closed_page_index )
        
        self._controller.UnclosePageKeys( page.GetPageKeys() )
        
        self._controller.pub( 'notify_page_unclosed', page )
        
        self._controller.pub( 'notify_new_undo' )
        
        self._controller.pub( 'notify_new_pages' )
        
    
    def _UploadPending( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        try:
            
            if isinstance( service, ClientServices.ServiceRestricted ):
                
                service.CheckFunctional( including_bandwidth = False )
                
            else:
                
                service.CheckFunctional()
                
            
        except Exception as e:
            
            wx.MessageBox( 'Unfortunately, there is a problem with starting the upload: ' + str( e ) )
            
            return
            
        
        HG.currently_uploading_pending = True
        
        self._controller.CallToThread( THREADUploadPending, service_key )
        
    
    def _VacuumDatabase( self ):
        
        text = 'This will rebuild the database, rewriting all indices and tables to be contiguous and optimising most operations. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        text += os.linesep * 2
        text += 'A \'soft\' vacuum will only reanalyze those databases that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        text += os.linesep * 2
        text += 'A \'full\' vacuum will immediately force a vacuum for the entire database. This can take substantially longer.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, title = 'Choose how thorough your vacuum will be.', yes_label = 'soft', no_label = 'full' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED )
                
            elif result == wx.ID_NO:
                
                self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED, force_vacuum = True )
                
            
        
    
    def _THREADSyncToTagArchive( self, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes = None ):
        
        if hashes is not None:
            
            hashes = set( hashes )
            
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        try:
            
            hta = HydrusTagArchive.HydrusTagArchive( hta_path )
            
            job_key.SetVariable( 'popup_title', 'syncing to tag archive ' + hta.GetName() )
            job_key.SetVariable( 'popup_text_1', 'preparing' )
            
            self._controller.pub( 'message', job_key )
            
            hydrus_hashes = []
            
            hash_type = hta.GetHashType()
            
            total_num_hta_hashes = 0
            
            for chunk_of_hta_hashes in HydrusData.SplitIteratorIntoChunks( hta.IterateHashes(), 1000 ):
                
                while job_key.IsPaused() or job_key.IsCancelled():
                    
                    time.sleep( 0.1 )
                    
                    if job_key.IsCancelled():
                        
                        job_key.SetVariable( 'popup_text_1', 'cancelled' )
                        
                        HydrusData.Print( job_key.ToString() )
                        
                        return
                        
                    
                
                if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                    
                    chunk_of_hydrus_hashes = chunk_of_hta_hashes
                    
                else:
                    
                    if hash_type == HydrusTagArchive.HASH_TYPE_MD5: given_hash_type = 'md5'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: given_hash_type = 'sha1'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: given_hash_type = 'sha512'
                    
                    chunk_of_hydrus_hashes = self._controller.Read( 'file_hashes', chunk_of_hta_hashes, given_hash_type, 'sha256' )
                    
                
                if file_service_key != CC.COMBINED_FILE_SERVICE_KEY:
                    
                    chunk_of_hydrus_hashes = self._controller.Read( 'filter_hashes', chunk_of_hydrus_hashes, file_service_key )
                    
                
                if hashes is not None:
                    
                    chunk_of_hydrus_hashes = [ hash for hash in chunk_of_hydrus_hashes if hash in hashes ]
                    
                
                hydrus_hashes.extend( chunk_of_hydrus_hashes )
                
                total_num_hta_hashes += len( chunk_of_hta_hashes )
                
                job_key.SetVariable( 'popup_text_1', 'matched ' + HydrusData.ConvertValueRangeToPrettyString( len( hydrus_hashes ), total_num_hta_hashes ) + ' files' )
                
                HG.client_controller.WaitUntilViewFree()
                
            
            del hta
            
            total_num_processed = 0
            
            for chunk_of_hydrus_hashes in HydrusData.SplitListIntoChunks( hydrus_hashes, 50 ):
        
                while job_key.IsPaused() or job_key.IsCancelled():
                    
                    time.sleep( 0.1 )
                    
                    if job_key.IsCancelled():
                        
                        job_key.SetVariable( 'popup_text_1', 'cancelled' )
                        
                        HydrusData.Print( job_key.ToString() )
                        
                        return
                        
                    
                
                self._controller.WriteSynchronous( 'sync_hashes_to_tag_archive', chunk_of_hydrus_hashes, hta_path, tag_service_key, adding, namespaces )
                
                total_num_processed += len( chunk_of_hydrus_hashes )
                
                job_key.SetVariable( 'popup_text_1', 'synced ' + HydrusData.ConvertValueRangeToPrettyString( total_num_processed, len( hydrus_hashes ) ) + ' files' )
                job_key.SetVariable( 'popup_gauge_1', ( total_num_processed, len( hydrus_hashes ) ) )
                
                HG.client_controller.WaitUntilViewFree()
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.SetVariable( 'popup_text_1', 'done!' )
            
            job_key.Finish()
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            job_key.Cancel()
            
        
    
    def AddModalMessage( self, job_key ):
        
        if job_key.IsCancelled() or job_key.IsDeleted():
            
            return
            
        
        if job_key.IsDone():
            
            self._controller.pub( 'message', job_key )
            
            return
            
        
        dialog_open = False
        
        tlps = wx.GetTopLevelWindows()
        
        for tlp in tlps:
            
            if isinstance( tlp, wx.Dialog ):
                
                dialog_open = True
                
            
        
        if self.IsIconized() or dialog_open:
            
            self._controller.CallLaterWXSafe( self, 2, self.AddModalMessage, job_key )
            
        else:
            
            title = job_key.GetIfHasVariable( 'popup_title' )
            
            if title is None:
                
                title = 'important job'
                
            
            hide_close_button = not job_key.IsCancellable()
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, title, hide_buttons = hide_close_button ) as dlg:
                
                panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
                
                dlg.SetPanel( panel )
                
                r = dlg.ShowModal()
                
            
        
    
    def DeleteAllClosedPages( self ):
        
        deletee_pages = [ page for ( time_closed, page ) in self._closed_pages ]
        
        self._closed_pages = []
        
        if len( deletee_pages ) > 0:
            
            self._DestroyPages( deletee_pages )
            
            self._notebook.SetFocus()
            
            self._controller.pub( 'notify_new_undo' )
            
        
    
    def DeleteOldClosedPages( self ):
        
        new_closed_pages = []
        
        now = HydrusData.GetNow()
        
        timeout = 60 * 60
        
        deletee_pages = []
        
        old_closed_pages = self._closed_pages
        
        self._closed_pages = []
        
        for ( time_closed, page ) in old_closed_pages:
            
            if time_closed + timeout < now:
                
                deletee_pages.append( page )
                
            else:
                
                self._closed_pages.append( ( time_closed, page ) )
                
            
        
        if len( old_closed_pages ) != len( self._closed_pages ):
            
            self._controller.pub( 'notify_new_undo' )
            
        
        self._DestroyPages( deletee_pages )
        
    
    def EventClose( self, event ):
        
        if not event.CanVeto():
            
            HG.emergency_exit = True
            
        
        exit_allowed = self.Exit()
        
        if not exit_allowed:
            
            event.Veto()
            
        
    
    def EventFocus( self, event ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetMediaFocus()
            
        
    
    def EventFrameNewPage( self, event ):
        
        screen_position = wx.GetMousePosition()
        
        self._notebook.EventNewPageFromScreenPosition( screen_position )
        
    
    def EventFrameNotebookMenu( self, event ):
        
        screen_position = wx.GetMousePosition()
        
        self._notebook.EventMenuFromScreenPosition( screen_position )
        
    
    def EventMenuClose( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None and hasattr( menu, 'hydrus_menubar_name' ):
            
            if menu in self._menubar_open_menu_stack:
                
                index = self._menubar_open_menu_stack.index( menu )
                
                del self._menubar_open_menu_stack[ index ]
                
            
            if len( self._menubar_open_menu_stack ) == 0:
                
                HG.client_controller.MenubarMenuIsClosed()
                
            
        
        event.Skip()
        
    
    def EventMenuOpen( self, event ):
        
        menu = event.GetMenu()
        
        if menu is not None and hasattr( menu, 'hydrus_menubar_name' ):
            
            if len( self._menubar_open_menu_stack ) == 0:
                
                HG.client_controller.MenubarMenuIsOpen()
                
            
            if menu not in self._menubar_open_menu_stack:
                
                self._menubar_open_menu_stack.append( menu )
                
            
        
        event.Skip()
        
    
    def EventMove( self, event ):
        
        if HydrusData.TimeHasPassedFloat( self._last_move_pub + 0.1 ):
            
            self._controller.pub( 'main_gui_move_event' )
            
            self._last_move_pub = HydrusData.GetNowPrecise()
            
        
        event.Skip()
        
    
    def TIMEREventAnimationUpdate( self, event ):
        
        try:
            
            windows = list( self._animation_update_windows )
            
            for window in windows:
                
                if not window:
                    
                    self._animation_update_windows.discard( window )
                    
                    continue
                    
                
                try:
                    
                    if HG.ui_timer_profile_mode:
                        
                        summary = 'Profiling animation timer: ' + repr( window )
                        
                        HydrusData.Profile( summary, 'window.TIMERAnimationUpdate()', globals(), locals(), min_duration_ms = 3 )
                        
                    else:
                        
                        window.TIMERAnimationUpdate()
                        
                    
                except Exception as e:
                    
                    self._animation_update_windows.discard( window )
                    
                
            
        except:
            
            # unusual error catch here, just to experiment. user was getting wxAssertionError on m_window failed, no GetSize() without window
            # I figured at the time that this is some window manager being unhappy with doing animation on a hidden window,
            # but it could also be a half-dead window trying to draw to a dead bmp or something, and then getting stuck somehow
            # traceback was on the for loop list iteration line,
            # which I think was just the C++/wxAssertionError having trouble making the right trace wew
            
            self._animation_update_windows = set()
            
            windows = []
            
        
        if len( self._animation_update_windows ) == 0:
            
            self._animation_update_timer.Stop()
            
        
    
    def Exit( self, restart = False, force_shutdown_maintenance = False ):
        
        # the return value here is 'exit allowed'
        
        if not HG.emergency_exit:
            
            able_to_close_statement = self._notebook.GetTestAbleToCloseStatement()
            
            if HC.options[ 'confirm_client_exit' ] or able_to_close_statement is not None:
                
                if restart:
                    
                    text = 'Are you sure you want to restart the client? (Will auto-yes in 15 seconds)'
                    
                else:
                    
                    text = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
                    
                
                if able_to_close_statement is not None:
                    
                    text += os.linesep * 2
                    text += able_to_close_statement
                    
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    job = self._controller.CallLaterWXSafe( dlg, 15, dlg.EndModal, wx.ID_YES )
                    
                    try:
                        
                        if dlg.ShowModal() == wx.ID_NO:
                            
                            return False
                            
                        
                    finally:
                        
                        job.Cancel()
                        
                    
                
            
        
        if restart:
            
            HG.restart = True
            
        
        if force_shutdown_maintenance:
            
            HG.do_idle_shutdown_work = True
            
        
        try:
            
            self._notebook.SaveGUISession( 'last session' )
            self._notebook.SaveGUISession( 'exit session' )
            
            self._DestroyTimers()
            
            self.DeleteAllClosedPages() # wx crashes if any are left in here, wew
            
            if self._message_manager:
                
                self._message_manager.CleanBeforeDestroy()
                
                self._message_manager.Hide()
                
            
            self._notebook.CleanBeforeDestroy()
            
            if self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ):
                
                self._SaveSplitterPositions()
                
            
            ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
            
            self._controller.WriteSynchronous( 'save_options', HC.options )
            
            self._controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
        
        for tlp in wx.GetTopLevelWindows():
            
            tlp.Hide()
            
        
        if HG.emergency_exit:
            
            self.Destroy()
            
            self._controller.Exit()
            
        else:
            
            self._controller.CreateSplash()
            
            wx.CallAfter( self._controller.Exit )
            
            self.DestroyLater()
            
        
        return True
        
    
    def FlipDarkmode( self ):
        
        current_colourset = self._new_options.GetString( 'current_colourset' )
        
        if current_colourset == 'darkmode':
            
            new_colourset = 'default'
            
        elif current_colourset == 'default':
            
            new_colourset = 'darkmode'
            
        
        self._new_options.SetString( 'current_colourset', new_colourset )
        
        HG.client_controller.pub( 'notify_new_colourset' )
        
    
    def FleshOutPredicates( self, predicates ):
        
        good_predicates = []
        
        for predicate in predicates:
            
            predicate = predicate.GetCountlessCopy()
            
            ( predicate_type, value, inclusive ) = predicate.GetInfo()
            
            if value is None and predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_SIZE, HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS, HC.PREDICATE_TYPE_SYSTEM_AGE, HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, HC.PREDICATE_TYPE_SYSTEM_HASH, HC.PREDICATE_TYPE_SYSTEM_DURATION, HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, HC.PREDICATE_TYPE_SYSTEM_MIME, HC.PREDICATE_TYPE_SYSTEM_RATING, HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT, HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS ]:
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'input predicate', hide_buttons = True ) as dlg:
                    
                    panel = ClientGUIPredicates.InputFileSystemPredicate( dlg, predicate_type )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        good_predicates.extend( panel.GetValue() )
                        
                    
                
            elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_UNTAGGED:
                
                good_predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 0 ) ) )
                
            elif predicate_type == HC.PREDICATE_TYPE_LABEL:
                
                continue
            
            else:
                
                good_predicates.append( predicate )
                
            
        
        return good_predicates
        
    
    def GetCurrentPage( self ):
        
        return self._notebook.GetCurrentMediaPage()
        
    
    def GetCurrentSessionPageInfoDict( self ):
        
        return self._notebook.GetPageInfoDict( is_selected = True )
        
    
    def GetTotalPageCounts( self ):
        
        total_active_page_count = self._notebook.GetNumPages()
        
        total_closed_page_count = len( self._closed_pages )
        
        return ( total_active_page_count, total_closed_page_count )
        
    
    def IShouldRegularlyUpdate( self, window ):
        
        current_page = self.GetCurrentPage()
        
        if current_page is not None:
            
            in_current_page = ClientGUIFunctions.IsWXAncestor( window, current_page )
            
            if in_current_page:
                
                return True
                
            
        
        in_other_window = ClientGUIFunctions.GetTLP( window ) != self
        
        return in_other_window
        
    
    def ImportFiles( self, paths ):
        
        # can more easily do this when file_seeds are doing their own tags
        
        # get current media page
        # if it is an import page, ask user if they want to add it to the page or make a new one
        # if using existing, then load the panel without file import options
        # think about how to merge 'delete_after_success' or not--maybe this can be handled by file_seeds as well
        
        self._ImportFiles( paths )
        
    
    def ImportURLFromAPI( self, url, service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page ):
        
        try:
            
            ( normalised_url, result_text ) = self._ImportURL( url, service_keys_to_tags = service_keys_to_tags, destination_page_name = destination_page_name, destination_page_key = destination_page_key, show_destination_page = show_destination_page )
            
            return ( normalised_url, result_text )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            raise HydrusExceptions.InsufficientCredentialsException( str( e ) )
            
        
    
    def ImportURLFromDragAndDrop( self, url ):
        
        try:
            
            self._ImportURL( url )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
    
    def IsCurrentPage( self, page_key ):
        
        result = self._notebook.GetCurrentMediaPage()
        
        if result is None:
            
            return False
            
        else:
            
            return page_key == result.GetPageKey()
            
        
    
    def NewPageImportHDD( self, paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportHDD( paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success )
        
        self._notebook.NewPage( management_controller, on_deepest_notebook = True )
        
    
    def NewPageQuery( self, service_key, initial_hashes = None, initial_predicates = None, page_name = None, do_sort = False ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        self._notebook.NewPageQuery( service_key, initial_hashes = initial_hashes, initial_predicates = initial_predicates, page_name = page_name, on_deepest_notebook = True, do_sort = do_sort )
        
    
    def NotifyClosedPage( self, page ):
        
        if self._clipboard_watcher_destination_page_urls == page:
            
            self._clipboard_watcher_destination_page_urls = None
            
        
        if self._clipboard_watcher_destination_page_watcher == page:
            
            self._clipboard_watcher_destination_page_watcher = None
            
        
        close_time = HydrusData.GetNow()
        
        self._closed_pages.append( ( close_time, page ) )
        
        self._controller.ClosePageKeys( page.GetPageKeys() )
        
        if self._notebook.GetNumPages() == 0:
            
            self._notebook.SetFocus()
            
        
        self._DirtyMenu( 'pages' )
        
        self._menu_updater.Update()
        
    
    def NotifyDeletedPage( self, page ):
        
        if self._notebook.GetNumPages() == 0:
            
            self._notebook.SetFocus()
            
        
        self._DestroyPages( ( page, ) )
        
        self._DirtyMenu( 'pages' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewExportFolders( self ):
        
        self._DirtyMenu( 'file' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewImportFolders( self ):
        
        self._DirtyMenu( 'file' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewOptions( self ):
        
        self._DirtyMenu( 'services' )
        self._DirtyMenu( 'help' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewPages( self ):
        
        self._DirtyMenu( 'pages' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewPending( self ):
        
        self._DirtyMenu( 'pending' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewPermissions( self ):
        
        self._DirtyMenu( 'pages' )
        self._DirtyMenu( 'services' )
        self._DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewServices( self ):
        
        self._DirtyMenu( 'pages' )
        self._DirtyMenu( 'services' )
        self._DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewSessions( self ):
        
        self._DirtyMenu( 'pages' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewUndo( self ):
        
        self._DirtyMenu( 'undo' )
        
        self._menu_updater.Update()
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        tlp = ClientGUIFunctions.GetTLP( self )
        
        if tlp.IsIconized() and not self._notebook.HasMediaPageName( page_name ):
            
            self._controller.CallLaterWXSafe( self, 10.0, self.PresentImportedFilesToPage, hashes, page_name )
            
            return
            
        
        dest_page = self._notebook.PresentImportedFilesToPage( hashes, page_name )
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'refresh':
                
                self._Refresh()
                
            elif action == 'new_page':
                
                self._notebook.ChooseNewPageForDeepestNotebook()
                
            elif action == 'new_page_of_pages':
                
                self._notebook.NewPagesNotebook( on_deepest_notebook = True )
                
            elif action == 'new_duplicate_filter_page':
                
                self._notebook.NewPageDuplicateFilter( on_deepest_notebook = True )
                
            elif action == 'new_gallery_downloader_page':
                
                self._notebook.NewPageImportGallery( on_deepest_notebook = True )
                
            elif action == 'new_simple_downloader_page':
                
                self._notebook.NewPageImportSimpleDownloader( on_deepest_notebook = True )
                
            elif action == 'new_url_downloader_page':
                
                self._notebook.NewPageImportURLs( on_deepest_notebook = True )
                
            elif action == 'new_watcher_downloader_page':
                
                self._notebook.NewPageImportMultipleWatcher( on_deepest_notebook = True )
                
            elif action == 'close_page':
                
                self._notebook.CloseCurrentPage()
                
            elif action == 'unclose_page':
                
                self._UnclosePage()
                
            elif action == 'check_all_import_folders':
                
                self._CheckImportFolder()
                
            elif action == 'flip_darkmode':
                
                self.FlipDarkmode()
                
            elif action == 'show_hide_splitters':
                
                self._ShowHideSplitters()
                
            elif action == 'synchronised_wait_switch':
                
                self._SetSynchronisedWait()
                
            elif action == 'set_media_focus':
                
                self._SetMediaFocus()
                
            elif action == 'set_search_focus':
                
                self._SetSearchFocus()
                
            elif action == 'redo':
                
                self._controller.pub( 'redo' )
                
            elif action == 'undo':
                
                self._controller.pub( 'undo' )
                
            elif action == 'flip_debug_force_idle_mode_do_not_set_this':
                
                self._SwitchBoolean( 'force_idle_mode' )
                
                self._DirtyMenu( 'help' )
                
                self._menu_updater.Update()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def RefreshMenu( self ):
        
        if not self:
            
            return
            
        
        db_going_to_hang_if_we_hit_it = HG.client_controller.DBCurrentlyDoingJob()
        menu_open = HG.client_controller.MenuIsOpen()
        
        if db_going_to_hang_if_we_hit_it or menu_open:
            
            self._controller.CallLaterWXSafe( self, 0.5, self.RefreshMenu )
            
            return
            
        
        if len( self._dirty_menus ) > 0:
            
            name = self._dirty_menus.pop()
            
            ( menu_or_none, label ) = self._GenerateMenuInfo( name )
            
            old_menu_index = self._FindMenuBarIndex( name )
            
            if old_menu_index == wx.NOT_FOUND:
                
                if menu_or_none is not None:
                    
                    menu = menu_or_none
                    
                    insert_index = 0
                    
                    # for every menu that may display, if it is displayed now, bump up insertion index up one
                    for possible_name in MENU_ORDER:
                        
                        if possible_name == name:
                            
                            break
                            
                        
                        possible_menu_index = self._FindMenuBarIndex( possible_name )
                        
                        if possible_menu_index != wx.NOT_FOUND:
                            
                            insert_index += 1
                            
                        
                    
                    self._menubar.Insert( insert_index, menu, label )
                    
                
            else:
                
                if name == 'pending' and HG.currently_uploading_pending:
                    
                    self._menubar.SetMenuLabel( old_menu_index, label )
                    
                else:
                    
                    old_menu = self._menubar.GetMenu( old_menu_index )
                    
                    if menu_or_none is not None:
                        
                        menu = menu_or_none
                        
                        self._menubar.Replace( old_menu_index, menu, label )
                        
                    else:
                        
                        self._menubar.Remove( old_menu_index )
                        
                    
                    ClientGUIMenus.DestroyMenu( self, old_menu )
                    
                
            
        
        if len( self._dirty_menus ) > 0:
            
            self._controller.CallLaterWXSafe( self, 0.5, self.RefreshMenu )
            
        
    
    def RefreshStatusBar( self ):
        
        self._RefreshStatusBar()
        
    
    def RegisterAnimationUpdateWindow( self, window ):
        
        self._animation_update_windows.add( window )
        
        if self._animation_update_timer is not None and not self._animation_update_timer.IsRunning():
            
            self._animation_update_timer.Start( 5, wx.TIMER_CONTINUOUS )
            
        
    
    def RegisterUIUpdateWindow( self, window ):
        
        self._ui_update_windows.add( window )
        
        if self._ui_update_repeating_job is None:
            
            self._ui_update_repeating_job = self._controller.CallRepeatingWXSafe( self, 0.0, 0.1, self.REPEATINGUIUpdate )
            
        
    
    def REPEATINGBandwidth( self ):
        
        global_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        
        boot_time = self._controller.GetBootTime()
        
        time_since_boot = max( 1, HydrusData.GetNow() - boot_time )
        
        usage_since_boot = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, time_since_boot )
        
        bandwidth_status = HydrusData.ToHumanBytes( usage_since_boot )
        
        current_usage = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        if current_usage > 0:
            
            bandwidth_status += ' (' + HydrusData.ToHumanBytes( current_usage ) + '/s)'
            
        
        self._statusbar.SetStatusText( bandwidth_status, 1 )
        
    
    def REPEATINGClipboardWatcher( self ):
        
        allow_watchers = self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' )
        allow_other_recognised_urls = self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' )
        
        if not ( allow_watchers or allow_other_recognised_urls ):
            
            self._clipboard_watcher_repeating_job.Cancel()
            
            self._clipboard_watcher_repeating_job = None
            
            return
            
        
        try:
            
            text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing:
            
            text = ''
            
        except Exception as e:
            
            HydrusData.ShowText( 'Could not access the clipboard: {}'.format( e ) )
            
            self._clipboard_watcher_repeating_job.Cancel()
            
            self._clipboard_watcher_repeating_job = None
            
            return
            
        
        if text != self._last_clipboard_watched_text:
            
            self._last_clipboard_watched_text = text
            
            for possible_url in HydrusText.DeserialiseNewlinedTexts( text ):
                
                if not possible_url.startswith( 'http' ):
                    
                    continue
                    
                
                try:
                    
                    self._ImportURL( possible_url, show_destination_page = False, allow_watchers = allow_watchers, allow_other_recognised_urls = allow_other_recognised_urls, allow_unrecognised_urls = False )
                    
                except HydrusExceptions.URLClassException:
                    
                    pass
                    
                except HydrusExceptions.DataMissing:
                    
                    HydrusData.ShowText( 'Could not find a new page to place the clipboard URL. Perhaps the client is at its page limit.' )
                    
                    break
                    
                
            
        
    
    def REPEATINGPageUpdate( self ):
        
        page = self.GetCurrentPage()
        
        if page is not None:
            
            if HG.ui_timer_profile_mode:
                
                summary = 'Profiling page timer: ' + repr( page )
                
                HydrusData.Profile( summary, 'page.REPEATINGPageUpdate()', globals(), locals(), min_duration_ms = 3 )
                
            else:
                
                page.REPEATINGPageUpdate()
                
            
        
    
    def REPEATINGUIUpdate( self ):
        
        for window in list( self._ui_update_windows ):
            
            if not window:
                
                self._ui_update_windows.discard( window )
                
                continue
                
            
            try:
                
                if HG.ui_timer_profile_mode:
                    
                    summary = 'Profiling ui update timer: ' + repr( window )
                    
                    HydrusData.Profile( summary, 'window.TIMERUIUpdate()', globals(), locals(), min_duration_ms = 3 )
                    
                else:
                    
                    window.TIMERUIUpdate()
                    
                
            except Exception as e:
                
                self._ui_update_windows.discard( window )
                
                HydrusData.ShowException( e )
                
            
        
        if len( self._ui_update_windows ) == 0:
            
            self._ui_update_repeating_job.Cancel()
            
            self._ui_update_repeating_job = None
            
        
    
    def SaveLastSession( self ):
        
        only_save_last_session_during_idle = self._controller.new_options.GetBoolean( 'only_save_last_session_during_idle' )
        
        if only_save_last_session_during_idle and not self._controller.CurrentlyIdle():
            
            next_call_delay = 60
            
        else:
            
            if HC.options[ 'default_gui_session' ] == 'last session':
                
                self._notebook.SaveGUISession( 'last session' )
                
            
            last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
            
            next_call_delay = last_session_save_period_minutes * 60
            
        
        self._controller.CallLaterWXSafe( self, next_call_delay, self.SaveLastSession )
        
    
    def SetMediaFocus( self ):
        
        self._SetMediaFocus()
        
    
    def SetStatusBarDirty( self ):
        
        self._statusbar_thread_updater.Update()
        
    
    def ShowPage( self, page_key ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            raise HydrusExceptions.DataMissing( 'Could not find that page!' )
            
        
        self._notebook.ShowPage( page )
        
    
    def SyncToTagArchive( self, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes = None ):
        
        self._controller.CallToThread( self._THREADSyncToTagArchive, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes )
        
    
    def UnregisterAnimationUpdateWindow( self, window ):
        
        self._animation_update_windows.discard( window )
        
    
    def UnregisterUIUpdateWindow( self, window ):
        
        self._ui_update_windows.discard( window )
        
    
class FrameSplashPanel( wx.Panel ):
    
    WIDTH = 480
    HEIGHT = 280
    
    def __init__( self, parent, controller ):
        
        wx.Panel.__init__( self, parent )
        
        self._controller = controller
        
        self._dirty = True
        
        self._my_status = FrameSplashStatus( self._controller, self )
        
        self._bmp = wx.Bitmap( self.WIDTH, self.HEIGHT, 24 )
        
        self.SetClientSize( ( self.WIDTH, self.HEIGHT ) )
        self.SetMinClientSize( ( self.WIDTH, self.HEIGHT ) )
        
        self._drag_init_click_coordinates = None
        self._drag_init_position = None
        self._initial_position = self.GetParent().GetPosition()
        
        # this is 124 x 166
        self._hydrus = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'hydrus_splash.png' ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
    
    def _Redraw( self, dc ):
        
        ( title_text, status_text, status_subtext ) = self._my_status.GetTexts()
        
        dc.SetBackground( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) ) )
        
        dc.Clear()
        
        #
        
        x = ( self.WIDTH - 124 ) // 2
        y = 15
        
        dc.DrawBitmap( self._hydrus, x, y )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        y += 166 + 15
        
        #
        
        ( width, height ) = dc.GetTextExtent( title_text )
        
        text_gap = ( self.HEIGHT - y - height * 3 ) // 4
        
        x = ( self.WIDTH - width ) // 2
        y += text_gap
        
        dc.DrawText( title_text, x, y )
        
        #
        
        y += height + text_gap
        
        ( width, height ) = dc.GetTextExtent( status_text )
        
        x = ( self.WIDTH - width ) // 2
        
        dc.DrawText( status_text, x, y )
        
        #
        
        y += height + text_gap
        
        ( width, height ) = dc.GetTextExtent( status_subtext )
        
        x = ( self.WIDTH - width ) // 2
        
        dc.DrawText( status_subtext, x, y )
        
    
    def EventDrag( self, event ):
        
        if event.Dragging() and self._drag_init_click_coordinates is not None:
            
            ( init_x, init_y ) = self._drag_init_click_coordinates
            
            ( x, y ) = wx.GetMousePosition()
            
            total_drag_delta = ( x - init_x, y - init_y )
            
            #
            
            ( init_x, init_y ) = self._drag_init_position
            
            ( total_delta_x, total_delta_y ) = total_drag_delta
            
            self.GetParent().SetPosition( ( init_x + total_delta_x, init_y + total_delta_y ) )
            
        
    
    def EventDragBegin( self, event ):
        
        self._drag_init_click_coordinates = wx.GetMousePosition()
        self._drag_init_position = self.GetParent().GetPosition()
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._drag_init_click_coordinates = None
        
        event.Skip()
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._bmp )
        
        if self._dirty:
            
            self._Redraw( dc )
            
        
    
    def SetDirty( self ):
        
        if not self:
            
            return
            
        
        self._dirty = True
        
        self.Refresh()
        
    
# We have this to be an off-wx-thread-happy container for this info, as the framesplash has to deal with messages in the fuzzy time of shutdown
# all of a sudden, pubsubs are processed in non wx-thread time, so this handles that safely and lets the gui know if the wx controller is still running
class FrameSplashStatus( object ):
    
    def __init__( self, controller, ui ):
        
        self._controller = controller
        self._ui = ui
        
        self._lock = threading.Lock()
        
        self._title_text = ''
        self._status_text = ''
        self._status_subtext = ''
        
        self._controller.sub( self, 'SetTitleText', 'splash_set_title_text' )
        self._controller.sub( self, 'SetText', 'splash_set_status_text' )
        self._controller.sub( self, 'SetSubtext', 'splash_set_status_subtext' )
        
    
    def _NotifyUI( self ):
        
        def wx_code():
            
            if not self._ui:
                
                return
                
            
            self._ui.SetDirty()
            
        
        wx.CallAfter( wx_code )
        
    
    def GetTexts( self ):
        
        with self._lock:
            
            return ( self._title_text, self._status_text, self._status_subtext )
            
        
    
    def SetText( self, text, print_to_log = True ):
        
        if print_to_log and len( text ) > 0:
            
            HydrusData.Print( text )
            
        
        with self._lock:
            
            self._status_text = text
            self._status_subtext = ''
            
        
        self._NotifyUI()
        
    
    def SetSubtext( self, text ):
        
        with self._lock:
            
            self._status_subtext = text
            
        
        self._NotifyUI()
        
    
    def SetTitleText( self, text, print_to_log = True ):
        
        if print_to_log:
            
            HydrusData.DebugPrint( text )
            
        
        with self._lock:
            
            self._title_text = text
            self._status_text = ''
            self._status_subtext = ''
            
        
        self._NotifyUI()
        
    
class FrameSplash( wx.Frame ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        style = wx.CAPTION
        
        wx.Frame.__init__( self, None, style = style, title = 'hydrus client' )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self._my_panel = FrameSplashPanel( self, self._controller )
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._vbox.Add( self._my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( self._vbox )
        
        self.Fit()
        
        self.Center()
        
        self.Show( True )
        
        self.Raise()
        
    
    def CancelShutdownMaintenance( self ):
        
        self._cancel_shutdown_maintenance.SetLabelText( 'stopping\u2026' )
        self._cancel_shutdown_maintenance.Disable()
        
        HG.do_idle_shutdown_work = False
        
    
    def MakeCancelShutdownButton( self ):
        
        self._cancel_shutdown_maintenance = ClientGUICommon.BetterButton( self, 'stop shutdown maintenance', self.CancelShutdownMaintenance )
        
        self._vbox.Insert( 0, self._cancel_shutdown_maintenance, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.Fit()
        
    
