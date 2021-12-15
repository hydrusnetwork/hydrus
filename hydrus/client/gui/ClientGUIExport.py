import os
import time
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientExporting
from hydrus.client import ClientSearch
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags

class EditExportFoldersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folders ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._export_folders_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._export_folders = ClientGUIListCtrl.BetterListCtrl( self._export_folders_panel, CGLC.COLUMN_LIST_EXPORT_FOLDERS.ID, 6, self._ConvertExportFolderToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        self._export_folders_panel.SetListCtrl( self._export_folders )
        
        self._export_folders_panel.AddButton( 'add', self._AddFolder )
        self._export_folders_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
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
        
        new_options = HG.client_controller.new_options
        
        phrase = new_options.GetString( 'export_phrase' )
        
        name = 'export folder'
        path = ''
        export_type = HC.EXPORT_FOLDER_TYPE_REGULAR
        delete_from_client_after_export = False
        
        default_local_file_service_key = HG.client_controller.services_manager.GetDefaultLocalFileServiceKey()
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ default_local_file_service_key ] )
        
        file_search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context )
        
        period = 15 * 60
        
        export_folder = ClientExporting.ExportFolder( name, path, export_type = export_type, delete_from_client_after_export = delete_from_client_after_export, file_search_context = file_search_context, period = period, phrase = phrase )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folder' ) as dlg:
            
            panel = EditExportFolderPanel( dlg, export_folder )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                export_folder = panel.GetValue()
                
                export_folder.SetNonDupeName( self._GetExistingNames() )
                
                self._export_folders.AddDatas( ( export_folder, ) )
                
            
        
    
    def _ConvertExportFolderToListCtrlTuples( self, export_folder: ClientExporting.ExportFolder ):
        
        ( name, path, export_type, delete_from_client_after_export, file_search_context, run_regularly, period, phrase, last_checked, paused, run_now ) = export_folder.ToTuple()
        
        if export_type == HC.EXPORT_FOLDER_TYPE_REGULAR:
            
            pretty_export_type = 'regular'
            
        elif export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            pretty_export_type = 'synchronise'
            
        
        if delete_from_client_after_export:
            
            pretty_export_type += ' and deleting from the client!'
            
        
        pretty_file_search_context = ', '.join( predicate.ToString( with_count = False ) for predicate in file_search_context.GetPredicates() )
        
        if run_regularly:
            
            pretty_period = HydrusData.TimeDeltaToPrettyTimeDelta( period )
            
        else:
            
            pretty_period = 'not running regularly'
            
        
        if run_now:
            
            pretty_period += ' (running after dialog ok)'
            
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        pretty_phrase = phrase
        
        last_error = export_folder.GetLastError()
        
        display_tuple = ( name, path, pretty_export_type, pretty_file_search_context, pretty_paused, pretty_period, pretty_phrase, last_error )
        
        sort_tuple = ( name, path, pretty_export_type, pretty_file_search_context, paused, period, phrase, last_error )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        export_folders = self._export_folders.GetData( only_selected = True )
        
        for export_folder in export_folders:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folder' ) as dlg:
                
                panel = EditExportFolderPanel( dlg, export_folder )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_export_folder = panel.GetValue()
                    
                    self._export_folders.DeleteDatas( ( export_folder, ) )
                    
                    edited_export_folder.SetNonDupeName( self._GetExistingNames() )
                    
                    self._export_folders.AddDatas( ( edited_export_folder, ) )
                    
                else:
                    
                    return
                    
                
            
        
    
    def _GetExistingNames( self ):
        
        existing_names = { export_folder.GetName() for export_folder in self._export_folders.GetData() }
        
        return existing_names
        
    
    def GetValue( self ):
        
        export_folders = self._export_folders.GetData()
        
        return export_folders
        
    
class EditExportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, export_folder: ClientExporting.ExportFolder ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._export_folder = export_folder
        
        ( name, path, export_type, delete_from_client_after_export, file_search_context, run_regularly, period, phrase, self._last_checked, paused, run_now ) = self._export_folder.ToTuple()
        
        self._path_box = ClientGUICommon.StaticBox( self, 'name and location' )
        
        self._name = QW.QLineEdit( self._path_box )
        
        self._path = QP.DirPickerCtrl( self._path_box )
        
        #
        
        self._type_box = ClientGUICommon.StaticBox( self, 'type of export' )
        
        self._type = ClientGUICommon.BetterChoice( self._type_box )
        self._type.addItem( 'regular', HC.EXPORT_FOLDER_TYPE_REGULAR )
        self._type.addItem( 'synchronise', HC.EXPORT_FOLDER_TYPE_SYNCHRONISE )
        
        self._delete_from_client_after_export = QW.QCheckBox( self._type_box )
        
        #
        
        self._query_box = ClientGUICommon.StaticBox( self, 'query to export' )
        
        self._page_key = 'export folders placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._query_box, self._page_key, file_search_context, allow_all_known_files = False, force_system_everything = True )
        
        #
        
        self._period_box = ClientGUICommon.StaticBox( self, 'export period' )
        
        self._period = ClientGUITime.TimeDeltaButton( self._period_box, min = 3 * 60, days = True, hours = True, minutes = True )
        
        self._run_regularly = QW.QCheckBox( self._period_box )
        
        self._paused = QW.QCheckBox( self._period_box )
        
        self._run_now = QW.QCheckBox( self._period_box )
        
        #
        
        self._phrase_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = QW.QLineEdit( self._phrase_box )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._phrase_box )
        
        #
        
        self._name.setText( name )
        
        self._path.SetPath( path )
        
        self._type.SetValue( export_type )
        
        self._delete_from_client_after_export.setChecked( delete_from_client_after_export )
        
        self._period.SetValue( period )
        
        self._run_regularly.setChecked( run_regularly )
        
        self._paused.setChecked( paused )
        
        self._run_now.setChecked( run_now )
        
        self._pattern.setText( phrase )
        
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
        
        rows.append( ( 'delete files from client after export: ', self._delete_from_client_after_export ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._type_box, rows )
        
        self._type_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._query_box.Add( self._tag_autocomplete )
        
        self._period_box.Add( self._period, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'run regularly?: ', self._run_regularly ) )
        rows.append( ( 'paused: ', self._paused ) )
        rows.append( ( 'run on dialog ok: ', self._run_now ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._period_box, rows )
        
        self._period_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        phrase_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( phrase_hbox, self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( phrase_hbox, self._examples, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._phrase_box.Add( phrase_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._type_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._query_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._period_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._phrase_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateTypeDeleteUI()
        
        self._type.currentIndexChanged.connect( self._UpdateTypeDeleteUI )
        self._delete_from_client_after_export.clicked.connect( self.EventDeleteFilesAfterExport )
        
    
    def _UpdateTypeDeleteUI( self ):
        
        if self._type.GetValue() == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            self._delete_from_client_after_export.setEnabled( False )
            
            if self._delete_from_client_after_export.isChecked():
                
                self._delete_from_client_after_export.setChecked( False )
                
            
        else:
            
            self._delete_from_client_after_export.setEnabled( True )
            
        
    
    def UserIsOKToOK( self ):
        
        if self._delete_from_client_after_export.isChecked():
            
            message = 'You have set this export folder to delete the files from the client after export! Are you absolutely sure this is what you want?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
    def EventDeleteFilesAfterExport( self ):
        
        if self._delete_from_client_after_export.isChecked():
            
            QW.QMessageBox.warning( self, 'Warning', 'This will delete the exported files from your client after the export! If you do not know what this means, uncheck it!' )
            
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        path = self._path.GetPath()
        
        export_type = self._type.GetValue()
        
        delete_from_client_after_export = self._delete_from_client_after_export.isChecked()
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        run_regularly = self._run_regularly.isChecked()
        
        period = self._period.GetValue()
        
        if self._path.GetPath() in ( '', None ):
            
            raise HydrusExceptions.VetoException( 'You must enter a folder path to export to!' )
            
        
        phrase = self._pattern.text()
        
        try:
            
            ClientExporting.ParseExportPhrase( phrase )
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( 'Could not parse that export phrase! ' + str( e ) )
            
        
        run_now = self._run_now.isChecked()
        
        paused = self._paused.isChecked()
        
        last_error = self._export_folder.GetLastError()
        
        export_folder = ClientExporting.ExportFolder(
            name,
            path = path,
            export_type = export_type,
            delete_from_client_after_export = delete_from_client_after_export,
            file_search_context = file_search_context,
            run_regularly = run_regularly,
            period = period,
            phrase = phrase,
            last_checked = self._last_checked,
            paused = paused,
            run_now = run_now,
            last_error = last_error
        )
        
        return export_folder
        
    
class EditSidecarExporterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, sidecar_exporter: ClientExporting.SidecarExporter ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._service_keys_to_tag_data = dict( sidecar_exporter.GetTagData() )
        
        #
        
        # ok, I guess a multi-column list of services, then tag filter and display type options
        # open it, you make a new edit panel type
        
        # add (with test for remaining services), edit, delete
        
        #
        
        # populate that lad
        
        #
        
        vbox = QP.VBoxLayout()
        
        #QP.AddToLayout( vbox, self._tag_data_listctrl, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        sidecar_exporter = ClientExporting.SidecarExporter( service_keys_to_tag_data = self._service_keys_to_tag_data )
        
        return sidecar_exporter
        
    
class EditSidecarExporterTagDataPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_filter: HydrusTags.TagFilter, tag_display_type: int ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        message = 'Filter the tags you want to export here. Anything that passes this filter is exported.'
        
        self._tag_filter = ClientGUITags.TagFilterButton( self, message, tag_filter )
        
        self._tag_display_type = ClientGUICommon.BetterChoice( self )
        
        self._tag_display_type.addItem( 'with siblings and parents applied', ClientTags.TAG_DISPLAY_ACTUAL )
        self._tag_display_type.addItem( 'as the tags are actually stored', ClientTags.TAG_DISPLAY_STORAGE )
        
        #
        
        self._tag_display_type.SetValue( tag_display_type )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Tags to export: ', self._tag_filter ) )
        rows.append( ( 'Type to export: ', self._tag_display_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        tag_filter = self._tag_filter.GetValue()
        tag_display_type = self._tag_display_type.GetValue()
        
        return ( tag_filter, tag_display_type )
        
    
class ReviewExportFilesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, flat_media, do_export_and_then_quit = False ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        new_options = HG.client_controller.new_options
        
        self._media_to_paths = {}
        self._existing_filenames = set()
        self._last_phrase_used = ''
        self._last_dir_used = ''
        
        self._tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'files\' tags' )
        
        services_manager = HG.client_controller.services_manager
        
        self._neighbouring_txt_tag_service_keys = services_manager.FilterValidServiceKeys( new_options.GetKeyList( 'default_neighbouring_txt_tag_service_keys' ) )
        
        t = ClientGUIListBoxes.ListBoxTagsMedia( self._tags_box, ClientTags.TAG_DISPLAY_ACTUAL, include_counts = True )
        
        self._tags_box.SetTagsBox( t )
        
        self._tags_box.setMinimumSize( QC.QSize( 220, 300 ) )
        
        self._paths = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_EXPORT_FILES.ID, 24, self._ConvertDataToListCtrlTuples, use_simple_delete = True )
        
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
        
        self._delete_files_after_export = QW.QCheckBox( 'delete files from client after export?', self )
        self._delete_files_after_export.setObjectName( 'HydrusWarning' )
        
        self._export_symlinks = QW.QCheckBox( 'EXPERIMENTAL: export symlinks', self )
        self._export_symlinks.setObjectName( 'HydrusWarning' )
        
        text = 'This will export all the files\' tags, newline separated, into .txts beside the files themselves.'
        
        self._export_tag_txts_services_button = ClientGUICommon.BetterButton( self, 'set .txt services', self._SetTxtServices )
        
        self._export_tag_txts = QW.QCheckBox( 'export tags to .txt files?', self )
        self._export_tag_txts.setToolTip( text )
        self._export_tag_txts.clicked.connect( self.EventExportTagTxtsChanged )
        
        self._export = QW.QPushButton( 'export', self )
        self._export.clicked.connect( self._DoExport )
        
        #
        
        export_path = ClientExporting.GetExportPath()
        
        if export_path is not None:
            
            self._directory_picker.SetPath( export_path )
            
        
        phrase = new_options.GetString( 'export_phrase' )
        
        self._pattern.setText( phrase )
        
        if len( self._neighbouring_txt_tag_service_keys ) > 0:
            
            self._export_tag_txts.setChecked( True )
            
        
        self._paths.SetData( list( enumerate( flat_media ) ) )
        
        self._delete_files_after_export.setChecked( HG.client_controller.new_options.GetBoolean( 'delete_files_after_export' ) )
        self._delete_files_after_export.clicked.connect( self.EventDeleteFilesChanged )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._export_symlinks.setVisible( False )
            
        
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
        
        txt_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( txt_hbox, self._export_tag_txts_services_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( txt_hbox, self._export_tag_txts, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( vbox, self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._delete_files_after_export, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._export_symlinks, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, txt_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._export, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._RefreshTags()
        
        self._UpdateTxtButton()
        
        ClientGUIFunctions.SetFocusLater( self._export )
        
        self._paths.itemSelectionChanged.connect( self._RefreshTags )
        
        if do_export_and_then_quit:
            
            HG.client_controller.CallAfterQtSafe( self, 'doing export before dialog quit', self._DoExport, True )
            
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        directory = self._directory_picker.GetPath()
        
        ( ordering_index, media ) = data
        
        number = ordering_index
        mime = media.GetMime()
        
        try:
            
            path = self._GetPath( media )
            
        except Exception as e:
            
            path = str( e )
            
        
        pretty_number = HydrusData.ToHumanInt( ordering_index + 1 )
        pretty_mime = HC.mime_string_lookup[ mime ]
        
        pretty_path = path
        
        if not path.startswith( directory ):
            
            pretty_path = 'INVALID, above destination directory: ' + path
            
        
        display_tuple = ( pretty_number, pretty_mime, pretty_path )
        sort_tuple = ( number, pretty_mime, path )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DoExport( self, quit_afterwards = False ):
        
        delete_afterwards = self._delete_files_after_export.isChecked()
        export_symlinks = self._export_symlinks.isChecked() and not delete_afterwards
        
        if quit_afterwards:
            
            message = 'Export as shown?'
            
            if delete_afterwards:
                
                message += os.linesep * 2
                message += 'THE FILES WILL BE DELETED FROM THE CLIENT AFTERWARDS'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                self.parentWidget().close()
                
                return
                
            
        elif delete_afterwards:
            
            message = 'THE FILES WILL BE DELETED FROM THE CLIENT AFTERWARDS'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
        
        self._RefreshPaths()
        
        export_tag_txts = self._export_tag_txts.isChecked()
        
        if self._export_tag_txts.isChecked():
            
            neighbouring_txt_tag_service_keys = self._neighbouring_txt_tag_service_keys
            
        else:
            
            neighbouring_txt_tag_service_keys = []
            
        
        directory = self._directory_picker.GetPath()
        
        HydrusPaths.MakeSureDirectoryExists( directory )
        
        pattern = self._pattern.text()
        
        HG.client_controller.new_options.SetString( 'export_phrase', pattern )
        
        try:
            
            terms = ClientExporting.ParseExportPhrase( pattern )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._export.setEnabled( False )
        
        to_do = self._paths.GetData()
        
        to_do = [ ( ordering_index, media, self._GetPath( media ) ) for ( ordering_index, media ) in to_do ]
        
        num_to_do = len( to_do )
        
        def qt_update_label( text ):
            
            if not QP.isValid( self ) or not QP.isValid( self._export ) or not self._export:
                
                return
                
            
            self._export.setText( text )
            
        
        def qt_done( quit_afterwards ):
            
            if not QP.isValid( self ) or not QP.isValid( self._export ) or not self._export:
                
                return
                
            
            self._export.setEnabled( True )
            
            if quit_afterwards:
                
                QP.CallAfter( self.parentWidget().close )
                
            
        
        def do_it( directory, neighbouring_txt_tag_service_keys, delete_afterwards, export_symlinks, quit_afterwards ):
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetStatusTitle( 'file export' )
            
            HG.client_controller.pub( 'message', job_key )
            
            pauser = HydrusData.BigJobPauser()
            
            for ( index, ( ordering_index, media, path ) ) in enumerate( to_do ):
                
                if job_key.IsCancelled():
                    
                    break
                    
                
                try:
                    
                    x_of_y = HydrusData.ConvertValueRangeToPrettyString( index + 1, num_to_do )
                    
                    job_key.SetVariable( 'popup_text_1', 'Done {}'.format( x_of_y ) )
                    job_key.SetVariable( 'popup_gauge_1', ( index + 1, num_to_do ) )
                    
                    QP.CallAfter( qt_update_label, x_of_y )
                    
                    hash = media.GetHash()
                    mime = media.GetMime()
                    
                    path = os.path.normpath( path )
                    
                    if not path.startswith( directory ):
                        
                        raise Exception( 'It seems a destination path was above the main export directory! The file was "{}" and its destination path was "{}".'.format( hash.hex(), path ) )
                        
                    
                    path_dir = os.path.dirname( path )
                    
                    HydrusPaths.MakeSureDirectoryExists( path_dir )
                    
                    if export_tag_txts:
                        
                        tags_manager = media.GetTagsManager()
                        
                        tags = set()
                        
                        for service_key in neighbouring_txt_tag_service_keys:
                            
                            current_tags = tags_manager.GetCurrent( service_key, ClientTags.TAG_DISPLAY_ACTUAL )
                            
                            tags.update( current_tags )
                            
                        
                        tags = sorted( tags )
                        
                        txt_path = path + '.txt'
                        
                        with open( txt_path, 'w', encoding = 'utf-8' ) as f:
                            
                            f.write( os.linesep.join( tags ) )
                            
                        
                    
                    source_path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
                    
                    if export_symlinks:
                        
                        os.symlink( source_path, path )
                        
                    else:
                        
                        HydrusPaths.MirrorFile( source_path, path )
                        
                        HydrusPaths.MakeFileWriteable( path )
                        
                    
                except:
                    
                    QP.CallAfter( QW.QMessageBox.information, self, 'Information', 'Encountered a problem while attempting to export file with index '+str(ordering_index+1)+':'+os.linesep*2+traceback.format_exc() )
                    
                    break
                    
                
                pauser.Pause()
                
            
            if not job_key.IsCancelled() and delete_afterwards:
                
                QP.CallAfter( qt_update_label, 'deleting' )
                
                delete_lock_for_archived_files = HG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
                
                if delete_lock_for_archived_files:
                    
                    deletee_hashes = { media.GetHash() for ( ordering_index, media, path ) in to_do if not media.HasArchive() }
                    
                else:
                    
                    deletee_hashes = { media.GetHash() for ( ordering_index, media, path ) in to_do }
                    
                
                chunks_of_hashes = HydrusData.SplitListIntoChunks( deletee_hashes, 64 )
                
                reason = 'Deleted after manual export to "{}".'.format( directory )
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) for chunk_of_hashes in chunks_of_hashes ]
                
                for content_update in content_updates:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
                    
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.SetVariable( 'popup_text_1', 'Done!' )
            
            job_key.Finish()
            
            job_key.Delete( 5 )
            
            QP.CallAfter( qt_update_label, 'done!' )
            
            time.sleep( 1 )
            
            QP.CallAfter( qt_update_label, 'export' )
            
            QP.CallAfter( qt_done, quit_afterwards )
            
        
        HG.client_controller.CallToThread( do_it, directory, neighbouring_txt_tag_service_keys, delete_afterwards, export_symlinks, quit_afterwards )
        
    
    def _GetPath( self, media ):
        
        if media in self._media_to_paths:
            
            return self._media_to_paths[ media ]
            
        
        directory = self._directory_picker.GetPath()
        
        pattern = self._pattern.text()
        
        terms = ClientExporting.ParseExportPhrase( pattern )
        
        filename = ClientExporting.GenerateExportFilename( directory, media, terms, do_not_use_filenames = self._existing_filenames )
        
        path = os.path.join( directory, filename )
        
        path = os.path.normpath( path )
        
        self._existing_filenames.add( filename )
        self._media_to_paths[ media ] = path
        
        return path
        
    
    def _RefreshPaths( self ):
        
        pattern = self._pattern.text()
        dir_path = self._directory_picker.GetPath()
        
        if pattern == self._last_phrase_used and dir_path == self._last_dir_used:
            
            return
            
        
        self._last_phrase_used = pattern
        self._last_dir_used = dir_path
        
        HG.client_controller.new_options.SetString( 'export_phrase', pattern )
        
        self._existing_filenames = set()
        self._media_to_paths = {}
        
        self._paths.UpdateDatas()
        
    
    def _RefreshTags( self ):
        
        data = self._paths.GetData( only_selected = True )
        
        if len( data ) == 0:
            
            data = self._paths.GetData()
            
        
        all_media = [ media for ( ordering_index, media ) in data ]
        
        self._tags_box.SetTagsByMedia( all_media )
        
    
    def _SetTxtServices( self ):
        
        services_manager = HG.client_controller.services_manager
        
        tag_services = services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        choice_tuples = [ ( service.GetName(), service.GetServiceKey(), service.GetServiceKey() in self._neighbouring_txt_tag_service_keys ) for service in tag_services ]
        
        try:
            
            neighbouring_txt_tag_service_keys = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select tag services', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._neighbouring_txt_tag_service_keys = neighbouring_txt_tag_service_keys
        
        HG.client_controller.new_options.SetKeyList( 'default_neighbouring_txt_tag_service_keys', self._neighbouring_txt_tag_service_keys )
        
        if len( self._neighbouring_txt_tag_service_keys ) == 0:
            
            self._export_tag_txts.setChecked( False )
            
        
        self._UpdateTxtButton()
        
    
    def _UpdateTxtButton( self ):
        
        if self._export_tag_txts.isChecked():
            
            self._export_tag_txts_services_button.setEnabled( True )
            
        else:
            
            self._export_tag_txts_services_button.setEnabled( False )
            
        
        if len( self._neighbouring_txt_tag_service_keys ) == 0:
            
            tt = 'No services set.'
            
        else:
            
            names = [ HG.client_controller.services_manager.GetName( service_key ) for service_key in self._neighbouring_txt_tag_service_keys ]
            
            tt = ', '.join( names )
            
        
        self._export_tag_txts_services_button.setToolTip( tt )
        
    
    def EventExport( self, event ):
        
        self._DoExport()
        
    
    def EventDeleteFilesChanged( self ):
        
        value = self._delete_files_after_export.isChecked()
        
        HG.client_controller.new_options.SetBoolean( 'delete_files_after_export', value )
        
        if value:
            
            self._export_symlinks.setChecked( False )
            
        
    
    def EventExportTagTxtsChanged( self ):
        
        turning_on = self._export_tag_txts.isChecked()
        
        self._UpdateTxtButton()
        
        if turning_on:
            
            self._SetTxtServices()
            
        else:
            
            HG.client_controller.new_options.SetKeyList( 'default_neighbouring_txt_tag_service_keys', [] )
            
        
    
    def EventOpenLocation( self ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            HydrusPaths.LaunchDirectory( directory )
        
        
    
