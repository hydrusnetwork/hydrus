import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImportOptionsPanels
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing.options import ImportOptionsContainer

def GetPasteObject( win: QW.QWidget ) -> ImportOptionsContainer.ImportOptionsContainer:
    
    try:
        
        raw_text = CG.client_controller.GetClipboardText()
        
    except HydrusExceptions.DataMissing as e:
        
        HydrusData.PrintException( e )
        
        ClientGUIDialogsMessage.ShowCritical( win, 'Problem pasting!', str(e) )
        
        raise HydrusExceptions.CancelledException()
        
    
    try:
        
        pasted_import_options_container = HydrusSerialisable.CreateFromString( raw_text )
        
        if not isinstance( pasted_import_options_container, ImportOptionsContainer.ImportOptionsContainer ):
            
            raise Exception( 'Not an Import options Container!' )
            
        
    except Exception as e:
        
        ClientGUIDialogsQuick.PresentClipboardParseError( win, raw_text, 'JSON-serialised Import Options Container', e )
        
        raise HydrusExceptions.CancelledException()
        
    
    return pasted_import_options_container
    

PASTE_REPLACE = 0
PASTE_MERGE = 1
PASTE_FILL_IN = 2

class EditImportOptionsContainerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, import_options_container_manager: ImportOptionsContainer.ImportOptionsManager, import_options_container: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, url_class_key: bytes | None = None, simple_mode: bool = True, favourites_name: str | None = None ):
        
        super().__init__( parent )
        
        self._import_options_container_manager = import_options_container_manager
        self._import_options_caller_type = import_options_caller_type
        self._url_class_key = url_class_key
        self._simple_mode = simple_mode
        
        if import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS and url_class_key is not None:
            
            try:
                
                name = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key ).GetName()
                
            except Exception as e:
                
                name = 'Unknown URL Class'
                
            
            label = f'You are editing URL Class "{name}".'
            
        else:
            
            label = f'You are editing "{ImportOptionsContainer.import_options_caller_type_str_lookup[ import_options_caller_type ]}".'
            
        
        label += '\n\n'
        label += ImportOptionsContainer.import_options_caller_type_desc_lookup[ import_options_caller_type ]
        
        self._description_label = ClientGUICommon.BetterStaticText( self, label = label )
        self._description_label.setWordWrap( True )
        self._description_label.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._name_edit_panel = QW.QWidget( self )
        
        self._name_edit = QW.QLineEdit( self._name_edit_panel )
        
        if favourites_name is not None:
            
            self._name_edit.setText( favourites_name )
            
        
        self._copy_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self._Copy )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'replace-paste: reset this to default and paste', 'Replace what is selected with what you have in the clipboard.', self._Paste ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'merge-paste: paste, overwriting on conflicts', 'Overwrite what is selected with what you have in the clipboard.', self._PasteMerge ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'fill-in-gaps-paste: paste, but set only where currently default', 'Fill in what is selected with what you have in the clipboard.', self._PasteFillIn ) )
        
        self._paste_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().paste, menu_template_items )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste an entire set of import options.' ) )
        
        self._favourites_button = ImportOptionsContainerFavouritesButton( self, self._import_options_container_manager, edit_allowed = self._import_options_caller_type != ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES )
        
        if simple_mode:
            
            import_options_types_to_list_here = ImportOptionsContainer.IMPORT_OPTIONS_TYPES_SIMPLE_MODE_LOOKUP[ import_options_caller_type ]
            
            for import_options_type in ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER:
                
                if import_options_type not in import_options_types_to_list_here and import_options_container.HasImportOptions( import_options_type ):
                    
                    import_options_types_to_list_here.append( import_options_type )
                    
                
            
        else:
            
            import_options_types_to_list_here = ImportOptionsContainer.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER
            
        
        if import_options_caller_type in ImportOptionsContainer.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES:
            
            import_options_types_to_list_here = [ iot for iot in import_options_types_to_list_here if iot not in ImportOptionsContainer.IMPORT_OPTIONS_TYPES_DOWNLOADER_ONLY ]
            
        
        self._listbook = ClientGUIListBook.ListBook( self, list_chars_height = len( import_options_types_to_list_here ), orientation = QC.Qt.Orientation.Vertical, no_vertical_scrollbar = True )
        
        #
        
        if self._import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            default_import_options_container = ImportOptionsContainer.ImportOptionsContainer()
            
        else:
            
            # let's make a full container for the parent, as if this guy was empty
            # we can query that guy to get nice default labels 'uses subscription' and so on
            
            preference_stack = ImportOptionsContainer.GetImportOptionsCallerTypesPreferenceOrderFull( self._import_options_caller_type, url_class_key = self._url_class_key )
            
            caller_type_for_default = ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL
            
            try:
                
                index = preference_stack.index( self._import_options_caller_type )
                
                caller_type_for_default = preference_stack[ index + 1 ]
                
            except Exception as e:
                
                pass
                
            
            default_import_options_container = import_options_container_manager.GenerateFullImportOptionsContainer( ImportOptionsContainer.ImportOptionsContainer(), caller_type_for_default )
            
        
        selectee_type = CG.client_controller.new_options.GetInteger( 'last_selected_import_options_container_panel_options_type' )
        selectee_page = None
        
        for import_options_type in import_options_types_to_list_here:
            
            panel = DefaultableImportOptionsPanel(
                self._listbook,
                self._import_options_container_manager,
                import_options_type,
                import_options_container,
                default_import_options_container,
                self._import_options_caller_type,
                url_class_key = self._url_class_key
            )
            
            if import_options_type == selectee_type:
                
                selectee_page = panel
                
            
            panel.valueChanged.connect( self._UpdateLabels )
            
            self._listbook.addTab( panel, ImportOptionsContainer.import_options_type_str_lookup[ import_options_type ] )
            
        
        if selectee_page is not None:
            
            self._listbook.SelectPage( selectee_page )
            
        
        self._UpdateLabels()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name_edit ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._name_edit_panel, rows )
        
        self._name_edit_panel.setLayout( gridbox )
        
        self._name_edit_panel.setVisible( self._import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( button_hbox, self._favourites_button, CC.FLAGS_ON_RIGHT )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._description_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._name_edit_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._listbook.currentChanged.connect( self._UpdatePageChanged )
        
    
    def _Copy( self ):
        
        import_options_container = self.GetValue()
        
        payload = import_options_container.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _Paste( self, paste_type = PASTE_REPLACE ):
        
        try:
            
            pasted_import_options_container = GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if paste_type == PASTE_REPLACE:
            
            final_import_options_container = pasted_import_options_container
            
            if self._import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
                
                try:
                    
                    final_import_options_container.SetAndCheckFull()
                    
                except:
                    
                    ClientGUIDialogsMessage.ShowInformation( self, 'Hey, you tried to paste a non-full import options container into the "global" entry. Did you mean to do a merge-paste instead?' )
                    
                    return
                    
                
            
        else:
            
            final_import_options_container = self.GetValue().Duplicate()
            
            if paste_type == PASTE_MERGE:
                
                final_import_options_container.OverwriteWithThisSlice( pasted_import_options_container )
                
            else:
                
                final_import_options_container.FillInWithThisSlice( pasted_import_options_container )
                
            
        
        self.SetValue( final_import_options_container )
        
    
    def SetValue( self, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        for page in self._listbook.GetPages():
            
            page = typing.cast( DefaultableImportOptionsPanel, page )
            
            import_options_type = page.GetImportOptionsType()
            
            import_options = import_options_container.GetImportOptions( import_options_type )
            
            if import_options is None:
                
                page.SetDefault( True )
                
            else:
                
                page.SetValue( import_options )
                page.SetDefault( False )
                
            
        
        self._UpdateLabels()
        
    
    def _PasteFillIn( self ):
        
        self._Paste( paste_type = PASTE_FILL_IN )
        
    
    def _PasteMerge( self ):
        
        self._Paste( paste_type = PASTE_MERGE )
        
    
    def _UpdatePageChanged( self ):
        
        panel: DefaultableImportOptionsPanel | None = self._listbook.currentWidget()
        
        if panel is not None:
            
            import_options_type = panel.GetImportOptionsType()
            
            CG.client_controller.new_options.SetInteger( 'last_selected_import_options_container_panel_options_type', import_options_type )
            
        
    
    def _UpdateLabels( self ):
        
        for ( i, page ) in enumerate( self._listbook.GetPages() ):
            
            page = typing.cast( DefaultableImportOptionsPanel, page )
            
            label = page.GetLabel()
            
            self._listbook.setTabText( i, label )
            
        
    
    def GetName( self ) -> str:
        
        name = self._name_edit.text()
        
        if name == '':
            
            name = 'favourite'
            
        
        return name
        
    
    def GetValue( self ) -> ImportOptionsContainer.ImportOptionsContainer:
        
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        for page in self._listbook.GetPages():
            
            page = typing.cast( DefaultableImportOptionsPanel, page )
            
            if not page.IsDefault():
                
                import_options_container.SetImportOptions( page.GetImportOptionsType(), page.GetValue() )
                
            
        
        return import_options_container
        
    

class ImportOptionsContainerFavouritesButton( ClientGUICommon.IconButton ):
    
    def __init__( self, parent: QW.QWidget, import_options_container_manager: ImportOptionsContainer.ImportOptionsManager, edit_allowed = True ):
        
        super().__init__( parent, CC.global_icons().star, self._ShowMenu )
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( 'favourites' ) )
        
        self._import_options_container_manager = import_options_container_manager
        self._edit_allowed = edit_allowed
        
        if not self._edit_allowed and len( self._import_options_container_manager.GetFavouriteImportOptionContainers() ) == 0:
            
            self.setEnabled( False )
            
        
    
    def _Add( self ):
        
        name = 'new import options favourite'
        import_options_container = ImportOptionsContainer.ImportOptionsContainer()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit favourite import options' ) as dlg:
            
            panel = EditImportOptionsContainerPanel( dlg, self._import_options_container_manager, import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES, favourites_name = name )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_name = panel.GetName()
                edited_import_options_container = panel.GetValue()
                
                self._import_options_container_manager.AddFavourite( edited_name, edited_import_options_container )
                
            
        
    
    def _Copy( self, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        payload = import_options_container.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', payload )
        
    
    def _Delete( self, name: str ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, f'Delete the favourite named "{name}"?' )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._import_options_container_manager.DeleteFavourite( name )
        
    
    def _Edit( self, name: str, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit favourite import options' ) as dlg:
            
            panel = EditImportOptionsContainerPanel( dlg, self._import_options_container_manager, import_options_container, ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES, favourites_name = name )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_name = panel.GetName()
                edited_import_options_container = panel.GetValue()
                
                self._import_options_container_manager.EditFavourite( name, edited_name, edited_import_options_container )
                
            
        
    
    def _ShowMenu( self ):
        
        names_to_favourite_options_containers = self._import_options_container_manager.GetFavouriteImportOptionContainers()
        
        names_in_order = sorted( names_to_favourite_options_containers.keys(), key = HydrusText.HumanTextSortKey )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        #
        
        ClientGUIMenus.AppendMenuLabel( menu, 'favourites', make_it_bold = True )
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( names_to_favourite_options_containers ) > 0:
            
            copy_menu = ClientGUIMenus.GenerateMenu( menu )
            
            for name in names_in_order:
                
                import_options_container = names_to_favourite_options_containers[ name ]
                
                summary = import_options_container.GetSummary( show_downloader_options = True )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, f'{name} - {summary}', 'copy this import options container to clipboard', self._Copy, import_options_container )
                
            
            ClientGUIMenus.AppendMenu( menu, copy_menu, 'copy' )
            
        
        if self._edit_allowed:
            
            edit_menu = ClientGUIMenus.GenerateMenu( self )
            
            if len( names_to_favourite_options_containers ) > 0:
                
                for name in names_in_order:
                    
                    import_options_container = names_to_favourite_options_containers[ name ]
                    
                    summary = import_options_container.GetSummary( show_downloader_options = True )
                    
                    ClientGUIMenus.AppendMenuItem( edit_menu, f'{name} - {summary}', 'copy this import options container to clipboard', self._Edit, name, import_options_container )
                    
                
                ClientGUIMenus.AppendSeparator( edit_menu )
                
            
            ClientGUIMenus.AppendMenuItem( edit_menu, 'add new favourite', 'Create an empty favourite', self._Add )
            
            ClientGUIMenus.AppendMenu( menu, edit_menu, 'edit' )
            
            #
            
            if len( names_to_favourite_options_containers ) > 0:
                
                delete_menu = ClientGUIMenus.GenerateMenu( menu )
                
                for name in names_in_order:
                    
                    import_options_container = names_to_favourite_options_containers[ name ]
                    
                    summary = import_options_container.GetSummary( show_downloader_options = True )
                    
                    ClientGUIMenus.AppendMenuItem( delete_menu, f'{name} - {summary}', 'delete this import options container from the favourites store', self._Delete, name )
                    
                
                ClientGUIMenus.AppendMenu( menu, delete_menu, 'delete' )
                
            
        
        #
        
        CGC.core().PopupMenu( self, menu )
        
    

class DefaultableImportOptionsPanel( ClientGUICommon.StaticBox ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, import_options_container_manager: ImportOptionsContainer.ImportOptionsManager, import_options_type: int, import_options_container: ImportOptionsContainer.ImportOptionsContainer, default_import_options_container: ImportOptionsContainer.ImportOptionsContainer, import_options_caller_type: int, url_class_key: bytes | None = None ):
        
        super().__init__( parent, ImportOptionsContainer.import_options_type_str_lookup[ import_options_type ] )
        
        self._import_options_container_manager = import_options_container_manager
        self._import_options_type = import_options_type
        self._default_import_options_container = default_import_options_container
        self._import_options_caller_type = import_options_caller_type
        self._url_class_key = url_class_key
        
        if import_options_container.HasImportOptions( self._import_options_type ):
            
            is_default = False
            
            import_options = import_options_container.GetImportOptions( self._import_options_type )
            
        else:
            
            is_default = True
            
            import_options = self._default_import_options_container.GetImportOptions( self._import_options_type )
            
        
        #
        
        self._description_label = ClientGUICommon.BetterStaticText( self, label = ImportOptionsContainer.import_options_type_desc_lookup[ import_options_type ] )
        self._description_label.setWordWrap( True )
        self._description_label.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._use_default_dropdown = ClientGUICommon.BetterChoice( self )
        
        self._use_default_dropdown.addItem( f'use the default import options ({self._default_import_options_container.GetSourceLabel( self._import_options_type )})', True )
        self._use_default_dropdown.addItem( 'use specific import options', False )
        
        self._use_default_dropdown.SetValue( is_default )
        
        self._paste_button = ClientGUICommon.IconButton( self, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste an just this type of import options, if your clipboard holds it.' ) )
        
        if import_options_caller_type == ImportOptionsContainer.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL and not is_default:
            
            self._use_default_dropdown.setVisible( False )
            
        
        show_downloader_options = not self._import_options_caller_type in ImportOptionsContainer.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES
        
        if self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PREFETCH:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditPrefetchImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_FILE_FILTERING:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditFileFilteringImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAG_FILTERING:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditTagFilteringImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_LOCATIONS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditLocationImportOptionsPanel( self, import_options, show_downloader_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_TAGS:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditTagImportOptionsPanel( self, import_options, show_downloader_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_NOTES:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditNoteImportOptionsPanel( self, import_options )
            
        elif self._import_options_type == ImportOptionsContainer.IMPORT_OPTIONS_TYPE_PRESENTATION:
            
            self._options_panel = ClientGUIImportOptionsPanels.EditPresentationImportOptions( self, import_options )
            
        else:
            
            raise Exception( 'Unknown import options type!' )
            
        
        self._options_panel.valueChanged.connect( self.valueChanged )
        
        self._UpdateIsDefaultVisibility()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._use_default_dropdown, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        hbox.addStretch( 0 )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER )
        
        self.Add( self._description_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._use_default_dropdown.currentIndexChanged.connect( self._UpdateIsDefaultVisibility )
        self._use_default_dropdown.currentIndexChanged.connect( self.valueChanged )
        
    
    def _Paste( self ):
        
        try:
            
            pasted_import_options_container = GetPasteObject( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        import_options = pasted_import_options_container.GetImportOptions( self._import_options_type )
        
        if import_options is None:
            
            message = f'Hey, I am afraid what you pasted does not have a defined (non-default) import options of type "{ImportOptionsContainer.import_options_type_str_lookup[ self._import_options_type ]}"! Make sure you copied the right thing and try again.'
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
            return
            
        
        self._options_panel.SetValue( import_options )
        
        self._use_default_dropdown.SetValue( False )
        self._UpdateIsDefaultVisibility()
        
        self.valueChanged.emit()
        
    
    def _UpdateIsDefaultVisibility( self ):
        
        self._options_panel.setVisible( not self._use_default_dropdown.GetValue() )
        
    
    def GetImportOptionsType( self ) -> int:
        
        return self._import_options_type
        
    
    def GetLabel( self ) -> str:
        
        label = ImportOptionsContainer.import_options_type_str_lookup[ self._import_options_type ]
        
        if self._use_default_dropdown.GetValue():
            
            default_label = self._default_import_options_container.GetSourceLabel( self._import_options_type )
            
            label += f': default ({default_label})'
            
        else:
            
            import_options = self.GetValue()
            
            show_downloader_options = not self._import_options_caller_type in ImportOptionsContainer.NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES
            
            summary = import_options.GetSummary( show_downloader_options )
            
            if len( summary ) > 0:
                
                label += ': ' + summary
                
            
        
        return HydrusText.ElideText( label.splitlines()[0], 256 )
        
    
    def GetValue( self ) -> ImportOptionsContainer.ImportOptionsMetatype:
        
        return self._options_panel.GetValue()
        
    
    def SetValue( self, import_options: ImportOptionsContainer.ImportOptionsMetatype ):
        
        self._options_panel.SetValue( import_options )
        
    
    def IsDefault( self ) -> bool:
        
        return self._use_default_dropdown.GetValue()
        
    
    def SetDefault( self, value: bool ):
        
        self._use_default_dropdown.SetValue( value )
        
        self._UpdateIsDefaultVisibility()
        
    
