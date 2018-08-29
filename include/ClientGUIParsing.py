import bs4
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIControls
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIScrolledPanels
import ClientGUISerialisable
import ClientGUITopLevelWindows
import ClientNetworkingJobs
import ClientParsing
import ClientPaths
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import json
import os
import sys
import threading
import traceback
import time
import wx

( StringConverterEvent, EVT_STRING_CONVERTER ) = wx.lib.newevent.NewCommandEvent()

class StringConverterButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_converter ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._example_string_override = None
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string converter', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditStringConverterPanel( dlg, self._string_converter, example_string_override = self._example_string_override )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
        wx.QueueEvent( self.GetEventHandler(), StringConverterEvent( -1 ) )
        
    
    def _UpdateLabel( self ):
        
        num_rules = len( self._string_converter.transformations )
        
        if num_rules == 0:
            
            label = 'no string transformations'
            
        else:
            
            label = HydrusData.ToHumanInt( num_rules ) + ' string transformations'
            
        
        self.SetLabelText( label )
        
    
    def GetValue( self ):
        
        return self._string_converter
        
    
    def SetExampleString( self, example_string ):
        
        self._example_string_override = example_string
        
    
    def SetValue( self, string_converter ):
        
        self._string_converter = string_converter
        
        self._UpdateLabel()
        
    
class StringMatchButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_match ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string match', self._Edit )
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string match', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditStringMatchPanel( dlg, self._string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._string_match = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_match.ToUnicode()
        
        self.SetLabelText( label )
        
    
    def GetValue( self ):
        
        return self._string_match
        
    
    def SetValue( self, string_match ):
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
class EditCompoundFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#compound_formula' ) )
        
        menu_items.append( ( 'normal', 'open the compound formula help', 'Open the help page for compound formulae in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._formulae = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._formulae.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_formula = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_formula = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_formula_up = ClientGUICommon.BetterButton( edit_panel, u'\u2191', self.MoveUp )
        
        self._delete_formula = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_formula_down = ClientGUICommon.BetterButton( edit_panel, u'\u2193', self.MoveDown )
        
        self._sub_phrase = wx.TextCtrl( edit_panel )
        
        ( formulae, sub_phrase, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for formula in formulae:
            
            pretty_formula = formula.ToPrettyString()
            
            self._formulae.Append( pretty_formula, formula )
            
        
        self._sub_phrase.SetValue( sub_phrase )
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_formula_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_formula, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_formula_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        formulae_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        formulae_hbox.Add( self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        formulae_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_formula, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_formula, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'substitution phrase:', self._sub_phrase ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        existing_formula = ClientParsing.ParseFormulaHTML()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditFormulaPanel( dlg, existing_formula, self._test_panel.GetTestContext )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_formula = panel.GetValue()
                
                pretty_formula = new_formula.ToPrettyString()
                
                self._formulae.Append( pretty_formula, new_formula )
                
            
        
    
    def Delete( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if self._formulae.GetCount() == 1:
                
                wx.MessageBox( 'A compound formula needs at least one sub-formula!' )
                
            else:
                
                self._formulae.Delete( selection )
                
            
        
    
    def Edit( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            old_formula = self._formulae.GetClientData( selection )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit formula', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditFormulaPanel( dlg, old_formula, self._test_panel.GetTestContext )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    new_formula = panel.GetValue()
                    
                    pretty_formula = new_formula.ToPrettyString()
                    
                    self._formulae.SetString( selection, pretty_formula )
                    self._formulae.SetClientData( selection, new_formula )
                    
                
            
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        formulae = [ self._formulae.GetClientData( i ) for i in range( self._formulae.GetCount() ) ]
        
        sub_phrase = self._sub_phrase.GetValue()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaCompound( formulae, sub_phrase, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._formulae.GetCount():
            
            pretty_rule = self._formulae.GetString( selection )
            rule = self._formulae.GetClientData( selection )
            
            self._formulae.Delete( selection )
            
            self._formulae.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._formulae.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._formulae.GetString( selection )
            rule = self._formulae.GetClientData( selection )
            
            self._formulae.Delete( selection )
            
            self._formulae.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditContextVariableFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#context_variable_formula' ) )
        
        menu_items.append( ( 'normal', 'open the context variable formula help', 'Open the help page for context variable formulae in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._variable_name = wx.TextCtrl( edit_panel )
        
        ( variable_name, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        self._variable_name.SetValue( variable_name )
        
        #
        
        rows = []
        
        rows.append( ( 'variable name:', self._variable_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        variable_name = self._variable_name.GetValue()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaContextVariable( variable_name, string_match, string_converter )
        
        return formula
        
    
class EditFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context_callable ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._current_formula = formula
        self._test_context_callable = test_context_callable
        
        #
        
        my_panel = ClientGUICommon.StaticBox( self, 'formula' )
        
        self._formula_description = ClientGUICommon.SaneMultilineTextCtrl( my_panel )
        
        ( width, height ) = ClientGUICommon.ConvertTextToPixels( self._formula_description, ( 90, 8 ) )
        
        self._formula_description.SetInitialSize( ( width, height ) )
        
        self._formula_description.Disable()
        
        self._edit_formula = ClientGUICommon.BetterButton( my_panel, 'edit formula', self._EditFormula )
        
        self._change_formula_type = ClientGUICommon.BetterButton( my_panel, 'change formula type', self._ChangeFormulaType )
        
        #
        
        self._UpdateControls()
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._edit_formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.Add( self._change_formula_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        my_panel.Add( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        my_panel.Add( button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ChangeFormulaType( self ):
        
        if self._current_formula.ParsesSeparatedContent():
            
            new_html = ClientParsing.ParseFormulaHTML( content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
            new_json = ClientParsing.ParseFormulaJSON( content_to_fetch = ClientParsing.JSON_CONTENT_JSON )
            
        else:
            
            new_html = ClientParsing.ParseFormulaHTML()
            new_json = ClientParsing.ParseFormulaJSON()
            
        
        new_compound = ClientParsing.ParseFormulaCompound()
        new_context_variable = ClientParsing.ParseFormulaContextVariable()
        
        if isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            order = ( 'json', 'compound', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            order = ( 'html', 'compound', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaCompound ):
            
            order = ( 'html', 'json', 'context_variable' )
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            order = ( 'html', 'json', 'compound', 'context_variable' )
            
        
        choice_tuples = []
        
        for formula_type in order:
            
            if formula_type == 'html':
                
                choice_tuples.append( ( 'change to a new HTML formula', new_html ) )
                
            elif formula_type == 'json':
                
                choice_tuples.append( ( 'change to a new JSON formula', new_json ) )
                
            elif formula_type == 'compound':
                
                choice_tuples.append( ( 'change to a new COMPOUND formula', new_compound ) )
                
            elif formula_type == 'context_variable':
                
                choice_tuples.append( ( 'change to a new CONTEXT VARIABLE formula', new_context_variable ) )
                
            
        
        with ClientGUIDialogs.DialogSelectFromList( self, 'select formula type', choice_tuples ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = dlg.GetChoice()
                
            
        
        self._UpdateControls()
        
    
    def _EditFormula( self ):
        
        if isinstance( self._current_formula, ClientParsing.ParseFormulaHTML ):
            
            panel_class = EditHTMLFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaJSON ):
            
            panel_class = EditJSONFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaCompound ):
            
            panel_class = EditCompoundFormulaPanel
            
        elif isinstance( self._current_formula, ClientParsing.ParseFormulaContextVariable ):
            
            panel_class = EditContextVariableFormulaPanel
            
        
        test_context = self._test_context_callable()
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = panel_class( dlg, self._current_formula, test_context )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = panel.GetValue()
                
                self._UpdateControls()
                
            
        
    
    def _UpdateControls( self ):
        
        if self._current_formula is None:
            
            self._formula_description.SetValue( '' )
            
            self._edit_formula.Disable()
            self._change_formula_type.Disable()
            
        else:
            
            self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
            
            self._edit_formula.Enable()
            self._change_formula_type.Enable()
            
        
    
    def GetValue( self ):
        
        return self._current_formula
        
    
class EditHTMLTagRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( rule_type, tag_name, tag_attributes, tag_index, tag_depth, should_test_tag_string, tag_string_string_match ) = tag_rule.ToTuple()
        
        if tag_name is None:
            
            tag_name = ''
            
        
        if tag_attributes is None:
            
            tag_attributes = {}
            
        
        if tag_depth is None:
            
            tag_depth = 1
            
        
        self._current_description = ClientGUICommon.BetterStaticText( self )
        
        self._rule_type = ClientGUICommon.BetterChoice( self )
        
        self._rule_type.Append( 'search descendents', ClientParsing.HTML_RULE_TYPE_DESCENDING )
        self._rule_type.Append( 'walk back up ancestors', ClientParsing.HTML_RULE_TYPE_ASCENDING )
        
        self._tag_name = wx.TextCtrl( self )
        
        self._tag_attributes = ClientGUIControls.EditStringToStringDictControl( self, tag_attributes )
        
        self._tag_index = ClientGUICommon.NoneableSpinCtrl( self, 'index to fetch', none_phrase = 'get all', min = 0, max = 255 )
        
        self._tag_depth = wx.SpinCtrl( self, min = 1, max = 255 )
        
        self._should_test_tag_string = wx.CheckBox( self )
        
        self._tag_string_string_match = StringMatchButton( self, tag_string_string_match )
        
        #
        
        self._rule_type.SelectClientData( rule_type )
        self._tag_name.SetValue( tag_name )
        self._tag_index.SetValue( tag_index )
        self._tag_depth.SetValue( tag_depth )
        self._should_test_tag_string.SetValue( should_test_tag_string )
        
        self._UpdateTypeControls()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
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
        
        vbox.Add( self._current_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._tag_attributes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( gridbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self._UpdateShouldTest()
        
        #
        
        self._rule_type.Bind( wx.EVT_CHOICE, self.EventTypeChanged )
        self._tag_name.Bind( wx.EVT_TEXT, self.EventVariableChanged )
        self._tag_attributes.Bind( ClientGUIListCtrl.EVT_LIST_CTRL, self.EventVariableChanged)
        self._tag_index.Bind( wx.EVT_SPINCTRL, self.EventVariableChanged )
        self._tag_depth.Bind( wx.EVT_SPINCTRL, self.EventVariableChanged )
        
        self._should_test_tag_string.Bind( wx.EVT_CHECKBOX, self.EventShouldTestChanged )
        
    
    def _UpdateShouldTest( self ):
        
        if self._should_test_tag_string.GetValue():
            
            self._tag_string_string_match.Enable()
            
        else:
            
            self._tag_string_string_match.Disable()
            
        
    
    def _UpdateTypeControls( self ):
        
        rule_type = self._rule_type.GetChoice()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            self._tag_attributes.Enable()
            self._tag_index.Enable()
            
            self._tag_depth.Disable()
            
        else:
            
            self._tag_attributes.Disable()
            self._tag_index.Disable()
            
            self._tag_depth.Enable()
            
        
        self._UpdateDescription()
        
    
    def _UpdateDescription( self ):
        
        tag_rule = self.GetValue()
        
        label = tag_rule.ToString()
        
        self._current_description.SetLabelText( label )
        
    
    def EventShouldTestChanged( self, event ):
        
        self._UpdateShouldTest()
        
    
    def EventTypeChanged( self, event ):
        
        self._UpdateTypeControls()
        
        event.Skip()
        
    
    def EventVariableChanged( self, event ):
        
        self._UpdateDescription()
        
        event.Skip()
        
    
    def GetValue( self ):
        
        rule_type = self._rule_type.GetChoice()
        
        tag_name = self._tag_name.GetValue()
        
        if tag_name == '':
            
            tag_name = None
            
        
        should_test_tag_string = self._should_test_tag_string.GetValue()
        tag_string_string_match = self._tag_string_string_match.GetValue()
        
        if rule_type == ClientParsing.HTML_RULE_TYPE_DESCENDING:
            
            tag_attributes = self._tag_attributes.GetValue()
            tag_index = self._tag_index.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        elif rule_type == ClientParsing.HTML_RULE_TYPE_ASCENDING:
            
            tag_depth = self._tag_depth.GetValue()
            
            tag_rule = ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_depth = tag_depth, should_test_tag_string = should_test_tag_string, tag_string_string_match = tag_string_string_match )
            
        
        return tag_rule
        
    
class EditHTMLFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#html_formula' ) )
        
        menu_items.append( ( 'normal', 'open the html formula help', 'Open the help page for html formulae in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._tag_rules = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._tag_rules.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, u'\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, u'\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.Append( 'attribute', ClientParsing.HTML_CONTENT_ATTRIBUTE )
        self._content_to_fetch.Append( 'string', ClientParsing.HTML_CONTENT_STRING )
        self._content_to_fetch.Append( 'html', ClientParsing.HTML_CONTENT_HTML )
        
        self._content_to_fetch.Bind( wx.EVT_CHOICE, self.EventContentChoice )
        
        self._attribute_to_fetch = wx.TextCtrl( edit_panel )
        
        ( tag_rules, content_to_fetch, attribute_to_fetch, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for rule in tag_rules:
            
            pretty_rule = rule.ToString()
            
            self._tag_rules.Append( pretty_rule, rule )
            
        
        self._content_to_fetch.SelectClientData( content_to_fetch )
        
        self._attribute_to_fetch.SetValue( attribute_to_fetch )
        
        self._UpdateControls()
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_rule_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_rule, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_rule_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        tag_rules_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        tag_rules_hbox.Add( self._tag_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        tag_rules_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_rule, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_rule, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        rows.append( ( 'attribute to fetch: ', self._attribute_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _UpdateControls( self ):
        
        if self._content_to_fetch.GetChoice() == ClientParsing.HTML_CONTENT_ATTRIBUTE:
            
            self._attribute_to_fetch.Enable()
            
        else:
            
            self._attribute_to_fetch.Disable()
            
        
    
    def Add( self ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = ClientParsing.ParseRuleHTML()
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = rule.ToString()
                
                self._tag_rules.Append( pretty_rule, rule )
                
            
        
    
    def Delete( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._tag_rules.Delete( selection )
            
        
    
    def Edit( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._tag_rules.GetClientData( selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = rule.ToString()
                    
                    self._tag_rules.SetString( selection, pretty_rule )
                    self._tag_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventContentChoice( self, event ):
        
        self._UpdateControls()
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        tags_rules = [ self._tag_rules.GetClientData( i ) for i in range( self._tag_rules.GetCount() ) ]
        
        content_to_fetch = self._content_to_fetch.GetChoice()
        
        attribute_to_fetch = self._attribute_to_fetch.GetValue()
        
        if content_to_fetch == ClientParsing.HTML_CONTENT_ATTRIBUTE and attribute_to_fetch == '':
            
            raise HydrusExceptions.VetoException( 'Please enter an attribute to fetch!' )
            
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaHTML( tags_rules, content_to_fetch, attribute_to_fetch, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._tag_rules.GetCount():
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditJSONParsingRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    DICT_ENTRY = 0
    ALL_LIST_ITEMS = 1
    INDEXED_LIST_ITEM = 2
    
    def __init__( self, parent, rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._type = ClientGUICommon.BetterChoice( self )
        
        self._type.Append( 'dictionary entry', self.DICT_ENTRY )
        self._type.Append( 'all dictionary/list items', self.ALL_LIST_ITEMS )
        self._type.Append( 'indexed list item', self.INDEXED_LIST_ITEM)
        
        self._key = wx.TextCtrl( self )
        
        self._index = wx.SpinCtrl( self, min = 0, max = 65535 )
        
        #
        
        if rule is None:
            
            self._type.SelectClientData( self.ALL_LIST_ITEMS )
            
        elif isinstance( rule, int ):
            
            self._type.SelectClientData( self.INDEXED_LIST_ITEM )
            
            self._index.SetValue( rule )
            
        else:
            
            self._type.SelectClientData( self.DICT_ENTRY )
            
            self._key.SetValue( rule )
            
        
        self._UpdateHideShow()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'dict entry: ', self._key ) )
        rows.append( ( 'list index: ', self._index ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox.Add( self._type, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._type.Bind( wx.EVT_CHOICE, self.EventChoice )
        
    
    def _UpdateHideShow( self ):
        
        self._key.Disable()
        self._index.Disable()
        
        choice = self._type.GetChoice()
        
        if choice == self.DICT_ENTRY:
            
            self._key.Enable()
            
        elif choice == self.INDEXED_LIST_ITEM:
            
            self._index.Enable()
            
        
    
    def EventChoice( self, event ):
        
        self._UpdateHideShow()
        
    
    def GetValue( self ):
        
        choice = self._type.GetChoice()
        
        if choice == self.DICT_ENTRY:
            
            rule = self._key.GetValue()
            
        elif choice == self.INDEXED_LIST_ITEM:
            
            rule = self._index.GetValue()
            
        else:
            
            rule = None
            
        
        return rule
        
    
class EditJSONFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_formulae.html#json_formula' ) )
        
        menu_items.append( ( 'normal', 'open the json formula help', 'Open the help page for json formulae in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._parse_rules = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._parse_rules.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, u'\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, u'\u2193', self.MoveDown )
        
        self._content_to_fetch = ClientGUICommon.BetterChoice( edit_panel )
        
        self._content_to_fetch.Append( 'string', ClientParsing.JSON_CONTENT_STRING )
        self._content_to_fetch.Append( 'json', ClientParsing.JSON_CONTENT_JSON )
        
        ( parse_rules, content_to_fetch, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        for rule in parse_rules:
            
            pretty_rule = ClientParsing.RenderJSONParseRule( rule )
            
            self._parse_rules.Append( pretty_rule, rule )
            
        
        self._content_to_fetch.SelectClientData( content_to_fetch )
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.Add( self._move_rule_up, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._delete_rule, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( self._move_rule_down, CC.FLAGS_VCENTER )
        udd_button_vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        parse_rules_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        parse_rules_hbox.Add( self._parse_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        parse_rules_hbox.Add( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.Add( self._add_rule, CC.FLAGS_VCENTER )
        ae_button_hbox.Add( self._edit_rule, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'content to fetch:', self._content_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( parse_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        dlg_title = 'edit parse rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            new_rule = 'post'
            
            panel = EditJSONParsingRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                
                self._parse_rules.Append( pretty_rule, rule )
                
            
        
    
    def Delete( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._parse_rules.Delete( selection )
            
        
    
    def Edit( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._parse_rules.GetClientData( selection )
            
            dlg_title = 'edit parse rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditJSONParsingRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = ClientParsing.RenderJSONParseRule( rule )
                    
                    self._parse_rules.SetString( selection, pretty_rule )
                    self._parse_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        parse_rules = [ self._parse_rules.GetClientData( i ) for i in range( self._parse_rules.GetCount() ) ]
        
        content_to_fetch = self._content_to_fetch.GetChoice()
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaJSON( parse_rules, content_to_fetch, string_match, string_converter )
        
        return formula
        
    
    def MoveDown( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._parse_rules.GetCount():
            
            pretty_rule = self._parse_rules.GetString( selection )
            rule = self._parse_rules.GetClientData( selection )
            
            self._parse_rules.Delete( selection )
            
            self._parse_rules.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def MoveUp( self ):
        
        selection = self._parse_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._parse_rules.GetString( selection )
            rule = self._parse_rules.GetClientData( selection )
            
            self._parse_rules.Delete( selection )
            
            self._parse_rules.Insert( pretty_rule, selection - 1, rule )
            
        
    
class EditContentParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, content_parser, test_context ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_content_parsers.html#content_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the content parsers help', 'Open the help page for content parsers in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        self._edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( self._edit_panel )
        
        self._content_panel = ClientGUICommon.StaticBox( self._edit_panel, 'content type' )
        
        self._content_type = ClientGUICommon.BetterChoice( self._content_panel )
        
        self._content_type.Append( 'urls', HC.CONTENT_TYPE_URLS )
        self._content_type.Append( 'tags', HC.CONTENT_TYPE_MAPPINGS )
        self._content_type.Append( 'file hash', HC.CONTENT_TYPE_HASH )
        self._content_type.Append( 'timestamp', HC.CONTENT_TYPE_TIMESTAMP )
        self._content_type.Append( 'watcher page title', HC.CONTENT_TYPE_TITLE )
        self._content_type.Append( 'veto', HC.CONTENT_TYPE_VETO )
        
        self._content_type.Bind( wx.EVT_CHOICE, self.EventContentTypeChange )
        
        self._urls_panel = wx.Panel( self._content_panel )
        
        self._url_type = ClientGUICommon.BetterChoice( self._urls_panel )
        
        self._url_type.Append( 'url to download/pursue (file/post url)', HC.URL_TYPE_DESIRED )
        self._url_type.Append( 'url to associate (source url)', HC.URL_TYPE_SOURCE )
        self._url_type.Append( 'next gallery page', HC.URL_TYPE_NEXT )
        
        self._file_priority = wx.SpinCtrl( self._urls_panel, min = 0, max = 100 )
        self._file_priority.SetValue( 50 )
        
        self._mappings_panel = wx.Panel( self._content_panel )
        
        self._namespace = wx.TextCtrl( self._mappings_panel )
        
        self._hash_panel = wx.Panel( self._content_panel )
        
        self._hash_type = ClientGUICommon.BetterChoice( self._hash_panel )
        
        for hash_type in ( 'md5', 'sha1', 'sha256', 'sha512' ):
            
            self._hash_type.Append( hash_type, hash_type )
            
        
        self._timestamp_panel = wx.Panel( self._content_panel )
        
        self._timestamp_type = ClientGUICommon.BetterChoice( self._timestamp_panel )
        
        self._timestamp_type.Append( 'source time', HC.TIMESTAMP_TYPE_SOURCE )
        
        self._title_panel = wx.Panel( self._content_panel )
        
        self._title_priority = wx.SpinCtrl( self._title_panel, min = 0, max = 100 )
        self._title_priority.SetValue( 50 )
        
        self._veto_panel = wx.Panel( self._content_panel )
        
        self._veto_if_matches_found = wx.CheckBox( self._veto_panel )
        self._string_match = EditStringMatchPanel( self._veto_panel )
        
        ( name, content_type, formula, additional_info ) = content_parser.ToTuple()
        
        self._formula = EditFormulaPanel( self._edit_panel, formula, self.GetTestContext )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
        
        #
        
        self._name.SetValue( name )
        
        self._content_type.SelectClientData( content_type )
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            ( url_type, priority ) = additional_info
            
            self._url_type.SelectClientData( url_type )
            self._file_priority.SetValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = additional_info
            
            self._namespace.SetValue( namespace )
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            hash_type = additional_info
            
            self._hash_type.SelectClientData( hash_type )
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = additional_info
            
            self._timestamp_type.SelectClientData( timestamp_type )
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = additional_info
            
            self._title_priority.SetValue( priority )
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            ( veto_if_matches_found, string_match ) = additional_info
            
            self._veto_if_matches_found.SetValue( veto_if_matches_found )
            self._string_match.SetValue( string_match )
            
        
        #
        
        rows = []
        
        rows.append( ( 'url type: ', self._url_type ) )
        rows.append( ( 'file url quality precedence (higher is better): ', self._file_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._urls_panel, rows )
        
        self._urls_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._mappings_panel, rows )
        
        self._mappings_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'hash type: ', self._hash_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._hash_panel, rows )
        
        self._hash_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'timestamp type: ', self._timestamp_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._timestamp_panel, rows )
        
        self._timestamp_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'title precedence (higher is better): ', self._title_priority ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._title_panel, rows )
        
        self._title_panel.SetSizer( gridbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'veto if match found (OFF means \'veto if match not found\'): ', self._veto_if_matches_found ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._veto_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._string_match, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._veto_panel.SetSizer( vbox )
        
        
        #
        
        rows = []
        
        rows.append( ( 'content type: ', self._content_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._content_panel, rows )
        
        self._content_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._urls_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._mappings_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._hash_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._timestamp_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._title_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.Add( self._veto_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._edit_panel, rows )
        
        self._edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._edit_panel.Add( self._content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._edit_panel.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.EventContentTypeChange( None )
        
    
    def EventContentTypeChange( self, event ):
        
        choice = self._content_type.GetChoice()
        
        self._urls_panel.Hide()
        self._mappings_panel.Hide()
        self._hash_panel.Hide()
        self._timestamp_panel.Hide()
        self._title_panel.Hide()
        self._veto_panel.Hide()
        
        if choice == HC.CONTENT_TYPE_URLS:
            
            self._urls_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_MAPPINGS:
            
            self._mappings_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_HASH:
            
            self._hash_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_TIMESTAMP:
            
            self._timestamp_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_TITLE:
            
            self._title_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_VETO:
            
            self._veto_panel.Show()
            
        
        self._content_panel.Layout()
        self._edit_panel.Layout()
        
    
    def GetTestContext( self ):
        
        return self._test_panel.GetTestContext()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        content_type = self._content_type.GetChoice()
        
        formula = self._formula.GetValue()
        
        if content_type == HC.CONTENT_TYPE_URLS:
            
            url_type = self._url_type.GetChoice()
            priority = self._file_priority.GetValue()
            
            additional_info = ( url_type, priority )
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = self._namespace.GetValue()
            
            additional_info = namespace
            
        elif content_type == HC.CONTENT_TYPE_HASH:
            
            hash_type = self._hash_type.GetChoice()
            
            additional_info = hash_type
            
        elif content_type == HC.CONTENT_TYPE_TIMESTAMP:
            
            timestamp_type = self._timestamp_type.GetChoice()
            
            additional_info = timestamp_type
            
        elif content_type == HC.CONTENT_TYPE_TITLE:
            
            priority = self._title_priority.GetValue()
            
            additional_info = priority
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            veto_if_matches_found = self._veto_if_matches_found.GetValue()
            string_match = self._string_match.GetValue()
            
            additional_info = ( veto_if_matches_found, string_match )
            
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = content_type, formula = formula, additional_info = additional_info )
        
        return content_parser
        
    
class EditContentParsersPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, test_context_callable ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'content parsers' )
        
        self._test_context_callable = test_context_callable
        
        content_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'produces', 40 ) ]
        
        self._content_parsers = ClientGUIListCtrl.BetterListCtrl( content_parsers_panel, 'content_parsers', 10, 24, columns, self._ConvertContentParserToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        content_parsers_panel.SetListCtrl( self._content_parsers )
        
        content_parsers_panel.AddButton( 'add', self._Add )
        content_parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        content_parsers_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        content_parsers_panel.AddSeparator()
        content_parsers_panel.AddImportExportButtons( ( ClientParsing.ContentParser, ), self._AddContentParser )
        
        #
        
        self.Add( content_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        dlg_title = 'edit content node'
        
        content_parser = ClientParsing.ContentParser( 'new content parser' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            test_context = self._test_context_callable()
            
            panel = EditContentParserPanel( dlg_edit, content_parser, test_context )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_content_parser = panel.GetValue()
                
                self._AddContentParser( new_content_parser )
                
            
        
    
    def _AddContentParser( self, content_parser ):
        
        HydrusSerialisable.SetNonDupeName( content_parser, self._GetExistingNames() )
        
        self._content_parsers.AddDatas( ( content_parser, ) )
        
        self._content_parsers.Sort()
        
    
    def _ConvertContentParserToListCtrlTuples( self, content_parser ):
        
        name = content_parser.GetName()
        
        produces = list( content_parser.GetParsableContent() )
        
        pretty_name = name
        
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces, include_veto = True )
        
        display_tuple = ( pretty_name, pretty_produces )
        sort_tuple = ( name, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._content_parsers.DeleteSelected()
                
            
        
    
    def _Edit( self ):
        
        content_parsers = self._content_parsers.GetData( only_selected = True )
        
        for content_parser in content_parsers:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit content parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                test_context = self._test_context_callable()
                
                panel = EditContentParserPanel( dlg, content_parser, test_context )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_content_parser = panel.GetValue()
                    
                    self._content_parsers.DeleteDatas( ( content_parser, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_content_parser, self._GetExistingNames() )
                    
                    self._content_parsers.AddDatas( ( edited_content_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._content_parsers.Sort()
        
    
    def _GetExistingNames( self ):
        
        names = { content_parser.GetName() for content_parser in self._content_parsers.GetData() }
        
        return names
        
    
    def GetData( self ):
        
        return self._content_parsers.GetData()
        
    
    def AddDatas( self, content_parsers ):
        
        self._content_parsers.AddDatas( content_parsers )
        
        self._content_parsers.Sort()
        
    
class EditNodes( wx.Panel ):
    
    def __init__( self, parent, nodes, referral_url_callable, example_data_callable ):
        
        wx.Panel.__init__( self, parent )
        
        self._referral_url_callable = referral_url_callable
        self._example_data_callable = example_data_callable
        
        self._nodes = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 200, [ ( 'name', 120 ), ( 'node type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'content node', 'A node that parses the given data for content.', self.AddContentNode ) )
        menu_items.append( ( 'normal', 'link node', 'A node that parses the given data for a link, which it then pursues.', self.AddLinkNode ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy', self.Copy )
        
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self.Paste )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        for node in nodes:
            
            ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( node )
            
            self._nodes.Append( display_tuple, sort_tuple, node )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.Add( self._nodes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertNodeToTuples( self, node ):
        
        ( name, node_type, produces ) = node.ToPrettyStrings()
        
        return ( ( name, node_type, produces ), ( name, node_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for node in self._nodes.GetObjects( only_selected = True ):
            
            to_export.append( node )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, ( ClientParsing.ContentParser, ClientParsing.ParseNodeContentLink ) ):
                
                node = obj
                
                ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( node )
                
                self._nodes.Append( display_tuple, sort_tuple, node )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
    def AddContentNode( self ):
        
        dlg_title = 'edit content node'
        
        empty_node = ClientParsing.ContentParser()
        
        panel_class = EditContentParserPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddLinkNode( self ):
        
        dlg_title = 'edit link node'
        
        empty_node = ClientParsing.ParseNodeContentLink()
        
        panel_class = EditParseNodeContentLinkPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddNode( self, dlg_title, empty_node, panel_class ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            referral_url = self._referral_url_callable()
            example_data = self._example_data_callable()
            
            if isinstance( empty_node, ClientParsing.ContentParser ):
                
                panel = panel_class( dlg_edit, empty_node, ( {}, example_data ) )
                
            else:
                
                panel = panel_class( dlg_edit, empty_node, referral_url, example_data )
                
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_node = panel.GetValue()
                
                ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( new_node )
                
                self._nodes.Append( display_tuple, sort_tuple, new_node )
                
            
        
    
    def Copy( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._nodes.RemoveAllSelected()
                
            
        
    
    def Duplicate( self ):
        
        nodes_to_dupe = self._nodes.GetObjects( only_selected = True )
        
        for node in nodes_to_dupe:
            
            dupe_node = node.Duplicate()
            
            ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( dupe_node )
            
            self._nodes.Append( display_tuple, sort_tuple, dupe_node )
            
        
    
    def Edit( self ):
        
        for i in self._nodes.GetAllSelected():
            
            node = self._nodes.GetObject( i )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit node', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                referral_url = self._referral_url_callable()
                example_data = self._example_data_callable()
                
                if isinstance( node, ClientParsing.ContentParser ):
                    
                    panel = EditContentParserPanel( dlg, node, ( {}, example_data ) )
                    
                elif isinstance( node, ClientParsing.ParseNodeContentLink ):
                    
                    panel = EditParseNodeContentLinkPanel( dlg, node, example_data = example_data )
                    
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_node = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( edited_node )
                    
                    self._nodes.UpdateRow( i, display_tuple, sort_tuple, edited_node )
                    
                
                
            
        
    
    def GetValue( self ):
        
        return self._nodes.GetObjects()
        
    
    def Paste( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
class EditParseNodeContentLinkPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, referral_url = None, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if referral_url is None:
            
            referral_url = 'test-url.com/test_query'
            
        
        self._referral_url = referral_url
        
        if example_data is None:
            
            example_data = ''
            
        
        self._my_example_url = None
        
        notebook = wx.Notebook( self )
        
        ( name, formula, children ) = node.ToTuple()
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        get_example_parsing_context = lambda: {}
        
        self._formula = EditFormulaPanel( edit_panel, formula, self.GetTestContext )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._example_data.SetValue( example_data )
        
        self._test_parse = wx.Button( test_panel, label = 'test parse' )
        self._test_parse.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        self._test_fetch_result = wx.Button( test_panel, label = 'try fetching the first result' )
        self._test_fetch_result.Bind( wx.EVT_BUTTON, self.EventTestFetchResult )
        self._test_fetch_result.Disable()
        
        self._my_example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This node looks for one or more urls in the data it is given, requests each in turn, and gives the results to its children for further parsing.

If your previous query result responds with links to where the actual content is, use this node to bridge the gap.

The formula should attempt to parse full or relative urls. If the url is relative (like href="/page/123"), it will be appended to the referral url given by this node's parent. It will then attempt to GET them all.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.SetWrapWidth( 400 )
        
        #
        
        self._name.SetValue( name )
        
        #
        
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_fetch_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._my_example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        
    
    def EventTestFetchResult( self, event ):
        
        # this should be published to a job key panel or something so user can see it and cancel if needed
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', self._my_example_url, referral_url = self._referral_url )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.CancelledException:
            
            self._my_example_data.SetValue( 'fetch cancelled' )
            
            return
            
        except HydrusExceptions.NetworkException as e:
            
            self._my_example_data.SetValue( 'fetch failed' )
            
            raise
            
        
        example_data = network_job.GetContent()
        
        try:
            
            self._example_data.SetValue( example_data )
            
        except UnicodeDecodeError:
            
            self._example_data.SetValue( 'The fetched data, which had length ' + HydrusData.ConvertIntToBytes( len( example_data ) ) + ', did not appear to be displayable text.' )
            
        
    
    def EventTestParse( self, event ):
        
        def wx_code( parsed_urls ):
            
            if not self:
                
                return
                
            
            if len( parsed_urls ) > 0:
                
                self._my_example_url = parsed_urls[0]
                self._test_fetch_result.Enable()
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( parsed_urls ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( parsed_urls )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        
        def do_it( node, data, referral_url ):
            
            try:
                
                stop_time = HydrusData.GetNow() + 30
                
                job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
                
                parsed_urls = node.ParseURLs( job_key, data, referral_url )
                
                wx.CallAfter( wx_code, parsed_urls )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                wx.CallAfter( wx.MessageBox, message )
                
            
        
        node = self.GetValue()
        data = self._example_data.GetValue()
        referral_url = self._referral_url
        
        HG.client_controller.CallToThread( do_it, node, data, referral_url )
        
    
    def GetExampleData( self ):
        
        return self._example_data.GetValue()
        
    
    def GetExampleURL( self ):
        
        if self._my_example_url is not None:
            
            return self._my_example_url
            
        else:
            
            return ''
            
        
    
    def GetTestContext( self ):
        
        return ( {}, self._example_data.GetValue() )
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        formula = self._formula.GetValue()
        
        children = self._children.GetValue()
        
        node = ClientParsing.ParseNodeContentLink( name = name, formula = formula, children = children )
        
        return node
        
    
class EditPageParserPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parser, formula = None, test_context = None ):
        
        self._original_parser = parser
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_parsers_page_parsers.html#page_parsers' ) )
        
        menu_items.append( ( 'normal', 'open the page parser help', 'Open the help page for page parsers in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
        
        #
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        edit_notebook = wx.Notebook( edit_panel )
        
        #
        
        main_panel = wx.Panel( edit_notebook )
        
        main_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( main_panel )
        
        #
        
        conversion_panel = ClientGUICommon.StaticBox( main_panel, 'pre-parsing conversion' )
        
        string_converter = parser.GetStringConverter()
        
        self._string_converter = StringConverterButton( conversion_panel, string_converter )
        
        #
        
        example_urls_panel = ClientGUICommon.StaticBox( main_panel, 'example urls' )
        
        self._example_urls = ClientGUIListBoxes.AddEditDeleteListBox( example_urls_panel, 6, HydrusData.ToUnicode, self._AddExampleURL, self._EditExampleURL )
        
        #
        
        formula_panel = wx.Panel( edit_notebook )
        
        self._formula = EditFormulaPanel( formula_panel, formula, self.GetTestContext )
        
        #
        
        sub_page_parsers_notebook_panel = wx.Panel( edit_notebook )
        
        sub_page_parsers_notebook_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        #
        
        sub_page_parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( sub_page_parsers_notebook_panel )
        
        columns = [ ( 'name', 24 ), ( '\'post\' separation formula', 24 ), ( 'produces', -1 ) ]
        
        self._sub_page_parsers = ClientGUIListCtrl.BetterListCtrl( sub_page_parsers_panel, 'sub_page_parsers', 4, 36, columns, self._ConvertSubPageParserToListCtrlTuple, delete_key_callback = self._DeleteSubPageParser, activation_callback = self._EditSubPageParser )
        
        sub_page_parsers_panel.SetListCtrl( self._sub_page_parsers )
        
        sub_page_parsers_panel.AddButton( 'add', self._AddSubPageParser )
        sub_page_parsers_panel.AddButton( 'edit', self._EditSubPageParser, enabled_only_on_selection = True )
        sub_page_parsers_panel.AddButton( 'delete', self._DeleteSubPageParser, enabled_only_on_selection = True )
        
        #
        
        
        content_parsers_panel = wx.Panel( edit_notebook )
        
        content_parsers_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        #
        
        self._content_parsers = EditContentParsersPanel( content_parsers_panel, self.GetTestContext )
        
        #
        
        test_panel = ClientGUICommon.StaticBox( self, 'test' )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        test_url_fetch_panel = ClientGUICommon.StaticBox( test_panel, 'fetch test data from url' )
        
        self._test_url = wx.TextCtrl( test_url_fetch_panel )
        self._test_referral_url = wx.TextCtrl( test_url_fetch_panel )
        self._fetch_example_data = ClientGUICommon.BetterButton( test_url_fetch_panel, 'fetch test data from url', self._FetchExampleData )
        self._test_network_job_control = ClientGUIControls.NetworkJobControl( test_url_fetch_panel )
        
        if test_context is None:
            
            example_parsing_context = parser.GetExampleParsingContext()
            example_data = ''
            
            test_context = ( example_parsing_context, example_data )
            
        
        if formula is None:
            
            self._test_panel = TestPanel( test_panel, self.GetValue, test_context = test_context )
            
        else:
            
            self._test_panel = TestPanelSubsidiary( test_panel, self.GetValue, self.GetFormula, test_context = test_context )
            
        
        #
        
        name = parser.GetName()
        
        ( sub_page_parsers, content_parsers ) = parser.GetContentParsers()
        
        example_urls = parser.GetExampleURLs()
        
        if len( example_urls ) > 0:
            
            self._test_url.SetValue( example_urls[0] )
            
        
        self._name.SetValue( name )
        
        self._sub_page_parsers.AddDatas( sub_page_parsers )
        
        self._sub_page_parsers.Sort()
        
        self._content_parsers.AddDatas( content_parsers )
        
        self._example_urls.AddDatas( example_urls )
        
        #
        
        st = ClientGUICommon.BetterStaticText( conversion_panel, 'If the data this parser gets is wrapped in some quote marks or is otherwise encoded,\nyou can convert it to neat HTML/JSON first with this.' )
        
        conversion_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        conversion_panel.Add( self._string_converter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        example_urls_panel.Add( self._example_urls, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( main_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( conversion_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( example_urls_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        main_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        formula_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( sub_page_parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sub_page_parsers_notebook_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._content_parsers, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        content_parsers_panel.SetSizer( vbox )
        
        #
        
        rows = []
        
        rows.append( ( 'url: ', self._test_url ) )
        rows.append( ( 'referral url (optional): ', self._test_referral_url ) )
        
        gridbox = ClientGUICommon.WrapInGrid( test_url_fetch_panel, rows )
        
        test_url_fetch_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_url_fetch_panel.Add( self._fetch_example_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_url_fetch_panel.Add( self._test_network_job_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        test_panel.Add( test_url_fetch_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        test_panel.Add( self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if formula is not None:
            
            test_url_fetch_panel.Hide()
            
        
        #
        
        if formula is None:
            
            formula_panel.Hide()
            
        else:
            
            example_urls_panel.Hide()
            edit_notebook.AddPage( formula_panel, 'separation formula', select = False )
            
        
        edit_notebook.AddPage( main_panel, 'main', select = True )
        edit_notebook.AddPage( sub_page_parsers_notebook_panel, 'subsidiary page parsers', select = False )
        edit_notebook.AddPage( content_parsers_panel, 'content parsers', select = False )
        
        edit_panel.Add( edit_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _AddExampleURL( self ):
        
        message = 'Enter example URL.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                return ( True, dlg.GetValue() )
                
            else:
                
                return ( False, '' )
                
            
        
    
    def _AddSubPageParser( self ):
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'div', tag_attributes = { 'class' : 'thumb' } ) ], content_to_fetch = ClientParsing.HTML_CONTENT_HTML )
        page_parser = ClientParsing.PageParser( 'new sub page parser' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_context = self._test_panel.GetTestContext() )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_page_parser = panel.GetValue()
                
                new_formula = panel.GetFormula()
                
                new_sub_page_parser = ( new_formula, new_page_parser )
                
                self._sub_page_parsers.AddDatas( ( new_sub_page_parser, ) )
                
                self._sub_page_parsers.Sort()
                
            
        
    
    def _ConvertSubPageParserToListCtrlTuple( self, sub_page_parser ):
        
        ( formula, page_parser ) = sub_page_parser
        
        name = page_parser.GetName()
        
        produces = page_parser.GetParsableContent()
        
        produces = list( produces )
        
        produces.sort()
        
        pretty_name = name
        pretty_formula = formula.ToPrettyString()
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces )
        
        display_tuple = ( pretty_name, pretty_formula, pretty_produces )
        sort_tuple = ( name, pretty_formula, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteSubPageParser( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._sub_page_parsers.DeleteSelected()
                
            
        
    
    def _EditExampleURL( self, example_url ):
        
        message = 'Enter example URL.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, default = example_url ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                return ( True, dlg.GetValue() )
                
            else:
                
                return ( False, '' )
                
            
        
    
    def _EditSubPageParser( self ):
        
        selected_data = self._sub_page_parsers.GetData( only_selected = True )
        
        for sub_page_parser in selected_data:
            
            ( formula, page_parser ) = sub_page_parser
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit sub page parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, page_parser, formula = formula, test_context = self._test_panel.GetTestContext() )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    self._sub_page_parsers.DeleteDatas( ( sub_page_parser, ) )
                    
                    new_page_parser = panel.GetValue()
                    
                    new_formula = panel.GetFormula()
                    
                    new_sub_page_parser = ( new_formula, new_page_parser )
                    
                    self._sub_page_parsers.AddDatas( ( new_sub_page_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._sub_page_parsers.Sort()
        
    
    def _FetchExampleData( self ):
        
        def wait_and_do_it( network_job ):
            
            def wx_tidy_up( example_data ):
                
                if not self:
                    
                    return
                    
                
                self._test_panel.SetExampleData( example_data )
                
                self._test_network_job_control.ClearNetworkJob()
                
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContent()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + os.linesep * 2 + HydrusData.ToUnicode( e )
                
                HydrusData.ShowException( e )
                
            
            wx.CallAfter( wx_tidy_up, example_data )
            
        
        url = self._test_url.GetValue()
        referral_url = self._test_referral_url.GetValue()
        
        if referral_url == '':
            
            referral_url = None
            
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', url, referral_url = referral_url )
        
        self._test_network_job_control.SetNetworkJob( network_job )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        HG.client_controller.CallToThread( wait_and_do_it, network_job )
        
    
    def GetTestContext( self ):
        
        return self._test_panel.GetTestContext()
        
    
    def GetFormula( self ):
        
        return self._formula.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        parser_key = self._original_parser.GetParserKey()
        
        string_converter = self._string_converter.GetValue()
        
        sub_page_parsers = self._sub_page_parsers.GetData()
        
        content_parsers = self._content_parsers.GetData()
        
        example_urls = self._example_urls.GetData()
        
        example_parsing_context = self._test_panel.GetExampleParsingContext()
        
        parser = ClientParsing.PageParser( name, parser_key = parser_key, string_converter = string_converter, sub_page_parsers = sub_page_parsers, content_parsers = content_parsers, example_urls = example_urls, example_parsing_context = example_parsing_context )
        
        return parser
        
    
class EditParsersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, parsers ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        parsers_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'example urls', 40 ), ( 'produces', 40 ) ]
        
        self._parsers = ClientGUIListCtrl.BetterListCtrl( parsers_panel, 'parsers', 20, 24, columns, self._ConvertParserToListCtrlTuple, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        parsers_panel.SetListCtrl( self._parsers )
        
        parsers_panel.AddButton( 'add', self._Add )
        parsers_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        parsers_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        parsers_panel.AddSeparator()
        parsers_panel.AddImportExportButtons( ( ClientParsing.PageParser, ), self._AddParser )
        parsers_panel.AddSeparator()
        parsers_panel.AddDefaultsButton( ClientDefaults.GetDefaultParsers, self._AddParser )
        
        #
        
        self._parsers.AddDatas( parsers )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( parsers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        new_parser = ClientParsing.PageParser( 'new page parser' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = EditPageParserPanel( dlg_edit, new_parser )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_parser = panel.GetValue()
                
                self._AddParser( new_parser )
                
                self._parsers.Sort()
                
            
        
    
    def _AddParser( self, parser ):
        
        HydrusSerialisable.SetNonDupeName( parser, self._GetExistingNames() )
        
        parser.RegenerateParserKey()
        
        self._parsers.AddDatas( ( parser, ) )
        
    
    def _ConvertParserToListCtrlTuple( self, parser ):
        
        name = parser.GetName()
        
        example_urls = list( parser.GetExampleURLs() )
        example_urls.sort()
        
        produces = list( parser.GetParsableContent() )
        
        produces.sort()
        
        pretty_name = name
        pretty_example_urls = ', '.join( example_urls )
        
        pretty_produces = ClientParsing.ConvertParsableContentToPrettyString( produces )
        
        display_tuple = ( pretty_name, pretty_example_urls, pretty_produces )
        sort_tuple = ( name, example_urls, produces )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._parsers.DeleteSelected()
                
            
        
    
    def _Edit( self ):
        
        parsers = self._parsers.GetData( only_selected = True )
        
        for parser in parsers:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit parser', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = EditPageParserPanel( dlg, parser )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_parser = panel.GetValue()
                    
                    self._parsers.DeleteDatas( ( parser, ) )
                    
                    HydrusSerialisable.SetNonDupeName( edited_parser, self._GetExistingNames() )
                    
                    self._parsers.AddDatas( ( edited_parser, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._parsers.Sort()
        
    
    def _GetExistingNames( self ):
        
        names = { parser.GetName() for parser in self._parsers.GetData() }
        
        return names
        
    
    def GetValue( self ):
        
        return self._parsers.GetData()
        
    
class EditParsingScriptFileLookupPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, script ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( name, url, query_type, file_identifier_type, file_identifier_string_converter, file_identifier_arg_name, static_args, children ) = script.ToTuple()
        
        #
        
        notebook = wx.Notebook( self )
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        query_panel = ClientGUICommon.StaticBox( edit_panel, 'query' )
        
        self._url = wx.TextCtrl( query_panel )
        
        self._url.SetValue( url )
        
        self._query_type = ClientGUICommon.BetterChoice( query_panel )
        
        self._query_type.Append( 'GET', HC.GET )
        self._query_type.Append( 'POST', HC.POST )
        
        self._file_identifier_type = ClientGUICommon.BetterChoice( query_panel )
        
        for t in [ ClientParsing.FILE_IDENTIFIER_TYPE_FILE, ClientParsing.FILE_IDENTIFIER_TYPE_MD5, ClientParsing.FILE_IDENTIFIER_TYPE_SHA1, ClientParsing.FILE_IDENTIFIER_TYPE_SHA256, ClientParsing.FILE_IDENTIFIER_TYPE_SHA512, ClientParsing.FILE_IDENTIFIER_TYPE_USER_INPUT ]:
            
            self._file_identifier_type.Append( ClientParsing.file_identifier_string_lookup[ t ], t )
            
        
        self._file_identifier_string_converter = StringConverterButton( query_panel, file_identifier_string_converter )
        
        self._file_identifier_arg_name = wx.TextCtrl( query_panel )
        
        static_args_panel = ClientGUICommon.StaticBox( query_panel, 'static arguments' )
        
        self._static_args = ClientGUIControls.EditStringToStringDictControl( static_args_panel, static_args )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._test_script_management = ScriptManagementControl( test_panel )
        
        self._test_arg = wx.TextCtrl( test_panel )
        
        self._test_arg.SetValue( 'enter example file path, hex hash, or raw user input here' )
        
        self._fetch_data = wx.Button( test_panel, label = 'fetch response' )
        self._fetch_data.Bind( wx.EVT_BUTTON, self.EventFetchData )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._test_parsing = wx.Button( test_panel, label = 'test parse (note if you have \'link\' nodes, they will make their requests)' )
        self._test_parsing.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This script looks up tags for a single file.

It will download the result of a query that might look something like this:

http://www.file-lookup.com/form.php?q=getsometags&md5=[md5-in-hex]

And pass that html to a number of 'parsing children' that will each look through it in turn and try to find tags.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.SetWrapWidth( 400 )
        
        #
        
        self._name.SetValue( name )
        
        self._query_type.SelectClientData( query_type )
        self._file_identifier_type.SelectClientData( file_identifier_type )
        self._file_identifier_arg_name.SetValue( file_identifier_arg_name )
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        rows = []
        
        rows.append( ( 'url', self._url ) )
        rows.append( ( 'query type: ', self._query_type ) )
        rows.append( ( 'file identifier type: ', self._file_identifier_type ) )
        rows.append( ( 'file identifier conversion (typically to hex): ', self._file_identifier_string_converter ) )
        rows.append( ( 'file identifier GET/POST argument name: ', self._file_identifier_arg_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( query_panel, rows )
        
        static_args_panel.Add( self._static_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        query_message = 'This query will be executed first.'
        
        query_panel.Add( wx.StaticText( query_panel, label = query_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        query_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        query_panel.Add( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        children_message = 'The data returned by the query will be passed to each of these children for content parsing.'
        
        children_panel.Add( wx.StaticText( children_panel, label = children_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'script name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._test_script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def EventFetchData( self, event ):
        
        script = self.GetValue()
        
        test_arg = self._test_arg.GetValue()
        
        file_identifier_type = self._file_identifier_type.GetChoice()
        
        if file_identifier_type == ClientParsing.FILE_IDENTIFIER_TYPE_FILE:
            
            if not os.path.exists( test_arg ):
                
                wx.MessageBox( 'That file does not exist!' )
                
                return
                
            
            file_identifier = test_arg
            
        elif file_identifier_type == ClientParsing.FILE_IDENTIFIER_TYPE_USER_INPUT:
            
            file_identifier = test_arg
            
        else:
            
            file_identifier = test_arg.decode( 'hex' )
            
        
        try:
            
            stop_time = HydrusData.GetNow() + 30
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            self._test_script_management.SetJobKey( job_key )
            
            example_data = script.FetchData( job_key, file_identifier )
            
            try:
                
                self._example_data.SetValue( example_data )
                
            except UnicodeDecodeError:
                
                self._example_data.SetValue( 'The fetched data, which had length ' + HydrusData.ConvertIntToBytes( len( example_data ) ) + ', did not appear to be displayable text.' )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not fetch data!'
            message += os.linesep * 2
            message += HydrusData.ToUnicode( e )
            
            wx.MessageBox( message )
            
        finally:
            
            job_key.Finish()
            
        
    
    def EventTestParse( self, event ):
        
        def wx_code( results ):
            
            if not self:
                
                return
                
            
            result_lines = [ '*** ' + HydrusData.ToHumanInt( len( results ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( ( ClientParsing.ConvertParseResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        
        def do_it( script, job_key, data ):
            
            try:
                
                results = script.Parse( job_key, data )
                
                wx.CallAfter( wx_code, results )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                wx.CallAfter( wx.MessageBox, message )
                
            finally:
                
                job_key.Finish()
                
            
        
        script = self.GetValue()
        
        stop_time = HydrusData.GetNow() + 30
        
        job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
        
        self._test_script_management.SetJobKey( job_key )
        
        data = self._example_data.GetValue()
        
        HG.client_controller.CallToThread( do_it, script, job_key, data )
        
    
    def GetExampleData( self ):
        
        return self._example_data.GetValue()
        
    
    def GetExampleURL( self ):
        
        return self._url.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        url = self._url.GetValue()
        query_type = self._query_type.GetChoice()
        file_identifier_type = self._file_identifier_type.GetChoice()
        file_identifier_string_converter = self._file_identifier_string_converter.GetValue()
        file_identifier_arg_name = self._file_identifier_arg_name.GetValue()
        static_args = self._static_args.GetValue()
        children = self._children.GetValue()
        
        script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children )
        
        return script
        
    
class EditStringConverterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_converter, example_string_override = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        transformations_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( '#', 3 ), ( 'transformation', 30 ), ( 'result', -1 ) ]
        
        self._transformations = ClientGUIListCtrl.BetterListCtrl( transformations_panel, 'string_converter_transformations', 7, 35, columns, self._ConvertTransformationToListCtrlTuple, delete_key_callback = self._DeleteTransformation, activation_callback = self._EditTransformation )
        
        transformations_panel.SetListCtrl( self._transformations )
        
        transformations_panel.AddButton( 'add', self._AddTransformation )
        transformations_panel.AddButton( 'edit', self._EditTransformation, enabled_only_on_selection = True )
        transformations_panel.AddButton( 'delete', self._DeleteTransformation, enabled_only_on_selection = True )
        
        transformations_panel.AddSeparator()
        
        transformations_panel.AddButton( 'move up', self._MoveUp, enabled_check_func = self._CanMoveUp )
        transformations_panel.AddButton( 'move down', self._MoveDown, enabled_check_func = self._CanMoveDown )
        
        self._example_string = wx.TextCtrl( self )
        
        #
        
        self._transformations.AddDatas( [ ( i + 1, transformation_type, data ) for ( i, ( transformation_type, data ) ) in enumerate( string_converter.transformations ) ] )
        
        if example_string_override is None:
            
            self._example_string.SetValue( string_converter.example_string )
            
        else:
            
            self._example_string.SetValue( example_string_override )
            
        
        self._transformations.UpdateDatas() # to refresh, now they are all in the list
        
        self._transformations.Sort( 0 )
        
        #
        
        rows = []
        
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( transformations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._example_string.Bind( wx.EVT_TEXT, self.EventUpdate )
        
    
    def _AddTransformation( self ):
        
        transformation_type = ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT
        data = ' extra text'
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = self._TransformationPanel( dlg, transformation_type, data )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                number = self._transformations.GetItemCount() + 1
                
                ( transformation_type, data ) = panel.GetValue()
                
                enumerated_transformation = ( number, transformation_type, data )
                
                self._transformations.AddDatas( ( enumerated_transformation, ) )
                
            
        
        self._transformations.UpdateDatas() # need to refresh string after the insertion, so the new row can be included in the parsing calcs
        
        self._transformations.Sort()
        
    
    def _CanMoveDown( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        if len( selected_data ) == 1:
            
            ( number, transformation_type, data ) = selected_data[0]
            
            if number < self._transformations.GetItemCount():
                
                return True
                
            
        
        return False
        
    
    def _CanMoveUp( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        if len( selected_data ) == 1:
            
            ( number, transformation_type, data ) = selected_data[0]
            
            if number > 1:
                
                return True
                
            
        
        return False
        
    
    def _ConvertTransformationToListCtrlTuple( self, transformation ):
        
        ( number, transformation_type, data ) = transformation
        
        pretty_number = HydrusData.ToHumanInt( number )
        pretty_transformation = ClientParsing.StringConverter.TransformationToUnicode( ( transformation_type, data ) )
        
        string_converter = self._GetValue()
        
        try:
            
            pretty_result = ClientParsing.MakeParsedTextPretty( string_converter.Convert( self._example_string.GetValue(), number ) )
            
        except HydrusExceptions.StringConvertException as e:
            
            pretty_result = str( e )
            
        
        display_tuple = ( pretty_number, pretty_transformation, pretty_result )
        sort_tuple = ( number, number, number )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteTransformation( self ):
        
        if len( self._transformations.GetData( only_selected = True ) ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Delete all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._transformations.DeleteSelected()
                    
                
            
        
        # now we need to shuffle up any missing numbers
        
        num_rows = self._transformations.GetItemCount()
        
        i = 1
        search_i = i
        
        while i <= num_rows:
            
            try:
                
                transformation = self._GetTransformation( search_i )
                
                if search_i != i:
                    
                    self._transformations.DeleteDatas( ( transformation, ) )
                    
                    ( search_i, transformation_type, data ) = transformation
                    
                    transformation = ( i, transformation_type, data )
                    
                    self._transformations.AddDatas( ( transformation, ) )
                    
                
                i += 1
                search_i = i
                
            except HydrusExceptions.DataMissing:
                
                search_i += 1
                
            
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _EditTransformation( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        for enumerated_transformation in selected_data:
            
            ( number, transformation_type, data ) = enumerated_transformation
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = self._TransformationPanel( dlg, transformation_type, data )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    self._transformations.DeleteDatas( ( enumerated_transformation, ) )
                    
                    ( transformation_type, data ) = panel.GetValue()
                    
                    enumerated_transformation = ( number, transformation_type, data )
                    
                    self._transformations.AddDatas( ( enumerated_transformation, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _GetTransformation( self, desired_number ):
        
        for transformation in self._transformations.GetData():
            
            ( number, transformation_type, data ) = transformation
            
            if number == desired_number:
                
                return transformation
                
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetValue( self ):
        
        enumerated_transformations = list( self._transformations.GetData() )
        
        enumerated_transformations.sort()
        
        transformations = [ ( transformation_type, data ) for ( number, transformation_type, data ) in enumerated_transformations ]
        
        example_string = self._example_string.GetValue()
        
        string_converter = ClientParsing.StringConverter( transformations, example_string )
        
        return string_converter
        
    
    def _MoveDown( self ):
        
        selected_transformation = self._transformations.GetData( only_selected = True )[0]
        
        ( number, transformation_type, data ) = selected_transformation
        
        swap_transformation = self._GetTransformation( number + 1 )
        
        self._SwapTransformations( selected_transformation, swap_transformation )
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _MoveUp( self ):
        
        selected_transformation = self._transformations.GetData( only_selected = True )[0]
        
        ( number, transformation_type, data ) = selected_transformation
        
        swap_transformation = self._GetTransformation( number - 1 )
        
        self._SwapTransformations( selected_transformation, swap_transformation )
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _SwapTransformations( self, one, two ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        one_selected = one in selected_data
        two_selected = two in selected_data
        
        self._transformations.DeleteDatas( ( one, two ) )
        
        ( number_1, transformation_type_1, data_1 ) = one
        ( number_2, transformation_type_2, data_2 ) = two
        
        one = ( number_2, transformation_type_1, data_1 )
        two = ( number_1, transformation_type_2, data_2 )
        
        self._transformations.AddDatas( ( one, two ) )
        
        if one_selected:
            
            self._transformations.SelectDatas( ( one, ) )
            
        
        if two_selected:
            
            self._transformations.SelectDatas( ( two, ) )
            
        
    
    def EventUpdate( self, event ):
        
        self._transformations.UpdateDatas()
        
    
    def GetValue( self ):
        
        string_converter = self._GetValue()
        
        try:
            
            string_converter.Convert( self._example_string.GetValue() )
            
        except HydrusExceptions.StringConvertException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that can be converted!' )
            
        
        return string_converter
        
    
    class _TransformationPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, transformation_type, data ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._transformation_type = ClientGUICommon.BetterChoice( self )
            
            for t_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_REVERSE, ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._transformation_type.Append( ClientParsing.transformation_type_str_lookup[ t_type ], t_type )
                
            
            self._data_text = wx.TextCtrl( self )
            self._data_number = wx.SpinCtrl( self, min = 0, max = 65535 )
            self._data_encoding = ClientGUICommon.BetterChoice( self )
            self._data_regex_pattern = wx.TextCtrl( self )
            self._data_regex_repl = wx.TextCtrl( self )
            self._data_date_link = ClientGUICommon.BetterHyperLink( self, 'link to date info', 'https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior' )
            self._data_timezone = ClientGUICommon.BetterChoice( self )
            self._data_timezone_offset = wx.SpinCtrl( self, min = -86400, max = 86400 )
            
            for e in ( 'hex', 'base64' ):
                
                self._data_encoding.Append( e, e )
                
            
            self._data_timezone.Append( 'GMT', HC.TIMEZONE_GMT )
            self._data_timezone.Append( 'Local', HC.TIMEZONE_LOCAL )
            self._data_timezone.Append( 'Offset', HC.TIMEZONE_OFFSET )
            
            #
            
            self._transformation_type.SelectClientData( transformation_type )
            
            self._UpdateDataControls()
            
            #
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_ENCODE ):
                
                self._data_encoding.SelectClientData( data )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                ( pattern, repl ) = data
                
                self._data_regex_pattern.SetValue( pattern )
                self._data_regex_repl.SetValue( repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                ( phrase, timezone_type, timezone_offset ) = data
                
                self._data_text.SetValue( phrase )
                self._data_timezone.SelectClientData( timezone_type )
                self._data_timezone_offset.SetValue( timezone_offset )
                
            elif data is not None:
                
                if isinstance( data, int ):
                    
                    self._data_number.SetValue( data )
                    
                else:
                    
                    self._data_text.SetValue( data )
                    
                
            
            #
            
            rows = []
            
            rows.append( ( 'string data: ', self._data_text ) )
            rows.append( ( 'number data: ', self._data_number ) )
            rows.append( ( 'encoding data: ', self._data_encoding ) )
            rows.append( ( 'regex pattern: ', self._data_regex_pattern ) )
            rows.append( ( 'regex replacement: ', self._data_regex_repl ) )
            rows.append( ( 'date info: ', self._data_date_link ) )
            rows.append( ( 'date timezone: ', self._data_timezone ) )
            rows.append( ( 'timezone offset: ', self._data_timezone_offset ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._transformation_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            #
            
            self._transformation_type.Bind( wx.EVT_CHOICE, self.EventChoice )
            self._data_timezone.Bind( wx.EVT_CHOICE, self.EventChoice )
            
        
        def _UpdateDataControls( self ):
            
            self._data_text.Disable()
            self._data_number.Disable()
            self._data_encoding.Disable()
            self._data_regex_pattern.Disable()
            self._data_regex_repl.Disable()
            self._data_timezone.Disable()
            self._data_timezone_offset.Disable()
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                self._data_encoding.Enable()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE ):
                
                self._data_text.Enable()
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                    
                    self._data_timezone.Enable()
                    
                    if self._data_timezone.GetChoice() == HC.TIMEZONE_OFFSET:
                        
                        self._data_timezone_offset.Enable()
                        
                    
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._data_number.Enable()
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION:
                    
                    self._data_number.SetMin( -65535 )
                    
                else:
                    
                    self._data_number.SetMin( 0 )
                    
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                self._data_regex_pattern.Enable()
                self._data_regex_repl.Enable()
                
            
        
        def EventChoice( self, event ):
            
            self._UpdateDataControls()
            
        
        def GetValue( self ):
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                data = self._data_encoding.GetChoice()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT ):
                
                data = self._data_text.GetValue()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                data = self._data_number.GetValue()
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                pattern = self._data_regex_pattern.GetValue()
                repl = self._data_regex_repl.GetValue()
                
                data = ( pattern, repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                phrase = self._data_text.GetValue()
                timezone_time = self._data_timezone.GetChoice()
                timezone_offset = self._data_timezone_offset.GetValue()
                
                data = ( phrase, timezone_time, timezone_offset )
                
            else:
                
                data = None
                
            
            return ( transformation_type, data )
            
        
    
class EditStringMatchPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_match = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if string_match is None:
            
            string_match = ClientParsing.StringMatch()
            
        
        self._match_type = ClientGUICommon.BetterChoice( self )
        
        self._match_type.Append( 'any characters', ClientParsing.STRING_MATCH_ANY )
        self._match_type.Append( 'fixed characters', ClientParsing.STRING_MATCH_FIXED )
        self._match_type.Append( 'character set', ClientParsing.STRING_MATCH_FLEXIBLE )
        self._match_type.Append( 'regex', ClientParsing.STRING_MATCH_REGEX )
        
        self._match_value_text_input = wx.TextCtrl( self )
        
        self._match_value_flexible_input = ClientGUICommon.BetterChoice( self )
        
        self._match_value_flexible_input.Append( 'alphabetic characters (a-zA-Z)', ClientParsing.ALPHA )
        self._match_value_flexible_input.Append( 'alphanumeric characters (a-zA-Z0-9)', ClientParsing.ALPHANUMERIC )
        self._match_value_flexible_input.Append( 'numeric characters (0-9)', ClientParsing.NUMERIC )
        
        self._min_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        self._max_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        
        self._example_string = wx.TextCtrl( self )
        
        self._example_string_matches = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self.SetValue( string_match )
        
        #
        
        rows = []
        
        rows.append( ( 'match type: ', self._match_type ) )
        rows.append( ( 'match text: ', self._match_value_text_input ) )
        rows.append( ( 'match value (character set): ', self._match_value_flexible_input ) )
        rows.append( ( 'minumum allowed number of characters: ', self._min_chars ) )
        rows.append( ( 'maximum allowed number of characters: ', self._max_chars ) )
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._example_string_matches, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._match_type.Bind( wx.EVT_CHOICE, self.EventUpdate )
        self._match_value_text_input.Bind( wx.EVT_TEXT, self.EventUpdate )
        self._match_value_flexible_input.Bind( wx.EVT_CHOICE, self.EventUpdate )
        self._min_chars.Bind( wx.EVT_SPINCTRL, self.EventUpdate )
        self._max_chars.Bind( wx.EVT_SPINCTRL, self.EventUpdate )
        self._example_string.Bind( wx.EVT_TEXT, self.EventUpdate )
        
    
    def _GetValue( self ):
        
        match_type = self._match_type.GetChoice()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            match_value = ''
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            match_value = self._match_value_flexible_input.GetChoice()
            
        else:
            
            match_value = self._match_value_text_input.GetValue()
            
        
        min_chars = self._min_chars.GetValue()
        max_chars = self._max_chars.GetValue()
        
        example_string = self._example_string.GetValue()
        
        string_match = ClientParsing.StringMatch( match_type = match_type, match_value = match_value, min_chars = min_chars, max_chars = max_chars, example_string = example_string )
        
        return string_match
        
    
    def _UpdateControls( self ):
        
        match_type = self._match_type.GetChoice()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            self._match_value_text_input.Disable()
            self._match_value_flexible_input.Disable()
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_text_input.Disable()
            self._match_value_flexible_input.Enable()
            
        else:
            
            self._match_value_text_input.Enable()
            self._match_value_flexible_input.Disable()
            
        
        if match_type == ClientParsing.STRING_MATCH_FIXED:
            
            self._min_chars.SetValue( None )
            self._max_chars.SetValue( None )
            
            self._min_chars.Disable()
            self._max_chars.Disable()
            
            self._example_string.SetValue( self._match_value_text_input.GetValue() )
            
            self._example_string_matches.SetLabelText( '' )
            
        else:
            
            self._min_chars.Enable()
            self._max_chars.Enable()
            
            string_match = self._GetValue()
            
            try:
                
                string_match.Test( self._example_string.GetValue() )
                
                self._example_string_matches.SetLabelText( 'Example matches ok!' )
                self._example_string_matches.SetForegroundColour( ( 0, 128, 0 ) )
                
            except HydrusExceptions.StringMatchException as e:
                
                reason = HydrusData.ToUnicode( e )
                
                self._example_string_matches.SetLabelText( 'Example does not match - ' + reason )
                self._example_string_matches.SetForegroundColour( ( 128, 0, 0 ) )
                
            
        
    
    def EventUpdate( self, event ):
        
        self._UpdateControls()
        
        event.Skip()
        
    
    def GetValue( self ):
        
        string_match = self._GetValue()
        
        try:
            
            string_match.Test( self._example_string.GetValue() )
            
        except HydrusExceptions.StringMatchException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that matches the given rules!' )
            
        
        return string_match
        
    
    def SetValue( self, string_match ):
        
        ( match_type, match_value, min_chars, max_chars, example_string ) = string_match.ToTuple()
        
        self._match_type.SelectClientData( match_type )
        
        if match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_flexible_input.SelectClientData( match_value )
            
        else:
            
            self._match_value_flexible_input.SelectClientData( ClientParsing.ALPHA )
            
            self._match_value_text_input.SetValue( match_value )
            
        
        self._min_chars.SetValue( min_chars )
        self._max_chars.SetValue( max_chars )
        
        self._example_string.SetValue( example_string )
        
        self._UpdateControls()
        
    
class ManageParsingScriptsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    SCRIPT_TYPES = []
    
    SCRIPT_TYPES.append( HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._scripts = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 200, [ ( 'name', 140 ), ( 'query type', 80 ), ( 'script type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'file lookup script', 'A script that fetches content for a known file.', self.AddFileLookupScript ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'to clipboard', 'Serialise the script and put it on your clipboard.', self.ExportToClipboard ) )
        menu_items.append( ( 'normal', 'to png', 'Serialise the script and encode it to an image file you can easily share with other hydrus users.', self.ExportToPng ) )
        
        self._export_button = ClientGUICommon.MenuButton( self, 'export', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'from clipboard', 'Load a script from text in your clipboard.', self.ImportFromClipboard ) )
        menu_items.append( ( 'normal', 'from png', 'Load a script from an encoded png.', self.ImportFromPng ) )
        
        self._import_button = ClientGUICommon.MenuButton( self, 'import', menu_items )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        scripts = []
        
        for script_type in self.SCRIPT_TYPES:
            
            scripts.extend( HG.client_controller.Read( 'serialisable_named', script_type ) )
            
        
        for script in scripts:
            
            ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( script )
            
            self._scripts.Append( display_tuple, sort_tuple, script )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._export_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._import_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.Add( self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertScriptToTuples( self, script ):
        
        ( name, query_type, script_type, produces ) = script.ToPrettyStrings()
        
        return ( ( name, query_type, script_type, produces ), ( name, query_type, script_type, produces ) )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for script in self._scripts.GetObjects( only_selected = True ):
            
            to_export.append( script )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, ClientParsing.ParseRootFileLookup ):
                
                script = obj
                
                self._scripts.SetNonDupeName( script )
                
                ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( script )
                
                self._scripts.Append( display_tuple, sort_tuple, script )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
    def AddFileLookupScript( self ):
        
        name = 'new script'
        url = ''
        query_type = HC.GET
        file_identifier_type = ClientParsing.FILE_IDENTIFIER_TYPE_MD5
        file_identifier_string_converter = ClientParsing.StringConverter( ( ( ClientParsing.STRING_TRANSFORMATION_ENCODE, 'hex' ), ), 'some hash bytes' )
        file_identifier_arg_name = 'md5'
        static_args = {}
        children = []
        
        dlg_title = 'edit file metadata lookup script'
        
        empty_script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
        
        panel_class = EditParsingScriptFileLookupPanel
        
        self.AddScript( dlg_title, empty_script, panel_class )
        
    
    def AddScript( self, dlg_title, empty_script, panel_class ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = panel_class( dlg_edit, empty_script )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_script = panel.GetValue()
                
                self._scripts.SetNonDupeName( new_script )
                
                ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( new_script )
                
                self._scripts.Append( display_tuple, sort_tuple, new_script )
                
            
        
    
    def CommitChanges( self ):
        
        scripts = self._scripts.GetObjects()
        
        HG.client_controller.Write( 'serialisables_overwrite', self.SCRIPT_TYPES, scripts )
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._scripts.RemoveAllSelected()
                
            
        
    
    def Duplicate( self ):
        
        scripts_to_dupe = self._scripts.GetObjects( only_selected = True )
        
        for script in scripts_to_dupe:
            
            dupe_script = script.Duplicate()
            
            self._scripts.SetNonDupeName( dupe_script )
            
            ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( dupe_script )
            
            self._scripts.Append( display_tuple, sort_tuple, dupe_script )
            
        
    
    def Edit( self ):
        
        for i in self._scripts.GetAllSelected():
            
            script = self._scripts.GetObject( i )
            
            if isinstance( script, ClientParsing.ParseRootFileLookup ):
                
                panel_class = EditParsingScriptFileLookupPanel
                
                dlg_title = 'edit file lookup script'
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
                
                original_name = script.GetName()
                
                panel = panel_class( dlg, script )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_script = panel.GetValue()
                    
                    if edited_script.GetName() != original_name:
                        
                        self._scripts.SetNonDupeName( edited_script )
                        
                    
                    ( display_tuple, sort_tuple ) = self._ConvertScriptToTuples( edited_script )
                    
                    self._scripts.UpdateRow( i, display_tuple, sort_tuple, edited_script )
                    
                
                
            
        
    
    def ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def ExportToPng( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PngExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
    
    def ImportFromClipboard( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
    def ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png with the encoded script', wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                try:
                    
                    payload = ClientSerialisable.LoadFromPng( path )
                    
                except Exception as e:
                    
                    wx.MessageBox( HydrusData.ToUnicode( e ) )
                    
                    return
                    
                
                try:
                    
                    obj = HydrusSerialisable.CreateFromNetworkString( payload )
                    
                    self._ImportObject( obj )
                    
                except:
                    
                    wx.MessageBox( 'I could not understand what was encoded in the png!' )
                    
                
            
        
    
class ScriptManagementControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._job_key = None
        
        self._lock = threading.Lock()
        
        self._recent_urls = []
        
        main_panel = ClientGUICommon.StaticBox( self, 'script control' )
        
        self._status = wx.StaticText( main_panel )
        self._gauge = ClientGUICommon.Gauge( main_panel )
        
        self._link_button = wx.BitmapButton( main_panel, bitmap = CC.GlobalBMPs.link )
        self._link_button.Bind( wx.EVT_BUTTON, self.EventLinkButton )
        self._link_button.SetToolTip( 'urls found by the script' )
        
        self._cancel_button = wx.BitmapButton( main_panel, bitmap = CC.GlobalBMPs.stop )
        self._cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelButton )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._link_button, CC.FLAGS_VCENTER )
        hbox.Add( self._cancel_button, CC.FLAGS_VCENTER )
        
        main_panel.Add( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( main_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        #
        
        self._Reset()
        
    
    def _Reset( self ):
        
        self._status.SetLabelText( '' )
        self._gauge.SetRange( 1 )
        self._gauge.SetValue( 0 )
        
        self._link_button.Disable()
        self._cancel_button.Disable()
        
    
    def _Update( self ):
        
        if self._job_key is None:
            
            self._Reset()
            
        else:
            
            if self._job_key.HasVariable( 'script_status' ):
                
                status = self._job_key.GetIfHasVariable( 'script_status' )
                
            else:
                
                status = ''
                
            
            if status != self._status.GetLabelText():
                
                self._status.SetLabelText( status )
                
            
            if self._job_key.HasVariable( 'script_gauge' ):
                
                ( value, range ) = self._job_key.GetIfHasVariable( 'script_gauge' )
                
            else:
                
                ( value, range ) = ( 0, 1 )
                
            
            self._gauge.SetRange( range )
            self._gauge.SetValue( value )
            
            urls = self._job_key.GetURLs()
            
            if len( urls ) == 0:
                
                if self._link_button.IsEnabled():
                    
                    self._link_button.Disable()
                    
                
            else:
                
                if not self._link_button.IsEnabled():
                    
                    self._link_button.Enable()
                    
                
            
            if self._job_key.IsDone():
                
                if self._cancel_button.IsEnabled():
                    
                    self._cancel_button.Disable()
                    
                
            else:
                
                if not self._cancel_button.IsEnabled():
                    
                    self._cancel_button.Enable()
                    
                
            
        
    
    def TIMERUIUpdate( self ):
        
        with self._lock:
            
            self._Update()
            
            if self._job_key is None:
                
                HG.client_controller.gui.UnregisterUIUpdateWindow( self )
                
            
        
    
    def EventCancelButton( self, event ):
        
        with self._lock:
            
            if self._job_key is not None:
                
                self._job_key.Cancel()
                
            
        
    
    def EventLinkButton( self, event ):
        
        with self._lock:
            
            if self._job_key is None:
                
                return
                
            
            urls = self._job_key.GetURLs()
            
        
        menu = wx.Menu()
        
        for url in urls:
            
            ClientGUIMenus.AppendMenuItem( self, menu, url, 'launch this url in your browser', ClientPaths.LaunchURLInWebBrowser, url )
            
        
        HG.client_controller.PopupMenu( self, menu )
        
        
    
    def SetJobKey( self, job_key ):
        
        with self._lock:
            
            self._job_key = job_key
            
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
class TestPanel( wx.Panel ):
    
    def __init__( self, parent, object_callable, test_context = None ):
        
        wx.Panel.__init__( self, parent )
        
        if test_context is None:
            
            test_context = ( {}, '' )
            
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._object_callable = object_callable
        
        self._example_parsing_context = ClientGUIControls.StringToStringDictButton( self, 'edit example parsing context' )
        
        self._example_data_description = ClientGUICommon.BetterStaticText( self )
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.copy, self._Copy )
        self._copy_button.SetToolTip( 'Copy the current example data to the clipboard.' )
        
        self._fetch_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.link, self._FetchFromURL )
        self._fetch_button.SetToolTip( 'Fetch data from a URL.' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.paste, self._Paste )
        self._paste_button.SetToolTip( 'Paste the current clipboard data into here.' )
        
        self._example_data_preview = ClientGUICommon.SaneMultilineTextCtrl( self, style = wx.TE_READONLY )
        
        size = ClientGUICommon.ConvertTextToPixels( self._example_data_preview, ( 80, 12 ) )
        
        self._example_data_preview.SetInitialSize( size )
        
        self._test_parse = ClientGUICommon.BetterButton( self, 'test parse', self.TestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( self )
        
        size = ClientGUICommon.ConvertTextToPixels( self._example_data_preview, ( 80, 12 ) )
        
        self._results.SetInitialSize( size )
        
        #
        
        ( example_parsing_context, example_data ) = test_context
        
        self._example_parsing_context.SetValue( example_parsing_context )
        
        self._SetExampleData( example_data )
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons_hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
        buttons_hbox.Add( self._fetch_button, CC.FLAGS_VCENTER )
        buttons_hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        desc_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        desc_hbox.Add( self._example_data_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        desc_hbox.Add( buttons_hbox, CC.FLAGS_BUTTON_SIZER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._example_parsing_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( desc_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._example_data_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Copy( self ):
        
        HG.client_controller.pub( 'clipboard', 'text', self._example_data )
        
    
    def _FetchFromURL( self ):
        
        def wx_code( example_data ):
            
            if not self:
                
                return
                
            
            self._SetExampleData( example_data )
            
        
        def do_it( url ):
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContent()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + os.linesep * 2 + HydrusData.ToUnicode( e )
                
                HydrusData.ShowException( e )
                
            
            wx.CallAfter( wx_code, example_data )
            
        
        message = 'Enter URL to fetch data for.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, default = 'enter url', allow_blank = False) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                url = dlg.GetValue()
                
                HG.client_controller.CallToThread( do_it, url )
                
            
        
    
    def _Paste( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        self._SetExampleData( raw_text )
        
    
    def _SetExampleData( self, example_data ):
        
        self._example_data = example_data
        
        if len( example_data ) > 0:
            
            parse_phrase = 'uncertain data type'
            
            # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
            if '<html' in example_data:
                
                parse_phrase = 'looks like HTML'
                
            
            # put this second, so if the JSON contains some HTML, it'll overwrite here. decent compromise
            try:
                
                json.loads( example_data )
                
                parse_phrase = 'looks like JSON'
                
            except:
                
                pass
                
            
            description = HydrusData.ConvertIntToBytes( len( example_data ) ) + ' total, ' + parse_phrase
            
            if len( example_data ) > 1024:
                
                preview = 'PREVIEW:' + os.linesep + HydrusData.ToUnicode( example_data[:1024] )
                
            else:
                
                preview = example_data
                
            
            self._test_parse.Enable()
            
        else:
            
            description = 'no example data set yet'
            preview = ''
            
            self._test_parse.Disable()
            
        
        self._example_data_description.SetLabelText( description )
        self._example_data_preview.SetValue( preview )
        
    
    def GetExampleParsingContext( self ):
        
        return self._example_parsing_context.GetValue()
        
    
    def GetTestContext( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ( example_parsing_context, self._example_data )
        
    
    def TestParse( self ):
        
        obj = self._object_callable()
        
        ( example_parsing_context, example_data ) = self.GetTestContext()
        
        try:
            
            results_text = obj.ParsePretty( example_parsing_context, example_data )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            etype = type( e )
            
            value = HydrusData.ToUnicode( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + HydrusData.ToUnicode( etype.__name__ ) + ': ' + HydrusData.ToUnicode( value ) + os.linesep + HydrusData.ToUnicode( trace )
            
            self._results.SetValue( message )
            
        
    
    def SetExampleData( self, example_data ):
        
        self._SetExampleData( example_data )
        
    
class TestPanelSubsidiary( TestPanel ):
    
    def __init__( self, parent, object_callable, formula_callable, test_context = None ):
        
        TestPanel.__init__( self, parent, object_callable, test_context = test_context )
        
        self._formula_callable = formula_callable
        
        self._formula_description = ClientGUICommon.BetterStaticText( self )
        
        self._refresh_formula_description_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.refresh, self._UpdateFormulaDescription )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._refresh_formula_description_button, CC.FLAGS_LONE_BUTTON )
        
        vbox = self.GetSizer()
        
        vbox.Insert( 2, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._UpdateFormulaDescription()
        
    
    def _UpdateFormulaDescription( self ):
        
        formula = self._formula_callable()
        
        if formula is None:
            
            description = 'No formula set'
            
        else:
            
            try:
                
                example_parsing_context = self._example_parsing_context.GetValue()
                
                posts = formula.Parse( example_parsing_context, self._example_data )
                
                description = HydrusData.ToHumanInt( len( posts ) ) + ' subsidiary posts parsed'
                
            except HydrusExceptions.ParseException as e:
                
                description = HydrusData.ToUnicode( e )
                
            
        
        self._formula_description.SetLabelText( description )
        
    
    def TestParse( self ):
        
        self._UpdateFormulaDescription()
        
        formula = self._formula_callable()
        
        page_parser = self._object_callable()
        
        try:
            
            example_parsing_context = self._example_parsing_context.GetValue()
            
            if formula is None:
                
                posts = [ self._example_data ]
                
            else:
                
                posts = formula.Parse( example_parsing_context, self._example_data )
                
            
            pretty_texts = []
            
            for post in posts:
                
                pretty_text = page_parser.ParsePretty( example_parsing_context, post )
                
                pretty_texts.append( pretty_text )
                
            
            separator = os.linesep * 2
            
            end_pretty_text = separator.join( pretty_texts )
            
            self._results.SetValue( end_pretty_text )
            
        except Exception as e:
            
            etype = type( e )
            
            value = HydrusData.ToUnicode( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + os.linesep + HydrusData.ToUnicode( etype.__name__ ) + ': ' + HydrusData.ToUnicode( value ) + os.linesep + HydrusData.ToUnicode( trace )
            
            self._results.SetValue( message )
            
        
    
    
