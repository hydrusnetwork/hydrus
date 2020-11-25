import collections
import gc
import hashlib
import os
import random
import re
import ssl
import subprocess
import sys
import threading
import time
import traceback

import cv2
import PIL
import sqlite3

import qtpy
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPaths
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNetwork
from hydrus.core import HydrusNetworking
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusVideoHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientExporting
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client import ClientRendering
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDownloaders
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIExport
from hydrus.client.gui import ClientGUIFrames
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIImport
from hydrus.client.gui import ClientGUILogin
from hydrus.client.gui import ClientGUIManagement
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIMPV
from hydrus.client.gui import ClientGUINetwork
from hydrus.client.gui import ClientGUIPages
from hydrus.client.gui import ClientGUIParsing
from hydrus.client.gui import ClientGUIPopupMessages
from hydrus.client.gui import ClientGUIServices
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsManagement
from hydrus.client.gui import ClientGUIScrolledPanelsReview
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIShortcutControls
from hydrus.client.gui import ClientGUISplash
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import ClientGUISubscriptions
from hydrus.client.gui import ClientGUISystemTray
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts

MENU_ORDER = [ 'file', 'undo', 'pages', 'database', 'network', 'services', 'tags', 'pending', 'help' ]

def THREADUploadPending( service_key ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        service_name = service.GetName()
        service_type = service.GetServiceType()
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'uploading pending to ' + service_name )
        
        nums_pending = HG.client_controller.Read( 'nums_pending' )
        
        info = nums_pending[ service_key ]
        
        initial_num_pending = sum( info.values() )
        
        result = HG.client_controller.Read( 'pending', service_key )
        
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
                    
                    if isinstance( result, ClientMediaResult.MediaResult ):
                        
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
                    
                    if isinstance( result, ClientMediaResult.MediaResult ):
                        
                        media_result = result
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        try:
                            
                            service.PinFile( hash, mime )
                            
                        except HydrusExceptions.DataMissing:
                            
                            HydrusData.ShowText( 'File {} could not be pinned!'.format( hash.hexh() ) )
                            
                            continue
                            
                        
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
        
        if service_type == HC.TAG_REPOSITORY:
            
            types_to_clear = (
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS
            )
            
        elif service_type in ( HC.FILE_REPOSITORY, HC.IPFS ):
            
            types_to_clear = (
                HC.SERVICE_INFO_NUM_PENDING_FILES,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES
            )
            
        
        HG.client_controller.Write( 'delete_service_info', service_key, types_to_clear )
        
        HG.currently_uploading_pending = False
        HG.client_controller.pub( 'notify_new_pending' )
        
    
