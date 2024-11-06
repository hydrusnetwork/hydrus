import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientParsing
from hydrus.client import ClientSerialisable
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUIStringPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.parsing import ClientGUIParsingTest
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton

class EditSpecificFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool ):
        
        super().__init__( parent )
        
        self._collapse_newlines = collapse_newlines
        
    
    def GetValue( self ):
        
        raise NotImplementedError()
        
    

class EditContextVariableFormulaPanel( EditSpecificFormulaPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool, formula: ClientParsing.ParseFormulaContextVariable, test_data: ClientParsing.ParsingTestData ):
        
        super().__init__( parent, collapse_newlines )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_CONTEXT_VARIABLE_FORMULA )
        
        menu_items.append( ( 'normal', 'open the context variable formula help', 'Open the help page for context variable formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        self._test_panel.SetCollapseNewlines( collapse_newlines )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._variable_name = QW.QLineEdit( edit_panel )
        
        variable_name = formula.GetVariableName()
        name = formula.GetName()
        string_processor = formula.GetStringProcessor()
        
        self._name = QW.QLineEdit( edit_panel )
        self._name.setText( name )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'Optional, and decorative only. Leave blank to set nothing.' ) )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        self._variable_name.setText( variable_name )
        
        #
        
        rows = []
        
        rows.append( ( 'name/description:', self._name ) )
        rows.append( ( 'variable name:', self._variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if collapse_newlines:
            
            label = 'Newlines are removed from parsed strings right after parsing, before string processing.'
            
        else:
            
            label = 'Newlines are not collapsed here (probably a note parser)'
            
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, label, ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        variable_name = self._variable_name.text()
        
        name = self._name.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaContextVariable( variable_name = variable_name, name = name, string_processor = string_processor )
        
        return formula
        
    
class EditFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, formula: ClientParsing.ParseFormula, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ] ):
        
        super().__init__( parent )
        
        self._current_formula = formula
        self._test_data_callable = test_data_callable
        
        self._collapse_newlines = True
        
        #
        
        my_panel = ClientGUICommon.StaticBox( self, 'formula' )
        
        self._formula_description = QW.QPlainTextEdit( my_panel )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._formula_description, ( 90, 8 ) )
        
        self._formula_description.setMinimumWidth( width )
        self._formula_description.setMinimumHeight( height )
        
        self._formula_description.setEnabled( False )
        
        self._edit_formula = ClientGUICommon.BetterButton( my_panel, 'edit formula', self._EditFormula )
        
        self._change_formula_type = ClientGUICommon.BetterButton( my_panel, 'change formula type', self._ChangeFormulaType )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'to clipboard', 'Serialise the formula and put it on your clipboard.', self.ExportToClipboard ) )
        menu_items.append( ( 'normal', 'to png', 'Serialise the formula and encode it to an image file you can easily share with other hydrus users.', self.ExportToPNG ) )
        
        self._export_button = ClientGUIMenuButton.MenuButton( self, 'export', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'from clipboard', 'Load a formula from text in your clipboard.', self.ImportFromClipboard ) )
        menu_items.append( ( 'normal', 'from png', 'Load a formula from an encoded png.', self.ImportFromPNG ) )
        
        self._import_button = ClientGUIMenuButton.MenuButton( self, 'import', menu_items )
        
        #
        
        self._UpdateControls()
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._edit_formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._change_formula_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._export_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._import_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        my_panel.Add( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        my_panel.Add( button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ChangeFormulaType( self ):
        
        if self._current_formula.ParsesSeparatedContent():
            
            new_html = ClientParsing.ParseFormulaHTML( content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
            new_json = ClientParsing.ParseFormulaJSON( content_to_fetch = ClientParsing.JSON_CONTENT_JSON )
            
        else:
            
            new_html = ClientParsing.ParseFormulaHTML()
            new_json = ClientParsing.ParseFormulaJSON()
            
        
        new_zipper = ClientParsing.ParseFormulaZipper()
        new_context_variable = ClientParsing.ParseFormulaContextVariable()
        new_nested = ClientParsing.ParseFormulaNested()
        
        choice_tuples = []
        
        if not isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            choice_tuples.append( ( 'change to a new HTML formula', new_html ) )
            
        
        if not isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            choice_tuples.append( ( 'change to a new JSON formula', new_json ) )
            
        
        if not isinstance( self._current_formula, ClientParsing.ParseFormulaNested ):
            
            choice_tuples.append( ( 'change to a new NESTED formula', new_nested ) )
            
        
        if not isinstance( self._current_formula, ClientParsing.ParseFormulaZipper ):
            
            choice_tuples.append( ( 'change to a new ZIPPER formula', new_zipper ) )
            
        
        if not isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            choice_tuples.append( ( 'change to a new CONTEXT VARIABLE formula', new_context_variable ) )
            
        
        try:
            
            self._current_formula = ClientGUIDialogsQuick.SelectFromList( self, 'select formula type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._UpdateControls()
        
    
    def _EditFormula( self ):
        
        if isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            panel_class = EditHTMLFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            panel_class = EditJSONFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaNested ):
            
            panel_class = EditNestedFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaZipper ):
            
            panel_class = EditZipperFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            panel_class = EditContextVariableFormulaPanel
            
        else:
            
            raise Exception( 'Formula type not found!' )
            
        
        test_data = self._test_data_callable()
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = panel_class( dlg, self._collapse_newlines, self._current_formula, test_data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._current_formula = panel.GetValue()
                
                self._UpdateControls()
                
            
        
    
    def _GetExportObject( self ):
        
        return self._current_formula
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, ClientParsing.ParseFormula ):
            
            formula = obj
            
            self._current_formula = formula
            
            self._UpdateControls()
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, f'That was not a formula--it was a: {type(obj).__name__}' )
            
        
    
    def ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            CG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def ExportToPNG( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PNGExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def ImportFromClipboard( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Formula', e )
            
        
    
    def ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png with the encoded formula', wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                try:
                    
                    payload = ClientSerialisable.LoadFromPNG( path )
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', str(e) )
                    
                    return
                    
                
                try:
                    
                    obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                    
                    self._ImportObject( obj )
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', 'I could not understand what was encoded in the png!' )
                    
                
            
        
    
    def _UpdateControls( self ):
        
        if self._current_formula is None:
            
            self._formula_description.clear()
            
            self._edit_formula.setEnabled( False )
            self._change_formula_type.setEnabled( False )
            
        else:
            
            self._formula_description.setPlainText( self._current_formula.ToPrettyMultilineString() )
            
            self._edit_formula.setEnabled( True )
            self._change_formula_type.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        return self._current_formula
        
    
    def SetCollapseNewlines( self, value: bool ):
        
        self._collapse_newlines = value
        
    

class EditHTMLTagRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_rule ):
        
        super().__init__( parent )
        
        ( rule_type, tag_name, tag_attributes, tag_index, tag_depth, should_test_tag_string, tag_string_string_match ) = tag_rule.ToTuple()
        
        if tag_name is None:
            
            tag_name = ''
            
        
        if tag_attributes is None:
            
            tag_attributes = {}
            
        
        if tag_depth is None:
            
            tag_depth = 1
            
        
        self._current_description = ClientGUICommon.BetterStaticText( self )
        
        self._rule_type = ClientGUICommon.BetterChoice( self )
        
        self._rule_type.addItem( 'search descendants', ClientParsing.HTML_RULE_TYPE_DESCENDING )
        self._rule_type.addItem( 'walk back up ancestors', ClientParsing.HTML_RULE_TYPE_ASCENDING )
        self._rule_type.addItem( 'search previous siblings', ClientParsing.HTML_RULE_TYPE_PREV_SIBLINGS )
        self._rule_type.addItem( 'search next siblings', ClientParsing.HTML_RULE_TYPE_NEXT_SIBLINGS )
        
        self._tag_name = QW.QLineEdit( self )
        
        self._tag_attributes = ClientGUIStringControls.StringToStringDictControl( self, tag_attributes, min_height = 4 )
        
        self._tag_index = ClientGUICommon.NoneableSpinCtrl( self, 0, message = 'index to fetch', none_phrase = 'get all', min = -65536, max = 65535 )
        self._tag_index.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can make this negative to do negative indexing, e.g. -2 for "Select the second from last item".' ) )
        
        self._tag_depth = ClientGUICommon.BetterSpinBox( self, min=1, max=255 )
        
        self._should_test_tag_string = QW.QCheckBox( self )
        
        self._tag_string_string_match = ClientGUIStringControls.StringMatchButton( self, tag_string_string_match )
        
        #
        
        self._rule_type.SetValue( rule_type )
        self._tag_name.setText( tag_name )
        self._tag_index.SetValue( tag_index )
        self._tag_depth.setValue( tag_depth )
        self._should_test_tag_string.setChecked( should_test_tag_string )
        
        self._UpdateTypeControls()
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'rule type: ', self._rule_type ) )
        rows.append( ( 'tag name: ', self._tag_name ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'index to fetch: ', self._tag_index ) )
        rows.append( ( 'depth to climb: ', self._tag_depth ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'should test tag string: ', self._should_test_tag_string ) )
        rows.append( ( 'tag string match: ', self._tag_string_string_match ) )
        
        gridbox_3 = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, self._current_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_attributes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateShouldTest()
        
        #
        
        self._rule_type.currentIndexChanged.connect( self.EventTypeChanged )
        self._tag_name.textChanged.connect( self.EventVariableChanged )
        self._tag_attributes.columnListContentsChanged.connect( self.EventVariableChanged )
        self._tag_index.valueChanged.connect( self.EventVariableChanged )
        self._tag_depth.valueChanged.connect( self.EventVariableChanged )
        
        self._should_test_tag_string.clicked.connect( self.EventShouldTestChanged )
        
        ClientGUIFunctions.SetFocusLater( self._tag_name )
        
    
    def _UpdateShouldTest( self ):
        
        if self._should_test_tag_string.isChecked():
            
            self._tag_string_string_match.setEnabled( True )
            
        else:
            
            self._tag_string_string_match.setEnabled( False )
            
        
    
    def _UpdateTypeControls( self ):
        
        rule_type = self._rule_type.GetValue()
        
        if rule_type in [ ClientParsing.HTML_RULE_TYPE_DESCENDING, ClientParsing.HTML_RULE_TYPE_NEXT_SIBLINGS, ClientParsing.HTML_RULE_TYPE_PREV_SIBLINGS ]:
            
            self._tag_attributes.setEnabled( True )
            self._tag_index.setEnabled( True )
            
            self._tag_depth.setEnabled( False )
            
        else:
            
            self._tag_attributes.setEnabled( False )
            self._tag_index.setEnabled( False )
            
            self._tag_depth.setEnabled( True )
            
        
        self._UpdateDescription()
        
    
    def _UpdateDescription( self ):
        
        tag_rule = self.GetValue()
        
        label = tag_rule.ToString()
        
        self._current_description.setText( label )
        
    
    def EventShouldTestChanged( self ):
        
        self._UpdateShouldTest()
        
    
    def EventTypeChanged( self, index ):
        
        self._UpdateTypeControls()
        
    
    def EventVariableChanged( self ):
        
        self._UpdateDescription()
        
    
    def GetValue( self ):
        
        rule_type = self._rule_type.GetValue()
        
        tag_name = self._tag_name.text()
        
        if tag_name == '':
            
            tag_name = None
            
        
        should_test_tag_string = self._should_test_tag_string.isChecked()
        tag_string_string_match = self._tag_string_string_match.GetValue()
        
        if rule_type in [ ClientParsing.HTML_RULE_TYPE_DESCENDING, ClientParsing.HTML_RULE_TYPE_NEXT_SIBLINGS, ClientParsing.HTML_RULE_TYPE_PREV_SIBLINGS ]:
            
            tag_attributes = self._tag_attributes.GetValue()
            tag_index = self._tag_index.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        elif rule_type == ClientParsing.HTML_RULE_TYPE_ASCENDING:
            
            tag_depth = self._tag_depth.value()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_depth = tag_depth, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        
        return tag_rule
        
    
