import collections
import collections.abc
import os
import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIFileSeedCache
from hydrus.client.gui.importing import ClientGUIGallerySeedLog
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMetadataMigration
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationTest
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIRegex
from hydrus.client.importing import ClientImporting
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters

class CheckerOptionsButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal( ClientImportOptions.CheckerOptions )
    
    def __init__( self, parent, checker_options: ClientImportOptions.CheckerOptions ):
        
        super().__init__( parent, 'checker options', self._EditOptions )
        
        self._checker_options = checker_options
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit checker options' ) as dlg:
            
            panel = ClientGUITime.EditCheckerOptions( dlg, self._checker_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                checker_options = panel.GetValue()
                
                self._SetValue( checker_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( self._checker_options.GetSummary() ) )
        
    
    def _SetValue( self, checker_options ):
        
        self._checker_options = checker_options
        
        self._SetToolTip()
        
        self.valueChanged.emit( self._checker_options )
        
    
    def GetValue( self ):
        
        return self._checker_options
        
    
    def SetValue( self, checker_options ):
        
        self._SetValue( checker_options )
        
    

class CheckBoxLineEdit( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, placeholder_text ):
        
        super().__init__( parent )
        
        self._checkbox = QW.QCheckBox( self )
        
        self._lineedit = QW.QLineEdit( self )
        self._lineedit.setMinimumWidth( 100 )
        
        self._lineedit.setPlaceholderText( placeholder_text )
        
        self._checkbox.clicked.connect( self.valueChanged )
        self._lineedit.textEdited.connect( self._LineEditChanged )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._lineedit, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( hbox )
        
    
    def _LineEditChanged( self ):
        
        # if the user unchecks and then clears the text, we won't re-check, but otherwise check on text change
        if self._lineedit.text() != '' and not self._checkbox.isChecked():
            
            self._checkbox.setChecked( True )
            
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        return self._lineedit.text()
        
    
    def IsChecked( self ):
        
        return self._checkbox.isChecked()
        
    
    def SetChecked( self, value ):
        
        self._checkbox.setChecked( value )
        
    
    def SetValue( self, text ):
        
        self._lineedit.setText( text )
        
    

class FilenameTaggingOptionsPanel( QW.QWidget ):
    
    movePageLeft = QC.Signal()
    movePageRight = QC.Signal()
    tagsChanged = QC.Signal()
    
    def __init__( self, parent, service_key, filename_tagging_options = None, present_for_accompanying_file_list = False ):
        
        if filename_tagging_options is None:
            
            # pull from an options default
            
            filename_tagging_options = TagImportOptions.FilenameTaggingOptions()
            
        
        super().__init__( parent )
        
        self._service_key = service_key
        
        self._notebook = QW.QTabWidget( self )
        
        # eventually these will take 'regexoptions' or whatever object and 'showspecificfiles' as well
        
        self._simple_panel = self._SimplePanel( self._notebook, self._service_key, filename_tagging_options, present_for_accompanying_file_list )
        self._advanced_panel = self._AdvancedPanel( self._notebook, self._service_key, filename_tagging_options, present_for_accompanying_file_list )
        
        self._simple_panel.movePageLeft.connect( self.movePageLeft )
        self._simple_panel.movePageRight.connect( self.movePageRight )
        
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
        
        tags = CG.client_controller.tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_STORAGE, self._service_key, tags )
        
        return tags
        
    
    def SetSearchFocus( self ):
        
        if self._notebook.currentWidget() == self._simple_panel:
            
            self._simple_panel.SetSearchFocus()
        
    
    def SetSelectedPaths( self, paths ):
        
        self._simple_panel.SetSelectedPaths( paths )
        
    
    class _AdvancedPanel( QW.QWidget ):
        
        tagsChanged = QC.Signal()
        
        def __init__( self, parent, service_key, filename_tagging_options, present_for_accompanying_file_list ):
            
            super().__init__( parent )
            
            self._service_key = service_key
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
            
            quick_namespaces_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._quick_namespaces_panel )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_QUICK_NAMESPACES.ID, self._ConvertQuickRegexDataToDisplayTuple, self._ConvertQuickRegexDataToSortTuple )
            
            self._quick_namespaces_list = ClientGUIListCtrl.BetterListCtrlTreeView( quick_namespaces_listctrl_panel, 4, model, use_simple_delete = True, activation_callback = self.EditQuickNamespaces )
            
            quick_namespaces_listctrl_panel.SetListCtrl( self._quick_namespaces_list )
            
            quick_namespaces_listctrl_panel.AddButton( 'add', self.AddQuickNamespace )
            quick_namespaces_listctrl_panel.AddButton( 'edit', self.EditQuickNamespaces, enabled_only_on_single_selection = True )
            quick_namespaces_listctrl_panel.AddDeleteButton()
            
            #
            
            self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
            
            self._regexes = ClientGUIListBoxes.BetterQListWidget( self._regexes_panel )
            self._regexes.itemDoubleClicked.connect( self.EventRemoveRegex )
            
            self._regex_input = ClientGUIRegex.RegexInput( self )
            
            #
            
            self._num_panel = ClientGUICommon.StaticBox( self, '#' )
            
            self._num_base = ClientGUICommon.BetterSpinBox( self._num_panel, min=-10000000, max=10000000, width = 60 )
            self._num_base.setValue( 1 )
            self._num_base.valueChanged.connect( self.tagsChanged )
            
            self._num_step = ClientGUICommon.BetterSpinBox( self._num_panel, min=-1000000, max=1000000, width = 60 )
            self._num_step.setValue( 1 )
            self._num_step.valueChanged.connect( self.tagsChanged )
            
            self._num_namespace = QW.QLineEdit( self._num_panel )
            self._num_namespace.setFixedWidth( 100 )
            self._num_namespace.textChanged.connect( self.tagsChanged )
            
            if not self._present_for_accompanying_file_list:
                
                self._num_panel.hide()
                
            
            #
            
            ( quick_namespaces, regexes ) = filename_tagging_options.AdvancedToTuple()
            
            self._quick_namespaces_list.AddDatas( quick_namespaces )
            
            self._quick_namespaces_list.Sort()
            
            for regex in regexes:
                
                self._regexes.Append( regex, regex )
                
            
            #
            
            self._quick_namespaces_panel.Add( quick_namespaces_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self._regexes_panel.Add( self._regexes, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._regexes_panel.Add( self._regex_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
            self._regex_input.SetEnterCallable( self.AddRegex )
            
        
        def _ConvertQuickRegexDataToDisplayTuple( self, data ):
            
            ( namespace, regex ) = data
            
            display_tuple = ( namespace, regex )
            
            return display_tuple
            
        
        _ConvertQuickRegexDataToSortTuple = _ConvertQuickRegexDataToDisplayTuple
        
        def AddQuickNamespace( self ):
            
            with ClientGUIDialogs.DialogInputNamespaceRegex( self ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    ( namespace, regex ) = dlg.GetInfo()
                    
                    data = ( namespace, regex )
                    
                    self._quick_namespaces_list.AddData( data, select_sort_and_scroll = True )
                    
                
            
        
        def EditQuickNamespaces( self ):
            
            old_data = self._quick_namespaces_list.GetTopSelectedData()
            
            if old_data is None:
                
                return
                
            
            ( namespace, regex ) = old_data
            
            with ClientGUIDialogs.DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    ( new_namespace, new_regex ) = dlg.GetInfo()
                    
                    new_data = ( new_namespace, new_regex )
                    
                    if new_data != old_data:
                        
                        self._quick_namespaces_list.ReplaceData( old_data, new_data, sort_and_scroll = True )
                        
                    
                
            
        
        def AddRegex( self ):
            
            regex = self._regex_input.GetValue()
            
            if regex != '':
                
                try:
                    
                    re.compile( regex )
                    
                except Exception as e:
                    
                    text = 'That regex would not compile!'
                    text += '\n' * 2
                    text += str( e )
                    
                    ClientGUIDialogsMessage.ShowWarning( self, text )
                    
                    return
                    
                
                self._regexes.Append( regex, regex )
                
                self._regex_input.SetValue( '' )
                
                self.tagsChanged.emit()
                
            
        
        def EventRemoveRegex( self, item ):
            
            if self._regexes.GetNumSelected() > 0:
                
                selected = list( self._regexes.GetData( only_selected = True ) )
                
                self._regex_input.SetValue( selected[0] )
                
                self._regexes.DeleteSelected()
                
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
            
            regexes = self._regexes.GetData()
            
            filename_tagging_options.AdvancedSetTuple( quick_namespaces, regexes )
            
        
    
    class _SimplePanel( QW.QWidget ):
        
        movePageLeft = QC.Signal()
        movePageRight = QC.Signal()
        tagsChanged = QC.Signal()
        
        def __init__( self, parent, service_key, filename_tagging_options, present_for_accompanying_file_list ):
            
            super().__init__( parent )
            
            self._service_key = service_key
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
            
            self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._tags_panel, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._tag_autocomplete_all = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tags_panel, self.EnterTags, default_location_context, service_key, show_paste_button = True )
            
            self._tag_autocomplete_all.movePageLeft.connect( self.movePageLeft )
            self._tag_autocomplete_all.movePageRight.connect( self.movePageRight )
            self._tag_autocomplete_all.externalCopyKeyPressEvent.connect( self._tags.keyPressEvent )
            
            self._tags.tagsChanged.connect( self._tag_autocomplete_all.SetContextTags )
            
            self._tags_paste_button = ClientGUICommon.BetterButton( self._tags_panel, 'paste tags', self._PasteTags )
            
            #
            
            self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for selected files' )
            
            self._paths_to_single_tags = collections.defaultdict( set )
            
            self._single_tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._single_tags_panel, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
            
            self._single_tags_paste_button = ClientGUICommon.BetterButton( self._single_tags_panel, 'paste tags', self._PasteSingleTags )
            
            self._tag_autocomplete_selection = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.EnterTagsSingle, default_location_context, service_key, show_paste_button = True )
            
            self._tag_autocomplete_selection.movePageLeft.connect( self.movePageLeft )
            self._tag_autocomplete_selection.movePageRight.connect( self.movePageRight )
            self._tag_autocomplete_selection.externalCopyKeyPressEvent.connect( self._single_tags.keyPressEvent )
            
            self._single_tags.tagsChanged.connect( self._tag_autocomplete_selection.SetContextTags )
            
            self.SetSelectedPaths( [] )
            
            if not self._present_for_accompanying_file_list:
                
                self._single_tags_panel.hide()
                
            
            #
            
            self._checkboxes_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            rows = []
            
            self._filename_namespace = CheckBoxLineEdit( self._checkboxes_panel, 'namespace' )
            
            rows.append( ( 'add filename?', self._filename_namespace ) )
            
            # TODO: Ok, when we move to arbitrary string processing from filenames, and we scrub this, we will want 'easy-add rule' buttons to do this
            # When we do, add a thing that adds the nth, including negative n index values. as some users want four deep
            # there must be a way to wangle this code into String Processors
            
            self._directory_namespace_controls = {}
            
            directory_items = []
            
            directory_items.append( ( 0, 'first' ) )
            directory_items.append( ( 1, 'second' ) )
            directory_items.append( ( 2, 'third' ) )
            directory_items.append( ( -3, 'third last' ) )
            directory_items.append( ( -2, 'second last' ) )
            directory_items.append( ( -1, 'last' ) )
            
            for ( index, phrase ) in directory_items:
                
                widget = CheckBoxLineEdit( self._checkboxes_panel, 'namespace' )
                
                rows.append( ( f'add {phrase} directory?', widget ) )
                
                self._directory_namespace_controls[ index ] = widget
                
            
            filename_gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            #
            
            ( tags_for_all, add_filename, directory_dict ) = filename_tagging_options.SimpleToTuple()
            
            self._tags.AddTags( tags_for_all )
            
            ( add_filename_boolean, add_filename_namespace ) = add_filename
            
            self._filename_namespace.SetChecked( add_filename_boolean )
            self._filename_namespace.SetValue( add_filename_namespace )
            
            for ( index, ( dir_boolean, dir_namespace ) ) in directory_dict.items():
                
                widget = self._directory_namespace_controls[ index ]
                
                widget.SetChecked( dir_boolean )
                widget.SetValue( dir_namespace )
                
                widget.valueChanged.connect( self.tagsChanged )
                
            
            #
            
            self._tags_panel.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._tags_panel.Add( self._tag_autocomplete_all, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._tags_panel.Add( self._tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._single_tags_panel.Add( self._single_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._single_tags_panel.Add( self._tag_autocomplete_selection, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._single_tags_panel.Add( self._single_tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._checkboxes_panel.Add( filename_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._checkboxes_panel.Add( QW.QWidget( self._checkboxes_panel ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._single_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._checkboxes_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.setLayout( hbox )
            
            #
            
            self._tags.tagsRemoved.connect( self.tagsChanged )
            self._single_tags.tagsRemoved.connect( self.SingleTagsRemoved )
            
            self._filename_namespace.valueChanged.connect( self.tagsChanged )
            
            self._tag_autocomplete_all.tagsPasted.connect( self.EnterTagsOnlyAdd )
            self._tag_autocomplete_selection.tagsPasted.connect( self.EnterTagsSingleOnlyAdd )
            
        
        def _GetTagsFromClipboard( self ):
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
                
                return
                
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( raw_text )
                
                tags = HydrusTags.CleanTags( tags )
                
                return tags
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of tags', e )
                
                raise
                
            
        
        def _PasteTags( self ):
            
            try:
                
                tags = self._GetTagsFromClipboard()
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
                
                return
                
            
            self.EnterTags( tags )
            
        
        def _PasteSingleTags( self ):
            
            try:
                
                tags = self._GetTagsFromClipboard()
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
                
                return
                
            
            self.EnterTagsSingle( tags )
            
        
        def EnterTags( self, tags ):
            
            CG.client_controller.Write( 'push_recent_tags', self._service_key, tags )
            
            if len( tags ) > 0:
                
                self._tags.AddTags( tags )
                
                self.tagsChanged.emit()
                
            
        
        def EnterTagsOnlyAdd( self, tags ):
            
            current_tags = self._tags.GetTags()
            
            tags = { tag for tag in tags if tag not in current_tags }
            
            if len( tags ) > 0:
                
                self.EnterTags( tags )
                
            
        
        def EnterTagsSingle( self, tags ):
            
            CG.client_controller.Write( 'push_recent_tags', self._service_key, tags )
            
            if len( tags ) > 0:
                
                self._single_tags.AddTags( tags )
                
                for path in self._selected_paths:
                    
                    current_tags = self._paths_to_single_tags[ path ]
                    
                    current_tags.update( tags )
                    
                
                self.tagsChanged.emit()
                
            
        
        def EnterTagsSingleOnlyAdd( self, tags ):
            
            current_tags = self._single_tags.GetTags()
            
            tags = { tag for tag in tags if tag not in current_tags }
            
            if len( tags ) > 0:
                
                self.EnterTagsSingle( tags )
                
            
        
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
            
        
        def SetSearchFocus( self ):
            
            ClientGUIFunctions.SetFocusLater( self._tag_autocomplete_all )
            
        
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
            
            add_filename = ( self._filename_namespace.IsChecked(), self._filename_namespace.GetValue() )
            
            directories_dict = {}
            
            for ( index, widget ) in self._directory_namespace_controls.items():
                
                directories_dict[ index ] = ( widget.IsChecked(), widget.GetValue() )
                
            
            filename_tagging_options.SimpleSetTuple( tags_for_all, add_filename, directories_dict )
            
        
    

class EditLocalImportFilenameTaggingPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, paths ):
        
        # TODO: a really nice rewrite for all this, perhaps when I go for string conversions here, would be to eliminate the multi-page format and instead update the controls.
        # an option here is to mutate the sidecars a little and just have a 'filename' source. this could wangle everything neatly and send to whatever service
        # but only if the UI can stay helpful. maybe we shouldn't replace the easy UI, but we can replace the guts behind the scenes with metadata routers
        # however, changing service while maintaining focus and list selection would be great
        
        super().__init__( parent )
        
        self._paths = paths
        
        self._filename_tagging_option_pages = []
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        # TODO: could have default import here and favourites system
        metadata_routers = []
        
        self._metadata_router_page = self._MetadataRoutersPanel( self._notebook, metadata_routers, paths )
        
        self._notebook.addTab( self._metadata_router_page, 'sidecars' )
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._FilenameTaggingOptionsPanel( self._notebook, service_key, paths )
            
            self._filename_tagging_option_pages.append( page )
            
            page.movePageLeft.connect( self.MovePageLeft )
            page.movePageRight.connect( self.MovePageRight )
            
            self._notebook.addTab( page, name )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab = first tab disappears bug
                CG.client_controller.CallAfterQtSafe( self, self._notebook.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._notebook.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
        CG.client_controller.CallAfterQtSafe( self, self._SetSearchFocus )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if self.sender() != self._notebook:
            
            return
            
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page: EditLocalImportFilenameTaggingPanel._FilenameTaggingOptionsPanel = self._notebook.currentWidget()
            
            if current_page in self._filename_tagging_option_pages:
                
                CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
                
            
        
    
    def _SetSearchFocus( self ):
        
        current_page: EditLocalImportFilenameTaggingPanel._FilenameTaggingOptionsPanel = self._notebook.currentWidget()
        
        current_page.SetSearchFocus()
        
    
    def GetValue( self ):
        
        metadata_routers = self._metadata_router_page.GetValue()
        
        paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
        
        for page in self._filename_tagging_option_pages:
            
            ( service_key, paths_to_tags ) = page.GetInfo()
            
            for ( path, tags ) in paths_to_tags.items():
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                paths_to_additional_service_keys_to_tags[ path ][ service_key ] = tags
                
            
        
        return ( metadata_routers, paths_to_additional_service_keys_to_tags )
        
    
    def MovePageLeft( self ):
        
        self._notebook.SelectLeft()
        
        self._SetSearchFocus()
        
    
    def MovePageRight( self ):
        
        self._notebook.SelectRight()
        
        self._SetSearchFocus()
        
    
    class _FilenameTaggingOptionsPanel( QW.QWidget ):
        
        movePageLeft = QC.Signal()
        movePageRight = QC.Signal()
        
        def __init__( self, parent, service_key, paths ):
            
            super().__init__( parent )
            
            self._service_key = service_key
            self._paths = paths
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_PATHS_TO_TAGS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
            
            self._paths_list = ClientGUIListCtrl.BetterListCtrlTreeView( self, 10, model )
            
            self._paths_list.selectionModel().selectionChanged.connect( self.EventItemSelected )
            
            #
            
            self._filename_tagging_panel = FilenameTaggingOptionsPanel( self, self._service_key, present_for_accompanying_file_list = True )
            
            self._filename_tagging_panel.movePageLeft.connect( self.movePageLeft )
            self._filename_tagging_panel.movePageRight.connect( self.movePageRight )
            
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
            
        
        def _ConvertDataToDisplayTuple( self, data ):
            
            ( index, path ) = data
            
            tags = self._GetTags( index, path )
            
            pretty_index = HydrusNumbers.ToHumanInt( index + 1 )
            
            pretty_tags = ', '.join( tags )
            
            return ( pretty_index, path, pretty_tags )
            
        
        def _ConvertDataToSortTuple( self, data ):
            
            ( index, path ) = data
            
            return ( index, path, index )
            
        
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
                
            
            self._schedule_refresh_file_list_job = CG.client_controller.CallLaterQtSafe( self, 0.5, 'refresh path list', self.RefreshFileList )
            
        
        def SetSearchFocus( self ):
            
            self._filename_tagging_panel.SetSearchFocus()
            
        
    
    class _MetadataRoutersPanel( QW.QWidget ):
        
        def __init__( self, parent, metadata_routers, paths ):
            
            super().__init__( parent )
            
            self._paths = paths
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_PATHS_TO_TAGS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
            
            self._paths_list = ClientGUIListCtrl.BetterListCtrlTreeView( self, 10, model )
            
            allowed_importer_classes = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT, ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON ]
            allowed_exporter_classes = [ ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps ]
            test_context_factory = ClientGUIMetadataMigrationTest.MigrationTestContextFactorySidecar( self._paths[ : ClientGUIMetadataMigrationTest.HOW_MANY_EXAMPLE_OBJECTS_TO_USE ] )
            
            self._metadata_routers_panel = ClientGUICommon.StaticBox( self, 'sidecar import routes' )
            
            self._metadata_routers_control = ClientGUIMetadataMigration.SingleFileMetadataRoutersControl( self, metadata_routers, allowed_importer_classes, allowed_exporter_classes, test_context_factory )
            
            #
            
            self._schedule_refresh_file_list_job = None
            
            #
            
            # i.e. ( index, path )
            self._paths_list.AddDatas( list( enumerate( self._paths ) ) )
            
            #
            
            self._metadata_routers_panel.Add( self._metadata_routers_control, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            label = 'You can import tags, URLs, and other metadata via "sidecars", which are little text files accompanying each import file. For instance, where importing "cool_image.jpg", you can tell hydrus to check "cool_image.jpg.txt" for a list of tags to add.'
            
            st = ClientGUICommon.BetterStaticText( self, label )
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._metadata_routers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            self._metadata_routers_control.listBoxChanged.connect( self.ScheduleRefreshFileList )
            
        
        def _ConvertDataToDisplayTuple( self, data ):
            
            ( index, path ) = data
            
            strings = self._GetPrettyStrings( path )
            
            pretty_index = HydrusNumbers.ToHumanInt( index + 1 )
            
            pretty_path = path
            pretty_strings = ', '.join( strings )
            
            return ( pretty_index, pretty_path, pretty_strings )
            
        
        def _ConvertDataToSortTuple( self, data ):
            
            ( index, path ) = data
            
            return ( index, path, index )
            
        
        def _GetPrettyStrings( self, path ):
            
            strings = []
            
            metadata_routers = self._metadata_routers_control.GetValue()
            
            for router in metadata_routers:
                
                pre_processed_strings = set()
                
                for importer in router.GetImporters():
                    
                    if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar ):
                        
                        pre_processed_strings.update( importer.Import( path ) )
                        
                    else:
                        
                        continue
                        
                    
                
                if len( pre_processed_strings ) == 0:
                    
                    continue
                    
                
                processed_strings = router.GetStringProcessor().ProcessStrings( pre_processed_strings )
                
                exporter = router.GetExporter()
                
                if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
                    
                    processed_strings = HydrusTags.CleanTags( processed_strings )
                    
                elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes ):
                    
                    processed_strings = [ f'note: {HydrusText.GetFirstLineSummary( s )}' for s in processed_strings ]
                    
                
                strings.extend( sorted( processed_strings ) )
                
            
            return strings
            
        
        def GetValue( self ):
            
            return self._metadata_routers_control.GetValue()
            
        
        def RefreshFileList( self ):
            
            self._paths_list.UpdateDatas()
            
        
        def ScheduleRefreshFileList( self ):
            
            if self._schedule_refresh_file_list_job is not None:
                
                self._schedule_refresh_file_list_job.Cancel()
                
                self._schedule_refresh_file_list_job = None
                
            
            self._schedule_refresh_file_list_job = CG.client_controller.CallLaterQtSafe( self, 0.5, 'refresh path list', self.RefreshFileList )
            
        
        def SetSearchFocus( self ):
            
            pass
            
        
    
class EditFilenameTaggingOptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_key, filename_tagging_options, example_path = None ):
        
        super().__init__( parent )
        
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
        
        if example_path is not None:
            
            self._example_path_input.setText( example_path )
            
        
    
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
            
        
        self._schedule_refresh_tags_job = CG.client_controller.CallLaterQtSafe( self, 0.5, 'refresh tags', self.RefreshTags )
        
    
class GalleryImportPanel( ClientGUICommon.StaticBox ):
    
    importOptionsChanged = QC.Signal()
    
    def __init__( self, parent, page_key, name = 'gallery query' ):
        
        super().__init__( parent, name, start_expanded = True, can_expand = True )
        
        self._page_key = page_key
        
        self._gallery_import = None
        
        #
        
        self._query_text = QW.QLineEdit( self )
        self._query_text.setReadOnly( True )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'imports' )
        
        self._file_status = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        self._files_pause_button = ClientGUICommon.IconButton( self._import_queue_panel, CC.global_icons().file_pause, self.PauseFiles )
        self._files_pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play files' ) )
        
        self._gallery_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._gallery_status = ClientGUICommon.BetterStaticText( self._gallery_panel, ellipsize_end = True )
        
        self._gallery_pause_button = ClientGUICommon.IconButton( self._gallery_panel, CC.global_icons().gallery_pause, self.PauseGallery )
        self._gallery_pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play search' ) )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._gallery_panel, False, True, 'search', page_key = self._page_key )
        
        self._gallery_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._gallery_panel )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self, 2000,'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.valueChanged.connect( self.EventFileLimit )
        self._file_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'stop searching the gallery once this many files has been reached' ) )
        
        file_import_options = FileImportOptions.FileImportOptions()
        file_import_options.SetIsDefault( True )
        
        tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        note_import_options.SetIsDefault( True )
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
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
        self.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._import_options_button.fileImportOptionsChanged.connect( self._SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._SetTagImportOptions )
        
        self._file_limit.valueChanged.connect( self.importOptionsChanged )
        self._import_options_button.importOptionsChanged.connect( self.importOptionsChanged )
        
        self._UpdateControlsForNewGalleryImport()
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _SetFileImportOptions( self, file_import_options: FileImportOptions.FileImportOptions ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetFileImportOptions( file_import_options )
            
        
    
    def _SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetNoteImportOptions( note_import_options )
            
        
    
    def _SetTagImportOptions( self, tag_import_options: TagImportOptions.TagImportOptions ):
        
        if self._gallery_import is not None:
            
            self._gallery_import.SetTagImportOptions( tag_import_options )
            
        
    
    def _UpdateControlsForNewGalleryImport( self ):
        
        if self._gallery_import is None:
            
            self._import_queue_panel.setEnabled( False )
            self._gallery_panel.setEnabled( False )
            
            self._file_limit.setEnabled( False )
            self._import_options_button.setEnabled( False )
            
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
            self._import_options_button.setEnabled( True )
            
            query = self._gallery_import.GetQueryText()
            
            self._query_text.setText( query )
            
            file_limit = self._gallery_import.GetFileLimit()
            
            self._file_limit.SetValue( file_limit )
            
            file_import_options = self._gallery_import.GetFileImportOptions()
            tag_import_options = self._gallery_import.GetTagImportOptions()
            note_import_options = self._gallery_import.GetNoteImportOptions()
            
            self._import_options_button.SetFileImportOptions( file_import_options )
            self._import_options_button.SetTagImportOptions( tag_import_options )
            self._import_options_button.SetNoteImportOptions( note_import_options )
            
            file_seed_cache = self._gallery_import.GetFileSeedCache()
            
            self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
            
            gallery_seed_log = self._gallery_import.GetGallerySeedLog()
            
            self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
            
        
    
    def _UpdateStatus( self ):
        
        if self._gallery_import is not None:
            
            ( gallery_status, file_status, files_paused, gallery_paused ) = self._gallery_import.GetStatus()
            
            if files_paused:
                
                self._files_pause_button.SetIconSmart( CC.global_icons().file_play )
                
            else:
                
                self._files_pause_button.SetIconSmart( CC.global_icons().file_pause )
                
            
            if gallery_paused:
                
                self._gallery_pause_button.SetIconSmart( CC.global_icons().gallery_play )
                
            else:
                
                self._gallery_pause_button.SetIconSmart( CC.global_icons().gallery_pause )
                
            
            self._gallery_status.setText( gallery_status )
            
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
        
        if CG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._UpdateStatus()
            
        
    
class GUGKeyAndNameSelector( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, gug_key_and_name, update_callable = None ):
        
        super().__init__( parent, 'gallery selector', self._Edit )
        
        gug = CG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
        
        if gug is not None:
            
            gug_key_and_name = gug.GetGUGKeyAndName()
            
        
        self._gug_key_and_name = gug_key_and_name
        self._update_callable = update_callable
        
        self._SetLabel()
        
    
    def _Edit( self ):
        
        domain_manager = CG.client_controller.network_engine.domain_manager
        
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
            
            choice_tuples.append( ( f'--other galleries{HC.UNICODE_ELLIPSIS}', -1 ) )
            
        
        non_functional_choice_tuples = []
        
        if len( non_functional_gugs ) > 0:
            
            for gug in non_functional_gugs:
                
                s = gug.GetName()
                
                try:
                    
                    gug.CheckFunctional()
                    
                except HydrusExceptions.ParseException as e:
                    
                    s = '{} ({})'.format( gug.GetName(), e )
                    
                
                non_functional_choice_tuples.append( ( s, gug ) )
                
            
            choice_tuples.append( ( f'--non-functional galleries{HC.UNICODE_ELLIPSIS}', -2 ) )
            
        
        try:
            
            gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', choice_tuples, value_to_select = my_gug, sort_tuples = False, allow_insta_one_item_select = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if gug == -1:
            
            try:
                
                gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', second_choice_tuples, value_to_select = my_gug, sort_tuples = False, allow_insta_one_item_select = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        elif gug == -2:
            
            try:
                
                gug = ClientGUIDialogsQuick.SelectFromList( self, 'select gallery', non_functional_choice_tuples, value_to_select = my_gug, sort_tuples = False, allow_insta_one_item_select = False )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        
        gug_key_and_name = gug.GetGUGKeyAndName()
        
        self._SetValue( gug_key_and_name )
        
    
    def _SetLabel( self ):
        
        label = self._gug_key_and_name[1]
        
        gug = CG.client_controller.network_engine.domain_manager.GetGUG( self._gug_key_and_name )
        
        if gug is None:
            
            label = 'not found: ' + label
            
        
        self.setText( label )
        
    
    def _SetValue( self, gug_key_and_name ):
        
        self._gug_key_and_name = gug_key_and_name
        
        self._SetLabel()
        
        if self._update_callable is not None:
            
            self._update_callable( gug_key_and_name )
            
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        return self._gug_key_and_name
        
    
    def SetValue( self, gug_key_and_name ):
        
        self._SetValue( gug_key_and_name )
        
    
class WatcherReviewPanel( ClientGUICommon.StaticBox ):
    
    importOptionsChanged = QC.Signal()
    
    def __init__( self, parent, page_key, name = 'watcher' ):
        
        super().__init__( parent, name, start_expanded = True, can_expand = True )
        
        self._page_key = page_key
        self._watcher = None
        
        self._watcher_subject = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._watcher_url = QW.QLineEdit( self )
        self._watcher_url.setReadOnly( True )
        
        self._options_panel = QW.QWidget( self )
        
        #
        
        imports_panel = ClientGUICommon.StaticBox( self._options_panel, 'imports' )
        
        self._files_pause_button = ClientGUICommon.IconButton( imports_panel, CC.global_icons().file_pause, self.PauseFiles )
        self._files_pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play files' ) )
        
        self._file_status = ClientGUICommon.BetterStaticText( imports_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( imports_panel, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( imports_panel )
        
        #
        
        checker_panel = ClientGUICommon.StaticBox( self._options_panel, 'checker' )
        
        self._file_velocity_status = ClientGUICommon.BetterStaticText( checker_panel, ellipsize_end = True )
        
        self._checking_pause_button = ClientGUICommon.IconButton( checker_panel, CC.global_icons().gallery_pause, self.PauseChecking )
        self._checking_pause_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play checking' ) )
        
        self._watcher_status = ClientGUICommon.BetterStaticText( checker_panel, ellipsize_end = True )
        
        self._check_now_button = QW.QPushButton( 'check now', checker_panel )
        self._check_now_button.clicked.connect( self.EventCheckNow )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( checker_panel, True, False, 'check', page_key = self._page_key )
        
        checker_options = ClientImportOptions.CheckerOptions()
        
        self._checker_options_button = CheckerOptionsButton( checker_panel, checker_options )
        
        self._checker_download_control = ClientGUINetworkJobControl.NetworkJobControl( checker_panel )
        
        file_import_options = FileImportOptions.FileImportOptions()
        file_import_options.SetIsDefault( True )
        
        tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        note_import_options.SetIsDefault( True )
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
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
        checker_panel.Add( self._checker_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        checker_panel.Add( self._checker_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, imports_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, checker_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._options_panel.setLayout( vbox )
        
        self.Add( self._watcher_subject, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._watcher_url, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._options_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._import_options_button.fileImportOptionsChanged.connect( self._SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._SetTagImportOptions )
        
        self._checker_options_button.valueChanged.connect( self._SetCheckerOptions )
        
        self._checker_options_button.valueChanged.connect( self.importOptionsChanged )
        self._import_options_button.importOptionsChanged.connect( self.importOptionsChanged )
        
        self._UpdateControlsForNewWatcher()
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _SetCheckerOptions( self, checker_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetCheckerOptions( checker_options )
            
        
    
    def _SetFileImportOptions( self, file_import_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetFileImportOptions( file_import_options )
            
        
    
    def _SetNoteImportOptions( self, note_import_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetNoteImportOptions( note_import_options )
            
        
    
    def _SetTagImportOptions( self, tag_import_options ):
        
        if self._watcher is not None:
            
            self._watcher.SetTagImportOptions( tag_import_options )
            
        
    
    def _UpdateControlsForNewWatcher( self ):
        
        if self._watcher is None:
            
            self._options_panel.setEnabled( False )
            
            self._import_options_button.setEnabled( False )
            
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
            
            self._import_options_button.setEnabled( True )
            
            if self._watcher.HasURL():
                
                url = self._watcher.GetURL()
                
                self._watcher_url.setText( url )
                
            else:
                
                self._watcher_url.clear()
                
            
            checker_options = self._watcher.GetCheckerOptions()
            
            self._checker_options_button.SetValue( checker_options )
            
            file_import_options = self._watcher.GetFileImportOptions()
            tag_import_options = self._watcher.GetTagImportOptions()
            note_import_options = self._watcher.GetNoteImportOptions()
            
            self._import_options_button.SetFileImportOptions( file_import_options )
            self._import_options_button.SetTagImportOptions( tag_import_options )
            self._import_options_button.SetNoteImportOptions( note_import_options )
            
            file_seed_cache = self._watcher.GetFileSeedCache()
            
            self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
            
            gallery_seed_log = self._watcher.GetGallerySeedLog()
            
            self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
            
        
    
    def _UpdateStatus( self ):
        
        if self._watcher is not None:
            
            ( file_status, files_paused, file_velocity_status, next_check_time, watcher_status, subject, checking_status, check_now, checking_paused ) = self._watcher.GetStatus()
            
            if files_paused:
                
                self._files_pause_button.SetIconSmart( CC.global_icons().file_play )
                
            else:
                
                self._files_pause_button.SetIconSmart( CC.global_icons().file_pause )
                
            
            self._file_status.setText( file_status )
            
            self._file_velocity_status.setText( file_velocity_status )
            
            if checking_paused:
                
                self._checking_pause_button.SetIconSmart( CC.global_icons().gallery_play )
                
            else:
                
                if watcher_status == '' and next_check_time is not None:
                    
                    if HydrusTime.TimeHasPassed( next_check_time ):
                        
                        watcher_status = 'checking imminently'
                        
                    else:
                        
                        watcher_status = 'next check ' + HydrusTime.TimestampToPrettyTimeDelta( next_check_time, just_now_threshold = 0 )
                        
                    
                
                self._checking_pause_button.SetIconSmart( CC.global_icons().gallery_pause )
                
            
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
        
        if CG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._UpdateStatus()
            
        
    
