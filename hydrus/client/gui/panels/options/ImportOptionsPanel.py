from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

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
from hydrus.client.importing.options import ImportOptionsContainer

class ImportOptionsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options, import_options_manager: ImportOptionsContainer.ImportOptionsManager ):
        super().__init__( parent )
        
        self._new_options = new_options
        self._import_options_container_manager: ImportOptionsContainer.ImportOptionsManager = import_options_manager.Duplicate()
        
        menu_template_items = [ ]
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open help dialog', 'Open a dialog with more information about this panel.', self._ShowHelp ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._simple_mode = QW.QCheckBox( self )
        self._simple_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'The options system allows you to set any options type anywhere. You can make a particular URL Class "present" differently to other Post URLs or set up subscription-only note parsing if you really want, but by default, I hide options that are crazy and a waste of time. Uncheck this to see everything and implement your options mind palace.' ) )
        
        self._simple_mode.setChecked( self._new_options.GetBoolean( 'import_options_simple_mode' ) )
        
        simple_mode_hbox = ClientGUICommon.WrapInText( self._simple_mode, self, 'keep this panel simple to use' )
        
        #
        
        default_import_options_panel = ClientGUICommon.StaticBox( self, 'default import options' )
        
        default_import_options_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( default_import_options_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_DEFAULT_IMPORT_OPTIONS.ID, self._ConvertDefaultDataToDisplayTuple, self._ConvertDefaultDataToSortTuple )
        
        self._default_import_options_list = ClientGUIListCtrl.BetterListCtrlTreeView( default_import_options_list_panel, 7, model, activation_callback = self._EditDefault )
        
        default_import_options_list_panel.SetListCtrl( self._default_import_options_list )
        
        default_import_options_list_panel.AddButton( 'show stack', self._SeeDefaultStack, enabled_only_on_single_selection = True )
        default_import_options_list_panel.AddSeparator()
        default_import_options_list_panel.AddButton( 'copy', self._CopyDefault, enabled_only_on_single_selection = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'replace-paste: delete what is selected and paste', 'Replace what is selected with what you have in the clipboard.', self._PasteDefault ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'merge-paste: paste onto what is selected, overwriting on conflicts', 'Overwrite what is selected with what you have in the clipboard.', self._PasteDefaultMerge ) )
        
        default_import_options_list_panel.AddMenuButton( 'paste', menu_template_items, enabled_only_on_selection = True )
        default_import_options_list_panel.AddButton( 'edit', self._EditDefault, enabled_only_on_single_selection = True )
        default_import_options_list_panel.AddButton( 'clear', self._ClearDefault, enabled_only_on_selection = True )
        
        #
        
        url_class_import_options_panel = ClientGUICommon.StaticBox( self, 'url class import options' )
        
        url_class_import_options_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( url_class_import_options_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_URL_CLASS_IMPORT_OPTIONS.ID, self._ConvertURLClassDataToDisplayTuple, self._ConvertURLClassDataToSortTuple )
        
        self._url_class_import_options_list = ClientGUIListCtrl.BetterListCtrlTreeView( url_class_import_options_list_panel, 12, model, activation_callback = self._EditURLClass )
        
        url_class_import_options_list_panel.SetListCtrl( self._url_class_import_options_list )
        
        url_class_import_options_list_panel.AddButton( 'show stack', self._SeeURLClassStack, enabled_only_on_single_selection = True )
        url_class_import_options_list_panel.AddSeparator()
        url_class_import_options_list_panel.AddButton( 'copy', self._CopyURLClass, enabled_only_on_single_selection = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'replace-paste: delete what is selected and paste', 'Replace what is selected with what you have in the clipboard.', self._PasteURLClass ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'merge-paste: paste onto what is selected, overwriting on conflicts', 'Overwrite what is selected with what you have in the clipboard.', self._PasteURLClassMerge ) )
        
        url_class_import_options_list_panel.AddMenuButton( 'paste', menu_template_items, enabled_only_on_selection = True )
        url_class_import_options_list_panel.AddButton( 'edit', self._EditURLClass, enabled_only_on_single_selection = True )
        url_class_import_options_list_panel.AddButton( 'clear', self._ClearURLClass, enabled_only_on_selection = True )
        
        #
        
        self._default_import_options_list.AddDatas( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER )
        
        self._default_import_options_list.Sort()
        
        url_classes = CG.client_controller.network_engine.domain_manager.GetURLClasses()
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_GALLERY ) ]
        
        self._url_class_import_options_list.AddDatas( eligible_url_classes )
        
        self._url_class_import_options_list.Sort()
        
        #
        
        default_import_options_panel.Add( default_import_options_list_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        url_class_import_options_panel.Add( url_class_import_options_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, simple_mode_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, default_import_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, url_class_import_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ClearDefault( self ):
        
        selected = self._default_import_options_list.GetData( only_selected = True )
        
        if ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL in selected:
            
            selected.remove( ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL )
            
            if len( selected ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'You cannot clear the "global" set! It has to have an entry for everything, to be the fallback default.' )
                
                return
                
            
        
        summary = ', '.join( [ ImportOptionsContainer.import_options_caller_type_str_lookup[ import_options_caller_type ] for import_options_caller_type in selected ] )
        
        message = f'Clear all custom import options from {summary}?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        for import_options_caller_type in selected:
            
            self._import_options_container_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, ImportOptionsContainer.ImportOptionsContainer() )
            
        
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
            
            self._import_options_container_manager.SetDefaultImportOptionsContainerForURLClass( url_class.GetClassKey(), ImportOptionsContainer.ImportOptionsContainer() )
            
        
        self._default_import_options_list.UpdateDatas( selected )
        
    
    def _ConvertDefaultDataToDisplayTuple( self, import_options_caller_type: int ):
        
        pretty_name = ImportOptionsContainer.import_options_caller_type_str_lookup[ import_options_caller_type ]
        
        try:
            
            import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
            
            show_downloader_options = not import_options_caller_type in ImportOptionsContainer.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES
            
            pretty_defaults = import_options_container.GetSummary( show_downloader_options = show_downloader_options )
            
        except Exception as e:
            
            pretty_defaults = f'ERROR: {e}'
            
        
        display_tuple = ( pretty_name, pretty_defaults )
        
        return display_tuple
        
    
    def _ConvertDefaultDataToSortTuple( self, import_options_caller_type: int ):
        
        ( pretty_name, pretty_defaults ) = self._ConvertDefaultDataToDisplayTuple( import_options_caller_type )
        
        sort_name = - ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER.index( import_options_caller_type )
        
        sort_tuple = ( sort_name, pretty_defaults )
        
        return sort_tuple
        
    
    def _ConvertURLClassDataToDisplayTuple( self, url_class: ClientNetworkingURLClass.URLClass ):
        
        url_class_key = url_class.GetClassKey()
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            pretty_defaults_set = ''
            
        else:
            
            pretty_defaults_set = import_options_container.GetSummary( show_downloader_options = True )
            
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_defaults_set )
        
        return display_tuple
        
    
    _ConvertURLClassDataToSortTuple = _ConvertURLClassDataToDisplayTuple
    
    def _CopyDefault( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
        
        payload = import_options_container.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _CopyURLClass( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        url_class_key = selected.GetClassKey()
        
        import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'There are no import options set for this url class!' )
            
        else:
            
            payload = import_options_container.DumpToString()
            
            CG.client_controller.pub( 'clipboard', 'text', payload )
            
        
    
    def _EditDefault( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = ClientGUIImportOptionsContainer.EditImportOptionsContainerPanel( dlg, self._import_options_container_manager, import_options_container, import_options_caller_type, simple_mode = self._simple_mode.isChecked() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_options_container = panel.GetValue()
                
                self._import_options_container_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, edited_import_options_container )
                
                self._default_import_options_list.UpdateDatas( ( selected, ) )
                
            
        
    
    def _EditURLClass( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        url_class_key = selected.GetClassKey()
        
        import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
        
        if import_options_container is None:
            
            import_options_container = ImportOptionsContainer.ImportOptionsContainer()
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = ClientGUIImportOptionsContainer.EditImportOptionsContainerPanel( dlg, self._import_options_container_manager, import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS, url_class_key = url_class_key, simple_mode = self._simple_mode.isChecked() )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_options_container = panel.GetValue()
                
                self._import_options_container_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, edited_import_options_container )
                
                self._url_class_import_options_list.UpdateDatas( ( selected, ) )
                
            
        
    
    def _GetPasteObject( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            raise HydrusExceptions.CancelledException()
            
        
        try:
            
            pasted_import_options_container = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( pasted_import_options_container, ImportOptionsContainer.ImportOptionsContainer ):
                
                raise Exception( 'Not an Import options Container!' )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Import Options Container', e )
            
            raise HydrusExceptions.CancelledException()
            
        
        return pasted_import_options_container
        
    
    def _PasteDefault( self, do_merge = False ):
        
        try:
            
            pasted_import_options_container = self._GetPasteObject()
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        import_options_caller_types = self._default_import_options_list.GetData( only_selected = True )
        
        for import_options_caller_type in import_options_caller_types:
            
            if do_merge:
                
                existing_import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForCallerType( import_options_caller_type )
                
                edited_import_options_container = existing_import_options_container.Duplicate()
                
                edited_import_options_container.OverwriteWithThisSlice( pasted_import_options_container )
                
            else:
                
                if import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
                    
                    try:
                        
                        pasted_import_options_container.SetAndCheckFull()
                        
                    except:
                        
                        ClientGUIDialogsMessage.ShowInformation( self, 'Hey, you tried to paste a non-full import options container into the "global" entry. Did you mean to do a merge-paste instead?' )
                        
                        continue
                        
                    
                
                edited_import_options_container = pasted_import_options_container.Duplicate()
                
            
            self._import_options_container_manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, edited_import_options_container )
            
        
        self._default_import_options_list.UpdateDatas( import_options_caller_types )
        
    
    def _PasteDefaultMerge( self ):
        
        self._PasteDefault( do_merge = True )
        
    
    def _PasteURLClass( self, do_merge = False ):
        
        try:
            
            pasted_import_options_container = self._GetPasteObject()
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        url_classes = self._url_class_import_options_list.GetData( only_selected = True )
        
        for url_class in url_classes:
            
            url_class_key = url_class.GetClassKey()
            
            if do_merge:
                
                existing_import_options_container = self._import_options_container_manager.GetDefaultImportOptionsContainerForURLClass( url_class_key )
                
                if existing_import_options_container is None:
                    
                    edited_import_options_container = pasted_import_options_container.Duplicate()
                    
                else:
                    
                    edited_import_options_container = existing_import_options_container.Duplicate()
                    
                    edited_import_options_container.OverwriteWithThisSlice( pasted_import_options_container )
                    
                
            else:
                
                edited_import_options_container = pasted_import_options_container.Duplicate()
                
            
            self._import_options_container_manager.SetDefaultImportOptionsContainerForURLClass( url_class_key, edited_import_options_container )
            
        
        self._url_class_import_options_list.UpdateDatas( url_classes )
        
    
    def _PasteURLClassMerge( self ):
        
        self._PasteURLClass( do_merge = True )
        
    
    def _SeeDefaultStack( self ):
        
        selected = self._default_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = selected
        
        if import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            message = 'The "global" set is the fallback default that all the other options will eventually use as the options-of-last-resort. No importer uses "global" as its primary import context.'
            
        else:
            
            preference_stack_description = ImportOptionsContainer.GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type )
            
            message = f'The stack for {ImportOptionsContainer.import_options_caller_type_str_lookup[ import_options_caller_type ]}, from first- to last-checked, is:'
            message += '\n\n'
            message += preference_stack_description
            
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _SeeURLClassStack( self ):
        
        selected = self._url_class_import_options_list.GetTopSelectedData()
        
        if selected is None:
            
            return
            
        
        import_options_caller_type = ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS
        url_class = selected
        
        preference_stack_description = ImportOptionsContainer.GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type, url_class_key = url_class.GetClassKey() )
        
        message = f'The stack for when this url class is encountered, from first- to last-checked, is:'
        message += '\n\n'
        message += preference_stack_description
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _ShowHelp( self ):
        message = '''tl;dr: Go into "global" and set every panel how you want. Never touch this again, and rarely set a "specific" import options override on a specific downloader.

Hydrus can import files in different ways. Sometimes it is something you are watching and interacting with, sometimes it happens in the background, without any UI at all. You can customise the various "import options" extensively.

There are options governing how files pre-screened, where they are imported to, and what metadata is added with them. Each of these is separated to let you mix and match.

There is a "global" options structure that represents a basic default for all imports. If nothing else has anything set, your imports will use whatever is in the global set.

Atop the global set sits a stack of increasingly specific contexts, for instance, for a local hard drive import, you would have:

- the specific page's import options, which you set with a button in the UI
- the general "local hard drive import" import options
- the global import options

When the import engine needs to check the "file filtering" options, it checks the top-most layer to see if it has anything set. If that layer has those options, that is what is used. If the layer is set to "use the default", the import engine goes down a layer and checks again. This is how the specific import options you might set on a particular page will override anything else while global will act as the final backstop.

Most of the time, just set what sounds correct. If you want subscriptions to only publish "new inbox files" to their buttons/pages, then set up "presentation" options for your subs, easy as that. Every edit panel has a short description of the context being edited and which options are appropriate to edit for it. The one wrinkle to watch out for is the "url class" settings, which generally override the other layers, which allows you to set a specific tag blacklist for a particular domain. Click "show stack" to see exactly how a particular import context stacks up.

Keep things simple and deliberate!'''
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def UpdateOptions( self ):
        # set our updated manager to be the main manager of the controller
        # don't do it yet though obviously, only once we actually have one
        
        self._new_options.SetBoolean( 'import_options_simple_mode', self._simple_mode.isChecked() )
        
        pass
        
    