class EditHTMLFormulaPanel( EditSpecificFormulaPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool, formula: ClientParsing.ParseFormulaHTML, test_data: ClientParsing.ParsingTestData ):
        
        super().__init__( parent, collapse_newlines )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_HTML_FORMULA )
        
        menu_items.append( ( 'normal', 'open the html formula help', 'Open the help page for html formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        self._test_panel.SetCollapseNewlines( self._collapse_newlines )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._tag_rules = ClientGUIListBoxes.BetterQListWidget( edit_panel )
        self._tag_rules.setSelectionMode( QW.QAbstractItemView.SingleSelection )

        self._tag_rules.itemDoubleClicked.connect( self.Edit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.addItem( 'attribute', ClientParsing.HTML_CONTENT_ATTRIBUTE )
        self._content_to_fetch.addItem( 'string', ClientParsing.HTML_CONTENT_STRING )
        self._content_to_fetch.addItem( 'html', ClientParsing.HTML_CONTENT_HTML )
        
        self._content_to_fetch.currentIndexChanged.connect( self._UpdateControls )
        
        self._attribute_to_fetch = QW.QLineEdit( edit_panel )
        
        tag_rules = formula.GetTagRules()
        content_to_fetch = formula.GetContentToFetch()
        attribute_to_fetch = formula.GetAttributeToFetch()
        name = formula.GetName()
        string_processor = formula.GetStringProcessor()
        
        self._name = QW.QLineEdit( edit_panel )
        self._name.setText( name )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'Optional, and decorative only. Leave blank to set nothing.' ) )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        for rule in tag_rules:
            
            pretty_rule = rule.ToString()
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.addItem( item )
            
        
        self._content_to_fetch.SetValue( content_to_fetch )
        
        self._attribute_to_fetch.setText( attribute_to_fetch )
        
        self._UpdateControls()
        
        #
        
        udd_button_vbox = QP.VBoxLayout()
        
        udd_button_vbox.addStretch( 1 )
        QP.AddToLayout( udd_button_vbox, self._move_rule_up, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._delete_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._move_rule_down, CC.FLAGS_CENTER_PERPENDICULAR )
        udd_button_vbox.addStretch( 1 )
        
        tag_rules_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( tag_rules_hbox, self._tag_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( tag_rules_hbox, udd_button_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        ae_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ae_button_hbox, self._add_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ae_button_hbox, self._edit_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'name/description:', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        edit_panel.Add( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        rows.append( ( 'attribute to fetch: ', self._attribute_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if collapse_newlines:
            
            label = 'Newlines are removed from parsed strings right after parsing, before string processing.'
            
        else:
            
            label = 'Newlines are not collapsed here (probably a note parser)'
            
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, label, ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _UpdateControls( self ):
        
        if self._content_to_fetch.GetValue() == ClientParsing.HTML_CONTENT_ATTRIBUTE:
            
            self._attribute_to_fetch.setEnabled( True )
            
        else:
            
            self._attribute_to_fetch.setEnabled( False )
            
        
    
    def Add( self ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ClientParsing.ParseRuleHTML()
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                rule = panel.GetValue()
                
                pretty_rule = rule.ToString()
                
                item = QW.QListWidgetItem()
                item.setText( pretty_rule )
                item.setData( QC.Qt.UserRole, rule )
                self._tag_rules.addItem( item )
                
            
        
    
    def Delete( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules )
        
        if selection != -1:
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
        
    
    def Edit( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules )
        
        if selection != -1:
            
            rule = QP.GetClientData( self._tag_rules, selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = rule.ToString()
                    
                    self._tag_rules.item( selection ).setText( pretty_rule )
                    self._tag_rules.item( selection ).setData( QC.Qt.UserRole, rule )
                    
                
            
        
    
    def GetValue( self ):
        
        tag_rules = [ QP.GetClientData( self._tag_rules, i ) for i in range( self._tag_rules.count() ) ]
        
        content_to_fetch = self._content_to_fetch.GetValue()
        
        attribute_to_fetch = self._attribute_to_fetch.text()
        
        if content_to_fetch == ClientParsing.HTML_CONTENT_ATTRIBUTE and attribute_to_fetch == '':
            
            raise HydrusExceptions.VetoException( 'Please enter an attribute to fetch!' )
            
        
        name = self._name.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaHTML(
            tag_rules = tag_rules,
            content_to_fetch = content_to_fetch,
            attribute_to_fetch = attribute_to_fetch,
            name = name,
            string_processor = string_processor
        )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules )
        
        if selection != -1 and selection + 1 < self._tag_rules.count():
            
            pretty_rule = self._tag_rules.item( selection ).text()
            rule = QP.GetClientData( self._tag_rules, selection )
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.insertItem( selection + 1, item )
            
        
    
    def MoveUp( self ):
        
        selection = QP.ListWidgetGetSelection( self._tag_rules )
        
        if selection != -1 and selection > 0:
            
            pretty_rule = self._tag_rules.item( selection ).text()
            rule = QP.GetClientData( self._tag_rules, selection )
            
            QP.ListWidgetDelete( self._tag_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._tag_rules.insertItem( selection - 1, item )
            
        
    
class EditJSONParsingRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, rule: ClientParsing.ParseRuleHTML ):
        
        super().__init__( parent )
        
        self._parse_rule_type = ClientGUICommon.BetterChoice( self )
        
        self._parse_rule_type.addItem( 'dictionary entry', ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY )
        self._parse_rule_type.addItem( 'all dictionary/list items', ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS )
        self._parse_rule_type.addItem( 'indexed item', ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM )
        self._parse_rule_type.addItem( 'de-minify json', ClientParsing.JSON_PARSE_RULE_TYPE_DEMINIFY_JSON )
        
        string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' )
        
        self._string_match = ClientGUIStringPanels.EditStringMatchPanel( self, string_match )
        
        self._index = ClientGUICommon.BetterSpinBox( self, min=-65536, max=65535 )
        self._index.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can make this negative to do negative indexing, i.e. "Select the second from last item".' ) )
        
        #
        
        ( parse_rule_type, parse_rule ) = rule
        
        self._parse_rule_type.SetValue( parse_rule_type )
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.setValue( parse_rule )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.SetValue( parse_rule )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DEMINIFY_JSON:
            
            self._index.setValue( parse_rule )
            
        
        self._UpdateHideShow()
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'list index: ', self._index ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, self._parse_rule_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._parse_rule_type.currentIndexChanged.connect( self._UpdateHideShow )
        
    
    def _UpdateHideShow( self ):
        
        self._string_match.setEnabled( False )
        self._index.setEnabled( False )
        
        parse_rule_type = self._parse_rule_type.GetValue()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            self._string_match.setEnabled( True )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            self._index.setEnabled( True )
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DEMINIFY_JSON:
            
            self._index.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        parse_rule_type = self._parse_rule_type.GetValue()
        
        if parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY:
            
            parse_rule = self._string_match.GetValue()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM:
            
            parse_rule = self._index.value()
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS:
            
            parse_rule = None
            
        elif parse_rule_type == ClientParsing.JSON_PARSE_RULE_TYPE_DEMINIFY_JSON:
            
            parse_rule = self._index.value()
            
        
        return ( parse_rule_type, parse_rule )
        
    
class EditJSONFormulaPanel( EditSpecificFormulaPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool, formula: ClientParsing.ParseFormulaJSON, test_data: ClientParsing.ParsingTestData ):
        
        super().__init__( parent, collapse_newlines )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_JSON_FORMULA )
        
        menu_items.append( ( 'normal', 'open the json formula help', 'Open the help page for json formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        self._test_panel.SetCollapseNewlines( collapse_newlines )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._parse_rules = ClientGUIListBoxes.BetterQListWidget( edit_panel )
        self._parse_rules.setSelectionMode( QW.QAbstractItemView.SingleSelection )
        self._parse_rules.itemDoubleClicked.connect( self.Edit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, '\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, '\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.addItem( 'string', ClientParsing.JSON_CONTENT_STRING )
        self._content_to_fetch.addItem( 'dictionary keys', ClientParsing.JSON_CONTENT_DICT_KEYS )
        self._content_to_fetch.addItem( 'json', ClientParsing.JSON_CONTENT_JSON )
        
        parse_rules = formula.GetParseRules()
        content_to_fetch = formula.GetContentToFetch()
        name = formula.GetName()
        string_processor = formula.GetStringProcessor()
        
        self._name = QW.QLineEdit( edit_panel )
        self._name.setText( name )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'Optional, and decorative only. Leave blank to set nothing.' ) )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        for rule in parse_rules:
            
            pretty_rule = ClientParsing.RenderJSONParseRule( rule )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.addItem( item )
            
        
        self._content_to_fetch.SetValue( content_to_fetch )
        
        #
        
        udd_button_vbox = QP.VBoxLayout()
        
        udd_button_vbox.addStretch( 1 )
        QP.AddToLayout( udd_button_vbox, self._move_rule_up, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._delete_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( udd_button_vbox, self._move_rule_down, CC.FLAGS_CENTER_PERPENDICULAR )
        udd_button_vbox.addStretch( 1 )
        
        parse_rules_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( parse_rules_hbox, self._parse_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( parse_rules_hbox, udd_button_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        ae_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ae_button_hbox, self._add_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ae_button_hbox, self._edit_rule, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'name/description:', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        edit_panel.Add( parse_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if collapse_newlines:
            
            label = 'Newlines are removed from parsed strings right after parsing, before string processing.'
            
        else:
            
            label = 'Newlines are not collapsed here (probably a note parser)'
            
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, label, ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def Add( self ):
        
        dlg_title = 'edit parse rule'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
            
            panel = EditJSONParsingRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                rule = panel.GetValue()
                
                pretty_rule = ClientParsing.RenderJSONParseRule( rule )

                item = QW.QListWidgetItem()
                item.setText( pretty_rule )
                item.setData( QC.Qt.UserRole, rule )
                self._parse_rules.addItem( item )
                
            
        
    
    def Delete( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules )
        
        if selection != -1:
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
        
    
    def Edit( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules )
        
        if selection != -1:
            
            rule = QP.GetClientData( self._parse_rules, selection )
            
            dlg_title = 'edit parse rule'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditJSONParsingRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                    
                    self._parse_rules.item( selection ).setText( pretty_rule )
                    self._parse_rules.item( selection ).setData( QC.Qt.UserRole, rule )
                    
                
            
        
    
    def GetValue( self ):
        
        parse_rules = [ QP.GetClientData( self._parse_rules, i ) for i in range( self._parse_rules.count() ) ]
        
        content_to_fetch = self._content_to_fetch.GetValue()
        
        name = self._name.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaJSON( parse_rules = parse_rules, content_to_fetch = content_to_fetch, name = name, string_processor = string_processor )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules )
        
        if selection != -1 and selection + 1 < self._parse_rules.count():
            
            pretty_rule = self._parse_rules.item( selection ).text()
            rule = QP.GetClientData( self._parse_rules, selection )
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.insertItem( selection + 1, item )
            
        
    
    def MoveUp( self ):
        
        selection = QP.ListWidgetGetSelection( self._parse_rules )
        
        if selection != -1 and selection > 0:
            
            pretty_rule = self._parse_rules.item( selection ).text()
            rule = QP.GetClientData( self._parse_rules, selection )
            
            QP.ListWidgetDelete( self._parse_rules, selection )
            
            item = QW.QListWidgetItem()
            item.setText( pretty_rule )
            item.setData( QC.Qt.UserRole, rule )
            self._parse_rules.insertItem( selection - 1, item )
            
        
    

class EditNestedFormulaPanel( EditSpecificFormulaPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool, formula: ClientParsing.ParseFormulaNested, test_data: ClientParsing.ParsingTestData ):
        
        super().__init__( parent, collapse_newlines )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_NESTED_FORMULA )
        
        menu_items.append( ( 'normal', 'open the nested formula help', 'Open the help page for nested formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        self._test_panel.SetCollapseNewlines( self._collapse_newlines )
        
        #
        
        main_formula = formula.GetMainFormula()
        sub_formula = formula.GetSubFormula()
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        main_panel = ClientGUICommon.StaticBox( edit_panel, 'first formula' )
        
        self._main_formula_panel = EditFormulaPanel( main_panel, main_formula, test_data_callable = self._test_panel.GetTestData )
        
        sub_panel = ClientGUICommon.StaticBox( edit_panel, 'second formula' )
        
        self._sub_formula_panel = EditFormulaPanel( sub_panel, sub_formula, test_data_callable = self._GetSubTestData )
        
        name = formula.GetName()
        string_processor = formula.GetStringProcessor()
        
        self._name = QW.QLineEdit( edit_panel )
        self._name.setText( name )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'Optional, and decorative only. Leave blank to set nothing.' ) )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        main_panel.Add( self._main_formula_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        sub_panel.Add( self._sub_formula_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        label = 'Whatever is parsed by the first formula is sent to the second. Use this if you have JSON embedded in HTML or vice versa. Even if the thing you want to parse is very simple, it can be worth doing it this proper way to ensure html entities etc.. are decoded properly and naturally!'
        
        st = ClientGUICommon.BetterStaticText( edit_panel, label )
        
        st.setWordWrap( True )
        
        edit_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'name/description:', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        edit_panel.Add( main_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( sub_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if collapse_newlines:
            
            label = 'Newlines are removed from parsed strings right after parsing, before string processing.'
            
        else:
            
            label = 'Newlines are not collapsed here (probably a note parser)'
            
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, label, ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _GetSubTestData( self ) -> ClientParsing.ParsingTestData:
        
        test_data = self._test_panel.GetTestData()
        
        example_parsing_context = test_data.parsing_context
        
        main_formula = self._main_formula_panel.GetValue()
        
        main_texts = [ '' ]
        
        try:
            
            for text in test_data.texts:
                
                main_texts = main_formula.Parse( example_parsing_context, text, self._collapse_newlines )
                
                if len( main_texts ) > 0:
                    
                    break
                    
                
            
        except:
            
            main_texts = [ '' ]
            
        
        return ClientParsing.ParsingTestData( example_parsing_context, main_texts )
        
    
    def GetValue( self ):
        
        main_formula = self._main_formula_panel.GetValue()
        sub_formula = self._sub_formula_panel.GetValue()
        name = self._name.text()
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaNested( main_formula = main_formula, sub_formula = sub_formula, name = name, string_processor = string_processor )
        
        return formula
        
    

class EditZipperFormulaPanel( EditSpecificFormulaPanel ):
    
    def __init__( self, parent: QW.QWidget, collapse_newlines: bool, formula: ClientParsing.ParseFormulaZipper, test_data: ClientParsing.ParsingTestData ):
        
        super().__init__( parent, collapse_newlines )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_ZIPPER_FORMULA )
        
        menu_items.append( ( 'normal', 'open the zipper formula help', 'Open the help page for zipper formulae in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        self._test_panel = ClientGUIParsingTest.TestPanelFormula( test_panel, self.GetValue, test_data = test_data )
        
        self._test_panel.SetCollapseNewlines( self._collapse_newlines )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._formulae = ClientGUIListBoxes.QueueListBox( edit_panel, 6, self._ConvertFormulaToListString, add_callable = self._Add, edit_callable = self._Edit )
        
        self._formulae.AddImportExportButtons( ( ClientParsing.ParseFormula, ) )
        
        self._sub_phrase = QW.QLineEdit( edit_panel )
        
        formulae = formula.GetFormulae()
        sub_phrase = formula.GetSubstitutionPhrase()
        name = formula.GetName()
        string_processor = formula.GetStringProcessor()
        
        self._name = QW.QLineEdit( edit_panel )
        self._name.setText( name )
        self._name.setToolTip( ClientGUIFunctions.WrapToolTip( 'Optional, and decorative only. Leave blank to set nothing.' ) )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( edit_panel, string_processor, self._test_panel.GetTestDataForStringProcessor )
        
        #
        
        self._formulae.AddDatas( formulae )
        
        self._sub_phrase.setText( sub_phrase )
        
        #
        
        rows = []
        
        rows.append( ( 'name/description:', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        edit_panel.Add( self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'substitution phrase:', self._sub_phrase ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if collapse_newlines:
            
            label = 'Newlines are removed from parsed strings right after parsing, before string processing.'
            
        else:
            
            label = 'Newlines are not collapsed here (probably a note parser)'
            
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, label, ellipsize_end = True ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        existing_formula = ClientParsing.ParseFormulaHTML()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditFormulaPanel( dlg, existing_formula, self._test_panel.GetTestDataForChild )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_formula = panel.GetValue()
                
                return new_formula
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _ConvertFormulaToListString( self, formula: ClientParsing.ParseFormula ) -> str:
        
        return formula.ToPrettyString()
        
    
    def _Edit( self, old_formula ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditFormulaPanel( dlg, old_formula, self._test_panel.GetTestDataForChild )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_formula = panel.GetValue()
                
                return new_formula
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def GetValue( self ):
        
        formulae = self._formulae.GetData()
        
        sub_phrase = self._sub_phrase.text()
        
        name = self._name.text()
        
        string_processor = self._string_processor_button.GetValue()
        
        formula = ClientParsing.ParseFormulaZipper(
            formulae = formulae,
            sub_phrase = sub_phrase,
            name = name,
            string_processor = string_processor
        )
        
        return formula
        
    
