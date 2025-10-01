import hashlib
import os
import random
import re
import threading
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEnvironment
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusMemory
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.exporting import ClientExportingFiles
from hydrus.client.gui import ClientGUIAboutWindow
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICharts
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDownloaders
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIFrames
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIPopupMessages
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUISplash
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import ClientGUISubscriptions
from hydrus.client.gui import ClientGUISystemTray
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QLocator
from hydrus.client.gui import ClientGUILocatorSearchProviders
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.gui.canvas import ClientGUIMPV
from hydrus.client.gui.exporting import ClientGUIExport
from hydrus.client.gui.importing import ClientGUIImportFolders
from hydrus.client.gui.media import ClientGUIMediaControls
from hydrus.client.gui.metadata import ClientGUITagDisplayMaintenanceEdit
from hydrus.client.gui.metadata import ClientGUIManageTagParents
from hydrus.client.gui.metadata import ClientGUIManageTagSiblings
from hydrus.client.gui.metadata import ClientGUIMigrateTags
from hydrus.client.gui.metadata import ClientGUITagFilter
from hydrus.client.gui.metadata import ClientGUITagDisplayOptions
from hydrus.client.gui.metadata import ClientGUITagDisplayMaintenanceReview
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.networking import ClientGUILogin
from hydrus.client.gui.networking import ClientGUINetwork
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIPages
from hydrus.client.gui.pages import ClientGUIPagesCore
from hydrus.client.gui.pages import ClientGUISession
from hydrus.client.gui.panels import ClientGUIManageOptionsPanel
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels import ClientGUIScrolledPanelsReview
from hydrus.client.gui.panels import ClientGUIURLClass
from hydrus.client.gui.parsing import ClientGUIParsing
from hydrus.client.gui.parsing import ClientGUIParsingLegacy
from hydrus.client.gui.services import ClientGUIClientsideServices
from hydrus.client.gui.services import ClientGUIModalClientsideServiceActions
from hydrus.client.gui.services import ClientGUIModalServersideServiceActions
from hydrus.client.gui.services import ClientGUIServersideServices
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.parsing import ClientParsing

MENU_ORDER = [ 'file', 'undo', 'pages', 'database', 'network', 'services', 'tags', 'pending', 'help' ]

def CrashTheProgram( win: QW.QWidget ):
    
    def crashtime_nice():
        
        os.abort()
        
    
    def crashtime_not_nice():
        
        for i in range( 100 ):
            
            CG.client_controller.gui.repaint()
            
            time.sleep( 0.1 )
            
        
    
    message = 'u wot mate I\'ll hook u in the gabber'
    
    yes_tuples = []
    
    yes_tuples.append( ( 'nice crash', True ) )
    yes_tuples.append( ( 'not a nice crash', False ) )
    
    try:
        
        result = ClientGUIDialogsQuick.GetYesYesNo( win, message, yes_tuples = yes_tuples, no_label = 'forget it' )
        
    except HydrusExceptions.CancelledException:
        
        return
        
    
    if result:
        
        crashtime_nice()
        
    else:
        
        CG.client_controller.CallToThread( crashtime_not_nice )
        
    

def TurnOffCrashReporting():
    
    from hydrus.core import HydrusLogger
    
    HydrusLogger.turn_off_faulthandler()
    

def GetTagServiceKeyForMaintenance( win: QW.QWidget ):
    
    tag_services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
    
    choice_tuples = [ ( 'all services', None, 'Do it for everything. Can take a long time!' ) ]
    
    for service in tag_services:
        
        choice_tuples.append( ( service.GetName(), service.GetServiceKey(), service.GetName() ) )
        
    
    return ClientGUIDialogsQuick.SelectFromListButtons( win, 'Which service?', choice_tuples )
    
def THREADUploadPending( service_key ):
    
    finished_all_uploads = False
    
    paused_content_types = set()
    unauthorised_content_types = set()
    content_types_to_request = set()
    
    job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        service_name = service.GetName()
        service_type = service.GetServiceType()
        
        if service_type in HC.REPOSITORIES:
            
            account = service.GetAccount()
            
            if account.IsUnknown():
                
                HydrusData.ShowText( 'Your account is currently unsynced, so the upload was cancelled. Please refresh the account under _review services_.' )
                
                return
                
            
        
        job_status.SetStatusTitle( 'uploading pending to ' + service_name )
        
        nums_pending = CG.client_controller.Read( 'nums_pending' )
        
        nums_pending_for_this_service = nums_pending[ service_key ]
        
        content_types_for_this_service = set( HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service_type ] )
        
        if service_type in HC.REPOSITORIES:
            
            content_types_to_count_types_and_permissions = {
                HC.CONTENT_TYPE_FILES : ( ( HC.SERVICE_INFO_NUM_PENDING_FILES, HC.PERMISSION_ACTION_CREATE ), ( HC.SERVICE_INFO_NUM_PETITIONED_FILES, HC.PERMISSION_ACTION_PETITION ) ),
                HC.CONTENT_TYPE_MAPPINGS : ( ( HC.SERVICE_INFO_NUM_PENDING_MAPPINGS, HC.PERMISSION_ACTION_CREATE ), ( HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS, HC.PERMISSION_ACTION_PETITION ) ),
                HC.CONTENT_TYPE_TAG_PARENTS : ( ( HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION ), ( HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION ) ),
                HC.CONTENT_TYPE_TAG_SIBLINGS : ( ( HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ), ( HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ) )
            }
            
            for content_type in content_types_for_this_service:
                
                for ( count_type, permission ) in content_types_to_count_types_and_permissions[ content_type ]:
                    
                    if count_type not in nums_pending_for_this_service:
                        
                        continue
                        
                    
                    num_pending = nums_pending_for_this_service[ count_type ]
                    
                    if num_pending == 0:
                        
                        continue
                        
                    
                    if account.HasPermission( content_type, permission ):
                        
                        if service.IsPausedUpdateProcessing( content_type ):
                            
                            paused_content_types.add( content_type )
                            
                        else:
                            
                            content_types_to_request.add( content_type )
                            
                        
                    else:
                        
                        unauthorised_content_types.add( content_type )
                        
                    
                
            
            if len( unauthorised_content_types ) > 0:
                
                message = 'Unfortunately, your account ({}) does not have full permission to upload all your pending content of type ({})!'.format(
                    account.GetAccountType().GetTitle(),
                    ', '.join( ( HC.content_type_string_lookup[ content_type ] for content_type in unauthorised_content_types ) )
                )
                
                message += '\n' * 2
                message += 'If you are currently using a public, read-only account (such as with the PTR), you may be able to generate your own private account with more permissions. Please hit the button below to open this service in _manage services_ and see if you can generate a new account. If accounts cannot be automatically created, you may have to contact the server owner directly to get this permission.'
                message += '\n' * 2
                message += 'If you think your account does have this permission, try refreshing it under _review services_.'
                
                unauthorised_job_status = ClientThreading.JobStatus()
                
                unauthorised_job_status.SetStatusTitle( 'some data was not uploaded!' )
                
                unauthorised_job_status.SetStatusText( message )
                
                if len( content_types_to_request ) > 0:
                    
                    unauthorised_job_status.FinishAndDismiss( 120 )
                    
                
                call = HydrusData.Call( CG.client_controller.pub, 'open_manage_services_and_try_to_auto_create_account', service_key )
                
                call.SetLabel( 'open manage services and check for auto-creatable accounts' )
                
                unauthorised_job_status.SetUserCallable( call )
                
                CG.client_controller.pub( 'message', unauthorised_job_status )
                
            
            if len( paused_content_types ) > 0:
                
                message = 'You have some pending content of type ({}), but processing for that is currently paused! No worries, but I won\'t upload the paused stuff. If you want to upload it, please unpause in _review services_ and then catch up processing.'.format(
                    ', '.join( ( HC.content_type_string_lookup[ content_type ] for content_type in paused_content_types ) )
                )
                
                HydrusData.ShowText( message )
                
            
        else:
            
            content_types_to_request = content_types_for_this_service
            
        
        if len( content_types_to_request ) == 0:
            
            return
            
        
        initial_num_pending = sum( nums_pending_for_this_service.values() )
        num_to_do = initial_num_pending
        
        current_ideal_weight = 100
        
        result = CG.client_controller.Read( 'pending', service_key, content_types_to_request, ideal_weight = current_ideal_weight )
        
        CG.client_controller.pub( 'message', job_status )
        
        no_results_found = result is None
        
        while result is not None:
            
            time_started_this_loop = HydrusTime.GetNowPrecise()
            
            nums_pending = CG.client_controller.Read( 'nums_pending' )
            
            nums_pending_for_this_service = nums_pending[ service_key ]
            
            remaining_num_pending = sum( nums_pending_for_this_service.values() )
            
            # sometimes more come in while we are pending, -754/1,234 ha ha
            num_to_do = max( num_to_do, remaining_num_pending )
            
            num_done = num_to_do - remaining_num_pending
            
            job_status.SetStatusText( 'uploading to ' + service_name + ': ' + HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) )
            job_status.SetGauge( num_done, num_to_do )
            
            while job_status.IsPaused() or job_status.IsCancelled():
                
                time.sleep( 0.1 )
                
                if job_status.IsCancelled():
                    
                    job_status.DeleteGauge()
                    job_status.SetStatusText( 'cancelled' )
                    
                    HydrusData.Print( job_status.ToString() )
                    
                    job_status.FinishAndDismiss( 5 )
                    
                    return
                    
                
            
            try:
                
                if service_type in HC.REPOSITORIES:
                    
                    if isinstance( result, ClientMediaResult.MediaResult ):
                        
                        media_result = result
                        
                        client_files_manager = CG.client_controller.client_files_manager
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        path = client_files_manager.GetFilePath( hash, mime )
                        
                        service.Request( HC.POST, 'file', file_body_path = path )
                        
                        file_info_manager = media_result.GetFileInfoManager()
                        
                        timestamp_ms = HydrusTime.GetNowMS()
                        
                        content_update_row = ( file_info_manager, timestamp_ms )
                        
                        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                        
                    else:
                        
                        client_to_server_update = result
                        
                        service.Request( HC.POST, 'update', { 'client_to_server_update' : client_to_server_update } )
                        
                        content_updates = ClientContentUpdates.ConvertClientToServerUpdateToContentUpdates( client_to_server_update )
                        
                    
                    if len( content_updates ) > 0:
                        
                        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service_key, content_updates ) )
                        
                    
                elif service_type == HC.IPFS:
                    
                    if isinstance( result, ClientMediaResult.MediaResult ):
                        
                        media_result = result
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        try:
                            
                            service.PinFile( hash, mime )
                            
                        except HydrusExceptions.DataMissing:
                            
                            HydrusData.ShowText( 'File {} could not be pinned!'.format( hash.hex() ) )
                            
                            continue
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'File could not be pinned: {}'.format( e ) )
                            
                            return
                            
                        
                    else:
                        
                        ( hash, multihash ) = result
                        
                        service.UnpinFile( hash, multihash )
                        
                    
                
            except HydrusExceptions.ServerBusyException:
                
                job_status.SetStatusText( service.GetName() + ' was busy. please try again in a few minutes' )
                
                job_status.Cancel()
                
                return
                
            
            CG.client_controller.pub( 'notify_new_pending' )
            
            CG.client_controller.WaitUntilViewFree()
            
            total_time_this_loop_took = HydrusTime.GetNowPrecise() - time_started_this_loop
            
            if total_time_this_loop_took > 1.5:
                
                current_ideal_weight = max( 25, int( current_ideal_weight * 0.95 ) )
                
            elif total_time_this_loop_took < 0.5:
                
                current_ideal_weight = min( 500, int( current_ideal_weight * 1.05 ) )
                
            
            result = CG.client_controller.Read( 'pending', service_key, content_types_to_request, ideal_weight = current_ideal_weight )
            
        
        finished_all_uploads = result is None
        
        if initial_num_pending > 0 and no_results_found and service_type == HC.TAG_REPOSITORY:
            
            HydrusData.ShowText( 'Hey, your pending menu may have a miscount! It seems like you have pending count, but nothing was found in the database. Please run _database->regenerate->tag storage mappings cache (just pending, instant calculation) when convenient. Make sure it is the "instant, just pending" regeneration!' )
            
        
        job_status.DeleteGauge()
        job_status.SetStatusText( 'upload done!' )
        
    except Exception as e:
        
        r = re.search( '[a-fA-F0-9]{64}', str( e ) )
        
        if r is not None:
            
            possible_hash = bytes.fromhex( r.group() )
            
            HydrusData.ShowText( 'Found a possible hash in that error message--trying to show it in a new page.' )
            
            CG.client_controller.pub( 'imported_files_to_page', [ possible_hash ], 'files that did not upload right' )
            
        
        job_status.SetStatusText( service.GetName() + ' error' )
        
        job_status.Cancel()
        
        raise
        
    finally:
        
        CG.client_controller.pub( 'notify_pending_upload_finished', service_key )
        
        HydrusData.Print( job_status.ToString() )
        
        if len( content_types_to_request ) == 0:
            
            job_status.FinishAndDismiss()
            
        else:
            
            job_status.FinishAndDismiss( 5 )
            
        
    
    if finished_all_uploads:
        
        if service_type == HC.TAG_REPOSITORY:
            
            types_to_delete = (
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS
            )
            
        elif service_type in ( HC.FILE_REPOSITORY, HC.IPFS ):
            
            types_to_delete = (
                HC.SERVICE_INFO_NUM_PENDING_FILES,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES
            )
            
        
        CG.client_controller.Write( 'delete_service_info', service_key, types_to_delete )
        
    

