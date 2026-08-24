from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImportOptionsContainer
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing.options import ImportOptionsConstants as IOC
from hydrus.client.importing.options import ImportOptionsContainer
from hydrus.client.importing.options import ImportOptionsManager

class ImportOptionsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options, import_options_manager: ImportOptionsManager.ImportOptionsManager ):
        super().__init__( parent )
        
        self._new_options = new_options
        self._import_options_manager: ImportOptionsManager.ImportOptionsManager = import_options_manager.Duplicate()
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open tl;dr', 'Open a dialog with brief information about this panel.', self._ShowTLDR ) )
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_IMPORT_OPTIONS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the import options help', 'Open the HTML help that talks about this whole system.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._simple_mode = QW.QCheckBox( self )
        self._simple_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'The options system allows you to set any options type anywhere. You can make a particular URL Class "present" differently to other Post URLs or set up subscription-only note parsing if you really want, but by default, I hide options that are crazy and generally a waste of time. Uncheck this to see everything and implement your options mind palace.' ) )
        
        self._simple_mode.setChecked( self._new_options.GetBoolean( 'import_options_simple_mode' ) )
        
        simple_mode_hbox = ClientGUICommon.WrapInText( self._simple_mode, self, 'keep this panel simple :^)' )
        
        #
        
        default_import_options_panel = ClientGUICommon.StaticBox( self, 'default import options' )
        
        default_import_options_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( default_import_options_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DEFAULT_IMPORT_OPTIONS.ID, self._ConvertDefaultDataToDisplayTuple, self._ConvertDefaultDataToSortTuple )
        
        self._default_import_options_list = ClientGUIListCtrl.BetterListCtrlTreeView( default_import_options_list_panel, 7, model, activation_callback = self._EditDefault )
        
        default_import_options_list_panel.SetListCtrl( self._default_import_options_list )
        
        default_import_options_list_panel.AddButton( 'show stack', self._SeeDefaultStack, enabled_only_on_single_selection = True )
        default_import_options_list_panel.AddSeparator()
        self._copy_default_button = default_import_options_list_panel.AddIconButton( CC.global_icons().copy, self._CopyDefault, enabled_only_on_single_selection = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'custom paste: choose what you want', 'Open a dialog with the current options and what is in your clipboard and choose what to keep and overwrite.', self._PasteDefaultCustom ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'merge-paste', 'Replace what is selected with what you have in the clipboard that is non-default.', self._PasteDefault ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'fill-in-gaps-paste', 'Fill in what is currently default in the selected with what you have in the clipboard that is non-default.', self._PasteDefaultMerge ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'replace-paste', 'Replace what is selected with what you have in the clipboard.', self._PasteDefaultFillIn ) )
        
        self._paste_default_button = default_import_options_list_panel.AddMenuIconButton( CC.global_icons().paste, 'paste a new set of options from the clipboard', menu_template_items, enabled_only_on_selection = True )
        
        self._default_favourites_button = ClientGUIImportOptionsContainer.ImportOptionsContainerFavouritesButton( self, self._import_options_manager, edit_allowed = True )
        default_import_options_list_panel.AddWindow( self._default_favourites_button )
        
        default_import_options_list_panel.AddButton( 'edit', self._EditDefault, enabled_only_on_single_selection = True )
        default_import_options_list_panel.AddButton( 'clear', self._ClearDefault, enabled_only_on_selection = True )
        default_import_options_list_panel.AddSeparator()
        default_import_options_list_panel.AddButton( 'reset to defaults', self._ResetDefaultToDefault )
        
        #
        
        url_class_import_options_panel = ClientGUICommon.StaticBox( self, 'url class import options' )
        
        url_class_import_options_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( url_class_import_options_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_IMPORT_OPTIONS.ID, self._ConvertURLClassDataToDisplayTuple, self._ConvertURLClassDataToSortTuple )
        
        self._url_class_import_options_list = ClientGUIListCtrl.BetterListCtrlTreeView( url_class_import_options_list_panel, 12, model, activation_callback = self._EditURLClass )
        
        url_class_import_options_list_panel.SetListCtrl( self._url_class_import_options_list )
        
        url_class_import_options_list_panel.AddButton( 'show stack', self._SeeURLClassStack, enabled_only_on_single_selection = True )
        url_class_import_options_list_panel.AddSeparator()
        self._copy_url_class_button = url_class_import_options_list_panel.AddIconButton( CC.global_icons().copy, self._CopyURLClass, enabled_only_on_single_selection = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'custom paste: choose what you want', 'Open a dialog with the current options and what is in your clipboard and choose what to keep and overwrite.', self._PasteURLClassCustom ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'merge-paste', 'Replace what is selected with what you have in the clipboard that is non-default.', self._PasteURLClass ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'fill-in-gaps-paste', 'Fill in what is currently default in the selected with what you have in the clipboard that is non-default.', self._PasteURLClassMerge ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'replace-paste', 'Replace what is selected with what you have in the clipboard.', self._PasteURLClassFillIn ) )
        
        self._paste_url_class_button = url_class_import_options_list_panel.AddMenuIconButton( CC.global_icons().paste, 'paste a new set of options from the clipboard', menu_template_items, enabled_only_on_selection = True )
        
        self._url_class_favourites_button = ClientGUIImportOptionsContainer.ImportOptionsContainerFavouritesButton( self, self._import_options_manager, edit_allowed = True )
        url_class_import_options_list_panel.AddWindow( self._url_class_favourites_button )
        
        url_class_import_options_list_panel.AddButton( 'edit', self._EditURLClass, enabled_only_on_single_selection = True )
        url_class_import_options_list_panel.AddButton( 'clear', self._ClearURLClass, enabled_only_on_selection = True )
        
        #
        
        self._default_import_options_list.AddDatas( IOC.IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER )
        
        self._default_import_options_list.Sort()
        
        url_classes = CG.client_controller.network_engine.domain_manager.GetURLClasses()
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_GALLERY ) ]
        
        self._url_class_import_options_list.AddDatas( eligible_url_classes )
        
        self._url_class_import_options_list.Sort()
        
        #
        
        default_import_options_panel.Add( default_import_options_list_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        url_class_import_options_panel.Add( url_class_import_options_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        label = 'This is a new system that has migrated the three old file/tag/note import options into seven sub-types and allowing more sophisticated mix-and-match defaults and favourites/templating. I would like feedback on what is good/bad/confusing, thank you!'
        
        test_st = ClientGUICommon.BetterStaticText( self, label = label )
        test_st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        test_st.setObjectName( 'HydrusWarning' )
        test_st.setWordWrap( True )
        
        QP.AddToLayout( vbox, test_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, simple_mode_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, default_import_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, url_class_import_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._default_favourites_button.loadFavourite.connect( self._LoadFavouriteDefault )
        self._default_favourites_button.loadFavouriteCustom.connect( self._LoadFavouriteDefaultCustom )
        self._url_class_favourites_button.loadFavourite.connect( self._LoadFavouriteURLClass )
        self._url_class_favourites_button.loadFavouriteCustom.connect( self._LoadFavouriteURLClassCustom )
        
    
    def _ClearDefault( self ):
        
        selected = self._default_import_options_list.GetData( only_selected = True )
        
        if IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL in selected:
            
            selected.remove( IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL )
            
            if len( selected ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'You cannot clear the "global" set! It has to have an entry for everything, to be the fallback default.' )
                
                return
                
            
        
        summary = ', '.join( [ IOC.import_options_caller_type_str_lookup[ import_options_caller_type ] for import_options_caller_type in selected ] )
        
        message = f'Clear all custom import options from {summary}?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        for import_options_caller_type in selected:
            
            self._import_options_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, ImportOptionsContainer.ImportOptionsContainer() )
            
        
        self._default_import_options_list.UpdateDatas( selected )
        
    
    def _ClearURLClass( self ):
        
        selected = self._url_class_import_options_list.GetData( only_selected = True )
        
        if len( selected ) > 1:
            
            message = f'Clear all custom import options for {HydrusNumbers.ToHumanInt( len( selected ) )} url class entries?'
            
        else:
            
            message = f'Clear all custom import options for this entry?'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        for url_class in selected:
            
            self._import_options_manager.SetDefaultImportOptionsContainerForURLClass( url_class.GetClassKey(), ImportOptionsContainer.ImportOptionsContainer() )
            
        
        self._url_class_import_options_list.UpdateDatas( selected )
        
    
    def _ConvertDefaultDataToDisplayTuple( self, import_options_caller_type: int ):
        
        pretty_name = IOC.import_options_caller_type_str_lookup[ import_options_caller_type ]
        
        try:
            
            import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
            
            pretty_defaults = import_options_container.GetSummary( import_options_caller_type )
            
        except Exception as e:
            
            pretty_defaults = f'ERROR: {e}'
            
        
        display_tuple = ( pretty_name, pretty_defaults )
        
        return display_tuple
        
    
    def _ConvertDefaultDataToSortTuple( self, import_options_caller_type: int ):
        
        ( pretty_name, pretty_defaults ) = self._ConvertDefaultDataToDisplayTuple( import_options_caller_type )
        
        sort_name = - IOC.IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER.index( import_options_caller_type )
        
        sort_tuple = ( sort_name, pretty_defaults )
        
        return sort_tuple
        
    
    def _ConvertURLClassDataToDisplayTuple( self, url_class: ClientNetworkingURLClass.URLClass ):
        
        url_class_key = url_class.GetClassKey()
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            pretty_defaults_set = ''
            
        else:
            
            pretty_defaults_set = import_options_container.GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_defaults_set )
        
        return display_tuple
        
    
    _ConvertURLClassDataToSortTuple = _ConvertURLClassDataToDisplayTuple
    
    def _CopyDefault( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
        
        payload = import_options_container.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', payload )
        
        self._copy_default_button.ShowMicroNotification( f'Copied!' )
        
    
    def _CopyURLClass( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        url_class_key = selected.GetClassKey()
        
        import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'There are no import options set for this url class!' )
            
        else:
            
            payload = import_options_container.DumpToString()
            
            CG.client_controller.pub( 'clipboard', 'text', payload )
            
            self._copy_url_class_button.ShowMicroNotification( f'Copied!' )
            
        
    
    def _EditDefault( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
        
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = ClientGUIImportOptionsContainer.EditImportOptionsContainerPanel(
                dlg,
                self._import_options_manager,
                import_options_caller_type,
                import_options_container,
                simple_mode = self._simple_mode.isChecked()
            )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_options_container = panel.GetValue()
                
                self._import_options_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, edited_import_options_container )
                
                self._default_import_options_list.UpdateDatas( ( selected, ) )
                
            
        
    
    def _EditURLClass( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        url_class = selected
        
        url_class_key = url_class.GetClassKey()
        
        import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            import_options_container = ImportOptionsContainer.ImportOptionsContainer()
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = ClientGUIImportOptionsContainer.EditImportOptionsContainerPanel(
                dlg,
                self._import_options_manager,
                IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS,
                import_options_container,
                url_class_keys = [ url_class_key ],
                simple_mode = self._simple_mode.isChecked()
            )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_options_container = panel.GetValue()
                
                self._import_options_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, edited_import_options_container )
                
                self._url_class_import_options_list.UpdateDatas( ( url_class, ) )
                
            
        
    
    def _LoadFavouriteDefault( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._LoadFavouriteDefaultDoIt( incoming_import_options_container, False )
        
    
    def _LoadFavouriteDefaultCustom( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._LoadFavouriteDefaultDoIt( incoming_import_options_container, True )
        
    
    def _LoadFavouriteDefaultDoIt( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer, do_custom_merge: bool ):
        
        selected_import_options_caller_types = self._default_import_options_list.GetData( only_selected = True )
        
        if len( selected_import_options_caller_types ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Hey, nothing is selected in the default list--select something and try loading again.' )
            
            return
            
        
        if do_custom_merge:
            
            if not self._default_import_options_list.HasOneSelected():
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Hey, multiple items in the default list are selected. I am only going to do this on the topmost selected.' )
                
            
            import_options_caller_type = self._default_import_options_list.GetTopSelectedData()
            
            current_import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
            
            try:
                
                final_import_options_container = ClientGUIImportOptionsContainer.DoCustomOverwrite(
                    self,
                    self._simple_mode.isChecked(),
                    import_options_caller_type,
                    current_import_options_container,
                    incoming_import_options_container
                )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            final_import_options_container = incoming_import_options_container
            
        
        if IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL in selected_import_options_caller_types and not final_import_options_container.IsFull():
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Hey, the import options that was entered was not full, but the Global entry has to have something for everything. Please try again!' )
            
            return
            
        
        for import_options_caller_type in selected_import_options_caller_types:
            
            self._import_options_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, final_import_options_container )
            
        
        self._default_import_options_list.UpdateDatas( selected_import_options_caller_types )
        
    
    def _LoadFavouriteURLClass( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._LoadFavouriteURLClassDoIt( incoming_import_options_container, False )
        
    
    def _LoadFavouriteURLClassCustom( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._LoadFavouriteURLClassDoIt( incoming_import_options_container, True )
        
    
    def _LoadFavouriteURLClassDoIt( self, incoming_import_options_container: ImportOptionsContainer.ImportOptionsContainer, do_custom_merge: bool ):
        
        selected_url_classes = self._url_class_import_options_list.GetData( only_selected = True )
        
        if len( selected_url_classes ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Hey, nothing is selected in the URL Class list--select something and try loading again.' )
            
            return
            
        
        if do_custom_merge:
            
            if not self._url_class_import_options_list.HasOneSelected():
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Hey, multiple items in the URL Class list are selected. I am only going to do this on the topmost selected. If you need to do this to multiple entries, set up one exactly how you want and then copy/replace-paste to the rest.' )
                
            
            url_class = self._url_class_import_options_list.GetTopSelectedData()
            
            url_class_key = url_class.GetClassKey()
            
            current_import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
            
            if current_import_options_container is None:
                
                current_import_options_container = ImportOptionsContainer.ImportOptionsContainer()
                
            
            import_options_caller_type = IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS
            
            try:
                
                final_import_options_container = ClientGUIImportOptionsContainer.DoCustomOverwrite(
                    self,
                    self._simple_mode.isChecked(),
                    import_options_caller_type,
                    current_import_options_container,
                    incoming_import_options_container
                )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            final_import_options_container = incoming_import_options_container
            
        
        for url_class in selected_url_classes:
            
            url_class_key = url_class.GetClassKey()
            
            self._import_options_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, final_import_options_container )
            
        
        self._url_class_import_options_list.UpdateDatas( selected_url_classes )
        
    
    def _PasteDefault( self, paste_type = ClientGUIImportOptionsContainer.PASTE_REPLACE ):
        
        try:
            
            pasted_import_options_container = ClientGUIImportOptionsContainer.GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        import_options_caller_types = self._default_import_options_list.GetData( only_selected = True )
        
        for import_options_caller_type in import_options_caller_types:
            
            if paste_type in ( ClientGUIImportOptionsContainer.PASTE_MERGE, ClientGUIImportOptionsContainer.PASTE_FILL_IN ):
                
                existing_import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
                
                edited_import_options_container = existing_import_options_container.Duplicate()
                
                if paste_type == ClientGUIImportOptionsContainer.PASTE_MERGE:
                    
                    edited_import_options_container.OverwriteWithThisSlice( pasted_import_options_container )
                    
                else:
                    
                    edited_import_options_container.FillInWithThisSlice( pasted_import_options_container )
                    
                
            else:
                
                if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
                    
                    if not pasted_import_options_container.IsFull():
                        
                        ClientGUIDialogsMessage.ShowInformation( self, 'Hey, you tried to paste a non-full import options container into the "global" entry. Did you mean to do a merge-paste instead?' )
                        
                    
                
                edited_import_options_container = pasted_import_options_container.Duplicate()
                
            
            self._import_options_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, edited_import_options_container )
            
        
        self._default_import_options_list.UpdateDatas( import_options_caller_types )
        
        self._paste_default_button.ShowMicroNotification( f'Pasted!' )
        
    
    def _PasteDefaultCustom( self ):
        
        try:
            
            pasted_import_options_container = ClientGUIImportOptionsContainer.GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._LoadFavouriteDefault( pasted_import_options_container )
        
        self._paste_default_button.ShowMicroNotification( f'Pasted!' )
        
    
    def _PasteDefaultFillIn( self ):
        
        self._PasteDefault( paste_type = ClientGUIImportOptionsContainer.PASTE_FILL_IN )
        
    
    def _PasteDefaultMerge( self ):
        
        self._PasteDefault( paste_type = ClientGUIImportOptionsContainer.PASTE_MERGE )
        
    
    def _PasteURLClass( self, paste_type = ClientGUIImportOptionsContainer.PASTE_REPLACE ):
        
        try:
            
            pasted_import_options_container = ClientGUIImportOptionsContainer.GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        url_classes = self._url_class_import_options_list.GetData( only_selected = True )
        
        for url_class in url_classes:
            
            url_class_key = url_class.GetClassKey()
            
            if paste_type in ( ClientGUIImportOptionsContainer.PASTE_MERGE, ClientGUIImportOptionsContainer.PASTE_FILL_IN ):
                
                existing_import_options_container = self._import_options_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
                
                if existing_import_options_container is None:
                    
                    edited_import_options_container = pasted_import_options_container.Duplicate()
                    
                else:
                    
                    edited_import_options_container = existing_import_options_container.Duplicate()
                    
                    if paste_type == ClientGUIImportOptionsContainer.PASTE_MERGE:
                        
                        edited_import_options_container.OverwriteWithThisSlice( pasted_import_options_container )
                        
                    else:
                        
                        edited_import_options_container.FillInWithThisSlice( pasted_import_options_container )
                        
                    
                
            else:
                
                edited_import_options_container = pasted_import_options_container.Duplicate()
                
            
            self._import_options_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, edited_import_options_container )
            
        
        self._url_class_import_options_list.UpdateDatas( url_classes )
        
        self._paste_url_class_button.ShowMicroNotification( f'Pasted!' )
        
    
    def _PasteURLClassCustom( self ):
        
        try:
            
            pasted_import_options_container = ClientGUIImportOptionsContainer.GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._LoadFavouriteURLClass( pasted_import_options_container )
        
        self._paste_url_class_button.ShowMicroNotification( f'Pasted!' )
        
    
    def _PasteURLClassFillIn( self ):
        
        self._PasteURLClass( paste_type = ClientGUIImportOptionsContainer.PASTE_FILL_IN )
        
    
    def _PasteURLClassMerge( self ):
        
        self._PasteURLClass( paste_type = ClientGUIImportOptionsContainer.PASTE_MERGE )
        
    
    def _ResetDefaultToDefault( self ):
        
        choice_tuples = [
            ( 'reset top defaults', 'defaults', 'Clear the default import options list and set everything back to how a new client database has it.' ),
            ( 'reset url classes', 'url_classes', 'Clear all the default URL Class entries.' ),
            ( 'reset favourites/templates', 'favourites', 'Clear the favourites/templates under the star icon button.' )
        ]
        
        try:
            
            default_reset_result = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Reset things?', choice_tuples )
            
        except HydrusExceptions.CancelledException as e:
            
            return
            
        
        message = f'Hey, you selected to reset "{default_reset_result}". I am going to clear everything and reset to defaults, ok? If it does not go how you want, cancel out of the options dialog.'
        
        yn_result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'let\'s do it', no_label = 'no, hold off' )
        
        if yn_result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        if default_reset_result == 'defaults':
            
            ImportOptionsManager.ImportOptionsManager.STATICPopulateManagerWithDefaultDefaults( self._import_options_manager )
            
            self._default_import_options_list.UpdateDatas()
            
        elif default_reset_result == 'url_classes':
            
            url_class_keys = list( self._import_options_manager.GetURLClassKeysToDefaultImportOptionsContainers().keys() )
            
            for url_class_key in url_class_keys:
                
                self._import_options_manager.DeleteDefaultImportOptionsContainerForURLClass( url_class_key )
                
            
            ImportOptionsManager.ImportOptionsManager.STATICPopulateManagerWithDefaultURLClassDefaults( self._import_options_manager )
            
            self._url_class_import_options_list.UpdateDatas()
            
        elif default_reset_result == 'favourites':
            
            self._import_options_manager.SetFavouriteImportOptionContainers( {} )
            
            ImportOptionsManager.ImportOptionsManager.STATICPopulateManagerWithDefaultFavourites( self._import_options_manager )
            
        
    
    def _SeeDefaultStack( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        if import_options_caller_type == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            message = 'The "global" set is the fallback default that all the other options will eventually use as the options-of-last-resort. No importer uses "global" as its primary import context.'
            
        else:
            
            preference_stack_description = ImportOptionsManager.GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type )
            
            message = f'The stack for {IOC.import_options_caller_type_str_lookup[ import_options_caller_type ]}, from first- to last-checked, is:'
            message += '\n\n'
            message += preference_stack_description
            
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _SeeURLClassStack( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = IOC.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS
        url_class = selected
        
        preference_stack_description = ImportOptionsManager.GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type, url_class_key = url_class.GetClassKey() )
        
        message = f'The stack for when this url class is encountered, from first- to last-checked, is:'
        message += '\n\n'
        message += preference_stack_description
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _ShowTLDR( self ):
        
        message = '''tl;dr: Go into "gallery/post urls" and make sure tags are going where you want. Never touch this again, and, on occasion, set a "custom" import options override on a specific downloader.'''
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def UpdateOptions( self ):
        
        CG.client_controller.import_options_manager = self._import_options_manager
        
        self._new_options.SetBoolean( 'import_options_simple_mode', self._simple_mode.isChecked() )
        
    
