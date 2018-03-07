import ClientConstants as CC
import ClientGUIACDropdown
import ClientGUICommon
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUITopLevelWindows
import ClientImporting
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusTags
import HydrusText
import os
import re
import wx
import wx.adv

class FileImportOptionsButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, file_import_options, update_callable = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'file import options', self._EditOptions )
        
        self._file_import_options = file_import_options
        self._update_callable = update_callable
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit file import options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditFileImportOptions( dlg, self._file_import_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                file_import_options = panel.GetValue()
                
                self._SetValue( file_import_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.SetToolTip( self._file_import_options.GetSummary() )
        
    
    def _SetValue( self, file_import_options ):
        
        self._file_import_options = file_import_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._file_import_options )
            
        
    
    def GetValue( self ):
        
        return self._file_import_options
        
    
    def SetValue( self, file_import_options ):
        
        self._SetValue( file_import_options )
        
    
class FilenameTaggingOptionsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, tag_update_callable, filename_tagging_options = None, present_for_accompanying_file_list = False ):
        
        if filename_tagging_options is None:
            
            # pull from an options default
            
            filename_tagging_options = ClientImporting.FilenameTaggingOptions()
            
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        
        self._notebook = wx.Notebook( self )
        
        # eventually these will take 'regexoptions' or whatever object and 'showspecificfiles' as well
        
        self._simple_panel = self._SimplePanel( self._notebook, self._service_key, tag_update_callable, filename_tagging_options, present_for_accompanying_file_list )
        self._advanced_panel = self._AdvancedPanel( self._notebook, self._service_key, tag_update_callable, filename_tagging_options, present_for_accompanying_file_list )
        
        self._notebook.AddPage( self._simple_panel, 'simple', select = True )
        self._notebook.AddPage( self._advanced_panel, 'advanced' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetFilenameTaggingOptions( self ):
        
        filename_tagging_options = ClientImporting.FilenameTaggingOptions()
        
        self._advanced_panel.UpdateFilenameTaggingOptions( filename_tagging_options )
        self._simple_panel.UpdateFilenameTaggingOptions( filename_tagging_options )
        
        return filename_tagging_options
        
    
    def GetTags( self, index, path ):
        
        tags = set()
        
        tags.update( self._simple_panel.GetTags( index, path ) )
        tags.update( self._advanced_panel.GetTags( index, path ) )
        
        tags = HydrusTags.CleanTags( tags )
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        tag_censorship_manager = HG.client_controller.GetManager( 'tag_censorship' )
        
        tags = siblings_manager.CollapseTags( self._service_key, tags )
        tags = parents_manager.ExpandTags( self._service_key, tags )
        tags = tag_censorship_manager.FilterTags( self._service_key, tags )
        
        return tags
        
    
    def SetSelectedPaths( self, paths ):
        
        self._simple_panel.SetSelectedPaths( paths )
        
    
    class _AdvancedPanel( wx.Panel ):
        
        def __init__( self, parent, service_key, refresh_callable, filename_tagging_options, present_for_accompanying_file_list ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._refresh_callable = refresh_callable
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
            
            self._quick_namespaces_list = ClientGUIListCtrl.BetterListCtrl( self._quick_namespaces_panel, 'quick_namespaces', 4, 20, [ ( 'namespace', 12 ), ( 'regex', -1 ) ], self._ConvertQuickRegexDataToListCtrlTuples, delete_key_callback = self.DeleteQuickNamespaces, activation_callback = self.EditQuickNamespaces )
            
            self._add_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'add' )
            self._add_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventAddQuickNamespace )
            self._add_quick_namespace_button.SetMinSize( ( 20, -1 ) )
            
            self._edit_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'edit' )
            self._edit_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventEditQuickNamespace )
            self._edit_quick_namespace_button.SetMinSize( ( 20, -1 ) )
            
            self._delete_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'delete' )
            self._delete_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventDeleteQuickNamespace )
            self._delete_quick_namespace_button.SetMinSize( ( 20, -1 ) )
            
            #
            
            self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
            
            self._regexes = wx.ListBox( self._regexes_panel )
            self._regexes.Bind( wx.EVT_LISTBOX_DCLICK, self.EventRemoveRegex )
            
            self._regex_box = wx.TextCtrl( self._regexes_panel, style=wx.TE_PROCESS_ENTER )
            self._regex_box.Bind( wx.EVT_TEXT_ENTER, self.EventAddRegex )
            
            self._regex_shortcuts = ClientGUICommon.RegexButton( self._regexes_panel )
            
            self._regex_intro_link = wx.adv.HyperlinkCtrl( self._regexes_panel, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
            self._regex_practise_link = wx.adv.HyperlinkCtrl( self._regexes_panel, id = -1, label = 'regex practise', url = 'http://regexr.com/3cvmf' )
            
            #
            
            self._num_panel = ClientGUICommon.StaticBox( self, '#' )
            
            self._num_base = wx.SpinCtrl( self._num_panel, min = -10000000, max = 10000000, size = ( 60, -1 ) )
            self._num_base.SetValue( 1 )
            self._num_base.Bind( wx.EVT_SPINCTRL, self.EventRecalcNum )
            
            self._num_step = wx.SpinCtrl( self._num_panel, min = -1000000, max = 1000000, size = ( 60, -1 ) )
            self._num_step.SetValue( 1 )
            self._num_step.Bind( wx.EVT_SPINCTRL, self.EventRecalcNum )
            
            self._num_namespace = wx.TextCtrl( self._num_panel, size = ( 100, -1 ) )
            self._num_namespace.Bind( wx.EVT_TEXT, self.EventNumNamespaceChanged )
            
            if not self._present_for_accompanying_file_list:
                
                self._num_panel.Hide()
                
            
            #
            
            ( quick_namespaces, regexes ) = filename_tagging_options.AdvancedToTuple()
            
            self._quick_namespaces_list.AddDatas( quick_namespaces )
            
            for regex in regexes:
                
                self._regexes.Append( regex )
                
            
            #
            
            button_box = wx.BoxSizer( wx.HORIZONTAL )
            
            button_box.Add( self._add_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
            button_box.Add( self._edit_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
            button_box.Add( self._delete_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._quick_namespaces_panel.Add( self._quick_namespaces_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._quick_namespaces_panel.Add( button_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            self._regexes_panel.Add( self._regexes, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._regexes_panel.Add( self._regex_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._regexes_panel.Add( self._regex_shortcuts, CC.FLAGS_LONE_BUTTON )
            self._regexes_panel.Add( self._regex_intro_link, CC.FLAGS_LONE_BUTTON )
            self._regexes_panel.Add( self._regex_practise_link, CC.FLAGS_LONE_BUTTON )
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( wx.StaticText( self._num_panel, label = '# base/step: ' ), CC.FLAGS_VCENTER )
            hbox.Add( self._num_base, CC.FLAGS_VCENTER )
            hbox.Add( self._num_step, CC.FLAGS_VCENTER )
            
            self._num_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( wx.StaticText( self._num_panel, label = '# namespace: ' ), CC.FLAGS_VCENTER )
            hbox.Add( self._num_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._num_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            second_vbox = wx.BoxSizer( wx.VERTICAL )
            
            second_vbox.Add( self._regexes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            second_vbox.Add( self._num_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._quick_namespaces_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( second_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
        
        def _ConvertQuickRegexDataToListCtrlTuples( self, data ):
            
            ( namespace, regex ) = data
            
            display_tuple = ( namespace, regex )
            sort_tuple = ( namespace, regex )
            
            return ( display_tuple, sort_tuple )
            
        
        def DeleteQuickNamespaces( self ):
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._quick_namespaces_list.DeleteSelected()
                    
                    self._refresh_callable()
                    
                
            
        
        def EditQuickNamespaces( self ):
            
            data_to_edit = self._quick_namespaces_list.GetData( only_selected = True )
            
            for old_data in data_to_edit:
                
                ( namespace, regex ) = old_data
                
                import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( new_namespace, new_regex ) = dlg.GetInfo()
                        
                        new_data = ( new_namespace, new_regex )
                        
                        if new_data != old_data:
                            
                            self._quick_namespaces_list.DeleteDatas( ( old_data, ) )
                            
                            self._quick_namespaces_list.AddDatas( ( new_data, ) )
                            
                        
                    
                
            
            self._refresh_callable()
            
        
        def EventAddRegex( self, event ):
            
            regex = self._regex_box.GetValue()
            
            if regex != '':
                
                try:
                    
                    re.compile( regex, flags = re.UNICODE )
                    
                except Exception as e:
                    
                    text = 'That regex would not compile!'
                    text += os.linesep * 2
                    text += HydrusData.ToUnicode( e )
                    
                    wx.MessageBox( text )
                    
                    return
                    
                
                self._regexes.Append( regex )
                
                self._regex_box.Clear()
                
                self._refresh_callable()
                
            
        
        def EventAddQuickNamespace( self, event ):
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogInputNamespaceRegex( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( namespace, regex ) = dlg.GetInfo()
                    
                    data = ( namespace, regex )
                    
                    self._quick_namespaces_list.AddDatas( ( data, ) )
                    
                    self._refresh_callable()
                    
                
            
        
        def EventDeleteQuickNamespace( self, event ):
            
            self.DeleteQuickNamespaces()
            
        
        def EventEditQuickNamespace( self, event ):
            
            self.EditQuickNamespaces()
            
        
        def EventNumNamespaceChanged( self, event ):
            
            self._refresh_callable()
            
        
        def EventRecalcNum( self, event ):
            
            self._refresh_callable()
            
        
        def EventRemoveRegex( self, event ):
            
            selection = self._regexes.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                if len( self._regex_box.GetValue() ) == 0: self._regex_box.SetValue( self._regexes.GetString( selection ) )
                
                self._regexes.Delete( selection )
                
                self._refresh_callable()
                
            
        
        def GetTags( self, index, path ):
            
            tags = set()
            
            num_namespace = self._num_namespace.GetValue()
            
            if num_namespace != '':
                
                num_base = self._num_base.GetValue()
                num_step = self._num_step.GetValue()
                
                tag_num = num_base + index * num_step
                
                tags.add( num_namespace + ':' + str( tag_num ) )
                
            
            return tags
            
        
        def UpdateFilenameTaggingOptions( self, filename_tagging_options ):
            
            quick_namespaces = self._quick_namespaces_list.GetData()
            
            regexes = self._regexes.GetStrings()
            
            filename_tagging_options.AdvancedSetTuple( quick_namespaces, regexes )
            
        
    
    class _SimplePanel( wx.Panel ):
        
        def __init__( self, parent, service_key, refresh_callable, filename_tagging_options, present_for_accompanying_file_list ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._refresh_callable = refresh_callable
            self._present_for_accompanying_file_list = present_for_accompanying_file_list
            
            #
            
            self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
            
            self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._tags_panel, self._service_key, self.TagsRemoved )
            
            expand_parents = True
            
            self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tags_panel, self.EnterTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            
            self._tags_paste_button = ClientGUICommon.BetterButton( self._tags_panel, 'paste tags', self._PasteTags )
            
            #
            
            self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for selected files' )
            
            self._paths_to_single_tags = collections.defaultdict( set )
            
            self._single_tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._single_tags_panel, self._service_key, self.SingleTagsRemoved )
            
            self._single_tags_paste_button = ClientGUICommon.BetterButton( self._single_tags_panel, 'paste tags', self._PasteSingleTags )
            
            expand_parents = True
            
            self._single_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.EnterTagsSingle, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            
            self.SetSelectedPaths( [] )
            
            if not self._present_for_accompanying_file_list:
                
                self._single_tags_panel.Hide()
                
            
            #
            
            self._checkboxes_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._load_from_txt_files_checkbox = wx.CheckBox( self._checkboxes_panel, label = 'try to load tags from neighbouring .txt files' )
            
            txt_files_help_button = ClientGUICommon.BetterBitmapButton( self._checkboxes_panel, CC.GlobalBMPs.help, self._ShowTXTHelp )
            txt_files_help_button.SetToolTip( 'Show help regarding importing tags from .txt files.' )
            
            self._filename_namespace = wx.TextCtrl( self._checkboxes_panel )
            self._filename_namespace.SetMinSize( ( 100, -1 ) )
            
            self._filename_checkbox = wx.CheckBox( self._checkboxes_panel, label = 'add filename? [namespace]' )
            
            self._dir_namespace_1 = wx.TextCtrl( self._checkboxes_panel )
            self._dir_namespace_1.SetMinSize( ( 100, -1 ) )
            
            self._dir_checkbox_1 = wx.CheckBox( self._checkboxes_panel, label = 'add first directory? [namespace]' )
            
            self._dir_namespace_2 = wx.TextCtrl( self._checkboxes_panel )
            self._dir_namespace_2.SetMinSize( ( 100, -1 ) )
            
            self._dir_checkbox_2 = wx.CheckBox( self._checkboxes_panel, label = 'add second directory? [namespace]' )
            
            self._dir_namespace_3 = wx.TextCtrl( self._checkboxes_panel )
            self._dir_namespace_3.SetMinSize( ( 100, -1 ) )
            
            self._dir_checkbox_3 = wx.CheckBox( self._checkboxes_panel, label = 'add third directory? [namespace]' )
            
            #
            
            ( tags_for_all, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory ) = filename_tagging_options.SimpleToTuple()
            
            self._tags.AddTags( tags_for_all )
            self._load_from_txt_files_checkbox.SetValue( load_from_neighbouring_txt_files )
            
            ( add_filename_boolean, add_filename_namespace ) = add_filename
            
            self._filename_checkbox.SetValue( add_filename_boolean )
            self._filename_namespace.SetValue( add_filename_namespace )
            
            ( dir_1_boolean, dir_1_namespace ) = add_first_directory
            
            self._dir_checkbox_1.SetValue( dir_1_boolean )
            self._dir_namespace_1.SetValue( dir_1_namespace )
            
            ( dir_2_boolean, dir_2_namespace ) = add_second_directory
            
            self._dir_checkbox_2.SetValue( dir_2_boolean )
            self._dir_namespace_2.SetValue( dir_2_namespace )
            
            ( dir_3_boolean, dir_3_namespace ) = add_third_directory
            
            self._dir_checkbox_3.SetValue( dir_3_boolean )
            self._dir_namespace_3.SetValue( dir_3_namespace )
            
            #
            
            self._tags_panel.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._tags_panel.Add( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._tags_panel.Add( self._tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._single_tags_panel.Add( self._single_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._single_tags_panel.Add( self._single_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._single_tags_panel.Add( self._single_tags_paste_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            txt_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            txt_hbox.Add( self._load_from_txt_files_checkbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            txt_hbox.Add( txt_files_help_button, CC.FLAGS_VCENTER )
            
            filename_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            filename_hbox.Add( self._filename_checkbox, CC.FLAGS_VCENTER )
            filename_hbox.Add( self._filename_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dir_hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
            
            dir_hbox_1.Add( self._dir_checkbox_1, CC.FLAGS_VCENTER )
            dir_hbox_1.Add( self._dir_namespace_1, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dir_hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
            
            dir_hbox_2.Add( self._dir_checkbox_2, CC.FLAGS_VCENTER )
            dir_hbox_2.Add( self._dir_namespace_2, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            dir_hbox_3 = wx.BoxSizer( wx.HORIZONTAL )
            
            dir_hbox_3.Add( self._dir_checkbox_3, CC.FLAGS_VCENTER )
            dir_hbox_3.Add( self._dir_namespace_3, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._checkboxes_panel.Add( txt_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._checkboxes_panel.Add( filename_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._checkboxes_panel.Add( dir_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._checkboxes_panel.Add( dir_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._checkboxes_panel.Add( dir_hbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( self._single_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( self._checkboxes_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( hbox )
            
            #
            
            self._load_from_txt_files_checkbox.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
            self._filename_namespace.Bind( wx.EVT_TEXT, self.EventRefresh )
            self._filename_checkbox.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
            self._dir_namespace_1.Bind( wx.EVT_TEXT, self.EventRefresh )
            self._dir_checkbox_1.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
            self._dir_namespace_2.Bind( wx.EVT_TEXT, self.EventRefresh )
            self._dir_checkbox_2.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
            self._dir_namespace_3.Bind( wx.EVT_TEXT, self.EventRefresh )
            self._dir_checkbox_3.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
            
        
        def _GetTagsFromClipboard( self ):
            
            text = HG.client_controller.GetClipboardText()
            
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
                
                wx.MessageBox( HydrusData.ToUnicode( e ) )
                
                return
                
            
            self.EnterTags( tags )
            
        
        def _PasteSingleTags( self ):
            
            try:
                
                tags = self._GetTagsFromClipboard()
                
            except Exception as e:
                
                wx.MessageBox( HydrusData.ToUnicode( e ) )
                
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
            
            wx.MessageBox( message )
            
        
        def EnterTags( self, tags ):
            
            tag_parents_manager = HG.client_controller.GetManager( 'tag_parents' )
            
            parents = set()
            
            for tag in tags:
                
                some_parents = tag_parents_manager.GetParents( self._service_key, tag )
                
                parents.update( some_parents )
                
            
            if len( tags ) > 0:
                
                self._tags.AddTags( tags )
                self._tags.AddTags( parents )
                
                self._refresh_callable()
                
            
        
        def EnterTagsSingle( self, tags ):
            
            tag_parents_manager = HG.client_controller.GetManager( 'tag_parents' )
            
            parents = set()
            
            for tag in tags:
                
                some_parents = tag_parents_manager.GetParents( self._service_key, tag )
                
                parents.update( some_parents )
                
            
            if len( tags ) > 0:
                
                self._single_tags.AddTags( tags )
                self._single_tags.AddTags( parents )
                
                for path in self._selected_paths:
                    
                    current_tags = self._paths_to_single_tags[ path ]
                    
                    current_tags.update( tags )
                    current_tags.update( parents )
                    
                
                self._refresh_callable()
                
            
        
        def EventRefresh( self, event ):
            
            self._refresh_callable()
            
        
        def GetTags( self, index, path ):
            
            tags = set()
            
            if path in self._paths_to_single_tags:
                
                tags.update( self._paths_to_single_tags[ path ] )
                
            
            return tags
            
        
        def SingleTagsRemoved( self, tags ):
            
            for path in self._selected_paths:
                
                current_tags = self._paths_to_single_tags[ path ]
                
                current_tags.difference_update( tags )
                
            
            self._refresh_callable()
            
        
        def SetSelectedPaths( self, paths ):
            
            self._selected_paths = paths
            
            single_tags = set()
            
            if len( paths ) > 0:
                
                for path in self._selected_paths:
                    
                    if path in self._paths_to_single_tags:
                        
                        single_tags.update( self._paths_to_single_tags[ path ] )
                        
                    
                
                self._single_tag_box.Enable()
                self._single_tags_paste_button.Enable()
                
            else:
                
                self._single_tag_box.Disable()
                self._single_tags_paste_button.Disable()
                
            
            self._single_tags.SetTags( single_tags )
            
        
        def TagsRemoved( self, tag ):
            
            self._refresh_callable()
            
        
        def UpdateFilenameTaggingOptions( self, filename_tagging_options ):
            
            tags_for_all = self._tags.GetTags()
            load_from_neighbouring_txt_files = self._load_from_txt_files_checkbox.GetValue()
            
            add_filename_boolean = self._filename_checkbox.GetValue()
            add_filename_namespace = self._filename_namespace.GetValue()
            
            add_filename = ( add_filename_boolean, add_filename_namespace )
            
            dir_1_boolean = self._dir_checkbox_1.GetValue()
            dir_1_namespace = self._dir_namespace_1.GetValue()
            
            add_first_directory = ( dir_1_boolean, dir_1_namespace )
            
            dir_2_boolean = self._dir_checkbox_2.GetValue()
            dir_2_namespace = self._dir_namespace_2.GetValue()
            
            add_second_directory = ( dir_2_boolean, dir_2_namespace )
            
            dir_3_boolean = self._dir_checkbox_3.GetValue()
            dir_3_namespace = self._dir_namespace_3.GetValue()
            
            add_third_directory = ( dir_3_boolean, dir_3_namespace )
            
            filename_tagging_options.SimpleSetTuple( tags_for_all, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory )
            
        
    
class EditLocalImportFilenameTaggingPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, paths ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._paths = paths
        
        self._tag_repositories = ClientGUICommon.ListBook( self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        for service in services:
            
            if service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_CREATE ):
                
                service_key = service.GetServiceKey()
                
                name = service.GetName()
                
                self._tag_repositories.AddPageArgs( name, service_key, self._Panel, ( self._tag_repositories, service_key, paths ), {} )
                
            
        
        page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_KEY, paths )
        
        name = CC.LOCAL_TAG_SERVICE_KEY
        
        self._tag_repositories.AddPage( name, name, page )
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        self._tag_repositories.Select( default_tag_repository_key )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        paths_to_tags = collections.defaultdict( dict )
        
        for page in self._tag_repositories.GetActivePages():
            
            ( service_key, page_of_paths_to_tags ) = page.GetInfo()
            
            for ( path, tags ) in page_of_paths_to_tags.items(): paths_to_tags[ path ][ service_key ] = tags
            
        
        return paths_to_tags
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, paths ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._paths = paths
            
            self._paths_list = ClientGUIListCtrl.BetterListCtrl( self, 'paths_to_tags', 25, 40, [ ( '#', 4 ), ( 'path', 40 ), ( 'tags', -1 ) ], self._ConvertDataToListCtrlTuples )
            
            self._paths_list.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._paths_list.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            #
            
            self._filename_tagging_panel = FilenameTaggingOptionsPanel( self, self._service_key, self.RefreshFileList, present_for_accompanying_file_list = True )
            
            #
            
            # i.e. ( index, path )
            self._paths_list.AddDatas( list( enumerate( self._paths ) ) )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._filename_tagging_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def _ConvertDataToListCtrlTuples( self, data ):
            
            ( index, path ) = data
            
            tags = self._GetTags( index, path )
            
            pretty_index = HydrusData.ConvertIntToPrettyString( index + 1 )
            
            pretty_path = path
            pretty_tags = ', '.join( tags )
            
            display_tuple = ( pretty_index, pretty_path, pretty_tags )
            sort_tuple = ( index, path, tags )
            
            return ( display_tuple, sort_tuple )
            
        
        def _GetTags( self, index, path ):
            
            filename_tagging_options = self._filename_tagging_panel.GetFilenameTaggingOptions()
            
            tags = filename_tagging_options.GetTags( self._service_key, path )
            
            tags.update( self._filename_tagging_panel.GetTags( index, path ) )
            
            tags = list( tags )
            
            tags.sort()
            
            return tags
            
        
        def EventItemSelected( self, event ):
            
            paths = [ path for ( index, path ) in self._paths_list.GetData( only_selected = True ) ]
            
            self._filename_tagging_panel.SetSelectedPaths( paths )
            
            event.Skip()
            
        
        def GetInfo( self ):
            
            paths_to_tags = { path : self._GetTags( index, path ) for ( index, path ) in self._paths_list.GetData() }
            
            return ( self._service_key, paths_to_tags )
            
        
        def RefreshFileList( self ):
            
            self._paths_list.UpdateDatas()
            
        
class EditFilenameTaggingOptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_key, filename_tagging_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._service_key = service_key
        
        self._example_path_input = wx.TextCtrl( self )
        self._example_output = wx.TextCtrl( self )
        
        self._filename_tagging_options_panel = FilenameTaggingOptionsPanel( self, self._service_key, self.RefreshTags, filename_tagging_options = filename_tagging_options, present_for_accompanying_file_list = False )
        
        #
        
        self._example_path_input.SetValue( 'enter example path here' )
        self._example_output.Disable()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._example_path_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._example_output, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._filename_tagging_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        #
        
        self._example_path_input.Bind( wx.EVT_TEXT, self.EventText )
        
    
    def EventText( self, event ):
        
        self.RefreshTags()
        
    
    def GetValue( self ):
        
        return self._filename_tagging_options_panel.GetFilenameTaggingOptions()
        
    
    def RefreshTags( self ):
        
        example_path_input = self._example_path_input.GetValue()
        
        filename_tagging_options = self.GetValue()
        
        try:
            
            tags = filename_tagging_options.GetTags( self._service_key, example_path_input )
            
        except:
            
            tags = [ 'could not parse' ]
            
        
        self._example_output.SetValue( ', '.join( tags ) )
        
    
class TagImportOptionsButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, namespaces, tag_import_options, update_callable = None, show_url_options = True ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'tag import options', self._EditOptions )
        
        self._namespaces = namespaces
        self._tag_import_options = tag_import_options
        self._update_callable = update_callable
        self._show_url_options = show_url_options
        
        self._SetToolTip()
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag import options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditTagImportOptionsPanel( dlg, self._namespaces, self._tag_import_options, show_url_options = self._show_url_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                tag_import_options = panel.GetValue()
                
                self._SetValue( tag_import_options )
                
            
        
    
    def _SetToolTip( self ):
        
        self.SetToolTip( self._tag_import_options.GetSummary( self._show_url_options ) )
        
    
    def _SetValue( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options
        
        self._SetToolTip()
        
        if self._update_callable is not None:
            
            self._update_callable( self._tag_import_options )
            
        
    
    def GetValue( self ):
        
        return self._tag_import_options
        
    
    def SetNamespaces( self, namespaces ):
        
        self._namespaces = namespaces
        
    
    def SetValue( self, tag_import_options ):
        
        self._SetValue( tag_import_options )
        
    