class FrameGUI( CAC.ApplicationCommandProcessorMixin, ClientGUITopLevelWindows.MainFrameThatResizes ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        super().__init__( None, 'main', 'main_gui' )
        
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
        self._statusbar_db_thread_updater = ClientGUIAsync.FastThreadToGUIUpdater( self._statusbar, self.RefreshStatusBarDB )
        
        self._canvas_frames = [] # Keep references to canvas frames so they won't get garbage collected (canvas frames don't have a parent)
        
        self._persistent_mpv_widgets = []
        self._isolated_mpv_widgets = []
        
        self._have_shown_session_size_warning = False
        
        self._closed_pages = []
        
        self._lock = threading.Lock()
        
        self._delayed_dialog_lock = threading.Lock()
        
        self._first_session_loaded = False
        
        self._done_save_and_hide = False
        
        self._did_a_backup_this_session = False
        
        self._notebook = ClientGUIPages.PagesNotebook( self, 'top page notebook' )
        
        self._page_nav_history = ClientGUIPages.PagesHistory()
        
        self._currently_uploading_pending = set()
        
        self._last_clipboard_watched_text = ''
        self._clipboard_watcher_destination_page_watcher = None
        self._clipboard_watcher_destination_page_urls = None
        
        self.installEventFilter( self )
        
        drop_target = ClientGUIDragDrop.FileDropTarget( self, self.ImportFiles, self.ImportURLFromDragAndDrop, self._notebook.MediaDragAndDropDropped )
        self.installEventFilter( ClientGUIDragDrop.FileDropTarget( self, self.ImportFiles, self.ImportURLFromDragAndDrop, self._notebook.MediaDragAndDropDropped ) )
        self._notebook.AddSupplementaryTabBarDropTarget( drop_target ) # ugly hack to make the case of files/media dropped onto a tab work
        
        self._message_manager = ClientGUIPopupMessages.PopupMessageManager( self, self._controller.job_status_popup_queue )
        
        self._pending_modal_job_statuses = set()
        
        self._controller.sub( self, 'AddModalMessage', 'modal_message' )
        self._controller.sub( self, 'CreateNewSubscriptionGapDownloader', 'make_new_subscription_gap_downloader' )
        self._controller.sub( self, 'DeleteOldClosedPages', 'delete_old_closed_pages' )
        self._controller.sub( self, 'DoFileStorageRebalance', 'do_file_storage_rebalance' )
        self._controller.sub( self, 'MaintainMemory', 'memory_maintenance_pulse' )
        self._controller.sub( self, 'NewPageDuplicates', 'new_page_duplicates' )
        self._controller.sub( self, 'NewPageImportHDD', 'new_hdd_import' )
        self._controller.sub( self, 'NewPageQuery', 'new_page_query' )
        self._controller.sub( self, 'NotifyAdvancedMode', 'notify_advanced_mode' )
        self._controller.sub( self, 'NotifyClosedPage', 'notify_closed_page' )
        self._controller.sub( self, 'NotifyDeletedPage', 'notify_deleted_page' )
        self._controller.sub( self, 'NotifyNewExportFolders', 'notify_new_export_folders' )
        self._controller.sub( self, 'NotifyNewImportFolders', 'notify_new_import_folders' )
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'NotifyNewPages', 'notify_new_pages' )
        self._controller.sub( self, 'NotifyNewPagesCount', 'notify_new_pages_count' )
        self._controller.sub( self, 'NotifyNewPending', 'notify_new_pending' )
        self._controller.sub( self, 'NotifyNewPermissions', 'notify_new_permissions' )
        self._controller.sub( self, 'NotifyNewPermissions', 'notify_account_sync_due' )
        self._controller.sub( self, 'NotifyNewServices', 'notify_new_services_gui' )
        self._controller.sub( self, 'NotifyNewSessions', 'notify_new_sessions' )
        self._controller.sub( self, 'NotifyNewUndo', 'notify_new_undo' )
        self._controller.sub( self, 'NotifyPendingUploadFinished', 'notify_pending_upload_finished' )
        self._controller.sub( self, 'NotifyRefreshNetworkMenu', 'notify_refresh_network_menu' )
        self._controller.sub( self, 'PresentImportedFilesToPage', 'imported_files_to_page' )
        self._controller.sub( self, 'SetDBLockedStatus', 'db_locked_status' )
        self._controller.sub( self, 'SetStatusBarDirty', 'set_status_bar_dirty' )
        self._controller.sub( self, 'SetStatusBarDirtyDB', 'set_status_bar_db_dirty' )
        self._controller.sub( self, 'TryToOpenManageServicesForAutoAccountCreation', 'open_manage_services_and_try_to_auto_create_account' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setCentralWidget( QW.QWidget() )
        self.centralWidget().setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self._was_maximised = self.isMaximized()
        
        self._InitialiseMenubar()
        
        self._RefreshStatusBar()
        
        self._bandwidth_repeating_job = self._controller.CallRepeatingQtSafe( self, 1.0, 1.0, 'repeating bandwidth status update', self.REPEATINGBandwidth )
        
        self._page_update_repeating_job = self._controller.CallRepeatingQtSafe( self, 0.25, 0.25, 'repeating page update', self.REPEATINGPageUpdate )
        
        self._clipboard_watcher_repeating_job = None
        
        self._ui_update_repeating_job = None
        
        self._ui_update_windows = set()
        
        self._animation_update_timer = QC.QTimer( self )
        self._animation_update_timer.setTimerType( QC.Qt.TimerType.PreciseTimer )
        self._animation_update_timer.timeout.connect( self.TIMEREventAnimationUpdate )
        
        self._animation_update_windows = set()
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'main_gui' ] )
        
        self._system_tray_hidden_tlws = []
        self._have_system_tray_icon = False
        self._system_tray_icon = None
        
        self._have_shown_once = False
        
        if ClientGUISystemTray.SystemTrayAvailable() and self._controller.new_options.GetBoolean( 'start_client_in_system_tray' ):
            
            self._currently_minimised_to_system_tray = True
            
            self.hide()
            
            self._system_tray_hidden_tlws.append( ( self.isMaximized(), self ) )
            
        else:
            
            self.show()
            
            self._have_shown_once = True
            
        
        self._UpdateSystemTrayIcon( currently_booting = True )
        
        self._notebook.freshSessionLoaded.connect( self.ReportFreshSessionLoaded )
        
        self._controller.CallLaterQtSafe( self, 0.5, 'initialise session', self._InitialiseSession ) # do this in callafter as some pages want to talk to controller.gui, which doesn't exist yet!
        
        ClientGUIFunctions.UpdateAppDisplayName()
        
        # locator setup
        
        self._locator = QLocator.QLocator( self )
        
        # TODO: Rework this to StacicIconPath and change the fetch to name not name.png
        self._locator.setIconPathFactory( HydrusStaticDir.GetStaticPath )
        
        # TODO: make configurable which providers + order
        self._locator.addProvider( ClientGUILocatorSearchProviders.CalculatorSearchProvider() )
        self._locator.addProvider( ClientGUILocatorSearchProviders.MainMenuSearchProvider() )
        self._locator.addProvider( ClientGUILocatorSearchProviders.MediaMenuSearchProvider() )
        self._locator.addProvider( ClientGUILocatorSearchProviders.PagesSearchProvider() )
        self._locator_widget = QLocator.QLocatorWidget( self,
            width = 800,
            resultHeight = 36,
            titleHeight = 36,
            primaryTextWidth = 430,
            secondaryTextWidth = 280,
            maxVisibleItemCount = 16
        )
        self._locator_widget.setDefaultStylingEnabled( False )
        self._locator_widget.setLocator( self._locator )
        self._locator_widget.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        self._locator_widget.setEscapeShortcuts( [ QG.QKeySequence( QC.Qt.Key.Key_Escape ) ] )
        # self._locator_widget.setQueryTimeout( 100 ) # how much to wait before starting a search after user edit. default 0
        
        #
        
        try:
            
            mpv_available_at_start = self._controller.new_options.GetBoolean( 'mpv_available_at_start' )
            
            if not mpv_available_at_start and ClientGUIMPV.MPV_IS_AVAILABLE:
                
                # ok, mpv has started working!
                
                self._controller.new_options.SetBoolean( 'mpv_available_at_start', True )
                
                original_mimes_to_view_options = self._new_options.GetMediaViewOptions()
                
                edited_mimes_to_view_options = dict( original_mimes_to_view_options )
                
                we_done_it = False
                
                for general_mime in ( HC.GENERAL_VIDEO, HC.GENERAL_ANIMATION, HC.GENERAL_AUDIO ):
                    
                    if general_mime in original_mimes_to_view_options:
                        
                        view_options = original_mimes_to_view_options[ general_mime ]
                        
                        ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = view_options
                        
                        if media_show_action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE:
                            
                            media_show_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV
                            preview_show_action = CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV
                            
                            view_options = ( media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                            
                            edited_mimes_to_view_options[ general_mime ] = view_options
                            
                            we_done_it = True
                            
                        
                    
                
                if we_done_it:
                    
                    self._controller.new_options.SetMediaViewOptions( edited_mimes_to_view_options )
                    
                    HydrusData.ShowText( 'Hey, MPV was not working on a previous boot, but it looks like it is now. I have updated your media view settings to use MPV.')
                    
                else:
                    
                    HydrusData.ShowText( 'Hey, MPV was not working on a previous boot, but it looks like it is now. You might like to check your file view settings under options->media.')
                    
                
            
        except Exception as e:
            
            HydrusData.ShowText( 'Hey, while trying to check some MPV stuff on boot, I encountered an error. Please let hydev know.' )
            
            HydrusData.ShowException( e )
            
        
    
    def _AboutWindow( self ):
        
        ClientGUIAboutWindow.ShowAboutWindow( self )
        
    
    def _AnalyzeDatabase( self ):
        
        message = 'This will gather statistical information on the database\'s indices, helping the query planner perform efficiently. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        message += '\n' * 2
        message += 'A \'soft\' analyze will only reanalyze those indices that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        message += '\n' * 2
        message += 'A \'full\' analyze will force a run over every index in the database. This can take substantially longer. If you do not have a specific reason to select this, it is probably pointless.'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'soft', False ) )
        yes_tuples.append( ( 'full', True ) )
        
        try:
            
            do_full = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        def do_it():
            
            if do_full:
                
                CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, force_reanalyze = True )
                
            else:
                
                stop_time = HydrusTime.GetNow() + 120
                
                CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = stop_time )
                
            
            HydrusData.ShowText( 'Done!' )
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _AutoRepoSetup( self ):
        
        host = 'ptr.hydrus.network'
        port = 45871
        access_key = bytes.fromhex( '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f' )
        
        ptr_credentials = HydrusNetwork.Credentials( host = host, port = port, access_key = access_key )
        
        def do_it():
            
            all_services = list( self._controller.services_manager.GetServices() )
            
            all_names = [ s.GetName() for s in all_services ]
            
            name = HydrusData.GetNonDupeName( 'public tag repository', all_names, do_casefold = True )
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.TAG_REPOSITORY
            
            public_tag_repo = ClientServices.GenerateService( service_key, service_type, name )
            
            public_tag_repo.SetCredentials( ptr_credentials )
            
            all_services.append( public_tag_repo )
            
            self._controller.SetServices( all_services )
            
            message = 'PTR setup done! Check services->review services to see it.'
            message += '\n' * 2
            message += 'The PTR has a lot of tags and will sync a little bit at a time when you are not using the client. Expect it to take a few weeks to sync fully.'
            
            HydrusData.ShowText( message )
            
        
        have_it_already = False
        
        services = self._controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        for service in services:
            
            credentials = service.GetCredentials()
            
            if credentials.GetSerialisableTuple() == ptr_credentials.GetSerialisableTuple():
                
                have_it_already = True
                
                break
                
            
        
        text = 'This will automatically set up your client with public shared \'read-only\' account for the Public Tag Repository, just as if you had added it manually under services->manage services.'
        text += '\n' * 2
        text += 'Over the coming weeks, your client will download updates and then process them into your database in idle time, and the PTR\'s tags will increasingly appear across your files. If you decide to upload tags, it is just a couple of clicks (under services->manage services again) to generate your own account that has permission to do so.'
        text += '\n' * 2
        text += 'Be aware that the PTR has been growing since 2011 and now has more than two billion mappings. As of 2021-06, it requires about 6GB of bandwidth and file storage, and your database itself will grow by 50GB! Processing also takes a lot of CPU and HDD work, and, due to the unavoidable mechanical latency of HDDs, will only work if your hydrus database (the .db files, normally in install_dir/db) is on an SSD.'
        text += '\n' * 2
        text += '++++If you are on a mechanical HDD or will not be able to free up enough space on your SSD, cancel out now.++++'
        
        if have_it_already:
            
            text += '\n' * 2
            text += 'You seem to have the PTR already. If it is paused or desynchronised, this is best fixed under services->review services. Are you sure you want to add a duplicate?'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'not now' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.CallToThread( do_it )
            
        
    
    def _BackupDatabase( self ):
        
        path = self._new_options.GetNoneableString( 'backup_path' )
        
        if path is None:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No backup path is set!' )
            
            return
            
        
        if not os.path.exists( path ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'The backup path does not exist--creating it now.' )
            
            HydrusPaths.MakeSureDirectoryExists( path )
            
        
        client_db_path = os.path.join( path, 'client.db' )
        
        if os.path.exists( client_db_path ):
            
            action = 'Update the existing'
            
        else:
            
            action = 'Create a new'
            
        
        text = action + ' backup at "' + path + '"?'
        text += '\n' * 2
        text += 'The database will be locked while the backup occurs, which may lock up your gui as well.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            only_changed_page_data = True
            about_to_save = True
            
            session = self._notebook.GetCurrentGUISession( CC.LAST_SESSION_SESSION_NAME, only_changed_page_data, about_to_save )
            
            session = self._FleshOutSessionWithCleanDataIfNeeded( self._notebook, CC.LAST_SESSION_SESSION_NAME, session )
            
            self._controller.SaveGUISession( session )
            
            session.SetName( CC.EXIT_SESSION_SESSION_NAME )
            
            self._controller.SaveGUISession( session )
            
            self._controller.Write( 'backup', path )
            
            CG.client_controller.new_options.SetNoneableInteger( 'last_backup_time', HydrusTime.GetNow() )
            
            self._did_a_backup_this_session = True
            
            self._menu_updater_database.update()
            
        
    
    def _BackupServer( self, service_key ):
        
        def do_it( service ):
            
            started = HydrusTime.GetNow()
            
            service.Request( HC.POST, 'backup' )
            
            HydrusData.ShowText( 'Server backup started!' )
            
            time.sleep( 10 )
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            while result_bytes == b'1':
                
                if HG.started_shutdown:
                    
                    return
                    
                
                time.sleep( 10 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusTime.GetNow() - started
            
            HydrusData.ShowText( 'Server backup done in ' + HydrusTime.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and copy its database files. It will probably take a few minutes to complete, during which time it will not be able to serve any requests.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def _BootOrStopClipboardWatcherIfNeeded( self ):
        
        allow_watchers = self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' )
        allow_other_recognised_urls = self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' )
        
        if allow_watchers or allow_other_recognised_urls:
            
            if self._clipboard_watcher_repeating_job is None:
                
                self._clipboard_watcher_repeating_job = self._controller.CallRepeatingQtSafe( self, 1.0, 1.0, 'repeating clipboard watcher', self.REPEATINGClipboardWatcher )
                
            
        else:
            
            if self._clipboard_watcher_destination_page_watcher is not None:
                
                self._clipboard_watcher_repeating_job.Cancel()
                
                self._clipboard_watcher_repeating_job = None
                
            
        
    
    def _CheckDBIntegrity( self ):
        
        message = 'This will check the SQLite database files for corruption. It may take several minutes to complete.'
        message += '\n' * 2
        message += 'In general, this routine is quite laggy, especially as it checks always checks your entire database, and is better done from the command line where you have more control. If you are worried your database is malformed, check [install_dir/db/help my db is broke.txt].'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Run integrity check?', yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'db_integrity' )
            
        
    
    def _CheckImportFolder( self, name = None ):
        
        if self._controller.new_options.GetBoolean( 'pause_import_folders_sync' ):
            
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
        
        text = 'Are you sure you want to delete _all_ file view count/duration and \'last time viewed\' records? This cannot be undone.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADVANCED, 'clear' )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
            
            self._controller.WriteSynchronous( 'content_updates', content_update_package )
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Delete done! Please restart the client to see the changes in the UI.' )
            
        
    
    def _ClearOrphanFiles( self ):
        
        text = 'This job will iterate through every file in your database\'s file storage, extracting any it does not expect to be there. This is particularly useful for \'re-syncing\' your file storage to what it should be after, say, marrying an older/newer database with a newer/older file storage.'
        text += '\n' * 2
        text += 'You can choose to move the orphans in your file directories somewhere or delete them. Orphan thumbnails will be put in a subdirectory, in case you wish to perform reverse lookups.'
        text += '\n' * 2
        text += 'Access to files and thumbnails will be slightly limited while this runs, and it may take some time.'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'move them somewhere', 'move' ) )
        yes_tuples.append( ( 'delete them', 'delete' ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        client_files_manager = self._controller.client_files_manager
        
        if result == 'move':
            
            with QP.DirDialog( self, 'Select location.' ) as dlg_3:
                
                if dlg_3.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = dlg_3.GetPath()
                    
                    self._controller.CallToThread( client_files_manager.ClearOrphans, path )
                    
                
            
        elif result == 'delete':
            
            self._controller.CallToThread( client_files_manager.ClearOrphans )
            
        
    
    def _ClearOrphanFileRecords( self ):
        
        text = 'DO NOT RUN THIS UNLESS YOU KNOW YOU NEED TO'
        text += '\n' * 2
        text += 'This will instruct the database to review its file records\' integrity. If anything appears to be in a specific domain (e.g. my files) but not an umbrella domain (e.g. all my files), and the actual file also exists on disk, it will try to recover the record. If the file does not actually exist on disk, or the record is in the umbrella domain and not in the specific domain, or if recovery data cannot be found, the record will be deleted.'
        text += '\n' * 2
        text += 'You typically do not ever see these files and they are basically harmless, but they can offset some file counts confusingly and may break other maintenance routines. You probably only need to run this if you can\'t process the apparent last handful of duplicate filter pairs or hydrus dev otherwise told you to try it.'
        text += '\n' * 2
        text += 'It will create a popup message while it works and inform you of the number of orphan records found. It may lock up the client for a bit.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'clear_orphan_file_records' )
            
        
    
    def _ClearOrphanHashedSerialisables( self ):
        
        text = 'DO NOT RUN THIS UNLESS YOU KNOW YOU NEED TO. MAKE A BACKUP BEFORE YOU RUN IT'
        text += '\n' * 2
        text += 'This force-runs a routine that regularly removes some spare data from the database. You most likely do not need to run it.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            controller = self._controller
            
            def do_it():
                
                num_done = controller.WriteSynchronous( 'maintain_hashed_serialisables', force_start = True )
                
                if num_done == 0:
                    
                    message = 'No orphans found!'
                    
                else:
                    
                    message = '{} orphans cleared!'.format( HydrusNumbers.ToHumanInt( num_done ) )
                    
                
                HydrusData.ShowText( message )
                
            
            CG.client_controller.CallToThread( do_it )
            
        
    
    def _ClearOrphanTables( self ):
        
        text = 'DO NOT RUN THIS UNLESS YOU KNOW YOU NEED TO. MAKE A BACKUP BEFORE YOU RUN IT'
        text += '\n' * 2
        text += 'This will instruct the database to review its service tables and delete any orphans. This will typically do nothing, but hydrus dev may tell you to run this, just to check. Be sure you have a recent backup before you run this--if it deletes something important by accident, you will want to roll back!'
        text += '\n' * 2
        text += 'It will create popups if it finds anything to delete.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'clear_orphan_tables' )
            
        
    
    def _CullFileViewingStats( self ):
        
        text = 'If your file viewing statistics have some erroneous values due to many short views or accidental long views, this routine will cull your current numbers to compensate. For instance:'
        text += '\n' * 2
        text += 'If you have a file with 100 views over 100 seconds and a minimum view time of 2 seconds, this will cull the views to 50.'
        text += '\n' * 2
        text += 'If you have a file with 10 views over 100000 seconds and a maximum view time of 60 seconds, this will cull the total viewtime to 600 seconds.'
        text += '\n' * 2
        text += 'It will work for both preview and media views based on their separate rules.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.WriteSynchronous( 'cull_file_viewing_statistics' )
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Cull done! Please restart the client to see the changes in the UI.' )
            
        
    
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
            
            try:
                
                result = ClientGUIDialogsQuick.GetYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if result == 'file':
                
                with QP.FileDialog( self, 'select where to save content', default_filename = 'output.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as f_dlg:
                    
                    if f_dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        path = f_dlg.GetPath()
                        
                        with open( path, 'wb' ) as f:
                            
                            f.write( content )
                            
                        
                    
                
            elif result == 'clipboard':
                
                text = network_job.GetContentText()
                
                self._controller.pub( 'clipboard', 'text', text )
                
            
        
        def thread_wait( url ):
            
            from hydrus.client.networking import ClientNetworkingJobs
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusTitle( 'debug network job' )
            
            job_status.SetNetworkJob( network_job )
            
            self._controller.pub( 'message', job_status )
            
            self._controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
            finally:
                
                job_status.FinishAndDismiss( seconds = 3 )
                
            
            CG.client_controller.CallAfter( self, qt_code, network_job )
            
        
        try:
            
            url = ClientGUIDialogsQuick.EnterText( self, 'Enter the URL.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._controller.CallToThread( thread_wait, url )
        
    
    def _DebugIsolateMPVWindows( self ):
        
        HydrusData.ShowText( f'Isolated {HydrusNumbers.ToHumanInt( len( self._persistent_mpv_widgets ) )} MPV widgets.' )
        
        self._isolated_mpv_widgets.extend( self._persistent_mpv_widgets )
        
        self._persistent_mpv_widgets = []
        
    
    def _DebugMakeDelayedModalPopup( self, cancellable ):
        
        def do_it( controller, cancellable ):
            
            time.sleep( 5 )
            
            job_status = ClientThreading.JobStatus( cancellable = cancellable )
            
            job_status.SetStatusTitle( 'debug modal job' )
            
            controller.pub( 'modal_message', job_status )
            
            for i in range( 10 ):
                
                if job_status.IsCancelled():
                    
                    break
                    
                
                job_status.SetStatusText( 'Will auto-dismiss in ' + HydrusTime.TimeDeltaToPrettyTimeDelta( 10 - i ) + '.' )
                job_status.SetGauge( i, 10 )
                
                time.sleep( 1 )
                
            
            job_status.FinishAndDismiss()
            
        
        self._controller.CallToThread( do_it, self._controller, cancellable )
        
    
    def _DebugLongTextPopup( self ):
        
        words = [ 'test', 'a', 'longish', 'statictext', 'm8' ]
        
        text = random.choice( words )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( text )
        
        self._controller.pub( 'message', job_status )
        
        t = 0
        
        for i in range( 2, 64 ):
            
            text += ' {}'.format( random.choice( words ) )
            
            t += 0.2
            
            self._controller.CallLater( t, job_status.SetStatusText, text )
            
        
        words = [ 'test', 'a', 'longish', 'statictext', 'm8' ]
        
        text = random.choice( words )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'test long title' )
        
        self._controller.pub( 'message', job_status )
        
        for i in range( 2, 64 ):
            
            text += ' {}'.format( random.choice( words ) )
            
            t += 0.2
            
            self._controller.CallLater( t, job_status.SetStatusTitle, text )
            
        
    
    def _DebugMakeParentlessTextCtrl( self ):
        
        with QP.Dialog( None, title = 'parentless debug dialog' ) as dlg:
            
            control = QW.QLineEdit( dlg )
            
            control.setText( 'debug test input' )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, control, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dlg.setLayout( vbox )
            
            dlg.exec()
            
        
    
    def _DebugMakeQMessageBox( self ):
        
        ClientGUIDialogsMessage.ShowWarning( self, 'This is a test message!\n\nI have a second line of information to give! I will repeat it! I have a second line of information to give! I will repeat it! I have a second line of information to give! I will repeat it! I have a second line of information to give! I will repeat it! I have a second line of information to give! I will repeat it!' )
        
    
    def _DebugMakeSomePopups( self ):
        
        for i in range( 1, 7 ):
            
            HydrusData.ShowText( 'This is a test popup message -- ' + str( i ) )
            
        
        brother_classem_pinniped = '''++++What the fuck did you just fucking say about me, you worthless heretic? I'll have you know I graduated top of my aspirant tournament in the Heralds of Ultramar, and I've led an endless crusade of secret raids against the forces of The Great Enemy, and I have over 30 million confirmed purgings. I am trained in armored warfare and I'm the top brother in all the 8th Company. You are nothing to me but just another heretic. I will wipe you the fuck out with precision the likes of which has never been seen before in this Galaxy, mark my fucking words. You think you can get away with saying that shit to me over the Divine Astropathic Network? Think again, traitor. As we speak I am contacting my secret network of inquisitors across the galaxy and your malign powers are being traced right now so you better prepare for the holy storm, maggot. The storm that wipes out the pathetic little thing you call your soul. You're fucking dead, kid. I can transit the immaterium to anywhere, anytime, and I can kill you in over seven hundred ways, and that's just with my purity seals. Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the Departmento Munitorum and I will use it to its full extent to wipe your miserable ass off the face of the galaxy, you little shit. If only you could have known what holy retribution your little "clever" comment was about to bring down upon you, maybe you would have held your fucking impure mutant tongue. But you couldn't, you didn't, and now you're paying the price, you Emperor-damned heretic.++++\n\n++++Better crippled in body than corrupt in mind++++\n\n++++The Emperor Protects++++'''
        
        HydrusData.ShowText( 'This is a very long message:  \n\n' + brother_classem_pinniped )
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'This popup has a very long title -- it is a subscription that is running with a long "artist sub 123456" kind of name' )
        
        job_status.SetStatusText( 'test' )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'user call test' )
        
        job_status.SetStatusText( 'click the button m8' )
        
        call = HydrusData.Call( HydrusData.ShowText, 'iv damke' )
        
        call.SetLabel( 'cheeki breeki' )
        
        job_status.SetUserCallable( call )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        service_keys = list( CG.client_controller.services_manager.GetServiceKeys( ( HC.TAG_REPOSITORY, ) ) )
        
        if len( service_keys ) > 0:
            
            service_key = service_keys[0]
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusTitle( 'auto-account creation test' )
            
            call = HydrusData.Call( CG.client_controller.pub, 'open_manage_services_and_try_to_auto_create_account', service_key )
            
            call.SetLabel( 'open manage services and check for auto-creatable accounts' )
            
            job_status.SetUserCallable( call )
            
            CG.client_controller.pub( 'message', job_status )
            
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'client api test file popup' )
        
        hashes = [ bytes.fromhex( '78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538' ) ]
        
        job_status.SetFiles( hashes, 'go' )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'Popup file merge test' )
        
        job_status.SetStatusText( 'hey I should have five files' )
        
        job_status.SetVariable( 'attached_files_mergable', True )
        
        hashes = [ HydrusData.GenerateKey() for i in range( 3 ) ]
        
        job_status.SetFiles( hashes, 'cool pics' )
        
        self._controller.pub( 'message', job_status )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'Popup file merge test' )
        
        job_status.SetStatusText( 'hey you should not see me, I should be merged' )
        
        job_status.SetVariable( 'attached_files_mergable', True )
        
        job_status.SetFiles( [ HydrusData.GenerateKey() for i in range( 2 ) ] + [ hashes[0] ], 'cool pics' )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( 'sub gap downloader test' )
        
        from hydrus.client.importing.options import FileImportOptions
        
        file_import_options = FileImportOptions.FileImportOptions()
        file_import_options.SetIsDefault( True )
        
        from hydrus.client.importing.options import TagImportOptions
        
        tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
        from hydrus.client.importing.options import NoteImportOptions
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        note_import_options.SetIsDefault( True )
        
        call = HydrusData.Call( CG.client_controller.pub, 'make_new_subscription_gap_downloader', ( b'', 'safebooru tag search' ), 'skirt', file_import_options, tag_import_options, note_import_options, 2 )
        
        call.SetLabel( 'start a new downloader for this to fill in the gap!' )
        
        job_status.SetUserCallable( call )
        
        CG.client_controller.pub( 'message', job_status )
        
        #
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusTitle( '\u24c9\u24d7\u24d8\u24e2 \u24d8\u24e2 \u24d0 \u24e3\u24d4\u24e2\u24e3 \u24e4\u24dd\u24d8\u24d2\u24de\u24d3\u24d4 \u24dc\u24d4\u24e2\u24e2\u24d0\u24d6\u24d4' )
        
        job_status.SetStatusText( '\u24b2\u24a0\u24b2 \u24a7\u249c\u249f' )
        job_status.SetStatusText( 'p\u0250\u05df \u028d\u01dd\u028d', 2 )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( 'test job' )
        
        job_status.SetStatusText( 'Currently processing test job 5/8' )
        job_status.SetGauge( 4, 8 )
        
        self._controller.pub( 'message', job_status )
        
        self._controller.CallLater( 2.0, job_status.SetStatusText, 'Pulsing subjob', level = 2 )
        
        self._controller.CallLater( 2.0, job_status.SetGauge, 0, None, level = 2 )
        
        #
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( 'test network control' )
        
        job_status.SetStatusText( 'Downloading...' )
        job_status.SetGauge( 2, 21 )
        
        from hydrus.client.networking import ClientNetworkingJobs
        
        job_status.SetNetworkJob( ClientNetworkingJobs.NetworkJob( 'GET', 'https://site.com/123456' ) )
        
        self._controller.pub( 'message', job_status )
        
        #
        
        e = HydrusExceptions.DataMissing( 'This is a test exception' )
        
        HydrusData.ShowException( e, do_wait = False )
        
        #
        
        for i in range( 1, 4 ):
            
            self._controller.CallLater( 0.5 * i, HydrusData.ShowText, 'This is a delayed popup message -- ' + str( i ) )
            
        
    
    def _DebugResetColumnListManager( self ):
        
        message = 'This will reset all saved column widths for all multi-column lists across the program. You may need to restart the client to see changes.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._controller.column_list_manager.ResetToDefaults()
        
    
    def _DebugShowMemoryUseDifferences( self ):
        
        if not HydrusMemory.PYMPLER_OK:
            
            HydrusData.ShowText( 'Sorry, you need pympler for this!' )
            
            return
            
        
        HydrusMemory.PrintSnapshotDiff()
        
    
    def _DebugTakeMemoryUseSnapshot( self ):
        
        if not HydrusMemory.PYMPLER_OK:
            
            HydrusData.ShowText( 'Sorry, you need pympler for this!' )
            
            return
            
        
        HydrusMemory.TakeMemoryUseSnapshot()
        
    
    def _DebugPrintMemoryUse( self ):
        
        if not HydrusMemory.PYMPLER_OK:
            
            HydrusData.ShowText( 'Sorry, you need pympler for this!' )
            
            return
            
        
        HydrusMemory.PrintCurrentMemoryUse( ( QW.QWidget, ) )
        
    
    def _DebugShowScheduledJobs( self ):
        
        self._controller.DebugShowScheduledJobs()
        
    
    def _DeleteGUISession( self, name ):
        
        message = 'Delete session "' + name + '"?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Delete session?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER, name )
            
            self._controller.pub( 'notify_new_sessions' )
            
        
    
    def _DeleteServiceInfo( self, only_pending = False ):
        
        if only_pending:
            
            services = CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.IPFS ) )
            
            types_to_delete = (
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS,
                HC.SERVICE_INFO_NUM_PENDING_FILES,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES
            )
            
            message = 'This will clear and regen the number for the pending menu up top. Due to unusual situations and little counting bugs, these numbers can sometimes become unsynced. It should not take long at all, and will update instantly if changed.'
            
        else:
            
            services = CG.client_controller.services_manager.GetServices()
            
            types_to_delete = None
            
            message = 'This clears the cached counts for things like the number of files or tags on a service. Due to unusual situations and little counting bugs, these numbers can sometimes become unsynced. Clearing them forces an accurate recount from source.'
            message += '\n' * 2
            message += 'Some GUI elements (review services, mainly) may be slow the next time they launch. Especially if you clear for all services.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            choice_tuples = [ ( service.GetName(), service.GetServiceKey(), service.GetName() ) for service in services ]
            
            choice_tuples.sort()
            
            choice_tuples.insert( 0, ( 'all services', None, 'Do it for everything. Can take a long time!' ) )
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which service?', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'delete_service_info', types_to_delete = types_to_delete, service_key = service_key )
            
        
    
    def _DestroyPages( self, pages ):
        
        for page in pages:
            
            if page and QP.isValid( page ):
                
                page.CleanBeforeDestroy()
                
                page.deleteLater()
                
            
        
    
    def _DestroyTimers( self ):
        
        if self._animation_update_timer is not None:
            
            self._animation_update_timer.stop()
            
            self._animation_update_timer = None
            
        
    
    def _DoMenuBarStyleHack( self ):
        
        # yo just as a fun side thing, if you try to set your style to windowsvista after windows11 on 6.7.2, all your menubar menus go transparent
        
        try:
            
            if ClientGUIStyle.CURRENT_STYLE_NAME == 'windows11':
                
                stylesheet = '''QMenuBar { padding: 2px; margin: 0px }
QMenuBar::item { padding: 2px 8px; margin: 0px; }'''
                
            else:
                
                stylesheet = ''
                
            
            self._menubar.setStyleSheet( stylesheet )
            
        except Exception as e:
            
            HydrusData.Print( 'I tried to do the menubar style hack, but got this exception (please let hydev know):' )
            HydrusData.PrintException( e, do_wait = False)
            
        
    
    def _ExportDownloader( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export downloaders' ) as dlg:
            
            panel = ClientGUIParsing.DownloaderExportPanel( dlg, self._controller.network_engine )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _FetchIP( self, service_key ):
        
        try:
            
            file_hash_hex = ClientGUIDialogsQuick.EnterText( self, 'Enter the file\'s hash.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        try:
            
            hash = bytes.fromhex( file_hash_hex )
            
        except:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'Could not parse that hash!' )
            
            return
            
        
        service = self._controller.services_manager.GetService( service_key )
        
        with ClientGUICommon.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash } )
        
        ip = response[ 'ip' ]
        timestamp = response[ 'timestamp' ]
        
        utc_time = HydrusTime.TimestampToPrettyTime( timestamp, in_utc = True )
        local_time = HydrusTime.TimestampToPrettyTime( timestamp )
        
        text = 'File Hash: ' + hash.hex()
        text += '\n'
        text += 'Uploader\'s IP: ' + ip
        text += 'Upload Time (UTC): ' + utc_time
        text += 'Upload Time (Your time): ' + local_time
        
        HydrusData.Print( text )
        
        ClientGUIDialogsMessage.ShowInformation( self, text + '\n' * 2 + 'This has been written to the log.' )
        
    
    def _FindMenuBarIndex( self, name ):
        
        for index in range( len( self._menubar.actions() ) ):
            
            if self._menubar.actions()[ index ].property( 'hydrus_menubar_name' ) == name:
                
                return index
                
            
        
        return -1
        
    
    def _FixLogicallyInconsistentMappings( self ):
        
        message = 'This will check for tags that are occupying mutually exclusive states--either current & pending or deleted & petitioned.'
        message += '\n' * 2
        message += 'Please run this if you attempt to upload some tags and get a related error. You may need some follow-up regeneration work to correct autocomplete or \'num pending\' counts.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'fix_logically_inconsistent_mappings', tag_service_key = tag_service_key )
            
        
    
    def _FixMissingArchiveTimes( self ):
        
        def do_it_scan_step( job_status ):
            
            num_missing_legacy = self._controller.Read( 'missing_archive_timestamps_legacy_count', job_status )
            
            if job_status.IsCancelled():
                
                return
                
            
            num_missing_import = self._controller.Read( 'missing_archive_timestamps_import_count', job_status )
            
            if job_status.IsCancelled():
                
                return
                
            
            CG.client_controller.CallAfterQtSafe( self, 'missing archive times reporter', qt_present_results, job_status, num_missing_legacy, num_missing_import )
            
        
        def qt_present_results( job_status, num_missing_legacy, num_missing_import ):
            
            if num_missing_legacy > 0 or num_missing_import > 0:
                
                message = 'It looks like there are some missing archive times. You have:'
                
                yes_tuples = []
                
                if num_missing_legacy > 0:
                    
                    message += f'\n\n--{HydrusNumbers.ToHumanInt( num_missing_legacy )} Missing Legacy Times--'
                    message += '\n\nThese are files that were archived before hydrus started tracking archive time (2022-02). If you select to fill these in, hydrus will insert a synthetic time that is import time + 20% of the time to 2022-02 or any file deletion time.'
                    
                    yes_tuples.append( ( 'do legacy times', [ 'legacy' ] ) )
                    
                
                if num_missing_import > 0:
                    
                    message += f'\n\n--{HydrusNumbers.ToHumanInt( num_missing_import )} Missing Import Times--'
                    message += '\n\nThese are most likely files that were imported with "automatically archive", which for some period until 2024-12 were not recording archive times due to a bug. It may include a few other instances of missing archived files (e.g. you manually deleted one). If you select to fill these in, hydrus will insert a synthetic time that is the same as the import time.'
                    
                    yes_tuples.append( ( 'do import times', [ 'import' ] ) )
                    
                
                if num_missing_legacy > 0 and num_missing_import > 0:
                    
                    yes_tuples.append( ( 'do both', [ 'legacy', 'import' ] ) )
                    
                
                try:
                    
                    jobs = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
                    
                except HydrusExceptions.CancelledException:
                    
                    job_status.FinishAndDismiss()
                    
                    return
                    
                
                self._controller.CallToThread( do_it_fix_step, job_status, jobs )
                
            else:
                
                job_status.SetStatusText( 'No missing archive times found!' )
                
                job_status.Finish()
                
            
        
        def do_it_fix_step( job_status, jobs ):
            
            for job in jobs:
                
                if job == 'legacy':
                    
                    self._controller.WriteSynchronous( 'missing_archive_timestamps_legacy_fillin', job_status )
                    
                elif job == 'import':
                    
                    self._controller.WriteSynchronous( 'missing_archive_timestamps_import_fillin', job_status )
                    
                
                if job_status.IsCancelled():
                    
                    return
                    
                
            
            job_status.SetStatusText( 'Done!' )
            job_status.Finish()
            
        
        message = 'There are a couple of ways your client may be missing archive times for your files. This will scan for missing times and then present you with the results and a choice on what to do.'
        message += '\n' * 2
        message += 'The scan may take a while. It will have a popup showing its work, but it may lock up your client for a bit while it works.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'start the scan', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'missing archive times work' )
            CG.client_controller.pub( 'message', job_status )
            
            self._controller.CallToThread( do_it_scan_step, job_status )
            
        
    
    def _FleshOutSessionWithCleanDataIfNeeded( self, notebook: ClientGUIPages.PagesNotebook, name: str, session: ClientGUISession.GUISessionContainer ):
        
        unchanged_page_data_hashes = session.GetUnchangedPageDataHashes()
        
        have_hashed_serialised_objects = self._controller.Read( 'have_hashed_serialised_objects', unchanged_page_data_hashes )
        
        if not have_hashed_serialised_objects:
            
            only_changed_page_data = False
            about_to_save = True
            
            session = notebook.GetCurrentGUISession( name, only_changed_page_data, about_to_save )
            
        
        return session
        
    
    def _FlipClipboardWatcher( self, option_name ):
        
        self._controller.new_options.FlipBoolean( option_name )
        
        self._controller.WriteSynchronous( 'serialisable', self._controller.new_options )
        
        self._last_clipboard_watched_text = ''
        
        if self._clipboard_watcher_repeating_job is None:
            
            self._BootOrStopClipboardWatcherIfNeeded()
            
        
    
    def _FlipMinimiseRestore( self ):
        
        if not self._currently_minimised_to_system_tray:
            
            if self.isMinimized():
                
                self.RestoreOrActivateWindow()
                
            else:
                
                self.showMinimized()
                
            
        
    
    def _FlipShowHideWholeUI( self ):
        
        if not ClientGUISystemTray.SystemTrayAvailable():
            
            try:
                
                raise Exception( 'Was called to flip hide/show to system tray, but system tray is not available!' )
                
            except Exception as e:
                
                HydrusData.PrintException( e, do_wait = False )
                
            
            return
            
        
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
                
            
            CG.client_controller.pub( 'pause_all_media' )
            
            for tlw in visible_tlws:
                
                tlw.hide()
                
                self._system_tray_hidden_tlws.append( ( tlw.isMaximized(), tlw ) )
                
            
        else:
            
            for ( was_maximised, tlw ) in self._system_tray_hidden_tlws:
                
                if QP.isValid( tlw ):
                    
                    tlw.show()
                    
                    if was_maximised:
                        
                        tlw.showMaximized()
                        
                    
                
            
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
        
    
    def _GetTablesAndColumnsUsingDefinitions( self ):
        
        choice_tuples = [ ( HC.content_type_string_lookup[ content_type ], content_type, HC.content_type_string_lookup[ content_type ] ) for content_type in [ HC.CONTENT_TYPE_HASH, HC.CONTENT_TYPE_TAG ] ]
        
        try:
            
            message = '''SUPER ADVANCED!

This will gather all the tables and columns that use the particular content type and put them in your clipboard in the format "(schema_name.)table_name,column_name". If you want to do mass SELECT or DELETE operations for each of a particular definition, use a multi-editor tool in a powerful text editor to edit all the lines at once (with Ctrl+D, usually).

Some tables are referred to by "external_x" schema name, so when you have your commands written out, you will need to either remove the schema names; or use the connect.bat in the db dir, which sets up the correct names for you; or manually initialise your session like so:

.open client.db
ATTACH "client.caches.db" as external_caches;
ATTACH "client.master.db" as external_master;
ATTACH "client.mappings.db" as external_mappings;'''
            
            content_type = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Select which content type to fetch for', choice_tuples, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        tables_and_columns = self._controller.Read( 'tables_and_columns_using_definitions', content_type )
        
        text = '\n'.join( ( f'{table_name},{column_name}' for ( table_name, column_name ) in tables_and_columns ) )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
        HydrusData.ShowText( f'{HydrusNumbers.ToHumanInt(len(tables_and_columns))} table and column pairs sent to clipboard.' )
        
    
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
            
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review files to import' )
        
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
                
                ClientGUIDialogsMessage.ShowWarning( self, 'No files in that directory!' )
                
                return
                
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            try:
                
                job_status.SetStatusTitle( 'importing updates' )
                CG.client_controller.pub( 'message', job_status )
                
                for ( i, update_path ) in enumerate( update_paths ):
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        job_status.SetStatusText( 'Cancelled!' )
                        
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
                        
                        job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( i, num_to_do ) )
                        job_status.SetGauge( i, num_to_do )
                        
                    
                
                if num_errors == 0:
                    
                    job_status.SetStatusText( 'Done!' )
                    
                else:
                    
                    job_status.SetStatusText( 'Done with ' + HydrusNumbers.ToHumanInt( num_errors ) + ' errors (written to the log).' )
                    
                
            finally:
                
                job_status.DeleteGauge()
                
                job_status.Finish()
                
            
        
        message = 'This lets you manually import a directory of update files for your repositories. Any update files that match what your repositories are looking for will be automatically linked so they do not have to be downloaded.'
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
        with QP.DirDialog( self, 'Select location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = dlg.GetPath()
                
                self._controller.CallToThread( do_it, path )
                
            
        
    
    def _ImportURL(
        self,
        unclean_url,
        filterable_tags = None,
        additional_service_keys_to_tags = None,
        destination_page_name = None,
        destination_page_key = None,
        show_destination_page = True,
        allow_watchers = True,
        allow_other_recognised_urls = True,
        allow_unrecognised_urls = True,
        destination_location_context = None
        ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        ClientNetworkingFunctions.CheckLooksLikeAFullURL( unclean_url )
        
        url = ClientNetworkingFunctions.EnsureURLIsEncoded( unclean_url )
        
        url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url, for_server = True )
        
        ( url_type, match_name, can_parse, cannot_parse_reason ) = self._controller.network_engine.domain_manager.GetURLParseCapability( url )
        
        if url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and not can_parse:
            
            message = 'This URL was recognised as a "{}" but it cannot be parsed: {}'.format( match_name, cannot_parse_reason )
            message += '\n' * 2
            message += 'Since this URL cannot be parsed, a downloader cannot be created for it! Please check your url class links under the \'networking\' menu.'
            
            raise HydrusExceptions.URLClassException( message )
            
        
        url_caught = False
        
        if ( url_type == HC.URL_TYPE_UNKNOWN and allow_unrecognised_urls ) or ( url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY ) and allow_other_recognised_urls ):
            
            url_caught = True
            
            page = self._notebook.GetOrMakeURLImportPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page, destination_location_context = destination_location_context )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                sidebar = page.GetSidebar()
                
                sidebar.PendURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        elif url_type == HC.URL_TYPE_WATCHABLE and allow_watchers:
            
            url_caught = True
            
            page = self._notebook.GetOrMakeMultipleWatcherPage( desired_page_name = destination_page_name, desired_page_key = destination_page_key, select_page = show_destination_page )
            
            if page is not None:
                
                if show_destination_page:
                    
                    self._notebook.ShowPage( page )
                    
                
                sidebar = page.GetSidebar()
                
                sidebar.PendURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
                
                return ( url, '"{}" URL added successfully.'.format( match_name ) )
                
            
        
        if url_caught:
            
            raise HydrusExceptions.DataMissing( '"{}" URL was accepted but not added successfully--could not find/generate a new downloader page for it.'.format( match_name ) )
            
        
    
    def _InitialiseMenubar( self ):
        
        use_native_menubar = CG.client_controller.new_options.GetBoolean( 'use_native_menubar' )
        
        if use_native_menubar:
            
            self._menubar = QW.QMenuBar()
            
            self._menubar.setNativeMenuBar( True )
            
            if not self._menubar.isNativeMenuBar():
                
                self._menubar.setParent( self )
                
            
        else:
            
            self._menubar = QW.QMenuBar( self )
            
            self._menubar.setNativeMenuBar( False )
            
            self._DoMenuBarStyleHack()
            
        
        self._menu_updater_file = self._InitialiseMenubarGetMenuUpdaterFile()
        self._menu_updater_database = self._InitialiseMenubarGetMenuUpdaterDatabase()
        self._menu_updater_network = self._InitialiseMenubarGetMenuUpdaterNetwork()
        self._menu_updater_pages = self._InitialiseMenubarGetMenuUpdaterPages()
        self._menu_updater_pending = self._InitialiseMenubarGetMenuUpdaterPending()
        self._menu_updater_services = self._InitialiseMenubarGetMenuUpdaterServices()
        self._menu_updater_tags = self._InitialiseMenubarGetMenuUpdaterTags()
        self._menu_updater_undo = self._InitialiseMenubarGetMenuUpdaterUndo()
        
        self._menu_updater_pages_count = ClientGUIAsync.FastThreadToGUIUpdater( self, self._UpdateMenuPagesCount )
        self._menu_updater_pages_history = ClientGUIAsync.FastThreadToGUIUpdater( self, self._UpdateMenuPagesHistory )
        
        self._boned_updater = self._InitialiseMenubarGetBonesUpdater()
        self._file_history_updater = self._InitialiseMenubarGetFileHistoryUpdater()
        
        self.setMenuBar( self._menubar )
        
        for name in MENU_ORDER:
            
            if name == 'database':
                
                ( menu, label ) = self._InitialiseMenuInfoDatabase()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_database.update()
                
            elif name == 'file':
                
                ( menu, label ) = self._InitialiseMenuInfoFile()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_file.update()
                
            elif name == 'help':
                
                ( menu, label ) = self._InitialiseMenuInfoHelp()
                
                self.ReplaceMenu( name, menu, label )
                
            elif name == 'network':
                
                ( menu, label ) = self._InitialiseMenuInfoNetwork()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_network.update()
                
            elif name == 'pages':
                
                ( menu, label ) = self._InitialiseMenuInfoPages()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_pages.update()
                
            elif name == 'pending':
                
                self._pending_service_keys_to_submenus = {}
                
                self._menubar_pending_submenu = ClientGUIMenus.GenerateMenu( self )
                
                self.ReplaceMenu( name, self._menubar_pending_submenu, '&pending' )
                
                self._menu_updater_pending.update()
                
            elif name == 'services':
                
                ( menu, label ) = self._InitialiseMenuInfoServices()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_services.update()
                
            elif name == 'tags':
                
                ( menu, label ) = self._InitialiseMenuInfoTags()
                
                self.ReplaceMenu( name, menu, label )
                
                self._menu_updater_tags.update()
                
            elif name == 'undo':
                
                ( self._menubar_undo_submenu, label ) = self._InitialiseMenuInfoUndo()
                
                self.ReplaceMenu( name, self._menubar_undo_submenu, label )
                
                self._menu_updater_undo.update()
                
            
        
    
    def _InitialiseMenubarGetBonesUpdater( self ):
        
        # this thing used to fetch the db stuff itself, so it has the weird async updater stuff. refactor into a straight call sometime
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review your fate', frame_key = 'mr_bones' )
            
            panel = ClientGUIScrolledPanelsReview.ReviewHowBonedAmI( frame )
            
            frame.SetPanel( panel )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetFileHistoryUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'file history', frame_key = 'file_history_chart' )
            
            panel = ClientGUIScrolledPanelsReview.ReviewFileHistory( frame )
            
            frame.SetPanel( panel )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterDatabase( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            all_locations_are_default = CG.client_controller.client_files_manager.AllLocationsAreDefault()
            
            return all_locations_are_default
            
        
        def publish_callable( result ):
            
            all_locations_are_default = result
            
            backup_path = self._new_options.GetNoneableString( 'backup_path' )
            
            self._menubar_database_set_up_backup_path.setVisible( all_locations_are_default and backup_path is None )
            
            self._menubar_database_update_backup.setVisible( all_locations_are_default and backup_path is not None )
            
            last_backup_time = CG.client_controller.new_options.GetNoneableInteger( 'last_backup_time' )
            
            message = 'update database backup'
            
            if last_backup_time is not None:
                
                if not HydrusTime.TimeHasPassed( last_backup_time + 1800 ):
                    
                    message += ' (did one recently)'
                    
                else:
                    
                    message += ' (last {})'.format( HydrusTime.TimestampToPrettyTimeDelta( last_backup_time ) )
                    
                
            
            self._menubar_database_update_backup.setText( message )
            
            self._menubar_database_change_backup_path.setVisible( all_locations_are_default and backup_path is not None )
            
            self._menubar_database_restore_backup.setVisible( all_locations_are_default )
            
            self._menubar_database_multiple_location_label.setVisible( not all_locations_are_default )
            
            self._menubar_database_file_maintenance_during_idle.setChecked( CG.client_controller.new_options.GetBoolean( 'file_maintenance_during_idle' ) )
            self._menubar_database_file_maintenance_during_active.setChecked( CG.client_controller.new_options.GetBoolean( 'file_maintenance_during_active' ) )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterFile( self ):
        
        def loading_callable():
            
            self._menubar_file_import_submenu.setEnabled( False )
            self._menubar_file_export_submenu.setEnabled( False )
            
        
        def work_callable( args ):
            
            import_folder_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            export_folder_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            return ( import_folder_names, export_folder_names )
            
        
        def publish_callable( result ):
            
            ( import_folder_names, export_folder_names ) = result
            
            self._menubar_file_import_submenu.setEnabled( True )
            
            self._menubar_file_import_submenu.clear()
            
            self._menubar_file_import_submenu.menuAction().setVisible( len( import_folder_names ) > 0 )
            
            if len( import_folder_names ) > 0:
                
                if len( import_folder_names ) > 1:
                    
                    ClientGUIMenus.AppendMenuItem( self._menubar_file_import_submenu, 'check all', 'Check all import folders.', self._CheckImportFolder )
                    
                    ClientGUIMenus.AppendSeparator( self._menubar_file_import_submenu )
                    
                
                for name in import_folder_names:
                    
                    ClientGUIMenus.AppendMenuItem( self._menubar_file_import_submenu, name, 'Check this import folder now.', self._CheckImportFolder, name )
                    
                
            
            self._menubar_file_export_submenu.setEnabled( True )
            
            self._menubar_file_export_submenu.clear()
            
            self._menubar_file_export_submenu.menuAction().setVisible( len( export_folder_names ) > 0 )
            
            if len( export_folder_names ) > 0:
                
                if len( export_folder_names ) > 1:
                    
                    ClientGUIMenus.AppendMenuItem( self._menubar_file_export_submenu, 'run all', 'Run all export folders.', self._RunExportFolder )
                    
                    ClientGUIMenus.AppendSeparator( self._menubar_file_export_submenu )
                    
                
                for name in export_folder_names:
                    
                    ClientGUIMenus.AppendMenuItem( self._menubar_file_export_submenu, name, 'Run this export folder now.', self._RunExportFolder, name )
                    
                
            
            simple_non_windows = not HC.PLATFORM_WINDOWS and not CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
            
            windows_or_advanced_non_windows = not simple_non_windows
            
            self._menubar_file_minimise_to_system_tray.setVisible( ClientGUISystemTray.SystemTrayAvailable() and windows_or_advanced_non_windows )
            
            self._menubar_file_import_folders_paused.setChecked( CG.client_controller.new_options.GetBoolean( 'pause_import_folders_sync' ) )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterNetwork( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            advanced_mode = self._controller.new_options.GetBoolean( 'advanced_mode' )
            
            self._menubar_network_nudge_subs.setVisible( advanced_mode )
            
            self._menubar_network_all_traffic_paused.setChecked( CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
            
            self._menubar_network_subscriptions_paused.setChecked( CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ) )
            
            self._menubar_network_paged_import_queues_paused.setChecked( CG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' ) )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterPages( self ):
        
        def loading_callable():
            
            self._menubar_pages_sessions_submenu.setEnabled( False )
            self._menubar_pages_search_submenu.setEnabled( False )
            self._menubar_pages_petition_submenu.setEnabled( False )
            
        
        def work_callable( args ):
            
            gui_session_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
            
            if len( gui_session_names ) > 0:
                
                gui_session_names_to_backup_timestamps_ms = CG.client_controller.Read( 'serialisable_names_to_backup_timestamps_ms', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
                
            else:
                
                gui_session_names_to_backup_timestamps_ms = {}
                
            
            return ( gui_session_names, gui_session_names_to_backup_timestamps_ms )
            
        
        def publish_callable( result ):
            
            self._UpdateMenuPagesCount()
            
            #
            
            ( gui_session_names, gui_session_names_to_backup_timestamps_ms ) = result
            
            gui_session_names = sorted( gui_session_names )
            
            self._menubar_pages_sessions_submenu.setEnabled( True )
            
            self._menubar_pages_sessions_submenu.clear()
            
            if len( gui_session_names ) > 0:
                
                load = ClientGUIMenus.GenerateMenu( self._menubar_pages_sessions_submenu )
                
                for name in gui_session_names:
                    
                    ClientGUIMenus.AppendMenuItem( load, name, 'Close all other pages and load this session.', self._notebook.LoadGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( self._menubar_pages_sessions_submenu, load, 'clear and load' )
                
                append = ClientGUIMenus.GenerateMenu( self._menubar_pages_sessions_submenu )
                
                for name in gui_session_names:
                    
                    ClientGUIMenus.AppendMenuItem( append, name, 'Append this session to whatever pages are already open.', self._notebook.AppendGUISessionFreshest, name )
                    
                
                ClientGUIMenus.AppendMenu( self._menubar_pages_sessions_submenu, append, 'append' )
                
                if len( gui_session_names_to_backup_timestamps_ms ) > 0:
                    
                    append_backup = ClientGUIMenus.GenerateMenu( self._menubar_pages_sessions_submenu )
                    
                    rows = sorted( gui_session_names_to_backup_timestamps_ms.items() )
                    
                    for ( name, timestamps_ms ) in rows:
                        
                        submenu = ClientGUIMenus.GenerateMenu( append_backup )
                        
                        for timestamp_ms in timestamps_ms:
                            
                            ClientGUIMenus.AppendMenuItem( submenu, HydrusTime.TimestampToPrettyTime( HydrusTime.SecondiseMS( timestamp_ms ) ), 'Append this backup session to whatever pages are already open.', self._notebook.AppendGUISessionBackup, name, timestamp_ms )
                            
                        
                        ClientGUIMenus.AppendMenu( append_backup, submenu, name )
                        
                    
                    ClientGUIMenus.AppendMenu( self._menubar_pages_sessions_submenu, append_backup, 'append session backup' )
                    
                
            
            save = ClientGUIMenus.GenerateMenu( self._menubar_pages_sessions_submenu )
            
            for name in gui_session_names:
                
                if name in ClientGUISession.RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( save, name, 'Save the existing open pages as a session.', self.ProposeSaveGUISession, name )
                
            
            ClientGUIMenus.AppendMenuItem( save, 'as new session' + HC.UNICODE_ELLIPSIS, 'Save the existing open pages as a session.', self.ProposeSaveGUISession )
            
            ClientGUIMenus.AppendMenu( self._menubar_pages_sessions_submenu, save, 'save' )
            
            if len( set( gui_session_names ).difference( ClientGUISession.RESERVED_SESSION_NAMES ) ) > 0:
                
                delete = ClientGUIMenus.GenerateMenu( self._menubar_pages_sessions_submenu )
                
                for name in gui_session_names:
                    
                    if name in ClientGUISession.RESERVED_SESSION_NAMES:
                        
                        continue
                        
                    
                    ClientGUIMenus.AppendMenuItem( delete, name, 'Delete this session.', self._DeleteGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( self._menubar_pages_sessions_submenu, delete, 'delete' )
                
            
            #
            
            self._menubar_pages_search_submenu.setEnabled( True )
            
            self._menubar_pages_search_submenu.clear()
            
            services = self._controller.services_manager.GetServices()
            
            local_file_services = [ service for service in services if service.GetServiceType() == HC.LOCAL_FILE_DOMAIN ]
            
            for service in local_file_services:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( service.GetServiceKey() )
                
                ClientGUIMenus.AppendMenuItem( self._menubar_pages_search_submenu, service.GetName(), 'Open a new search tab.', self._notebook.NewPageQuery, location_context, on_deepest_notebook = True )
                
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.TRASH_SERVICE_KEY )
            
            ClientGUIMenus.AppendMenuItem( self._menubar_pages_search_submenu, 'trash', 'Open a new search tab for your recently deleted files.', self._notebook.NewPageQuery, location_context, on_deepest_notebook = True )
            
            repositories = [ service for service in services if service.GetServiceType() in HC.REPOSITORIES ]
            
            file_repositories = [ service for service in repositories if service.GetServiceType() == HC.FILE_REPOSITORY ]
            
            for service in file_repositories:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( service.GetServiceKey() )
                
                ClientGUIMenus.AppendMenuItem( self._menubar_pages_search_submenu, service.GetName(), 'Open a new search tab for ' + service.GetName() + '.', self._notebook.NewPageQuery, location_context, on_deepest_notebook = True )
                
            
            petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES ]
            
            petition_resolvable_repositories = [ repository for repository in repositories if True in ( repository.HasPermission( content_type, action ) for ( content_type, action ) in petition_permissions ) ]
            
            self._menubar_pages_petition_submenu.setEnabled( True )
            
            self._menubar_pages_petition_submenu.clear()
            
            self._menubar_pages_petition_submenu.menuAction().setVisible( len( petition_resolvable_repositories ) > 0 )
            
            for service in petition_resolvable_repositories:
                
                ClientGUIMenus.AppendMenuItem( self._menubar_pages_petition_submenu, service.GetName(), 'Open a new petition page for ' + service.GetName() + '.', self._notebook.NewPagePetitions, service.GetServiceKey(), on_deepest_notebook = True )
                
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterPending( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            nums_pending = CG.client_controller.Read( 'nums_pending' )
            
            return nums_pending
            
        
        def publish_callable( result ):
            
            nums_pending = result
            
            total_num_pending = 0
            
            for service_key in nums_pending.keys():
                
                if service_key not in self._pending_service_keys_to_submenus:
                    
                    service = self._controller.services_manager.GetService( service_key )
                    
                    name = service.GetName()
                    
                    submenu = ClientGUIMenus.GenerateMenu( self._menubar_pending_submenu )
                    
                    ClientGUIMenus.AppendMenuItem( submenu, 'commit', 'Upload {}\'s pending content.'.format( name ), self.UploadPending, service_key )
                    ClientGUIMenus.AppendMenuItem( submenu, 'forget', 'Clear {}\'s pending content.'.format( name ), self.ForgetPending, service_key )
                    
                    ClientGUIMenus.SetMenuTitle( submenu, name )
                    
                    insert_before_action = None
                    
                    for action in self._menubar_pending_submenu.actions():
                        
                        if action.text() > name:
                            
                            insert_before_action = action
                            
                            break
                            
                        
                    
                    if insert_before_action is None:
                        
                        self._menubar_pending_submenu.addMenu( submenu )
                        
                    else:
                        
                        self._menubar_pending_submenu.insertMenu( insert_before_action, submenu )
                        
                    
                    self._pending_service_keys_to_submenus[ service_key ] = submenu
                    
                
            
            for ( service_key, submenu ) in self._pending_service_keys_to_submenus.items():
                
                num_pending = 0
                num_petitioned = 0
                
                if service_key in nums_pending:
                    
                    info = nums_pending[ service_key ]
                    
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
                        
                    
                    if num_pending + num_petitioned > 0:
                        
                        if service_key in self._currently_uploading_pending:
                            
                            title = '{}: currently uploading {}'.format( name, HydrusNumbers.ToHumanInt( num_pending + num_petitioned ) )
                            
                        else:
                            
                            submessages = []
                            
                            if num_pending > 0:
                                
                                submessages.append( '{} {}'.format( HydrusNumbers.ToHumanInt( num_pending ), pending_phrase ) )
                                
                            
                            if num_petitioned > 0:
                                
                                submessages.append( '{} {}'.format( HydrusNumbers.ToHumanInt( num_petitioned ), petitioned_phrase ) )
                                
                            
                            title = '{}: {}'.format( name, ', '.join( submessages ) )
                            
                        
                        submenu.setEnabled( service_key not in self._currently_uploading_pending )
                        
                        ClientGUIMenus.SetMenuTitle( submenu, title )
                        
                    
                
                submenu.menuAction().setVisible( num_pending + num_petitioned > 0 )
                
                total_num_pending += num_pending + num_petitioned
                
            
            ClientGUIMenus.SetMenuTitle( self._menubar_pending_submenu, 'pending ({})'.format( HydrusNumbers.ToHumanInt( total_num_pending ) ) )
            
            self._menubar_pending_submenu.menuAction().setEnabled( total_num_pending > 0 )
            
            has_pending_services = len( self._controller.services_manager.GetServiceKeys( ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.IPFS ) ) ) > 0
            
            self._menubar_pending_submenu.menuAction().setVisible( has_pending_services )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterServices( self ):
        
        def loading_callable():
            
            self._menubar_services_admin_submenu.setEnabled( False )
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            self._menubar_services_admin_submenu.setEnabled( True )
            
            self._menubar_services_admin_submenu.clear()
            
            repository_admin_permissions = [ ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE ), ( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ), ( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_MODERATE ), ( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE ) ]
            
            repositories = self._controller.services_manager.GetServices( HC.REPOSITORIES )
            admin_repositories = [ service for service in repositories if True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_admin_permissions ) ]
            
            servers_admin = self._controller.services_manager.GetServices( ( HC.SERVER_ADMIN, ) )
            server_admins = [ service for service in servers_admin if service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE ) ]
            
            admin_services = admin_repositories + server_admins
            
            if len( admin_services ) > 0:
                
                for service in admin_services:
                    
                    submenu = ClientGUIMenus.GenerateMenu( self._menubar_services_admin_submenu )
                    
                    service_key = service.GetServiceKey()
                    
                    service_type = service.GetServiceType()
                    
                    can_create_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
                    can_overrule_accounts = service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
                    can_overrule_account_types = service.HasPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_MODERATE )
                    can_overrule_services = service.HasPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
                    can_overrule_options = service.HasPermission( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE )
                    
                    if can_overrule_accounts:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'review all accounts' + HC.UNICODE_ELLIPSIS, 'See all accounts.', self._STARTReviewAllAccounts, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'modify an account' + HC.UNICODE_ELLIPSIS, 'Modify a specific account\'s type and expiration.', self._ModifyAccount, service_key )
                        
                    
                    if can_overrule_accounts and service_type == HC.FILE_REPOSITORY:
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'get an uploader\'s ip address' + HC.UNICODE_ELLIPSIS, 'Fetch the ip address that uploaded a specific file, if the service knows it.', self._FetchIP, service_key )
                        
                    
                    if can_create_accounts:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'create new accounts' + HC.UNICODE_ELLIPSIS, 'Create new accounts for this service.', self._GenerateNewAccounts, service_key )
                        
                    
                    if can_overrule_account_types:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'manage account types', 'Add, edit and delete account types for this service.', self._STARTManageAccountTypes, service_key )
                        
                    
                    if can_overrule_options and service_type in HC.REPOSITORIES:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'change update period' + HC.UNICODE_ELLIPSIS, 'Change the update period for this service.', self._ManageServiceOptionsUpdatePeriod, service_key )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'change anonymisation period' + HC.UNICODE_ELLIPSIS, 'Change the account history nullification period for this service.', self._ManageServiceOptionsNullificationPeriod, service_key )
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            ClientGUIMenus.AppendSeparator( submenu )
                            
                            ClientGUIMenus.AppendMenuItem( submenu, 'edit tag filter' + HC.UNICODE_ELLIPSIS, 'Change the tag filter for this service.', ClientGUIModalServersideServiceActions.ManageServiceOptionsTagFilter, self, service_key )
                            ClientGUIMenus.AppendMenuItem( submenu, 'purge tags' + HC.UNICODE_ELLIPSIS, 'Delete tags completely from the service.', ClientGUIModalClientsideServiceActions.OpenPurgeTagsWindow, self, service_key, [] )
                            ClientGUIMenus.AppendMenuItem( submenu, 'purge tag filter', 'Sync the tag filter to the service, deleting anything that does not pass.', ClientGUIModalClientsideServiceActions.StartPurgeTagFilter, self, service_key )
                            
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'maintenance: regen service info', 'Add, edit, and delete this server\'s services.', self._ServerMaintenanceRegenServiceInfo, service_key )
                        
                    
                    if can_overrule_services and service_type == HC.SERVER_ADMIN:
                        
                        ClientGUIMenus.AppendSeparator( submenu )
                        
                        ClientGUIMenus.AppendMenuItem( submenu, 'manage services' + HC.UNICODE_ELLIPSIS, 'Add, edit, and delete this server\'s services.', self._ManageServer, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'restart server services', 'Command the server to disconnect and restart its services.', self._RestartServerServices, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'backup server', 'Command the server to temporarily pause and back up its database.', self._BackupServer, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'vacuum server', 'Command the server to temporarily pause and vacuum its database.', self._VacuumServer, service_key )
                        ClientGUIMenus.AppendSeparator( submenu )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: on', 'Command the server to lock itself and disconnect its db.', self._LockServer, service_key, True )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: test', 'See if the server is currently busy.', self._TestServerBusy, service_key )
                        ClientGUIMenus.AppendMenuItem( submenu, 'server/db lock: off', 'Command the server to unlock itself and resume its db.', self._LockServer, service_key, False )
                        
                    
                    ClientGUIMenus.AppendMenu( self._menubar_services_admin_submenu, submenu, service.GetName() )
                    
                
            
            self._menubar_services_admin_submenu.menuAction().setVisible( len( admin_services ) > 0 )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterTags( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            self._menubar_tags_tag_display_maintenance_during_idle.setChecked( CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ) )
            self._menubar_tags_tag_display_maintenance_during_active.setChecked( CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ) )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenubarGetMenuUpdaterUndo( self ):
        
        def loading_callable():
            
            self._menubar_undo_closed_pages_submenu.setEnabled( False )
            
        
        def work_callable( args ):
            
            return 1
            
        
        def publish_callable( result ):
            
            have_closed_pages = len( self._closed_pages ) > 0
            
            undo_manager = self._controller.GetManager( 'undo' )
            
            ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
            
            have_undo_stuff = undo_string is not None or redo_string is not None
            
            if have_closed_pages or have_undo_stuff:
                
                self._menubar_undo_undo.setVisible( undo_string is not None )
                
                if undo_string is not None:
                    
                    ClientGUIMenus.SetMenuItemLabel( self._menubar_undo_undo, undo_string )
                    
                
                self._menubar_undo_redo.setVisible( redo_string is not None )
                
                if redo_string is not None:
                    
                    ClientGUIMenus.SetMenuItemLabel( self._menubar_undo_redo, redo_string )
                    
                
                self._menubar_undo_closed_pages_submenu.setEnabled( True )
                
                self._menubar_undo_closed_pages_submenu.clear()
                
                self._menubar_undo_closed_pages_submenu.menuAction().setVisible( have_closed_pages )
                
                if have_closed_pages:
                    
                    ClientGUIMenus.AppendMenuItem( self._menubar_undo_closed_pages_submenu, 'clear all' + HC.UNICODE_ELLIPSIS, 'Remove all closed pages from memory.', self.AskToDeleteAllClosedPages )
                    
                    self._menubar_undo_closed_pages_submenu.addSeparator()
                    
                    args = []
                    
                    for ( i, ( time_closed, page ) ) in enumerate( self._closed_pages ):
                        
                        menu_name = page.GetNameForMenu()
                        
                        args.append( ( i, menu_name ) )
                        
                    
                    args.reverse() # so that recently closed are at the top
                    
                    for ( index, name ) in args:
                        
                        ClientGUIMenus.AppendMenuItem( self._menubar_undo_closed_pages_submenu, name, 'Restore this page.', self._UnclosePage, index )
                        
                    
                
            
            self._menubar_undo_submenu.menuAction().setEnabled( have_closed_pages or have_undo_stuff )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseMenuInfoDatabase( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'set a password' + HC.UNICODE_ELLIPSIS, 'Set a simple password for the database so only you can open it in the client.', self._SetPassword )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        self._menubar_database_set_up_backup_path = ClientGUIMenus.AppendMenuItem( menu, 'set up a database backup location' + HC.UNICODE_ELLIPSIS, 'Choose a path to back the database up to.', self._SetupBackupPath )
        self._menubar_database_update_backup = ClientGUIMenus.AppendMenuItem( menu, 'update database backup' + HC.UNICODE_ELLIPSIS, 'Back the database up to an external location.', self._BackupDatabase )
        self._menubar_database_change_backup_path = ClientGUIMenus.AppendMenuItem( menu, 'change database backup location' + HC.UNICODE_ELLIPSIS, 'Choose a path to back the database up to.', self._SetupBackupPath )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        self._menubar_database_restore_backup = ClientGUIMenus.AppendMenuItem( menu, 'restore from a database backup' + HC.UNICODE_ELLIPSIS, 'Restore the database from an external location.', self._controller.RestoreDatabase )
        
        message = 'Your database is stored across multiple locations. The in-client backup routine can only handle simple databases (in one location), so the menu commands to backup have been hidden. To back up, please use a third-party program that will work better than anything I can write.'
        message += '\n' * 2
        message += 'Check the help for more info on how best to backup manually.'
        
        self._menubar_database_multiple_location_label = ClientGUIMenus.AppendMenuItem( menu, 'database is stored in multiple locations', 'The database is migrated, and internal backups are not possible--click for more info.', HydrusData.ShowText, message )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'move media files' + HC.UNICODE_ELLIPSIS, 'Review and manage the locations your database is stored.', self._MoveMediaFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'how boned am I?', 'Check for a summary of your ride so far.', self._HowBonedAmI )
        ClientGUIMenus.AppendMenuItem( menu, 'view file history', 'See a chart of your file import history.', self._ShowFileHistory )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        #
        
        file_maintenance_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( file_maintenance_menu, 'manage scheduled jobs' + HC.UNICODE_ELLIPSIS, 'Review outstanding jobs, and schedule new ones.', self._ReviewFileMaintenance )
        ClientGUIMenus.AppendSeparator( file_maintenance_menu )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'file_maintenance_during_idle' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        self._menubar_database_file_maintenance_during_idle = ClientGUIMenus.AppendMenuCheckItem( file_maintenance_menu, 'work file jobs during idle time', 'Control whether file maintenance can work during idle time.', current_value, func )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'file_maintenance_during_active' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        self._menubar_database_file_maintenance_during_active = ClientGUIMenus.AppendMenuCheckItem( file_maintenance_menu, 'work file jobs during normal time', 'Control whether file maintenance can work during normal time.', current_value, func )
        
        ClientGUIMenus.AppendSeparator( file_maintenance_menu )
        
        ClientGUIMenus.AppendMenuItem( file_maintenance_menu, 'clear orphan files' + HC.UNICODE_ELLIPSIS, 'Clear out surplus files that have found their way into the file structure.', self._ClearOrphanFiles )
        
        ClientGUIMenus.AppendSeparator( file_maintenance_menu )
        
        ClientGUIMenus.AppendMenuItem( file_maintenance_menu, 'fix missing file archived times' + HC.UNICODE_ELLIPSIS, 'Search for and fill-in missing file archive times.', self._FixMissingArchiveTimes )
        
        ClientGUIMenus.AppendMenu( menu, file_maintenance_menu, 'file maintenance' )
        
        #
        
        db_maintenance_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'review deferred delete table data', 'See how many tables are being deleted in the background.', self._ReviewDeferredDeleteTableData )
        
        ClientGUIMenus.AppendSeparator( db_maintenance_submenu )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'database_deferred_delete_maintenance_during_idle' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        ClientGUIMenus.AppendMenuCheckItem( db_maintenance_submenu, 'work deferred delete jobs during idle time', 'Control whether database deferred delete maintenance can work during idle time.', current_value, func )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'database_deferred_delete_maintenance_during_active' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        ClientGUIMenus.AppendMenuCheckItem( db_maintenance_submenu, 'work deferred delete jobs during normal time', 'Control whether database deferred delete maintenance can work during normal time.', current_value, func )
        
        #
        
        ClientGUIMenus.AppendSeparator( db_maintenance_submenu )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'analyze' + HC.UNICODE_ELLIPSIS, 'Optimise slow queries by running statistical analyses on the database.', self._AnalyzeDatabase )
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'review vacuum data' + HC.UNICODE_ELLIPSIS, 'See whether it is worth rebuilding the database to reformat tables and recover disk space.', self._ReviewVacuumData )
        
        ClientGUIMenus.AppendSeparator( db_maintenance_submenu )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'clear/fix orphan file records' + HC.UNICODE_ELLIPSIS, 'Clear out surplus file records that have not been deleted correctly.', self._ClearOrphanFileRecords )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'clear orphan tables' + HC.UNICODE_ELLIPSIS, 'Clear out surplus db tables that have not been deleted correctly.', self._ClearOrphanTables )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'clear orphan hashed serialisables' + HC.UNICODE_ELLIPSIS, 'Clear non-needed cached hashed serialisable objects.', self._ClearOrphanHashedSerialisables )
        
        ClientGUIMenus.AppendSeparator( db_maintenance_submenu )
        
        ClientGUIMenus.AppendMenuItem( db_maintenance_submenu, 'get tables using definitions' + HC.UNICODE_ELLIPSIS, 'Fetch every table from the database that uses a particular id type.', self._GetTablesAndColumnsUsingDefinitions )
        
        ClientGUIMenus.AppendMenu( menu, db_maintenance_submenu, 'db maintenance' )
        
        check_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( check_submenu, 'database integrity' + HC.UNICODE_ELLIPSIS, 'Examine the database for file corruption.', self._CheckDBIntegrity )
        ClientGUIMenus.AppendSeparator( check_submenu )
        ClientGUIMenus.AppendMenuItem( check_submenu, 'fix invalid tags' + HC.UNICODE_ELLIPSIS, 'Scan the database for invalid tags.', self._RepairInvalidTags )
        ClientGUIMenus.AppendMenuItem( check_submenu, 'fix logically inconsistent mappings' + HC.UNICODE_ELLIPSIS, 'Remove tags that are occupying two mutually exclusive states.', self._FixLogicallyInconsistentMappings )
        ClientGUIMenus.AppendSeparator( check_submenu )
        ClientGUIMenus.AppendMenuItem( check_submenu, 'repopulate truncated mappings tables' + HC.UNICODE_ELLIPSIS, 'Use the mappings cache to try to repair a previously damaged mappings file.', self._RepopulateMappingsTables )
        ClientGUIMenus.AppendSeparator( check_submenu )
        ClientGUIMenus.AppendMenuItem( check_submenu, 'resync combined deleted files' + HC.UNICODE_ELLIPSIS, 'Resynchronise the store of all known deleted files.', self._ResyncCombinedDeletedFiles )
        ClientGUIMenus.AppendMenuItem( check_submenu, 'resync tag mappings cache files' + HC.UNICODE_ELLIPSIS, 'Check the tag mappings cache for surplus or missing files.', self._ResyncTagMappingsCacheFiles )
        
        ClientGUIMenus.AppendMenu( menu, check_submenu, 'check and repair' )
        
        regen_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'total pending count, in the pending menu' + HC.UNICODE_ELLIPSIS, 'Regenerate the pending count up top.', self._DeleteServiceInfo, only_pending = True )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag storage mappings cache (all, with deferred siblings & parents calculation)' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag mappings cache, fixing bad tags or miscounts.', self._RegenerateTagMappingsCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag storage mappings cache (just pending tags, instant calculation)' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag pending mappings cache, fixing bad tags or miscounts.', self._RegenerateTagPendingMappingsCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag display mappings cache (all, deferred siblings & parents calculation)' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag display mappings cache, fixing bad tags or miscounts.', self._RegenerateTagDisplayMappingsCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag display mappings cache (just pending tags, instant calculation)' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag display pending mappings cache, fixing bad tags or miscounts.', self._RegenerateTagDisplayPendingMappingsCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag display mappings cache (missing file repopulation)' + HC.UNICODE_ELLIPSIS, 'Repopulate the mappings cache if you know it is lacking files, fixing bad tags or miscounts.', self._RepopulateTagDisplayMappingsCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag siblings lookup cache' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag siblings cache. Useful if you see an error in sibling presentation.', self._RegenerateTagSiblingsLookupCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag parents lookup cache' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the tag parents cache. Useful if you see an error in parent presentation.', self._RegenerateTagParentsLookupCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag text search cache' + HC.UNICODE_ELLIPSIS, 'Delete and regenerate the cache hydrus uses for fast tag search.', self._RegenerateTagCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag text search cache (subtags repopulation)' + HC.UNICODE_ELLIPSIS, 'Repopulate the subtags for the cache hydrus uses for fast tag search.', self._RepopulateTagCacheMissingSubtags )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'tag text search cache (searchable subtag maps)' + HC.UNICODE_ELLIPSIS, 'Regenerate the searchable subtag maps.', self._RegenerateTagCacheSearchableSubtagsMaps )
        
        ClientGUIMenus.AppendSeparator( regen_submenu )
        
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'local hashes cache' + HC.UNICODE_ELLIPSIS, 'Repopulate the cache hydrus uses for fast hash lookup for local files.', self._RegenerateLocalHashCache )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'local tags cache' + HC.UNICODE_ELLIPSIS, 'Repopulate the cache hydrus uses for fast tag lookup for local files.', self._RegenerateLocalTagCache )
        
        ClientGUIMenus.AppendSeparator( regen_submenu )
        
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'service info numbers' + HC.UNICODE_ELLIPSIS, 'Delete all cached service info like total number of mappings or files, in case it has become desynchronised. Some parts of the gui may be laggy immediately after this as these numbers are recalculated.', self._DeleteServiceInfo )
        ClientGUIMenus.AppendMenuItem( regen_submenu, 'similar files search tree' + HC.UNICODE_ELLIPSIS, 'Delete and recreate the similar files search tree.', self._RegenerateSimilarFilesTree )
        
        ClientGUIMenus.AppendMenu( menu, regen_submenu, 'regenerate' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        file_viewing_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( file_viewing_submenu, 'clear all file viewing statistics' + HC.UNICODE_ELLIPSIS, 'Delete all file viewing records from the database.', self._ClearFileViewingStats )
        ClientGUIMenus.AppendMenuItem( file_viewing_submenu, 'cull file viewing statistics based on current min/max values' + HC.UNICODE_ELLIPSIS, 'Cull your file viewing statistics based on minimum and maximum permitted time deltas.', self._CullFileViewingStats )
        
        ClientGUIMenus.AppendMenu( menu, file_viewing_submenu, 'file viewing statistics' )
        
        return ( menu, '&database' )
        
    
    def _InitialiseMenuInfoFile( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'import files' + HC.UNICODE_ELLIPSIS, 'Add new files to the database.', self._ImportFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        #
        
        i_and_e_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        submenu = ClientGUIMenus.GenerateMenu( i_and_e_submenu )
        
        self._menubar_file_import_folders_paused = ClientGUIMenus.AppendMenuCheckItem( submenu, 'import folders', 'Pause the client\'s import folders.', self._controller.new_options.GetBoolean( 'pause_import_folders_sync' ), self._PausePlaySync, 'import_folders' )
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'export folders', 'Pause the client\'s export folders.', self._controller.new_options.GetBoolean( 'pause_export_folders_sync' ), self._PausePlaySync, 'export_folders' )
        
        ClientGUIMenus.AppendMenu( i_and_e_submenu, submenu, 'pause' )
        
        ClientGUIMenus.AppendSeparator( i_and_e_submenu )
        
        self._menubar_file_import_submenu = ClientGUIMenus.GenerateMenu( i_and_e_submenu )
        
        ClientGUIMenus.AppendMenu( i_and_e_submenu, self._menubar_file_import_submenu, 'check import folder now' )
        
        self._menubar_file_export_submenu = ClientGUIMenus.GenerateMenu( i_and_e_submenu )
        
        ClientGUIMenus.AppendMenu( i_and_e_submenu, self._menubar_file_export_submenu, 'run export folder now' )
        
        ClientGUIMenus.AppendSeparator( i_and_e_submenu )
        
        ClientGUIMenus.AppendMenuItem( i_and_e_submenu, 'manage import folders' + HC.UNICODE_ELLIPSIS, 'Manage folders from which the client can automatically import.', self._ManageImportFolders )
        ClientGUIMenus.AppendMenuItem( i_and_e_submenu, 'manage export folders' + HC.UNICODE_ELLIPSIS, 'Manage folders to which the client can automatically export.', self._ManageExportFolders )
        
        ClientGUIMenus.AppendMenu( menu, i_and_e_submenu, 'import and export folders' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        open = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( open, 'installation directory', 'Open the installation directory for this client.', self._OpenInstallFolder )
        ClientGUIMenus.AppendMenuItem( open, 'database directory', 'Open the database directory for this instance of the client.', self._OpenDBFolder )
        ClientGUIMenus.AppendMenuItem( open, 'quick export directory', 'Open the export directory so you can easily access the files you have exported.', self._OpenExportFolder )
        
        ClientGUIMenus.AppendMenu( menu, open, 'open' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'options' + HC.UNICODE_ELLIPSIS, 'Change how the client operates.', self._ManageOptions, role = QW.QAction.MenuRole.PreferencesRole )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        label = 'minimise to system tray'
        
        if not (HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS):
            
            label += ' (may be buggy/crashy!)'
            
        
        self._menubar_file_minimise_to_system_tray = ClientGUIMenus.AppendMenuItem( menu, label, 'Hide the client to an icon on your system tray.', self._FlipShowHideWholeUI, role = QW.QAction.MenuRole.ApplicationSpecificRole )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        we_borked_linux_pyinstaller = HC.PLATFORM_LINUX and not HC.RUNNING_FROM_SOURCE
        
        if not we_borked_linux_pyinstaller:
            
            ClientGUIMenus.AppendMenuItem( menu, 'restart', 'Shut the client down and then start it up again.', self.TryToExit, role = QW.QAction.MenuRole.ApplicationSpecificRole, restart = True )
            
        
        ClientGUIMenus.AppendMenuItem( menu, 'exit and force shutdown maintenance', 'Shut the client down and force any outstanding shutdown maintenance to run.', self.TryToExit, role = QW.QAction.MenuRole.ApplicationSpecificRole, force_shutdown_maintenance = True )
        
        ClientGUIMenus.AppendMenuItem( menu, 'exit', 'Shut the client down.', self.TryToExit, role = QW.QAction.MenuRole.QuitRole )
        
        return ( menu, '&file' )
        
    
    def _InitialiseMenuInfoHelp( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'help and getting started guide', 'Open hydrus\'s local help in your web browser.', self._OpenHelp )
        
        links = ClientGUIMenus.GenerateMenu( menu )
        
        site = ClientGUIMenus.AppendMenuIconItem( links, 'site', 'Open hydrus\'s website, which is a mirror of the local help.', CC.global_icons().hydrus_black_square, ClientPaths.LaunchURLInWebBrowser, 'https://hydrusnetwork.github.io/hydrus/' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'github repository', 'Open the hydrus github repository.', CC.global_icons().github, ClientPaths.LaunchURLInWebBrowser, 'https://github.com/hydrusnetwork/hydrus' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'latest build', 'Open the latest build on the hydrus github repository.', CC.global_icons().github, ClientPaths.LaunchURLInWebBrowser, 'https://github.com/hydrusnetwork/hydrus/releases/latest' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'issue tracker', 'Open the github issue tracker, which is run by users.', CC.global_icons().github, ClientPaths.LaunchURLInWebBrowser, 'https://github.com/hydrusnetwork/hydrus/issues' )
        site = ClientGUIMenus.AppendMenuIconItem( links, '8chan.moe /t/ (Hydrus Network General)', 'Open the 8chan.moe /t/ board, where a Hydrus Network General should exist with release posts and other status updates.', CC.global_icons().eight_chan, ClientPaths.LaunchURLInWebBrowser, 'https://8chan.moe/t/catalog.html' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'x', 'Open hydrus dev\'s X account, where he makes general progress updates and emergency notifications.', CC.global_icons().x, ClientPaths.LaunchURLInWebBrowser, 'https://x.com/hydrusnetwork' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'tumblr', 'Open hydrus dev\'s tumblr, where he makes release posts and other status updates.', CC.global_icons().tumblr, ClientPaths.LaunchURLInWebBrowser, 'https://hydrus.tumblr.com/' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'discord', 'Open a discord channel where many hydrus users congregate. Hydrus dev visits regularly.', CC.global_icons().discord, ClientPaths.LaunchURLInWebBrowser, 'https://discord.gg/wPHPCUZ' )
        site = ClientGUIMenus.AppendMenuIconItem( links, 'patreon', 'Open hydrus dev\'s patreon, which lets you support development.', CC.global_icons().patreon, ClientPaths.LaunchURLInWebBrowser, 'https://www.patreon.com/hydrus_dev' )
        
        ClientGUIMenus.AppendMenu( menu, links, 'links' )
        
        ClientGUIMenus.AppendMenuItem( menu, 'changelog', 'Open hydrus\'s local changelog in your web browser.', ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_CHANGELOG )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'add the public tag repository' + HC.UNICODE_ELLIPSIS, 'This will add the public tag repository to your client.', self._AutoRepoSetup )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        currently_darkmode = self._new_options.GetString( 'current_colourset' ) == 'darkmode'
        
        self._menu_item_help_darkmode = ClientGUIMenus.AppendMenuCheckItem( menu, 'darkmode', 'Set the \'darkmode\' colourset on and off.', currently_darkmode, self.FlipDarkmode )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'advanced_mode' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        self._menu_item_help_advanced_mode = ClientGUIMenus.AppendMenuCheckItem( menu, 'advanced mode', 'Turn on advanced menu options and buttons.', current_value, func )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        debug_menu = ClientGUIMenus.GenerateMenu( menu )
        
        debug_modes = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuCheckItem( debug_modes, 'force idle mode', 'Make the client consider itself idle and fire all maintenance routines right now. This may hang the gui for a while.', HG.force_idle_mode, self._SwitchBoolean, 'force_idle_mode' )
        ClientGUIMenus.AppendMenuItem( debug_modes, 'simulate a wake from sleep', 'Tell the controller to pretend that it just woke up from sleep.', self._controller.SimulateWakeFromSleepEvent )
        ClientGUIMenus.AppendMenuCheckItem( debug_modes, 'thumbnail debug mode', 'Show some thumbnail debug info.', HG.thumbnail_debug_mode, self._SwitchBoolean, 'thumbnail_debug_mode' )
        
        ClientGUIMenus.AppendMenu( debug_menu, debug_modes, 'debug modes' )
        
        profiling = ClientGUIMenus.GenerateMenu( debug_menu )
        
        profile_mode_message = 'If something is running slow, you can turn on a profile mode to have hydrus gather information on it. You probably want "db" profile mode, but if it seems to be lag related to dialog spawning or similar, you might like to try the "ui" mode.'
        profile_mode_message += '\n' * 2
        profile_mode_message += 'Turn the mode on, do the slow thing for a bit, and then turn it off. In your database directory will be a new profile log, which is really helpful for hydrus dev to figure out what is running slow for you and how to fix it.'
        profile_mode_message += '\n' * 2
        profile_mode_message += 'The Query Planner mode makes detailed database analysis of specific database queries. This is sometimes useful to hydev, but he will usually ask for it specifically.'
        profile_mode_message += '\n' * 2
        profile_mode_message += 'More information is available in the help, under \'reducing lag\'.'
        
        ClientGUIMenus.AppendMenuItem( profiling, 'what is this?', 'Show profile info.', ClientGUIDialogsMessage.ShowInformation, self, profile_mode_message )
        self._profile_mode_client_api_menu_item = ClientGUIMenus.AppendMenuCheckItem( profiling, 'profile mode (client api)', 'Run detailed \'profiles\' on Client API jobs.', HydrusProfiling.IsProfileMode( 'client_api' ), self.FlipProfileMode, 'client_api' )
        self._profile_mode_db_menu_item = ClientGUIMenus.AppendMenuCheckItem( profiling, 'profile mode (db)', 'Run detailed \'profiles\' on db jobs.', HydrusProfiling.IsProfileMode( 'db' ), self.FlipProfileMode, 'db' )
        self._profile_mode_threads_menu_item = ClientGUIMenus.AppendMenuCheckItem( profiling, 'profile mode (threads)', 'Run detailed \'profiles\' on background threaded tasks.', HydrusProfiling.IsProfileMode( 'threads' ), self.FlipProfileMode, 'threads' )
        self._profile_mode_ui_menu_item = ClientGUIMenus.AppendMenuCheckItem( profiling, 'profile mode (ui)', 'Run detailed \'profiles\' on some Qt jobs.', HydrusProfiling.IsProfileMode( 'ui' ), self.FlipProfileMode, 'ui' )
        ClientGUIMenus.AppendMenuCheckItem( profiling, 'query planner mode', 'Run detailed \'query plans\'.', HydrusProfiling.query_planner_mode, CG.client_controller.FlipQueryPlannerMode )
        
        ClientGUIMenus.AppendMenu( debug_menu, profiling, 'profiling' )
        
        report_modes = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'blurhash mode', 'Draw blurhashes instead of thumbnails.', HG.blurhash_mode, self._SwitchBoolean, 'blurhash_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'cache report mode', 'Have the image and thumb caches report their operation.', HG.cache_report_mode, self._SwitchBoolean, 'cache_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'callto report mode', 'Report whenever the thread pool is given a task.', HG.callto_report_mode, self._SwitchBoolean, 'callto_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'canvas tile borders mode', 'Draw tile borders.', HG.canvas_tile_outline_mode, self._SwitchBoolean, 'canvas_tile_outline_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'daemon report mode', 'Have the daemons report whenever they fire their jobs.', HG.daemon_report_mode, self._SwitchBoolean, 'daemon_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'db report mode', 'Have the db report query information, where supported.', HG.db_report_mode, self._SwitchBoolean, 'db_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'file report mode', 'Have the file manager report file request information, where supported.', HG.file_report_mode, self._SwitchBoolean, 'file_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'file import report mode', 'Have the db and file manager report file import progress.', HG.file_import_report_mode, self._SwitchBoolean, 'file_import_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'file sort report mode', 'Have the file sorter spam you with sort key results.', HG.file_sort_report_mode, self._SwitchBoolean, 'file_sort_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'gui report mode', 'Have the gui report inside information, where supported.', HG.gui_report_mode, self._SwitchBoolean, 'gui_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'hover window report mode', 'Have the hover windows report their show/hide logic.', HG.hover_window_report_mode, self._SwitchBoolean, 'hover_window_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'media load report mode', 'Have the client report media load information, where supported.', HG.media_load_report_mode, self._SwitchBoolean, 'media_load_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'mpv report mode', 'Have the client report significant mpv debug information.', HG.mpv_report_mode, self._SwitchBoolean, 'mpv_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'network report mode', 'Have the network engine report new jobs.', HG.network_report_mode, self._SwitchBoolean, 'network_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'network report mode (silent)', 'Have the network engine report new jobs, do not make spammy popups.', HG.network_report_mode_silent, self._SwitchBoolean, 'network_report_mode_silent' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'pubsub report mode', 'Report info about every pubsub processed.', HG.pubsub_report_mode, self._SwitchBoolean, 'pubsub_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'similar files metadata generation report mode', 'Have the perceptual_hash generation routine report its progress.', HG.phash_generation_report_mode, self._SwitchBoolean, 'phash_generation_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'shortcut report mode', 'Have the new shortcut system report what shortcuts it catches and whether it matches an action.', HG.shortcut_report_mode, self._SwitchBoolean, 'shortcut_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'subprocess report mode', 'Report whenever an external process is called.', HG.subprocess_report_mode, self._SwitchBoolean, 'subprocess_report_mode' )
        ClientGUIMenus.AppendMenuCheckItem( report_modes, 'subscription report mode', 'Have the subscription system report what it is doing.', HG.subscription_report_mode, self._SwitchBoolean, 'subscription_report_mode' )
        
        ClientGUIMenus.AppendMenu( debug_menu, report_modes, 'report modes' )
        
        gui_actions = ClientGUIMenus.GenerateMenu( debug_menu )
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        def flip_macos_antiflicker():
            
            HG.macos_antiflicker_test = not HG.macos_antiflicker_test
            
            if HG.macos_antiflicker_test:
                
                HydrusData.ShowText( 'Hey, the macOS safety code is now disabled. Please open a new media viewer and see if a mix of video and images show ok, no 100% CPU problems.' )
                
            
        
        if HC.PLATFORM_MACOS:
            
            ClientGUIMenus.AppendMenuItem( gui_actions, 'macos anti-flicker test', 'Try it out, let me know how it goes.', flip_macos_antiflicker )
            
        
        ClientGUIMenus.AppendMenuCheckItem( gui_actions, 'autocomplete delay mode', 'Delay all autocomplete requests at the database level by three seconds.', HG.autocomplete_delay_mode, self._SwitchBoolean, 'autocomplete_delay_mode' )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'close and reload current gui session', 'Save, clear, and then reload the current GUI Session. Might help with some forced style reloading.', self._ReloadCurrentGUISession )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'force a main gui layout now', 'Tell the gui to relayout--useful to test some gui bootup layout issues.', self.adjustSize )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'isolate existing mpv widgets', 'Tell the client to hide and do not re-use all existing mpv widgets, forcing new ones to be created on next request. This helps test out busted mpv windows that lose audio etc..', self._DebugIsolateMPVWindows )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a long text popup', 'Make a popup with text that will grow in size.', self._DebugLongTextPopup )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a modal popup in five seconds', 'Throw up a delayed modal popup to test with. It will stay alive for five seconds.', self._DebugMakeDelayedModalPopup, True )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a new page in five seconds', 'Throw a delayed page at the main notebook, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, self._controller.pub, 'new_page_query', default_location_context )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a non-cancellable modal popup in five seconds', 'Throw up a delayed modal popup to test with. It will stay alive for five seconds.', self._DebugMakeDelayedModalPopup, False )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a parentless text ctrl dialog', 'Make a parentless text control in a dialog to test some character event catching.', self._DebugMakeParentlessTextCtrl )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a popup in five seconds', 'Throw a delayed popup at the message manager, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, HydrusData.ShowText, 'This is a delayed popup message.' )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make a QMessageBox', 'Open a modal message dialog.', self._DebugMakeQMessageBox )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'make some popups', 'Throw some varied popups at the message manager, just to check it is working.', self._DebugMakeSomePopups )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'publish some sub files in five seconds', 'Publish some files like a subscription would.', self._controller.CallLater, 5, lambda: CG.client_controller.pub( 'imported_files_to_page', [ HydrusData.GenerateKey() for i in range( 5 ) ], 'example sub files' ) )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'refresh pages menu in five seconds', 'Delayed refresh the pages menu, giving you time to minimise or otherwise alter the client before it arrives.', self._controller.CallLater, 5, self._menu_updater_pages.update )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'reload current qss stylesheet', 'Reload the current QSS stylesheet. Helps if you just edited it on disk and do not want to restart.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RELOAD_CURRENT_STYLESHEET ) )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'reload icon cache', 'Reload the icons and pixmaps that new icon menus and buttons rely on. Will not affect widgets that are already loaded!', self._ReloadIconCache )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'reset multi-column list settings to default', 'Reset all multi-column list widths and other display settings to default.', self._DebugResetColumnListManager )
        ClientGUIMenus.AppendMenuItem( gui_actions, 'save \'last session\' gui session', 'Make an immediate save of the \'last session\' gui session. Mostly for testing crashes, where last session is not saved correctly.', self.ProposeSaveGUISession, CC.LAST_SESSION_SESSION_NAME )
        
        ClientGUIMenus.AppendMenu( debug_menu, gui_actions, 'gui actions' )
        
        data_actions = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuCheckItem( data_actions, 'db ui-hang relief mode', 'Have UI-synchronised database jobs process pending Qt events while they wait.', HG.db_ui_hang_relief_mode, self._SwitchBoolean, 'db_ui_hang_relief_mode' )
        ClientGUIMenus.AppendMenuItem( data_actions, 'flush log', 'Command the log to write any buffered contents to hard drive.', HydrusData.DebugPrint, 'Flushing log' )
        ClientGUIMenus.AppendMenuItem( data_actions, 'force database commit', 'Command the database to flush all pending changes to disk.', CG.client_controller.ForceDatabaseCommit )
        ClientGUIMenus.AppendMenuItem( data_actions, 'review threads', 'Show current threads and what they are doing.', self._ReviewThreads )
        ClientGUIMenus.AppendMenuItem( data_actions, 'show env', 'Print your current environment variables.', HydrusEnvironment.DumpEnv )
        ClientGUIMenus.AppendMenuItem( data_actions, 'show scheduled jobs', 'Print some information about the currently scheduled jobs log.', self._DebugShowScheduledJobs )
        ClientGUIMenus.AppendMenuItem( data_actions, 'subscription manager snapshot', 'Have the subscription system show what it is doing.', self._controller.subscriptions_manager.ShowSnapshot )
        ClientGUIMenus.AppendSeparator( data_actions )
        ClientGUIMenus.AppendMenuItem( data_actions, 'simulate program exit signal', 'Kill the program via a QApplication exit.', QW.QApplication.instance().exit )
        
        ClientGUIMenus.AppendMenu( debug_menu, data_actions, 'data actions' )
        
        memory_actions = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuItem( memory_actions, 'run fast memory maintenance', 'Tell all the fast caches to maintain themselves.', self._controller.MaintainMemoryFast )
        ClientGUIMenus.AppendMenuItem( memory_actions, 'run slow memory maintenance', 'Tell all the slow caches to maintain themselves.', self._controller.MaintainMemorySlow )
        ClientGUIMenus.AppendMenuItem( memory_actions, 'clear all rendering caches', 'Tell the image rendering system to forget all current images, tiles, and thumbs. This will often free up a bunch of memory immediately.', self._controller.ClearCaches )
        ClientGUIMenus.AppendMenuItem( memory_actions, 'clear thumbnail cache', 'Tell the thumbnail cache to forget everything and redraw all current thumbs.', self._controller.pub, 'clear_thumbnail_cache' )
        
        if HydrusMemory.PYMPLER_OK:
            
            ClientGUIMenus.AppendSeparator( memory_actions )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'WARNING, MEGA-LAGGY: print memory-use summary', 'Print some information about the python memory use to the log.', self._DebugPrintMemoryUse )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'WARNING, MEGA-LAGGY: take memory-use snapshot', 'Capture current memory use.', self._DebugTakeMemoryUseSnapshot )
            ClientGUIMenus.AppendMenuItem( memory_actions, 'WARNING, MEGA-LAGGY: print memory-use snapshot diff', 'Show memory use differences since the last snapshot.', self._DebugShowMemoryUseDifferences )
            
        
        ClientGUIMenus.AppendMenu( debug_menu, memory_actions, 'memory actions' )
        
        network_actions = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuItem( network_actions, 'review current network jobs', 'Review the jobs currently running in the network engine.', self._ReviewNetworkJobs )
        ClientGUIMenus.AppendMenuItem( network_actions, 'fetch a url', 'Fetch a URL using the network engine as per normal.', self._DebugFetchAURL )
        
        ClientGUIMenus.AppendMenu( debug_menu, network_actions, 'network actions' )
        
        tests = ClientGUIMenus.GenerateMenu( debug_menu )
        
        ClientGUIMenus.AppendMenuItem( tests, 'run the ui test', 'Run hydrus_dev\'s weekly UI Test. Guaranteed to work and not mess up your session, ha ha.', self._RunUITest )
        ClientGUIMenus.AppendMenuItem( tests, 'run the client api test', 'Run hydrus_dev\'s weekly Client API Test. Guaranteed to work and not mess up your session, ha ha.', self._RunClientAPITest )
        ClientGUIMenus.AppendMenuItem( tests, 'run the server test on fresh server', 'This will try to initialise an already running server.', self._RunServerTest )
        ClientGUIMenus.AppendSeparator( tests )
        ClientGUIMenus.AppendMenuItem( tests, 'run the visual duplicates tuning suite', 'Run some stats on some example files using the visual duplicates system.', self._RunVisualDuplicatesTuningSuite )
        ClientGUIMenus.AppendSeparator( tests )
        ClientGUIMenus.AppendMenuCheckItem( tests, 'fake petition mode', 'Fill the petition panels with fake local data for testing.', HG.fake_petition_mode, self._SwitchBoolean, 'fake_petition_mode' )
        ClientGUIMenus.AppendSeparator( tests )
        ClientGUIMenus.AppendMenuItem( tests, 'do self-sigterm', 'Test a sigterm call for fast, non-ui-originating shutdown.', CG.client_controller.DoSelfSigterm )
        ClientGUIMenus.AppendMenuItem( tests, 'do self-sigterm (fake)', 'Test a sigterm call for fast, non-ui-originating shutdown.', CG.client_controller.DoSelfSigtermFake )
        ClientGUIMenus.AppendSeparator( tests )
        ClientGUIMenus.AppendMenuItem( tests, 'turn off faulthandler crash logging', 'Disable the python crash logging so you can use WER or Linux Dumps for your own debugging situation.', TurnOffCrashReporting )
        ClientGUIMenus.AppendSeparator( tests )
        ClientGUIMenus.AppendMenuItem( tests, 'induce a program crash', 'Crash the program to test a crash dumping/debugging routine.', CrashTheProgram, self )
        
        ClientGUIMenus.AppendMenu( debug_menu, tests, 'tests, do not touch' )
        
        ClientGUIMenus.AppendMenu( menu, debug_menu, 'debug' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'about Qt', 'See information about the Qt framework.', QW.QMessageBox.aboutQt, self, role = QW.QAction.MenuRole.AboutQtRole )
        ClientGUIMenus.AppendMenuItem( menu, 'about', 'See this client\'s version and other information.', self._AboutWindow, role = QW.QAction.MenuRole.AboutRole )
        
        return ( menu, '&help' )
        
    
    def _InitialiseMenuInfoNetwork( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        pause_all_new_network_traffic = self._controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        
        self._menubar_network_all_traffic_paused = ClientGUIMenus.AppendMenuCheckItem( submenu, 'all new network traffic', 'Stop any new network jobs from sending data.', pause_all_new_network_traffic, self.FlipNetworkTrafficPaused )
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'always boot the client with paused network traffic', 'Always start the program with network traffic paused.', self._controller.new_options.GetBoolean( 'boot_with_network_traffic_paused' ), self._controller.new_options.FlipBoolean, 'boot_with_network_traffic_paused' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        self._menubar_network_subscriptions_paused = ClientGUIMenus.AppendMenuCheckItem( submenu, 'subscriptions', 'Pause the client\'s synchronisation with website subscriptions.', self._controller.new_options.GetBoolean( 'pause_subs_sync' ), self.FlipSubscriptionsPaused )
        
        self._menubar_network_nudge_subs = ClientGUIMenus.AppendMenuItem( submenu, 'nudge subscriptions awake', 'Tell the subs daemon to wake up, just in case any subs are due.', self._controller.subscriptions_manager.Wake )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        self._menubar_network_paged_import_queues_paused = ClientGUIMenus.AppendMenuCheckItem( submenu, 'paged file import queues', 'Pause all file import queues.', self._controller.new_options.GetBoolean( 'pause_all_file_queues' ), self._controller.new_options.FlipBoolean, 'pause_all_file_queues' )
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'gallery searches', 'Pause all gallery imports\' searching.', self._controller.new_options.GetBoolean( 'pause_all_gallery_searches' ), self._controller.new_options.FlipBoolean, 'pause_all_gallery_searches' )
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'watcher checkers', 'Pause all watchers\' checking.', self._controller.new_options.GetBoolean( 'pause_all_watcher_checkers' ), self._controller.new_options.FlipBoolean, 'pause_all_watcher_checkers' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'manage subscriptions' + HC.UNICODE_ELLIPSIS, 'Change the queries you want the client to regularly import from.', self._ManageSubscriptions )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'review bandwidth usage and edit rules', 'See where you are consuming data.', self._ReviewBandwidth )
        ClientGUIMenus.AppendMenuItem( submenu, 'review current network jobs', 'Review the jobs currently running in the network engine.', self._ReviewNetworkJobs )
        ClientGUIMenus.AppendMenuItem( submenu, 'review session cookies', 'Review and edit which cookies you have for which network contexts.', self._ReviewNetworkSessions )
        ClientGUIMenus.AppendMenuItem( submenu, 'manage http headers' + HC.UNICODE_ELLIPSIS, 'Configure how the client talks to the network.', self._ManageNetworkHeaders )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage upnp' + HC.UNICODE_ELLIPSIS, 'If your router supports it, see and edit your current UPnP NAT traversal mappings.', self._ManageUPnP )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'data' )
        
        #
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        if not ClientParsing.HTML5LIB_IS_OK:
            
            message = 'The client was unable to import html5lib on boot. This is an important parsing library that performs better than the usual backup, lxml. Without it, some downloaders will not work well and you will miss tags and files.'
            message += '\n' * 2
            message += 'You are likely running from source, so I recommend you close the client, run \'pip install html5lib\' (or whatever is appropriate for your environment) and try again. You can double-check what imported ok under help->about.'
            
            ClientGUIMenus.AppendMenuItem( submenu, '*** html5lib not found! ***', 'Your client does not have an important library.', ClientGUIDialogsMessage.ShowWarning, self, message )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
        
        ClientGUIMenus.AppendMenuItem( submenu, 'import downloaders' + HC.UNICODE_ELLIPSIS, 'Import new download capability through encoded pngs from other users.', self._ImportDownloaders )
        ClientGUIMenus.AppendMenuItem( submenu, 'export downloaders' + HC.UNICODE_ELLIPSIS, 'Export downloader components to easy-import pngs.', self._ExportDownloader )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage default import options' + HC.UNICODE_ELLIPSIS, 'Change the default import options for each of your linked url matches.', self._ManageDefaultImportOptions )
        ClientGUIMenus.AppendMenuItem( submenu, 'manage downloader and url display' + HC.UNICODE_ELLIPSIS, 'Configure how downloader objects present across the client.', self._ManageDownloaderDisplay )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        clipboard_menu = ClientGUIMenus.GenerateMenu( submenu )
        
        ClientGUIMenus.AppendMenuCheckItem( clipboard_menu, 'watcher urls', 'Automatically import watcher URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_watcher_urls' )
        ClientGUIMenus.AppendMenuCheckItem( clipboard_menu, 'other recognised urls', 'Automatically import recognised URLs that enter the clipboard just as if you drag-and-dropped them onto the ui.', self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' ), self._FlipClipboardWatcher, 'watch_clipboard_for_other_recognised_urls' )
        
        ClientGUIMenus.AppendMenu( submenu, clipboard_menu, 'watch clipboard for urls' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'downloaders' )
        
        #
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage url class links' + HC.UNICODE_ELLIPSIS, 'Configure how URLs present across the client.', self._ManageURLClassLinks )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage gallery url generators' + HC.UNICODE_ELLIPSIS, 'Manage the client\'s GUGs, which convert search terms into URLs.', self._ManageGUGs )
        ClientGUIMenus.AppendMenuItem( submenu, 'manage url classes' + HC.UNICODE_ELLIPSIS, 'Configure which URLs the client can recognise.', self._ManageURLClasses )
        ClientGUIMenus.AppendMenuItem( submenu, 'manage parsers' + HC.UNICODE_ELLIPSIS, 'Manage the client\'s parsers, which convert URL content into hydrus metadata.', self._ManageParsers )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'SEMI-LEGACY: manage file lookup scripts' + HC.UNICODE_ELLIPSIS, 'Manage how the client parses different types of web content.', self._ManageParsingScripts )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'downloader components' )
        
        #
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage logins' + HC.UNICODE_ELLIPSIS, 'Edit which domains you wish to log in to.', self._ManageLogins )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage login scripts' + HC.UNICODE_ELLIPSIS, 'Manage the client\'s login scripts, which define how to log in to different sites.', self._ManageLoginScripts )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'DEBUG: do tumblr GDPR click-through', 'Do a manual click-through for the tumblr GDPR page.', self._controller.CallLater, 0.0, self._controller.network_engine.login_manager.LoginTumblrGDPR )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'logins (legacy; simple sites only)' )
        
        #
        
        return ( menu, '&network' )
        
    
    def _InitialiseMenuInfoPages( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._menubar_pages_page_count = ClientGUIMenus.AppendMenuLabel( menu, 'initialising', 'You have this many pages open.' )
        
        self._menubar_pages_session_weight = ClientGUIMenus.AppendMenuItem( menu, 'initialising', 'Your session is this heavy.', self._ShowPageWeightInfo )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        self._page_nav_history_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuLabel( self._page_nav_history_menu, 'no tab history', 'Your page history is currently empty.', None, True )
        
        ClientGUIMenus.AppendMenu( menu, self._page_nav_history_menu, 'history' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'refresh', 'If the current page has a search, refresh it.', self._RefreshCurrentPage )
        
        splitter_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'show/hide sidebar and preview panel', 'Show or hide the panels on the left.', self._ShowHideSplitters )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuCheckItem( splitter_menu, 'save current page\'s sidebar/preview size on client exit', 'Set whether the current width and height of the sidebar and preview panels should be saved on client exit.', self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ), self._new_options.FlipBoolean, 'saving_sash_positions_on_exit' )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'save current page\'s sidebar/preview size now', 'Overwrite the saved value with the current page\'s sizes.', self._SaveSplitterPositions )
        
        ClientGUIMenus.AppendSeparator( splitter_menu )
        
        ClientGUIMenus.AppendMenuItem( splitter_menu, 'restore all pages\' sidebar/preview sizes to saved value', 'Restore all pages\' sizes to the saved value.', self._RestoreSplitterPositions )
        
        ClientGUIMenus.AppendMenu( menu, splitter_menu, 'sidebar and preview panels' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        self._menubar_pages_sessions_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, self._menubar_pages_sessions_submenu, 'sessions' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pick a new page' + HC.UNICODE_ELLIPSIS, 'Choose a new page to open.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE ) )
        
        #
        
        self._menubar_pages_search_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, self._menubar_pages_search_submenu, 'new file search page' )
        
        #
        
        self._menubar_pages_petition_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, self._menubar_pages_petition_submenu, 'new petition page' )
        
        #
        
        download_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( download_menu, 'url download', 'Open a new tab to download some separate urls.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'watcher', 'Open a new tab to watch threads or other updating locations.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'gallery', 'Open a new tab to download from gallery sites.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE ) )
        ClientGUIMenus.AppendMenuItem( download_menu, 'simple downloader', 'Open a new tab to download files from generic galleries or threads.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE ) )
        
        ClientGUIMenus.AppendMenu( menu, download_menu, 'new download page' )
        
        #
        
        special_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( special_menu, 'page of pages', 'Open a new tab that can hold more tabs.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE_OF_PAGES ) )
        ClientGUIMenus.AppendMenuItem( special_menu, 'duplicates processing', 'Open a new tab to discover and filter duplicate files.', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE ) )
        
        ClientGUIMenus.AppendMenu( menu, special_menu, 'new special page' )
        
        #
        
        ClientGUIMenus.AppendSeparator( menu )
        
        special_command_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( special_command_menu, 'clear all multiwatcher highlights', 'Command all multiwatcher pages to clear their highlighted watchers.', CG.client_controller.pub, 'clear_multiwatcher_highlights' )
        
        ClientGUIMenus.AppendMenu( menu, special_command_menu, 'special commands' )
        
        #
        
        return ( menu, '&pages' )
        
    
    def _InitialiseMenuInfoServices( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuCheckItem( submenu, 'all repository synchronisation', 'Pause the client\'s synchronisation with hydrus repositories.', self._controller.new_options.GetBoolean( 'pause_repo_sync' ), self._PausePlaySync, 'repo' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'pause' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'review services', 'Look at the services your client connects to.', self._ReviewServices )
        ClientGUIMenus.AppendMenuItem( menu, 'manage services' + HC.UNICODE_ELLIPSIS, 'Edit the services your client connects to.', self._ManageServices )
        
        self._menubar_services_admin_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, self._menubar_services_admin_submenu, 'administrate services' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'import repository update files' + HC.UNICODE_ELLIPSIS, 'Add repository update files to the database.', self._ImportUpdateFiles )
        
        return ( menu, '&services' )
        
    
    def _InitialiseMenuInfoTags( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'migrate tags' + HC.UNICODE_ELLIPSIS, 'Migrate tags from one place to another.', self._MigrateTags )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'manage tag display and search' + HC.UNICODE_ELLIPSIS, 'Set which tags you want to see from which services.', self._ManageTagDisplay )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'manage tag siblings' + HC.UNICODE_ELLIPSIS, 'Set certain tags to be automatically replaced with other tags.', self._ManageTagSiblings )
        ClientGUIMenus.AppendMenuItem( menu, 'manage tag parents' + HC.UNICODE_ELLIPSIS, 'Set certain tags to be automatically added with other tags.', self._ManageTagParents )
        
        ClientGUIMenus.AppendMenuItem( menu, 'manage where tag siblings and parents apply' + HC.UNICODE_ELLIPSIS, 'Set which services\' siblings and parents apply where.', self._ManageTagDisplayApplication )
        
        #
        
        tag_display_maintenance_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( tag_display_maintenance_menu, 'review current sync', 'See how siblings and parents are currently applied.', self._ReviewTagDisplayMaintenance )
        
        ClientGUIMenus.AppendSeparator( tag_display_maintenance_menu )
        
        ClientGUIMenus.AppendMenuItem( tag_display_maintenance_menu, 'sync now', 'Start up any outstanding work now.', self._SyncTagDisplayMaintenanceNow )
        
        ClientGUIMenus.AppendSeparator( tag_display_maintenance_menu )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'tag_display_maintenance_during_idle' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        self._menubar_tags_tag_display_maintenance_during_idle = ClientGUIMenus.AppendMenuCheckItem( tag_display_maintenance_menu, 'sync tag display during idle time', 'Control whether tag display processing can work during idle time.', current_value, func )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'tag_display_maintenance_during_active' )
        
        current_value = check_manager.GetCurrentValue()
        func = check_manager.Invert
        
        self._menubar_tags_tag_display_maintenance_during_active = ClientGUIMenus.AppendMenuCheckItem( tag_display_maintenance_menu, 'sync tag display during normal time', 'Control whether tag display processing can work during normal time.', current_value, func )
        
        ClientGUIMenus.AppendMenu( menu, tag_display_maintenance_menu, 'sibling/parent sync' )
        
        #
        
        return ( menu, '&tags' )
        
    
    
    def _InitialiseMenuInfoUndo( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._menubar_undo_undo = ClientGUIMenus.AppendMenuItem( menu, 'initialising', 'Undo last operation.', self._controller.pub, 'undo' )
        
        self._menubar_undo_redo = ClientGUIMenus.AppendMenuItem( menu, 'initialising', 'Redo last operation.', self._controller.pub, 'redo' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        self._menubar_undo_closed_pages_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenu( menu, self._menubar_undo_closed_pages_submenu, 'closed pages' )
        
        return ( menu, '&undo' )
        
    
    def _InitialiseSession( self ):
        
        default_gui_session = HC.options[ 'default_gui_session' ]
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
        
        cannot_load_from_db = default_gui_session not in existing_session_names
        
        load_a_blank_page = HC.options[ 'default_gui_session' ] == 'just a blank page' or cannot_load_from_db
        
        if not load_a_blank_page:
            
            if self._controller.LastShutdownWasBad():
                
                # this can be upgraded to a nicer checkboxlist dialog to select pages or w/e
                
                message = 'It looks like the last instance of the client did not shut down cleanly.'
                message += '\n' * 2
                message += 'Would you like to try loading your default session "' + default_gui_session + '", or just a blank page?'
                message += '\n' * 2
                message += 'This will auto-choose to open your default session in 15 seconds.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Previous shutdown was bad', yes_label = 'try to load "' + default_gui_session + '"', no_label = 'just load a blank page', auto_yes_time = 15 )
                
                if result == QW.QDialog.DialogCode.Rejected:
                    
                    load_a_blank_page = True
                    
                
            
        
        def do_it( default_gui_session, load_a_blank_page ):
            
            try:
                
                if load_a_blank_page:
                    
                    default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
                    
                    self._notebook.NewPageQuery( default_location_context, on_deepest_notebook = True )
                    
                    self._first_session_loaded = True
                    
                    self._controller.ReportFirstSessionInitialised()
                    
                else:
                    
                    self._notebook.LoadGUISession( default_gui_session )
                    
                
            finally:
                
                last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
                
                #self._controller.CallLaterQtSafe(self, 1.0, 'adjust size', self.adjustSize ) # some i3 thing--doesn't layout main gui on init for some reason
                
                self._controller.CallLaterQtSafe(self, last_session_save_period_minutes * 60, 'auto save session', self.AutoSaveLastSession )
                
                self._BootOrStopClipboardWatcherIfNeeded()
                
            
        
        self._controller.CallLaterQtSafe( self, 0.25, 'load initial session', do_it, default_gui_session, load_a_blank_page )
        
    
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
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        service = self._controller.services_manager.GetService( service_key )
        
        self._controller.CallToThread( do_it, service, lock )
        
    
    def _STARTManageAccountTypes( self, service_key ):
        
        admin_service = CG.client_controller.services_manager.GetService( service_key )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'loading account types' + HC.UNICODE_ELLIPSIS )
        
        self._controller.pub( 'message', job_status )
        
        def work_callable():
            
            response = admin_service.Request( HC.GET, 'account_types' )
            
            account_types = response[ 'account_types' ]
            
            return account_types
            
        
        def publish_callable( account_types ):
            
            job_status.FinishAndDismiss()
            
            self._ManageAccountTypes( service_key, account_types )
            
        
        def errback_callable( etype, value, tb ):
            
            HydrusData.ShowText( 'Sorry, unable to load account types:' )
            HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
        
        job.start()
        
    
    def _ManageAccountTypes( self, service_key, account_types ):
        
        admin_service = CG.client_controller.services_manager.GetService( service_key )
        
        title = 'edit account types'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUIHydrusNetwork.EditAccountTypesPanel( dlg, admin_service.GetServiceType(), account_types )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( account_types, deletee_account_type_keys_to_new_account_type_keys ) = panel.GetValue()
                
                serialisable_deletee_account_type_keys_to_new_account_type_keys = HydrusSerialisable.SerialisableBytesDictionary( deletee_account_type_keys_to_new_account_type_keys )
                
                def do_it():
                    
                    admin_service.Request( HC.POST, 'account_types', { 'account_types' : account_types, 'deletee_account_type_keys_to_new_account_type_keys' : serialisable_deletee_account_type_keys_to_new_account_type_keys } )
                    
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _ManageDefaultImportOptions( self ):
        
        title = 'edit default tag import options'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ) = domain_manager.GetDefaultTagImportOptions()
            
            ( file_post_default_note_import_options, watchable_default_note_import_options, url_class_keys_to_note_import_options ) = domain_manager.GetDefaultNoteImportOptions()
            
            url_classes = domain_manager.GetURLClasses()
            parsers = domain_manager.GetParsers()
            
            url_class_keys_to_parser_keys = domain_manager.GetURLClassKeysToParserKeys()
            
            panel = ClientGUIScrolledPanelsEdit.EditDefaultImportOptionsPanel(
                dlg,
                url_classes,
                parsers,
                url_class_keys_to_parser_keys,
                file_post_default_tag_import_options,
                watchable_default_tag_import_options,
                url_class_keys_to_tag_import_options,
                file_post_default_note_import_options,
                watchable_default_note_import_options,
                url_class_keys_to_note_import_options
            )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                (
                    file_post_default_tag_import_options,
                    watchable_default_tag_import_options,
                    url_class_keys_to_tag_import_options,
                    file_post_default_note_import_options,
                    watchable_default_note_import_options,
                    url_class_keys_to_note_import_options
                ) = panel.GetValue()
                
                domain_manager.SetDefaultTagImportOptions( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options )
                domain_manager.SetDefaultNoteImportOptions( file_post_default_note_import_options, watchable_default_note_import_options, url_class_keys_to_note_import_options )
                
            
        
    
    def _ManageDownloaderDisplay( self ):
        
        title = 'manage downloader display'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            gug_keys_to_display = domain_manager.GetGUGKeysToDisplay()
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_display = domain_manager.GetURLClassKeysToDisplay()
            
            show_unmatched_urls_in_media_viewer = CG.client_controller.new_options.GetBoolean( 'show_unmatched_urls_in_media_viewer' )
            
            panel = ClientGUIDownloaders.EditDownloaderDisplayPanel( dlg, self._controller.network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display, show_unmatched_urls_in_media_viewer )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( gug_keys_to_display, url_class_keys_to_display, show_unmatched_urls_in_media_viewer ) = panel.GetValue()
                
                domain_manager.SetGUGKeysToDisplay( gug_keys_to_display )
                domain_manager.SetURLClassKeysToDisplay( url_class_keys_to_display )
                
                CG.client_controller.new_options.SetBoolean( 'show_unmatched_urls_in_media_viewer', show_unmatched_urls_in_media_viewer )
                
            
        
    
    def _ManageExportFolders( self ):
        
        def qt_do_it():
            
            export_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folders' ) as dlg:
                
                panel = ClientGUIExport.EditExportFoldersPanel( dlg, export_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
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
                
                original_pause_status = controller.new_options.GetBoolean( 'pause_export_folders_sync' )
                
                controller.new_options.SetBoolean( 'pause_export_folders_sync', True )
                
                try:
                    
                    if HG.export_folders_running:
                        
                        job_status = ClientThreading.JobStatus()
                        
                        try:
                            
                            job_status.SetStatusText( 'Waiting for export folders to finish.' )
                            
                            controller.pub( 'message', job_status )
                            
                            while HG.export_folders_running:
                                
                                time.sleep( 0.1 )
                                
                                if HG.started_shutdown:
                                    
                                    return
                                    
                                
                            
                        finally:
                            
                            job_status.FinishAndDismiss()
                            
                        
                    
                    try:
                        
                        controller.CallBlockingToQt( self, qt_do_it )
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.new_options.SetBoolean( 'pause_export_folders_sync', original_pause_status )
                    
                    controller.pub( 'notify_new_export_folders' )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageGUGs( self ):
        
        title = 'manage gallery url generators'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            gugs = domain_manager.GetGUGs()
            
            panel = ClientGUIDownloaders.EditGUGsPanel( dlg, gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                gugs = panel.GetValue()
                
                domain_manager.SetGUGs( gugs )
                
            
        
    
    def _ManageImportFolders( self ):
        
        def qt_do_it():
            
            import_folders = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import folders' ) as dlg:
                
                panel = ClientGUIImportFolders.EditImportFoldersPanel( dlg, import_folders )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
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
                
                original_pause_status = controller.new_options.GetBoolean( 'pause_import_folders_sync' )
                
                controller.new_options.SetBoolean( 'pause_import_folders_sync', True )
                
                try:
                    
                    if HG.import_folders_running:
                        
                        job_status = ClientThreading.JobStatus()
                        
                        try:
                            
                            job_status.SetStatusText( 'Waiting for import folders to finish.' )
                            
                            controller.pub( 'message', job_status )
                            
                            while HG.import_folders_running:
                                
                                time.sleep( 0.1 )
                                
                                if HG.started_shutdown:
                                    
                                    return
                                    
                                
                            
                        finally:
                            
                            job_status.FinishAndDismiss()
                            
                        
                    
                    try:
                        
                        controller.CallBlockingToQt( self, qt_do_it )
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    
                finally:
                    
                    controller.new_options.SetBoolean( 'pause_import_folders_sync', original_pause_status )
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageLogins( self ):
        
        title = 'manage logins'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            login_manager = self._controller.network_engine.login_manager
            
            login_scripts = login_manager.GetLoginScripts()
            domains_to_login_info = login_manager.GetDomainsToLoginInfo()
            
            panel = ClientGUILogin.EditLoginsPanel( dlg, self._controller.network_engine, login_scripts, domains_to_login_info )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
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
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                login_scripts = panel.GetValue()
                
                login_manager.SetLoginScripts( login_scripts )
                
            
        
    
    def _ManageNetworkHeaders( self ):
        
        title = 'manage http headers'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            network_contexts_to_custom_header_dicts = domain_manager.GetNetworkContextsToCustomHeaderDicts()
            
            panel = ClientGUINetwork.EditNetworkContextCustomHeadersPanel( dlg, network_contexts_to_custom_header_dicts )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                network_contexts_to_custom_header_dicts = panel.GetValue()
                
                domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
                
            
        
    
    def _ManageOptions( self ):
        
        title = 'manage options'
        frame_key = 'manage_options_dialog'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title, frame_key ) as dlg:
            
            panel = ClientGUIManageOptionsPanel.ManageOptionsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        qt_style_name = self._controller.new_options.GetNoneableString( 'qt_style_name' )
        qt_stylesheet_name = self._controller.new_options.GetNoneableString( 'qt_stylesheet_name' )
        
        if qt_style_name != ClientGUIStyle.CURRENT_STYLE_NAME:
            
            try:
                
                if qt_style_name is None:
                    
                    ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                    
                else:
                    
                    ClientGUIStyle.SetStyleFromName( qt_style_name )
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            self._DoMenuBarStyleHack()
            
        
        if qt_stylesheet_name != ClientGUIStyle.CURRENT_STYLESHEET_FILENAME:
            
            try:
                
                if qt_stylesheet_name is None:
                    
                    ClientGUIStyle.ClearStyleSheet()
                    
                else:
                    
                    ClientGUIStyle.SetStyleSheetFromPath( qt_stylesheet_name )
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
        ClientGUIFunctions.UpdateAppDisplayName()
        
        self._controller.pub( 'wake_daemons' )
        self.SetStatusBarDirty()
        self._controller.pub( 'refresh_page_name' )
        self._controller.pub( 'notify_new_colourset' )
        self._controller.pub( 'notify_new_favourite_tags' )
        
        CG.client_controller.ReinitGlobalSettings()
        
        self._menu_item_help_darkmode.setChecked( CG.client_controller.new_options.GetString( 'current_colourset' ) == 'darkmode' )
        self._menu_item_help_advanced_mode.setChecked( self._new_options.GetBoolean( 'advanced_mode' ) )
        
        self._UpdateSystemTrayIcon()
        
    
    def _ManageParsers( self ):
        
        title = 'manage parsers'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            parsers = domain_manager.GetParsers()
            
            panel = ClientGUIParsing.EditParsersPanel( dlg, parsers )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                parsers = panel.GetValue()
                
                domain_manager.SetParsers( parsers )
                
                domain_manager.TryToLinkURLClassesAndParsers()
                
            
        
    
    def _ManageParsingScripts( self ):
        
        title = 'manage parsing scripts'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIParsingLegacy.ManageParsingScriptsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageServer( self, service_key ):
        
        title = 'manage server services'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIServersideServices.ManageServerServicesPanel( dlg, service_key )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageServices( self, auto_account_creation_service_key = None ):
        
        original_pause_status = self._controller.new_options.GetBoolean( 'pause_repo_sync' )
        
        self._controller.new_options.SetBoolean( 'pause_repo_sync', True )
        
        try:
            
            title = 'manage services'
            
            with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
                
                panel = ClientGUIClientsideServices.ManageClientServicesPanel( dlg, auto_account_creation_service_key = auto_account_creation_service_key )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        finally:
            
            self._controller.new_options.SetBoolean( 'pause_repo_sync', original_pause_status )
            
        
    
    def _ManageServiceOptionsNullificationPeriod( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        nullification_period = service.GetNullificationPeriod()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit anonymisation period' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUITime.TimeDeltaWidget( panel, min = HydrusNetwork.MIN_NULLIFICATION_PERIOD, days = True, hours = True, minutes = True, seconds = True )
            
            control.SetValue( nullification_period )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                nullification_period = control.GetValue()
                
                if nullification_period > HydrusNetwork.MAX_NULLIFICATION_PERIOD:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, the value you entered was too high. The max is {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MAX_NULLIFICATION_PERIOD ) ) )
                    
                    return
                    
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusTitle( 'setting anonymisation period' )
                job_status.SetStatusText( 'uploading' + HC.UNICODE_ELLIPSIS )
                
                self._controller.pub( 'message', job_status )
                
                def work_callable():
                    
                    service.Request( HC.POST, 'options_nullification_period', { 'nullification_period' : nullification_period } )
                    
                    return 1
                    
                
                def publish_callable( gumpf ):
                    
                    job_status.SetStatusText( 'done!' )
                    
                    job_status.FinishAndDismiss( 5 )
                    
                    service.SetAccountRefreshDueNow()
                    
                
                def errback_ui_cleanup_callable():
                    
                    job_status.SetStatusText( 'error!' )
                    
                    job_status.Finish()
                    
                
                job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
                
                job.start()
                
            
        
    
    def _ManageServiceOptionsTagFilter( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        tag_filter = service.GetTagFilter()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag repository tag filter' ) as dlg:
            
            namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            message = 'The repository will apply this to all new pending tags that are uploaded to it. Anything that does not pass is silently discarded.'
            
            panel = ClientGUITagFilter.EditTagFilterPanel( dlg, tag_filter, message = message, namespaces = namespaces )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                tag_filter = panel.GetValue()
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusTitle( 'setting tag filter' )
                job_status.SetStatusText( 'uploading' + HC.UNICODE_ELLIPSIS )
                
                self._controller.pub( 'message', job_status )
                
                def work_callable():
                    
                    service.Request( HC.POST, 'tag_filter', { 'tag_filter' : tag_filter } )
                    
                    return 1
                    
                
                def publish_callable( gumpf ):
                    
                    job_status.SetStatusText( 'done!' )
                    
                    job_status.FinishAndDismiss( 5 )
                    
                    service.SetAccountRefreshDueNow()
                    
                
                def errback_ui_cleanup_callable():
                    
                    job_status.SetStatusText( 'error!' )
                    
                    job_status.Finish()
                    
                
                job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
                
                job.start()
                
            
        
    
    def _ManageServiceOptionsUpdatePeriod( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        update_period = service.GetUpdatePeriod()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit update period' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUITime.TimeDeltaWidget( panel, min = HydrusNetwork.MIN_UPDATE_PERIOD, days = True, hours = True, minutes = True, seconds = True )
            
            control.SetValue( update_period )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                update_period = control.GetValue()
                
                if update_period > HydrusNetwork.MAX_UPDATE_PERIOD:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, the value you entered was too high. The max is {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MAX_UPDATE_PERIOD ) ) )
                    
                    return
                    
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusTitle( 'setting update period' )
                job_status.SetStatusText( 'uploading' + HC.UNICODE_ELLIPSIS )
                
                self._controller.pub( 'message', job_status )
                
                def work_callable():
                    
                    service.Request( HC.POST, 'options_update_period', { 'update_period' : update_period } )
                    
                    return 1
                    
                
                def publish_callable( gumpf ):
                    
                    job_status.SetStatusText( 'done!' )
                    
                    job_status.FinishAndDismiss( 5 )
                    
                    service.DoAFullMetadataResync()
                    
                    service.SetAccountRefreshDueNow()
                    
                
                def errback_ui_cleanup_callable():
                    
                    job_status.SetStatusText( 'error!' )
                    
                    job_status.Finish()
                    
                
                job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
                
                job.start()
                
            
        
    
    def _ManageSubscriptions( self ):
        
        def qt_do_it( subscriptions, missing_query_log_container_names, surplus_query_log_container_names ):
            
            if len( missing_query_log_container_names ) > 0:
                
                text = '{} subscription queries had missing database data! This is a serious error!'.format( HydrusNumbers.ToHumanInt( len( missing_query_log_container_names ) ) )
                text += '\n' * 2
                text += 'If you continue, the client will now create and save empty file/search logs for those queries, essentially resetting them, but if you know you need to exit and fix your database in a different way, cancel out now.'
                text += '\n' * 2
                text += 'If you do not know why this happened, you may have had a hard drive fault. Please consult "install_dir/db/help my db is broke.txt", and you may want to contact hydrus dev.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Missing Query Logs!', yes_label = 'continue', no_label = 'back out' )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    from hydrus.client.importing import ClientImportSubscriptionQuery
                    
                    for missing_query_log_container_name in missing_query_log_container_names:
                        
                        query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( missing_query_log_container_name )
                        
                        CG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                        
                    
                    for subscription in subscriptions:
                        
                        for query_header in subscription.GetQueryHeaders():
                            
                            if query_header.GetQueryLogContainerName() in missing_query_log_container_names:
                                
                                query_header.Reset( query_log_container )
                                
                            
                        
                    
                    CG.client_controller.subscriptions_manager.SetSubscriptions( subscriptions ) # save the reset
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
            if len( surplus_query_log_container_names ) > 0:
                
                text = 'When loading subscription data, the client discovered surplus orphaned subscription data for {} queries! This data is harmless and no longer used. The situation is however unusual, and probably due to an unusual deletion routine or a bug.'.format( HydrusNumbers.ToHumanInt( len( surplus_query_log_container_names ) ) )
                text += '\n' * 2
                text += 'If you continue, this surplus data will backed up to your database directory and then safely deleted from the database itself, but if you recently did manual database editing and know you need to exit and fix your database in a different way, cancel out now.'
                text += '\n' * 2
                text += 'If you do not know why this happened, hydrus dev would be interested in being told about it and the surrounding circumstances.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Orphan Query Logs!', yes_label = 'continue', no_label = 'back out' )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    sub_dir = os.path.join( self._controller.GetDBDir(), 'orphaned_query_log_containers' )
                    
                    HydrusPaths.MakeSureDirectoryExists( sub_dir )
                    
                    for surplus_query_log_container_name in surplus_query_log_container_names:
                        
                        surplus_query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, surplus_query_log_container_name )
                        
                        backup_path = os.path.join( sub_dir, 'qlc_{}.json'.format( surplus_query_log_container_name ) )
                        
                        with open( backup_path, 'w', encoding = 'utf-8' ) as f:
                            
                            f.write( surplus_query_log_container.DumpToString() )
                            
                        
                        CG.client_controller.WriteSynchronous( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, surplus_query_log_container_name )
                        
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
            title = 'manage subscriptions'
            frame_key = 'manage_subscriptions_dialog'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title, frame_key ) as dlg:
                
                panel = ClientGUISubscriptions.EditSubscriptionsPanel( dlg, subscriptions )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    ( subscriptions, edited_query_log_containers, deletee_query_log_container_names ) = panel.GetValue()
                    
                    return ( subscriptions, edited_query_log_containers, deletee_query_log_container_names )
                    
                else:
                    
                    raise HydrusExceptions.CancelledException()
                    
                
            
        
        def THREAD_do_it( controller ):
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusText( 'Waiting for current subscription work to finish.' )
            
            controller.pub( 'message', job_status )
            
            with self._delayed_dialog_lock:
                
                try:
                    
                    try:
                        
                        CG.client_controller.subscriptions_manager.PauseSubscriptionsForEditing()
                        
                        while CG.client_controller.subscriptions_manager.SubscriptionsRunning():
                            
                            time.sleep( 0.1 )
                            
                            if HG.started_shutdown:
                                
                                return
                                
                            
                        
                    finally:
                        
                        job_status.FinishAndDismiss()
                        
                    
                    subscriptions = CG.client_controller.subscriptions_manager.GetSubscriptions()
                    
                    expected_query_log_container_names = set()
                    
                    for subscription in subscriptions:
                        
                        expected_query_log_container_names.update( subscription.GetAllQueryLogContainerNames() )
                        
                    
                    actual_query_log_container_names = set( CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER ) )
                    
                    missing_query_log_container_names = expected_query_log_container_names.difference( actual_query_log_container_names )
                    
                    surplus_query_log_container_names = actual_query_log_container_names.difference( expected_query_log_container_names )
                    
                    try:
                        
                        done_job_status = ClientThreading.JobStatus()
                        
                        ( subscriptions, edited_query_log_containers, deletee_query_log_container_names ) = controller.CallBlockingToQt( self, qt_do_it, subscriptions, missing_query_log_container_names, surplus_query_log_container_names )
                        
                        done_job_status.SetStatusText( 'Saving subscription changes.' )
                        
                        controller.pub( 'message', done_job_status )
                        
                        CG.client_controller.WriteSynchronous(
                        'serialisable_atomic',
                        overwrite_types_and_objs = ( [ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ], subscriptions ),
                        set_objs = edited_query_log_containers,
                        deletee_types_to_names = { HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER : deletee_query_log_container_names }
                        )
                        
                        CG.client_controller.subscriptions_manager.SetSubscriptions( subscriptions )
                        
                    except HydrusExceptions.QtDeadWindowException:
                        
                        pass
                        
                    except HydrusExceptions.CancelledException:
                        
                        CG.client_controller.subscriptions_manager.Wake()
                        
                    finally:
                        
                        done_job_status.FinishAndDismiss()
                        
                    
                finally:
                    
                    CG.client_controller.subscriptions_manager.ResumeSubscriptionsAfterEditing()
                    
                
            
        
        self._controller.CallToThread( THREAD_do_it, self._controller )
        
    
    def _ManageTagDisplay( self ):
        
        title = 'manage tag display and search'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUITagDisplayOptions.EditTagDisplayManagerPanel( dlg, self._controller.tag_display_manager )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                tag_display_manager = panel.GetValue()
                
                tag_display_manager.SetDirty()
                
                self._controller.tag_display_manager = tag_display_manager
                
                self._controller.pub( 'notify_new_tag_display_rules' )
                
            
        
    
    def _ManageTagDisplayApplication( self ):
        
        title = 'manage where tag siblings and parents apply'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = self._controller.Read( 'tag_display_application' )
            
            panel = ClientGUITagDisplayMaintenanceEdit.EditTagDisplayApplication( dlg, master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( edited_master_service_keys_to_sibling_applicable_service_keys, edited_master_service_keys_to_parent_applicable_service_keys ) = panel.GetValue()
                
                self._controller.Write( 'tag_display_application', edited_master_service_keys_to_sibling_applicable_service_keys, edited_master_service_keys_to_parent_applicable_service_keys )
                
            
        
    
    def _ManageTagParents( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, 'manage tag parents' ) as dlg:
            
            panel = ClientGUIManageTagParents.ManageTagParents( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, 'manage tag siblings' ) as dlg:
            
            panel = ClientGUIManageTagSiblings.ManageTagSiblings( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _ManageURLClasses( self ):
        
        title = 'manage url classes'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            domain_manager = self._controller.network_engine.domain_manager
            
            url_classes = domain_manager.GetURLClasses()
            
            panel = ClientGUIURLClass.EditURLClassesPanel( dlg, url_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
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
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                url_class_keys_to_parser_keys = panel.GetValue()
                
                domain_manager.SetURLClassKeysToParserKeys( url_class_keys_to_parser_keys )
                
            
        
    
    def _ManageUPnP( self ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self ) as dlg: dlg.exec()
        
    
    def _MoveMediaFiles( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'move media files' ) as dlg:
            
            panel = ClientGUIScrolledPanelsReview.MoveMediaFilesPanel( dlg, self._controller )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        self._menu_updater_database.update()
        
    
    def _MigrateTags( self ):
        
        default_tag_service_key = self._controller.new_options.GetKey( 'default_tag_service_tab' )
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'migrate tags' )
        
        panel = ClientGUIMigrateTags.MigrateTagsPanel( frame, default_tag_service_key )
        
        frame.SetPanel( panel )
        
    
    def _ModifyAccount( self, service_key ):
        
        service = self._controller.services_manager.GetService( service_key )
        
        try:
            
            account_key_hex = ClientGUIDialogsQuick.EnterText( self, 'Enter the account id for the account to be modified.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        try:
            
            account_key = bytes.fromhex( account_key_hex )
            
        except:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'Could not parse that account id!' )
            
            return
            
        
        subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( account_key = account_key ) ]
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'manage accounts' )
        
        panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, service_key, subject_account_identifiers )
        
        frame.SetPanel( panel )
        
    
    def _OpenDBFolder( self ):
        
        HydrusPaths.LaunchDirectory( self._controller.GetDBDir() )
        
    
    def _OpenExportFolder( self ):
        
        export_path = ClientExportingFiles.GetExportPath()
        
        if export_path is None:
            
            HydrusData.ShowText( 'Unfortunately, your export path could not be determined!' )
            
        else:
            
            HydrusPaths.LaunchDirectory( export_path )
            
        
    
    def _OpenHelp( self ):
        
        ClientGUIDialogsQuick.OpenDocumentation( self, HC.DOCUMENTATION_INDEX )
        
    
    def _OpenInstallFolder( self ):
        
        HydrusPaths.LaunchDirectory( HC.BASE_DIR )
        
    
    def _PausePlaySync( self, sync_type ):
        
        if sync_type == 'repo':
            
            self._controller.new_options.FlipBoolean( 'pause_repo_sync' )
            
            self._controller.pub( 'notify_restart_repo_sync' )
            
        elif sync_type == 'export_folders':
            
            self._controller.new_options.FlipBoolean( 'pause_export_folders_sync' )
            
            self._controller.pub( 'notify_restart_export_folders_daemon' )
            
        elif sync_type == 'import_folders':
            
            self._controller.new_options.FlipBoolean( 'pause_import_folders_sync' )
            
            self._controller.import_folders_manager.Wake()
            
        
        self._controller.Write( 'save_options', HC.options )
        
    
    def _RefreshCurrentPage( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.RefreshQuery()
            
        
    
    def _RefreshStatusBar( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is None:
            
            media_status = ''
            
        else:
            
            media_status = page.GetPrettyStatusForStatusBar()
            
        
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
            
        
        self._statusbar.SetStatusText( media_status, 0 )
        self._statusbar.SetStatusText( idle_status, 2, tooltip = idle_tooltip )
        self._statusbar.SetStatusText( hydrus_busy_status, 3, tooltip = hydrus_busy_tooltip )
        self._statusbar.SetStatusText( busy_status, 4, tooltip = busy_tooltip )
        
        self._RefreshStatusBarDB()
        
    
    def _RefreshStatusBarDB( self ):
        
        ( db_status, job_name ) = CG.client_controller.GetDBStatus()
        
        if job_name is not None and job_name != '':
            
            db_tooltip = 'current db job: {}'.format( job_name )
            
        else:
            
            db_tooltip = None
            
        
        self._statusbar.SetStatusText( db_status, 5, tooltip = db_tooltip )
        
    
    def _RegenerateTagCache( self ):
        
        message = 'This will delete and then recreate the fast search cache for one or all tag services.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless. It fixes missing autocomplete or tag search results.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_tag_cache', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateLocalHashCache( self ):
        
        message = 'This will check and repair any bad rows in the local hashes cache, which keeps a small record of hashes for files on your hard drive. The cache isn\'t super important, but it speeds most operations up, and this routine fixes it when broken/desynced.'
        message += '\n' * 2
        message += 'If you have a lot of files, it can take a minute, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'regenerate_local_hash_cache' )
            
        
    
    def _RegenerateLocalTagCache( self ):
        
        message = 'This will delete and then recreate the local tag cache, which keeps a small record of tags for files on your hard drive. It isn\'t super important, but it speeds most operations up, and this routine fixes it when broken.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'regenerate_local_tag_cache' )
            
        
    
    def _RegenerateTagDisplayMappingsCache( self ):
        
        message = 'This will delete and then recreate the tag \'display\' mappings cache, which is used for user-presented tag searching, loading, and autocomplete counts. This is useful if miscounting (particularly related to siblings/parents) has somehow occurred.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang. All siblings and parents will have to be resynced.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_tag_display_mappings_cache', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateTagDisplayPendingMappingsCache( self ):
        
        message = 'This will delete and then recreate the pending tags on the tag \'display\' mappings cache, which is used for user-presented tag searching, loading, and autocomplete counts. This is useful if you have \'ghost\' pending tags or counts hanging around.'
        message += '\n' * 2
        message += 'If you have a millions of tags, pending or current, it can take a long time, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_tag_display_pending_mappings_cache', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateTagMappingsCache( self ):
        
        message = 'WARNING: Do not run this for no reason! On a large database, this could take hours to finish!'
        message += '\n' * 2
        message += 'This will delete and then recreate the entire tag \'storage\' mappings cache, which is used for tag calculation based on actual values and autocomplete counts in editing contexts like _manage tags_. This is useful if miscounting has somehow occurred.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang. It necessarily involves a regeneration of the tag display mappings cache, which relies on the storage cache, and the tag text search cache. All siblings and parents will have to be resynced.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_tag_mappings_cache', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateTagPendingMappingsCache( self ):
        
        message = 'This will delete and then recreate the pending tags on the whole tag mappings cache, which is used for multiple kinds of tag searching, loading, and autocomplete counts. This is useful if you have \'ghost\' pending tags or counts hanging around.'
        message += '\n' * 2
        message += 'If you have a millions of tags, pending or current, it can take a long time, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_tag_pending_mappings_cache', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateSimilarFilesTree( self ):
        
        message = 'This will delete and then recreate the similar files search tree. This is useful if it has somehow become unbalanced and similar files searches are running slow.'
        message += '\n' * 2
        message += 'If you have a lot of files, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it', check_for_cancelled = True )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'regenerate_similar_files_tree' )
            
        
    
    def _RegenerateTagCacheSearchableSubtagsMaps( self ):
        
        message = 'This will regenerate the fast search cache\'s \'unusual character logic\' lookup map, for one or all tag services.'
        message += '\n' * 2
        message += 'If you have a lot of tags, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless. It fixes missing autocomplete search results.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'regenerate_searchable_subtag_maps', tag_service_key = tag_service_key )
            
        
    
    def _RegenerateTagParentsLookupCache( self ):
        
        message = 'This will delete and then recreate the tag parents lookup cache, which is used for all basic tag parents operations. This is useful if it has become damaged or otherwise desynchronised.'
        message += '\n' * 2
        message += 'It should only take a second or two.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'regenerate_tag_parents_cache' )
            
        
    
    def _RegenerateTagSiblingsLookupCache( self ):
        
        message = 'This will delete and then recreate the tag siblings lookup cache, which is used for all basic tag sibling operations. This is useful if it has become damaged or otherwise desynchronised.'
        message += '\n' * 2
        message += 'It should only take a second or two. It necessarily involves a regeneration of the tag parents lookup cache.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'regenerate_tag_siblings_and_parents_cache' )
            
        
    
    def _ReloadCurrentGUISession( self ):
        
        name = 'temp_session_slot_for_reload_if_you_see_this_you_can_delete_it'
        only_changed_page_data = True
        about_to_save = True
        
        session = self._notebook.GetCurrentGUISession( name, only_changed_page_data, about_to_save )
        
        self._FleshOutSessionWithCleanDataIfNeeded( self._notebook, name, session )
        
        def qt_load():
            
            while self._notebook.count() > 0:
                
                self._notebook.CloseCurrentPage( polite = False )
                
            
            self._notebook.LoadGUISession( name )
            
            self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER, name )
            
            self._controller.pub( 'notify_new_sessions' )
            
            
        
        def do_save():
            
            CG.client_controller.SaveGUISession( session )
            
            CG.client_controller.CallBlockingToQt( self, qt_load )
            
        
        self._controller.CallToThread( do_save )
        
        
    
    def _ReloadIconCache( self ):
        
        CC.global_pixmaps().Reload()
        CC.global_icons().Reload()
        
        HydrusData.ShowText( 'Icon cache reloaded!' )
        
    
    def _RepairInvalidTags( self ):
        
        message = 'This will scan all your tags and repair any that are invalid. This might mean taking out unrenderable characters or cleaning up improper whitespace. If there is a tag collision once cleaned, it may add a (1)-style number on the end.'
        message += '\n' * 2
        message += 'If you have a lot of tags, it can take a long time, during which the gui may hang. If it finds bad tags, you should restart the program once it is complete.'
        message += '\n' * 2
        message += 'If you have not had tag rendering problems, there is no reason to run this.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'repairing invalid tags' )
            
            self._controller.pub( 'message', job_status )
            
            self._controller.Write( 'repair_invalid_tags', job_status = job_status )
            
        
    
    def _RepopulateMappingsTables( self ):
        
        message = 'WARNING: Do not run this for no reason!'
        message += '\n' * 2
        message += 'If you have significant local tags (e.g. \'my tags\') storage, recently had a \'malformed\' client.mappings.db file, and have since gone through clone/repair and now have a truncated file, this routine will attempt to recover missing tags from the smaller tag cache stored in client.caches.db.'
        message += '\n' * 2
        message += 'It can only recover tags for files currently stored by your client. It will take some time, during which the gui may hang. Once it is done, you probably want to regenerate your tag mappings cache, so that you are completely synced again.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'I have a reason to run this, let\'s do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetVariable( 'popup_text_title', 'repopulating mapping tables' )
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.pub( 'modal_message', job_status )
            
            self._controller.Write( 'repopulate_mappings_from_cache', tag_service_key = tag_service_key, job_status = job_status )
            
        
    
    def _RepopulateTagCacheMissingSubtags( self ):
        
        message = 'This will repopulate the fast search cache\'s subtag search, filling in missing entries, for one or all tag services.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless. It fixes missing autocomplete or tag search results.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'repopulate_tag_cache_missing_subtags', tag_service_key = tag_service_key )
            
        
    
    def _RepopulateTagDisplayMappingsCache( self ):
        
        message = 'This will go through your mappings cache and fill in any missing files. It is radically faster than a full regen, and adds siblings and parents instantly, but it only solves the problem of missing file rows.'
        message += '\n' * 2
        message += 'If you have a millions of tags, pending or current, it can take a long time, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'repopulate_tag_display_mappings_cache', tag_service_key = tag_service_key )
            
        
    
    def _RestartServerServices( self, service_key ):
        
        def do_it( service ):
            
            started = HydrusTime.GetNow()
            
            service.Request( HC.POST, 'restart_services' )
            
            HydrusData.ShowText( 'Server service restart started!' )
            
            time_started = HydrusTime.GetNowMS()
            
            working_now = False
            
            while not working_now:
                
                if HG.view_shutdown:
                    
                    return
                    
                
                time.sleep( 5 )
                
                try:
                    
                    result_bytes = service.Request( HC.GET, 'busy' )
                    
                    working_now = True
                    
                except:
                    
                    pass
                    
                
                if HydrusTime.TimeHasPassedMS( time_started + ( 60 * 1000 ) ):
                    
                    HydrusData.ShowText( 'It has been a minute and the server is not back up. Abandoning check--something is super delayed/not working!' )
                    
                    return
                    
                
            
            HydrusData.ShowText( 'Server is back up!' )
            
        
        message = 'This will tell the server to restart its services. If you have swapped in a new ssl cert, this will load that new one.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def _RestoreSplitterPositions( self ):
        
        self._controller.pub( 'set_splitter_positions', HC.options[ 'hpos' ], HC.options[ 'vpos' ] )
        
    
    def _ResyncCombinedDeletedFiles( self ):
        
        message = 'This will resynchronise the "deleted from anywhere" cache to the actual records in the database, ensuring that various tag searches over the deleted files domain give correct counts and file results. It isn\'t super important, but this routine fixes it if it is desynchronised.'
        message += '\n' * 2
        message += 'It should not take all that long, but if you have a lot of deleted files, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'resync_combined_deleted_files', do_full_rebuild = True )
            
        
    
    def _ResyncTagMappingsCacheFiles( self ):
        
        message = 'This will scan your mappings cache for surplus or missing files and correct them. This is useful if you see ghost files or if searches miss files that have the tag.'
        message += '\n' * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang. It should be much faster than the full regen options though!'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it--now choose which service', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            try:
                
                tag_service_key = GetTagServiceKeyForMaintenance( self )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            self._controller.Write( 'resync_tag_mappings_cache_files', tag_service_key = tag_service_key )
            
        
    
    def _STARTReviewAllAccounts( self, service_key ):
        
        admin_service = CG.client_controller.services_manager.GetService( service_key )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'loading accounts' + HC.UNICODE_ELLIPSIS )
        
        self._controller.pub( 'message', job_status )
        
        def work_callable():
            
            response = admin_service.Request( HC.GET, 'all_accounts' )
            
            accounts = response[ 'accounts' ]
            
            return accounts
            
        
        def publish_callable( accounts ):
            
            job_status.FinishAndDismiss()
            
            self._ReviewAllAccounts( service_key, accounts )
            
        
        def errback_callable( etype, value, tb ):
            
            HydrusData.ShowText( 'Sorry, unable to load accounts:' )
            HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
        
        job.start()
        
    
    def _ReviewAllAccounts( self, service_key, accounts ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'all accounts' )
        
        panel = ClientGUIHydrusNetwork.ListAccountsPanel( frame, service_key, accounts )
        
        frame.SetPanel( panel )
        
    
    def _ReviewBandwidth( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review bandwidth use and edit rules' )
        
        panel = ClientGUINetwork.ReviewAllBandwidthPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewDeferredDeleteTableData( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review deferred delete data' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewDeferredDeleteTableData( frame, self._controller )
        
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
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review services', 'review_services' )
        
        panel = ClientGUIClientsideServices.ReviewServicesPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewTagDisplayMaintenance( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'tag display sync' )
        
        panel = ClientGUITagDisplayMaintenanceReview.ReviewTagDisplayMaintenancePanel( frame )
        
        frame.SetPanel( panel )
        
    
    def _ReviewThreads( self ):
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review threads' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewThreads( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _ReviewVacuumData( self ):
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        def work_callable():
            
            vacuum_data = self._controller.Read( 'vacuum_data' )
            
            return vacuum_data
            
        
        def publish_callable( vacuum_data ):
            
            if job_status.IsCancelled():
                
                return
                
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review vacuum data' )
            
            panel = ClientGUIScrolledPanelsReview.ReviewVacuumData( frame, self._controller, vacuum_data )
            
            frame.SetPanel( panel )
            
            job_status.FinishAndDismiss()
            
        
        job_status.SetStatusText( 'loading database data' )
        
        self._controller.pub( 'message', job_status )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _RunExportFolder( self, name = None ):
        
        if self._controller.new_options.GetBoolean( 'pause_export_folders_sync' ):
            
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
            
            client_api_service = CG.client_controller.services_manager.GetService( CC.CLIENT_API_SERVICE_KEY )
            
            port = client_api_service.GetPort()
            
            was_running_before = port is not None
            
            if not was_running_before:
                
                port = 6666
                
                client_api_service._port = port
                
                CG.client_controller.RestartClientServerServices()
                
                time.sleep( 5 )
                
            
            #
            
            api_permissions = ClientAPI.APIPermissions( name = 'hydrus test access', permits_everything = True )
            
            access_key = api_permissions.GetAccessKey()
            
            CG.client_controller.client_api_manager.AddAccess( api_permissions )
            
            #
            
            try:
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusTitle( 'client api test' )
                
                CG.client_controller.pub( 'message', job_status )
                
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
                
                job_status.SetStatusText( 'add url test' )
                
                local_tag_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
                
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
                
                job_status.SetStatusText( 'get session test' )
                
                def get_client_api_page():
                    
                    r = s.get( '{}/manage_pages/get_pages'.format( api_base ) )
                    
                    pages_to_process = [ r.json()[ 'pages' ] ]
                    pages = []
                    
                    while len( pages_to_process ) > 0:
                        
                        page_to_process = pages_to_process.pop()
                        
                        if page_to_process[ 'page_type' ] == ClientGUIPagesCore.PAGE_TYPE_PAGE_OF_PAGES:
                            
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
                        
                        hash_ids_to_hashes_and_tag_info[ item[ 'file_id' ] ] = ( item[ 'hash' ], item[ 'tags' ] )
                        
                    
                    return hash_ids_to_hashes_and_tag_info
                    
                
                hash_ids_to_hashes_and_tag_info = get_hash_ids_to_hashes_and_tag_info()
                
                samus_hash_id = None
                
                for ( hash_id, ( hash_hex, tag_info ) ) in hash_ids_to_hashes_and_tag_info.items():
                    
                    if hash_hex == samus_hash_hex:
                        
                        samus_hash_id = hash_id
                        
                    
                
                if samus_hash_id is None:
                    
                    raise Exception( 'Could not find the samus hash!' )
                    
                
                samus_tag_info = hash_ids_to_hashes_and_tag_info[ samus_hash_id ][1]
                
                if samus_test_tag not in samus_tag_info[ local_tag_service.GetServiceKey().hex() ][ 'storage_tags' ][ str( HC.CONTENT_STATUS_CURRENT ) ]:
                    
                    raise Exception( 'Did not have the tag!' )
                    
                
                #
                
                def qt_session_gubbins():
                    
                    self.ProposeSaveGUISession( CC.LAST_SESSION_SESSION_NAME )
                    
                    page = self._notebook.GetPageFromPageKey( bytes.fromhex( destination_page_key_hex ) )
                    
                    self._notebook.ShowPage( page )
                    
                    self._notebook.CloseCurrentPage()
                    
                    self.ProposeSaveGUISession( CC.LAST_SESSION_SESSION_NAME )
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                    
                    page = self._notebook.NewPageQuery( location_context )
                    
                    return page.GetPageKey()
                    
                
                page_key = CG.client_controller.CallBlockingToQt( CG.client_controller.gui, qt_session_gubbins )
                
                #
                
                request_args = {}
                
                request_args[ 'page_key' ] = page_key.hex()
                request_args[ 'hashes' ] = [ '78f92ba4a786225ee2a1236efa6b7dc81dd729faf4af99f96f3e20bad6d8b538' ]
                
                data = json.dumps( request_args )
                
                r = s.post( '{}/manage_pages/add_files'.format( api_base ), data = data )
                
                time.sleep( 0.25 )
                
                r = s.post( '{}/manage_pages/add_files'.format( api_base ), data = data )
                
                time.sleep( 0.25 )
                
            finally:
                
                #
                
                CG.client_controller.client_api_manager.DeleteAccess( ( access_key, ) )
                
                #
                
                if not was_running_before:
                    
                    client_api_service._port = None
                    
                    CG.client_controller.RestartClientServerServices()
                    
                
                job_status.FinishAndDismiss()
                
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _RunUITest( self ):
        
        def qt_open_pages():
            
            page_of_pages = self._notebook.NewPagesNotebook( on_deepest_notebook = False, select_page = True )
            
            t = 0.25
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self._notebook.NewPageQuery, default_location_context, page_name = 'test', on_deepest_notebook = True )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE_OF_PAGES ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', page_of_pages.NewPageQuery, default_location_context, page_name ='test', on_deepest_notebook = False )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE ) )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProposeSaveGUISession, CC.LAST_SESSION_SESSION_NAME  )
            
            return page_of_pages
            
        
        def qt_close_unclose_one_page():
            
            self._notebook.CloseCurrentPage()
            
            CG.client_controller.CallLaterQtSafe( self, 0.5, 'test job', self._UnclosePage )
            
        
        def qt_close_pages( page_of_pages ):
            
            indices = list( range( page_of_pages.count() ) )
            
            indices.reverse()
            
            t = 0.0
            
            for i in indices:
                
                CG.client_controller.CallLaterQtSafe( self, t, 'test job', page_of_pages._ClosePage, i )
                
                t += 0.25
                
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self._notebook.CloseCurrentPage )
            
            t += 0.25
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.DeleteAllClosedPages )
            
        
        def qt_test_ac():
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            SYS_PRED_REFRESH = 1.0
            
            page = self._notebook.NewPageQuery( default_location_context, page_name = 'test', select_page = True )
            
            t = 0.5
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', page.SetSearchFocus )
            
            ac_widget = page.GetSidebar()._tag_autocomplete._text_ctrl
            
            t += 0.5
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_MEDIA_FOCUS ) )
            
            t += 0.5
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self.ProcessApplicationCommand, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS ) )
            
            t += 0.5
            
            uias = QP.UIActionSimulator()
            
            for c in 'the colour of her hair':
                
                CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, ord( c ), text = c  )
                
                t += 0.01
                
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            t += SYS_PRED_REFRESH
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            t += SYS_PRED_REFRESH
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Down )
            
            t += 0.05
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            t += SYS_PRED_REFRESH
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Down )
            
            t += 0.05
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            t += SYS_PRED_REFRESH
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            for i in range( 20 ):
                
                t += SYS_PRED_REFRESH
                
                for j in range( i + 1 ):
                    
                    CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Down )
                    
                    t += 0.1
                    
                
                CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
                
                t += SYS_PRED_REFRESH
                
                CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, None, QC.Qt.Key.Key_Return )
                
            
            t += 1.0
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Down )
            
            t += 0.05
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', uias.Char, ac_widget, QC.Qt.Key.Key_Return )
            
            t += 1.0
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', self._notebook.CloseCurrentPage )
            
            t += 0.1
            
            CG.client_controller.CallLaterQtSafe( self, t, 'test job', HydrusData.ShowText, 'ui test done' )
            
        
        def do_it():
            
            # pages
            
            page_of_pages = CG.client_controller.CallBlockingToQt( self, qt_open_pages )
            
            time.sleep( 4 )
            
            CG.client_controller.CallBlockingToQt( self, qt_close_unclose_one_page )
            
            time.sleep( 1.5 )
            
            CG.client_controller.CallBlockingToQt( self, qt_close_pages, page_of_pages )
            
            time.sleep( 5 )
            
            del page_of_pages
            
            # a/c
            
            CG.client_controller.CallBlockingToQt( self, qt_test_ac )
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _RunServerTest( self ):
        
        def do_it():
            
            host = '127.0.0.1'
            port = HC.DEFAULT_SERVER_ADMIN_PORT
            
            HydrusData.ShowText( 'Creating admin service' + HC.UNICODE_ELLIPSIS )
            
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
            
            CG.client_controller.CallAfter( self, ClientGUIFrames.ShowKeys, 'access', ( access_key, ) )
            
            #
            
            time.sleep( 5 )
            
            HydrusData.ShowText( 'Creating tag and file services' + HC.UNICODE_ELLIPSIS )
            
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
            
        
        text = 'Woe unto you unless you click "no" NOW.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.CallToThread( do_it )
            
        
    
    def _RunVisualDuplicatesTuningSuite( self ):
        
        text = 'Turn back, do not proceed, click "no" NOW.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        from hydrus.client.files.images import ClientVisualDataTuningSuite
        
        test_dir = QW.QFileDialog.getExistingDirectory( self, '', '' )
        
        if test_dir == '':
            
            return
            
        
        ClientVisualDataTuningSuite.RunTuningSuite( test_dir )
        
    
    def _SaveSplitterPositions( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
            
        
    
    def _ServerMaintenanceRegenServiceInfo( self, service_key: bytes ):
        
        def do_it( service ):
            
            started = HydrusTime.GetNow()
            
            service.Request( HC.POST, 'maintenance_regen_service_info' )
            
            HydrusData.ShowText( 'Maintenance started!' )
            
            time.sleep( 10 )
            
            result_bytes = service.Request( HC.GET, 'busy' )
            
            while result_bytes == b'1':
                
                if HG.started_shutdown:
                    
                    return
                    
                
                time.sleep( 10 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusTime.GetNow() - started
            
            HydrusData.ShowText( 'Server maintenance done in ' + HydrusTime.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to recalculate the cached numbers for number of files, mappings, actionable petitions and so on. It may take a little while to complete, during which time it will not be able to serve any requests.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts. This does not encrypt or truly lock the database files or media folders; it is just a simple check on boot. It will stop noobs from easily booting your client and poking around if you leave your machine unattended.

Do not forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or run from edited source to regain access.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        try:
            
            password = ClientGUIDialogsQuick.EnterText( self, message, allow_blank = True, min_char_width = 36 )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if password == '':
            
            text = 'Clear any existing password?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            password = None
            
        else:
            
            message = 'Please enter it again.'
            
            try:
                
                password_confirmation = ClientGUIDialogsQuick.EnterText( self, message, allow_blank = False, min_char_width = 36 )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if password != password_confirmation:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', 'Those passwords did not match!' )
                
                return
                
            
        
        self._controller.Write( 'set_password', password )
        
    
    def _SetMediaFocus( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetMediaFocus()
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.SetSearchFocus()
            
        
    
    def _SetupBackupPath( self ):
        
        existing_backup_path = self._new_options.GetNoneableString( 'backup_path' )
        
        if existing_backup_path is None:
            
            backup_intro = 'Everything in your client is stored in the \'database\', which consists of a handful of .db files and a single subdirectory that contains all your media files. It is a very good idea to maintain a regular backup schedule--to save from hard drive failure, serious software fault, accidental deletion, or any other unexpected problem. It sucks to lose all your work, so make sure it can\'t happen!'
            backup_intro += '\n' * 2
            backup_intro += 'If you prefer to create a manual backup with an external program like FreeFileSync, then please cancel out of the dialog after this and set up whatever you like, but if you would rather a simple solution, simply select a directory and the client will remember it as the designated backup location. Creating or updating your backup can be triggered at any time from the database menu.'
            backup_intro += '\n' * 2
            backup_intro += 'An ideal backup location is initially empty and on a different hard drive.'
            backup_intro += '\n' * 2
            backup_intro += 'If you have a large database (100,000+ files) or a slow hard drive, creating the initial backup may take a long time--perhaps an hour or more--but updating an existing backup should only take a couple of minutes (since the client only has to copy new or modified files). Try to update your backup every week!'
            backup_intro += '\n' * 2
            backup_intro += 'If you would like some more info on making or restoring backups, please consult the help\'s \'installing and updating\' page.'
            
        else:
            
            backup_intro = 'Your current backup location is "{}".'.format( existing_backup_path )
            backup_intro += '\n' * 2
            backup_intro += 'If your client is getting large and/or complicated, I recommend you start backing up with a proper external program like FreeFileSync. If you would like some more info on making or restoring backups, please consult the help\'s \'installing and updating\' page.'
            
        
        ClientGUIDialogsMessage.ShowInformation( self, backup_intro )
        
        with QP.DirDialog( self, 'Select backup location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = dlg.GetPath()
                
                if path == '':
                    
                    return
                    
                
                if path == self._controller.GetDBDir():
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'That directory is your current database directory! You cannot backup to the same location you are backing up from!' )
                    
                    return
                    
                
                if path == existing_backup_path:
                    
                    ClientGUIDialogsMessage.ShowInformation( self, 'The path you chose is your current saved backup path. No changes have been made.' )
                    
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
                text += '\n' * 2
                text += extra_info
                text += '\n' * 2
                text += 'Are you sure this is the correct directory?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    self._new_options.SetNoneableString( 'backup_path', path )
                    self._new_options.SetNoneableInteger( 'last_backup_time', None )
                    
                    text = 'Would you like to create your backup now?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, text )
                    
                    if result == QW.QDialog.DialogCode.Accepted:
                        
                        self._BackupDatabase()
                        
                    
                    self._menu_updater_database.update()
                    
                
            
        
    
    def _ShowFileHistory( self ):
        
        if not ClientGUICharts.QT_CHARTS_OK:
            
            message = 'Sorry, you do not have QtCharts available, so this chart cannot be shown!'
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
            return
            
        
        self._file_history_updater.update()
        
    
    def _ShowHideSplitters( self ):
        
        page = self._notebook.GetCurrentMediaPage()
        
        if page is not None:
            
            page.ShowHideSplit()
            
        
    
    def _ShowPageWeightInfo( self ):
        
        (
            total_active_page_count,
            total_active_num_hashes,
            total_active_num_seeds,
            total_closed_page_count,
            total_closed_num_hashes,
            total_closed_num_seeds
        ) = self.GetTotalPageCounts()
        
        total_active_num_hashes_weight = ClientGUIPages.ConvertNumHashesToWeight( total_active_num_hashes )
        total_active_num_seeds_weight = ClientGUIPages.ConvertNumSeedsToWeight( total_active_num_seeds )
        
        total_closed_num_hashes_weight = ClientGUIPages.ConvertNumHashesToWeight( total_closed_num_hashes )
        total_closed_num_seeds_weight = ClientGUIPages.ConvertNumSeedsToWeight( total_closed_num_seeds )
        
        message = 'Session weight is a simple representation of your pages combined memory and CPU load. A file counts as 1, and a URL counts as 20.'
        message += '\n' * 2
        message += 'Try to keep the total below 10 million! It is also generally better to spread it around--have five download pages each of 500k weight rather than one page with 2.5M.'
        message += '\n' * 2
        message += 'Your {} open pages\' total is: {}'.format( total_active_page_count, HydrusNumbers.ToHumanInt( total_active_num_hashes_weight + total_active_num_seeds_weight ) )
        message += '\n' * 2
        message += 'Specifically, your file weight is {} and URL weight is {}.'.format( HydrusNumbers.ToHumanInt( total_active_num_hashes_weight ), HydrusNumbers.ToHumanInt( total_active_num_seeds_weight ) )
        message += '\n' * 2
        message += 'For extra info, your {} closed pages (in the undo list) have total weight {}, being file weight {} and URL weight {}.'.format(
            total_closed_page_count,
            HydrusNumbers.ToHumanInt( total_closed_num_hashes_weight + total_closed_num_seeds_weight ),
            HydrusNumbers.ToHumanInt( total_closed_num_hashes_weight ),
            HydrusNumbers.ToHumanInt( total_closed_num_seeds_weight )
        )
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _SwitchBoolean( self, name ):
        
        if name == 'autocomplete_delay_mode':
            
            HG.autocomplete_delay_mode = not HG.autocomplete_delay_mode
            
        elif name == 'blurhash_mode':
            
            HG.blurhash_mode = not HG.blurhash_mode
            
            self._controller.pub( 'clear_thumbnail_cache' )
            
        elif name == 'cache_report_mode':
            
            HG.cache_report_mode = not HG.cache_report_mode
            
        elif name == 'callto_report_mode':
            
            HG.callto_report_mode = not HG.callto_report_mode
            
        elif name == 'canvas_tile_outline_mode':
            
            HG.canvas_tile_outline_mode = not HG.canvas_tile_outline_mode
            
        elif name == 'daemon_report_mode':
            
            HG.daemon_report_mode = not HG.daemon_report_mode
            
        elif name == 'db_report_mode':
            
            HG.db_report_mode = not HG.db_report_mode
            
        elif name == 'db_ui_hang_relief_mode':
            
            HG.db_ui_hang_relief_mode = not HG.db_ui_hang_relief_mode
            
        elif name == 'fake_petition_mode':
            
            HG.fake_petition_mode = not HG.fake_petition_mode
            
        elif name == 'file_import_report_mode':
            
            HG.file_import_report_mode = not HG.file_import_report_mode
            
        elif name == 'file_report_mode':
            
            HG.file_report_mode = not HG.file_report_mode
            
        elif name == 'file_sort_report_mode':
            
            HG.file_sort_report_mode = not HG.file_sort_report_mode
            
        elif name == 'gui_report_mode':
            
            HG.gui_report_mode = not HG.gui_report_mode
            
        elif name == 'hover_window_report_mode':
            
            HG.hover_window_report_mode = not HG.hover_window_report_mode
            
        elif name == 'media_load_report_mode':
            
            HG.media_load_report_mode = not HG.media_load_report_mode
            
        elif name == 'mpv_report_mode':
            
            HG.mpv_report_mode = not HG.mpv_report_mode
            
            level = 'debug' if HG.mpv_report_mode else 'fatal'
            
            self._controller.pub( 'set_mpv_log_level', level )
            
        elif name == 'network_report_mode':
            
            HG.network_report_mode = not HG.network_report_mode
            HG.network_report_mode_silent = False
            
        elif name == 'network_report_mode_silent':
            
            HG.network_report_mode = not HG.network_report_mode
            HG.network_report_mode_silent = True
            
        elif name == 'phash_generation_report_mode':
            
            HG.phash_generation_report_mode = not HG.phash_generation_report_mode
            
        elif name == 'pubsub_report_mode':
            
            HG.pubsub_report_mode = not HG.pubsub_report_mode
            
        elif name == 'shortcut_report_mode':
            
            HG.shortcut_report_mode = not HG.shortcut_report_mode
            
        elif name == 'subprocess_report_mode':
            
            HG.subprocess_report_mode = not HG.subprocess_report_mode
            
        elif name == 'subscription_report_mode':
            
            HG.subscription_report_mode = not HG.subscription_report_mode
            
        elif name == 'thumbnail_debug_mode':
            
            HG.thumbnail_debug_mode = not HG.thumbnail_debug_mode
            
        elif name == 'force_idle_mode':
            
            HG.force_idle_mode = not HG.force_idle_mode
            
            self._controller.pub( 'wake_idle_workers' )
            self.SetStatusBarDirty()
            
        
    
    def _SyncTagDisplayMaintenanceNow( self ):
        
        def do_it():
            
            # this guy can block for db access, so do it off Qt
            there_was_work_to_do = CG.client_controller.tag_display_maintenance_manager.SyncFasterNow()
            
            if not there_was_work_to_do:
                
                HydrusData.ShowText( 'Seems like we are all synced already!' )
                
            
        
        self._controller.CallToThread( do_it )
        
    
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
        
        self._menu_updater_undo.update()
        
        self._controller.pub( 'notify_new_pages' )
        
    
    def _UpdateMenuPagesCount( self ):
        
        (
            total_active_page_count,
            total_active_num_hashes,
            total_active_num_seeds,
            total_closed_page_count,
            total_closed_num_hashes,
            total_closed_num_seeds
        ) = self.GetTotalPageCounts()
        
        total_active_weight = ClientGUIPages.ConvertNumHashesAndSeedsToWeight( total_active_num_hashes, total_active_num_seeds )
        
        if total_active_weight > 10000000 and self._controller.new_options.GetBoolean( 'show_session_size_warnings' ) and not self._have_shown_session_size_warning:
            
            self._have_shown_session_size_warning = True
            
            HydrusData.ShowText( 'Your session weight is {}, which is pretty big! To keep your UI lag-free, please try to close some pages or clear some finished downloaders!'.format( HydrusNumbers.ToHumanInt( total_active_weight ) ) )
            
        
        ClientGUIMenus.SetMenuItemLabel( self._menubar_pages_page_count, '{} pages open'.format( HydrusNumbers.ToHumanInt( total_active_page_count ) ) )
        
        ClientGUIMenus.SetMenuItemLabel( self._menubar_pages_session_weight, 'total session weight: {}'.format( HydrusNumbers.ToHumanInt( total_active_weight ) ) )
        
    
    def _UpdateMenuPagesHistory( self ):
        
        self._page_nav_history_menu.clear()
        
        low_page = self._notebook.GetCurrentMediaPage()
        
        self.RefreshPageHistoryMenuClean()
        
        if low_page is not None:
            
            self._page_nav_history.AddPage( low_page )
            
        
        for i, ( page_key, page_name ) in enumerate( reversed( self._page_nav_history.GetHistory() ) ):
            
            if i > 99: #let's set a maximum size of history to be displayed in the menu
                
                break
                
            
            history_menuitem = ClientGUIMenus.AppendMenuItem( self._page_nav_history_menu, '{}: {}'.format( i + 1, page_name ), 'Activate this tab from your viewing history.', CG.client_controller.gui.ShowPage, page_key )
            
            if i == 0:
                
                font = history_menuitem.font()
                font.setBold( True )
                history_menuitem.setFont( font )
                
            
        
    
    
    def _UpdateSystemTrayIcon( self, currently_booting = False ):
        
        if not ClientGUISystemTray.SystemTrayAvailable() or ( not (HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS ) and not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) ):
            
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
                self._system_tray_icon.flip_minimise_ui.connect( self._FlipMinimiseRestore )
                self._system_tray_icon.exit_client.connect( self.TryToExit )
                self._system_tray_icon.flip_pause_network_jobs.connect( self.FlipNetworkTrafficPaused )
                self._system_tray_icon.flip_pause_subscription_jobs.connect( self.FlipSubscriptionsPaused )
                
                self._have_system_tray_icon = True
                
            
            self._system_tray_icon.show()
            
            self._system_tray_icon.SetShouldAlwaysShow( always_show_system_tray_icon )
            self._system_tray_icon.SetUIIsCurrentlyShown( not self._currently_minimised_to_system_tray )
            self._system_tray_icon.SetUIIsCurrentlyMinimised( self.isMinimized() )
            self._system_tray_icon.SetNetworkTrafficPaused( new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
            self._system_tray_icon.SetSubscriptionsPaused( new_options.GetBoolean( 'pause_subs_sync' ) )
            
        else:
            
            if self._have_system_tray_icon:
                
                self._system_tray_icon.deleteLater()
                
                self._system_tray_icon = None
                
                self._have_system_tray_icon = False
                
            
        
    
    def _VacuumDatabase( self ):
        
        text = 'This will rebuild the database, rewriting all indices and tables to be contiguous and optimising most operations. It also truncates the database files, recovering unused space back to your hard drive. It typically happens automatically every few months, but you can force it here.'
        text += '\n' * 2
        text += 'If you have no reason to run this, it is usually pointless. If you have a very large database on an HDD instead of an SSD, it may take upwards of an hour, during which your gui may hang. A popup message will show its status.'
        text += '\n' * 2
        text += 'A \'soft\' vacuum will only reanalyze those databases that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        text += '\n' * 2
        text += 'A \'full\' vacuum will immediately force a vacuum for the entire database. This can take substantially longer.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Choose how thorough your vacuum will be.', yes_label = 'soft', no_label = 'full', check_for_cancelled = True )
        
        if was_cancelled:
            
            return
            
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED )
            
        elif result == QW.QDialog.DialogCode.Rejected:
            
            self._controller.Write( 'vacuum', maintenance_mode = HC.MAINTENANCE_FORCED, force_vacuum = True )
            
        
    
    def _VacuumServer( self, service_key ):
        
        def do_it( service ):
            
            started = HydrusTime.GetNow()
            
            service.Request( HC.POST, 'vacuum' )
            
            HydrusData.ShowText( 'Server vacuum started!' )
            
            result_bytes = b'1'
            
            while result_bytes == b'1':
                
                if HG.view_shutdown:
                    
                    return
                    
                
                time.sleep( 5 )
                
                result_bytes = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusTime.GetNow() - started
            
            HydrusData.ShowText( 'Server vacuum done in ' + HydrusTime.TimeDeltaToPrettyTimeDelta( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and vacuum its database files. It may take some time to complete, during which time it will not be able to serve any requests.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            service = self._controller.services_manager.GetService( service_key )
            
            self._controller.CallToThread( do_it, service )
            
        
    
    def AddModalMessage( self, job_status: ClientThreading.JobStatus ):
        
        if job_status.IsDismissed():
            
            return
            
        
        if job_status.IsDone():
            
            self._controller.pub( 'message', job_status )
            
            return
            
        
        dialog_is_open = ClientGUIFunctions.DialogIsOpen()
        
        if self._CurrentlyMinimisedOrHidden() or dialog_is_open or not ClientGUIFunctions.TLWOrChildIsActive( self ):
            
            self._pending_modal_job_statuses.add( job_status )
            
        else:
            
            CG.client_controller.pub( 'pause_all_media' )
            
            title = job_status.GetStatusTitle()
            
            if title is None:
                
                title = 'important job'
                
            
            hide_close_button = not job_status.IsCancellable()
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title, hide_buttons = hide_close_button, do_not_activate = True ) as dlg:
                
                panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_status )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def AskToDeleteAllClosedPages( self ):
        
        message = 'Clear the {} closed pages?'.format( HydrusNumbers.ToHumanInt( len( self._closed_pages ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self.DeleteAllClosedPages()
            
        
    
    def AutoSaveLastSession( self ):
        
        only_save_last_session_during_idle = self._controller.new_options.GetBoolean( 'only_save_last_session_during_idle' )
        
        if only_save_last_session_during_idle and not self._controller.CurrentlyIdle():
            
            self._controller.CallLaterQtSafe( self, 60, 'auto session save wait loop', self.AutoSaveLastSession )
            
        else:
            
            if HC.options[ 'default_gui_session' ] == CC.LAST_SESSION_SESSION_NAME:
                
                only_changed_page_data = True
                about_to_save = True
                
                session = self._notebook.GetCurrentGUISession( CC.LAST_SESSION_SESSION_NAME, only_changed_page_data, about_to_save )
                
                session = self._FleshOutSessionWithCleanDataIfNeeded( self._notebook, CC.LAST_SESSION_SESSION_NAME, session )
                
                callable = self.AutoSaveLastSession
                
                last_session_save_period_minutes = self._controller.new_options.GetInteger( 'last_session_save_period_minutes' )
                
                next_call_delay = last_session_save_period_minutes * 60
                
                def do_it( controller, session, win, next_call_delay, callable ):
                    
                    controller.SaveGUISession( session )
                    
                    controller.CallLaterQtSafe( win, next_call_delay, 'auto save session', callable )
                    
                
                self._controller.CallToThread( do_it, self._controller, session, self, next_call_delay, callable )
                
            
        
    
    def closeEvent( self, event ):
        
        try:
            
            if ClientGUISystemTray.SystemTrayAvailable() and self._controller.new_options.GetBoolean( 'close_client_to_system_tray' ):
                
                self._FlipShowHideWholeUI()
                
                return
                
            
            self.TryToExit()
            
        finally:
            
            event.ignore() # we always ignore, as we'll close through the window through other means
            
        
    
    def CreateNewSubscriptionGapDownloader( self, gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit ):
        
        page = self._notebook.GetOrMakeGalleryDownloaderPage( desired_page_name = 'subscription gap downloaders', select_page = True )
        
        if page is None:
            
            HydrusData.ShowText( 'Sorry, could not create the downloader page! Is your session super full atm?' )
            
        
        panel = page.GetSidebar()
        
        panel.PendSubscriptionGapDownloader( gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit )
        
        self._notebook.ShowPage( page )
        
    
    def DeleteAllClosedPages( self ):
        
        deletee_pages = [ page for ( time_closed, page ) in self._closed_pages ]
        
        self._closed_pages = []
        
        if len( deletee_pages ) > 0:
            
            self._DestroyPages( deletee_pages )
            
            self._menu_updater_undo.update()
            
        
    
    def DeleteOldClosedPages( self ):
        
        new_closed_pages = []
        
        now = HydrusTime.GetNow()
        
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
            
            self._menu_updater_undo.update()
            
        
        self._DestroyPages( deletee_pages )
        
    
    def DoFileStorageRebalance( self, job_status: ClientThreading.JobStatus ):
        
        self._controller.CallToThread( self._controller.client_files_manager.Rebalance, job_status )
        
        job_status.SetStatusTitle( 'rebalancing files' )
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( None, 'migrating files' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_status, hide_main_gui = True )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        self._MoveMediaFiles()
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if watched == self:
                
                if event.type() == QC.QEvent.Type.WindowStateChange:
                    
                    event = typing.cast( QG.QWindowStateChangeEvent, event )
                    
                    was_minimised = event.oldState() == QC.Qt.WindowState.WindowMinimized
                    is_minimised = self.isMinimized()
                    
                    if was_minimised != is_minimised:
                        
                        if self._have_system_tray_icon:
                            
                            self._system_tray_icon.SetUIIsCurrentlyMinimised( is_minimised )
                            
                        
                        if is_minimised:
                            
                            self._was_maximised = event.oldState() == QC.Qt.WindowState.WindowMaximized
                            
                            if ClientGUISystemTray.SystemTrayAvailable() and not self._currently_minimised_to_system_tray and self._controller.new_options.GetBoolean( 'minimise_client_to_system_tray' ):
                                
                                self._FlipShowHideWholeUI()
                                
                                return True
                                
                            
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
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
                    
                
                try:
                    
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
        
        if not self._new_options.GetBoolean( 'override_stylesheet_colours' ):
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Hey, this command comes from an old colour system. If you want to change to darkmode, try _options->style_ instead. Or, if you know what you are doing, make sure you flip the "override" checkbox in _options->colours_ and then try this again.' )
            
        
        current_colourset = self._new_options.GetString( 'current_colourset' )
        
        if current_colourset == 'darkmode':
            
            new_colourset = 'default'
            
        elif current_colourset == 'default':
            
            new_colourset = 'darkmode'
            
        
        self._new_options.SetString( 'current_colourset', new_colourset )
        
        CG.client_controller.pub( 'notify_new_colourset' )
        
    
    def FlipNetworkTrafficPaused( self ):
        
        self._controller.network_engine.PausePlayNewJobs()
        
        self._UpdateSystemTrayIcon()
        
        self._menu_updater_network.update()
        
    
    def FlipProfileMode( self, name ):
        
        HydrusProfiling.FlipProfileMode( name )
        
        self._profile_mode_client_api_menu_item.setChecked( HydrusProfiling.IsProfileMode( 'client_api' ) )
        self._profile_mode_db_menu_item.setChecked( HydrusProfiling.IsProfileMode( 'db' ) )
        self._profile_mode_threads_menu_item.setChecked( HydrusProfiling.IsProfileMode( 'threads' ) )
        self._profile_mode_ui_menu_item.setChecked( HydrusProfiling.IsProfileMode( 'ui' ) )
        
    
    def FlipSubscriptionsPaused( self ):
        
        self._controller.new_options.FlipBoolean( 'pause_subs_sync' )
        
        self._controller.subscriptions_manager.Wake()
        
        self._controller.Write( 'save_options', HC.options )
        
        self._UpdateSystemTrayIcon()
        
        self._menu_updater_network.update()
        
    
    def ForgetPending( self, service_key ):
        
        service_name = self._controller.services_manager.GetName( service_key )
        
        message = 'Are you sure you want to delete the pending data for {}?'.format( service_name )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.Write( 'delete_pending', service_key )
            
        
    
    def GetCurrentPage( self ):
        
        return self._notebook.GetCurrentMediaPage()
        
    
    def GetCurrentSessionPageAPIInfoDict( self ):
        
        return self._notebook.GetSessionAPIInfoDict( is_selected = True )
        
    
    def GetMPVWidget( self, parent ):
        
        if len( self._persistent_mpv_widgets ) == 0:
            
            mpv_widget = ClientGUIMPV.MPVWidget( parent )
            
            self._persistent_mpv_widgets.append( mpv_widget )
            
        
        mpv_widget = self._persistent_mpv_widgets.pop()
        
        if mpv_widget.parentWidget() is self:
            
            mpv_widget.setParent( parent )
            
        
        return mpv_widget
        
    
    def GetPageFromPageKey( self, page_key ):
        
        return self._notebook.GetPageFromPageKey( page_key )
        
    
    def GetPageAPIInfoDict( self, page_key, simple ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            return None
            
        else:
            
            return page.GetAPIInfoDict( simple )
            
        
    
    def GetTotalPageCounts( self ):
        
        total_active_page_count = self._notebook.GetNumPagesHeld()
        
        total_closed_page_count = len( self._closed_pages )
        
        ( total_active_num_hashes, total_active_num_seeds ) = self._notebook.GetTotalNumHashesAndSeeds()
        
        total_closed_num_hashes = 0
        total_closed_num_seeds = 0
        
        for ( time_closed, page ) in self._closed_pages:
            
            ( num_hashes, num_seeds ) = page.GetTotalNumHashesAndSeeds()
            
            total_closed_num_hashes += num_hashes
            total_closed_num_seeds += num_seeds
            
        
        return (
            total_active_page_count,
            total_active_num_hashes,
            total_active_num_seeds,
            total_closed_page_count,
            total_closed_num_hashes,
            total_closed_num_seeds
        )
        
    
    def HideToSystemTray( self ):
        
        shown = not self._currently_minimised_to_system_tray
        
        windows_or_advanced_mode = HC.PLATFORM_WINDOWS or CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
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
        
    
    def ImportURLFromAPI( self, url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page, destination_location_context ):
        
        try:
            
            ( normalised_url, result_text ) = self._ImportURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags, destination_page_name = destination_page_name, destination_page_key = destination_page_key, show_destination_page = show_destination_page, destination_location_context = destination_location_context )
            
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
            
            show_destination_page = CG.client_controller.new_options.GetBoolean( 'show_destination_page_when_dnd_url' )
            
            self._ImportURL( url, show_destination_page = show_destination_page )
            
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
            
        
    
    def IsCurrentlyUploadingPending( self, service_key ):
        
        return service_key in self._currently_uploading_pending
        
    
    def MaintainCanvasFrameReferences( self ):
        
        self._canvas_frames = [ frame for frame in self._canvas_frames if QP.isValid( frame ) ]
        
    
    def MaintainMemory( self ):
        
        self._menu_updater_database.update()
        
    
    def NewPageDuplicates(
        self,
        location_context: ClientLocation.LocationContext,
        initial_predicates = None,
        page_name = None,
        select_page = True,
        activate_window = False
    ):
        
        self._notebook.NewPageDuplicateFilter(
            location_context,
            initial_predicates = initial_predicates,
            page_name = page_name,
            on_deepest_notebook = True,
            select_page = select_page
        )
        
        if activate_window and not self.isActiveWindow():
            
            self.activateWindow()
            
        
    
    def NewPageImportHDD( self, paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success ):
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportHDD( paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success )
        
        self._notebook.NewPage( page_manager, on_deepest_notebook = True )
        
    
    def NewPageQuery(
        self,
        location_context: ClientLocation.LocationContext,
        initial_hashes = None,
        initial_predicates = None,
        initial_sort = None,
        initial_collect = None,
        page_name = None,
        do_sort = False,
        select_page = True,
        activate_window = False
    ):
        
        self._notebook.NewPageQuery(
            location_context,
            initial_hashes = initial_hashes,
            initial_predicates = initial_predicates,
            initial_sort = initial_sort,
            initial_collect = initial_collect,
            page_name = page_name,
            on_deepest_notebook = True,
            do_sort = do_sort,
            select_page = select_page
        )
        
        if activate_window and not self.isActiveWindow():
            
            self.activateWindow()
            
        
    
    def NotifyAdvancedMode( self ):
        
        self._menu_updater_network.update()
        self._menu_updater_file.update()
        
    
    def NotifyClosedPage( self, page ):
        
        if self._clipboard_watcher_destination_page_urls == page:
            
            self._clipboard_watcher_destination_page_urls = None
            
        
        if self._clipboard_watcher_destination_page_watcher == page:
            
            self._clipboard_watcher_destination_page_watcher = None
            
        
        close_time = HydrusTime.GetNow()
        
        self._closed_pages.append( ( close_time, page ) )
        
        self._controller.ClosePageKeys( page.GetPageKeys() )
        
        self._menu_updater_pages_history.Update()
        self._menu_updater_pages.update()
        self._menu_updater_undo.update()
        
    
    def NotifyDeletedPage( self, page ):
        
        self._DestroyPages( ( page, ) )
        
        self._menu_updater_pages.update()
        
    
    def NotifyMediaViewerExiting( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'activate_main_gui_on_viewer_close' ):
            
            self.activateWindow()
            
        
    
    def NotifyNewExportFolders( self ):
        
        self._menu_updater_file.update()
        
    
    def NotifyNewImportFolders( self ):
        
        self._menu_updater_file.update()
        
    
    def NotifyNewOptions( self ):
        
        self._menu_updater_database.update()
        self._menu_updater_services.update()
        self._menu_updater_tags.update()
        
    
    def NotifyNewPages( self ):
        
        self._menu_updater_pages.update()
        
    
    def NotifyNewPagesCount( self ):
        
        self._menu_updater_pages_count.Update()
        
    
    def NotifyNewPending( self ):
        
        self._menu_updater_pending.update()
        
    
    def NotifyNewPermissions( self ):
        
        self._menu_updater_pages.update()
        self._menu_updater_services.update()
        
    
    def NotifyNewServices( self ):
        
        self._menu_updater_pages.update()
        self._menu_updater_services.update()
        
    
    def NotifyNewSessions( self ):
        
        self._menu_updater_pages.update()
        
    
    def NotifyNewUndo( self ):
        
        self._menu_updater_undo.update()
        
    
    def NotifyPendingUploadFinished( self, service_key: bytes ):
        
        self._currently_uploading_pending.discard( service_key )
        
        self._menu_updater_pending.update()
        
    
    def NotifyRefreshNetworkMenu( self ):
        
        self._menu_updater_network.update()
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        self._notebook.PresentImportedFilesToPage( hashes, page_name )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
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
                
                self._RefreshCurrentPage()
                
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
                
            elif action == CAC.SIMPLE_GLOBAL_PROFILE_MODE_FLIP:
                
                self.FlipProfileMode( 'db' )
                
            elif action == CAC.SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW:
                
                CG.client_controller.new_options.FlipBoolean( 'force_animation_scanbar_show' )
                
            elif action == CAC.SIMPLE_OPEN_COMMAND_PALETTE:
                
                self._locator_widget.start()
                
            elif action == CAC.SIMPLE_RELOAD_CURRENT_STYLESHEET:
                
                ClientGUIStyle.ReloadStyleSheet()
                
            elif action == CAC.SIMPLE_SHOW_HIDE_SPLITTERS:
                
                self._ShowHideSplitters()
                
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
                
            elif action == CAC.SIMPLE_OPEN_OPTIONS:
                
                self._ManageOptions()
                
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
                
                try:
                    
                    message = 'Enter a name for the new session.'
                    
                    name = ClientGUIDialogsQuick.EnterText( self, message, default = suggested_name )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                if name in ClientGUISession.RESERVED_SESSION_NAMES:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, you cannot have that name! Try another.' )
                    
                else:
                    
                    existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
                    
                    if name in existing_session_names:
                        
                        message = 'Session "{}" already exists! Do you want to overwrite it?'.format( name )
                        
                        ( result, closed_by_user ) = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no, choose another name', check_for_cancelled = True )
                        
                        if closed_by_user:
                            
                            return
                            
                        elif result == QW.QDialog.DialogCode.Rejected:
                            
                            continue
                            
                        
                    
                    break
                    
                
            
        elif name not in ClientGUISession.RESERVED_SESSION_NAMES: # i.e. a human asked to do this
            
            message = 'Overwrite "{}" session?'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        #
        
        only_changed_page_data = True
        about_to_save = True
        
        session = notebook.GetCurrentGUISession( name, only_changed_page_data, about_to_save )
        
        self._FleshOutSessionWithCleanDataIfNeeded( notebook, name, session )
        
        self._controller.CallToThread( self._controller.SaveGUISession, session )
        
    
    def RedownloadURLsForceFetch( self, urls ):
        
        if len( urls ) == 0:
            
            return
            
        
        urls = sorted( urls )
        
        tag_import_options = CG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( None, urls[0] )
        
        tag_import_options = tag_import_options.Duplicate()
        
        tag_import_options.SetShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( True )
        tag_import_options.SetShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( True )
        
        page = self._notebook.GetOrMakeURLImportPage( desired_page_name = 'forced urls downloader', destination_tag_import_options = tag_import_options )
        
        sidebar = page.GetSidebar()
        
        for url in urls:
            
            sidebar.PendURL( url )
            
        
    
    def RefreshPage( self, page_key: bytes ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            raise HydrusExceptions.DataMissing( 'Could not find that page!' )
            
        
        page.RefreshQuery()
        
    
    def RefreshPageHistoryMenu( self ):
        
        self._menu_updater_pages_history.Update()
        
    
    def RefreshPageHistoryMenuClean( self ):
        
        open_pages = self._notebook.GetPageKeys()
        
        self._page_nav_history.CleanPages( open_pages )
        
    
    def RefreshStatusBar( self ):
        
        self._RefreshStatusBar()
        
    
    def RefreshStatusBarDB( self ):
        
        self._RefreshStatusBarDB()
        
    
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
            
            self._ui_update_repeating_job = self._controller.CallRepeatingQtSafe( self, 0.0, 0.1, 'repeating ui update', self.REPEATINGUIUpdate )
            
        
    
    def ReleaseMPVWidget( self, mpv_widget ):
        
        mpv_widget.setParent( self )
        
        self._persistent_mpv_widgets.append( mpv_widget )
        
    
    def _UnloadAndPurgeQtMediaplayer( self, qt_media_player: ClientGUICanvasMedia.QtMediaPlayer ):
        
        if qt_media_player.IsCompletelyUnloaded():
            
            qt_media_player.deleteLater()
            
        else:
            
            qt_media_player.TryToUnload()
            
            self._controller.CallLaterQtSafe( self, 5.0, 'purge QMediaPlayer', self._UnloadAndPurgeQtMediaplayer, qt_media_player )
            
        
    
    def ReleaseQtMediaPlayer( self, qt_media_player: ClientGUICanvasMedia.QtMediaPlayer ):
        
        if qt_media_player.parentWidget() != self:
            
            qt_media_player.setParent( self )
            
        
        self._controller.CallLaterQtSafe( self, 5.0, 'start QMediaPlayer purge', self._UnloadAndPurgeQtMediaplayer, qt_media_player )
        
    
    def REPEATINGBandwidth( self ):
        
        if self._currently_minimised_to_system_tray:
            
            return
            
        
        global_tracker = self._controller.network_engine.bandwidth_manager.GetMySessionTracker()
        
        boot_time_ms = self._controller.GetBootTimestampMS()
        
        time_since_boot_ms = max( 1000, HydrusTime.GetNowMS() - boot_time_ms )
        
        usage_since_boot = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, HydrusTime.SecondiseMS( time_since_boot_ms ) )
        
        bandwidth_status = HydrusData.ToHumanBytes( usage_since_boot )
        
        current_usage = global_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        if current_usage > 0:
            
            bandwidth_status += ' (' + HydrusData.ToHumanBytes( current_usage ) + '/s)'
            
        
        if self._controller.new_options.GetBoolean( 'pause_subs_sync' ):
            
            bandwidth_status += ', subs paused'
            
        
        if self._controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ):
            
            bandwidth_status += ', network paused'
            
        
        tooltip = 'total bandwidth used this session, and current use'
        
        self._statusbar.SetStatusText( bandwidth_status, 1, tooltip = tooltip )
        
    
    def REPEATINGClipboardWatcher( self ):
        
        allow_watchers = self._controller.new_options.GetBoolean( 'watch_clipboard_for_watcher_urls' )
        allow_other_recognised_urls = self._controller.new_options.GetBoolean( 'watch_clipboard_for_other_recognised_urls' )
        
        if not ( allow_watchers or allow_other_recognised_urls ):
            
            self._BootOrStopClipboardWatcherIfNeeded()
            
            return
            
        
        try:
            
            text = CG.client_controller.GetClipboardText()
            
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
        
        if self._currently_minimised_to_system_tray:
            
            return
            
        
        page = self.GetCurrentPage()
        
        if page is not None:
            
            page.REPEATINGPageUpdate()
            
        
        if len( self._pending_modal_job_statuses ) > 0:
            
            # another safety thing. normally modal lads are shown immediately, no problem, but sometimes they can be delayed
            job_status = self._pending_modal_job_statuses.pop()
            
            self._controller.pub( 'modal_message', job_status )
            
        
    
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
                
            
            try:
                
                window.TIMERUIUpdate()
                
            except Exception as e:
                
                self._ui_update_windows.discard( window )
                
                HydrusData.ShowException( e )
                
            
        
        if len( self._ui_update_windows ) == 0:
            
            self._ui_update_repeating_job.Cancel()
            
            self._ui_update_repeating_job = None
            
        
    
    def ReportFreshSessionLoaded( self, gui_session: ClientGUISession.GUISessionContainer ):
        
        if not self._first_session_loaded:
            
            self._first_session_loaded = True
            
            self._controller.ReportFirstSessionInitialised()
            
        
        if gui_session.GetName() == CC.LAST_SESSION_SESSION_NAME:
            
            self._controller.ReportLastSessionLoaded( gui_session )
            
        
    
    def ReplaceMenu( self, name, menu_or_none, label ):
        
        # this is now way more complicated than I generally need, but I'll hang on to it for the moment
        
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
            
        
    
    def SaveAndHide( self ):
        
        if self._done_save_and_hide:
            
            return
            
        
        CG.client_controller.pub( 'pause_all_media' )
        
        try:
            
            if self._have_system_tray_icon:
                
                self._system_tray_icon.hide()
                
            
            if QP.isValid( self._message_manager ):
                
                self._message_manager.CleanBeforeDestroy()
                
            
            #
            
            if self._have_shown_once:
                
                if self._new_options.GetBoolean( 'saving_sash_positions_on_exit' ):
                    
                    self._SaveSplitterPositions()
                    
                
                ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
                
            
            for tlw in QW.QApplication.topLevelWidgets():
                
                if not isinstance( tlw, ClientGUISplash.FrameSplash ):
                    
                    tlw.hide()
                    
                
            
            #
            
            if self._first_session_loaded:
                
                only_changed_page_data = True
                about_to_save = True
                
                session = self._notebook.GetCurrentGUISession( CC.LAST_SESSION_SESSION_NAME, only_changed_page_data, about_to_save )
                
                session = self._FleshOutSessionWithCleanDataIfNeeded( self._notebook, CC.LAST_SESSION_SESSION_NAME, session )
                
                self._controller.SaveGUISession( session )
                
                session.SetName( CC.EXIT_SESSION_SESSION_NAME )
                
                self._controller.SaveGUISession( session )
                
            
            #
            
            self._DestroyTimers()
            
            self.DeleteAllClosedPages()
            
            self._notebook.CleanBeforeDestroy()
            
            self._controller.WriteSynchronous( 'save_options', HC.options )
            
            self._controller.WriteSynchronous( 'serialisable', self._new_options )
            
            self._done_save_and_hide = True
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
        
    
    def SetMediaFocus( self ):
        
        self._SetMediaFocus()
        
    
    def SetStatusBarDirty( self ):
        
        self._statusbar_thread_updater.Update()
        
    
    def SetStatusBarDirtyDB( self ):
        
        self._statusbar_db_thread_updater.Update()
        
    
    def ShowPage( self, page_key ):
        
        page = self._notebook.GetPageFromPageKey( page_key )
        
        if page is None:
            
            raise HydrusExceptions.DataMissing( 'Could not find that page!' )
            
        
        self._notebook.ShowPage( page )
        
    
    def TryToExit( self, restart = False, force_shutdown_maintenance = False ):
        
        if not self._controller.DoingFastExit():
            
            reasons_and_pages = self._notebook.GetAbleToCloseData( for_session_close = True )
            
            if HC.options[ 'confirm_client_exit' ] or len( reasons_and_pages ) > 0:
                
                if restart:
                    
                    text = 'Are you sure you want to restart the client? (Will auto-yes in 15 seconds)'
                    
                else:
                    
                    text = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
                    
                
                if len( reasons_and_pages ) > 0:
                    
                    able_to_close_statement = ClientGUIPages.ConvertReasonsAndPagesToStatement( reasons_and_pages )
                    
                    if 'import' in able_to_close_statement:
                        
                        text += '\n' * 2
                        text += 'Importers will save and continue their work on the next start.'
                        
                    
                    text += '\n' * 2
                    text += able_to_close_statement
                    
                    
                    try:
                        
                        ClientGUIPages.ShowReasonsAndPagesConfirmationDialog( self, reasons_and_pages, text, auto_yes_time = 15 )
                        
                    except HydrusExceptions.VetoException:
                        
                        return
                        
                    
                else:
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, text, auto_yes_time = 15 )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
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
                
                shutdown_work_due = HydrusTime.TimeHasPassed( last_shutdown_work_time + shutdown_work_period )
                
                if shutdown_work_due:
                    
                    if idle_shutdown_action == CC.IDLE_ON_SHUTDOWN:
                        
                        HG.do_idle_shutdown_work = True
                        
                    elif idle_shutdown_action == CC.IDLE_ON_SHUTDOWN_ASK_FIRST:
                        
                        idle_shutdown_max_minutes = self._controller.options[ 'idle_shutdown_max_minutes' ]
                        
                        time_to_stop = HydrusTime.GetNow() + ( idle_shutdown_max_minutes * 60 )
                        
                        work_to_do = self._controller.GetIdleShutdownWorkDue( time_to_stop )
                        
                        if len( work_to_do ) > 0:
                            
                            text = 'Is now a good time for the client to do up to ' + HydrusNumbers.ToHumanInt( idle_shutdown_max_minutes ) + ' minutes\' maintenance work? (Will auto-no in 15 seconds)'
                            text += '\n' * 2
                            
                            if CG.client_controller.IsFirstStart():
                                
                                text += 'Since this is your first session, this maintenance should just be some quick initialisation work. It should only take a few seconds.'
                                text += '\n' * 2
                                
                            
                            text += 'The outstanding jobs appear to be:'
                            text += '\n' * 2
                            text += '\n'.join( work_to_do )
                            
                            ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, title = 'Maintenance is due', auto_no_time = 15, check_for_cancelled = True )
                            
                            if was_cancelled:
                                
                                return
                                
                            elif result == QW.QDialog.DialogCode.Accepted:
                                
                                HG.do_idle_shutdown_work = True
                                
                            else:
                                
                                # if they said no, don't keep asking
                                self._controller.Write( 'register_shutdown_work' )
                                
                            
                        
                    
                
            except Exception as e:
                
                self._controller.BlockingSafeShowCriticalMessage( 'shutdown error', 'There was a problem trying to review pending shutdown maintenance work. No shutdown maintenance work will be done, and info has been written to the log. Please let hydev know.' )
                
                HydrusData.PrintException( e )
                
                HG.do_idle_shutdown_work = False
                
            
        
        CG.client_controller.CallAfter( self, self._controller.Exit )
        
    
    def TryToOpenManageServicesForAutoAccountCreation( self, service_key: bytes ):
        
        self._ManageServices( auto_account_creation_service_key = service_key )
        
    
    def UnregisterAnimationUpdateWindow( self, window ):
        
        self._animation_update_windows.discard( window )
        
    
    def UnregisterUIUpdateWindow( self, window ):
        
        self._ui_update_windows.discard( window )
        
    
    def UploadPending( self, service_key ):
        
        if service_key in self._currently_uploading_pending:
            
            return False
            
        
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
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'Unfortunately, there is a problem with starting the upload: ' + str( e ) )
            
            return False
            
        
        self._currently_uploading_pending.add( service_key )
        
        self._menu_updater_pending.update()
        
        self._controller.CallToThread( THREADUploadPending, service_key )
        
        return True
        
    
