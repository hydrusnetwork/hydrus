import collections
import collections.abc
import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesPhysical
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIPopupMessages
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUIMenuButton

class ReviewGranularityPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller", current_granularity: int ):
        
        self._controller = controller
        
        self._new_options = self._controller.new_options
        
        super().__init__( parent )
        
        self._current_granularity = current_granularity
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DATABASE_MIGRATION_GRANULARITY )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html migration/granularity help', 'Open the help page for database migration/granularity in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'detailed help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        title = 'The client uses many subfolders to split up your collection into manageable chunks. As clients have grown, we are pushing from a granularity of 2, which means 512 subfolders, to 3, which means 8,192.'
        title += '\n\n'
        title += 'Migrating to a higher granularity requires running a job here and then repeating it on your backups.'
        
        self._title_st = ClientGUICommon.BetterStaticText( self, label = title )
        self._title_st.setWordWrap( True )
        
        granularity_panel = ClientGUICommon.StaticBox( self, 'this client' )
        
        self._granularity_st = ClientGUICommon.BetterStaticText( granularity_panel )
        self._granularity_st.setWordWrap( True )
        
        self._migrate_2to3_button = ClientGUICommon.BetterButton( granularity_panel, 'I AM READY TO GO FROM 2 TO 3', self._Migrate2To3 )
        
        backup_panel = ClientGUICommon.StaticBox( self, 'granularising offline storage' )
        
        label = 'If you have a backup from when you were granularity 2, updating it from your new 3 will be hellish expensive because all the files have moved. Click the button here to granularise your backup, too, so it has the same folder structure as your client. Trust me, this will save lots of time.'
        
        self._backup_st = ClientGUICommon.BetterStaticText( backup_panel, label = label )
        self._backup_st.setWordWrap( True )
        
        self._migrate_backup_button_2to3 = ClientGUICommon.BetterButton( backup_panel, 'Migrate an offline folder from 2 to 3', self._MigrateFolder2To3 )
        self._migrate_backup_button_3to2 = ClientGUICommon.BetterButton( backup_panel, 'Migrate an offline folder from 3 to 2', self._MigrateFolder3To2 )
        
        #
        
        granularity_panel.Add( self._granularity_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        granularity_panel.Add( self._migrate_2to3_button, CC.FLAGS_ON_RIGHT )
        
        backup_panel.Add( self._backup_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        backup_panel.Add( self._migrate_backup_button_2to3, CC.FLAGS_ON_RIGHT )
        backup_panel.Add( self._migrate_backup_button_3to2, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        warning = 'THIS IS SERIOUSLY ONLY FOR ADVANCED USERS. AS I GATHER BETTER SPEED ESTIMATES, I ONLY WANT USERS WITH LESS THAN A MILLION USERS TO TRY THIS FOR NOW.'
        
        warning_st = ClientGUICommon.BetterStaticText( self, warning )
        warning_st.setObjectName( 'HydrusWarning' )
        warning_st.setWordWrap( True )
        
        QP.AddToLayout( vbox, warning_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._title_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, granularity_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, backup_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateGranularityLabel()
        
    
    def _Migrate2To3( self ):
        
        if self._current_granularity != 2:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'error!', f'Hey, your current granularity is {self._current_granularity}, but it needs to be 2 to enter this process! Something went wrong, please tell hydev.' )
            
            return
            
        
        message = 'We are going to be rearranging your file storage completely. The process can be cancelled if it is taking too long, but it has to do the same amount of work to undo. Once it is completed, it cannot currently be easily reversed. If it fails half way through, I will attempt to undo it.'
        message += '\n\n'
        message += 'Ideally, your client is currently calm and not trying to import many things. I estimate this runs on an SSD at 5,000 files/s, an HDD at 500 files/s, NAS at 100 files/s, and should not be attempted on cloud storage. If you think it will take too long, is ok to simply not do this.'
        message += '\n\n'
        message += 'Do you have a recent backup, in case something goes wrong?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, 'One last check!', yes_label = 'yes, I have a backup and I am ready', no_label = 'no, I am not ready' )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( 'Granularising Client File Storage' )
        
        def qt_cancelled():
            
            try:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'The job was cancelled by you and I think everything was undone ok.' )
                
            finally:
                
                self.setEnabled( True )
                
            
        
        def qt_error( e: Exception ):
            
            try:
                
                HydrusData.PrintException( e, do_wait = False )
                
                message = 'Something went wrong with the granularisation!! This is bad news. If this is the second time you are seeing this error, the database should have been able to undo the work successfully and you can return to normal work.'
                message += '\n\n'
                message += 'If this is the first error you saw, or the error has changed from the first time, then we have had a more serious problem. You should probably contact hydev regardless.'
                message += '\n\n'
                message += 'The error, which has been written in more detail to log, was:'
                message += '\n\n'
                message += str( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Oh no!', message )
                
            finally:
                
                self.setEnabled( True )
                
            
        
        def qt_ok( time_took_float: float, num_files_moved: int, num_weird_dirs: int, num_weird_files: int ):
            
            try:
                
                self._current_granularity = 3
                
                self._UpdateGranularityLabel()
                
                message = f'{HydrusNumbers.ToHumanInt( num_files_moved )} files moved in {HydrusTime.TimeDeltaToPrettyTimeDelta( time_took_float )}.'
                
                if num_weird_dirs == 0 and num_weird_files == 0:
                    
                    message += '\n\n'
                    message += 'Everything went great. You now have lower-latency file storage. The next step is to repeat this process for your backup file storage folders. Let hydev know if you have any problems!'
                    
                else:
                    
                    message += '\n\n'
                    message += 'Things went great. You now have lower-latency file storage. The next step is to repeat this process for your backup file storage folders. Let hydev know if you have any problems!'
                    message += '\n\n'
                    message += f'By the way, you had {HydrusNumbers.ToHumanInt( num_weird_dirs )} weird directories and {HydrusNumbers.ToHumanInt( num_weird_files )} weird files in your storage. They were not touched, but everything has been logged, so check out your log and see what that old cruft is. It is probably something like OS-level thumbnail metadata; not a big deal.'
                    
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
                
            finally:
                
                self.setEnabled( True )
                
            
        
        def do_it():
            
            try:
                
                time_started_float = HydrusTime.GetNowFloat()
                
                ( num_files_moved, num_weird_dirs, num_weird_files ) = CG.client_controller.client_files_manager.Granularise2To3( job_status )
                
                time_took_float = HydrusTime.GetNowFloat() - time_started_float
                
                CG.client_controller.CallAfterQtSafe( self, qt_ok, time_took_float, num_files_moved, num_weird_dirs, num_weird_files )
                
            except Exception as e:
                
                if isinstance( e, HydrusExceptions.DBException ) and isinstance( e.db_e, HydrusExceptions.CancelledException ):
                    
                    CG.client_controller.CallAfterQtSafe( self, qt_cancelled )
                    
                else:
                    
                    CG.client_controller.CallAfterQtSafe( self, qt_error, e )
                    
                
            finally:
                
                self.setEnabled( True )
                
            
        
        self.setEnabled( False )
        
        CG.client_controller.CallToThread( do_it )
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'Granularising', hide_buttons = True ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_status )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _MigrateFolder2To3( self ):
        
        self.MigrateFolder( 2, 3 )
        
    
    def _MigrateFolder3To2( self ):
        
        self.MigrateFolder( 3, 2 )
        
    
    def MigrateFolder( self, starting_granularity: int, ending_granularity: int ):
        
        message = 'We are going to be rearranging the file storage of your selected folder completely. The process cannot be cancelled or undone. I estimate it runs on an SSD at 5,000 files/s, an HDD at 500 files/s, NAS at 100 files/s, and should not be attempted on cloud storage.'
        message += '\n\n'
        message += 'When I ask which folder to work on, you want to select the one that _contains_ stuff like f86 or t32, often called "client_files" under a "db" dir. I will scan it beforehand to make sure it looks correct.'
        message += '\n\n'
        message += 'Are you ready?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, 'Ready check!', yes_label = 'yes, I am ready', no_label = 'no, I am not ready' )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        message = 'Select folder to regranularise.'
        
        try:
            
            base_location_path = ClientGUIDialogsQuick.PickDirectory( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        estimated_granularity = ClientFilesPhysical.EstimateBaseLocationGranularity( base_location_path )
        
        if estimated_granularity is None:
            
            message = 'I examined the folder but I am not sure what I am looking at. Are you sure this is correct?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, 'Unable to determine current granularity.' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        elif estimated_granularity != starting_granularity:
            
            if estimated_granularity == ending_granularity:
                
                message = f'I examined the folder, but I think it is already granularity {ending_granularity}. Maybe it is a mixed folder? Are you sure this is correct?'
                
            else:
                
                message = f'I examined the folder, but I think its current granularity is {estimated_granularity}! I do not know what is going on. Are you sure this is correct?'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, 'Proceed at your own risk.' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        else:
            
            message = 'Everything looks good. Start?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, 'Looking good.' )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( 'Regranularising a Client File Storage Folder' )
        
        def qt_cancelled():
            
            message = 'You cancelled the job. The folder is now likely in a mixed state, so you will want to re-do the job either way to undo or complete it.'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        def qt_error( e: Exception ):
            
            HydrusData.PrintException( e, do_wait = False )
            
            message = 'Something went wrong with the granularisation!! This may be bad news, but if it stopped half way through and you know how to fix the issue (maybe an errant file called "a" that you should move out?), you can just retry it and it will try to continue where it left off. The error, which has been written in more detail to log, was:'
            message += '\n\n'
            message += str( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Oh no!', message )
            
        
        def qt_ok( time_took_float: float, num_files_moved, num_weird_dirs: int, num_weird_files: int ):
            
            message = f'{HydrusNumbers.ToHumanInt( num_files_moved )} files moved in {HydrusTime.TimeDeltaToPrettyTimeDelta( time_took_float )}.'
            
            if num_weird_dirs == 0 and num_weird_files == 0:
                
                message += '\n\n'
                message += f'Everything went great. Your folder has been granularised to level {ending_granularity}.'
                
            else:
                
                message += '\n\n'
                message += f'Things went great. Your folder has been granularised to level {ending_granularity}.'
                message += '\n\n'
                message += f'By the way, you had {HydrusNumbers.ToHumanInt( num_weird_dirs )} weird directories and {HydrusNumbers.ToHumanInt( num_weird_files )} weird files in your storage. They were not touched, but everything has been logged, so check out your log and see what that old cruft is. It is probably something like OS-level thumbnail metadata; not a big deal.'
                
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        def do_it():
            
            try:
                
                time_started_float = HydrusTime.GetNowFloat()
                
                ( num_files_moved, num_weird_dirs, num_weird_files ) = ClientFilesPhysical.RegranulariseBaseLocation( [ base_location_path ], [ 'f', 't' ], starting_granularity, ending_granularity, job_status )
                
                time_took_float = HydrusTime.GetNowFloat() - time_started_float
                
                CG.client_controller.CallAfterQtSafe( self, qt_ok, time_took_float, num_files_moved, num_weird_dirs, num_weird_files )
                
            except HydrusExceptions.CancelledException:
                
                CG.client_controller.CallAfterQtSafe( self, qt_cancelled )
                
            except Exception as e:
                
                CG.client_controller.CallAfterQtSafe( self, qt_error, e )
                
            
        
        CG.client_controller.CallToThread( do_it )
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'Granularising', hide_buttons = True ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_status )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _UpdateGranularityLabel( self ):
        
        show_button = False
        
        if self._current_granularity == 2:
            
            show_button = True
            
            granularity_label = 'Your granularity is currently 2. If you are an advanced user, you are invited to move to 3.'
            
        elif self._current_granularity == 3:
            
            granularity_label = 'Your granularity is currently 3. How is it going?'
            
        else:
            
            granularity_label = f'Your granularity is "{self._current_granularity}", which is undefined! Close the client and contact hydev immediately.'
            
        
        self._granularity_st.setText( granularity_label )
        self._migrate_2to3_button.setVisible( show_button )
        
    

class MoveMediaFilesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        self._new_options = self._controller.new_options
        
        super().__init__( parent )
        
        ( self._current_granularity, self._client_files_subfolders ) = CG.client_controller.Read( 'client_files_subfolders' )
        
        ( self._media_base_locations, self._ideal_thumbnails_base_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        service_info = CG.client_controller.Read( 'service_info', CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
        
        self._hydrus_local_file_storage_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        self._hydrus_local_file_storage_total_num = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DATABASE_MIGRATION )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html migration help', 'Open the help page for database migration in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'database components' )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        file_locations_panel = ClientGUICommon.StaticBox( self, 'media file locations' )
        
        current_media_base_locations_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( file_locations_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DB_MIGRATION_LOCATIONS.ID, self._ConvertLocationToDisplayTuple, self._ConvertLocationToSortTuple )
        
        self._current_media_base_locations_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( current_media_base_locations_listctrl_panel, 8, model, activation_callback = self._SetMaxNumBytes )
        self._current_media_base_locations_listctrl.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        self._current_media_base_locations_listctrl.Sort()
        
        current_media_base_locations_listctrl_panel.SetListCtrl( self._current_media_base_locations_listctrl )
        
        current_media_base_locations_listctrl_panel.AddButton( 'add new location for files', self._SelectPathToAdd )
        current_media_base_locations_listctrl_panel.AddButton( 'increase location weight', self._IncreaseWeight, enabled_check_func = self._CanIncreaseWeight )
        current_media_base_locations_listctrl_panel.AddButton( 'decrease location weight', self._DecreaseWeight, enabled_check_func = self._CanDecreaseWeight )
        current_media_base_locations_listctrl_panel.AddButton( 'set max size', self._SetMaxNumBytes, enabled_check_func = self._CanSetMaxNumBytes )
        current_media_base_locations_listctrl_panel.AddButton( 'remove location', self._RemoveSelectedBaseLocation, enabled_check_func = self._CanRemoveLocation )
        
        self._thumbnails_location = QW.QLineEdit( file_locations_panel )
        self._thumbnails_location.setEnabled( False )
        
        self._thumbnails_location_set = ClientGUICommon.BetterButton( file_locations_panel, 'set', self._SetThumbnailLocation )
        
        self._thumbnails_location_clear = ClientGUICommon.BetterButton( file_locations_panel, 'clear', self._ClearThumbnailLocation )
        
        self._granularity_status_st = ClientGUICommon.BetterStaticText( file_locations_panel )
        self._granularity_status_st.setAlignment( QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
        
        self._granularity_button = ClientGUICommon.BetterButton( file_locations_panel, 'manage granularity', self._ManageGranularity )
        
        self._rebalance_status_st = ClientGUICommon.BetterStaticText( file_locations_panel )
        self._rebalance_status_st.setAlignment( QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
        
        self._rebalance_button = ClientGUICommon.BetterButton( file_locations_panel, 'move files now', self._Rebalance )
        
        #
        
        info_panel.Add( self._current_install_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_db_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_media_paths_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        t_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( t_hbox, ClientGUICommon.BetterStaticText( file_locations_panel, 'thumbnail location override' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( t_hbox, self._thumbnails_location, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( t_hbox, self._thumbnails_location_set, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( t_hbox, self._thumbnails_location_clear, CC.FLAGS_CENTER_PERPENDICULAR )
        
        granularity_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( granularity_hbox, self._granularity_status_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( granularity_hbox, self._granularity_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rebalance_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( rebalance_hbox, self._rebalance_status_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( rebalance_hbox, self._rebalance_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        file_locations_panel.Add( current_media_base_locations_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        file_locations_panel.Add( t_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        file_locations_panel.Add( granularity_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        file_locations_panel.Add( rebalance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'THIS IS ADVANCED. DO NOT CHANGE ANYTHING HERE UNLESS YOU KNOW WHAT IT DOES!'
        
        warning_st = ClientGUICommon.BetterStaticText( self, label = message )
        
        warning_st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, warning_st, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, file_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 100 )
        
        self.setMinimumWidth( min_width )
        
        self._Update()
        
    
    def _AddBaseLocation( self, base_location ):
        
        if base_location in self._media_base_locations:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You already have that location entered!' )
            
            return
            
        
        if self._ideal_thumbnails_base_location_override is not None and base_location.path == self._ideal_thumbnails_base_location_override.path:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'That path is already used as the special thumbnail location--please choose another.' )
            
            return
            
        
        self._media_base_locations.add( base_location )
        
        self._SaveToDB()
        
    
    def _AdjustWeight( self, amount ):
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                new_amount = base_location.ideal_weight + amount
                
                if new_amount > 0:
                    
                    base_location.ideal_weight = new_amount
                    
                    self._SaveToDB()
                    
                elif new_amount <= 0:
                    
                    self._RemoveBaseLocation( base_location )
                    
                
            else:
                
                if amount > 0:
                    
                    new_base_location = ClientFilesPhysical.FilesStorageBaseLocation( base_location.path, amount )
                    
                    if base_location != self._ideal_thumbnails_base_location_override:
                        
                        self._AddBaseLocation( new_base_location )
                        
                    
                
            
        
    
    def _CanDecreaseWeight( self ):
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                is_big = base_location.ideal_weight > 1
                others_can_take_slack = len( self._media_base_locations ) > 1
                
                if is_big or others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanIncreaseWeight( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                if len( self._media_base_locations ) > 1:
                    
                    return True
                    
                
            elif base_location in locations_to_file_weights:
                
                return True
                
            
        
        return False
        
    
    def _CanRemoveLocation( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                others_can_take_slack = len( self._media_base_locations ) > 1
                
                if others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanSetMaxNumBytes( self ):
        
        only_one_location_is_limitless = len( [ 1 for base_location in self._media_base_locations if base_location.max_num_bytes is None ] ) == 1
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                if base_location.max_num_bytes is None and only_one_location_is_limitless:
                    
                    return False
                    
                
                return True
                
            
        
        return False
        
    
    def _ClearThumbnailLocation( self ):
        
        message = 'Clear the custom thumbnail location? This will schedule all the thumbnail files to migrate back into the regular file locations.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._ideal_thumbnails_base_location_override = None
        
        self._SaveToDB()
        
    
    def _ConvertLocationToDisplayTuple( self, base_location: ClientFilesPhysical.FilesStorageBaseLocation ):
        
        f_space = self._hydrus_local_file_storage_total_size
        ( t_space_min, t_space_max ) = self._GetThumbnailSizeEstimates()
        
        #
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        path = base_location.path
        
        pretty_location = path
        
        if base_location.real_path != base_location.path:
            
            pretty_location = f'{pretty_location} (Real path: {base_location.real_path})'
            
        
        if os.path.exists( path ):
            
            try:
                
                free_space = HydrusPaths.GetFreeSpace( path )
                pretty_free_space = HydrusData.ToHumanBytes( free_space )
                
            except Exception as e:
                
                message = 'There was a problem finding the free space for "{path}"! Perhaps this location does not exist?'
                
                HydrusData.Print( message )
                
                HydrusData.PrintException( e )
                
                free_space = 0
                pretty_free_space = 'problem finding free space'
                
            
            if free_space is None:
                
                pretty_free_space = 'unknown'
                
            
        else:
            
            pretty_location = f'DOES NOT EXIST: {pretty_location}'
            
            pretty_free_space = 'DOES NOT EXIST'
            
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( base_location.path )
        portable = not os.path.isabs( portable_location )
        
        if portable:
            
            pretty_portable = 'yes'
            
        else:
            
            pretty_portable = 'no'
            
        
        fp = locations_to_file_weights[ base_location ]
        tp = locations_to_thumb_weights[ base_location ]
        
        p = lambda some_f: HydrusNumbers.FloatToPercentage( some_f, sf = 2 )
        
        current_bytes = fp * f_space + tp * t_space_max
        
        usages = []
        
        if fp > 0:
            
            usages.append( p( fp ) + ' files' )
            
        
        if tp > 0:
            
            usages.append( p( tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if fp == tp:
                
                usages = [ p( fp ) + ' everything' ]
                
            
            pretty_current_usage = HydrusData.ToHumanBytes( current_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_current_usage = 'nothing'
            
        
        #
        
        if base_location in self._media_base_locations:
            
            ideal_weight = base_location.ideal_weight
            
            pretty_ideal_weight = str( int( ideal_weight ) )
            
        else:
            
            if base_location in locations_to_file_weights:
                
                pretty_ideal_weight = '0'
                
            else:
                
                pretty_ideal_weight = 'n/a'
                
            
        
        if base_location.max_num_bytes is None:
            
            pretty_max_num_bytes = 'n/a'
            
        else:
            
            pretty_max_num_bytes = HydrusData.ToHumanBytes( base_location.max_num_bytes )
            
        
        ideal_fp = self._media_base_locations_to_ideal_usage.get( base_location, 0.0 )
        
        if self._ideal_thumbnails_base_location_override is None:
            
            ideal_tp = ideal_fp
            
        else:
            
            if base_location == self._ideal_thumbnails_base_location_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
        
        ideal_bytes = ideal_fp * f_space + ideal_tp * t_space_max
        
        ideal_usage = ( ideal_fp, ideal_tp )
        
        usages = []
        
        if ideal_fp > 0:
            
            usages.append( p( ideal_fp ) + ' files' )
            
        
        if ideal_tp > 0:
            
            usages.append( p( ideal_tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if ideal_fp == ideal_tp:
                
                usages = [ p( ideal_fp ) + ' everything' ]
                
            
            pretty_ideal_usage = HydrusData.ToHumanBytes( ideal_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_ideal_usage = 'nothing'
            
        
        display_tuple = ( pretty_location, pretty_portable, pretty_free_space, pretty_current_usage, pretty_ideal_weight, pretty_max_num_bytes, pretty_ideal_usage )
        
        return display_tuple
        
    
    def _ConvertLocationToSortTuple( self, base_location: ClientFilesPhysical.FilesStorageBaseLocation ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        path = base_location.path
        
        if os.path.exists( path ):
            
            pretty_location = path
            
            try:
                
                free_space = HydrusPaths.GetFreeSpace( path )
                
            except Exception as e:
                
                message = 'There was a problem finding the free space for "{path}"! Perhaps this location does not exist?'
                
                HydrusData.Print( message )
                
                HydrusData.PrintException( e )
                
                free_space = 0
                
            
            if free_space is None:
                
                free_space = 0
                
            
        else:
            
            pretty_location = 'DOES NOT EXIST: {}'.format( path )
            
            free_space = 0
            
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( base_location.path )
        portable = not os.path.isabs( portable_location )
        
        fp = locations_to_file_weights[ base_location ]
        tp = locations_to_thumb_weights[ base_location ]
        
        current_usage = ( fp, tp )
        
        #
        
        if base_location in self._media_base_locations:
            
            ideal_weight = base_location.ideal_weight
            
        else:
            
            ideal_weight = 0
            
        
        if base_location.max_num_bytes is None:
            
            sort_max_num_bytes = -1
            
        else:
            
            sort_max_num_bytes = base_location.max_num_bytes
            
        
        ideal_fp = self._media_base_locations_to_ideal_usage.get( base_location, 0.0 )
        
        if self._ideal_thumbnails_base_location_override is None:
            
            ideal_tp = ideal_fp
            
        else:
            
            if base_location == self._ideal_thumbnails_base_location_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
        
        ideal_usage = ( ideal_fp, ideal_tp )
        
        sort_tuple = ( pretty_location, portable, free_space, ideal_weight, ideal_usage, sort_max_num_bytes, current_usage )
        
        return sort_tuple
        
    
    def _DecreaseWeight( self ):
        
        self._AdjustWeight( -1 )
        
    
    def _GetLocationsToCurrentWeights( self ):
        
        locations_to_file_weights = collections.Counter()
        locations_to_thumb_weights = collections.Counter()
        
        for client_files_subfolder in self._client_files_subfolders:
            
            prefix = client_files_subfolder.prefix
            base_location = client_files_subfolder.base_location
            
            subfolder_weight = client_files_subfolder.GetNormalisedWeight()
            
            if prefix.startswith( 'f' ):
                
                locations_to_file_weights[ base_location ] += subfolder_weight
                
            
            if prefix.startswith( 't' ):
                
                locations_to_thumb_weights[ base_location ] += subfolder_weight
                
            
        
        return ( locations_to_file_weights, locations_to_thumb_weights )
        
    
    def _GetListCtrlLocations( self ):
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        all_locations = set()
        
        all_locations.update( self._media_base_locations )
        
        if self._ideal_thumbnails_base_location_override is not None:
            
            all_locations.add( self._ideal_thumbnails_base_location_override )
            
        
        all_locations.update( locations_to_file_weights.keys() )
        all_locations.update( locations_to_thumb_weights.keys() )
        
        all_locations = list( all_locations )
        
        return all_locations
        
    
    def _GetThumbnailSizeEstimates( self ):
        
        ( t_width, t_height ) = CG.client_controller.options[ 'thumbnail_dimensions' ]
        
        typical_thumb_num_pixels = 320 * 240
        typical_thumb_size = 36 * 1024
        
        our_thumb_num_pixels = t_width * t_height
        our_thumb_size_estimate = typical_thumb_size * ( our_thumb_num_pixels / typical_thumb_num_pixels )
        
        our_total_thumb_size_estimate = self._hydrus_local_file_storage_total_num * our_thumb_size_estimate
        
        return ( int( our_total_thumb_size_estimate * 0.8 ), int( our_total_thumb_size_estimate * 1.4 ) )
        
    
    def _IncreaseWeight( self ):
        
        self._AdjustWeight( 1 )
        
    
    def _ManageGranularity( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'manage granularity' ) as dlg:
            
            panel = ReviewGranularityPanel( dlg, self._controller, self._current_granularity )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        self._Update()
        
    
    def _Rebalance( self ):
        
        for base_location in self._GetListCtrlLocations():
            
            if not os.path.exists( base_location.path ):
                
                message = 'The path "{}" does not exist! Please ensure all the locations on this dialog are valid before trying to rebalance your files.'.format( base_location )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
                return
                
            
        
        
        message = 'Moving files can be a slow and slightly laggy process, with the UI intermittently hanging, which sometimes makes manually stopping a large ongoing job difficult. Would you like to set a max runtime on this job?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'run for 10 minutes', 600 ) )
        yes_tuples.append( ( 'run for 30 minutes', 1800 ) )
        yes_tuples.append( ( 'run for 1 hour', 3600 ) )
        yes_tuples.append( ( 'run for custom time', -1 ) )
        yes_tuples.append( ( 'run indefinitely', None ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if result is None:
            
            stop_time = None
            
        else:
            
            if result == -1:
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'set time to run' ) as dlg:
                    
                    panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                    
                    control = ClientGUITime.TimeDeltaWidget( self, min = 60, days = False, hours = True, minutes = True )
                    
                    control.SetValue( 7200 )
                    
                    panel.SetControl( control, perpendicular = True )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        result = int( control.GetValue() )
                        
                    else:
                        
                        return
                        
                    
                
            
            stop_time = HydrusTime.GetNow() + result
            
        
        job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
        
        CG.client_controller.pub( 'do_file_storage_rebalance', job_status )
        
        self._OKParent()
        
    
    def _RemoveBaseLocation( self, base_location ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        removees = set()
        
        if base_location not in self._media_base_locations:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Please select a location with weight.' )
            
            return
            
        
        if len( self._media_base_locations ) == 1:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You cannot empty every single current file location--please add a new place for the files to be moved to and then try again.' )
            
        
        if os.path.exists( base_location.path ):
            
            if base_location in locations_to_file_weights:
                
                message = 'Are you sure you want to remove this location? This will schedule all of the files it is currently responsible for to be moved elsewhere.'
                
            else:
                
                message = 'Are you sure you want to remove this location?'
                
            
        else:
            
            if base_location in locations_to_file_weights:
                
                message = 'This path does not exist, but it seems to have files. This could be a critical error that has occurred while the client is open (maybe a drive unmounting?). I recommend you do not remove it here and instead shut the client down immediately and fix the problem, then restart it, which will run the \'recover missing file locations\' routine if needed.'
                
            else:
                
                message = 'This path does not exist. Just checking, but I recommend you remove it.'
                
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._media_base_locations.remove( base_location )
            
            self._SaveToDB()
            
        
    
    def _RemoveSelectedBaseLocation( self ):
        
        locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            self._RemoveBaseLocation( location )
            
        
    
    def _SaveToDB( self ):
        
        self._controller.Write( 'ideal_client_files_locations', self._media_base_locations, self._ideal_thumbnails_base_location_override )
        
        self._controller.client_files_manager.Reinit()
        
        self._Update()
        
    
    def _SelectPathToAdd( self ):
        
        try:
            
            path = ClientGUIDialogsQuick.PickDirectory( self, 'Select location.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 1 )
        
        self._AddBaseLocation( base_location )
        
    
    def _SetMaxNumBytes( self ):
        
        if not self._CanSetMaxNumBytes():
            
            return
            
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                max_num_bytes = base_location.max_num_bytes
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit max size' ) as dlg:
                    
                    message = 'If a location goes over its set size, it will schedule to migrate some files to other locations. At least one media location must have no limit.'
                    message += '\n' * 2
                    message += 'This is not precise (it works on average size, and thumbnails can add a bit), so give it some padding. Also, in general, remember it is not healthy to fill any hard drive more than 90% full.'
                    message += '\n' * 2
                    message += 'Also, this feature is under active development. The client will go over this limit if your collection grows significantly--the only way things rebalance atm are if you click "move files now"--but in future I will have things automatically migrate in the background to ensure limits are obeyed. This is just for advanced users to play with for now!'
                    
                    panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg, message = message )
                    
                    control = ClientGUIBytes.NoneableBytesControl( panel, 100 * ( 1024 ** 3 ) )
                    
                    control.SetValue( max_num_bytes )
                    
                    panel.SetControl( control, perpendicular = True )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        max_num_bytes = control.GetValue()
                        
                        base_location.max_num_bytes = max_num_bytes
                        
                        self._SaveToDB()
                        
                    
                
            
        
    
    def _SetThumbnailLocation( self ):
        
        if self._ideal_thumbnails_base_location_override is not None:
            
            starting_dir_path = self._ideal_thumbnails_base_location_override.path
            
        else:
            
            starting_dir_path = None
            
        
        try:
            
            path = ClientGUIDialogsQuick.PickDirectory( self, 'Select thumbnail location.', starting_dir_path = starting_dir_path )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        all_paths = { base_location.path for base_location in self._media_base_locations }
        
        if path in all_paths:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'That path already exists as a regular file location! Please choose another.' )
            
        else:
            
            self._ideal_thumbnails_base_location_override = ClientFilesPhysical.FilesStorageBaseLocation( path, 1 )
            
            self._SaveToDB()
            
        
    
    def _Update( self ):
        
        ( self._current_granularity, self._client_files_subfolders ) = CG.client_controller.Read( 'client_files_subfolders' )
        
        ( self._media_base_locations, self._ideal_thumbnails_base_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        self._media_base_locations_to_ideal_usage = ClientFilesPhysical.FilesStorageBaseLocation.STATICGetIdealWeights( self._hydrus_local_file_storage_total_size, self._media_base_locations )
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.setText( 'database (about '+HydrusData.ToHumanBytes(approx_total_db_size)+'): '+self._controller.GetDBDir() )
        self._current_install_path_st.setText( 'install: ' + HC.BASE_DIR )
        
        approx_total_client_files = self._hydrus_local_file_storage_total_size
        ( approx_total_thumbnails_min, approx_total_thumbnails_max ) = self._GetThumbnailSizeEstimates()
        
        label = 'media is {}, thumbnails are estimated at {}-{}'.format( HydrusData.ToHumanBytes( approx_total_client_files ), HydrusData.ToHumanBytes( approx_total_thumbnails_min ), HydrusData.ToHumanBytes( approx_total_thumbnails_max ) )
        
        self._current_media_paths_st.setText( label )
        self._current_media_paths_st.setToolTip( ClientGUIFunctions.WrapToolTip( 'Precise thumbnail sizes are not tracked, so this is an estimate based on your current thumbnail dimensions.' ) )
        
        base_locations = self._GetListCtrlLocations()
        
        self._current_media_base_locations_listctrl.SetData( base_locations )
        
        #
        
        if self._ideal_thumbnails_base_location_override is None:
            
            self._thumbnails_location.setText( 'none set' )
            
            self._thumbnails_location_clear.setEnabled( False )
            
        else:
            
            self._thumbnails_location.setText( self._ideal_thumbnails_base_location_override.path )
            
            self._thumbnails_location_clear.setEnabled( True )
            
        
        #
        
        if self._current_granularity == 2:
            
            granularity_label = 'You have a granularity of 2, which means 512 total subfolders.'
            
        elif self._current_granularity == 3:
            
            granularity_label = 'You have a granularity of 3, which means 8,192 total subfolders.'
            
        else:
            
            granularity_label = f'Your granularity is "{self._current_granularity}", which is not supported!! This is not supposed to happen.'
            
        
        self._granularity_status_st.setText( granularity_label )
        
        #
        
        if self._controller.client_files_manager.RebalanceWorkToDo():
            
            self._rebalance_button.setEnabled( True )
            
            self._rebalance_status_st.setText( 'files need to be moved' )
            self._rebalance_status_st.setObjectName( 'HydrusInvalid' )
            
        else:
            
            self._rebalance_button.setEnabled( False )
            
            self._rebalance_status_st.setText( 'all files are in their ideal locations' )
            self._rebalance_status_st.setObjectName( 'HydrusValid' )
            
        
        self._rebalance_status_st.style().polish( self._rebalance_status_st )
        
    
