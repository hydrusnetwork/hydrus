import os
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.exporting import ClientExportingFiles
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMetadataMigration
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationTest
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchFileSearchContext

class EditExportFoldersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folders ):
        
        super().__init__( parent )
        
        self._export_folders_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXPORT_FOLDERS.ID, self._ConvertExportFolderToDisplayTuple, self._ConvertExportFolderToSortTuple )
        
        self._export_folders = ClientGUIListCtrl.BetterListCtrlTreeView( self._export_folders_panel, 6, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._export_folders_panel.SetListCtrl( self._export_folders )
        
        self._export_folders_panel.AddButton( 'add', self._AddFolder )
        self._export_folders_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._export_folders_panel.AddDeleteButton()
        
        #
        
        self._export_folders.AddDatas( export_folders )
        
        self._export_folders.Sort()
        
        vbox = QP.VBoxLayout()
        
        intro = 'Here you can set the client to regularly export a certain query to a particular location.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,intro), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._export_folders_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddFolder( self ):
        
        new_options = CG.client_controller.new_options
        
        phrase = new_options.GetString( 'export_phrase' )
        
        name = 'export folder'
        path = ''
        export_type = HC.EXPORT_FOLDER_TYPE_REGULAR
        delete_from_client_after_export = False
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context )
        
        metadata_routers = new_options.GetDefaultExportFilesMetadataRouters()
        
        if len( metadata_routers ) > 0:
            
            message = 'You have some default metadata sidecar settings, most likely from a previous file export. They look like this:'
            message += '\n' * 2
            message += '\n'.join( [ router.ToString( pretty = True ) for router in metadata_routers ] )
            message += '\n' * 2
            message += 'Do you want these in the new export folder?'

            ( result, cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, no_label = 'no, I want an empty sidecar list', check_for_cancelled = True )
            
            if cancelled:
                
                return
                
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                metadata_routers = []
                
            
        
        period = 86400
        
        export_folder = ClientExportingFiles.ExportFolder(
            name,
            path,
            export_type = export_type,
            delete_from_client_after_export = delete_from_client_after_export,
            file_search_context = file_search_context,
            metadata_routers = metadata_routers,
            period = period,
            phrase = phrase
        )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folder' ) as dlg:
            
            panel = EditExportFolderPanel( dlg, export_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                export_folder = panel.GetValue()
                
                export_folder.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
                
                self._export_folders.AddData( export_folder, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertExportFolderToDisplayTuple( self, export_folder: ClientExportingFiles.ExportFolder ):
        
        ( name, path, export_type, delete_from_client_after_export, export_symlinks, file_search_context, run_regularly, period, phrase, last_checked, run_now ) = export_folder.ToTuple()
        
        pretty_export_type = 'regular'
        
        if export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            pretty_export_type = 'synchronise'
            
        
        if delete_from_client_after_export:
            
            pretty_export_type += ' and deleting from the client!'
            
        
        pretty_file_search_context = ', '.join( predicate.ToString( with_count = False ) for predicate in file_search_context.GetPredicates() )
        
        if run_regularly:
            
            pretty_period = HydrusTime.TimeDeltaToPrettyTimeDelta( period )
            
        else:
            
            pretty_period = 'not running regularly'
            
        
        if run_now:
            
            pretty_period += ' (running after dialog ok)'
            
        
        last_error = export_folder.GetLastError()
        
        return ( name, path, pretty_export_type, pretty_file_search_context, pretty_period, phrase, last_error )
        
    
    _ConvertExportFolderToSortTuple = _ConvertExportFolderToDisplayTuple
    
    def _Edit( self ):
        
        export_folder: typing.Optional[ ClientExportingFiles.ExportFolder ] = self._export_folders.GetTopSelectedData()
        
        if export_folder is None:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folder' ) as dlg:
            
            panel = EditExportFolderPanel( dlg, export_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_export_folder = panel.GetValue()
                
                if edited_export_folder.GetName() != export_folder.GetName():
                    
                    existing_names = self._GetExistingNames()
                    
                    existing_names.discard( export_folder.GetName() )
                    
                    edited_export_folder.SetNonDupeName( existing_names, do_casefold = True )
                    
                
                self._export_folders.ReplaceData( export_folder, edited_export_folder, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        existing_names = { export_folder.GetName() for export_folder in self._export_folders.GetData() }
        
        return existing_names
        
    
    def GetValue( self ):
        
        export_folders = self._export_folders.GetData()
        
        return export_folders
        
    
class EditExportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folder: ClientExportingFiles.ExportFolder ):
        
        super().__init__( parent )
        
        self._export_folder = export_folder
        
        ( name, path, export_type, delete_from_client_after_export, export_symlinks, file_search_context, run_regularly, period, phrase, self._last_checked, run_now ) = self._export_folder.ToTuple()
        
        self._path_box = ClientGUICommon.StaticBox( self, 'name and location' )
        
        self._name = QW.QLineEdit( self._path_box )
        
        self._path = QP.DirPickerCtrl( self._path_box )
        
        #
        
        self._type_box = ClientGUICommon.StaticBox( self, 'type of export' )
        
        self._type = ClientGUICommon.BetterChoice( self._type_box )
        self._type.addItem( 'regular', HC.EXPORT_FOLDER_TYPE_REGULAR )
        self._type.addItem( 'synchronise', HC.EXPORT_FOLDER_TYPE_SYNCHRONISE )
        
        self._delete_from_client_after_export = QW.QCheckBox( self._type_box )
        self._delete_from_client_after_export.setObjectName( 'HydrusWarning' )
        
        self._export_symlinks = QW.QCheckBox( self._type_box )
        self._export_symlinks.setObjectName( 'HydrusWarning' )
        
        if HC.PLATFORM_WINDOWS:
            
            self._export_symlinks.setToolTip( ClientGUIFunctions.WrapToolTip( 'You probably need to run hydrus as Admin for this to work on Windows.' ) )
            
        
        #
        
        self._period_box = ClientGUICommon.StaticBox( self, 'export period' )
        
        self._period = ClientGUITime.TimeDeltaButton( self._period_box, min = 3 * 60, days = True, hours = True, minutes = True )
        
        self._run_regularly = QW.QCheckBox( self._period_box )
        
        self._run_now = QW.QCheckBox( self._period_box )
        
        self._show_working_popup = QW.QCheckBox( self._period_box )
        
        #
        
        self._query_box = ClientGUICommon.StaticBox( self, 'query to export' )
        
        self._page_key = b'export folders placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._query_box, self._page_key, file_search_context, allow_all_known_files = False, force_system_everything = True )
        
        #
        
        self._phrase_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = QW.QLineEdit( self._phrase_box )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._phrase_box )
        
        #
        
        self._metadata_routers_box = ClientGUICommon.StaticBox( self, 'sidecar exporting' )
        
        self._overwrite_sidecars_on_next_run = QW.QCheckBox( self._metadata_routers_box )
        self._always_overwrite_sidecars = QW.QCheckBox( self._metadata_routers_box )
        
        metadata_routers = export_folder.GetMetadataRouters()
        allowed_importer_classes = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaNotes, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps ]
        allowed_exporter_classes = [ ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ]
        self._test_context_factory = ClientGUIMetadataMigrationTest.MigrationTestContextFactoryMedia( [] )
        
        self._metadata_routers_button = ClientGUIMetadataMigration.SingleFileMetadataRoutersButton( self._metadata_routers_box, metadata_routers, allowed_importer_classes, allowed_exporter_classes, self._test_context_factory )
        
        self._update_test_context_factory_button = ClientGUICommon.BetterButton( self._metadata_routers_box, 'update test example files', self._UpdateTestExampleFiles )
        
        #
        
        self._name.setText( name )
        
        self._path.SetPath( path )
        
        self._type.SetValue( export_type )
        
        self._delete_from_client_after_export.setChecked( delete_from_client_after_export )
        
        self._export_symlinks.setChecked( export_symlinks )
        
        self._period.SetValue( period )
        
        self._run_regularly.setChecked( run_regularly )
        
        self._run_now.setChecked( run_now )
        
        self._show_working_popup.setChecked( export_folder.ShowWorkingPopup() )
        
        self._pattern.setText( phrase )
        
        self._overwrite_sidecars_on_next_run.setChecked( export_folder.GetOverwriteSidecarsOnNextRun() )
        self._always_overwrite_sidecars.setChecked( export_folder.GetAlwaysOverwriteSidecars() )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'folder path: ', self._path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._path_box, rows )
        
        self._path_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        text = '''regular - try to export the files to the directory, overwriting if the filesize if different

synchronise - try to export the files to the directory, overwriting if the filesize if different, and delete anything else in the directory

If you select synchronise, be careful!'''
        
        st = ClientGUICommon.BetterStaticText( self._type_box, label = text )
        st.setWordWrap( True )
        
        self._type_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._type_box.Add( self._type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'trash files in hydrus client after export: ', self._delete_from_client_after_export ) )
        rows.append( ( 'EXPERIMENTAL: export symlinks', self._export_symlinks ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._type_box, rows )
        
        self._type_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._query_box.Add( self._tag_autocomplete )
        
        rows = []
        
        rows.append( ( 'run regularly?: ', self._run_regularly ) )
        rows.append( self._period )
        rows.append( ( 'show popup when working regularly?: ', self._show_working_popup ) )
        rows.append( ( 'run on dialog ok: ', self._run_now ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._period_box, rows )
        
        self._period_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        phrase_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( phrase_hbox, self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( phrase_hbox, self._examples, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._phrase_box.Add( phrase_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        label = 'By default, an export folder will not update pre-existing sidecar files. If you change the sidecar actions here, or if the metadata has changed and you want those updates, hit the "overwrite all sidecars on next run" checkbox.'
        label += '\n\n'
        label += 'You can force the export folder to regenerate all your sidecars on every run, but this is an expensive operation. It is only appropriate for an export folder that runs manually or rarely.'
        label += '\n\n'
        label += 'DO NOT SET YOUR EXPORT FOLDER TO REGEN ALL YOUR SIDECARS EVERY THIRTY MINUTES.'
        
        st = ClientGUICommon.BetterStaticText( self._metadata_routers_box, label = label )
        st.setWordWrap( True )
        
        self._metadata_routers_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'overwrite all sidecars on next run: ', self._overwrite_sidecars_on_next_run ) )
        rows.append( ( 'DANGEROUS: always overwrite all sidecars on every run: ', self._always_overwrite_sidecars ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._period_box, rows )
        
        self._metadata_routers_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._metadata_routers_box.Add( self._metadata_routers_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._metadata_routers_box.Add( self._update_test_context_factory_button, CC.FLAGS_ON_RIGHT )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._type_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._period_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._query_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._phrase_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._metadata_routers_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateTypeDeleteUI()
        self._UpdateRunRegularly()
        
        self._type.currentIndexChanged.connect( self._UpdateTypeDeleteUI )
        self._delete_from_client_after_export.clicked.connect( self.EventDeleteFilesAfterExport )
        self._run_regularly.clicked.connect( self._UpdateRunRegularly )
        
        self._tag_autocomplete.searchChanged.connect( self._SearchUpdated )
        
        self._SearchUpdated()
        
    
    def _SearchUpdated( self ):
        
        self._update_test_context_factory_button.setText( 'update test example files' )
        
        self._update_test_context_factory_button.setEnabled( True )
        
    
    def _UpdateRunRegularly( self ):
        
        run_regularly = self._run_regularly.isChecked()
        
        self._period.setEnabled( run_regularly )
        self._show_working_popup.setEnabled( run_regularly )
        
    
    def _UpdateTestExampleFiles( self ):
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        def work_callable():
            
            sort_by = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, limit_sort_by = sort_by )
            
            query_hash_ids = list( query_hash_ids )[:ClientGUIMetadataMigrationTest.HOW_MANY_EXAMPLE_OBJECTS_TO_USE]
            
            media_results = CG.client_controller.Read( 'media_results_from_ids', query_hash_ids )
            
            return media_results
            
        
        def publish_callable( media_results ):
            
            self._test_context_factory.SetExampleMediaResults( media_results )
            
            self._update_test_context_factory_button.setText( f'got {HydrusNumbers.ToHumanInt(len( media_results))} files!' )
            
        
        self._update_test_context_factory_button.setEnabled( False )
        
        self._update_test_context_factory_button.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _UpdateTypeDeleteUI( self ):
        
        if self._type.GetValue() == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            self._delete_from_client_after_export.setEnabled( False )
            
            if self._delete_from_client_after_export.isChecked():
                
                self._delete_from_client_after_export.setChecked( False )
                
            
        else:
            
            self._delete_from_client_after_export.setEnabled( True )
            
        
    
    def UserIsOKToOK( self ):
        
        if self._delete_from_client_after_export.isChecked():
            
            message = 'You have set this export folder to delete the files from the client (send them to trash) after export! Are you absolutely sure this is what you want?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def EventDeleteFilesAfterExport( self ):
        
        if self._delete_from_client_after_export.isChecked():
            
            ClientGUIDialogsMessage.ShowWarning( self, 'This will delete the exported files from your client (send them to trash) after the export! If you do not know what this means, uncheck it!' )
            
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        path = self._path.GetPath()
        
        export_type = self._type.GetValue()
        
        delete_from_client_after_export = self._delete_from_client_after_export.isChecked()

        export_symlinks = self._export_symlinks.isChecked()
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        metadata_routers = self._metadata_routers_button.GetValue()
        
        run_regularly = self._run_regularly.isChecked()
        
        period = self._period.GetValue()
        
        if self._path.GetPath() in ( '', None ):
            
            raise HydrusExceptions.VetoException( 'You must enter a folder path to export to!' )
            
        
        phrase = self._pattern.text()
        
        try:
            
            ClientExportingFiles.ParseExportPhrase( phrase )
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( 'Could not parse that export phrase! ' + str( e ) )
            
        
        run_now = self._run_now.isChecked()
        
        last_error = self._export_folder.GetLastError()
        
        show_working_popup = self._show_working_popup.isChecked()
        
        export_folder = ClientExportingFiles.ExportFolder(
            name,
            path = path,
            export_type = export_type,
            delete_from_client_after_export = delete_from_client_after_export,
            export_symlinks = export_symlinks,
            file_search_context = file_search_context,
            metadata_routers = metadata_routers,
            run_regularly = run_regularly,
            period = period,
            phrase = phrase,
            last_checked = self._last_checked,
            run_now = run_now,
            last_error = last_error,
            show_working_popup = show_working_popup
        )
        
        export_folder.SetOverwriteSidecarsOnNextRun( self._overwrite_sidecars_on_next_run.isChecked() )
        export_folder.SetAlwaysOverwriteSidecars( self._always_overwrite_sidecars.isChecked() )
        
        return export_folder
        
    

class ReviewExportFilesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, flat_media, do_export_and_then_quit = False ):
        
        super().__init__( parent )
        
        tag_presentation_location = CC.TAG_PRESENTATION_SEARCH_PAGE
        
        new_options = CG.client_controller.new_options
        
        self._media_to_paths = {}
        self._media_to_number_indices = { media : i + 1 for ( i, media ) in enumerate( flat_media ) }
        self._existing_filenames = set()
        self._last_phrase_used = ''
        self._last_dir_used = ''
        
        self._tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'files\' tags', tag_presentation_location )
        
        t = ClientGUIListBoxes.ListBoxTagsMedia( self._tags_box, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_presentation_location, include_counts = True )
        
        self._tags_box.SetTagsBox( t )
        
        self._tags_box.setMinimumSize( QC.QSize( 220, 300 ) )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EXPORT_FILES.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._paths = ClientGUIListCtrl.BetterListCtrlTreeView( self, 24, model, delete_key_callback = self._DeletePaths )
        
        self._paths.Sort()
        
        self._export_path_box = ClientGUICommon.StaticBox( self, 'export path' )
        
        self._directory_picker = QP.DirPickerCtrl( self._export_path_box )
        self._directory_picker.dirPickerChanged.connect( self._RefreshPaths )
        
        self._open_location = QW.QPushButton( 'open this location', self._export_path_box )
        self._open_location.clicked.connect( self.EventOpenLocation )
        
        self._filenames_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = QW.QLineEdit( self._filenames_box )
        
        self._update = QW.QPushButton( 'update', self._filenames_box )
        self._update.clicked.connect( self._RefreshPaths )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._filenames_box )
        
        self._delete_files_after_export = QW.QCheckBox( 'trash files in hydrus client after export', self )
        self._delete_files_after_export.setObjectName( 'HydrusWarning' )
        
        self._export_symlinks = QW.QCheckBox( 'EXPERIMENTAL: export symlinks', self )
        self._export_symlinks.setObjectName( 'HydrusWarning' )
        
        if HC.PLATFORM_WINDOWS:
            
            self._export_symlinks.setToolTip( ClientGUIFunctions.WrapToolTip( 'You probably need to run hydrus as Admin for this to work on Windows.' ) )
            
        
        metadata_routers = new_options.GetDefaultExportFilesMetadataRouters()
        allowed_importer_classes = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaNotes, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps ]
        allowed_exporter_classes = [ ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ]
        
        example_media_results = [ m.GetMediaResult() for m in list( flat_media )[:ClientGUIMetadataMigrationTest.HOW_MANY_EXAMPLE_OBJECTS_TO_USE] ]
        
        test_context_factory = ClientGUIMetadataMigrationTest.MigrationTestContextFactoryMedia( example_media_results )
        
        self._metadata_routers_button = ClientGUIMetadataMigration.SingleFileMetadataRoutersButton( self, metadata_routers, allowed_importer_classes, allowed_exporter_classes, test_context_factory )
        
        self._export = QW.QPushButton( 'export', self )
        self._export.clicked.connect( self._DoExport )
        
        #
        
        export_path = ClientExportingFiles.GetExportPath()
        
        if export_path is not None:
            
            self._directory_picker.SetPath( export_path )
            
        
        phrase = new_options.GetString( 'export_phrase' )
        
        self._pattern.setText( phrase )
        
        self._paths.SetData( flat_media )
        
        self._delete_files_after_export.setChecked( CG.client_controller.new_options.GetBoolean( 'delete_files_after_export' ) )
        self._delete_files_after_export.clicked.connect( self.EventDeleteFilesChanged )
        
        #
        
        top_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( top_hbox, self._tags_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( top_hbox, self._paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._directory_picker, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._open_location, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._export_path_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._update, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._examples, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._filenames_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( vbox, self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._delete_files_after_export, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._export_symlinks, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._metadata_routers_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._export, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._RefreshTags()
        
        ClientGUIFunctions.SetFocusLater( self._export )
        
        self._paths.selectionModel().selectionChanged.connect( self._RefreshTags )
        self._metadata_routers_button.valueChanged.connect( self._MetadataRoutersUpdated )
        
        if do_export_and_then_quit:
            
            CG.client_controller.CallAfterQtSafe( self, 'doing export before dialog quit', self._DoExport, True )
            
        
    
    def _ConvertDataToDisplayTuple( self, media ):
        
        directory = self._directory_picker.GetPath()
        
        number = self._media_to_number_indices[ media ]
        mime = media.GetMime()
        
        try:
            
            path = self._GetPath( media )
            
        except Exception as e:
            
            path = str( e )
            
        
        pretty_number = HydrusNumbers.ToHumanInt( number )
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        pretty_path = path
        
        if not path.startswith( directory ):
            
            pretty_path = 'INVALID, above destination directory: ' + path
            
        
        return ( pretty_number, pretty_mime, pretty_path )
        
    
    def _ConvertDataToSortTuple( self, media ):
        
        directory = self._directory_picker.GetPath()
        
        number = self._media_to_number_indices[ media ]
        mime = media.GetMime()
        
        try:
            
            path = self._GetPath( media )
            
        except Exception as e:
            
            path = str( e )
            
        
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        return ( number, pretty_mime, path )
        
    
    def _DeletePaths( self ):
        
        if not self._paths.HasSelected():
            
            return
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._paths.DeleteSelected()
            
            kept_media = set( self._paths.GetData() )
            
            media_in_correct_order = [ media for ( i, media ) in sorted( ( ( i, media ) for ( media, i ) in self._media_to_number_indices.items() ) ) ]
            
            i = 1
            self._media_to_number_indices = {}
            
            for media in media_in_correct_order:
                
                if media in kept_media:
                    
                    self._media_to_number_indices[ media ] = i
                    
                    i += 1
                    
                
            
            self._paths.UpdateDatas()
            
        
    
    def _DoExport( self, quit_afterwards = False ):
        
        delete_afterwards = self._delete_files_after_export.isChecked()
        export_symlinks = self._export_symlinks.isChecked() and not delete_afterwards
        
        if quit_afterwards:
            
            message = 'Export as shown?'
            
            if delete_afterwards:
                
                message += '\n' * 2
                message += 'THE FILES WILL BE SENT TO THE TRASH IN THE CLIENT AFTERWARDS'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                self.parentWidget().close()
                
                return
                
            
        elif delete_afterwards:
            
            message = 'THE FILES WILL BE SENT TO THE TRASH IN THE CLIENT AFTERWARDS'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        self._RefreshPaths()
        
        directory = self._directory_picker.GetPath()
        
        HydrusPaths.MakeSureDirectoryExists( directory )
        
        pattern = self._pattern.text()
        
        CG.client_controller.new_options.SetString( 'export_phrase', pattern )
        
        try:
            
            terms = ClientExportingFiles.ParseExportPhrase( pattern )
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowWarning( self, f'Problem parsing export phrase!\n\n{e}' )
            
            return
            
        
        metadata_routers = self._metadata_routers_button.GetValue()
        
        client_files_manager = CG.client_controller.client_files_manager
        
        self._export.setEnabled( False )
        
        flat_media = self._paths.GetData()
        
        to_do = [ ( media, self._GetPath( media ) ) for media in flat_media ]
        
        def qt_update_label( text ):
            
            if not QP.isValid( self ) or not QP.isValid( self._export ) or not self._export:
                
                return
                
            
            self._export.setText( text )
            
        
        def qt_done( quit_afterwards ):
            
            if not QP.isValid( self ) or not QP.isValid( self._export ) or not self._export:
                
                return
                
            
            self._export.setEnabled( True )
            
            if quit_afterwards:
                
                CG.client_controller.CallAfter( self, self.parentWidget().close )
                
            
        
        def do_it( directory, metadata_routers, delete_afterwards, export_symlinks, quit_afterwards, media_to_number_indices ):
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            job_status.SetStatusTitle( 'file export' )
            
            CG.client_controller.pub( 'message', job_status )
            
            pauser = HydrusThreading.BigJobPauser()
            
            actually_done_ok = []
            
            num_to_do = len( to_do )
            
            for ( index, ( media, dest_path ) ) in enumerate( to_do ):
                
                number = media_to_number_indices[ media ]
                
                if job_status.IsCancelled():
                    
                    break
                    
                
                try:
                    
                    x_of_y = HydrusNumbers.ValueRangeToPrettyString( index, num_to_do )
                    
                    job_status.SetStatusText( 'Exporting: {}'.format( x_of_y ) )
                    job_status.SetGauge( index, num_to_do )
                    
                    CG.client_controller.CallAfter( self, qt_update_label, x_of_y )
                    
                    hash = media.GetHash()
                    mime = media.GetMime()
                    
                    dest_path = os.path.normpath( dest_path )
                    
                    if not dest_path.startswith( directory ):
                        
                        raise Exception( 'It seems a destination path was above the main export directory! The file was "{}" and its destination path was "{}".'.format( hash.hex(), dest_path ) )
                        
                    
                    path_dir = os.path.dirname( dest_path )
                    
                    HydrusPaths.MakeSureDirectoryExists( path_dir )
                    
                    for metadata_router in metadata_routers:
                        
                        metadata_router.Work( media.GetMediaResult(), dest_path )
                        
                    
                    try:
                        
                        source_path = client_files_manager.GetFilePath( hash, mime )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        raise Exception( f'When trying to export {hash.hex()}, I discovered that it was actually missing from your client! The export job should stop now. You should go to _database->file maintenance_ and set up a scan for missing files!' )
                        
                    
                    if export_symlinks:
                        
                        try:
                            
                            os.symlink( source_path, dest_path )
                            
                        except OSError as e:
                            
                            if HC.PLATFORM_WINDOWS:
                                
                                raise Exception( 'The symlink creation failed. It may be you need to run hydrus as Admin for this to work!' ) from e
                                
                            else:
                                
                                raise
                                
                            
                    else:
                        
                        HydrusPaths.MirrorFile( source_path, dest_path )
                        
                        HydrusPaths.TryToGiveFileNicePermissionBits( dest_path )
                        
                    
                    actually_done_ok.append( media )
                    
                except Exception as e:
                    
                    if QP.isValid( self ):
                        
                        win = self
                        
                    else:
                        
                        win = CG.client_controller.GetMainTLW()
                        
                    
                    HydrusData.PrintException( e, do_wait = False )
                    
                    ClientGUIDialogsMessage.ShowCritical( win, 'Problem during file export!', f'Encountered a problem while attempting to export file #{HydrusNumbers.ToHumanInt( number )}:\n\n{e}' )
                    
                    break
                    
                
                pauser.Pause()
                
            
            if not job_status.IsCancelled() and delete_afterwards:
                
                CG.client_controller.CallAfter( self, qt_update_label, 'deleting' )
                
                actually_done_media_results = [ m.GetMediaResult() for m in actually_done_ok ]
                
                for ( num_done, num_to_do, chunk_of_deletee_media_results ) in HydrusLists.SplitListIntoChunksRich( actually_done_media_results, 64 ):
                    
                    reason = 'Deleted after manual export to "{}".'.format( directory )
                    
                    hashes = [ media_result.GetHash() for media_result in chunk_of_deletee_media_results ]
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = reason )
                    
                    CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, content_update ) )
                    
                
            
            job_status.DeleteGauge()
            job_status.SetStatusText( 'Done!' )
            
            job_status.FinishAndDismiss( 5 )
            
            CG.client_controller.CallAfter( self, qt_update_label, 'done!' )
            
            time.sleep( 1 )
            
            CG.client_controller.CallAfter( self, qt_update_label, 'export' )
            
            CG.client_controller.CallAfter( self, qt_done, quit_afterwards )
            
        
        CG.client_controller.CallToThread( do_it, directory, metadata_routers, delete_afterwards, export_symlinks, quit_afterwards, self._media_to_number_indices )
        
    
    def _GetPath( self, media ):
        
        if media in self._media_to_paths:
            
            return self._media_to_paths[ media ]
            
        
        directory = self._directory_picker.GetPath()
        
        pattern = self._pattern.text()
        
        terms = ClientExportingFiles.ParseExportPhrase( pattern )

        number = self._media_to_number_indices[ media ]
        
        filename = ClientExportingFiles.GenerateExportFilename( directory, media, terms, number, do_not_use_filenames = self._existing_filenames )
        
        path = os.path.join( directory, filename )
        
        path = os.path.normpath( path )
        
        self._existing_filenames.add( filename )
        self._media_to_paths[ media ] = path
        
        return path
        
    
    def _MetadataRoutersUpdated( self ):
        
        metadata_routers = self._metadata_routers_button.GetValue()
        
        CG.client_controller.new_options.SetDefaultExportFilesMetadataRouters( metadata_routers )
        
    
    def _RefreshPaths( self ):
        
        pattern = self._pattern.text()
        dir_path = self._directory_picker.GetPath()
        
        if pattern == self._last_phrase_used and dir_path == self._last_dir_used:
            
            return
            
        
        self._last_phrase_used = pattern
        self._last_dir_used = dir_path
        
        CG.client_controller.new_options.SetString( 'export_phrase', pattern )
        
        self._existing_filenames = set()
        self._media_to_paths = {}
        
        self._paths.UpdateDatas()
        
    
    def _RefreshTags( self ):
        
        flat_media = self._paths.GetData( only_selected = True )
        
        if len( flat_media ) == 0:
            
            flat_media = self._paths.GetData()
            
        
        self._tags_box.SetTagsByMedia( flat_media )
        
    
    def EventExport( self, event ):
        
        self._DoExport()
        
    
    def EventDeleteFilesChanged( self ):
        
        value = self._delete_files_after_export.isChecked()
        
        CG.client_controller.new_options.SetBoolean( 'delete_files_after_export', value )
        
        if value:
            
            self._export_symlinks.setChecked( False )
            
        
    
    def EventOpenLocation( self ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            if not os.path.exists( directory ):
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Does not exist!', 'That location does not seem to exist!' )
                
                return
                
            
            HydrusPaths.LaunchDirectory( directory )
            
        
    
