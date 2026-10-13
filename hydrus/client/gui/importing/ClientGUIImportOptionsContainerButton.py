from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.importing import ClientGUIImportOptionsContainer
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.importing.options import ImportOptionsConstants as IOC
from hydrus.client.importing.options import ImportOptionsContainer

class SpecificImportOptionsContainerButton( ClientGUICommon.ButtonWithMenuArrow ):
    
    importOptionsChanged = QC.Signal( ImportOptionsContainer.ImportOptionsContainer )
    
    def __init__( self, parent: QW.QWidget, default_stack_import_options_caller_type: int, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._default_stack_import_options_caller_type = default_stack_import_options_caller_type
        self._import_options_container = import_options_container
        
        action = QW.QAction()
        
        action.setText( 'import options' )
        action.setToolTip( ClientGUIFunctions.WrapToolTip( 'edit the different options for this importer' ) )
        
        action.triggered.connect( self._EditOptions )
        
        super().__init__( parent, action )
        
        self._UpdateLabelAndToolTip()
        
    
    def _CopyOneSetOfImportOptions( self, import_options_type: int ):
        
        import_options = self._import_options_container.GetImportOptions( import_options_type )
        
        if import_options is None:
            
            return
            
        
        json_string = import_options.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _CopyImportOptions( self ):
        
        json_string = self._import_options_container.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', json_string )
        
    
    def _EditDefaultImportOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit default import options' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            from hydrus.client.gui.panels.options import ImportOptionsPanel 
            
            options_panel = ImportOptionsPanel.ImportOptionsPanel( panel, CG.client_controller.new_options, CG.client_controller.import_options_manager )
            
            panel.SetControl( options_panel )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                options_panel.UpdateOptions()
                
            
        
    
    def _EditOptions( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit import options' ) as dlg:
            
            panel = ClientGUIImportOptionsContainer.EditSpecificImportOptionsContainerPanel(
                dlg,
                CG.client_controller.import_options_manager,
                self._default_stack_import_options_caller_type,
                self._import_options_container
            )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_import_options_container = panel.GetValue()
                
                self._SetValue( edited_import_options_container )
                
            
        
    
    def _LoadFavouriteCustom( self, loaded_import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        simple_mode = CG.client_controller.new_options.GetBoolean( 'import_options_simple_mode' )
        
        try:
            
            edited_import_options_container = ClientGUIImportOptionsContainer.DoCustomOverwrite( self, simple_mode, IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER, self._import_options_container, loaded_import_options_container )
            
        except HydrusExceptions.CancelledException as e:
            
            return
            
        
        self._SetValue( edited_import_options_container )
        
    
    def _PasteImportOptions( self ):
        
        # this should crib from the other paste stuff and boot that merge dialog mate. the menu too should follow that convention
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            pasted_import_options_container = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( pasted_import_options_container, ImportOptionsContainer.ImportOptionsContainer ):
                
                raise Exception( 'Not an Import Options Container!' )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Import Options Container', e )
            
            return
            
        
        simple_mode = CG.client_controller.new_options.GetBoolean( 'import_options_simple_mode' )
        
        try:
            
            edited_import_options_container = ClientGUIImportOptionsContainer.DoCustomOverwrite( self, simple_mode, IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER, self._import_options_container, pasted_import_options_container )
            
        except HydrusExceptions.CancelledException as e:
            
            return
            
        
        self._SetValue( edited_import_options_container )
        
    
    def _PopulateMenu( self, menu ):
        
        summary_menu = ClientGUIMenus.GenerateMenu( self )
        
        for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
            
            import_options = self._import_options_container.GetImportOptions( import_options_type )
            
            if import_options is None:
                
                summary = 'default'
                
            else:
                
                summary = import_options.GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
                
            
            label = IOC.import_options_type_str_lookup[ import_options_type ] + ': ' + summary
            
            ClientGUIMenus.AppendMenuLabel( summary_menu, label, label )
            
        
        ClientGUIMenus.AppendMenu( menu, summary_menu, 'current options' )
        
        names_to_favourite_options_containers = CG.client_controller.import_options_manager.GetFavouriteImportOptionContainers()
        
        names_in_order = sorted( names_to_favourite_options_containers.keys(), key = HydrusText.HumanTextSortKey )
        
        #
        
        if len( names_to_favourite_options_containers ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            load_menu = ClientGUIMenus.GenerateMenu( self )
            load_custom_menu = ClientGUIMenus.GenerateMenu( self )
            
            for name in names_in_order:
                
                import_options_container = names_to_favourite_options_containers[ name ]
                
                summary = import_options_container.GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
                
                ClientGUIMenus.AppendMenuItem( load_menu, f'{name} - {summary}', 'load this import options container to the current selection', self._SetValue, import_options_container )
                ClientGUIMenus.AppendMenuItem( load_custom_menu, f'{name} - {summary}', 'load some or all of this import options container to the current selection', self._LoadFavouriteCustom, import_options_container )
                
            
            ClientGUIMenus.AppendMenu( menu, load_menu, 'load' )
            ClientGUIMenus.AppendMenu( menu, load_custom_menu, 'custom load' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'edit defaults and favourites', 'Open up the options panel for import options.', self._EditDefaultImportOptions )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        copy_menu = ClientGUIMenus.GenerateMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( copy_menu, 'these import options', 'Copy everything this button is currently holding, even if that is "all default".', self._CopyImportOptions )
        
        copyable_import_options_types = [ import_options_type for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER if self._import_options_container.HasImportOptions( import_options_type ) ]
        
        if len( copyable_import_options_types ) > 0:
            
            ClientGUIMenus.AppendSeparator( copy_menu )
            
            for import_options_type in copyable_import_options_types:
                
                ClientGUIMenus.AppendMenuItem( copy_menu, IOC.import_options_type_str_lookup[ import_options_type ], 'Copy just this import options.', self._CopyOneSetOfImportOptions, import_options_type )
                
            
        
        ClientGUIMenus.AppendMenu( menu, copy_menu, 'copy' )
        
        ClientGUIMenus.AppendMenuItem( menu, 'paste', 'Paste what you have in the clipboard to this import options. Will start the custom merge dialog.', self._PasteImportOptions )
        
        if IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER != IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            ClientGUIMenus.AppendMenuItem( menu, 'clear', 'Set this completely back to default.', self._SetAllDefault )
            
        
    
    def _SetAllDefault( self ):
        
        if IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER == IOC.IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            return
            
        
        self._SetValue( ImportOptionsContainer.ImportOptionsContainer() )
        
    
    def _SetValue( self, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        something_actually_changed = import_options_container.DumpToString() != self._import_options_container.DumpToString()
        
        self._import_options_container = import_options_container
        
        if something_actually_changed:
            
            self._UpdateLabelAndToolTip()
            
            self.importOptionsChanged.emit( self._import_options_container )
            
        
    
    def _UpdateLabelAndToolTip( self ):
        
        non_default_import_options_types = [ import_options_type for import_options_type in IOC.IMPORT_OPTIONS_TYPES_CANONICAL_ORDER if self._import_options_container.HasImportOptions( import_options_type ) ]
        
        if len( non_default_import_options_types ) == 0:
            
            label = 'import options (all default)'
            tooltip = 'The import options here have nothing custom set. This importer will use the respective defaults.'
            
        elif len( non_default_import_options_types ) == 1:
            
            import_options_type = non_default_import_options_types[0]
            
            label = f'import options ({IOC.import_options_type_str_lookup[ import_options_type ]} set)'
            
            import_options = self._import_options_container.GetImportOptions( import_options_type )
            
            tooltip = import_options.GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
            
        else:
            
            all_types_string = ', '.join( [ IOC.import_options_type_str_lookup[ import_options_type ]  for import_options_type in non_default_import_options_types ] )
            
            label = f'import options ({all_types_string})'
            
            tooltip = '\n'.join( self._import_options_container.GetImportOptions( import_options_type ).GetSummary( IOC.IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER ) for import_options_type in non_default_import_options_types )
            
        
        my_action = self.defaultAction()
        
        my_action.setText( HydrusText.ElideText( label, 48 ) )
        
        my_action.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
        
    
    def GetValue( self ) -> ImportOptionsContainer.ImportOptionsContainer:
        
        return self._import_options_container
        
    
    def SetValue( self, import_options_container: ImportOptionsContainer.ImportOptionsContainer ):
        
        self._SetValue( import_options_container )
        
    