class FrameGUI( ClientGUITopLevelWindows.MainFrameThatResizes ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        title = self._controller.new_options.GetString( 'main_gui_title' )
        
        if title is None or title == '':
            
            title = 'hydrus client'
            
        
        ClientGUITopLevelWindows.MainFrameThatResizes.__init__( self, None, title, 'main_gui' )
        
        self._currently_minimised_to_system_tray = False
        
        bandwidth_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 17 )
        idle_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 6 )
        hydrus_busy_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 11 )
        system_busy_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 13 )
        db_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 14 )
        
        self._statusbar = QP.StatusBar( [ -1, bandwidth_width, idle_width, hydrus_busy_width, system_busy_width, db_width ] )
        self._statusbar.setSizeGripEnabled( True )
        self.setStatusBar( self._statusbar )
        
        self._statusbar_thread_updater = ClientGUIAsync.FastThreadToGUIUpdater( self._statusbar, self.RefreshStatusBar )
        
        self._canvas_frames = [] # Keep references to canvas frames so they won't get garbage collected (canvas frames don't have a parent)
        
        self._persistent_mpv_widgets = []
        
        self._closed_pages = []
        
        self._lock = threading.Lock()
        
        self._delayed_dialog_lock = threading.Lock()
        
        self._last_total_page_weight = None
        
        self._first_session_loaded = False
        
        self._done_save_and_close = False
        
        self._notebook = ClientGUIPages.PagesNotebook( self, self._controller, 'top page notebook' )
        
        self._garbage_snapshot = collections.Counter()
        
        self._last_clipboard_watched_text = ''
        self._clipboard_watcher_destination_page_watcher = None
        self._clipboard_watcher_destination_page_urls = None
        
        drop_target = ClientGUIDragDrop.FileDropTarget( self, self.ImportFiles, self.ImportURLFromDragAndDrop, self._notebook.MediaDragAndDropDropped )
        self.installEventFilter( ClientGUIDragDrop.FileDropTarget( self, self.ImportFiles, self.ImportURLFromDragAndDrop, self._notebook.MediaDragAndDropDropped ) )
        self._notebook.AddSupplementaryTabBarDropTarget( drop_target ) # ugly hack to make the case of files/media dropped onto a tab work
        
        self._message_manager = ClientGUIPopupMessages.PopupMessageManager( self )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventFrameNewPage )
        self._widget_event_filter.EVT_MIDDLE_DOWN( self.EventFrameNewPage )
        self._widget_event_filter.EVT_ICONIZE( self.EventIconize )
        
        self._widget_event_filter.EVT_MOVE( self.EventMove )
        self._last_move_pub = 0.0
        
        self._controller.sub( self, 'AddModalMessage', 'modal_message' )
        self._controller.sub( self, 'DeleteOldClosedPages', 'delete_old_closed_pages' )
        self._controller.sub( self, 'DoFileStorageRebalance', 'do_file_storage_rebalance' )
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
        self._controller.sub( self, 'SetStatusBarDirty', 'set_status_bar_dirty' )
        self._controller.sub( self, 'SetTitle', 'main_gui_title' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setCentralWidget( QW.QWidget() )
        self.centralWidget().setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self._was_maximised = self.isMaximized()
        
        self._InitialiseMenubar()
        
        self._RefreshStatusBar()
        
        self._bandwidth_repeating_job = self._controller.CallRepeatingQtSafe(self, 1.0, 1.0, self.REPEATINGBandwidth)
        
        self._page_update_repeating_job = self._controller.CallRepeatingQtSafe(self, 0.25, 0.25, self.REPEATINGPageUpdate)
        
        self._clipboard_watcher_repeating_job = None
        
        self._ui_update_repeating_job = None
        
        self._ui_update_windows = set()
        
        self._animation_update_timer = QC.QTimer( self )
        self._animation_update_timer.setTimerType( QC.Qt.PreciseTimer )
        self._animation_update_timer.timeout.connect( self.TIMEREventAnimationUpdate )
        
        self._animation_update_windows = set()
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'main_gui' ] )
        
        self._system_tray_hidden_tlws = []
        self._have_system_tray_icon = False
        self._system_tray_icon = None
        
        self._have_shown_once = False
        
        if self._controller.new_options.GetBoolean( 'start_client_in_system_tray' ):
            
            self._currently_minimised_to_system_tray = True
            
            self.hide()
            
            self._system_tray_hidden_tlws.append( ( self.isMaximized(), self ) )
            
        else:
            
            self.show()
            
            self._have_shown_once = True
            
        
        self._UpdateSystemTrayIcon( currently_booting = True )
        
        self._controller.CallLaterQtSafe( self, 0.5, self._InitialiseSession ) # do this in callafter as some pages want to talk to controller.gui, which doesn't exist yet!
        
    
    def _AboutWindow( self ):
        
        aboutinfo = QP.AboutDialogInfo()
        
        aboutinfo.SetName( 'hydrus client' )
        aboutinfo.SetVersion( str( HC.SOFTWARE_VERSION ) + ', using network version ' + str( HC.NETWORK_VERSION ) )
        
        library_versions = []
        
        # 2.7.12 (v2.7.12:d33e0cf91556, Jun 27 2016, 15:24:40) [MSC v.1500 64 bit (AMD64)]
        v = sys.version
        
        if ' ' in v:
            
            v = v.split( ' ' )[0]
            
        
        library_versions.append( ( 'python', v ) )
        library_versions.append( ( 'openssl', ssl.OPENSSL_VERSION ) )
        
        library_versions.append( ( 'OpenCV', cv2.__version__ ) )
        library_versions.append( ( 'Pillow', PIL.__version__ ) )
        
        if HC.RUNNING_FROM_FROZEN_BUILD and HC.PLATFORM_MACOS:
            
            library_versions.append( ( 'mpv: ', 'is not currently available on macOS' ) )
            
        else:
            
            if ClientGUIMPV.MPV_IS_AVAILABLE:
                
                library_versions.append( ( 'mpv api version: ', ClientGUIMPV.GetClientAPIVersionString() ) )
                
            else:
                
                HydrusData.ShowText( 'If this information helps, MPV failed to import because:' )
                HydrusData.ShowText( ClientGUIMPV.mpv_failed_reason )
                
                library_versions.append( ( 'mpv', 'not available' ) )
                
            
        
        library_versions.append( ( 'FFMPEG', HydrusVideoHandling.GetFFMPEGVersion() ) )
        
        library_versions.append( ( 'sqlite', sqlite3.sqlite_version ) )
        
        library_versions.append( ( 'Qt', QC.__version__ ) )
        
        if qtpy.PYSIDE2:
            
            import PySide2
            import shiboken2
            
            library_versions.append( ( 'PySide2', PySide2.__version__ ) )
            library_versions.append( ( 'shiboken2', shiboken2.__version__ ) )
            
        elif qtpy.PYQT5:

            from PyQt5.Qt import PYQT_VERSION_STR # pylint: disable=E0401
            from sip import SIP_VERSION_STR # pylint: disable=E0401

            library_versions.append( ( 'PyQt5', PYQT_VERSION_STR ) )
            library_versions.append( ( 'sip', SIP_VERSION_STR ) )
            
        
        from hydrus.client.networking import ClientNetworkingJobs
        
        if ClientNetworkingJobs.CLOUDSCRAPER_OK:
            
            library_versions.append( ( 'cloudscraper', ClientNetworkingJobs.cloudscraper.__version__ ) )
            
        else:
            
            library_versions.append( ( 'cloudscraper present: ', 'False' ) )
            
        
        library_versions.append( ( 'pyparsing present: ', str( ClientNetworkingJobs.PYPARSING_OK ) ) )
        library_versions.append( ( 'html5lib present: ', str( ClientParsing.HTML5LIB_IS_OK ) ) )
        library_versions.append( ( 'lxml present: ', str( ClientParsing.LXML_IS_OK ) ) )
        library_versions.append( ( 'lz4 present: ', str( ClientRendering.LZ4_OK ) ) )
        library_versions.append( ( 'install dir', HC.BASE_DIR ) )
        library_versions.append( ( 'db dir', HG.client_controller.db_dir ) )
        library_versions.append( ( 'temp dir', HydrusPaths.GetCurrentTempDir() ) )
        
        import locale
        
        l_string = locale.getlocale()[0]
        qtl_string = QC.QLocale().name()
        
        library_versions.append( ( 'locale strings', str( ( l_string, qtl_string ) ) ) )
        
        description = 'This client is the media management application of the hydrus software suite.'
        
        description += os.linesep * 2 + os.linesep.join( ( lib + ': ' + version for ( lib, version ) in library_versions ) )
        
        aboutinfo.SetDescription( description )
        
        if os.path.exists( HC.LICENSE_PATH ):
            
            with open( HC.LICENSE_PATH, 'r', encoding = 'utf-8' ) as f:
                
                license = f.read()
                
            
        else:
            
            license = 'no licence file found!'
            
        
        aboutinfo.SetLicense( license )
        
        aboutinfo.SetDevelopers( [ 'Anonymous' ] )
        aboutinfo.SetWebSite( 'https://hydrusnetwork.github.io/hydrus/' )
        
        QP.AboutBox( self, aboutinfo )
        
    
    def _AccountInfo( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account\'s account key.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                subject_account_key = bytes.fromhex( dlg.GetValue() )
                
                service = self._controller.services_manager.GetService( service_key )
                
                response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : subject_account_key } )
                
                account_info = response[ 'account_info' ]
                
                QW.QMessageBox.information( self, 'Information', str(account_info) )
                
            
        
    
    def _AnalyzeDatabase( self ):
        
        message = 'This will gather statistical information on the database\'s indices, helping the query planner perform efficiently. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        message += os.linesep * 2
        message += 'A \'soft\' analyze will only reanalyze those indices that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        message += os.linesep * 2
        message += 'A \'full\' analyze will force a run over every index in the database. This can take substantially longer. If you do not have a specific reason to select this, it is probably pointless.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose how thorough your analyze will be.', yes_label = 'soft', no_label = 'full', check_for_cancelled = True )
        
        if was_cancelled:
            
            return
            
        
        if result == QW.QDialog.Accepted:
            
            stop_time = HydrusData.GetNow() + 120
            
            self._controller.Write( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = stop_time )
            
        elif result == QW.QDialog.Rejected:
            
            self._controller.Write( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, force_reanalyze = True )
            
        
    
    def _AutoRepoSetup( self ):
        
        host = 'ptr.hydrus.network'
        port = 45871
        access_key = bytes.fromhex( '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f' )
        
        ptr_credentials = HydrusNetwork.Credentials( host = host, port = port, access_key = access_key )
        
        def do_it():
            
            all_services = list( self._controller.services_manager.GetServices() )
            
            all_names = [ s.GetName() for s in all_services ]
            
            name = HydrusData.GetNonDupeName( 'public tag repository', all_names )
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.TAG_REPOSITORY
            
            public_tag_repo = ClientServices.GenerateService( service_key, service_type, name )
            
            public_tag_repo.SetCredentials( ptr_credentials )
            
            all_services.append( public_tag_repo )
            
            self._controller.SetServices( all_services )
            
            message = 'PTR setup done! Check services->review services to see it.'
            message += os.linesep * 2
            message += 'The PTR has a lot of tags and will sync a little bit at a time when you are not using the client. Expect it to take a few weeks to sync fully.'
            
            HydrusData.ShowText( message )
            
        
        have_it_already = False
        
        services = self._controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        for service in services:
            
            credentials = service.GetCredentials()
            
            if credentials.GetSerialisableTuple() == ptr_credentials.GetSerialisableTuple():
                
                have_it_already = True
                
                break
                
            
        
        text = 'This will automatically set up your client with the Public Tag Repository, just as if you had added it manually under services->manage services.'
        text += os.linesep * 2
        text += 'Be aware that the PTR has been growing since 2011 and now has hundreds of millions of mappings. As of 2020-03, it requires about 4GB of bandwidth and file storage, and your database itself will grow by 25GB! Processing also takes a lot of CPU and HDD work, and, due to the unavoidable mechanical latency of HDDs, will only work in reasonable time if your hydrus database is on an SSD.'
        text += os.linesep * 2
        text += 'If you are on a mechanical HDD or do not have the space on your SSD, cancel out now.'
        
        if have_it_already:
            
            text += os.linesep * 2
            text += 'You seem to have the PTR already. If it is paused or desynchronised, this is best fixed under services->review services. Are you sure you want to add a duplicate?'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'not now' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.CallToThread( do_it )
            
        
    
    def _BackupDatabase( self ):
        
        path = self._new_options.GetNoneableString( 'backup_path' )
        
        if path is None:
            
            QW.QMessageBox.warning( self, 'Warning', 'No backup path is set!' )
            
            return
            
        
        if not os.path.exists( path ):
            
            QW.QMessageBox.information( self, 'Information', 'The backup path does not exist--creating it now.' )
            
            HydrusPaths.MakeSureDirectoryExists( path )
            
        
        client_db_path = os.path.join( path, 'client.db' )
        
        if os.path.exists( client_db_path ):
            
            action = 'Update the existing'
            
        else:
            
            action = 'Create a new'
            
        
        text = action + ' backup at "' + path + '"?'
        text += os.linesep * 2
        text += 'The database will be locked while the backup occurs, which may lock up your gui as well.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            session = self._notebook.GetCurrentGUISession( 'last session' )
            
            self._controller.SaveGUISession( session )
            
            session.SetName( 'exit session' )
            
            self._controller.SaveGUISession( session )
            
            self._controller.Write( 'backup', path )
            
        
    
    def _BackupServer( self, service_key ):
        
        def do_it( service ):
            
            started = HydrusData.GetNow()
            
            service.Request( HC.POST, 'backup' )
            
            HydrusData.ShowText( 'Server backup started!' )
            
            time.sleep( 10 )
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            while result_bytes == b'1':
                
                if HG.view_shutdown:
                    
                    return
                    
                
                time.sleep( 10 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusData.GetNow() - started
            
            HydrusData.ShowText( 'Server backup done in ' + HydrusData.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and copy its database files. It will probably take a few minutes to complete, during which time it will not be able to serve any requests.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def _CheckDBIntegrity( self ):
        
        message = 'This will check the database for missing and invalid entries. It may take several minutes to complete.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Run integrity check?', yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
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
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADVANCED, 'clear' )
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
            
            self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            QW.QMessageBox.information( self, 'Information', 'Delete done! Please restart the client to see the changes in the UI.' )
            
        
    
    def _ClearOrphanFiles( self ):
        
        text = 'This will iterate through every file in your database\'s file storage, removing any it does not expect to be there. It may take some time.'
        text += os.linesep * 2
        text += 'Files and thumbnails will be inaccessible while this occurs, so it is best to leave the client alone until it is done.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            text = 'What would you like to do with the orphaned files? Note that all orphaned thumbnails will be deleted.'
            
            client_files_manager = self._controller.client_files_manager
            
            ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Choose what do to with the orphans.', yes_label = 'move them somewhere', no_label = 'delete them', check_for_cancelled = True )
            
            if was_cancelled:
                
                return
                
            
            if result == QW.QDialog.Accepted:
                
                with QP.DirDialog( self, 'Select location.' ) as dlg_3:
                    
                    if dlg_3.exec() == QW.QDialog.Accepted:
                        
                        path = dlg_3.GetPath()
                        
                        self._controller.CallToThread( client_files_manager.ClearOrphans, path )
                        
                    
                
            elif result == QW.QDialog.Rejected:
                
                self._controller.CallToThread( client_files_manager.ClearOrphans )
                
            
        
    
    def _ClearOrphanFileRecords( self ):
        
        text = 'This will instruct the database to review its file records and delete any orphans. You typically do not ever see these files and they are basically harmless, but they can offset some file counts confusingly. You probably only need to run this if you can\'t process the apparent last handful of duplicate filter pairs or hydrus dev otherwise told you to try it.'
        text += os.linesep * 2
        text += 'It will create a popup message while it works and inform you of the number of orphan records found.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'clear_orphan_file_records' )
            
        
    
    def _ClearOrphanTables( self ):
        
        text = 'This will instruct the database to review its service tables and delete any orphans. This will typically do nothing, but hydrus dev may tell you to run this, just to check. Be sure you have a semi-recent backup before you run this.'
        text += os.linesep * 2
        text += 'It will create popups if it finds anything to delete.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'clear_orphan_tables' )
            
        
    
    def _CullFileViewingStats( self ):
        
        text = 'If your file viewing statistics have some erroneous values due to many short views or accidental long views, this routine will cull your current numbers to compensate. For instance:'
        text += os.linesep * 2
        text += 'If you have a file with 100 views over 100 seconds and a minimum view time of 2 seconds, this will cull the views to 50.'
        text += os.linesep * 2
        text += 'If you have a file with 10 views over 100000 seconds and a maximum view time of 60 seconds, this will cull the total viewtime to 600 seconds.'
        text += os.linesep * 2
        text += 'It will work for both preview and media views based on their separate rules.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.WriteSynchronous( 'cull_file_viewing_statistics' )
            
            QW.QMessageBox.information( self, 'Information', 'Cull done! Please restart the client to see the changes in the UI.' )
            
        
    
    def _CurrentlyMinimisedOrHidden( self ):
        
        return self.isMinimized() or self._currently_minimised_to_system_tray
        
    
    def _DebugFetchAURL( self ):
        
        def qt_code( network_job ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            content = network_job.GetContentBytes()
            
            text = 'Request complete. Length of response is ' + HydrusData.ToHumanBytes( len( content ) ) + '.'
            
            yes_tuples = []
            
            yes_tuples.append( ( 'save to file', 'file' ) )
            yes_tuples.append( ( 'copy to clipboard', 'clipboard' ) )
            
            with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    value = dlg.GetValue()
                    
                    if value == 'file':
                        
                        with QP.FileDialog( self, 'select where to save content', default_filename = 'result.html', acceptMode = QW.QFileDialog.AcceptSave, fileMode = QW.QFileDialog.AnyFile ) as f_dlg:
                            
                            if f_dlg.exec() == QW.QDialog.Accepted:
                                
                                path = f_dlg.GetPath()
                                
                                with open( path, 'wb' ) as f:
                                    
                                    f.write( content )
                                    
                                
                            
                        
                    elif value == 'clipboard':
                        
                        text = network_job.GetContentText()
                        
                        self._controller.pub( 'clipboard', 'text', text )
                        
                    
                
            
        
        def thread_wait( url ):
            
            from hydrus.client.networking import ClientNetworkingJobs
            
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
                
            
            QP.CallAfter( qt_code, network_job )
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the URL.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url = dlg.GetValue()
                
                self._controller.CallToThread( thread_wait, url )
                
            
        
    
    def _DebugMakeDelayedModalPopup( self, cancellable ):
        
        def do_it( controller, cancellable ):
            
            time.sleep( 5 )
            
            job_key = ClientThreading.JobKey( cancellable = cancellable )
            
            job_key.SetVariable( 'popup_title', 'debug modal job' )
            
            controller.pub( 'modal_message', job_key )
            
            for i in range( 10 ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                job_key.SetVariable( 'popup_text_1', 'Will auto-dismiss in ' + HydrusData.TimeDeltaToPrettyTimeDelta( 10 - i ) + '.' )
                job_key.SetVariable( 'popup_gauge_1', ( i, 10 ) )
                
                time.sleep( 1 )
                
            
            job_key.Delete()
            
        
        self._controller.CallToThread( do_it, self._controller, cancellable )
        
    
    def _DebugLongTextPopup( self ):
        
        words = [ 'test', 'a', 'longish', 'statictext', 'm8' ]
        
        text = random.choice( words )
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', text )
        
        self._controller.pub( 'message', job_key )
        
        t = 0
        
        for i in range( 2, 64 ):
            
            text += ' {}'.format( random.choice( words ) )
            
            t += 0.2
            
            self._controller.CallLater( t, job_key.SetVariable, 'popup_text_1', text )
            
        
        words = [ 'test', 'a', 'longish', 'statictext', 'm8' ]
        
        text = random.choice( words )
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'test long title' )
        
        self._controller.pub( 'message', job_key )
        
        for i in range( 2, 64 ):
            
            text += ' {}'.format( random.choice( words ) )
            
            t += 0.2
            
            self._controller.CallLater( t, job_key.SetVariable, 'popup_title', text )
            
        
    
    def _DebugMakeParentlessTextCtrl( self ):
        
        with QP.Dialog( None, title = 'parentless debug dialog' ) as dlg:
            
            control = QW.QLineEdit( dlg )
            
            control.setText( 'debug test input' )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, control, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dlg.setLayout( vbox )
            
            dlg.exec()
            
        
    
    def _DebugMakeSomePopups( self ):
        
        for i in range( 1, 7 ):
            
            HydrusData.ShowText( 'This is a test popup message -- ' + str( i ) )
            
        
        brother_classem_pinniped = '''++++What the fuck did you just fucking say about me, you worthless heretic? I'll have you know I graduated top of my aspirant tournament in the Heralds of Ultramar, and I've led an endless crusade of secret raids against the forces of The Great Enemy, and I have over 30 million confirmed purgings. I am trained in armored warfare and I'm the top brother in all the thousand Divine Chapters of the Adeptus Astartes. You are nothing to me but just another heretic. I will wipe you the fuck out with precision the likes of which has never been seen before in this universe, mark my fucking words. You think you can get away with saying that shit to me over the Warp? Think again, traitor. As we speak I am contacting my secret network of inquisitors across the galaxy and your malign powers are being traced right now so you better prepare for the holy storm, maggot. The storm that wipes out the pathetic little thing you call your soul. You're fucking dead, kid. I can warp anywhere, anytime, and I can kill you in over seven hundred ways, and that's just with my bolter. Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the Departmento Munitorum and I will use it to its full extent to wipe your miserable ass off the face of the galaxy, you little shit. If only you could have known what holy retribution your little "clever" comment was about to bring down upon you, maybe you would have held your fucking impure tongue. But you couldn't, you didn't, and now you're paying the price, you Emperor-damned heretic.++++\n\n++++Better crippled in body than corrupt in mind++++\n\n++++The Emperor Protects++++'''
        
        HydrusData.ShowText( 'This is a very long message:  \n\n' + brother_classem_pinniped )
        
        #
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', 'This popup has a very long title -- it is a subscription that is running with a long "artist sub 123456" kind of name' )
        
        job_key.SetVariable( 'popup_text_1', 'test' )
        
        self._controller.pub( 'message', job_key )
        
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
            
        
    
    def _DebugShowGarbageDifferences( self ):
        
        count = collections.Counter()
        
        for o in gc.get_objects():
            
            count[ type( o ) ] += 1
            
        
        count.subtract( self._garbage_snapshot )
        
        text = 'Garbage differences start here:'
        
        to_print = list( count.items() )
        
        to_print.sort( key = lambda pair: -pair[1] )
        
        for ( t, count ) in to_print:
            
            if count == 0:
                
                continue
                
            
            text += os.linesep + '{}: {}'.format( t, HydrusData.ToHumanInt( count ) )
            
        
        HydrusData.ShowText( text )
        
    
    def _DebugTakeGarbageSnapshot( self ):
        
        count = collections.Counter()
        
        for o in gc.get_objects():
            
            count[ type( o ) ] += 1
            
        
        self._garbage_snapshot = count
        
    
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
        
        objects_to_inspect = set()
        
        for o in gc.get_objects():
            
            # add objects to inspect here
            
            count[ type( o ) ] += 1
            
        
        current_frame = sys._getframe( 0 )
        
        for o in objects_to_inspect:
            
            HydrusData.Print( o )
            
            parents = gc.get_referrers( o )
            
            for parent in parents:
                
                if parent == current_frame or parent == objects_to_inspect:
                    
                    continue
                    
                
                HydrusData.Print( 'parent {}'.format( parent ) )
                
                grandparents = gc.get_referrers( parent )
                
                for gp in grandparents:
                    
                    if gp == current_frame or gp == parents:
                        
                        continue
                        
                    
                    HydrusData.Print( 'grandparent {}'.format( gp ) )
                    
                
            
            
        
        HydrusData.Print( 'currently tracked types:' )
        
        to_print = list( count.items() )
        
        to_print.sort( key = lambda pair: -pair[1] )
        
        for ( k, v ) in to_print:
            
            if v > 15:
                
                HydrusData.Print( ( k, v ) )
                
            
        
        HydrusData.DebugPrint( 'garbage printing finished' )
        
    
    def _DebugShowScheduledJobs( self ):
        
        self._controller.DebugShowScheduledJobs()
        
    
    def _DeleteGUISession( self, name ):
        
        message = 'Delete session "' + name + '"?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Delete session?' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
            
            self._controller.pub( 'notify_new_sessions' )
            
        
    
    def _DeletePending( self, service_key ):
        
        service_name = self._controller.services_manager.GetName( service_key )
        
        message = 'Are you sure you want to delete the pending data for {}?'.format( service_name )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'delete_pending', service_key )
            
        
    
    def _DeleteServiceInfo( self ):
        
        message = 'This clears the cached counts for things like the number of files or tags on a service. Due to unusual situations and little counting bugs, these numbers can sometimes become unsynced. Clearing them forces an accurate recount from source.'
        message += os.linesep * 2
        message += 'Some GUI elements (review services, mainly) may be slow the next time they launch.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'delete_service_info' )
            
        
    
    def _DestroyPages( self, pages ):
        
        for page in pages:
            
            if page and QP.isValid( page ):
                
                page.CleanBeforeDestroy()
                
                page.deleteLater()
                
            
        
    
    def _DestroyTimers( self ):
        
        if self._animation_update_timer is not None:
            
            self._animation_update_timer.stop()
            
            self._animation_update_timer = None
            
        
    
    def _EnableLoadTruncatedImages( self ):
        
        result = HydrusImageHandling.EnableLoadTruncatedImages()
        
        if not result:
            
            QW.QMessageBox.critical( self, 'Error', 'Could not turn on--perhaps your version of PIL does not support it?' )
            
        
    
    def _ExportDownloader( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export downloaders' ) as dlg:
            
            panel = ClientGUIParsing.DownloaderExportPanel( dlg, self._controller.network_engine )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _FetchIP( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the file\'s hash.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                hash = bytes.fromhex( dlg.GetValue() )
                
                service = self._controller.services_manager.GetService( service_key )
                
                with QP.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash } )
                
                ip = response[ 'ip' ]
                timestamp = response[ 'timestamp' ]
                
                gmt_time = HydrusData.ConvertTimestampToPrettyTime( timestamp, in_utc = True )
                local_time = HydrusData.ConvertTimestampToPrettyTime( timestamp )
                
                text = 'File Hash: ' + hash.hex()
                text += os.linesep
                text += 'Uploader\'s IP: ' + ip
                text += 'Upload Time (GMT): ' + gmt_time
                text += 'Upload Time (Your time): ' + local_time
                
                HydrusData.Print( text )
                
                QW.QMessageBox.information( self, 'Information', text+os.linesep*2+'This has been written to the log.' )
                
            
        
    
    def _FindMenuBarIndex( self, name ):
        
        for index in range( len( self._menubar.actions() ) ):
            
            if self._menubar.actions()[ index ].property( 'hydrus_menubar_name' ) == name:
                
                return index
                
            
        
        return -1
        
    
    def _FlipClipboardWatcher( self, option_name ):
        
        self._controller.new_options.FlipBoolean( option_name )
        
        self._last_clipboard_watched_text = ''
        
        if self._clipboard_watcher_repeating_job is None:
            
            self._clipboard_watcher_repeating_job = self._controller.CallRepeatingQtSafe(self, 1.0, 1.0, self.REPEATINGClipboardWatcher)
            
        
    
    def _FlipShowHideWholeUI( self ):
        
        if not self._currently_minimised_to_system_tray:
            
            visible_tlws = [ tlw for tlw in QW.QApplication.topLevelWidgets() if tlw.isVisible() or tlw.isMinimized() ]
            
            visible_dialogs = [ tlw for tlw in visible_tlws if isinstance( tlw, QW.QDialog ) ]
            
            if len( visible_dialogs ) > 0:
                
                dialog = visible_dialogs[ -1 ]
                
                dialog.activateWindow()
                
                return
                
            
            page = self.GetCurrentPage()
            
            if page is not None:
                
                page.PageHidden()
                
            
            HG.client_controller.pub( 'pause_all_media' )
            
            for tlw in visible_tlws:
                
                tlw.hide()
                
                self._system_tray_hidden_tlws.append( ( tlw.isMaximized(), tlw ) )
                
            
        else:
            
            for ( was_maximised, tlw ) in self._system_tray_hidden_tlws:
                
                if QP.isValid( tlw ):
                    
                    tlw.show()
                    
                
            
            self._have_shown_once = True
            
            page = self.GetCurrentPage()
            
            if page is not None:
                
                page.PageShown()
                
            
            self._system_tray_hidden_tlws = []
            
            self.RestoreOrActivateWindow()
            
        
        self._currently_minimised_to_system_tray = not self._currently_minimised_to_system_tray
        
        self._UpdateSystemTrayIcon()
        
    
    def _GenerateNewAccounts( self, service_key ):
        
        with ClientGUIDialogs.DialogGenerateNewAccounts( self, service_key ) as dlg: dlg.exec()
        
    
    def _HowBonedAmI( self ):
        
        self._controller.file_viewing_stats_manager.Flush()
        
        self._boned_updater.update()
        
    
    def _ImportDownloaders( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'import downloaders' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewDownloaderImport( frame, self._controller.network_engine )
        
        frame.SetPanel( panel )
        
    
    def _ImportFiles( self, paths = None ):
        
        if paths is None:
            
            paths = []
            
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'importing files' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewLocalFileImports( frame, paths )
        
        frame.SetPanel( panel )
        
    
    def _ImportUpdateFiles( self ):
        
        def do_it( external_update_dir ):
            
            num_errors = 0
            
            filenames = os.listdir( external_update_dir )
            
            update_paths = [ os.path.join( external_update_dir, filename ) for filename in filenames ]
            
            update_paths = list(filter( os.path.isfile, update_paths ))
            
            num_to_do = len( update_paths )
            
            if num_to_do == 0:
                
                QP.CallAfter( QW.QMessageBox.warning, self, 'Warning', 'No files in that directory!' )
                
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
        
        QW.QMessageBox.information( self, 'Information', message )
        
        with QP.DirDialog( self, 'Select location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                self._controller.CallToThread( do_it, path )
                
            
        
    
    def _ImportURL(
        self,
        url,
        filterable_tags = None,
        additional_service_keys_to_tags = None,
        destination_page_name = None,
        destination_page_key = None,
        show_destination_page = True,
        allow_watchers = True,
        allow_other_recognised_urls = True,
        allow_unrecognised_urls = True
        ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
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
            
            page = self._notebook.GetOrMakeURLImportPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                management_panel = page.GetManagementPanel()
                
                management_panel.PendURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        elif url_type == HC.URL_TYPE_WATCHABLE and allow_watchers:
            
            url_caught = True
            
            page = self._notebook.GetOrMakeMultipleWatcherPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                management_panel = page.GetManagementPanel()
                
                management_panel.PendURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        
        if url_caught:
            
            raise HydrusExceptions.DataMissing( '"{}" URL was accepted but not added successfully--could not find/generate a new downloader page for it.'.format( match_name ) )
            
        
    
    def _InitialiseMenubarGetBonesUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable():
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_text_1', 'Loading Statistics\u2026' )
            
            HG.client_controller.pub( 'message', job_key )
            
            boned_stats = HG.client_controller.Read( 'boned_stats' )
            
            return ( job_key, boned_stats )
            
        
        def publish_callable( result ):
            
            ( job_key, boned_stats ) = result
            
            job_key.Delete()
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review your fate' )
            
            panel = ClientGUIScrolledPanelsReview.ReviewHowBonedAmI( frame, boned_stats )
            
            frame.SetPanel( panel )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetFileMenuUpdater( self ):
        
        def loading_callable():
            
            self.DisableMenu( 'file' )
            
        
        def work_callable():
            
            import_folder_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            export_folder_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            return ( import_folder_names, export_folder_names )
            
        
        def publish_callable( result ):
            
            ( import_folder_names, export_folder_names ) = result
            
            ( menu, label ) = self.GenerateMenuInfoFile( import_folder_names, export_folder_names )
            
            self.ReplaceMenu( 'file', menu, label )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetPagesMenuUpdater( self ):
        
        def loading_callable():
            
            self.DisableMenu( 'pages' )
            
        
        def work_callable():
            
            gui_session_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            if len( gui_session_names ) > 0:
                
                gui_session_names_to_backup_timestamps = HG.client_controller.Read( 'serialisable_names_to_backup_timestamps', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
                
            else:
                
                gui_session_names_to_backup_timestamps = {}
                
            
            return ( gui_session_names, gui_session_names_to_backup_timestamps )
            
        
        def publish_callable( result ):
            
            ( gui_session_names, gui_session_names_to_backup_timestamps ) = result
            
            ( menu, label ) = self.GenerateMenuInfoPages( gui_session_names, gui_session_names_to_backup_timestamps )
            
            self.ReplaceMenu( 'pages', menu, label )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetPendingMenuUpdater( self ):
        
        def loading_callable():
            
            self.DisableMenu( 'pending' )
            
        
        def work_callable():
            
            nums_pending = HG.client_controller.Read( 'nums_pending' )
            
            return nums_pending
            
        
        def publish_callable( result ):
            
            nums_pending = result
            
            ( menu_or_none, label ) = self.GenerateMenuInfoPending( nums_pending )
            
            self.ReplaceMenu( 'pending', menu_or_none, label )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubar( self ):
        
        self._menubar = QW.QMenuBar( self )
        
        self._menubar.setNativeMenuBar( False )
        
        self._menu_updater = ClientGUIAsync.FastThreadToGUIUpdater( self._menubar, self.RefreshMenu )
        self._dirty_menus = set()
        
        self._menu_updater_file = self._InitialiseMenubarGetFileMenuUpdater()
        self._menu_updater_pages = self._InitialiseMenubarGetPagesMenuUpdater()
        self._menu_updater_pending = self._InitialiseMenubarGetPendingMenuUpdater()
        
        self._boned_updater = self._InitialiseMenubarGetBonesUpdater()
        
        self.setMenuBar( self._menubar )
        
        for name in MENU_ORDER:
            
            if name == 'file':
                
                self._menu_updater_file.update()
                
            elif name == 'pages':
                
                self._menu_updater_pages.update()
                
            elif name == 'pending':
                
                self._menu_updater_pending.update()
                
            else:
                
                ( menu_or_none, label ) = self.GenerateMenuInfo( name )
                
                self.ReplaceMenu( name, menu_or_none, label )
                
            
        
    
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
                message += os.linesep * 2
                message += 'This will auto-choose to open your default session in 15 seconds.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Previous shutdown was bad', yes_label = 'try to load "' + default_gui_session + '"', no_label = 'just load a blank page', auto_yes_time = 15 )
                
                if result == QW.QDialog.Rejected:
                    
                    load_a_blank_page = True
                    
                
            
        
        def do_it( default_gui_session, load_a_blank_page ):
            
            try:
                
                if load_a_blank_page:
                    
                    self._notebook.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, on_deepest_notebook = True )
                    
                else:
                    
                    self._notebook.LoadGUISession( default_gui_session )
                    
                
            finally:
                
                last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
                
                #self._controller.CallLaterQtSafe(self, 1.0, self.adjustSize ) # some i3 thing--doesn't layout main gui on init for some reason
                
                self._controller.CallLaterQtSafe(self, last_session_save_period_minutes * 60, self.AutoSaveLastSession)
                
                self._clipboard_watcher_repeating_job = self._controller.CallRepeatingQtSafe(self, 1.0, 1.0, self.REPEATINGClipboardWatcher)
                
                self._controller.ReportFirstSessionLoaded()
                
            
        
        self._controller.CallLaterQtSafe( self, 0.25, do_it, default_gui_session, load_a_blank_page )
        
    
    def _LockServer( self, service_key, lock ):
        
        def do_it( service, lock ):
            
            if lock:
                
                command = 'lock_on'
                done_message = 'Server locked!'
                
            else:
                
                command = 'lock_off'
                done_message = 'Server unlocked!'
                
            
            service.Request( HC.POST, command )
            
            HydrusData.ShowText( done_message )
            
        
        if lock:
            
            message = 'This will tell the server to lock and disconnect its database, in case you wish to make a db backup using an external program. It will not be able to serve any requests as long as it is locked. It may get funky if it is locked for hours and hours--if you need it paused for that long, I recommend just shutting it down instead.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
        
        service = self._controller.services_manager.GetService( service_key )
        
        self._controller.CallToThread( do_it, service, lock )
        
    
    def _ManageAccountTypes( self, service_key ):
        
        title = 'manage account types'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIServices.ManageAccountTypesPanel( dlg, service_key )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageDefaultTagImportOptions( self ):
        
        title = 'manage default tag import options'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ) = domain_manager.GetDefaultTagImportOptions()
            
            url_classes = domain_manager.GetURLClasses()
            parsers = domain_manager.GetParsers()
            
            url_class_keys_to_parser_keys = domain_manager.GetURLClassKeysToParserKeys()
            
            panel = ClientGUIScrolledPanelsEdit.EditDefaultTagImportOptionsPanel( dlg, url_classes, parsers, url_class_keys_to_parser_keys, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ) = panel.GetValue()
                
                domain_manager.SetDefaultTagImportOptions( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options )
                
            
        
    
    def _ManageDownloaderDisplay( self ):
        
        title = 'manage downloader display'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            gug_keys_to_display = domain_manager.GetGUGKeysToDisplay()
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_display = domain_manager.GetURLClassKeysToDisplay()
            
            show_unmatched_urls_in_media_viewer = HG.client_controller.new_options.GetBoolean( 'show_unmatched_urls_in_media_viewer' )
            
            panel = ClientGUIDownloaders.EditDownloaderDisplayPanel( dlg, self._controller.network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display, show_unmatched_urls_in_media_viewer )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( gug_keys_to_display, url_class_keys_to_display, show_unmatched_urls_in_media_viewer ) = panel.GetValue()
                
                domain_manager.SetGUGKeysToDisplay( gug_keys_to_display )
                domain_manager.SetURLClassKeysToDisplay( url_class_keys_to_display )
                
                HG.client_controller.new_options.SetBoolean( 'show_unmatched_urls_in_media_viewer', show_unmatched_urls_in_media_viewer )
                
            
        
    
    def _ManageExportFolders( self ):
        
        def qt_do_it():
            
            export_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folders' ) as dlg:
                
                panel = ClientGUIExport.EditExportFoldersPanel( dlg, export_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
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
                        
                        controller.CallBlockingToQt( self, qt_do_it )
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.options[ 'pause_export_folders_sync' ] = original_pause_status
                    
                    controller.pub( 'notify_new_export_folders' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageGUGs( self ):
        
        title = 'manage gallery url generators'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            panel = ClientGUIDownloaders.EditGUGsPanel( dlg, gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                gugs = panel.GetValue()
                
                domain_manager.SetGUGs( gugs )
                
            
        
    
    def _ManageImportFolders( self ):
        
        def qt_do_it():
            
            import_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import folders' ) as dlg:
                
                panel = ClientGUIImport.EditImportFoldersPanel( dlg, import_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
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
                        
                        controller.CallBlockingToQt(self, qt_do_it)
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.options[ 'pause_import_folders_sync' ] = original_pause_status
                    
                    controller.pub( 'notify_new_import_folders' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageLogins( self ):
        
        title = 'manage logins'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            login_manager = self._controller.network_engine.login_manager
            
            login_scripts = login_manager.GetLoginScripts()
            domains_to_login_info = login_manager.GetDomainsToLoginInfo()
            
            panel = ClientGUILogin.EditLoginsPanel( dlg, self._controller.network_engine, login_scripts, domains_to_login_info )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                domains_to_login_info = panel.GetValue()
                
                login_manager.SetDomainsToLoginInfo( domains_to_login_info )
                
                domains_to_login = panel.GetDomainsToLoginAfterOK()
                
                if len( domains_to_login ) > 0:
                    
                    self._controller.network_engine.ForceLogins( domains_to_login )
                    
                
            
        
    
    def _ManageLoginScripts( self ):
        
        title = 'manage login scripts'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            login_manager = self._controller.network_engine.login_manager
            
            login_scripts = login_manager.GetLoginScripts()
            
            panel = ClientGUILogin.EditLoginScriptsPanel( dlg, login_scripts )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                login_scripts = panel.GetValue()
                
                login_manager.SetLoginScripts( login_scripts )
                
            
        
    
    def _ManageNetworkHeaders( self ):
        
        title = 'manage http headers'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            network_contexts_to_custom_header_dicts = domain_manager.GetNetworkContextsToCustomHeaderDicts()
            
            panel = ClientGUINetwork.EditNetworkContextCustomHeadersPanel( dlg, network_contexts_to_custom_header_dicts )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                network_contexts_to_custom_header_dicts = panel.GetValue()
                
                domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
                
            
        
    
    def _ManageOptions( self ):
        
        title = 'manage options'
        frame_key = 'manage_options_dialog'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title, frame_key ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageOptionsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        qt_style_name = self._controller.new_options.GetNoneableString( 'qt_style_name' )
        qt_stylesheet_name = self._controller.new_options.GetNoneableString( 'qt_stylesheet_name' )
        
        try:
            
            if qt_style_name is None:
                
                ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                
            else:
                
                ClientGUIStyle.SetStyleFromName( qt_style_name )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
        try:
            
            if qt_stylesheet_name is None:
                
                ClientGUIStyle.ClearStylesheet()
                
            else:
                
                ClientGUIStyle.SetStylesheetFromPath( qt_stylesheet_name )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
        self._controller.pub( 'wake_daemons' )
        self.SetStatusBarDirty()
        self._controller.pub( 'refresh_page_name' )
        self._controller.pub( 'notify_new_colourset' )
        self._controller.pub( 'notify_new_favourite_tags' )
        
        self._UpdateSystemTrayIcon()
        
    
    def _ManageParsers( self ):
        
        title = 'manage parsers'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            parsers = domain_manager.GetParsers()
            
            panel = ClientGUIParsing.EditParsersPanel( dlg, parsers )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                parsers = panel.GetValue()
                
                domain_manager.SetParsers( parsers )
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
            
        
    
    def _ManageParsingScripts( self ):
        
        title = 'manage parsing scripts'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIParsing.ManageParsingScriptsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageServer( self, service_key ):
        
        title = 'manage server services'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIServices.ManageServerServicesPanel( dlg, service_key )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageServices( self ):
        
        original_pause_status = HC.options[ 'pause_repo_sync' ]
        
        HC.options[ 'pause_repo_sync' ] = True
        
        try:
            
            title = 'manage services'
            
            with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
                
                panel = ClientGUIServices.ManageClientServicesPanel( dlg )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        finally:
            
            HC.options[ 'pause_repo_sync' ] = original_pause_status
            
        
    
    def _ManageSubscriptions( self ):
        
        def qt_do_it( subscriptions, missing_query_log_container_names, surplus_query_log_container_names, original_pause_status ):
            
            if len( missing_query_log_container_names ) > 0:
                
                text = '{} subscription queries had missing database data! This is a serious error!'.format( HydrusData.ToHumanInt( len( missing_query_log_container_names ) ) )
                text += os.linesep * 2
                text += 'If you continue, the client will now create and save empty file/gallery logs for those queries, essentially resetting them, but if you know you need to exit and fix your database in a different way, cancel out now.'
                text += os.linesep * 2
                text += 'If you do not know why this happened, you may have had a hard drive fault. Please consult "install_dir/db/help my db is broke.txt", and you may want to contact hydrus dev.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Missing Query Logs!', yes_label = 'continue', no_label = 'back out' )
                
                if result == QW.QDialog.Accepted:
                    
                    from hydrus.client.importing import ClientImportSubscriptionQuery
                    
                    for missing_query_log_container_name in missing_query_log_container_names:
                        
                        query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( missing_query_log_container_name )
                        
                        HG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                        
                    
                    for subscription in subscriptions:
                        
                        for query_header in subscription.GetQueryHeaders():
                            
                            if query_header.GetQueryLogContainerName() in missing_query_log_container_names:
                                
                                query_header.Reset( query_log_container )
                                
                            
                        
                    
                    HG.client_controller.subscriptions_manager.SetSubscriptions( subscriptions ) # save the reset
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
            if len( surplus_query_log_container_names ) > 0:
                
                text = 'When loading subscription data, the client discovered surplus orphaned subscription data for {} queries! This data is harmless and no longer used. The situation is however unusual, and probably due to an unusual deletion routine or a bug.'.format( HydrusData.ToHumanInt( len( surplus_query_log_container_names ) ) )
                text += os.linesep * 2
                text += 'If you continue, this surplus data will backed up to your database directory and then safely deleted from the database itself, but if you recently did manual database editing and know you need to exit and fix your database in a different way, cancel out now.'
                text += os.linesep * 2
                text += 'If you do not know why this happened, hydrus dev would be interested in being told about it and the surrounding circumstances.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Orphan Query Logs!', yes_label = 'continue', no_label = 'back out' )
                
                if result == QW.QDialog.Accepted:
                    
                    sub_dir = os.path.join( self._controller.GetDBDir(), 'orphaned_query_log_containers' )
                    
                    HydrusPaths.MakeSureDirectoryExists( sub_dir )
                    
                    for surplus_query_log_container_name in surplus_query_log_container_names:
                        
                        surplus_query_log_container = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, surplus_query_log_container_name )
                        
                        backup_path = os.path.join( sub_dir, 'qlc_{}.json'.format( surplus_query_log_container_name ) )
                        
                        with open( backup_path, 'w', encoding = 'utf-8' ) as f:
                            
                            f.write( surplus_query_log_container.DumpToString() )
                            
                        
                        HG.client_controller.WriteSynchronous( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, surplus_query_log_container_name )
                        
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
            title = 'manage subscriptions'
            frame_key = 'manage_subscriptions_dialog'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title, frame_key ) as dlg:
                
                panel = ClientGUISubscriptions.EditSubscriptionsPanel( dlg, subscriptions, original_pause_status )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( subscriptions, edited_query_log_containers, deletee_query_log_container_names ) = panel.GetValue()
                    
                    return ( subscriptions, edited_query_log_containers, deletee_query_log_container_names )
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
        
        def THREAD_do_it( controller ):
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_text_1', 'Waiting for current subscription work to finish.' )
            
            controller.pub( 'message', job_key )
            
            with self._delayed_dialog_lock:
                
                try:
                    
                    try:
                        
                        original_pause_status = controller.options[ 'pause_subs_sync' ]
                        
                        controller.options[ 'pause_subs_sync' ] = True
                        
                        if HG.client_controller.subscriptions_manager.SubscriptionsRunning():
                            
                                while HG.client_controller.subscriptions_manager.SubscriptionsRunning():
                                    
                                    time.sleep( 0.1 )
                                    
                                    if HG.view_shutdown:
                                        
                                        return
                                        
                                    
                                
                            
                        
                    finally:
                        
                        job_key.Delete()
                        
                    
                    subscriptions = HG.client_controller.subscriptions_manager.GetSubscriptions()
                    
                    expected_query_log_container_names = set()
                    
                    for subscription in subscriptions:
                        
                        expected_query_log_container_names.update( subscription.GetAllQueryLogContainerNames() )
                        
                    
                    actual_query_log_container_names = set( HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER ) )
                    
                    missing_query_log_container_names = expected_query_log_container_names.difference( actual_query_log_container_names )
                    
                    surplus_query_log_container_names = actual_query_log_container_names.difference( expected_query_log_container_names )
                    
                    try:
                        
                        done_job_key = ClientThreading.JobKey()
                        
                        ( subscriptions, edited_query_log_containers, deletee_query_log_container_names ) = controller.CallBlockingToQt( self, qt_do_it, subscriptions, missing_query_log_container_names, surplus_query_log_container_names, original_pause_status )
                        
                        done_job_key.SetVariable( 'popup_text_1', 'Saving subscription changes.' )
                        
                        controller.pub( 'message', done_job_key )
                        
                        HG.client_controller.WriteSynchronous(
                        'serialisable_atomic',
                        overwrite_types_and_objs = ( [ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ], subscriptions ),
                        set_objs = edited_query_log_containers,
                        deletee_types_to_names = { HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER : deletee_query_log_container_names }
                        )
                        
                        HG.client_controller.subscriptions_manager.SetSubscriptions( subscriptions )
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    except HydrusExceptions.CancelledException:
                        
                        HG.client_controller.subscriptions_manager.Wake()
                        
                    finally:
                        
                        done_job_key.Delete()
                        
                    
                finally:
                    
                    controller.options[ 'pause_subs_sync' ] = original_pause_status
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageTagDisplay( self ):
        
        title = 'manage tag display and search'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUITags.EditTagDisplayManagerPanel( dlg, self._controller.tag_display_manager )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                tag_display_manager = panel.GetValue()
                
                tag_display_manager.SetDirty()
                
                self._controller.tag_display_manager = tag_display_manager
                
                self._controller.pub( 'notify_new_tag_display_rules' )
                
            
        
    
    def _ManageTagDisplayApplication( self ):
        
        title = 'manage where tag siblings and parents apply'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = self._controller.Read( 'tag_display_application' )
            
            panel = ClientGUITags.EditTagDisplayApplication( dlg, master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( edited_master_service_keys_to_sibling_applicable_service_keys, edited_master_service_keys_to_parent_applicable_service_keys ) = panel.GetValue()
                
                self._controller.Write( 'tag_display_application', edited_master_service_keys_to_sibling_applicable_service_keys, edited_master_service_keys_to_parent_applicable_service_keys )
                
            
        
    
    def _ManageTagParents( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, 'manage tag parents' ) as dlg:
            
            panel = ClientGUITags.ManageTagParents( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, 'manage tag siblings' ) as dlg:
            
            panel = ClientGUITags.ManageTagSiblings( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageURLClasses( self ):
        
        title = 'manage url classes'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            url_classes = domain_manager.GetURLClasses()
            
            panel = ClientGUIDownloaders.EditURLClassesPanel( dlg, url_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url_classes = panel.GetValue()
                
                domain_manager.SetURLClasses( url_classes )
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
            
        
    
    def _ManageURLClassLinks( self ):
        
        title = 'manage url class links'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            url_classes = domain_manager.GetURLClasses()
            parsers = domain_manager.GetParsers()
            
            url_class_keys_to_parser_keys = domain_manager.GetURLClassKeysToParserKeys()
            
            panel = ClientGUIDownloaders.EditURLClassLinksPanel( dlg, self._controller.network_engine, url_classes, parsers, url_class_keys_to_parser_keys )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url_class_keys_to_parser_keys = panel.GetValue()
                
                domain_manager.SetURLClassKeysToParserKeys( url_class_keys_to_parser_keys )
                
            
        
    
    def _ManageUPnP( self ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self ) as dlg: dlg.exec()
        
    
    def _MigrateDatabase( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'migrate database' ) as dlg:
            
            panel = ClientGUIScrolledPanelsReview.MigrateDatabasePanel( dlg, self._controller )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        self.DirtyMenu( 'database' )
        
        self._menu_updater.Update()
        
    
    def _MigrateTags( self ):
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'migrate tags' )
        
        panel = ClientGUIScrolledPanelsReview.MigrateTagsPanel( frame, default_tag_repository_key )
        
        frame.SetPanel( panel )
        
    
    def _ModifyAccount( self, service_key ):
        
        QW.QMessageBox.information( self, 'Information', 'this does not work yet!' )
        
        return
        
        service = self._controller.services_manager.GetService( service_key )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account key for the account to be modified.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                try:
                    
                    account_key = bytes.fromhex( dlg.GetValue() )
                    
                except:
                    
                    QW.QMessageBox.critical( self, 'Error', 'Could not parse that account key' )
                    
                    return
                    
                
                subject_account = 'blah' # fetch account from service
                
                with ClientGUIDialogs.DialogModifyAccounts( self, service_key, [ subject_account ] ) as dlg2: dlg2.exec()
                
            
        
    
    def _OpenDBFolder( self ):
        
        HydrusPaths.LaunchDirectory( self._controller.GetDBDir() )
        
    
    def _OpenExportFolder( self ):
        
        export_path = ClientExporting.GetExportPath()
        
        HydrusPaths.LaunchDirectory( export_path )
        
    
    def _OpenInstallFolder( self ):
        
        HydrusPaths.LaunchDirectory( HC.BASE_DIR )
        
    
    def _PausePlaySync( self, sync_type ):
        
        if sync_type == 'repo':
            
            HC.options[ 'pause_repo_sync' ] = not HC.options[ 'pause_repo_sync' ]
            
            self._controller.pub( 'notify_restart_repo_sync' )
            
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
        
        if not QP.isValid( self ) or not self._notebook or not self._statusbar or self._CurrentlyMinimisedOrHidden():
            
            return
            
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is None:
            
            media_status = ''
            
        else:
            
            media_status = page.GetPrettyStatus()
            
        
        if self._controller.CurrentlyIdle():
            
            idle_status = 'idle'
            idle_tooltip = 'client is idle, it can do maintenance work'
            
        else:
            
            idle_status = ''
            idle_tooltip = None
            
        
        hydrus_busy_status = self._controller.GetThreadPoolBusyStatus()
        hydrus_busy_tooltip = 'just a simple measure of how much hydrus wants to do atm'
        
        if self._controller.SystemBusy():
            
            busy_status = 'CPU busy'
            busy_tooltip = 'this computer has been doing work recently, so some hydrus maintenance will not start'
            
        else:
            
            busy_status = ''
            busy_tooltip = None
            
        
        ( db_status, job_name ) = HG.client_controller.GetDBStatus()
        
        if job_name is not None and job_name != '':
            
            db_tooltip = 'current db job: {}'.format( job_name )
            
        else:
            
            db_tooltip = None
            
        
        self._statusbar.setToolTip( job_name )
        
        self._statusbar.SetStatusText( media_status, 0 )
        self._statusbar.SetStatusText( idle_status, 2, tooltip = idle_tooltip )
        self._statusbar.SetStatusText( hydrus_busy_status, 3, tooltip = hydrus_busy_tooltip )
        self._statusbar.SetStatusText( busy_status, 4, tooltip = busy_tooltip )
        self._statusbar.SetStatusText( db_status, 5, tooltip = db_tooltip )
        
    
    def _RegenerateTagDisplayMappingsCache( self ):
        
        message = 'This will delete and then recreate the tag \'display\' mappings cache, which is used for user-presented tag searching, loading, and autocomplete counts. This is useful if miscounting (particularly related to siblings/parents) has somehow occurred.'
        message += os.linesep * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang. All siblings and parents will have to be resynced.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'regenerate_tag_display_mappings_cache' )
            
        
    
    def _RegenerateTagMappingsCache( self ):
        
        message = 'This will delete and then recreate the entire tag \'storage\' mappings cache, which is used for raw tag searching, loading, and autocomplete counts. This is useful if miscounting has somehow occurred.'
        message += os.linesep * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang. It necessarily involves a regeneration of the tag display mappings cache, which relies on the storage cache. All siblings and parents will have to be resynced.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'regenerate_tag_mappings_cache' )
            
        
    
    def _RegenerateSimilarFilesTree( self ):
        
        message = 'This will delete and then recreate the similar files search tree. This is useful if it has somehow become unbalanced and similar files searches are running slow.'
        message += os.linesep * 2
        message += 'If you have a lot of files, it can take a little while, during which the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it', check_for_cancelled = True )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'regenerate_similar_files' )
            
        
    
    def _RepairInvalidTags( self ):
        
        message = 'This will scan all your tags and repair any that are invalid. This might mean taking out unrenderable characters or cleaning up improper whitespace. If there is a tag collision once cleaned, it may add a (1)-style number on the end.'
        message += os.linesep * 2
        message += 'If you have a lot of tags, it can take a long time, during which the gui may hang. If it finds bad tags, you should restart the program once it is complete.'
        message += os.linesep * 2
        message += 'If you have not had tag rendering problems, there is no reason to run this.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'repairing invalid tags' )
            
            self._controller.pub( 'message', job_key )
            
            self._controller.Write( 'repair_invalid_tags', job_key = job_key )
            
        
    
    def _RepopulateMappingsTables( self ):
        
        message = 'WARNING: Do not run this for no reason!'
        message += os.linesep * 2
        message += 'If you have significant local tags (e.g. \'my tags\') storage, recently had a \'malformed\' client.mappings.db file, and have since gone through clone/repair and now have a truncated file, this routine will attempt to recover missing tags from the smaller tag cache stored in client.caches.db.'
        message += os.linesep * 2
        message += 'It can only recover tags for files currently stored by your client. It will take some time, during which the gui may hang. Once it is done, you probably want to regenerate your tag mappings cache, so that you are completely synced again.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'I have a reason to run this, let\'s do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetVariable( 'popup_text_title', 'repopulating mapping tables' )
            
            self._controller.pub( 'modal_message', job_key )
            
            self._controller.Write( 'repopulate_mappings_from_cache', job_key = job_key )
            
        
    
    def _RepopulateTagSearchCache( self ):
        
        message = 'This will go through all the tag definitions in the database and make sure there is a correct fast-search record for it.'
        message += os.linesep * 2
        message += 'It may take a long time, and the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_text_title', 'repopulating and updating tag text search cache' )
            
            self._controller.pub( 'modal_message', job_key )
            
            status_hook = lambda s: job_key.SetVariable( 'popup_text_1', s )
            
            def do_it():
                
                self._controller.WriteSynchronous( 'repopulate_tag_search_cache', status_hook = status_hook )
                
                job_key.Finish()
                
            
            self._controller.CallToThreadLongRunning( do_it )
            
        
    
    def _RegenerateTagParentsLookupCache( self ):
        
        message = 'This will delete and then recreate the tag parents lookup cache, which is used for all basic tag parents operations. This is useful if it has become damaged or otherwise desynchronised.'
        message += os.linesep * 2
        message += 'It should only take a second or two.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'regenerate_tag_parents_cache' )
            
        
    
    def _RegenerateTagSiblingsLookupCache( self ):
        
        message = 'This will delete and then recreate the tag siblings lookup cache, which is used for all basic tag sibling operations. This is useful if it has become damaged or otherwise desynchronised.'
        message += os.linesep * 2
        message += 'It should only take a second or two. It necessarily involves a regeneration of the tag parents lookup cache.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'regenerate_tag_siblings_cache' )
            
        
    
    def _RestoreSplitterPositions( self ):
        
        self._controller.pub( 'set_splitter_positions', HC.options[ 'hpos' ], HC.options[ 'vpos' ] )
        
    
    def _ReviewBandwidth( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review bandwidth' )
        
        panel = ClientGUINetwork.ReviewAllBandwidthPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewFileMaintenance( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'file maintenance' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewFileMaintenance( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewNetworkJobs( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review network jobs' )
        
        panel = ClientGUINetwork.ReviewNetworkJobs( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewNetworkSessions( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review session cookies' )
        
        panel = ClientGUINetwork.ReviewNetworkSessionsPanel( frame, self._controller.network_engine.session_manager )
        
        frame.SetPanel( panel )
        
    
    def _ReviewServices( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, self._controller.PrepStringForDisplay( 'Review Services' ), 'review_services' )
        
        panel = ClientGUIServices.ReviewServicesPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewTagDisplayMaintenance( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'tag display maintenance' )
        
        panel = ClientGUITags.ReviewTagDisplayMaintenancePanel( frame )
        
        frame.SetPanel( panel )
        
    
    def _ReviewThreads( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review threads' )
        
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
        
    
    def _RunClientAPITest( self ):
        
        # this is not to be a comprehensive test of client api functions, but a holistic sanity check to make sure everything is wired up right at UI level, with a live functioning client
        
        from hydrus.client import ClientAPI
        
        def do_it():
            
            # job key
            
            client_api_service = HG.client_controller.services_manager.GetService( CC.CLIENT_API_SERVICE_KEY )
            
            port = client_api_service.GetPort()
            
            was_running_before = port is not None
            
            if not was_running_before:
                
                port = 6666
                
                client_api_service._port = port
                
                HG.client_controller.RestartClientServerServices()
                
                time.sleep( 5 )
                
            
            #
            
            api_permissions = ClientAPI.APIPermissions( name = 'hydrus test access', basic_permissions = list( ClientAPI.ALLOWED_PERMISSIONS ), search_tag_filter = ClientTags.TagFilter() )
            
            access_key = api_permissions.GetAccessKey()
            
            HG.client_controller.client_api_manager.AddAccess( api_permissions )
            
            #
            
            try:
                
                job_key = ClientThreading.JobKey()
                
                job_key.SetVariable( 'popup_title', 'client api test' )
                
                HG.client_controller.pub( 'message', job_key )
                
                import requests
                import json
                
                s = requests.Session()
                
                s.verify = False
                
                s.headers[ 'Hydrus-Client-API-Access-Key' ] = access_key.hex()
                s.headers[ 'Content-Type' ] = 'application/json'
                
                if client_api_service.UseHTTPS():
                    
                    schema = 'https'
                    
                else:
                    
                    schema = 'http'
                    
                
                api_base = '{}://127.0.0.1:{}'.format( schema, port )
                
                #
                
                r = s.get( '{}/api_version'.format( api_base ) )
                
                j = r.json()
                
                if j[ 'version' ] != HC.CLIENT_API_VERSION:
                    
                    HydrusData.ShowText( 'version incorrect!: {}, {}'.format( j[ 'version' ], HC.CLIENT_API_VERSION ) )
                    
                
                #
                
                job_key.SetVariable( 'popup_text_1', 'add url test' )
                
                local_tag_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
                
                local_tag_service = random.choice( local_tag_services )
                
                local_tag_service_name = local_tag_service.GetName()
                
                samus_url = 'https://safebooru.org/index.php?page=post&s=view&id=3195917'
                samus_hash_hex = '78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538'
                samus_test_tag = 'client api test tag'
                samus_test_tag_filterable = 'client api test tag filterable'
                destination_page_name = 'client api test'
                
                request_args = {}
                
                request_args[ 'url' ] = samus_url
                request_args[ 'destination_page_name' ] = destination_page_name
                request_args[ 'service_names_to_additional_tags' ] = {
                    local_tag_service_name : [ samus_test_tag ]
                }
                request_args[ 'filterable_tags' ] = [
                    samus_test_tag_filterable
                ]
                
                data = json.dumps( request_args )
                
                r = s.post( '{}/add_urls/add_url'.format( api_base ), data = data )
                
                time.sleep( 0.25 )
                
                #
                
                job_key.SetVariable( 'popup_text_1', 'get session test' )
                
                def get_client_api_page():
                    
                    r = s.get( '{}/manage_pages/get_pages'.format( api_base ) )
                    
                    pages_to_process = [ r.json()[ 'pages' ] ]
                    pages = []
                    
                    while len( pages_to_process ) > 0:
                        
                        page_to_process = pages_to_process.pop()
                        
                        if page_to_process[ 'page_type' ] == ClientGUIManagement.MANAGEMENT_TYPE_PAGE_OF_PAGES:
                            
                            pages_to_process.extend( page_to_process[ 'pages' ] )
                            
                        else:
                            
                            pages.append( page_to_process )
                            
                        
                    
                    for page in pages:
                        
                        if page[ 'name' ] == destination_page_name:
                            
                            return page
                            
                        
                    
                
                client_api_page = get_client_api_page()
                
                if client_api_page is None:
                    
                    raise Exception( 'Could not find download page!' )
                    
                
                destination_page_key_hex = client_api_page[ 'page_key' ]
                
                def get_hash_ids():
                    
                    r = s.get( '{}/manage_pages/get_page_info?page_key={}'.format( api_base, destination_page_key_hex ) )
                    
                    hash_ids = r.json()[ 'page_info' ][ 'media' ][ 'hash_ids' ]
                    
                    return hash_ids
                    
                
                hash_ids = get_hash_ids()
                
                if len( hash_ids ) == 0:
                    
                    time.sleep( 3 )
                    
                
                hash_ids = get_hash_ids()
                
                if len( hash_ids ) == 0:
                    
                    raise Exception( 'The download page had no hashes!' )
                    
                
                #
                
                def get_hash_ids_to_hashes_and_tag_info():
                    
                    r = s.get( '{}/get_files/file_metadata?file_ids={}'.format( api_base, json.dumps( hash_ids ) ) )
                    
                    hash_ids_to_hashes_and_tag_info = {}
                    
                    for item in r.json()[ 'metadata' ]:
                        
                        hash_ids_to_hashes_and_tag_info[ item[ 'file_id' ] ] = ( item[ 'hash' ], item[ 'service_names_to_statuses_to_tags' ] )
                        
                    
                    return hash_ids_to_hashes_and_tag_info
                    
                
                hash_ids_to_hashes_and_tag_info = get_hash_ids_to_hashes_and_tag_info()
                
                samus_hash_id = None
                
                for ( hash_id, ( hash_hex, tag_info ) ) in hash_ids_to_hashes_and_tag_info.items():
                    
                    if hash_hex == samus_hash_hex:
                        
                        samus_hash_id = hash_id
                        
                    
                
                if samus_hash_id is None:
                    
                    raise Exception( 'Could not find the samus hash!' )
                    
                
                samus_tag_info = hash_ids_to_hashes_and_tag_info[ samus_hash_id ][1]
                
                if samus_test_tag not in samus_tag_info[ local_tag_service_name ][ str( HC.CONTENT_STATUS_CURRENT ) ]:
                    
                    raise Exception( 'Did not have the tag!' )
                    
                
                #
                
                def qt_session_gubbins():
                    
                    self.ProposeSaveGUISession( 'last session' )
                    
                    page = self._notebook.GetPageFromPageKey( bytes.fromhex( destination_page_key_hex ) )
                    
                    self._notebook.ShowPage( page )
                    
                    self._notebook.CloseCurrentPage()
                    
                    self.ProposeSaveGUISession( 'last session' )
                    
                
                HG.client_controller.CallBlockingToQt( HG.client_controller.gui, qt_session_gubbins )
                
            finally:
                
                #
                
                HG.client_controller.client_api_manager.DeleteAccess( ( access_key, ) )
                
                #
                
                if not was_running_before:
                    
                    client_api_service._port = None
                    
                    HG.client_controller.RestartClientServerServices()
                    
                
                job_key.Delete()
                
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _RunUITest( self ):
        
        def qt_open_pages():
            
            page_of_pages = self._notebook.NewPagesNotebook( on_deepest_notebook = False, select_page = True )
            
            t = 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self._notebook.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, page_name ='test', on_deepest_notebook = True)
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_PAGE_OF_PAGES))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, page_of_pages.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, page_name ='test', on_deepest_notebook = False)
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE))
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProposeSaveGUISession, 'last session' )
            
            return page_of_pages
            
        
        def qt_close_unclose_one_page():
            
            self._notebook.CloseCurrentPage()
            
            HG.client_controller.CallLaterQtSafe(self, 0.5, self._UnclosePage)
            
        
        def qt_close_pages( page_of_pages ):
            
            indices = list( range( page_of_pages.count() ) )
            
            indices.reverse()
            
            t = 0.0
            
            for i in indices:
                
                HG.client_controller.CallLaterQtSafe(self, t, page_of_pages._ClosePage, i)
                
                t += 0.25
                
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self._notebook.CloseCurrentPage)
            
            t += 0.25
            
            HG.client_controller.CallLaterQtSafe(self, t, self.DeleteAllClosedPages)
            
        
        def qt_test_ac():
            
            SYS_PRED_REFRESH = 1.0
            
            page = self._notebook.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, page_name = 'test', select_page = True )
            
            t = 0.5
            
            HG.client_controller.CallLaterQtSafe(self, t, page.SetSearchFocus)
            
            ac_widget = page.GetManagementPanel()._tag_autocomplete._text_ctrl
            
            t += 0.5
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_SET_MEDIA_FOCUS))
            
            t += 0.5
            
            HG.client_controller.CallLaterQtSafe(self, t, self.ProcessApplicationCommand, CAC.ApplicationCommand(CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_SET_SEARCH_FOCUS))
            
            t += 0.5
            
            uias = QP.UIActionSimulator()
            
            for c in 'the colour of her hair':
                
                HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, ord( c ), text = c )
                
                t += 0.01
                
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            t += SYS_PRED_REFRESH
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            t += SYS_PRED_REFRESH
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Down)
            
            t += 0.05
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            t += SYS_PRED_REFRESH
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Down)
            
            t += 0.05
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            t += SYS_PRED_REFRESH
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            for i in range( 16 ):
                
                t += SYS_PRED_REFRESH
                
                for j in range( i + 1 ):
                    
                    HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Down)
                    
                    t += 0.1
                    
                
                HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
                
                t += SYS_PRED_REFRESH
                
                HG.client_controller.CallLaterQtSafe(self, t, uias.Char, None, QC.Qt.Key_Return)
                
            
            t += 1.0
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Down)
            
            t += 0.05
            
            HG.client_controller.CallLaterQtSafe(self, t, uias.Char, ac_widget, QC.Qt.Key_Return)
            
            t += 1.0
            
            HG.client_controller.CallLaterQtSafe(self, t, self._notebook.CloseCurrentPage)
            
        
        def do_it():
            
            # pages
            
            page_of_pages = HG.client_controller.CallBlockingToQt(self, qt_open_pages)
            
            time.sleep( 4 )
            
            HG.client_controller.CallBlockingToQt(self, qt_close_unclose_one_page)
            
            time.sleep( 1.5 )
            
            HG.client_controller.CallBlockingToQt(self, qt_close_pages, page_of_pages)
            
            time.sleep( 5 )
            
            del page_of_pages
            
            # a/c
            
            HG.client_controller.CallBlockingToQt(self, qt_test_ac)
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _RunServerTest( self ):
        
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
                    
                    HydrusData.CheckProgramIsNotShuttingDown()
                    
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
            
            QP.CallAfter( ClientGUIFrames.ShowKeys, 'access', (access_key,) )
            
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
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.CallToThread( do_it )
            
        
    
    def _SaveSplitterPositions( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
            
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof by any means, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or run from edited source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = True, min_char_width = 24 ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
            
        
    
    def _PausePlaySearch( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.PausePlaySearch()
            
        
    
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
        
        QW.QMessageBox.information( self, 'Information', backup_intro )
        
        with QP.DirDialog( self, 'Select backup location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                if path == '':
                    
                    path = None
                    
                
                if path == self._controller.GetDBDir():
                    
                    QW.QMessageBox.critical( self, 'Error', 'That directory is your current database directory! You cannot backup to the same location you are backing up from!' )
                    
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
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text )
                
                if result == QW.QDialog.Accepted:
                    
                    self._new_options.SetNoneableString( 'backup_path', path )
                    
                    text = 'Would you like to create your backup now?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, text )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._BackupDatabase()
                        
                    
                
            
        
    
    def _ShowHideSplitters( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.ShowHideSplit()
            
        
    
    def _StartIPFSDownload( self ):
        
        ipfs_services = self._controller.services_manager.GetServices( ( HC.IPFS, ), randomised = True )
        
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
                
                result = dlg.exec()
                
                if result == QW.QDialog.Accepted:
                    
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
            
        elif name == 'db_ui_hang_relief_mode':
            
            HG.db_ui_hang_relief_mode = not HG.db_ui_hang_relief_mode
            
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
            
        
    
    def _TestServerBusy( self, service_key ):
        
        def do_it( service ):
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            if result_bytes == b'1':
                
                HydrusData.ShowText( 'server is busy' )
                
            elif result_bytes == b'0':
                
                HydrusData.ShowText( 'server is not busy' )
                
            else:
                
                HydrusData.ShowText( 'server responded in a way I do not understand' )
                
            
        
        service = self._controller.services_manager.GetService( service_key )
        
        self._controller.CallToThread( do_it, service )
        
    
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
                
            
            if isinstance( service, ClientServices.ServiceRepository ):
                
                if not service.IsMostlyCaughtUp():
                    
                    raise Exception( 'Repository processing is not caught up--please process more before you upload new content.' )
                    
                
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'Unfortunately, there is a problem with starting the upload: ' + str( e ) )
            
            return
            
        
        HG.currently_uploading_pending = True
        
        self._controller.CallToThread( THREADUploadPending, service_key )
        
    
    def _UpdateSystemTrayIcon( self, currently_booting = False ):
        
        if not ClientGUISystemTray.SystemTrayAvailable() or ( not HC.PLATFORM_WINDOWS and not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) ):
            
            return
            
        
        new_options = self._controller.new_options
        
        always_show_system_tray_icon = new_options.GetBoolean( 'always_show_system_tray_icon' )
        
        need_system_tray = always_show_system_tray_icon
        
        if self._currently_minimised_to_system_tray:
            
            need_system_tray = True
            
        
        if need_system_tray:
            
            if not self._have_system_tray_icon:
                
                self._system_tray_icon = ClientGUISystemTray.ClientSystemTrayIcon( self )
                
                self._system_tray_icon.highlight.connect( self.RestoreOrActivateWindow )
                self._system_tray_icon.flip_show_ui.connect( self._FlipShowHideWholeUI )
                self._system_tray_icon.exit_client.connect( self.TryToExit )
                self._system_tray_icon.flip_pause_network_jobs.connect( self.FlipNetworkTrafficPaused )
                self._system_tray_icon.flip_pause_subscription_jobs.connect( self.FlipSubscriptionsPaused )
                
                self._have_system_tray_icon = True
                
            
            self._system_tray_icon.show()
            
            self._system_tray_icon.SetShouldAlwaysShow( always_show_system_tray_icon )
            self._system_tray_icon.SetUIIsCurrentlyShown( not self._currently_minimised_to_system_tray )
            self._system_tray_icon.SetNetworkTrafficPaused( new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
            self._system_tray_icon.SetSubscriptionsPaused( HC.options[ 'pause_subs_sync' ] )
            
        else:
            
            if self._have_system_tray_icon:
                
                self._system_tray_icon.deleteLater()
                
                self._system_tray_icon = None
                
                self._have_system_tray_icon = False
                
            
        
    
    def _VacuumDatabase( self ):
        
        text = 'This will rebuild the database, rewriting all indices and tables to be contiguous and optimising most operations. It also truncates the database files, recovering unused space back to your hard drive. It typically happens automatically every few months, but you can force it here.'
        text += os.linesep * 2
        text += 'If you have no reason to run this, it is usually pointless. If you have a very large database on an HDD instead of an SSD, it may take upwards of an hour, during which your gui may hang. A popup message will show its status.'
        text += os.linesep * 2
        text += 'A \'soft\' vacuum will only reanalyze those databases that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        text += os.linesep * 2
        text += 'A \'full\' vacuum will immediately force a vacuum for the entire database. This can take substantially longer.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Choose how thorough your vacuum will be.', yes_label = 'soft', no_label = 'full', check_for_cancelled = True )
        
        if was_cancelled:
            
            return
            
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED )
            
        elif result == QW.QDialog.Rejected:
            
            self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED, force_vacuum = True )
            
        
    
    def _VacuumServer( self, service_key ):
        
        def do_it( service ):
            
            started = HydrusData.GetNow()
            
            service.Request( HC.POST, 'vacuum' )
            
            HydrusData.ShowText( 'Server vacuum started!' )
            
            time.sleep( 10 )
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            while result_bytes == b'1':
                
                if HG.view_shutdown:
                    
                    return
                    
                
                time.sleep( 10 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusData.GetNow() - started
            
            HydrusData.ShowText( 'Server vacuum done in ' + HydrusData.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and vacuum its database files. It may take some time to complete, during which time it will not be able to serve any requests.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def AddModalMessage( self, job_key ):
        
        if job_key.IsCancelled() or job_key.IsDeleted():
            
            return
            
        
        if job_key.IsDone():
            
            self._controller.pub( 'message', job_key )
            
            return
            
        
        dialog_is_open = ClientGUIFunctions.DialogIsOpen()
        
        if self._CurrentlyMinimisedOrHidden() or dialog_is_open or not ClientGUIFunctions.TLWOrChildIsActive( self ):
            
            self._controller.CallLaterQtSafe( self, 0.5, self.AddModalMessage, job_key )
            
        else:
            
            HG.client_controller.pub( 'pause_all_media' )
            
            title = job_key.GetIfHasVariable( 'popup_title' )
            
            if title is None:
                
                title = 'important job'
                
            
            hide_close_button = not job_key.IsCancellable()
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title, hide_buttons = hide_close_button, do_not_activate = True ) as dlg:
                
                panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def AutoSaveLastSession( self ):
        
        only_save_last_session_during_idle = self._controller.new_options.GetBoolean( 'only_save_last_session_during_idle' )
        
        if only_save_last_session_during_idle and not self._controller.CurrentlyIdle():
            
            self._controller.CallLaterQtSafe( self, 60, self.AutoSaveLastSession )
            
        else:
            
            if HC.options[ 'default_gui_session' ] == 'last session':
                
                session = self._notebook.GetCurrentGUISession( 'last session' )
                
                callable = self.AutoSaveLastSession
                
                last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
                
                next_call_delay = last_session_save_period_minutes * 60
                
                def do_it( controller, session, win, next_call_delay, callable ):
                    
                    controller.SaveGUISession( session )
                    
                    controller.CallLaterQtSafe( win, next_call_delay, callable )
                    
                
                self._controller.CallToThread( do_it, self._controller, session, self, next_call_delay, callable )
                
            
        
    
    def closeEvent( self, event ):
        
        if self._controller.new_options.GetBoolean( 'close_client_to_system_tray' ):
            
            self._FlipShowHideWholeUI()
            
            return
            
        
        self.TryToExit()
        
        event.ignore() # we always ignore, as we'll close through the window through other means
        
    
    def DeleteAllClosedPages( self ):
        
        deletee_pages = [ page for ( time_closed, page ) in self._closed_pages ]
        
        self._closed_pages = []
        
        if len( deletee_pages ) > 0:
            
            self._DestroyPages( deletee_pages )
            
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
        
    
    def DirtyMenu( self, name ):
        
        if name not in self._dirty_menus:
            
            self.DisableMenu( name )
            
            self._dirty_menus.add( name )
            
        
    
    def DisableMenu( self, name ):
        
        menu_index = self._FindMenuBarIndex( name )
        
        if menu_index != -1:                
            
            self._menubar.actions()[ menu_index ].setEnabled( False )
            
        
    
    def DoFileStorageRebalance( self, job_key: ClientThreading.JobKey ):
        
        self._controller.CallToThread( self._controller.client_files_manager.Rebalance, job_key )
        
        job_key.SetVariable( 'popup_title', 'rebalancing files' )
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( None, 'migrating files' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key, hide_main_gui = True )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        self._MigrateDatabase()
        
    
    def EventFrameNewPage( self, event ):
        
        screen_position = QG.QCursor.pos()
        
        self._notebook.EventNewPageFromScreenPosition( screen_position )
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            ClientGUITopLevelWindows.MainFrameThatResizes.mouseReleaseEvent( self, event )
            
            return
            
        
        screen_position = QG.QCursor.pos()
        
        self._notebook.ShowMenuFromScreenPosition( screen_position )
        
    
    def EventIconize( self, event: QG.QWindowStateChangeEvent ):
        
        if self.isMinimized():
            
            self._was_maximised = event.oldState() & QC.Qt.WindowMaximized
            
            if not self._currently_minimised_to_system_tray and self._controller.new_options.GetBoolean( 'minimise_client_to_system_tray' ):
                
                self._FlipShowHideWholeUI()
                
            
        else:
            
            QP.CallAfter( self.RefreshMenu )
            QP.CallAfter( self.RefreshStatusBar )
            
        
    
    def EventMove( self, event ):
        
        if HydrusData.TimeHasPassedFloat( self._last_move_pub + 0.1 ):
            
            self._controller.pub( 'top_level_window_move_event' )
            
            self._last_move_pub = HydrusData.GetNowPrecise()
            
        
        return True # was: event.ignore()
        
    
    def TIMEREventAnimationUpdate( self ):
        
        if self._currently_minimised_to_system_tray:
            
            return
            
        
        try:
            
            windows = list( self._animation_update_windows )
            
            for window in windows:
                
                if not QP.isValid( window ):
                    
                    self._animation_update_windows.discard( window )
                    
                    continue
                    
                
                tlw = window.window()
                
                if not tlw or not QP.isValid( tlw ):
                    
                    self._animation_update_windows.discard( window )
                    
                    continue
                    
                
                if self._currently_minimised_to_system_tray:
                    
                    continue
                    
                
                try:
                    
                    if HG.ui_timer_profile_mode:
                        
                        summary = 'Profiling animation timer: ' + repr( window )
                        
                        HydrusData.Profile( summary, 'window.TIMERAnimationUpdate()', globals(), locals(), min_duration_ms = 3 )
                        
                    else:
                        
                        window.TIMERAnimationUpdate()
                        
                    
                except Exception:
                    
                    self._animation_update_windows.discard( window )
                    
                
            
        except:
            
            # obsolote comment below, leaving it just in case
            #
            # unusual error catch here, just to experiment. user was getting wxAssertionError on m_window failed, no GetSize() without window
            # I figured at the time that this is some window manager being unhappy with doing animation on a hidden window,
            # but it could also be a half-dead window trying to draw to a dead bmp or something, and then getting stuck somehow
            # traceback was on the for loop list iteration line,
            # which I think was just the C++/wxAssertionError having trouble making the right trace wew
            
            self._animation_update_windows = set()
            
            windows = []
            
        
        if len( self._animation_update_windows ) == 0:
            
            self._animation_update_timer.stop()
            
        
    
    def FlipDarkmode( self ):
        
        current_colourset = self._new_options.GetString( 'current_colourset' )
        
        if current_colourset == 'darkmode':
            
            new_colourset = 'default'
            
        elif current_colourset == 'default':
            
            new_colourset = 'darkmode'
            
        
        self._new_options.SetString( 'current_colourset', new_colourset )
        
        HG.client_controller.pub( 'notify_new_colourset' )
        
    
    def FlipNetworkTrafficPaused( self ):
        
        self._controller.network_engine.PausePlayNewJobs()
        
        self._UpdateSystemTrayIcon()
        
        self.DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def FlipSubscriptionsPaused( self ):
        
        HC.options[ 'pause_subs_sync' ] = not HC.options[ 'pause_subs_sync' ]
        
        self._controller.subscriptions_manager.Wake()
        
        self._controller.Write( 'save_options', HC.options )
        
        self._UpdateSystemTrayIcon()
        
        self.DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def GenerateMenuInfo( self, name ):
        
        def undo():
            
            have_closed_pages = len( self._closed_pages ) > 0
            
            undo_manager = self._controller.GetManager( 'undo' )
            
            ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
            
            have_undo_stuff = undo_string is not None or redo_string is not None
            
            if have_closed_pages or have_undo_stuff:
                
                menu = QW.QMenu( self )
                
                if undo_string is not None:
                    ClientGUIMenus.AppendMenuItem( menu, undo_string, 'Undo last operation.', self._controller.pub, 'undo' )
                    
                
                if redo_string is not None:
                    ClientGUIMenus.AppendMenuItem( menu, redo_string, 'Redo last operation.', self._controller.pub, 'redo' )
                    
                
                if have_closed_pages:
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                    undo_pages = QW.QMenu( menu )
                    
                    ClientGUIMenus.AppendMenuItem( undo_pages, 'clear all', 'Remove all closed pages from memory.', self.DeleteAllClosedPages )
                    
                    undo_pages.addSeparator()
                    
                    args = []
                    
                    for ( i, ( time_closed, page ) ) in enumerate( self._closed_pages ):
                        
                        name = page.GetName()
                        
                        args.append( ( i, name + ' - ' + page.GetPrettyStatus() ) )
                        
                    
                    args.reverse() # so that recently closed are at the top
                    
                    for ( index, name ) in args:
                        
                        ClientGUIMenus.AppendMenuItem( undo_pages, name, 'Restore this page.', self._UnclosePage, index )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, undo_pages, 'closed pages' )
                    
                
            else:
                
                menu = None
                
            
            return ( menu, '&undo' )
            
        
        def database():
            
            menu = QW.QMenu( self )
            
            ClientGUIMenus.AppendMenuItem( menu, 'set a password', 'Set a simple password for the database so only you can open it in the client.', self._SetPassword )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if HG.client_controller.client_files_manager.AllLocationsAreDefault():
                
                backup_path = self._new_options.GetNoneableString( 'backup_path' )
                
                if backup_path is None:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'set up a database backup location', 'Choose a path to back the database up to.', self._SetupBackupPath )
                    
                else:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'update database backup', 'Back the database up to an external location.', self._BackupDatabase )
                    ClientGUIMenus.AppendMenuItem( menu, 'change database backup location', 'Choose a path to back the database up to.', self._SetupBackupPath )
                    
                
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( menu, 'restore from a database backup', 'Restore the database from an external location.', self._controller.RestoreDatabase )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            ClientGUIMenus.AppendMenuItem( menu, 'migrate database', 'Review and manage the locations your database is stored.', self._MigrateDatabase )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = QW.QMenu( menu )
            
            file_maintenance_menu = QW.QMenu( submenu )
            
            ClientGUIMenus.AppendMenuItem( file_maintenance_menu, 'manage scheduled jobs', 'Review outstanding jobs, and schedule new ones.', self._ReviewFileMaintenance )
            ClientGUIMenus.AppendSeparator( file_maintenance_menu )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'file_maintenance_during_idle' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( file_maintenance_menu, 'work file jobs during idle time', 'Control whether file maintenance can work during idle time.', current_value, func )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'file_maintenance_during_active' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( file_maintenance_menu, 'work file jobs during normal time', 'Control whether file maintenance can work during normal time.', current_value, func )
            
            ClientGUIMenus.AppendMenu( submenu, file_maintenance_menu, 'files' )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'vacuum', 'Defrag the database by completely rebuilding it.', self._VacuumDatabase )
            ClientGUIMenus.AppendMenuItem( submenu, 'analyze', 'Optimise slow queries by running statistical analyses on the database.', self._AnalyzeDatabase )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'clear orphan files', 'Clear out surplus files that have found their way into the file structure.', self._ClearOrphanFiles )
            ClientGUIMenus.AppendMenuItem( submenu, 'clear orphan file records', 'Clear out surplus file records that have not been deleted correctly.', self._ClearOrphanFileRecords )
            
            if self._controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( submenu, 'clear orphan tables', 'Clear out surplus db tables that have not been deleted correctly.', self._ClearOrphanTables )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'maintainance' )
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'database integrity', 'Have the database examine all its records for internal consistency.', self._CheckDBIntegrity )
            ClientGUIMenus.AppendMenuItem( submenu, 'repopulate truncated mappings tables', 'Use the mappings cache to try to repair a previously damaged mappings file.', self._RepopulateMappingsTables )
            ClientGUIMenus.AppendMenuItem( submenu, 'fix invalid tags', 'Scan the database for invalid tags.', self._RepairInvalidTags )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'check and repair' )
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'tag storage mappings cache', 'Delete and recreate the tag mappings cache, fixing any miscounts.', self._RegenerateTagMappingsCache )
            ClientGUIMenus.AppendMenuItem( submenu, 'tag display mappings cache', 'Delete and recreate the tag display mappings cache, fixing any miscounts.', self._RegenerateTagDisplayMappingsCache )
            ClientGUIMenus.AppendMenuItem( submenu, 'tag siblings lookup cache', 'Delete and recreate the tag siblings cache.', self._RegenerateTagSiblingsLookupCache )
            ClientGUIMenus.AppendMenuItem( submenu, 'tag parents lookup cache', 'Delete and recreate the tag siblings cache.', self._RegenerateTagParentsLookupCache )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'clear service info cache', 'Delete all cached service info like total number of mappings or files, in case it has become desynchronised. Some parts of the gui may be laggy immediately after this as these numbers are recalculated.', self._DeleteServiceInfo )
            ClientGUIMenus.AppendMenuItem( submenu, 'similar files search tree', 'Delete and recreate the similar files search tree.', self._RegenerateSimilarFilesTree )
            ClientGUIMenus.AppendMenuItem( submenu, 'tag definition search cache', 'Repopulate the cache hydrus uses for fast tag search.', self._RepopulateTagSearchCache )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'regenerate' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'clear all file viewing statistics', 'Delete all file viewing records from the database.', self._ClearFileViewingStats )
            ClientGUIMenus.AppendMenuItem( submenu, 'cull file viewing statistics based on current min/max values', 'Cull your file viewing statistics based on minimum and maximum permitted time deltas.', self._CullFileViewingStats )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file viewing statistics' )
            
            return ( menu, '&database' )
            
        
        def network():
            
            menu = QW.QMenu( self )
            
            submenu = QW.QMenu( menu )
            
            pause_all_new_network_traffic = self._controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
            
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'all new network traffic', 'Stop any new network jobs from sending data.', pause_all_new_network_traffic, self.FlipNetworkTrafficPaused )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'subscriptions', 'Pause the client\'s synchronisation with website subscriptions.', HC.options[ 'pause_subs_sync' ], self.FlipSubscriptionsPaused )
            
            if self._controller.new_options.GetBoolean( 'advanced_mode' ):
                
                ClientGUIMenus.AppendMenuItem( submenu, 'nudge subscriptions awake', 'Tell the subs daemon to wake up, just in case any subs are due.', self._controller.subscriptions_manager.Wake )
                
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'paged file import queues', 'Pause all file import queues.', self._controller.new_options.GetBoolean( 'pause_all_file_queues' ), self._controller.new_options.FlipBoolean, 'pause_all_file_queues' )
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'gallery searches', 'Pause all gallery imports\' searching.', self._controller.new_options.GetBoolean( 'pause_all_gallery_searches' ), self._controller.new_options.FlipBoolean, 'pause_all_gallery_searches' )
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'watcher checkers', 'Pause all watchers\' checking.', self._controller.new_options.GetBoolean( 'pause_all_watcher_checkers' ), self._controller.new_options.FlipBoolean, 'pause_all_watcher_checkers' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage subscriptions', 'Change the queries you want the client to regularly import from.', self._ManageSubscriptions )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'review bandwidth usage', 'See where you are consuming data.', self._ReviewBandwidth )
            ClientGUIMenus.AppendMenuItem( submenu, 'review current network jobs', 'Review the jobs currently running in the network engine.', self._ReviewNetworkJobs )
            ClientGUIMenus.AppendMenuItem( submenu, 'review session cookies', 'Review and edit which cookies you have for which network contexts.', self._ReviewNetworkSessions )
            ClientGUIMenus.AppendMenuItem( submenu, 'manage http headers', 'Configure how the client talks to the network.', self._ManageNetworkHeaders )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage upnp', 'If your router supports it, see and edit your current UPnP NAT traversal mappings.', self._ManageUPnP )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'data' )
            
            #
            
            submenu = QW.QMenu( menu )
            
            if not ClientParsing.HTML5LIB_IS_OK:
                
                message = 'The client was unable to import html5lib on boot. This is an important parsing library that performs better than the usual backup, lxml. Without it, some downloaders will not work well and you will miss tags and files.'
                message += os.linesep * 2
                message += 'You are likely running from source, so I recommend you close the client, run \'pip install html5lib\' (or whatever is appropriate for your environment) and try again. You can double-check what imported ok under help->about.'
                
                ClientGUIMenus.AppendMenuItem( submenu, '*** html5lib not found! ***', 'Your client does not have an important library.', QW.QMessageBox.warning, self, 'Warning', message )
                
                ClientGUIMenus.AppendSeparator( submenu )
                
            
            ClientGUIMenus.AppendMenuItem( submenu, 'import downloaders', 'Import new download capability through encoded pngs from other users.', self._ImportDownloaders )
            ClientGUIMenus.AppendMenuItem( submenu, 'export downloaders', 'Export downloader components to easy-import pngs.', self._ExportDownloader )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage default tag import options', 'Change the default tag import options for each of your linked url matches.', self._ManageDefaultTagImportOptions )
            ClientGUIMenus.AppendMenuItem( submenu, 'manage downloader and url display', 'Configure how downloader objects present across the client.', self._ManageDownloaderDisplay )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            clipboard_menu = QW.QMenu( submenu )
            
            ClientGUIMenus.AppendMenuCheckItem( clipboard_menu, 'watcher urls', 'Automatically import watcher URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_watcher_urls' )
            ClientGUIMenus.AppendMenuCheckItem( clipboard_menu, 'other recognised urls', 'Automatically import recognised URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_other_recognised_urls' )
            
            ClientGUIMenus.AppendMenu( submenu, clipboard_menu, 'watch clipboard for urls' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'downloaders' )
            
            #
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage url class links', 'Configure how URLs present across the client.', self._ManageURLClassLinks )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage gallery url generators', 'Manage the client\'s GUGs, which convert search terms into URLs.', self._ManageGUGs )
            ClientGUIMenus.AppendMenuItem( submenu, 'manage url classes', 'Configure which URLs the client can recognise.', self._ManageURLClasses )
            ClientGUIMenus.AppendMenuItem( submenu, 'manage parsers', 'Manage the client\'s parsers, which convert URL content into hydrus metadata.', self._ManageParsers )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'SEMI-LEGACY: manage file lookup scripts', 'Manage how the client parses different types of web content.', self._ManageParsingScripts )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'downloader components' )
            
            #
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage logins', 'Edit which domains you wish to log in to.', self._ManageLogins )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'manage login scripts', 'Manage the client\'s login scripts, which define how to log in to different sites.', self._ManageLoginScripts )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'DEBUG: do tumblr GDPR click-through', 'Do a manual click-through for the tumblr GDPR page.', self._controller.CallLater, 0.0, self._controller.network_engine.login_manager.LoginTumblrGDPR )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'logins' )
            
            #
            
            return ( menu, '&network' )
            
        
        def services():
            
            menu = QW.QMenu( self )
            
            tag_services = self._controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
            file_services = self._controller.services_manager.GetServices( ( HC.FILE_REPOSITORY, ) )
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuCheckItem( submenu, 'repositories synchronisation', 'Pause the client\'s synchronisation with hydrus repositories.', HC.options['pause_repo_sync'], self._PausePlaySync, 'repo' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'review services', 'Look at the services your client connects to.', self._ReviewServices )
            ClientGUIMenus.AppendMenuItem( menu, 'manage services', 'Edit the services your client connects to.', self._ManageServices )
            
            repository_admin_permissions = [ ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE ), ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ), ( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE ) ]
            
            repositories = self._controller.services_manager.GetServices( HC.REPOSITORIES )
            admin_repositories = [ service for service in repositories if True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_admin_permissions ) ]
            
            servers_admin = self._controller.services_manager.GetServices( ( HC.SERVER_ADMIN, ) )
            server_admins = [ service for service in servers_admin if service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE ) ]
            
            if len( admin_repositories ) > 0 or len( server_admins ) > 0:
                
                admin_menu = QW.QMenu( menu )
                
                for service in admin_repositories:
                    
                    submenu = QW.QMenu( admin_menu )
                    
                    service_key = service.GetServiceKey()
                    
                    can_create_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
                    can_overrule_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
                    can_overrule_account_types = service.HasPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_create_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'create new accounts', 'Create new account keys for this service.', self._GenerateNewAccounts, service_key )
                        
                    
                    if can_overrule_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'modify an account', 'Modify a specific account\'s type and expiration.', self._ModifyAccount, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'get an account\'s info', 'Fetch information about an account from the service.', self._AccountInfo, service_key )
                        
                    
                    if can_overrule_accounts and service.GetServiceType() == HC.FILE_REPOSITORY:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'get an uploader\'s ip address', 'Fetch the ip address that uploaded a specific file, if the service knows it.', self._FetchIP, service_key )
                        
                    
                    if can_overrule_account_types:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'manage account types', 'Add, edit and delete account types for this service.', self._ManageAccountTypes, service_key )
                        
                    
                    ClientGUIMenus.AppendMenu( admin_menu, submenu, service.GetName() )
                    
                
                for service in server_admins:
                    
                    submenu = QW.QMenu( admin_menu )
                    
                    service_key = service.GetServiceKey()
                    
                    can_create_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
                    can_overrule_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
                    can_overrule_account_types = service.HasPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_create_accounts:
                        ClientGUIMenus.AppendMenuItem( submenu, 'create new accounts', 'Create new account keys for this service.', self._GenerateNewAccounts, service_key )
                        
                    
                    if can_overrule_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'modify an account', 'Modify a specific account\'s type and expiration.', self._ModifyAccount, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'get an account\'s info', 'Fetch information about an account from the service.', self._AccountInfo, service_key )
                        
                    
                    if can_overrule_account_types:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'manage account types', 'Add, edit and delete account types for this service.', self._ManageAccountTypes, service_key )
                        
                    
                    can_overrule_services = service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE )
                    
                    if can_overrule_services:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'manage services', 'Add, edit, and delete this server\'s services.', self._ManageServer, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'backup server', 'Command the server to temporarily pause and back up its database.', self._BackupServer, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'vacuum server', 'Command the server to temporarily pause and vacuum its database.', self._VacuumServer, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: on', 'Command the server to lock itself and disconnect its db.', self._LockServer, service_key, True )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: test', 'See if the server is currently busy.', self._TestServerBusy, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: off', 'Command the server to unlock itself and resume its db.', self._LockServer, service_key, False )
                        
                    
                    ClientGUIMenus.AppendMenu( admin_menu, submenu, service.GetName() )
                    
                
                ClientGUIMenus.AppendMenu( menu, admin_menu, 'administrate services' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'import repository update files', 'Add repository update files to the database.', self._ImportUpdateFiles )
            
            return ( menu, '&services' )
            
        
        def tags():
            
            menu = QW.QMenu( self )
            
            ClientGUIMenus.AppendMenuItem( menu, 'migrate tags', 'Migrate tags from one place to another.', self._MigrateTags )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage tag display and search', 'Set which tags you want to see from which services.', self._ManageTagDisplay )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage tag siblings', 'Set certain tags to be automatically replaced with other tags.', self._ManageTagSiblings )
            ClientGUIMenus.AppendMenuItem( menu, 'manage tag parents', 'Set certain tags to be automatically added with other tags.', self._ManageTagParents )
            
            ClientGUIMenus.AppendMenuItem( menu, 'manage where tag siblings and parents apply', 'Set which services\' siblings and parents apply where.', self._ManageTagDisplayApplication )
            
            #
            
            tag_display_maintenance_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( tag_display_maintenance_menu, 'review tag sibling/parent maintenance', 'See how siblings and parents are currently applied.', self._ReviewTagDisplayMaintenance )
            ClientGUIMenus.AppendSeparator( tag_display_maintenance_menu )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'tag_display_maintenance_during_idle' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( tag_display_maintenance_menu, 'sync tag display during idle time', 'Control whether tag display maintenance can work during idle time.', current_value, func )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'tag_display_maintenance_during_active' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( tag_display_maintenance_menu, 'sync tag display during normal time', 'Control whether tag display maintenance can work during normal time.', current_value, func )
            
            ClientGUIMenus.AppendMenu( menu, tag_display_maintenance_menu, 'sibling/parent sync' )
            
            #
            
            return ( menu, '&tags' )
            
        
        def help():
            
            menu = QW.QMenu( self )
            
            ClientGUIMenus.AppendMenuItem( menu, 'help and getting started guide', 'Open hydrus\'s local help in your web browser.', ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'index.html' ) )
            
            links = QW.QMenu( menu )
            
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'site', 'Open hydrus\'s website, which is mostly a mirror of the local help.', CC.global_pixmaps().file_repository, ClientPaths.LaunchURLInWebBrowser, 'https://hydrusnetwork.github.io/hydrus/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'github repository', 'Open the hydrus github repository.', CC.global_pixmaps().github, ClientPaths.LaunchURLInWebBrowser, 'https://github.com/hydrusnetwork/hydrus' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'issue tracker', 'Open the github issue tracker, which is run by users.', CC.global_pixmaps().github, ClientPaths.LaunchURLInWebBrowser, 'https://github.com/hydrusnetwork/hydrus/issues' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, '8kun board', 'Open hydrus dev\'s 8kun board, where he makes release posts and other status updates.', CC.global_pixmaps().eight_kun, ClientPaths.LaunchURLInWebBrowser, 'https://8kun.top/hydrus/index.html' )
            site = ClientGUIMenus.AppendMenuItem( links, 'Endchan board bunker', 'Open hydrus dev\'s Endchan board, the bunker for when 8kun is unavailable. Try .org if .net is unavailable.', ClientPaths.LaunchURLInWebBrowser, 'https://endchan.net/hydrus/index.html' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'twitter', 'Open hydrus dev\'s twitter, where he makes general progress updates and emergency notifications.', CC.global_pixmaps().twitter, ClientPaths.LaunchURLInWebBrowser, 'https://twitter.com/hydrusnetwork' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'tumblr', 'Open hydrus dev\'s tumblr, where he makes release posts and other status updates.', CC.global_pixmaps().tumblr, ClientPaths.LaunchURLInWebBrowser, 'https://hydrus.tumblr.com/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'discord', 'Open a discord channel where many hydrus users congregate. Hydrus dev visits regularly.', CC.global_pixmaps().discord, ClientPaths.LaunchURLInWebBrowser, 'https://discord.gg/wPHPCUZ' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'patreon', 'Open hydrus dev\'s patreon, which lets you support development.', CC.global_pixmaps().patreon, ClientPaths.LaunchURLInWebBrowser, 'https://www.patreon.com/hydrus_dev' )
            
            ClientGUIMenus.AppendMenu( menu, links, 'links' )
            
            ClientGUIMenus.AppendMenuItem( menu, 'changelog', 'Open hydrus\'s local changelog in your web browser.', ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'changelog.html' ) )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'add the public tag repository', 'This will add the public tag repository to your client.', self._AutoRepoSetup )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'how boned am I?', 'Check for a summary of your ride so far.', self._HowBonedAmI )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            currently_darkmode = self._new_options.GetString( 'current_colourset' ) == 'darkmode'
            
            ClientGUIMenus.AppendMenuCheckItem( menu, 'darkmode', 'Set the \'darkmode\' colourset on and off.', currently_darkmode, self.FlipDarkmode )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'advanced_mode' )
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            ClientGUIMenus.AppendMenuCheckItem( menu, 'advanced mode', 'Turn on advanced menu options and buttons.', current_value, func )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            debug = QW.QMenu( menu )
            
            debug_modes = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuCheckItem( debug_modes, 'force idle mode', 'Make the client consider itself idle and fire all maintenance routines right now. This may hang the gui for a while.', HG.force_idle_mode, self._SwitchBoolean, 'force_idle_mode' )
            ClientGUIMenus.AppendMenuCheckItem( debug_modes, 'no page limit mode', 'Let the user create as many pages as they want with no warnings or prohibitions.', HG.no_page_limit_mode, self._SwitchBoolean, 'no_page_limit_mode' )
            ClientGUIMenus.AppendMenuCheckItem( debug_modes, 'thumbnail debug mode', 'Show some thumbnail debug info.', HG.thumbnail_debug_mode, self._SwitchBoolean, 'thumbnail_debug_mode' )
            ClientGUIMenus.AppendMenuItem( debug_modes, 'simulate a wake from sleep', 'Tell the controller to pretend that it just woke up from sleep.', self._controller.SimulateWakeFromSleepEvent )
            
            ClientGUIMenus.AppendMenu( debug, debug_modes, 'debug modes' )
            
            profile_modes = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuCheckItem( profile_modes, 'db profile mode', 'Run detailed \'profiles\' on every database query and dump this information to the log (this is very useful for hydrus dev to have, if something is running slow for you!).', HG.db_profile_mode, self._SwitchBoolean, 'db_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( profile_modes, 'menu profile mode', 'Run detailed \'profiles\' on menu actions.', HG.menu_profile_mode, self._SwitchBoolean, 'menu_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( profile_modes, 'pubsub profile mode', 'Run detailed \'profiles\' on every internal publisher/subscriber message and dump this information to the log. This can hammer your log with dozens of large dumps every second. Don\'t run it unless you know you need to.', HG.pubsub_profile_mode, self._SwitchBoolean, 'pubsub_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( profile_modes, 'ui timer profile mode', 'Run detailed \'profiles\' on every ui timer update. This will likely spam you!', HG.ui_timer_profile_mode, self._SwitchBoolean, 'ui_timer_profile_mode' )
            
            ClientGUIMenus.AppendMenu( debug, profile_modes, 'profile modes' )
            
            report_modes = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'callto report mode', 'Report whenever the thread pool is given a task.', HG.callto_report_mode, self._SwitchBoolean, 'callto_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'daemon report mode', 'Have the daemons report whenever they fire their jobs.', HG.daemon_report_mode, self._SwitchBoolean, 'daemon_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'db report mode', 'Have the db report query information, where supported.', HG.db_report_mode, self._SwitchBoolean, 'db_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'file import report mode', 'Have the db and file manager report file import progress.', HG.file_import_report_mode, self._SwitchBoolean, 'file_import_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'file report mode', 'Have the file manager report file request information, where supported.', HG.file_report_mode, self._SwitchBoolean, 'file_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'gui report mode', 'Have the gui report inside information, where supported.', HG.gui_report_mode, self._SwitchBoolean, 'gui_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'hover window report mode', 'Have the hover windows report their show/hide logic.', HG.hover_window_report_mode, self._SwitchBoolean, 'hover_window_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'media load report mode', 'Have the client report media load information, where supported.', HG.media_load_report_mode, self._SwitchBoolean, 'media_load_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'network report mode', 'Have the network engine report new jobs.', HG.network_report_mode, self._SwitchBoolean, 'network_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'pubsub report mode', 'Report info about every pubsub processed.', HG.pubsub_report_mode, self._SwitchBoolean, 'pubsub_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'similar files metadata generation report mode', 'Have the phash generation routine report its progress.', HG.phash_generation_report_mode, self._SwitchBoolean, 'phash_generation_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'shortcut report mode', 'Have the new shortcut system report what shortcuts it catches and whether it matches an action.', HG.shortcut_report_mode, self._SwitchBoolean, 'shortcut_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'subprocess report mode', 'Report whenever an external process is called.', HG.subprocess_report_mode, self._SwitchBoolean, 'subprocess_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( report_modes, 'subscription report mode', 'Have the subscription system report what it is doing.', HG.subscription_report_mode, self._SwitchBoolean, 'subscription_report_mode' )
            
            ClientGUIMenus.AppendMenu( debug, report_modes, 'report modes' )
            
            gui_actions = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make some popups', 'Throw some varied popups at the message manager, just to check it is working.', self._DebugMakeSomePopups )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a long text popup', 'Make a popup with text that will grow in size.', self._DebugLongTextPopup )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a popup in five seconds', 'Throw a delayed popup at the message manager, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, HydrusData.ShowText, 'This is a delayed popup message.' )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a modal popup in five seconds', 'Throw up a delayed modal popup to test with. It will stay alive for five seconds.', self._DebugMakeDelayedModalPopup, True )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a non-cancellable modal popup in five seconds', 'Throw up a delayed modal popup to test with. It will stay alive for five seconds.', self._DebugMakeDelayedModalPopup, False )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a new page in five seconds', 'Throw a delayed page at the main notebook, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, self._controller.pub, 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'refresh pages menu in five seconds', 'Delayed refresh the pages menu, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, self._menu_updater_pages.update )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'publish some sub files in five seconds', 'Publish some files like a subscription would.', self._controller.CallLater, 5, lambda: HG.client_controller.pub( 'imported_files_to_page', [ HydrusData.GenerateKey() for i in range( 5 ) ], 'example sub files' ) )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'make a parentless text ctrl dialog', 'Make a parentless text control in a dialog to test some character event catching.', self._DebugMakeParentlessTextCtrl )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'force a main gui layout now', 'Tell the gui to relayout--useful to test some gui bootup layout issues.', self.adjustSize )
            ClientGUIMenus.AppendMenuItem( gui_actions, 'save \'last session\' gui session', 'Make an immediate save of the \'last session\' gui session. Mostly for testing crashes, where last session is not saved correctly.', self.ProposeSaveGUISession, 'last session' )
            
            ClientGUIMenus.AppendMenu( debug, gui_actions, 'gui actions' )
            
            data_actions = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuCheckItem( data_actions, 'db ui-hang relief mode', 'Have UI-synchronised database jobs process pending Qt events while they wait.', HG.db_ui_hang_relief_mode, self._SwitchBoolean, 'db_ui_hang_relief_mode' )
            ClientGUIMenus.AppendMenuItem( data_actions, 'review threads', 'Show current threads and what they are doing.', self._ReviewThreads )
            ClientGUIMenus.AppendMenuItem( data_actions, 'show scheduled jobs', 'Print some information about the currently scheduled jobs log.', self._DebugShowScheduledJobs )
            ClientGUIMenus.AppendMenuItem( data_actions, 'subscription manager snapshot', 'Have the subscription system show what it is doing.', self._controller.subscriptions_manager.ShowSnapshot )
            ClientGUIMenus.AppendMenuItem( data_actions, 'flush log', 'Command the log to write any buffered contents to hard drive.', HydrusData.DebugPrint, 'Flushing log' )
            ClientGUIMenus.AppendMenuItem( data_actions, 'enable truncated image loading', 'Enable the truncated image loading to test out broken jpegs.', self._EnableLoadTruncatedImages )
            
            ClientGUIMenus.AppendMenu( debug, data_actions, 'data actions' )
            
            memory_actions = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuItem( memory_actions, 'run fast memory maintenance', 'Tell all the fast caches to maintain themselves.', self._controller.MaintainMemoryFast )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'run slow memory maintenance', 'Tell all the slow caches to maintain themselves.', self._controller.MaintainMemorySlow )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'clear image rendering cache', 'Tell the image rendering system to forget all current images. This will often free up a bunch of memory immediately.', self._controller.ClearCaches )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'clear thumbnail cache', 'Tell the thumbnail cache to forget everything and redraw all current thumbs.', self._controller.pub, 'reset_thumbnail_cache' )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'print garbage', 'Print some information about the python garbage to the log.', self._DebugPrintGarbage )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'take garbage snapshot', 'Capture current garbage object counts.', self._DebugTakeGarbageSnapshot )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'show garbage snapshot changes', 'Show object count differences from the last snapshot.', self._DebugShowGarbageDifferences )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'load whole db in disk cache', 'Contiguously read as much of the db as will fit into memory. This will massively speed up any subsequent big job.', self._controller.CallToThread, self._controller.Read, 'load_into_disk_cache' )
            
            ClientGUIMenus.AppendMenu( debug, memory_actions, 'memory actions' )
            
            network_actions = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuItem( network_actions, 'fetch a url', 'Fetch a URL using the network engine as per normal.', self._DebugFetchAURL )
            
            ClientGUIMenus.AppendMenu( debug, network_actions, 'network actions' )
            
            tests = QW.QMenu( debug )
            
            ClientGUIMenus.AppendMenuItem( tests, 'run the ui test', 'Run hydrus_dev\'s weekly UI Test. Guaranteed to work and not mess up your session, ha ha.', self._RunUITest )
            ClientGUIMenus.AppendMenuItem( tests, 'run the client api test', 'Run hydrus_dev\'s weekly Client API Test. Guaranteed to work and not mess up your session, ha ha.', self._RunClientAPITest )
            ClientGUIMenus.AppendMenuItem( tests, 'run the server test', 'This will try to boot the server in your install folder and initialise it. This is mostly here for testing purposes.', self._RunServerTest )
            
            ClientGUIMenus.AppendMenu( debug, tests, 'tests, do not touch' )
            
            ClientGUIMenus.AppendMenu( menu, debug, 'debug' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'about Qt', 'See information about the Qt framework.', QW.QMessageBox.aboutQt, self )
            ClientGUIMenus.AppendMenuItem( menu, 'about', 'See this client\'s version and other information.', self._AboutWindow )
            
            return ( menu, '&help' )
            
        
        if name == 'undo': result = undo()
        elif name == 'database': result = database()
        elif name == 'network': result = network()
        elif name == 'services': result = services()
        elif name == 'tags': result = tags()
        elif name == 'help': result = help()
        
        # hackery dackery doo
        ( menu_or_none, label ) = result
        
        return ( menu_or_none, label )
        
    
    def GenerateMenuInfoFile( self, import_folder_names, export_folder_names ):
        
        menu = QW.QMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'import files', 'Add new files to the database.', self._ImportFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        #
        
        i_and_e_submenu = QW.QMenu( menu )
        
        submenu = QW.QMenu( i_and_e_submenu )
        
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'import folders', 'Pause the client\'s import folders.', HC.options['pause_import_folders_sync'], self._PausePlaySync, 'import_folders' )
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'export folders', 'Pause the client\'s export folders.', HC.options['pause_export_folders_sync'], self._PausePlaySync, 'export_folders' )
        
        ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'pause' )
        
        ClientGUIMenus.AppendSeparator( i_and_e_submenu )
        
        if len( import_folder_names ) > 0:
            
            submenu = QW.QMenu( i_and_e_submenu )
            
            if len( import_folder_names ) > 1:
                
                ClientGUIMenus.AppendMenuItem( submenu, 'check all', 'Check all import folders.', self._CheckImportFolder )
                
                ClientGUIMenus.AppendSeparator( submenu )
                
            
            for name in import_folder_names:
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Check this import folder now.', self._CheckImportFolder, name )
                
            
            ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'check import folder now' )
            
        
        if len( export_folder_names ) > 0:
            
            submenu = QW.QMenu( i_and_e_submenu )
            
            if len( export_folder_names ) > 1:
                
                ClientGUIMenus.AppendMenuItem( submenu, 'run all', 'Run all export folders.', self._RunExportFolder )
                
                ClientGUIMenus.AppendSeparator( submenu )
                
            
            for name in export_folder_names:
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Run this export folder now.', self._RunExportFolder, name )
                
            
            ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'run export folder now' )
            
        
        ClientGUIMenus.AppendSeparator( i_and_e_submenu )
        
        ClientGUIMenus.AppendMenuItem( i_and_e_submenu, 'manage import folders', 'Manage folders from which the client can automatically import.', self._ManageImportFolders )
        ClientGUIMenus.AppendMenuItem( i_and_e_submenu, 'manage export folders', 'Manage folders to which the client can automatically export.', self._ManageExportFolders )
        
        ClientGUIMenus.AppendMenu( menu, i_and_e_submenu, 'import and export folders' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        open = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( open, 'installation directory', 'Open the installation directory for this client.', self._OpenInstallFolder )
        ClientGUIMenus.AppendMenuItem( open, 'database directory', 'Open the database directory for this instance of the client.', self._OpenDBFolder )
        ClientGUIMenus.AppendMenuItem( open, 'quick export directory', 'Open the export directory so you can easily access the files you have exported.', self._OpenExportFolder )
        
        ClientGUIMenus.AppendMenu( menu, open, 'open' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'options', 'Change how the client operates.', self._ManageOptions )
        ClientGUIMenus.AppendMenuItem( menu, 'shortcuts', 'Edit the shortcuts your client responds to.', ClientGUIShortcutControls.ManageShortcuts, self )
        
        if ClientGUISystemTray.SystemTrayAvailable() and not ( not HC.PLATFORM_WINDOWS and not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) ):
            
            ClientGUIMenus.AppendSeparator( menu )
            
            label = 'minimise to system tray'
            
            if not HC.PLATFORM_WINDOWS:
                
                label += ' (may be buggy/crashy!)'
                
            
            ClientGUIMenus.AppendMenuItem( menu, label, 'Hide the client to an icon on your system tray.', self._FlipShowHideWholeUI )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        we_borked_linux_pyinstaller = HC.PLATFORM_LINUX and not HC.RUNNING_FROM_SOURCE
        
        if not we_borked_linux_pyinstaller:
            
            ClientGUIMenus.AppendMenuItem( menu, 'restart', 'Shut the client down and then start it up again.', self.TryToExit, restart = True )
            
        
        ClientGUIMenus.AppendMenuItem( menu, 'exit and force shutdown maintenance', 'Shut the client down and force any outstanding shutdown maintenance to run.', self.TryToExit, force_shutdown_maintenance = True )
        
        ClientGUIMenus.AppendMenuItem( menu, 'exit', 'Shut the client down.', self.TryToExit )
        
        return ( menu, '&file' )
        
    
    def GenerateMenuInfoPages( self, gui_session_names, gui_session_names_to_backup_timestamps ):
        
        menu = QW.QMenu( self )
        
        ( total_active_page_count, total_closed_page_count, total_active_weight, total_closed_weight ) = self.GetTotalPageCounts()
        
        self._last_total_page_weight = total_active_weight + total_closed_weight
        
        ClientGUIMenus.AppendMenuLabel( menu, '{} pages open'.format( HydrusData.ToHumanInt( total_active_page_count ) ), 'You have this many pages open.' )
        ClientGUIMenus.AppendMenuLabel( menu, 'total session weight: {}'.format( HydrusData.ToHumanInt( self._last_total_page_weight ) ), 'Your session is this heavy.' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'refresh', 'If the current page has a search, refresh it.', self._Refresh )
        
        splitter_menu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'show/hide', 'Show or hide the panels on the left.', self._ShowHideSplitters )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuCheckItem( splitter_menu, 'save current page\'s sash positions on client exit', 'Set whether sash position should be saved over on client exit.', self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ), self._new_options.FlipBoolean, 'saving_sash_positions_on_exit' )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'save current page\'s sash positions now', 'Save the current page\'s sash positions.', self._SaveSplitterPositions )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'restore all pages\' sash positions to saved value', 'Restore the current sash positions for all pages to the values that are saved.', self._RestoreSplitterPositions )
        
        ClientGUIMenus.AppendMenu( menu, splitter_menu, 'management and preview panels' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        sessions = QW.QMenu( menu )
        
        gui_session_names = sorted( gui_session_names )
        
        if len( gui_session_names ) > 0:
            
            load = QW.QMenu( sessions )
            
            for name in gui_session_names:
                
                ClientGUIMenus.AppendMenuItem( load, name, 'Close all other pages and load this session.', self._notebook.LoadGUISession, name )
                
            
            ClientGUIMenus.AppendMenu( sessions, load, 'clear and load' )
            
            append = QW.QMenu( sessions )
            
            for name in gui_session_names:
                
                ClientGUIMenus.AppendMenuItem( append, name, 'Append this session to whatever pages are already open.', self._notebook.AppendGUISession, name )
                
            
            ClientGUIMenus.AppendMenu( sessions, append, 'append' )
            
            if len( gui_session_names_to_backup_timestamps ) > 0:
                
                append_backup = QW.QMenu( sessions )
                
                rows = sorted( gui_session_names_to_backup_timestamps.items() )
                
                for ( name, timestamps ) in rows:
                    
                    submenu = QW.QMenu( append_backup )
                    
                    for timestamp in timestamps:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, HydrusData.ConvertTimestampToPrettyTime( timestamp ), 'Append this backup session to whatever pages are already open.', self._notebook.AppendGUISessionBackup, name, timestamp )
                        
                    
                    ClientGUIMenus.AppendMenu( append_backup, submenu, name )
                    
                
                ClientGUIMenus.AppendMenu( sessions, append_backup, 'append session backup' )
                
            
        
        save = QW.QMenu( sessions )
        
        for name in gui_session_names:
            
            if name in ClientGUIPages.RESERVED_SESSION_NAMES:
                
                continue
                
            
            ClientGUIMenus.AppendMenuItem( save, name, 'Save the existing open pages as a session.', self.ProposeSaveGUISession, name )
            
        
        ClientGUIMenus.AppendMenuItem( save, 'as new session', 'Save the existing open pages as a session.', self.ProposeSaveGUISession )
        
        ClientGUIMenus.AppendMenu( sessions, save, 'save' )
        
        if len( set( gui_session_names ).difference( ClientGUIPages.RESERVED_SESSION_NAMES ) ) > 0:
            
            delete = QW.QMenu( sessions )
            
            for name in gui_session_names:
                
                if name in ClientGUIPages.RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( delete, name, 'Delete this session.', self._DeleteGUISession, name )
                
            
            ClientGUIMenus.AppendMenu( sessions, delete, 'delete' )
            
        
        ClientGUIMenus.AppendMenu( menu, sessions, 'sessions' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pick a new page', 'Choose a new page to open.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_PAGE ) )
        
        #
        
        search_menu = QW.QMenu( menu )
        
        services = self._controller.services_manager.GetServices()
        
        petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ]
        
        repositories = [ service for service in services if service.GetServiceType() in HC.REPOSITORIES ]
        
        file_repositories = [ service for service in repositories if service.GetServiceType() == HC.FILE_REPOSITORY ]
        
        petition_resolvable_repositories = [ repository for repository in repositories if True in ( repository.HasPermission( content_type, action ) for ( content_type, action ) in petition_permissions ) ]
        
        ClientGUIMenus.AppendMenuItem( search_menu, 'my files', 'Open a new search tab for your files.', self._notebook.NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY, on_deepest_notebook=True )
        ClientGUIMenus.AppendMenuItem( search_menu, 'trash', 'Open a new search tab for your recently deleted files.', self._notebook.NewPageQuery, CC.TRASH_SERVICE_KEY, on_deepest_notebook=True )
        
        for service in file_repositories:
            
            ClientGUIMenus.AppendMenuItem( search_menu, service.GetName(), 'Open a new search tab for ' + service.GetName() + '.', self._notebook.NewPageQuery, service.GetServiceKey(), on_deepest_notebook=True )
            
        
        ClientGUIMenus.AppendMenu( menu, search_menu, 'new search page' )
        
        #
        
        if len( petition_resolvable_repositories ) > 0:
            
            petition_menu = QW.QMenu( menu )
            
            for service in petition_resolvable_repositories:
                
                ClientGUIMenus.AppendMenuItem( petition_menu, service.GetName(), 'Open a new petition page for ' + service.GetName() + '.', self._notebook.NewPagePetitions, service.GetServiceKey(), on_deepest_notebook=True )
                
            
            ClientGUIMenus.AppendMenu( menu, petition_menu, 'new petition page' )
            
        
        #
        
        download_menu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( download_menu, 'url download', 'Open a new tab to download some separate urls.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'watcher', 'Open a new tab to watch threads or other updating locations.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'gallery', 'Open a new tab to download from gallery sites.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'simple downloader', 'Open a new tab to download files from generic galleries or threads.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE ) )
        
        ClientGUIMenus.AppendMenu( menu, download_menu, 'new download page' )
        
        #
        
        has_ipfs = len( [ service for service in services if service.GetServiceType() == HC.IPFS ] )
        
        if has_ipfs:
            
            download_popup_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( download_popup_menu, 'an ipfs multihash', 'Enter an IPFS multihash and attempt to import whatever is returned.', self._StartIPFSDownload )
            
            ClientGUIMenus.AppendMenu( menu, download_popup_menu, 'new download popup' )
            
        
        #
        
        special_menu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( special_menu, 'page of pages', 'Open a new tab that can hold more tabs.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_PAGE_OF_PAGES ) )
        ClientGUIMenus.AppendMenuItem( special_menu, 'duplicates processing', 'Open a new tab to discover and filter duplicate files.', self.ProcessApplicationCommand, CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_SIMPLE, CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE ) )
        
        ClientGUIMenus.AppendMenu( menu, special_menu, 'new special page' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        special_command_menu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( special_command_menu, 'clear all multiwatcher highlights', 'Command all multiwatcher pages to clear their highlighted watchers.', HG.client_controller.pub, 'clear_multiwatcher_highlights' )
        
        ClientGUIMenus.AppendMenu( menu, special_command_menu, 'special commands' )
        
        #
        
        return ( menu, '&pages' )
        
    
    def GenerateMenuInfoPending( self, nums_pending ):
        
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
                    
                    menu = QW.QMenu( self )
                    
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( submenu, 'commit', 'Upload ' + name + '\'s pending content.', self._UploadPending, service_key )
                ClientGUIMenus.AppendMenuItem( submenu, 'forget', 'Clear ' + name + '\'s pending content.', self._DeletePending, service_key )
                
                submessages = []
                
                if num_pending > 0:
                    
                    submessages.append( HydrusData.ToHumanInt( num_pending ) + ' ' + pending_phrase )
                    
                
                if num_petitioned > 0:
                    
                    submessages.append( HydrusData.ToHumanInt( num_petitioned ) + ' ' + petitioned_phrase )
                    
                
                message = name + ': ' + ', '.join( submessages )
                
                ClientGUIMenus.AppendMenu( menu, submenu, message )
                
            
            total_num_pending += num_pending + num_petitioned
            
        
        return ( menu, '&pending ({})'.format( HydrusData.ToHumanInt( total_num_pending ) ) )
        
    
    def GetCurrentPage( self ):
        
        return self._notebook.GetCurrentMediaPage()
        
    
    def GetCurrentSessionPageAPIInfoDict( self ):
        
        return self._notebook.GetSessionAPIInfoDict( is_selected = True )
        
    
    def GetMPVWidget( self, parent ):
        
        if len( self._persistent_mpv_widgets ) == 0:
            
            mpv_widget = ClientGUIMPV.mpvWidget( parent )
            
            self._persistent_mpv_widgets.append( mpv_widget )
            
        
        mpv_widget = self._persistent_mpv_widgets.pop()
        
        if mpv_widget.parentWidget() is self:
            
            mpv_widget.setParent( parent )
            
        
        return mpv_widget
        
    
    def GetPageAPIInfoDict( self, page_key, simple ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            return None
            
        else:
            
            return page.GetAPIInfoDict( simple )
            
        
    
    def GetTotalPageCounts( self ):
        
        total_active_page_count = self._notebook.GetNumPages()
        
        total_closed_page_count = len( self._closed_pages )
        
        total_active_weight = self._notebook.GetTotalWeight()
        total_closed_weight = sum( ( page.GetTotalWeight() for ( time_closed, page ) in self._closed_pages ) )
        
        return ( total_active_page_count, total_closed_page_count, total_active_weight, total_closed_weight )
        
    
    def HideToSystemTray( self ):
        
        shown = not self._currently_minimised_to_system_tray
        
        windows_or_advanced_mode = HC.PLATFORM_WINDOWS or HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        good_to_go = ClientGUISystemTray.SystemTrayAvailable() and windows_or_advanced_mode
        
        if shown and good_to_go:
            
            self._FlipShowHideWholeUI()
            
        
    
    def IShouldRegularlyUpdate( self, window ):
        
        current_page = self.GetCurrentPage()
        
        if current_page is not None:
            
            in_current_page = ClientGUIFunctions.IsQtAncestor( window, current_page )
            
            if in_current_page:
                
                return True
                
            
        
        in_other_window = window.window() != self
        
        return in_other_window
        
    
    def ImportFiles( self, paths ):
        
        # can more easily do this when file_seeds are doing their own tags
        
        # get current media page
        # if it is an import page, ask user if they want to add it to the page or make a new one
        # if using existing, then load the panel without file import options
        # think about how to merge 'delete_after_success' or not--maybe this can be handled by file_seeds as well
        
        self._ImportFiles( paths )
        
    
    def ImportURLFromAPI( self, url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page ):
        
        try:
            
            ( normalised_url, result_text ) = self._ImportURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags, destination_page_name = destination_page_name, destination_page_key = destination_page_key, show_destination_page = show_destination_page )
            
            return ( normalised_url, result_text )
            
        except ( HydrusExceptions.URLClassException, HydrusExceptions.NetworkException ):
            
            raise
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.BadRequestException( str( e ) )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            raise HydrusExceptions.ServerException( str( e ) )
            
        
    
    def ImportURLFromDragAndDrop( self, url ):
        
        try:
            
            self._ImportURL( url )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
    
    def ImportURL( self, url, destination_page_name ):
        
        try:
            
            self._ImportURL( url, destination_page_name = destination_page_name, show_destination_page = False )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
    
    def IsCurrentPage( self, page_key ):
        
        result = self._notebook.GetCurrentMediaPage()
        
        if result is None:
            
            return False
            
        else:
            
            return page_key == result.GetPageKey()
            
        
    
    def MaintainCanvasFrameReferences( self ):
        
        self._canvas_frames = [ frame for frame in self._canvas_frames if QP.isValid( frame ) ]
        
    
    def NewPageImportHDD( self, paths, file_import_options, paths_to_additional_service_keys_to_tags, delete_after_success ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportHDD( paths, file_import_options, paths_to_additional_service_keys_to_tags, delete_after_success )
        
        self._notebook.NewPage( management_controller, on_deepest_notebook = True )
        
    
    def NewPageQuery( self, service_key, initial_hashes = None, initial_predicates = None, page_name = None, do_sort = False, select_page = True, activate_window = False ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        self._notebook.NewPageQuery( service_key, initial_hashes = initial_hashes, initial_predicates = initial_predicates, page_name = page_name, on_deepest_notebook = True, do_sort = do_sort, select_page = select_page )
        
        if activate_window and not self.isActiveWindow():
            
            self.activateWindow()
            
        
    
    def NotifyClosedPage( self, page ):
        
        if self._clipboard_watcher_destination_page_urls == page:
            
            self._clipboard_watcher_destination_page_urls = None
            
        
        if self._clipboard_watcher_destination_page_watcher == page:
            
            self._clipboard_watcher_destination_page_watcher = None
            
        
        close_time = HydrusData.GetNow()
        
        self._closed_pages.append( ( close_time, page ) )
        
        self._controller.ClosePageKeys( page.GetPageKeys() )
        
        self._menu_updater_pages.update()
        
    
    def NotifyDeletedPage( self, page ):
        
        self._DestroyPages( ( page, ) )
        
        self._menu_updater_pages.update()
        
        self._menu_updater.Update()
        
    
    def NotifyNewExportFolders( self ):
        
        self._menu_updater_file.update()
        
        self._menu_updater.Update()
        
    
    def NotifyNewImportFolders( self ):
        
        self._menu_updater_file.update()
        
    
    def NotifyNewOptions( self ):
        
        self.DirtyMenu( 'database' )
        self.DirtyMenu( 'services' )
        self.DirtyMenu( 'help' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewPages( self ):
        
        self._menu_updater_pages.update()
        
    
    def NotifyNewPending( self ):
        
        self._menu_updater_pending.update()
        
    
    def NotifyNewPermissions( self ):
        
        self._menu_updater_pages.update()
        
        self.DirtyMenu( 'services' )
        self.DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewServices( self ):
        
        self._menu_updater_pages.update()
        
        self.DirtyMenu( 'services' )
        self.DirtyMenu( 'network' )
        
        self._menu_updater.Update()
        
    
    def NotifyNewSessions( self ):
        
        self._menu_updater_pages.update()
        
    
    def NotifyNewUndo( self ):
        
        self.DirtyMenu( 'undo' )
        
        self._menu_updater.Update()
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        self._notebook.PresentImportedFilesToPage( hashes, page_name )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        data = command.GetData()
        
        if command.IsSimpleCommand():
            
            action = data
            
            if action == CAC.SIMPLE_EXIT_APPLICATION:
                
                self.TryToExit()
                
            elif action == CAC.SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE:
                
                self.TryToExit( force_shutdown_maintenance = True )
                
            elif action == CAC.SIMPLE_RESTART_APPLICATION:
                
                self.TryToExit( restart = True )
                
            elif action == CAC.SIMPLE_HIDE_TO_SYSTEM_TRAY:
                
                self.HideToSystemTray()
                
            elif action == CAC.SIMPLE_MOVE_PAGES_SELECTION_LEFT:
                
                self._notebook.MoveSelection( -1 )
                
            elif action == CAC.SIMPLE_MOVE_PAGES_SELECTION_RIGHT:
                
                self._notebook.MoveSelection( 1 )
                
            elif action == CAC.SIMPLE_MOVE_PAGES_SELECTION_HOME:
                
                self._notebook.MoveSelectionEnd( -1 )
                
            elif action == CAC.SIMPLE_MOVE_PAGES_SELECTION_END:
                
                self._notebook.MoveSelectionEnd( 1 )
                
            elif action == CAC.SIMPLE_REFRESH:
                
                self._Refresh()
                
            elif action == CAC.SIMPLE_REFRESH_ALL_PAGES:
                
                self._notebook.RefreshAllPages()
                
            elif action == CAC.SIMPLE_REFRESH_PAGE_OF_PAGES_PAGES:
                
                page = self._notebook.GetCurrentMediaPage()
                
                if page is not None:
                    
                    parent = page.GetParentNotebook()
                    
                    parent.RefreshAllPages()
                    
                
            elif action == CAC.SIMPLE_NEW_PAGE:
                
                self._notebook.ChooseNewPageForDeepestNotebook()
                
            elif action == CAC.SIMPLE_NEW_PAGE_OF_PAGES:
                
                self._notebook.NewPagesNotebook( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE:
                
                self._notebook.NewPageDuplicateFilter( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE:
                
                self._notebook.NewPageImportGallery( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE:
                
                self._notebook.NewPageImportSimpleDownloader( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE:
                
                self._notebook.NewPageImportURLs( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE:
                
                self._notebook.NewPageImportMultipleWatcher( on_deepest_notebook = True )
                
            elif action == CAC.SIMPLE_CLOSE_PAGE:
                
                self._notebook.CloseCurrentPage()
                
            elif action == CAC.SIMPLE_UNCLOSE_PAGE:
                
                self._UnclosePage()
                
            elif action == CAC.SIMPLE_RUN_ALL_EXPORT_FOLDERS:
                
                self._RunExportFolder()
                
            elif action == CAC.SIMPLE_CHECK_ALL_IMPORT_FOLDERS:
                
                self._CheckImportFolder()
                
            elif action == CAC.SIMPLE_FLIP_DARKMODE:
                
                self.FlipDarkmode()
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, True )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_UNMUTE:
                
                ClientGUIMediaControls.SetMute( ClientGUIMediaControls.AUDIO_GLOBAL, False )
                
            elif action == CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP:
                
                ClientGUIMediaControls.FlipMute( ClientGUIMediaControls.AUDIO_GLOBAL )
                
            elif action == CAC.SIMPLE_SHOW_HIDE_SPLITTERS:
                
                self._ShowHideSplitters()
                
            elif action == CAC.SIMPLE_SYNCHRONISED_WAIT_SWITCH:
                
                self._PausePlaySearch()
                
            elif action == CAC.SIMPLE_SET_MEDIA_FOCUS:
                
                self._SetMediaFocus()
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            elif action == CAC.SIMPLE_REDO:
                
                self._controller.pub( 'redo' )
                
            elif action == CAC.SIMPLE_UNDO:
                
                self._controller.pub( 'undo' )
                
            elif action == CAC.SIMPLE_FLIP_DEBUG_FORCE_IDLE_MODE_DO_NOT_SET_THIS:
                
                self._SwitchBoolean( 'force_idle_mode' )
                
                self.DirtyMenu( 'help' )
                
                self._menu_updater.Update()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ProposeSaveGUISession( self, name = None, suggested_name = '', notebook = None ):
        
        if notebook is None:
            
            notebook = self._notebook
            
        
        if name is None:
            
            while True:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the new session.', default = suggested_name ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        name = dlg.GetValue()
                        
                        if name in ClientGUIPages.RESERVED_SESSION_NAMES:
                            
                            QW.QMessageBox.critical( self, 'Error', 'Sorry, you cannot have that name! Try another.' )
                            
                        else:
                            
                            existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
                            
                            if name in existing_session_names:
                                
                                message = 'Session "{}" already exists! Do you want to overwrite it?'.format( name )
                                
                                ( result, closed_by_user ) = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no, choose another name', check_for_cancelled = True )
                                
                                if closed_by_user:
                                    
                                    return
                                    
                                elif result == QW.QDialog.Rejected:
                                    
                                    continue
                                    
                                
                            
                            break
                            
                        
                    else:
                        
                        return
                        
                    
                
            
        elif name not in ClientGUIPages.RESERVED_SESSION_NAMES: # i.e. a human asked to do this
            
            message = 'Overwrite this session?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no' )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
        
        #
        
        session = notebook.GetCurrentGUISession( name )
        
        self._controller.CallToThread( self._controller.SaveGUISession, session )
        
    
    def RefreshMenu( self ):
        
        if not QP.isValid( self ) or not self or self._CurrentlyMinimisedOrHidden():
            
            return
            
        
        db_going_to_hang_if_we_hit_it = HG.client_controller.DBCurrentlyDoingJob()
        menu_open = CGC.core().MenuIsOpen()
        
        if db_going_to_hang_if_we_hit_it or menu_open:
            
            self._controller.CallLaterQtSafe( self, 0.5, self.RefreshMenu )
            
            return
            
        
        if len( self._dirty_menus ) > 0:
            
            name = self._dirty_menus.pop()
            
            if name not in ( 'file', 'pages', 'pending' ):
                
                ( menu_or_none, label ) = self.GenerateMenuInfo( name )
                
                self.ReplaceMenu( name, menu_or_none, label )
                
            
        
        if len( self._dirty_menus ) > 0:
            
            self._controller.CallLaterQtSafe( self, 0.5, self.RefreshMenu )
            
        
    
    def RefreshStatusBar( self ):
        
        self._RefreshStatusBar()
        
    
    def RegisterAnimationUpdateWindow( self, window ):
        
        self._animation_update_windows.add( window )
        
        if self._animation_update_timer is not None and not self._animation_update_timer.isActive():
            
            self._animation_update_timer.setInterval( 5 )
            
            self._animation_update_timer.start()
            
        
    
    def RegisterCanvasFrameReference( self, frame ):
        
        self._canvas_frames = [ fr for fr in self._canvas_frames if QP.isValid( fr ) ]
        
        self._canvas_frames.append( frame )
        
    
    def RegisterUIUpdateWindow( self, window ):
        
        self._ui_update_windows.add( window )
        
        if self._ui_update_repeating_job is None:
            
            self._ui_update_repeating_job = self._controller.CallRepeatingQtSafe(self, 0.0, 0.1, self.REPEATINGUIUpdate)
            
        
    
    def ReleaseMPVWidget( self, mpv_widget ):
        
        mpv_widget.setParent( self )
        
        self._persistent_mpv_widgets.append( mpv_widget )
        
    
    def REPEATINGBandwidth( self ):
        
        if not QP.isValid( self ) or self._CurrentlyMinimisedOrHidden():
            
            return
            
        
        global_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        
        boot_time = self._controller.GetBootTime()
        
        time_since_boot = max( 1, HydrusData.GetNow() - boot_time )
        
        usage_since_boot = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, time_since_boot )
        
        bandwidth_status = HydrusData.ToHumanBytes( usage_since_boot )
        
        current_usage = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        if current_usage > 0:
            
            bandwidth_status += ' (' + HydrusData.ToHumanBytes( current_usage ) + '/s)'
            
        
        if HC.options[ 'pause_subs_sync' ]:
            
            bandwidth_status += ', subs paused'
            
        
        if self._controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ):
            
            bandwidth_status += ', network paused'
            
        
        tooltip = 'total bandwidth used this session, and current use'
        
        self._statusbar.SetStatusText( bandwidth_status, 1, tooltip = tooltip )
        
    
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
        
        if not QP.isValid( self ) or self._CurrentlyMinimisedOrHidden():
            
            return
            
        
        page = self.GetCurrentPage()
        
        if page is not None:
            
            if HG.ui_timer_profile_mode:
                
                summary = 'Profiling page timer: ' + repr( page )
                
                HydrusData.Profile( summary, 'page.REPEATINGPageUpdate()', globals(), locals(), min_duration_ms = 3 )
                
            else:
                
                page.REPEATINGPageUpdate()
                
            
        
    
    def REPEATINGUIUpdate( self ):
        
        if self._currently_minimised_to_system_tray:
            
            return
            
        
        for window in list( self._ui_update_windows ):
            
            if not QP.isValid( window ):
                
                self._ui_update_windows.discard( window )
                
                continue
                
            
            tlw = window.window()
            
            if not tlw or not QP.isValid( tlw ):
                
                self._ui_update_windows.discard( window )
                
                continue
                
            
            if tlw == self and self._CurrentlyMinimisedOrHidden():
                
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
            
        
    
    def ReplaceMenu( self, name, menu_or_none, label ):
        
        if menu_or_none is not None:
            
            menu_or_none.menuAction().setProperty( 'hydrus_menubar_name', name )
            
            menu_or_none.setTitle( label )
            
        
        old_menu_index = self._FindMenuBarIndex( name )
        
        if old_menu_index == -1:
            
            if menu_or_none is not None:
                
                menu = menu_or_none
                
                insert_index = 0
                
                # for every menu that may display, if it is displayed now, bump up insertion index up one
                for possible_name in MENU_ORDER:
                    
                    if possible_name == name:
                        
                        break
                        
                    
                    possible_menu_index = self._FindMenuBarIndex( possible_name )
                    
                    if possible_menu_index != -1:
                        
                        insert_index += 1
                        
                    
                
                if len( self._menubar.actions() ) > insert_index:
                
                    action_before = self._menubar.actions()[ insert_index ]
                    
                else:
                    
                    action_before = None
                    
                
                menu.setParent( self )
                
                self._menubar.insertMenu( action_before, menu )
                
            
        else:
            
            if name == 'pending' and HG.currently_uploading_pending:
                
                self._menubar.actions()[ old_menu_index ].setText( label )
                
                if menu_or_none is not None:
                    
                    ClientGUIMenus.DestroyMenu( menu_or_none )
                    
                
            else:
                
                old_action = self._menubar.actions()[ old_menu_index ]
                
                old_menu = old_action.menu()
                
                if menu_or_none is not None:
                    
                    menu = menu_or_none
                    
                    menu.setParent( self )
                    
                    self._menubar.insertMenu( old_action, menu )
                    
                    self._menubar.removeAction( old_action )
                    
                else:
                    
                    self._menubar.removeAction( old_action )
                    
                
                ClientGUIMenus.DestroyMenu( old_menu )
            
        
    
    def RestoreOrActivateWindow( self ):
        
        if self.isMinimized():
            
            if self._was_maximised:
                
                self.showMaximized()
                
            else:
                
                self.showNormal()
                
            
        else:
            
            self.activateWindow()
            
        
    
    def SaveAndClose( self ):
        
        if self._done_save_and_close:
            
            return
            
        
        HG.client_controller.pub( 'pause_all_media' )
        
        try:
            
            if QP.isValid( self._message_manager ):
                
                self._message_manager.CleanBeforeDestroy()
                
                self._message_manager.hide()
                
            
            #
            
            if self._have_shown_once:
                
                if self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ):
                    
                    self._SaveSplitterPositions()
                    
                
                ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
                
            
            for tlw in QW.QApplication.topLevelWidgets():
                
                if not isinstance( tlw, ClientGUISplash.FrameSplash ):
                    
                    tlw.hide()
                    
                
            
            if self._have_system_tray_icon:
                
                self._system_tray_icon.hide()
                
            
            #
            
            session = self._notebook.GetCurrentGUISession( 'last session' )
            
            self._controller.SaveGUISession( session )
            
            session.SetName( 'exit session' )
            
            self._controller.SaveGUISession( session )
            
            #
            
            self._DestroyTimers()
            
            self.DeleteAllClosedPages()
            
            self._notebook.CleanBeforeDestroy()
            
            self._controller.WriteSynchronous( 'save_options', HC.options )
            
            self._controller.WriteSynchronous( 'serialisable', self._new_options )
            
            self._done_save_and_close = True
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
        
        self.deleteLater()
        
    
    def SetMediaFocus( self ):
        
        self._SetMediaFocus()
        
    
    def SetStatusBarDirty( self ):
        
        self._statusbar_thread_updater.Update()
        
    
    def ShowPage( self, page_key ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            raise HydrusExceptions.DataMissing( 'Could not find that page!' )
            
        
        self._notebook.ShowPage( page )
        
    
    def TryToExit( self, restart = False, force_shutdown_maintenance = False ):
        
        if not self._controller.DoingFastExit():
            
            able_to_close_statement = self._notebook.GetTestAbleToCloseStatement()
            
            if HC.options[ 'confirm_client_exit' ] or able_to_close_statement is not None:
                
                if restart:
                    
                    text = 'Are you sure you want to restart the client? (Will auto-yes in 15 seconds)'
                    
                else:
                    
                    text = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
                    
                
                if able_to_close_statement is not None:
                    
                    text += os.linesep * 2
                    text += able_to_close_statement
                    
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text, auto_yes_time = 15 )
                
                if result == QW.QDialog.Rejected:
                    
                    return
                    
                
            
        
        if restart:
            
            HG.restart = True
            
        
        if force_shutdown_maintenance or HG.do_idle_shutdown_work:
            
            HG.do_idle_shutdown_work = True
            
        else:
            
            try:
                
                idle_shutdown_action = self._controller.options[ 'idle_shutdown' ]
                
                last_shutdown_work_time = self._controller.Read( 'last_shutdown_work_time' )
                
                shutdown_work_period = self._controller.new_options.GetInteger( 'shutdown_work_period' )
                
                shutdown_work_due = HydrusData.TimeHasPassed( last_shutdown_work_time + shutdown_work_period )
                
                if shutdown_work_due:
                    
                    if idle_shutdown_action == CC.IDLE_ON_SHUTDOWN:
                        
                        HG.do_idle_shutdown_work = True
                        
                    elif idle_shutdown_action == CC.IDLE_ON_SHUTDOWN_ASK_FIRST:
                        
                        idle_shutdown_max_minutes = self._controller.options[ 'idle_shutdown_max_minutes' ]
                        
                        time_to_stop = HydrusData.GetNow() + ( idle_shutdown_max_minutes * 60 )
                        
                        work_to_do = self._controller.GetIdleShutdownWorkDue( time_to_stop )
                        
                        if len( work_to_do ) > 0:
                            
                            text = 'Is now a good time for the client to do up to ' + HydrusData.ToHumanInt( idle_shutdown_max_minutes ) + ' minutes\' maintenance work? (Will auto-no in 15 seconds)'
                            text += os.linesep * 2
                            text += 'The outstanding jobs appear to be:'
                            text += os.linesep * 2
                            text += os.linesep.join( work_to_do )
                            
                            ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Maintenance is due', auto_no_time = 15, check_for_cancelled = True )
                            
                            if was_cancelled:
                                
                                return
                                
                            elif result == QW.QDialog.Accepted:
                                
                                HG.do_idle_shutdown_work = True
                                
                            else:
                                
                                # if they said no, don't keep asking
                                self._controller.Write( 'last_shutdown_work_time', HydrusData.GetNow() )
                                
                            
                        
                    
                
            except Exception as e:
                
                self._controller.SafeShowCriticalMessage( 'shutdown error', 'There was a problem trying to review pending shutdown maintenance work. No shutdown maintenance work will be done, and info has been written to the log. Please let hydev know.' )
                
                HydrusData.PrintException( e )
                
                HG.do_idle_shutdown_work = False
                
            
        
        QP.CallAfter( self._controller.Exit )
        
    
    def UnregisterAnimationUpdateWindow( self, window ):
        
        self._animation_update_windows.discard( window )
        
    
    def UnregisterUIUpdateWindow( self, window ):
        
        self._ui_update_windows.discard( window )
        
    
