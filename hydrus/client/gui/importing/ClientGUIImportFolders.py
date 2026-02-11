import collections.abc
import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIFileSeedCache
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMetadataMigration
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationTest
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPathWidgets
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters

class EditImportFoldersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, import_folders ):
        
        super().__init__( parent )
        
        import_folders_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_IMPORT_FOLDERS.ID, self._ConvertImportFolderToDisplayTuple, self._ConvertImportFolderToSortTuple )
        
        self._import_folders = ClientGUIListCtrl.BetterListCtrlTreeView( import_folders_panel, 8, model, use_simple_delete = True, activation_callback = self._Edit )
        
        import_folders_panel.SetListCtrl( self._import_folders )
        
        import_folders_panel.AddButton( 'add', self._Add )
        import_folders_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        import_folders_panel.AddDeleteButton()
        
        #
        
        self._import_folders.SetData( import_folders )
        
        self._import_folders.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        intro = 'Here you can set the client to regularly check certain folders for new files to import.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,intro), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        warning = 'WARNING: Import folders check (and potentially move/delete!) the contents of all subdirectories as well as the base directory!'
        
        warning_st = ClientGUICommon.BetterStaticText( self, warning )
        warning_st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, warning_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, import_folders_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        import_folder = ClientImportLocal.ImportFolder( 'import folder' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import folder' ) as dlg:
            
            panel = EditImportFolderPanel( dlg, import_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                import_folder = panel.GetValue()
                
                import_folder.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
                
                self._import_folders.AddData( import_folder, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertImportFolderToDisplayTuple( self, import_folder ):
        
        ( name, path, paused, check_regularly, check_period ) = import_folder.ToListBoxTuple()
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        if not check_regularly:
            
            pretty_check_period = 'not checking regularly'
            
        else:
            
            pretty_check_period = HydrusTime.TimeDeltaToPrettyTimeDelta( check_period )
            
        
        display_tuple = ( name, path, pretty_paused, pretty_check_period )
        
        return display_tuple
        
    
    def _ConvertImportFolderToSortTuple( self, import_folder ):
        
        ( name, path, paused, check_regularly, check_period ) = import_folder.ToListBoxTuple()
        
        if not check_regularly:
            
            sort_check_period = ( 1, 0 )
            
        else:
            
            sort_check_period = ( 0, check_period )
            
        
        sort_tuple = ( name, path, paused, check_period )
        
        return sort_tuple
        
    
    def _Edit( self ):
        
        import_folder: ClientImportLocal.ImportFolder | None = self._import_folders.GetTopSelectedData()
        
        if import_folder is None:
            
            return
            
        
        original_name = import_folder.GetName()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import folder' ) as dlg:
            
            panel = EditImportFolderPanel( dlg, import_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_folder = panel.GetValue()
                
                if edited_import_folder.GetName() != original_name:
                    
                    existing_names = self._GetExistingNames()
                    
                    existing_names.discard( original_name )
                    
                    edited_import_folder.SetNonDupeName( existing_names, do_casefold = True )
                    
                
                self._import_folders.ReplaceData( import_folder, edited_import_folder, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        import_folders = self._import_folders.GetData()
        
        names = { import_folder.GetName() for import_folder in import_folders }
        
        return names
        
    
    def GetValue( self ) -> collections.abc.Collection[ ClientImportLocal.ImportFolder ]:
        
        import_folders = self._import_folders.GetData()
        
        return import_folders
        
    

class EditImportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, import_folder: ClientImportLocal.ImportFolder ):
        
        super().__init__( parent )
        
        self._import_folder = import_folder
        
        ( name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ) = self._import_folder.ToTuple()
        
        self._folder_box = ClientGUICommon.StaticBox( self, 'folder options' )
        
        self._name = QW.QLineEdit( self._folder_box )
        
        self._path = ClientGUIPathWidgets.DirPickerCtrl( self._folder_box )
        
        self._search_subdirectories = QW.QCheckBox( self._folder_box )
        
        self._check_regularly = QW.QCheckBox( self._folder_box )
        
        self._period = ClientGUITime.TimeDeltaButton( self._folder_box, min = 3 * 60, days = True, hours = True, minutes = True )
        
        self._last_modified_time_skip_period = ClientGUITime.TimeDeltaButton( self._folder_box, min = 1, days = True, hours = True, minutes = True, seconds = True )
        tt = 'If a file has a modified time more recent than this long ago, it will not be imported in the current check. Helps to avoid importing files that are in the process of downloading/copying (usually on a NAS where other "already in use" checks may fail).'
        self._last_modified_time_skip_period.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._paused = QW.QCheckBox( self._folder_box )
        
        self._check_now = QW.QCheckBox( self._folder_box )
        
        self._show_working_popup = QW.QCheckBox( self._folder_box )
        self._publish_files_to_popup_button = QW.QCheckBox( self._folder_box )
        self._publish_files_to_page = QW.QCheckBox( self._folder_box )
        
        self._file_seed_cache_button = ClientGUIFileSeedCache.FileSeedCacheButton( self._folder_box, self._import_folder.GetFileSeedCache, file_seed_cache_set_callable = self._import_folder.SetFileSeedCache )
        
        #
        
        show_downloader_options = False
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        
        #
        
        self._file_box = ClientGUICommon.StaticBox( self, 'source file actions' )
        
        def create_choice():
            
            choice = ClientGUICommon.BetterChoice( self._file_box )
            
            for if_id in ( CC.IMPORT_FOLDER_DELETE, CC.IMPORT_FOLDER_IGNORE, CC.IMPORT_FOLDER_MOVE ):
                
                choice.addItem( CC.import_folder_string_lookup[ if_id], if_id )
                
            
            choice.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you set this to delete or move, any sidecars will be deleted or moved also. If you are using the same sidecar for multiple files, you must not set delete/move or the sidecar will disappear for the next file import!' ) )
            
            choice.currentIndexChanged.connect( self._CheckLocations )
            
            return choice
            
        
        self._action_successful = create_choice()
        self._location_successful = ClientGUIPathWidgets.DirPickerCtrl( self._file_box )
        
        self._action_redundant = create_choice()
        self._location_redundant = ClientGUIPathWidgets.DirPickerCtrl( self._file_box )
        
        self._action_deleted = create_choice()
        self._location_deleted = ClientGUIPathWidgets.DirPickerCtrl( self._file_box )
        
        self._action_failed = create_choice()
        self._location_failed = ClientGUIPathWidgets.DirPickerCtrl( self._file_box )
        
        #
        
        self._filename_tagging_options_box = ClientGUICommon.StaticBox( self, 'metadata import' )
        
        filename_tagging_options_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._filename_tagging_options_box )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_FILENAME_TAGGING_OPTIONS.ID, self._ConvertFilenameTaggingOptionsToDisplayTuple, self._ConvertFilenameTaggingOptionsToSortTuple )
        
        self._filename_tagging_options = ClientGUIListCtrl.BetterListCtrlTreeView( filename_tagging_options_panel, 5, model, use_simple_delete = True, activation_callback = self._EditFilenameTaggingOptions )
        
        filename_tagging_options_panel.SetListCtrl( self._filename_tagging_options )
        
        filename_tagging_options_panel.AddButton( 'add', self._AddFilenameTaggingOptions )
        filename_tagging_options_panel.AddButton( 'edit', self._EditFilenameTaggingOptions, enabled_only_on_single_selection = True )
        filename_tagging_options_panel.AddDeleteButton()
        
        metadata_routers = self._import_folder.GetMetadataRouters()
        allowed_importer_classes = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT, ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON ]
        allowed_exporter_classes = [ ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps ]
        
        # example paths are set to this guy later, no worries
        self._sidecar_test_context_factory = ClientGUIMetadataMigrationTest.MigrationTestContextFactorySidecar( [] )
        
        self._metadata_routers_button = ClientGUIMetadataMigration.SingleFileMetadataRoutersButton( self, metadata_routers, allowed_importer_classes, allowed_exporter_classes, self._sidecar_test_context_factory )
        
        #
        
        self._name.setText( name )
        self._path.SetPath( path )
        
        self._search_subdirectories.setChecked( self._import_folder.GetSearchSubdirectories() )
        
        self._check_regularly.setChecked( check_regularly )
        
        self._period.SetValue( period )
        
        self._last_modified_time_skip_period.SetValue( import_folder.GetLastModifiedTimeSkipPeriod() )
        
        self._paused.setChecked( paused )
        
        self._show_working_popup.setChecked( show_working_popup )
        self._publish_files_to_popup_button.setChecked( publish_files_to_popup_button )
        self._publish_files_to_page.setChecked( publish_files_to_page )
        
        self._action_successful.SetValue( actions[ CC.STATUS_SUCCESSFUL_AND_NEW ] )
        if CC.STATUS_SUCCESSFUL_AND_NEW in action_locations:
            
            self._location_successful.SetPath( action_locations[ CC.STATUS_SUCCESSFUL_AND_NEW ] )
            
        
        self._action_redundant.SetValue( actions[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] )
        if CC.STATUS_SUCCESSFUL_BUT_REDUNDANT in action_locations:
            
            self._location_redundant.SetPath( action_locations[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] )
            
        
        self._action_deleted.SetValue( actions[ CC.STATUS_DELETED ] )
        if CC.STATUS_DELETED in action_locations:
            
            self._location_deleted.SetPath( action_locations[ CC.STATUS_DELETED ] )
            
        
        self._action_failed.SetValue( actions[ CC.STATUS_ERROR ] )
        if CC.STATUS_ERROR in action_locations:
            
            self._location_failed.SetPath( action_locations[ CC.STATUS_ERROR ] )
            
        
        good_tag_service_keys_to_filename_tagging_options = { service_key : filename_tagging_options for ( service_key, filename_tagging_options ) in list(tag_service_keys_to_filename_tagging_options.items()) if CG.client_controller.services_manager.ServiceExists( service_key ) }
        
        self._filename_tagging_options.AddDatas( list( good_tag_service_keys_to_filename_tagging_options.items() ) )
        
        self._filename_tagging_options.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'folder path: ', self._path ) )
        rows.append( ( 'search subdirectories: ', self._search_subdirectories ) )
        rows.append( ( 'currently paused (if set, will not ever do any work): ', self._paused ) )
        rows.append( ( 'check regularly?: ', self._check_regularly ) )
        rows.append( ( 'check period: ', self._period ) )
        rows.append( ( 'recent modified time skip period: ', self._last_modified_time_skip_period ) )
        rows.append( ( 'check on manage dialog ok: ', self._check_now ) )
        rows.append( ( 'show a popup while working: ', self._show_working_popup ) )
        rows.append( ( 'publish presented files to a popup button: ', self._publish_files_to_popup_button ) )
        rows.append( ( 'publish presented files to a page: ', self._publish_files_to_page ) )
        rows.append( ( 'review currently cached import paths: ', self._file_seed_cache_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._folder_box, rows )
        
        self._folder_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        gridbox = QP.GridLayout( cols = 3 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        QP.AddToLayout( gridbox, QW.QLabel( 'when a file imports successfully: ', self._file_box ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._action_successful, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._location_successful, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( gridbox, QW.QLabel( 'when a file is already in the db: ', self._file_box ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._action_redundant, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._location_redundant, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( gridbox, QW.QLabel( 'when a file has previously been deleted from the db: ', self._file_box ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._action_deleted, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._location_deleted, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( gridbox, QW.QLabel( 'when a file fails to import: ', self._file_box ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._action_failed, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._location_failed, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._file_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._filename_tagging_options_box.Add( ClientGUICommon.BetterStaticText( self._filename_tagging_options_box, 'filename tagging:' ), CC.FLAGS_CENTER_PERPENDICULAR )
        self._filename_tagging_options_box.Add( filename_tagging_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._filename_tagging_options_box.Add( ClientGUICommon.BetterStaticText( self._filename_tagging_options_box, 'sidecar importing:' ), CC.FLAGS_CENTER_PERPENDICULAR )
        self._filename_tagging_options_box.Add( self._metadata_routers_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._folder_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filename_tagging_options_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._CheckLocations()
        
        self._check_regularly.clicked.connect( self._UpdateCheckRegularly )
        
        self._UpdateCheckRegularly()
        
        self._path.dirPickerChanged.connect( self._PathChanged )
        
        self._PathChanged()
        
    
    def _AddFilenameTaggingOptions( self ):
        
        service_key = ClientGUIDialogsQuick.SelectServiceKey( HC.REAL_TAG_SERVICES )
        
        if service_key is None:
            
            return
            
        
        existing_service_keys = { service_key for ( service_key, filename_tagging_options ) in self._filename_tagging_options.GetData() }
        
        if service_key in existing_service_keys:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You already have an entry for that service key! Please try editing it instead!' )
            
            return
            
        
        example_paths = self._sidecar_test_context_factory.GetExampleFilePaths()
        
        if len( example_paths ) > 0:
            
            example_path = example_paths[0]
            
        else:
            
            example_path = None
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit filename tagging options' ) as dlg:
            
            filename_tagging_options = TagImportOptionsLegacy.FilenameTaggingOptions()
            
            panel = ClientGUIImport.EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options, example_path = example_path )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                filename_tagging_options = panel.GetValue()
                
                data = ( service_key, filename_tagging_options )
                
                self._filename_tagging_options.AddData( data, select_sort_and_scroll = True )
                
            
        
    
    def _CheckLocations( self ):
        
        if self._action_successful.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_successful.setEnabled( True )
            
        else:
            
            self._location_successful.setEnabled( False )
            
        
        if self._action_redundant.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_redundant.setEnabled( True )
            
        else:
            
            self._location_redundant.setEnabled( False )
            
        
        if self._action_deleted.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_deleted.setEnabled( True )
            
        else:
            
            self._location_deleted.setEnabled( False )
            
        
        if self._action_failed.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_failed.setEnabled( True )
            
        else:
            
            self._location_failed.setEnabled( False )
            
        
    
    def _CheckValid( self ):
        
        path = self._path.GetPath()
        
        if path in ( '', None ):
            
            raise HydrusExceptions.VetoException( 'You must enter a path to import from!' )
            
        
        if not os.path.exists( path ):
            
            ClientGUIDialogsMessage.ShowWarning( self, f'The path you have entered--"{path}"--does not exist! The dialog will not force you to correct it, but this import folder will do no work as long as the location is missing!' )
            
        
        ( dirs_that_allow_internal_work, dirs_that_cannot_be_touched ) = CG.client_controller.GetImportSensitiveDirectories()
        
        sensitive_paths = list( dirs_that_allow_internal_work ) + list( dirs_that_cannot_be_touched )
        
        for sensitive_path in sensitive_paths:
            
            if sensitive_path.startswith( path ):
                
                raise HydrusExceptions.VetoException( f'You cannot set an import path that includes certain sensitive directories. The problem directory in this case was "{sensitive_path}". Please choose another location.' )
                
            
            if sensitive_path not in dirs_that_allow_internal_work:
                
                if path.startswith( sensitive_path ):
                    
                    raise HydrusExceptions.VetoException( f'You cannot set an import path that is inside certain sensitive directories. The problem directory in this case was "{sensitive_path}". Please choose another location.' )
                    
                
            
        
        if self._action_successful.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_successful.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your successful file move location!' )
                
            
            if not os.path.exists( path ):
                
                ClientGUIDialogsMessage.ShowWarning( self, f'The path you have entered for your successful file move location--"{path}"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_redundant.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_redundant.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your redundant file move location!' )
                
            
            if not os.path.exists( path ):
                
                ClientGUIDialogsMessage.ShowWarning( self, f'The path you have entered for your redundant file move location--"{path}"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_deleted.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_deleted.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your deleted file move location!' )
                
            
            if not os.path.exists( path ):
                
                ClientGUIDialogsMessage.ShowWarning( self, f'The path you have entered for your deleted file move location--"{path}"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_failed.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_failed.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your failed file move location!' )
                
            
            if not os.path.exists( path ):
                
                ClientGUIDialogsMessage.ShowWarning( self, f'The path you have entered for your failed file move location--"{path}"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
    
    def _ConvertFilenameTaggingOptionsToDisplayTuple( self, data ):
        
        ( service_key, filename_tagging_options ) = data
        
        name = CG.client_controller.services_manager.GetName( service_key )
        
        display_tuple = ( name, )
        
        return display_tuple
        
    
    _ConvertFilenameTaggingOptionsToSortTuple = _ConvertFilenameTaggingOptionsToDisplayTuple
    
    def _EditFilenameTaggingOptions( self ):
        
        data = self._filename_tagging_options.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( service_key, filename_tagging_options ) = data
        
        example_paths = self._sidecar_test_context_factory.GetExampleFilePaths()
        
        if len( example_paths ) > 0:
            
            example_path = example_paths[0]
            
        else:
            
            example_path = None
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit filename tagging options' ) as dlg:
            
            panel = ClientGUIImport.EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options, example_path = example_path )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                filename_tagging_options = panel.GetValue()
                
                new_data = ( service_key, filename_tagging_options )
                
                self._filename_tagging_options.ReplaceData( data, new_data, sort_and_scroll = True )
                
            
        
        
    
    def _PathChanged( self ):
        
        path = self._path.GetPath()
        
        try:
            
            if os.path.exists( path ) and os.path.isdir( path ):
                
                filenames = list( os.listdir( path ) )[:ClientGUIMetadataMigrationTest.HOW_MANY_EXAMPLE_OBJECTS_TO_USE]
                
                example_paths = [ f for f in [ os.path.join( path, filename ) for filename in filenames ] if os.path.isfile( f ) and HydrusFileHandling.GetMime( f ) in HC.ALLOWED_MIMES ]
                
                self._sidecar_test_context_factory.SetExampleFilePaths( example_paths )
                
            
        except Exception as e:
            
            return
            
        
    
    def _UpdateCheckRegularly( self ):
        
        if self._check_regularly.isChecked():
            
            self._period.setEnabled( True )
            
        else:
            
            self._period.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        self._CheckValid()
        
        edited_import_folder = self._import_folder.Duplicate()
        
        name = self._name.text()
        path = self._path.GetPath()
        file_import_options = self._import_options_button.GetFileImportOptions()
        tag_import_options = self._import_options_button.GetTagImportOptions()
        
        actions = {}
        action_locations = {}
        
        actions[ CC.STATUS_SUCCESSFUL_AND_NEW ] = self._action_successful.GetValue()
        if actions[ CC.STATUS_SUCCESSFUL_AND_NEW ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_SUCCESSFUL_AND_NEW ] = self._location_successful.GetPath()
            
        
        actions[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] = self._action_redundant.GetValue()
        if actions[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] = self._location_redundant.GetPath()
            
        
        actions[ CC.STATUS_DELETED ] = self._action_deleted.GetValue()
        if actions[ CC.STATUS_DELETED] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_DELETED ] = self._location_deleted.GetPath()
            
        
        actions[ CC.STATUS_ERROR ] = self._action_failed.GetValue()
        if actions[ CC.STATUS_ERROR ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_ERROR ] = self._location_failed.GetPath()
            
        
        period = self._period.GetValue()
        
        check_regularly = self._check_regularly.isChecked()
        
        paused = self._paused.isChecked()
        
        check_now = self._check_now.isChecked()
        
        show_working_popup = self._show_working_popup.isChecked()
        publish_files_to_popup_button = self._publish_files_to_popup_button.isChecked()
        publish_files_to_page = self._publish_files_to_page.isChecked()
        
        tag_service_keys_to_filename_tagging_options = dict( self._filename_tagging_options.GetData() )
        
        edited_import_folder.SetTuple( name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
        
        edited_import_folder.SetLastModifiedTimeSkipPeriod( self._last_modified_time_skip_period.GetValue() )
        
        metadata_routers = self._metadata_routers_button.GetValue()
        
        edited_import_folder.SetMetadataRouters( metadata_routers )
        
        search_subdirectories = self._search_subdirectories.isChecked()
        
        edited_import_folder.SetSearchSubdirectories( search_subdirectories )
        
        return edited_import_folder
        
