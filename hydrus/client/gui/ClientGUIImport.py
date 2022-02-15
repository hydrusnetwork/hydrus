import collections
import os
import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFileSeedCache
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIGallerySeedLog
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIOptionsPanels
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.metadata import ClientTags

class CheckerOptionsButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, checker_options, update_callable = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'checker options', self._EditOptions )
        
        self._checker_options = checker_options
        self._update_callable = update_callable
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit checker options' ) as dlg:
            
            panel = ClientGUITime.EditCheckerOptions( dlg, self._checker_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                checker_options = panel.GetValue()
                
                self._SetValue( checker_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.setToolTip( self._checker_options.GetSummary() )
        
    
    def _SetValue( self, checker_options ):
        
        self._checker_options = checker_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._checker_options )
            
        
    
    def GetValue( self ):
        
        return self._checker_options
        
    
    def SetValue( self, checker_options ):
        
        self._SetValue( checker_options )
        
    
class FileImportOptionsButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, file_import_options, show_downloader_options, update_callable = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'file import options', self._EditOptions )
        
        self._file_import_options = file_import_options
        self._show_downloader_options = show_downloader_options
        self._update_callable = update_callable
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit file import options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditFileImportOptions( dlg, self._file_import_options, self._show_downloader_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                file_import_options = panel.GetValue()
                
                self._SetValue( file_import_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.setToolTip( self._file_import_options.GetSummary() )
        
    
    def _SetValue( self, file_import_options ):
        
        self._file_import_options = file_import_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._file_import_options )
            
        
    
    def GetValue( self ):
        
        return self._file_import_options
        
    
    def SetValue( self, file_import_options ):
        
        self._SetValue( file_import_options )
        
    
class FilenameTaggingOptionsPanel( QW.QWidget ):
    
    tagsChanged = QC.Signal()
    
    def __init__( self, parent, service_key, filename_tagging_options = None, present_for_accompanying_file_list = False ):
        
        if filename_tagging_options is None:
            
            # pull from an options default
            
            filename_tagging_options = TagImportOptions.FilenameTaggingOptions()
            
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        self._notebook = QW.QTabWidget( self )
        
        # eventually these will take 'regexoptions' or whatever object and 'showspecificfiles' as well
        
        self._simple_panel = self._SimplePanel( self._notebook, self._service_key, filename_tagging_options, present_for_accompanying_file_list )
        self._advanced_panel = self._AdvancedPanel( self._notebook, self._service_key, filename_tagging_options, present_for_accompanying_file_list )
        
        self._simple_panel.tagsChanged.connect( self.tagsChanged )
        self._advanced_panel.tagsChanged.connect( self.tagsChanged )
        
        self._notebook.addTab( self._simple_panel, 'simple' )
        self._notebook.setCurrentWidget( self._simple_panel )
        self._notebook.addTab( self._advanced_panel, 'advanced' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def GetFilenameTaggingOptions( self ):
        
        filename_tagging_options = TagImportOptions.FilenameTaggingOptions()
        
        self._advanced_panel.UpdateFilenameTaggingOptions( filename_tagging_options )
        self._simple_panel.UpdateFilenameTaggingOptions( filename_tagging_options )
        
        return filename_tagging_options
        
    
    def GetTags( self, index, path ):
        
        tags = set()
        
        tags.update( self._simple_panel.GetTags( index, path ) )
        tags.update( self._advanced_panel.GetTags( index, path ) )
        
        tags = HydrusTags.CleanTags( tags )
        
        tags = HG.client_controller.tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_STORAGE, self._service_key, tags )
        
        return tags
        
    
    def SetSelectedPaths( self, paths ):
        
        self._simple_panel.SetSelectedPaths( paths )
        
    
    class _AdvancedPanel( QW.QWidget ):
        
        tagsChanged = QC.Signal()
        
        def __init__( self, parent, service_key, filename_tagging_options, present_for_accompanying_file_list ):
            
            QW.QWidget.__init__( self, parent )
            
            self._service_key = service_key
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
            
            quick_namespaces_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._quick_namespaces_panel )
            
            self._quick_namespaces_list = ClientGUIListCtrl.BetterListCtrl( quick_namespaces_listctrl_panel, CGLC.COLUMN_LIST_QUICK_NAMESPACES.ID, 4, self._ConvertQuickRegexDataToListCtrlTuples, use_simple_delete = True, activation_callback = self.EditQuickNamespaces )
            
            quick_namespaces_listctrl_panel.SetListCtrl( self._quick_namespaces_list )
            
            quick_namespaces_listctrl_panel.AddButton( 'add', self.AddQuickNamespace )
            quick_namespaces_listctrl_panel.AddButton( 'edit', self.EditQuickNamespaces, enabled_only_on_selection = True )
            quick_namespaces_listctrl_panel.AddDeleteButton()
            
            #
            
            self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
            
            self._regexes = QW.QListWidget( self._regexes_panel )
            self._regexes.itemDoubleClicked.connect( self.EventRemoveRegex )
            
            self._regex_box = QW.QLineEdit()
            self._regex_box.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._regexes, self.AddRegex ) )
            
            self._regex_shortcuts = ClientGUICommon.RegexButton( self._regexes_panel )
            
            self._regex_intro_link = ClientGUICommon.BetterHyperLink( self._regexes_panel, 'a good regex introduction', 'https://www.aivosto.com/vbtips/regex.html' )
            self._regex_practise_link = ClientGUICommon.BetterHyperLink( self._regexes_panel, 'regex practice', 'https://regexr.com/3cvmf' )
            
            #
            
            self._num_panel = ClientGUICommon.StaticBox( self, '#' )
            
            self._num_base = QP.MakeQSpinBox( self._num_panel, min=-10000000, max=10000000, width = 60 )
            self._num_base.setValue( 1 )
            self._num_base.valueChanged.connect( self.tagsChanged )
            
            self._num_step = QP.MakeQSpinBox( self._num_panel, min=-1000000, max=1000000, width = 60 )
            self._num_step.setValue( 1 )
            self._num_step.valueChanged.connect( self.tagsChanged )
            
            self._num_namespace = QW.QLineEdit()
            self._num_namespace.setFixedWidth( 100 )
            self._num_namespace.textChanged.connect( self.tagsChanged )
            
            if not self._present_for_accompanying_file_list:
                
                self._num_panel.hide()
                
            
            #
            
            ( quick_namespaces, regexes ) = filename_tagging_options.AdvancedToTuple()
            
            self._quick_namespaces_list.AddDatas( quick_namespaces )
            
            self._quick_namespaces_list.Sort()
            
            for regex in regexes:
                
                self._regexes.addItem( regex )
                
            
            #
            
            self._quick_namespaces_panel.Add( quick_namespaces_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self._regexes_panel.Add( self._regexes, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._regexes_panel.Add( self._regex_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._regexes_panel.Add( self._regex_shortcuts, CC.FLAGS_ON_RIGHT )
            self._regexes_panel.Add( self._regex_intro_link, CC.FLAGS_ON_RIGHT )
            self._regexes_panel.Add( self._regex_practise_link, CC.FLAGS_ON_RIGHT )
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, QW.QLabel( '# base/step: ', self._num_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._num_base, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._num_step, CC.FLAGS_CENTER_PERPENDICULAR )
            
            self._num_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, QW.QLabel( '# namespace: ', self._num_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._num_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._num_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            second_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( second_vbox, self._regexes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( second_vbox, self._num_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._quick_namespaces_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, second_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.setLayout( hbox )
            
            self._quick_namespaces_list.columnListContentsChanged.connect( self.tagsChanged )
            
        
        def _ConvertQuickRegexDataToListCtrlTuples( self, data ):
            
            ( namespace, regex ) = data
            
            display_tuple = ( namespace, regex )
            sort_tuple = ( namespace, regex )
            
            return ( display_tuple, sort_tuple )
            
        
        def AddQuickNamespace( self ):
            
            with ClientGUIDialogs.DialogInputNamespaceRegex( self ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( namespace, regex ) = dlg.GetInfo()
                    
                    data = ( namespace, regex )
                    
                    self._quick_namespaces_list.AddDatas( ( data, ) )
                    
                
            
        
        def EditQuickNamespaces( self ):
            
            data_to_edit = self._quick_namespaces_list.GetData( only_selected = True )
            
            for old_data in data_to_edit:
                
                ( namespace, regex ) = old_data
                
                with ClientGUIDialogs.DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        ( new_namespace, new_regex ) = dlg.GetInfo()
                        
                        new_data = ( new_namespace, new_regex )
                        
                        if new_data != old_data:
                            
                            self._quick_namespaces_list.DeleteDatas( ( old_data, ) )
                            
                            self._quick_namespaces_list.AddDatas( ( new_data, ) )
                            
                        
                    
                
            
        
        def AddRegex( self ):
            
            regex = self._regex_box.text()
            
            if regex != '':
                
                try:
                    
                    re.compile( regex )
                    
                except Exception as e:
                    
                    text = 'That regex would not compile!'
                    text += os.linesep * 2
                    text += str( e )
                    
                    QW.QMessageBox.critical( self, 'Error', text )
                    
                    return
                    
                
                self._regexes.addItem( regex )
                
                self._regex_box.clear()
                
                self.tagsChanged.emit()
                
            
        
        def EventRemoveRegex( self, item ):
            
            selection = QP.ListWidgetGetSelection( self._regexes ) 
            
            if selection != -1:
                
                if len( self._regex_box.text() ) == 0:
                    
                    self._regex_box.setText( self._regexes.item( selection ).text() )
                    
                
                QP.ListWidgetDelete( self._regexes, selection )
                
                self.tagsChanged.emit()
                
            
        
        def GetTags( self, index, path ):
            
            tags = set()
            
            num_namespace = self._num_namespace.text()
            
            if num_namespace != '':
                
                num_base = self._num_base.value()
                num_step = self._num_step.value()
                
                tag_num = num_base + index * num_step
                
                tags.add( num_namespace + ':' + str( tag_num ) )
                
            
            return tags
            
        
        def UpdateFilenameTaggingOptions( self, filename_tagging_options ):
            
            quick_namespaces = self._quick_namespaces_list.GetData()
            
            regexes = QP.ListWidgetGetStrings( self._regexes )
            
            filename_tagging_options.AdvancedSetTuple( quick_namespaces, regexes )
            
        
    
    class _SimplePanel( QW.QWidget ):
        
        tagsChanged = QC.Signal()
        
        def __init__( self, parent, service_key, filename_tagging_options, present_for_accompanying_file_list ):
            
            QW.QWidget.__init__( self, parent )
            
            self._service_key = service_key
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
            
            self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._tags_panel, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            self._tag_autocomplete_all = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tags_panel, self.EnterTags, default_location_context, service_key, show_paste_button = True )
            
            self._tags_paste_button = ClientGUICommon.BetterButton( self._tags_panel, 'paste tags', self._PasteTags )
            
            #
            
            self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for selected files' )
            
            self._paths_to_single_tags = collections.defaultdict( set )
            
            self._single_tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._single_tags_panel, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            
            self._single_tags_paste_button = ClientGUICommon.BetterButton( self._single_tags_panel, 'paste tags', self._PasteSingleTags )
            
            self._tag_autocomplete_selection = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.EnterTagsSingle, default_location_context, service_key, show_paste_button = True )
            
            self.SetSelectedPaths( [] )
            
            if not self._present_for_accompanying_file_list:
                
                self._single_tags_panel.hide()
                
            
            #
            
            self._checkboxes_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._load_from_txt_files_checkbox = QW.QCheckBox( 'try to load tags from neighbouring .txt files', self._checkboxes_panel )
            
            txt_files_help_button = ClientGUICommon.BetterBitmapButton( self._checkboxes_panel, CC.global_pixmaps().help, self._ShowTXTHelp )
            txt_files_help_button.setToolTip( 'Show help regarding importing tags from .txt files.' )
            
            self._filename_namespace = QW.QLineEdit( self._checkboxes_panel )
            self._filename_namespace.setMinimumWidth( 100 )
            
            self._filename_checkbox = QW.QCheckBox( 'add filename? [namespace]', self._checkboxes_panel )
            
            self._directory_namespace_controls = {}
            
            directory_items = []
            
            directory_items.append( ( 0, 'first' ) )
            directory_items.append( ( 1, 'second' ) )
            directory_items.append( ( 2, 'third' ) )
            directory_items.append( ( -3, 'third last' ) )
            directory_items.append( ( -2, 'second last' ) )
            directory_items.append( ( -1, 'last' ) )
            
            for ( index, phrase ) in directory_items:
                
                dir_checkbox = QW.QCheckBox( 'add '+phrase+' directory? [namespace]', self._checkboxes_panel )
                
                dir_namespace_textctrl = QW.QLineEdit( self._checkboxes_panel )
                dir_namespace_textctrl.setMinimumWidth( 100 )
                
                self._directory_namespace_controls[ index ] = ( dir_checkbox, dir_namespace_textctrl )
                
            
            #
            
            ( tags_for_all, load_from_neighbouring_txt_files, add_filename, directory_dict ) = filename_tagging_options.SimpleToTuple()
            
            self._tags.AddTags( tags_for_all )
            self._load_from_txt_files_checkbox.setChecked( load_from_neighbouring_txt_files )
            
            ( add_filename_boolean, add_filename_namespace ) = add_filename
            
            self._filename_checkbox.setChecked( add_filename_boolean )
            self._filename_namespace.setText( add_filename_namespace )
            
            for ( index, ( dir_boolean, dir_namespace ) ) in directory_dict.items():
                
                ( dir_checkbox, dir_namespace_textctrl ) = self._directory_namespace_controls[ index ]
                
                dir_checkbox.setChecked( dir_boolean )
                dir_namespace_textctrl.setText( dir_namespace )
                
                dir_checkbox.clicked.connect( self.tagsChanged )
                dir_namespace_textctrl.textChanged.connect( self.tagsChanged )
                
            
            #
            
            self._tags_panel.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._tags_panel.Add( self._tag_autocomplete_all, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._tags_panel.Add( self._tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._single_tags_panel.Add( self._single_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._single_tags_panel.Add( self._tag_autocomplete_selection, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._single_tags_panel.Add( self._single_tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            txt_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( txt_hbox, self._load_from_txt_files_checkbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( txt_hbox, txt_files_help_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            filename_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( filename_hbox, self._filename_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( filename_hbox, self._filename_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._checkboxes_panel.Add( txt_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._checkboxes_panel.Add( filename_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            for index in ( 0, 1, 2, -3, -2, -1 ):
                
                hbox = QP.HBoxLayout()
                
                ( dir_checkbox, dir_namespace_textctrl ) = self._directory_namespace_controls[ index ]
                
                QP.AddToLayout( hbox, dir_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, dir_namespace_textctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._checkboxes_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._checkboxes_panel.Add( QW.QWidget( self._checkboxes_panel ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._single_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._checkboxes_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.setLayout( hbox )
            
            #
            
            self._tags.tagsRemoved.connect( self.tagsChanged )
            self._single_tags.tagsRemoved.connect( self.SingleTagsRemoved )
            
            self._load_from_txt_files_checkbox.clicked.connect( self.tagsChanged )
            self._filename_namespace.textChanged.connect( self.tagsChanged )
            self._filename_checkbox.clicked.connect( self.tagsChanged )
            
        
        def _GetTagsFromClipboard( self ):
            
            try:
                
                text = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( text )
                
                tags = HydrusTags.CleanTags( tags )
                
                return tags
                
            except:
                
                raise Exception( 'I could not understand what was in the clipboard' )
                
            
        
        def _PasteTags( self ):
            
            try:
                
                tags = self._GetTagsFromClipboard()
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            self.EnterTags( tags )
            
        
        def _PasteSingleTags( self ):
            
            try:
                
                tags = self._GetTagsFromClipboard()
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            self.EnterTagsSingle( tags )
            
        
        def _ShowTXTHelp( self ):
            
            message = 'If you would like to add custom tags with your files, add a .txt file beside the file like so:'
            message += os.linesep * 2
            message += 'my_file.jpg'
            message += os.linesep
            message += 'my_file.jpg.txt'
            message += os.linesep * 2
            message += 'And include your tags inside the .txt file in a newline-separated list (if you know how to script, generating these files automatically from another source of tags can save a lot of time!).'
            message += os.linesep * 2
            message += 'Make sure you preview the results in the table above to be certain everything is parsing correctly. Until you are comfortable with this, you should test it on just one or two files.'
            
            QW.QMessageBox.information( self, 'Information', message )
            
        
        def EnterTags( self, tags ):
            
            HG.client_controller.Write( 'push_recent_tags', self._service_key, tags )
            
            if len( tags ) > 0:
                
                self._tags.AddTags( tags )
                
                self.tagsChanged.emit()
                
            
        
        def EnterTagsSingle( self, tags ):
            
            HG.client_controller.Write( 'push_recent_tags', self._service_key, tags )
            
            if len( tags ) > 0:
                
                self._single_tags.AddTags( tags )
                
                for path in self._selected_paths:
                    
                    current_tags = self._paths_to_single_tags[ path ]
                    
                    current_tags.update( tags )
                    
                
                self.tagsChanged.emit()
                
            
        
        def GetTags( self, index, path ):
            
            tags = set()
            
            if path in self._paths_to_single_tags:
                
                tags.update( self._paths_to_single_tags[ path ] )
                
            
            return tags
            
        
        def SingleTagsRemoved( self ):
            
            tags = self._single_tags.GetTags()
            
            for path in self._selected_paths:
                
                self._paths_to_single_tags[ path ].intersection_update( tags )
                
            
            self.tagsChanged.emit()
            
        
        def SetSelectedPaths( self, paths ):
            
            self._selected_paths = paths
            
            single_tags = set()
            
            if len( paths ) > 0:
                
                for path in self._selected_paths:
                    
                    if path in self._paths_to_single_tags:
                        
                        single_tags.update( self._paths_to_single_tags[ path ] )
                        
                    
                
                self._tag_autocomplete_selection.setEnabled( True )
                self._single_tags_paste_button.setEnabled( True )
                
            else:
                
                self._tag_autocomplete_selection.setEnabled( False )
                self._single_tags_paste_button.setEnabled( False )
                
            
            self._single_tags.SetTags( single_tags )
            
        
        def TagsRemoved( self, *args ):
            
            self.tagsChanged.emit()
            
        
        def UpdateFilenameTaggingOptions( self, filename_tagging_options ):
            
            tags_for_all = self._tags.GetTags()
            load_from_neighbouring_txt_files = self._load_from_txt_files_checkbox.isChecked()
            
            add_filename = ( self._filename_checkbox.isChecked(), self._filename_namespace.text() )
            
            directories_dict = {}
            
            for ( index, ( dir_checkbox, dir_namespace_textctrl ) ) in self._directory_namespace_controls.items():
                
                directories_dict[ index ] = ( dir_checkbox.isChecked(), dir_namespace_textctrl.text() )
                
            
            filename_tagging_options.SimpleSetTuple( tags_for_all, load_from_neighbouring_txt_files, add_filename, directories_dict )
            
        
    
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
                    
                else:
                    
                    break
                    
                
            
        
        self._import_folders.Sort()
        
    
    def _GetExistingNames( self ):
        
        import_folders = self._import_folders.GetData()
        
        names = { import_folder.GetName() for import_folder in import_folders }
        
        return names
        
    
    def GetValue( self ):
        
        import_folders = self._import_folders.GetData()
        
        return import_folders
        
    
class EditImportFolderPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, import_folder ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._import_folder = import_folder
        
        ( name, path, mimes, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ) = self._import_folder.ToTuple()
        
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
        
        self._file_box = ClientGUICommon.StaticBox( self, 'file options' )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimes( self._file_box, HC.ALLOWED_MIMES )
        
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
        
        show_downloader_options = False
        
        self._file_import_options = FileImportOptionsButton( self._file_box, file_import_options, show_downloader_options )
        
        #
        
        self._tag_box = ClientGUICommon.StaticBox( self, 'tag options' )
        
        self._tag_import_options = TagImportOptionsButton( self._tag_box, tag_import_options, show_downloader_options )
        
        self._filename_tagging_options_box = ClientGUICommon.StaticBox( self._tag_box, 'filename tagging' )
        
        filename_tagging_options_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._filename_tagging_options_box )
        
        self._filename_tagging_options = ClientGUIListCtrl.BetterListCtrl( filename_tagging_options_panel, CGLC.COLUMN_LIST_FILENAME_TAGGING_OPTIONS.ID, 5, self._ConvertFilenameTaggingOptionsToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditFilenameTaggingOptions )
        
        filename_tagging_options_panel.SetListCtrl( self._filename_tagging_options )
        
        filename_tagging_options_panel.AddButton( 'add', self._AddFilenameTaggingOptions )
        filename_tagging_options_panel.AddButton( 'edit', self._EditFilenameTaggingOptions, enabled_only_on_selection = True )
        filename_tagging_options_panel.AddDeleteButton()
        
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
        
        self._mimes.SetValue( mimes )
        
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
        
        rows = []
        
        rows.append( ( 'mimes to import: ', self._mimes ) )
        
        mimes_gridbox = ClientGUICommon.WrapInGrid( self._file_box, rows, expand_text = True )
        
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
        
        self._file_box.Add( mimes_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_box.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._filename_tagging_options_box.Add( filename_tagging_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._tag_box.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._tag_box.Add( self._filename_tagging_options_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._folder_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
            
            panel = EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options )
            
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
        
        selected_data = self._filename_tagging_options.GetData( only_selected = True )
        
        for data in selected_data:
            
            ( service_key, filename_tagging_options ) = data
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit filename tagging options' ) as dlg:
                
                panel = EditFilenameTaggingOptionPanel( dlg, service_key, filename_tagging_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._filename_tagging_options.DeleteDatas( ( data, ) )
                    
                    filename_tagging_options = panel.GetValue()
                    
                    self._filename_tagging_options.AddDatas( [ ( service_key, filename_tagging_options ) ] )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _UpdateCheckRegularly( self ):
        
        if self._check_regularly.isChecked():
            
            self._period.setEnabled( True )
            
        else:
            
            self._period.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        self._CheckValid()
        
        name = self._name.text()
        path = self._path.GetPath()
        mimes = self._mimes.GetValue()
        file_import_options = self._file_import_options.GetValue()
        tag_import_options = self._tag_import_options.GetValue()
        
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
        
        self._import_folder.SetTuple( name, path, mimes, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
        
        return self._import_folder
        
    
class EditLocalImportFilenameTaggingPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, paths ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._paths = paths
        
        
        self._tag_repositories = ClientGUICommon.BetterNotebook( self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        default_tag_service_key = HG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_repositories, service_key, paths )
            
            select = service_key == default_tag_service_key
            
            tab_index = self._tag_repositories.addTab( page, name )
            if select: self._tag_repositories.setCurrentIndex( tab_index )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_repositories.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if self.sender() != self._tag_repositories:
            
            return
            
        
        if HG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = self._tag_repositories.currentWidget()
            
            HG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def GetValue( self ):
        
        paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
        
        for page in self._tag_repositories.GetPages():
            
            ( service_key, page_of_paths_to_tags ) = page.GetInfo()
            
            for ( path, tags ) in page_of_paths_to_tags.items():
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                paths_to_additional_service_keys_to_tags[ path ][ service_key ] = tags
                
            
        
        return paths_to_additional_service_keys_to_tags
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, paths ):
            
            QW.QWidget.__init__( self, parent )
            
            self._service_key = service_key
            self._paths = paths
            
            self._paths_list = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_PATHS_TO_TAGS.ID, 10, self._ConvertDataToListCtrlTuples )
            
            self._paths_list.itemSelectionChanged.connect( self.EventItemSelected )
            
            #
            
            self._filename_tagging_panel = FilenameTaggingOptionsPanel( self, self._service_key, present_for_accompanying_file_list = True )
            
            self._schedule_refresh_file_list_job = None
            
            #
            
            # i.e. ( index, path )
            self._paths_list.AddDatas( list( enumerate( self._paths ) ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._filename_tagging_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            self._filename_tagging_panel.tagsChanged.connect( self.ScheduleRefreshFileList )
            
        
        def _ConvertDataToListCtrlTuples( self, data ):
            
            ( index, path ) = data
            
            tags = self._GetTags( index, path )
            
            pretty_index = HydrusData.ToHumanInt( index + 1 )
            
            pretty_path = path
            pretty_tags = ', '.join( tags )
            
            display_tuple = ( pretty_index, pretty_path, pretty_tags )
            sort_tuple = ( index, path, tags )
            
            return ( display_tuple, sort_tuple )
            
        
        def _GetTags( self, index, path ):
            
            filename_tagging_options = self._filename_tagging_panel.GetFilenameTaggingOptions()
            
            tags = filename_tagging_options.GetTags( self._service_key, path )
            
            tags.update( self._filename_tagging_panel.GetTags( index, path ) )
            
            tags = sorted( tags )
            
            return tags
            
        
        def EventItemSelected( self ):
            
            paths = [ path for ( index, path ) in self._paths_list.GetData( only_selected = True ) ]
            
            self._filename_tagging_panel.SetSelectedPaths( paths )
            
        
        def GetInfo( self ):
            
            paths_to_tags = { path : self._GetTags( index, path ) for ( index, path ) in self._paths_list.GetData() }
            
            return ( self._service_key, paths_to_tags )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def RefreshFileList( self ):
            
            self._paths_list.UpdateDatas()
            
        
        def ScheduleRefreshFileList( self ):
            
            if self._schedule_refresh_file_list_job is not None:
                
                self._schedule_refresh_file_list_job.Cancel()
                
                self._schedule_refresh_file_list_job = None
                
            
            self._schedule_refresh_file_list_job = HG.client_controller.CallLaterQtSafe( self, 0.5, 'refresh path list', self.RefreshFileList )
            
        
    
class EditFilenameTaggingOptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_key, filename_tagging_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._service_key = service_key
        
        self._example_path_input = QW.QLineEdit( self )
        self._example_output = QW.QLineEdit( self )
        
        self._filename_tagging_options_panel = FilenameTaggingOptionsPanel( self, self._service_key, filename_tagging_options = filename_tagging_options, present_for_accompanying_file_list = False )
        
        self._schedule_refresh_tags_job = None
        
        #
        
        self._example_path_input.setPlaceholderText( 'enter example path here' )
        self._example_output.setEnabled( False )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._example_path_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_output, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filename_tagging_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._example_path_input.textChanged.connect( self.ScheduleRefreshTags )
        
        self._filename_tagging_options_panel.tagsChanged.connect( self.ScheduleRefreshTags )
        
    
    def GetValue( self ):
        
        return self._filename_tagging_options_panel.GetFilenameTaggingOptions()
        
    
    def RefreshTags( self ):
        
        example_path_input = self._example_path_input.text()
        
        filename_tagging_options = self.GetValue()
        
        try:
            
            tags = filename_tagging_options.GetTags( self._service_key, example_path_input )
            
        except:
            
            tags = [ 'could not parse' ]
            
        
        self._example_output.setText( ', '.join( tags ) )
        
    
    def ScheduleRefreshTags( self ):
        
        path = self._example_path_input.text()
        
        if path.startswith( '"' ) and path.endswith( '"' ):
            
            path = path[1:-1]
            
            self._example_path_input.setText( path )
            
        
        if path.startswith( 'file:///' ):
            
            path = path.replace( 'file:///', '', 1 )
            
            path = os.path.normpath( path )
            
            self._example_path_input.setText( path )
            
        
        if self._schedule_refresh_tags_job is not None:
            
            self._schedule_refresh_tags_job.Cancel()
            
            self._schedule_refresh_tags_job = None
            
        
        self._schedule_refresh_tags_job = HG.client_controller.CallLaterQtSafe( self, 0.5, 'refresh tags', self.RefreshTags )
        
    
class GalleryImportPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, page_key, name = 'gallery query' ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, name )
        
        self._page_key = page_key
        
        self._gallery_import = None
        
        #
        
        self._query_text = QW.QLineEdit( self )
        self._query_text.setReadOnly( True )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'imports' )
        
        self._file_status = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, HG.client_controller, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        self._files_pause_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.global_pixmaps().file_pause, self.PauseFiles )
        self._files_pause_button.setToolTip( 'pause/play files' )
        
        self._gallery_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._gallery_status = ClientGUICommon.BetterStaticText( self._gallery_panel, ellipsize_end = True )
        
        self._gallery_pause_button = ClientGUICommon.BetterBitmapButton( self._gallery_panel, CC.global_pixmaps().gallery_pause, self.PauseGallery )
        self._gallery_pause_button.setToolTip( 'pause/play search' )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._gallery_panel, HG.client_controller, False, True, 'search', page_key = self._page_key )
        
        self._gallery_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._gallery_panel )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self, 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.valueChanged.connect( self.EventFileLimit )
        self._file_limit.setToolTip( 'stop searching the gallery once this many files has been reached' )
        
        file_import_options = FileImportOptions.FileImportOptions()
        tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
        show_downloader_options = True
        
        self._file_import_options = FileImportOptionsButton( self, file_import_options, show_downloader_options, self._SetFileImportOptions )
        self._tag_import_options = TagImportOptionsButton( self, tag_import_options, show_downloader_options, update_callable = self._SetTagImportOptions, allow_default_selection = True )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._gallery_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._gallery_pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._gallery_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._file_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._files_pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.Add( self._query_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._gallery_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._UpdateControlsForNewGalleryImport()
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _SetFileImportOptions( self, file_import_options: FileImportOptions.FileImportOptions ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetFileImportOptions( file_import_options )
            
        
    
    def _SetTagImportOptions( self, tag_import_options: TagImportOptions.TagImportOptions ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetTagImportOptions( tag_import_options )
            
        
    
    def _UpdateControlsForNewGalleryImport( self ):
        
        if self._gallery_import is None:
            
            self._import_queue_panel.setEnabled( False )
            self._gallery_panel.setEnabled( False )
            
            self._file_limit.setEnabled( False )
            self._file_import_options.setEnabled( False )
            self._tag_import_options.setEnabled( False )
            
            self._query_text.clear()
            
            self._file_status.clear()
            
            self._gallery_status.clear()
            
            self._file_seed_cache_control.SetFileSeedCache( None )
            
            self._gallery_seed_log_control.SetGallerySeedLog( None )
            
            self._file_download_control.ClearNetworkJob()
            self._gallery_download_control.ClearNetworkJob()
            
        else:
            
            self._import_queue_panel.setEnabled( True )
            self._gallery_panel.setEnabled( True )
            
            self._file_limit.setEnabled( True )
            self._file_import_options.setEnabled( True )
            self._tag_import_options.setEnabled( True )
            
            query = self._gallery_import.GetQueryText()
            
            self._query_text.setText( query )
            
            file_limit = self._gallery_import.GetFileLimit()
            
            self._file_limit.SetValue( file_limit )
            
            file_import_options = self._gallery_import.GetFileImportOptions()
            
            self._file_import_options.SetValue( file_import_options )
            
            tag_import_options = self._gallery_import.GetTagImportOptions()
            
            self._tag_import_options.SetValue( tag_import_options )
            
            file_seed_cache = self._gallery_import.GetFileSeedCache()
            
            self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
            
            gallery_seed_log = self._gallery_import.GetGallerySeedLog()
            
            self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
            
        
    
    def _UpdateStatus( self ):
        
        if self._gallery_import is not None:
            
            ( gallery_status, file_status, files_paused, gallery_paused ) = self._gallery_import.GetStatus()
            
            if files_paused:
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._files_pause_button, CC.global_pixmaps().file_play )
                
            else:
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._files_pause_button, CC.global_pixmaps().file_pause )
                
            
            if gallery_paused:
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._gallery_pause_button, CC.global_pixmaps().gallery_play )
                
            else:
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._gallery_pause_button, CC.global_pixmaps().gallery_pause )
                
            
            if gallery_paused:
                
                if gallery_status == '':
                    
                    gallery_status = 'paused'
                    
                else:
                    
                    gallery_status = 'paused - ' + gallery_status
                    
                
            
            self._gallery_status.setText( gallery_status )
            
            if files_paused:
                
                if file_status == '':
                    
                    file_status = 'paused'
                    
                else:
                    
                    file_status = 'pausing - ' + file_status
                    
                
            
            self._file_status.setText( file_status )
            
            ( file_network_job, gallery_network_job ) = self._gallery_import.GetNetworkJobs()
            
            if file_network_job is None:
                
                self._file_download_control.ClearNetworkJob()
                
            else:
                
                self._file_download_control.SetNetworkJob( file_network_job )
                
            
            if gallery_network_job is None:
                
                self._gallery_download_control.ClearNetworkJob()
                
            else:
                
                self._gallery_download_control.SetNetworkJob( gallery_network_job )
                
            
        
    
    def EventFileLimit( self ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetFileLimit( self._file_limit.GetValue() )
            
        
    
    def PauseFiles( self ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.PausePlayFiles()
            
            self._UpdateStatus()
            
        
    
    def PauseGallery( self ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.PausePlayGallery()
            
            self._UpdateStatus()
            
        
    
    def SetGalleryImport( self, gallery_import ):
        
        self._gallery_import = gallery_import
        
        self._UpdateControlsForNewGalleryImport()
        
    
    def TIMERUIUpdate( self ):
        
        if HG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._UpdateStatus()
            
        
    
class GUGKeyAndNameSelector( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, gug_key_and_name, update_callable = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'gallery selector', self._Edit )
        
        gug = HG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
        
        if gug is not None:
            
            gug_key_and_name = gug.GetGUGKeyAndName()
            
        
        self._gug_key_and_name = gug_key_and_name
        self._update_callable = update_callable
        
        self._SetLabel()
        
    
    def _Edit( self ):
        
        domain_manager = HG.client_controller.network_engine.domain_manager
        
        # maybe relegate to hidden page and something like "(does not work)" if no gallery url class match
        
        my_gug = domain_manager.GetGUG( self._gug_key_and_name )
        
        gugs = list( domain_manager.GetGUGs() )
        gug_keys_to_display = domain_manager.GetGUGKeysToDisplay()
        
        gugs.sort( key = lambda g: g.GetName() )
        
        functional_gugs = []
        non_functional_gugs = []
        
        for gug in gugs:
            
            if gug.IsFunctional():
                
                functional_gugs.append( gug )
                
            else:
                
                non_functional_gugs.append( gug )
                
            
        
        choice_tuples = [ ( gug.GetName(), gug ) for gug in functional_gugs if gug.GetGUGKey() in gug_keys_to_display ]
        
        second_choice_tuples = [ ( gug.GetName(), gug ) for gug in functional_gugs if gug.GetGUGKey() not in gug_keys_to_display ]
        
        if len( second_choice_tuples ) > 0:
            
            choice_tuples.append( ( '--other galleries', -1 ) )
            
        
        if len( non_functional_gugs ) > 0:
            
            non_functional_choice_tuples = []
            
            for gug in non_functional_gugs:
                
                s = gug.GetName()
                
                try:
                    
                    gug.CheckFunctional()
                    
                except HydrusExceptions.ParseException as e:
                    
                    s = '{} ({})'.format( gug.GetName(), e )
                    
                
                non_functional_choice_tuples.append( ( s, gug ) )
                
            
            choice_tuples.append( ( '--non-functional galleries', -2 ) )
            
        
        try:
            
            gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', choice_tuples, value_to_select = my_gug, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if gug == -1:
            
            try:
                
                gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', second_choice_tuples, value_to_select = my_gug, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        elif gug == -2:
            
            try:
                
                gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', non_functional_choice_tuples, value_to_select = my_gug, sort_tuples = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        
        gug_key_and_name = gug.GetGUGKeyAndName()
        
        self._SetValue( gug_key_and_name )
        
    
    def _SetLabel( self ):
        
        label = self._gug_key_and_name[1]
        
        gug = HG.client_controller.network_engine.domain_manager.GetGUG( self._gug_key_and_name )
        
        if gug is None:
            
            label = 'not found: ' + label
            
        
        self.setText( label )
        
    
    def _SetValue( self, gug_key_and_name ):
        
        self._gug_key_and_name = gug_key_and_name
        
        self._SetLabel()
        
        if self._update_callable is not None:
            
            self._update_callable( gug_key_and_name )
            
        
    
    def GetValue( self ):
        
        return self._gug_key_and_name
        
    
    def SetValue( self, gug_key_and_name ):
        
        self._SetValue( gug_key_and_name )
        
    
class TagImportOptionsButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, tag_import_options, show_downloader_options, update_callable = None, allow_default_selection = False ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'tag import options', self._EditOptions )
        
        self._tag_import_options = tag_import_options
        self._show_downloader_options = show_downloader_options
        self._update_callable = update_callable
        self._allow_default_selection = allow_default_selection
        
        self._SetToolTip()
        
        #
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
    
    def _Copy( self ):
        
        json_string = self._tag_import_options.DumpToString()
        
        HG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag import options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditTagImportOptionsPanel( dlg, self._tag_import_options, self._show_downloader_options, allow_default_selection = self._allow_default_selection )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                tag_import_options = panel.GetValue()
                
                self._SetValue( tag_import_options )
                
            
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            tag_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( tag_import_options, TagImportOptions.TagImportOptions ):
                
                raise Exception( 'Not a Tag Import Options!' )
                
            
            self._tag_import_options = tag_import_options
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
            HydrusData.ShowException( e )
            
        
    
    def _SetDefault( self ):
        
        self._tag_import_options.SetDefault()
        
    
    def _SetToolTip( self ):
        
        summary = self._tag_import_options.GetSummary( self._show_downloader_options )
        
        self.setToolTip( summary )
        
    
    def _SetValue( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._tag_import_options )
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            ClientGUICommon.BetterButton.mouseReleaseEvent( self, event )
            
            return
            
        
        self.ShowMenu()
        
    
    def ShowMenu( self ):
        
        menu = QW.QMenu()
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy to clipboard', 'Serialise this tag import options and copy it to clipboard.', self._Copy )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'paste from clipboard', 'Try to import serialised tag import options from the clipboard.', self._Paste )
        
        if not self._tag_import_options.IsDefault():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'set to default', 'Set this tag import options to defer to the defaults.', self._SetDefault )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def GetValue( self ):
        
        return self._tag_import_options
        
    
    def SetNamespaces( self, namespaces ):
        
        self._namespaces = namespaces
        
    
    def SetValue( self, tag_import_options ):
        
        self._SetValue( tag_import_options )
        
    
class WatcherReviewPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, page_key, name = 'watcher' ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, name )
        
        self._page_key = page_key
        self._watcher = None
        
        self._watcher_subject = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._watcher_url = QW.QLineEdit( self )
        self._watcher_url.setReadOnly( True )
        
        self._options_panel = QW.QWidget( self )
        
        #
        
        imports_panel = ClientGUICommon.StaticBox( self._options_panel, 'imports' )
        
        self._files_pause_button = ClientGUICommon.BetterBitmapButton( imports_panel, CC.global_pixmaps().file_pause, self.PauseFiles )
        self._files_pause_button.setToolTip( 'pause/play files' )
        
        self._file_status = ClientGUICommon.BetterStaticText( imports_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( imports_panel, HG.client_controller, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( imports_panel )
        
        #
        
        checker_panel = ClientGUICommon.StaticBox( self._options_panel, 'checker' )
        
        self._file_velocity_status = ClientGUICommon.BetterStaticText( checker_panel, ellipsize_end = True )
        
        self._checking_pause_button = ClientGUICommon.BetterBitmapButton( checker_panel, CC.global_pixmaps().gallery_pause, self.PauseChecking )
        self._checking_pause_button.setToolTip( 'pause/play checking' )
        
        self._watcher_status = ClientGUICommon.BetterStaticText( checker_panel, ellipsize_end = True )
        
        self._check_now_button = QW.QPushButton( 'check now', checker_panel )
        self._check_now_button.clicked.connect( self.EventCheckNow )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( checker_panel, HG.client_controller, True, False, 'check', page_key = self._page_key )
        
        checker_options = ClientImportOptions.CheckerOptions()
        
        self._checker_options_button = CheckerOptionsButton( checker_panel, checker_options, update_callable = self._SetCheckerOptions )
        
        self._checker_download_control = ClientGUINetworkJobControl.NetworkJobControl( checker_panel )
        
        file_import_options = FileImportOptions.FileImportOptions()
        tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
        show_downloader_options = True
        
        self._file_import_options = FileImportOptionsButton( self, file_import_options, show_downloader_options, self._SetFileImportOptions )
        self._tag_import_options = TagImportOptionsButton( self, tag_import_options, show_downloader_options, update_callable = self._SetTagImportOptions, allow_default_selection = True )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._file_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._files_pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        imports_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        imports_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        imports_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox_1 = QP.HBoxLayout()
        
        QP.AddToLayout( hbox_1, self._file_velocity_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox_1, self._checking_pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox_2 = QP.HBoxLayout()
        
        QP.AddToLayout( hbox_2, self._watcher_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox_2, self._check_now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        checker_panel.Add( hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        checker_panel.Add( hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        checker_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        checker_panel.Add( self._checker_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        checker_panel.Add( self._checker_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, imports_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, checker_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._options_panel.setLayout( vbox )
        
        self.Add( self._watcher_subject, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._watcher_url, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._options_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._UpdateControlsForNewWatcher()
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _SetCheckerOptions( self, checker_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetCheckerOptions( checker_options )
            
        
    
    def _SetFileImportOptions( self, file_import_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetFileImportOptions( file_import_options )
            
        
    
    def _SetTagImportOptions( self, tag_import_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetTagImportOptions( tag_import_options )
            
        
    
    def _UpdateControlsForNewWatcher( self ):
        
        if self._watcher is None:
            
            self._options_panel.setEnabled( False )
            
            self._file_import_options.setEnabled( False )
            self._tag_import_options.setEnabled( False )
            
            self._watcher_subject.clear()
            
            self._watcher_url.clear()
            
            self._file_status.clear()
            
            self._file_velocity_status.clear()
            
            self._watcher_status.clear()
            
            self._file_seed_cache_control.SetFileSeedCache( None )
            
            self._gallery_seed_log_control.SetGallerySeedLog( None )
            
            self._file_download_control.ClearNetworkJob()
            self._checker_download_control.ClearNetworkJob()
            
        else:
            
            self._options_panel.setEnabled( True )
            
            self._file_import_options.setEnabled( True )
            self._tag_import_options.setEnabled( True )
            
            if self._watcher.HasURL():
                
                url = self._watcher.GetURL()
                
                self._watcher_url.setText( url )
                
            else:
                
                self._watcher_url.clear()
                
            
            checker_options = self._watcher.GetCheckerOptions()
            
            self._checker_options_button.SetValue( checker_options )
            
            file_import_options = self._watcher.GetFileImportOptions()
            
            self._file_import_options.SetValue( file_import_options )
            
            tag_import_options = self._watcher.GetTagImportOptions()
            
            self._tag_import_options.SetValue( tag_import_options )
            
            file_seed_cache = self._watcher.GetFileSeedCache()
            
            self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
            
            gallery_seed_log = self._watcher.GetGallerySeedLog()
            
            self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
            
        
    
    def _UpdateStatus( self ):
        
        if self._watcher is not None:
            
            ( file_status, files_paused, file_velocity_status, next_check_time, watcher_status, subject, checking_status, check_now, checking_paused ) = self._watcher.GetStatus()
            
            if files_paused:
                
                if file_status == '':
                    
                    file_status = 'paused'
                    
                else:
                    
                    file_status = 'pausing, ' + file_status
                    
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._files_pause_button, CC.global_pixmaps().file_play )
                
            else:
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._files_pause_button, CC.global_pixmaps().file_pause )
                
            
            self._file_status.setText( file_status )
            
            self._file_velocity_status.setText( file_velocity_status )
            
            if checking_paused:
                
                if watcher_status == '':
                    
                    watcher_status = 'paused'
                    
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._checking_pause_button, CC.global_pixmaps().gallery_play )
                
            else:
                
                if watcher_status == '' and next_check_time is not None:
                    
                    if HydrusData.TimeHasPassed( next_check_time ):
                        
                        watcher_status = 'checking imminently'
                        
                    else:
                        
                        watcher_status = 'next check ' + ClientData.TimestampToPrettyTimeDelta( next_check_time, just_now_threshold = 0 )
                        
                    
                
                ClientGUIFunctions.SetBitmapButtonBitmap( self._checking_pause_button, CC.global_pixmaps().gallery_pause )
                
            
            self._watcher_status.setText( watcher_status )
            
            if checking_status == ClientImporting.CHECKER_STATUS_404:
                
                self._checking_pause_button.setEnabled( False )
                
            elif checking_status == ClientImporting.CHECKER_STATUS_DEAD:
                
                self._checking_pause_button.setEnabled( False )
                
            else:
                
                self._checking_pause_button.setEnabled( True )
                
            
            if subject in ( '', 'unknown subject' ):
                
                subject = 'no subject'
                
            
            self._watcher_subject.setText( subject )
            
            if check_now:
                
                self._check_now_button.setEnabled( False )
                
            else:
                
                self._check_now_button.setEnabled( True )
                
            
            ( file_network_job, checker_network_job ) = self._watcher.GetNetworkJobs()
            
            if file_network_job is None:
                
                self._file_download_control.ClearNetworkJob()
                
            else:
                
                self._file_download_control.SetNetworkJob( file_network_job )
                
            
            if checker_network_job is None:
                
                self._checker_download_control.ClearNetworkJob()
                
            else:
                
                self._checker_download_control.SetNetworkJob( checker_network_job )
                
            
        
    
    def EventCheckNow( self ):
        
        if self._watcher is not None:
            
            self._watcher.CheckNow()
            
            self._UpdateStatus()
            
        
    
    def PauseChecking( self ):
        
        if self._watcher is not None:
            
            self._watcher.PausePlayChecking()
            
            self._UpdateStatus()
            
        
    
    def PauseFiles( self ):
        
        if self._watcher is not None:
            
            self._watcher.PausePlayFiles()
            
            self._UpdateStatus()
            
        
    
    def SetWatcher( self, watcher ):
        
        self._watcher = watcher
        
        self._UpdateControlsForNewWatcher()
        
    
    def TIMERUIUpdate( self ):
        
        if HG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._UpdateStatus()
            
        
    
