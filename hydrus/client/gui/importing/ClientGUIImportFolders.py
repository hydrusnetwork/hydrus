import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFileSeedCache
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMetadataMigration
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters

class EditImportFoldersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, import_folders ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        import_folders_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._import_folders = ClientGUIListCtrl.BetterListCtrl( import_folders_panel, CGLC.COLUMN_LIST_IMPORT_FOLDERS.ID, 8, self._ConvertImportFolderToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        import_folders_panel.SetListCtrl( self._import_folders )
        
        import_folders_panel.AddButton( 'add', self._Add )
        import_folders_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                import_folder = panel.GetValue()
                
                import_folder.SetNonDupeName( self._GetExistingNames() )
                
                self._import_folders.AddDatas( ( import_folder, ) )
                
                self._import_folders.Sort()
                
            
        
    
    def _ConvertImportFolderToListCtrlTuples( self, import_folder ):
        
        ( name, path, paused, check_regularly, check_period ) = import_folder.ToListBoxTuple()
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        if not check_regularly:
            
            pretty_check_period = 'not checking regularly'
            
        else:
            
            pretty_check_period = HydrusData.TimeDeltaToPrettyTimeDelta( check_period )
            
        
        sort_tuple = ( name, path, paused, check_period )
        display_tuple = ( name, path, pretty_paused, pretty_check_period )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        edited_datas = []
        
        import_folders = self._import_folders.GetData( only_selected = True )
        
        for import_folder in import_folders:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import folder' ) as dlg:
                
                panel = EditImportFolderPanel( dlg, import_folder )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_import_folder = panel.GetValue()
                    
                    self._import_folders.DeleteDatas( ( import_folder, ) )
                    
                    edited_import_folder.SetNonDupeName( self._GetExistingNames() )
                    
                    self._import_folders.AddDatas( ( edited_import_folder, ) )
                    
                    edited_datas.append( edited_import_folder )
                    
                else:
                    
                    break
                    
                
            
        
        self._import_folders.SelectDatas( edited_datas )
        
        self._import_folders.Sort()
        
    
    def _GetExistingNames( self ):
        
        import_folders = self._import_folders.GetData()
        
        names = { import_folder.GetName() for import_folder in import_folders }
        
        return names
        
    
    def GetValue( self ):
        
        import_folders = self._import_folders.GetData()
        
        return import_folders
        
    
class EditImportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, import_folder: ClientImportLocal.ImportFolder ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._import_folder = import_folder
        
        ( name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ) = self._import_folder.ToTuple()
        
        self._folder_box = ClientGUICommon.StaticBox( self, 'folder options' )
        
        self._name = QW.QLineEdit( self._folder_box )
        
        self._path = QP.DirPickerCtrl( self._folder_box )
        
        self._check_regularly = QW.QCheckBox( self._folder_box )
        
        self._period = ClientGUITime.TimeDeltaButton( self._folder_box, min = 3 * 60, days = True, hours = True, minutes = True )
        
        self._paused = QW.QCheckBox( self._folder_box )
        
        self._check_now = QW.QCheckBox( self._folder_box )
        
        self._show_working_popup = QW.QCheckBox( self._folder_box )
        self._publish_files_to_popup_button = QW.QCheckBox( self._folder_box )
        self._publish_files_to_page = QW.QCheckBox( self._folder_box )
        
        self._file_seed_cache_button = ClientGUIFileSeedCache.FileSeedCacheButton( self._folder_box, HG.client_controller, self._import_folder.GetFileSeedCache, file_seed_cache_set_callable = self._import_folder.SetFileSeedCache )
        
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
                
            
            choice.currentIndexChanged.connect( self._CheckLocations )
            
            return choice
            
        
        self._action_successful = create_choice()
        self._location_successful = QP.DirPickerCtrl( self._file_box )
        
        self._action_redundant = create_choice()
        self._location_redundant = QP.DirPickerCtrl( self._file_box )
        
        self._action_deleted = create_choice()
        self._location_deleted = QP.DirPickerCtrl( self._file_box )
        
        self._action_failed = create_choice()
        self._location_failed = QP.DirPickerCtrl( self._file_box )
        
        #
        
        self._filename_tagging_options_box = ClientGUICommon.StaticBox( self, 'metadata import' )
        
        filename_tagging_options_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._filename_tagging_options_box )
        
        self._filename_tagging_options = ClientGUIListCtrl.BetterListCtrl( filename_tagging_options_panel, CGLC.COLUMN_LIST_FILENAME_TAGGING_OPTIONS.ID, 5, self._ConvertFilenameTaggingOptionsToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditFilenameTaggingOptions )
        
        filename_tagging_options_panel.SetListCtrl( self._filename_tagging_options )
        
        filename_tagging_options_panel.AddButton( 'add', self._AddFilenameTaggingOptions )
        filename_tagging_options_panel.AddButton( 'edit', self._EditFilenameTaggingOptions, enabled_only_on_selection = True )
        filename_tagging_options_panel.AddDeleteButton()
        
        metadata_routers = self._import_folder.GetMetadataRouters()
        allowed_importer_classes = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT, ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON ]
        allowed_exporter_classes = [ ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs ]
        
        self._metadata_routers_button = ClientGUIMetadataMigration.SingleFileMetadataRoutersButton( self, metadata_routers, allowed_importer_classes, allowed_exporter_classes )
        
        services_manager = HG.client_controller.services_manager
        
        #
        
        self._name.setText( name )
        self._path.SetPath( path )
        
        self._check_regularly.setChecked( check_regularly )
        
        self._period.SetValue( period )
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
            
        
        good_tag_service_keys_to_filename_tagging_options = { service_key : filename_tagging_options for ( service_key, filename_tagging_options ) in list(tag_service_keys_to_filename_tagging_options.items()) if HG.client_controller.services_manager.ServiceExists( service_key ) }
        
        self._filename_tagging_options.AddDatas( list(good_tag_service_keys_to_filename_tagging_options.items()) )
        
        self._filename_tagging_options.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'folder path: ', self._path ) )
        rows.append( ( 'currently paused (if set, will not ever do any work): ', self._paused ) )
        rows.append( ( 'check regularly?: ', self._check_regularly ) )
        rows.append( ( 'check period: ', self._period ) )
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
        
    
    def _AddFilenameTaggingOptions( self ):
        
        service_key = ClientGUIDialogsQuick.SelectServiceKey( HC.REAL_TAG_SERVICES )
        
        if service_key is None:
            
            return
            
        
        existing_service_keys = { service_key for ( service_key, filename_tagging_options ) in self._filename_tagging_options.GetData() }
        
        if service_key in existing_service_keys:
            
            QW.QMessageBox.critical( self, 'Error', 'You already have an entry for that service key! Please try editing it instead!' )
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit filename tagging options' ) as dlg:
            
            filename_tagging_options = TagImportOptions.FilenameTaggingOptions()
            
            panel = ClientGUIImport.EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                filename_tagging_options = panel.GetValue()
                
                self._filename_tagging_options.AddDatas( [ ( service_key, filename_tagging_options ) ] )
                
                self._filename_tagging_options.Sort()
                
            
        
    
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
            
            QW.QMessageBox.warning( self, 'Warning', 'The path you have entered--"'+path+'"--does not exist! The dialog will not force you to correct it, but this import folder will do no work as long as the location is missing!' )
            
        
        if HC.BASE_DIR.startswith( path ) or HG.client_controller.GetDBDir().startswith( path ):
            
            raise HydrusExceptions.VetoException( 'You cannot set an import path that includes your install or database directory!' )
            
        
        if self._action_successful.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_successful.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your successful file move location!' )
                
            
            if not os.path.exists( path ):
                
                QW.QMessageBox.warning( self, 'Warning', 'The path you have entered for your successful file move location--"'+path+'"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_redundant.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_redundant.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your redundant file move location!' )
                
            
            if not os.path.exists( path ):
                
                QW.QMessageBox.warning( self, 'Warning', 'The path you have entered for your redundant file move location--"'+path+'"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_deleted.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_deleted.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your deleted file move location!' )
                
            
            if not os.path.exists( path ):
                
                QW.QMessageBox.warning( self, 'Warning', 'The path you have entered for your deleted file move location--"'+path+'"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
        if self._action_failed.GetValue() == CC.IMPORT_FOLDER_MOVE:
            
            path = self._location_failed.GetPath()
            
            if path in ( '', None ):
                
                raise HydrusExceptions.VetoException( 'You must enter a path for your failed file move location!' )
                
            
            if not os.path.exists( path ):
                
                QW.QMessageBox.warning( self, 'Warning', 'The path you have entered for your failed file move location--"'+path+'"--does not exist! The dialog will not force you to correct it, but you should not let this import folder run until you have corrected or created it!' )
                
            
        
    
    def _ConvertFilenameTaggingOptionsToListCtrlTuples( self, data ):
        
        ( service_key, filename_tagging_options ) = data
        
        name = HG.client_controller.services_manager.GetName( service_key )
        
        display_tuple = ( name, )
        sort_tuple = ( name, )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditFilenameTaggingOptions( self ):
        
        edited_datas = []
        
        selected_data = self._filename_tagging_options.GetData( only_selected = True )
        
        for data in selected_data:
            
            ( service_key, filename_tagging_options ) = data
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit filename tagging options' ) as dlg:
                
                panel = ClientGUIImport.EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._filename_tagging_options.DeleteDatas( ( data, ) )
                    
                    filename_tagging_options = panel.GetValue()
                    
                    new_data = ( service_key, filename_tagging_options )
                    
                    self._filename_tagging_options.AddDatas( [ new_data ] )
                    
                    edited_datas.append( new_data )
                    
                else:
                    
                    break
                    
                
            
        
        self._filename_tagging_options.SelectDatas( edited_datas )
        
    
    def _UpdateCheckRegularly( self ):
        
        if self._check_regularly.isChecked():
            
            self._period.setEnabled( True )
            
        else:
            
            self._period.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        self._CheckValid()
        
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
        
        self._import_folder.SetTuple( name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
        
        metadata_routers = self._metadata_routers_button.GetValue()
        
        self._import_folder.SetMetadataRouters( metadata_routers )
        
        return self._import_folder
        
