import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIControls
import ClientGUIListCtrl
import ClientGUIScrolledPanels
import ClientGUISerialisable
import ClientGUITopLevelWindows
import ClientNetworking
import ClientParsing
import ClientSerialisable
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import os
import threading
import time
import webbrowser
import wx

ID_TIMER_SCRIPT_UPDATE = wx.NewId()

class StringConverterButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_converter ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string converter' ) as dlg:
            
            panel = EditStringConverterPanel( dlg, self._string_converter )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        num_rules = len( self._string_converter.transformations )
        
        if num_rules == 0:
            
            label = 'no string transformations'
            
        else:
            
            label = HydrusData.ConvertIntToPrettyString( num_rules ) + ' string transformations'
            
        
        self.SetLabelText( label )
        
    
    def GetValue( self ):
        
        return self._string_converter
        
    
    def SetValue( self, string_converter ):
        
        self._string_converter = string_converter
        
        self._UpdateLabel()
        
    
class StringMatchButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_match ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string match', self._Edit )
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string match' ) as dlg:
            
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
        
    
class EditHTMLTagRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( name, attrs, index ) = rule
        
        self._name = wx.TextCtrl( self )
        
        self._attrs = ClientGUIControls.EditStringToStringDictControl( self, attrs )
        
        message = 'index to fetch'
        
        self._index = ClientGUICommon.NoneableSpinCtrl( self, message, none_phrase = 'get all', min = 0, max = 255 )
        
        #
        
        self._name.SetValue( name )
        
        self._index.SetValue( index )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'tag name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._attrs, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._index, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        attrs = self._attrs.GetValue()
        index = self._index.GetValue()
        
        return ( name, attrs, index )
        
    
class EditHTMLFormulaPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, formula, example_data ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        notebook = wx.Notebook( self )
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._tag_rules = wx.ListBox( edit_panel, style = wx.LB_SINGLE )
        self._tag_rules.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
        
        self._add_rule = ClientGUICommon.BetterButton( edit_panel, 'add', self.Add )
        
        self._edit_rule = ClientGUICommon.BetterButton( edit_panel, 'edit', self.Edit )
        
        self._move_rule_up = ClientGUICommon.BetterButton( edit_panel, u'\u2191', self.MoveUp )
        
        self._delete_rule = ClientGUICommon.BetterButton( edit_panel, 'X', self.Delete )
        
        self._move_rule_down = ClientGUICommon.BetterButton( edit_panel, u'\u2193', self.MoveDown )
        
        self._content_rule = wx.TextCtrl( edit_panel )
        
        ( tag_rules, content_rule, string_match, string_converter ) = formula.ToTuple()
        
        self._string_match_button = StringMatchButton( edit_panel, string_match )
        
        self._string_converter_button = StringConverterButton( edit_panel, string_converter )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._example_data.SetValue( example_data )
        
        self._run_test = ClientGUICommon.BetterButton( test_panel, 'test parse', self.TestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This searches html for simple strings, which it returns to its parent.

The html's branches will be searched recursively by each tag rule in turn and then the given attribute of the final tags will be returned.

So, to find the 'src' of the first <img> tag beneath all <span> tags with the class 'content', use:

'all span tags with class=content'
1st img tag'
attribute: src'

Leave the 'attribute' blank to fetch the string of the tag (i.e. <p>This part</p>).

Note that you can set _negative_ numbers for the 'remove characters' parts, which will remove all but that many of the opposite end's characters. For instance:

remove 2 from the beginning of 'abcdef' gives 'cdef'

remove -2 from the beginning of 'abcdef' gives 'ef'.'''
        
        info_st = wx.StaticText( info_panel, label = message )
        
        info_st.Wrap( 400 )
        
        #
        
        for rule in tag_rules:
            
            pretty_rule = ClientParsing.RenderTagRule( rule )
            
            self._tag_rules.Append( pretty_rule, rule )
            
        
        if content_rule is None:
            
            content_rule = ''
            
        
        self._content_rule.SetValue( content_rule )
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        udd_button_vbox = wx.BoxSizer( wx.VERTICAL )
        
        udd_button_vbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        udd_button_vbox.AddF( self._move_rule_up, CC.FLAGS_VCENTER )
        udd_button_vbox.AddF( self._delete_rule, CC.FLAGS_VCENTER )
        udd_button_vbox.AddF( self._move_rule_down, CC.FLAGS_VCENTER )
        udd_button_vbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        tag_rules_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        tag_rules_hbox.AddF( self._tag_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        tag_rules_hbox.AddF( udd_button_vbox, CC.FLAGS_VCENTER )
        
        ae_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ae_button_hbox.AddF( self._add_rule, CC.FLAGS_VCENTER )
        ae_button_hbox.AddF( self._edit_rule, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'attribute to fetch: ', self._content_rule ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._string_match_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._string_converter_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._run_test, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
            
            new_rule = ( 'a', {}, None )
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = ClientParsing.RenderTagRule( rule )
                
                self._tag_rules.Append( pretty_rule, rule )
                
            
        
    
    def Delete( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if self._tag_rules.GetCount() == 1:
                
                wx.MessageBox( 'A parsing formula needs at least one tag rule!' )
                
            else:
                
                self._tag_rules.Delete( selection )
                
            
        
    
    def Edit( self ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._tag_rules.GetClientData( selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = ClientParsing.RenderTagRule( rule )
                    
                    self._tag_rules.SetString( selection, pretty_rule )
                    self._tag_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def GetValue( self ):
        
        tags_rules = [ self._tag_rules.GetClientData( i ) for i in range( self._tag_rules.GetCount() ) ]
        content_rule = self._content_rule.GetValue()
        
        if content_rule == '':
            
            content_rule = None
            
        
        string_match = self._string_match_button.GetValue()
        
        string_converter = self._string_converter_button.GetValue()
        
        formula = ClientParsing.ParseFormulaHTML( tags_rules, content_rule, string_match, string_converter )
        
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
            
        
    
    def TestParse( self ):
        
        formula = self.GetValue()
        
        html = self._example_data.GetValue()
        
        try:
            
            results = formula.Parse( html )
            
            results = [ '*** RESULTS BEGIN ***' ] + results + [ '*** RESULTS END ***' ]
            
            results_text = os.linesep.join( results )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        
    
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
        
        button_hbox.AddF( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._copy_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._paste_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.AddF( self._nodes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
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
            
            if isinstance( obj, ( ClientParsing.ParseNodeContent, ClientParsing.ParseNodeContentLink ) ):
                
                node = obj
                
                ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( node )
                
                self._nodes.Append( display_tuple, sort_tuple, node )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
    def AddContentNode( self ):
        
        dlg_title = 'edit content node'
        
        empty_node = ClientParsing.ParseNodeContent()
        
        panel_class = EditParseNodeContentPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddLinkNode( self ):
        
        dlg_title = 'edit link node'
        
        empty_node = ClientParsing.ParseNodeContentLink()
        
        panel_class = EditParseNodeContentLinkPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddNode( self, dlg_title, empty_node, panel_class ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg_edit:
            
            referral_url = self._referral_url_callable()
            example_data = self._example_data_callable()
            
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit node' ) as dlg:
                
                if isinstance( node, ClientParsing.ParseNodeContent):
                    
                    panel_class = EditParseNodeContentPanel
                    
                elif isinstance( node, ClientParsing.ParseNodeContentLink ):
                    
                    panel_class = EditParseNodeContentLinkPanel
                    
                
                referral_url = self._referral_url_callable()
                example_data = self._example_data_callable()
                
                panel = panel_class( dlg, node, referral_url, example_data )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_node = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertNodeToTuples( edited_node )
                    
                    self._nodes.UpdateRow( i, display_tuple, sort_tuple, edited_node )
                    
                
                
            
        
    
    def GetValue( self ):
        
        return self._nodes.GetObjects()
        
    
    def Paste( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text )
                
                self._ImportObject( obj )
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
class EditParseNodeContentPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, referral_url = None, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if referral_url is None:
            
            referral_url = 'test-url.com/test_query'
            
        
        self._referral_url = referral_url
        
        if example_data is None:
            
            example_data = ''
            
        
        notebook = wx.Notebook( self )
        
        #
        
        self._edit_panel = wx.Panel( notebook )
        
        self._edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( self._edit_panel )
        
        self._content_panel = ClientGUICommon.StaticBox( self._edit_panel, 'content type' )
        
        self._content_type = ClientGUICommon.BetterChoice( self._content_panel )
        
        self._content_type.Append( 'tags', HC.CONTENT_TYPE_MAPPINGS )
        self._content_type.Append( 'veto', HC.CONTENT_TYPE_VETO )
        
        self._content_type.Bind( wx.EVT_CHOICE, self.EventContentTypeChange )
        
        # bind an event here when I add new content types that will dynamically hide/show the namespace/rating stuff and relayout as needed
        # it should have a forced name or something. whatever we'll use to discriminate between rating services on 'import options - ratings'
        # (this probably means sending and EditPanel size changed event or whatever)
        
        self._mappings_panel = wx.Panel( self._content_panel )
        
        self._namespace = wx.TextCtrl( self._mappings_panel )
        
        self._veto_panel = wx.Panel( self._content_panel )
        
        self._veto_if_matches_found = wx.CheckBox( self._veto_panel )
        self._match_if_text_present = wx.CheckBox( self._veto_panel )
        self._search_text = wx.TextCtrl( self._veto_panel )
        
        formula_panel = ClientGUICommon.StaticBox( self._edit_panel, 'formula' )
        
        self._formula_description = ClientGUICommon.SaneMultilineTextCtrl( formula_panel )
        
        self._formula_description.SetMinSize( ( -1, 200 ) )
        
        self._formula_description.Disable()
        
        self._edit_formula = ClientGUICommon.BetterButton( formula_panel, 'edit formula', self.EditFormula )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._test_parse = ClientGUICommon.BetterButton( test_panel, 'test parse', self.TestParse )
        
        self._results = ClientGUICommon.SaneMultilineTextCtrl( test_panel )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        info_panel = wx.Panel( notebook )
        
        message = '''This node takes html from its parent and applies a parsing formula to it to search for content.

Select the content type and set any additional info to further modify what the formula returns.

The 'veto' type will tell the parent panel that this page, while it returned 200 OK, is nonetheless incorrect (e.g. the searched-for image does not exist, so you have been redirected back to a default gallery page) and so no parsing should be done on it. If the value in the additional info box exists anywhere in what the formula finds, the veto will be raised.'''
        
        info_st = wx.StaticText( info_panel, label = message )
        
        info_st.Wrap( 400 )
        
        #
        
        ( name, content_type, self._current_formula, additional_info ) = node.ToTuple()
        
        self._name.SetValue( name )
        
        self._content_type.SelectClientData( content_type )
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = additional_info
            
            self._namespace.SetValue( namespace )
            
        elif content_type == HC.CONTENT_TYPE_VETO:
            
            ( veto_if_matches_found, match_if_text_present, search_text ) = additional_info
            
            self._veto_if_matches_found.SetValue( veto_if_matches_found )
            self._match_if_text_present.SetValue( match_if_text_present )
            self._search_text.SetValue( search_text )
            
        
        self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
        
        self._example_data.SetValue( example_data )
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._mappings_panel, rows )
        
        self._mappings_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'veto if matches found: ', self._veto_if_matches_found ) )
        rows.append( ( 'match if text present: ', self._match_if_text_present ) )
        rows.append( ( 'search text: ', self._search_text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._veto_panel, rows )
        
        self._veto_panel.SetSizer( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'content type: ', self._content_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._content_panel, rows )
        
        self._content_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.AddF( self._mappings_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._content_panel.AddF( self._veto_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        formula_panel.AddF( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        formula_panel.AddF( self._edit_formula, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._edit_panel, rows )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( formula_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( self._edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.EventContentTypeChange( None )
        
    
    def EventContentTypeChange( self, event ):
        
        choice = self._content_type.GetChoice()
        
        if choice == HC.CONTENT_TYPE_MAPPINGS:
            
            self._veto_panel.Hide()
            self._mappings_panel.Show()
            
        elif choice == HC.CONTENT_TYPE_VETO:
            
            self._mappings_panel.Hide()
            self._veto_panel.Show()
            
        
        self._content_panel.Layout()
        self._edit_panel.Layout()
        
    
    def EditFormula( self ):
        
        dlg_title = 'edit html formula'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
            
            example_data = self._example_data.GetValue()
            
            panel = EditHTMLFormulaPanel( dlg, self._current_formula, example_data )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = panel.GetValue()
                
                self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
                
            
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        content_type = self._content_type.GetChoice()
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            namespace = self._namespace.GetValue()
            
            additional_info = namespace
            
        else:
            
            veto_if_matches_found = self._veto_if_matches_found.GetValue()
            match_if_text_present = self._match_if_text_present.GetValue()
            search_text = self._search_text.GetValue()
            
            additional_info = ( veto_if_matches_found, match_if_text_present, search_text )
            
        
        formula = self._current_formula
        
        node = ClientParsing.ParseNodeContent( name = name, content_type = content_type, formula = formula, additional_info = additional_info )
        
        return node
        
    
    def TestParse( self ):
        
        node = self.GetValue()
        
        try:
            
            stop_time = HydrusData.GetNow() + 30
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            data = self._example_data.GetValue()
            referral_url = self._referral_url
            desired_content = 'all'
            
            results = node.Parse( job_key, data, referral_url, desired_content )
            
            result_lines = [ '*** RESULTS BEGIN ***' ]
            
            result_lines.extend( ( ClientParsing.ConvertContentResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        
    
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
        
        ( name, self._current_formula, children ) = node.ToTuple()
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        formula_panel = ClientGUICommon.StaticBox( edit_panel, 'formula' )
        
        self._formula_description = ClientGUICommon.SaneMultilineTextCtrl( formula_panel )
        
        self._formula_description.SetMinSize( ( -1, 200 ) )
        
        self._formula_description.Disable()
        
        self._edit_formula = ClientGUICommon.BetterButton( formula_panel, 'edit formula', self.EditFormula )
        
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
        
        info_st = wx.StaticText( info_panel, label = message )
        
        info_st.Wrap( 400 )
        
        #
        
        self._name.SetValue( name )
        
        self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
        
        #
        
        formula_panel.AddF( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        formula_panel.AddF( self._edit_formula, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        children_panel.AddF( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( formula_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_fetch_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._my_example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        
    
    def EditFormula( self ):
        
        dlg_title = 'edit html formula'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
            
            example_data = self._example_data.GetValue()
            
            panel = EditHTMLFormulaPanel( dlg, self._current_formula, example_data )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = panel.GetValue()
                
                self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
                
            
        
    
    def EventTestFetchResult( self, event ):
        
        # this should be published to a job key panel or something so user can see it and cancel if needed
        
        network_job = ClientNetworking.NetworkJob( 'GET', self._my_example_url, referral_url = self._referral_url )
        
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
        
        node = self.GetValue()
        
        try:
            
            stop_time = HydrusData.GetNow() + 30
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            data = self._example_data.GetValue()
            referral_url = self._referral_url
            desired_content = 'all'
            
            parsed_urls = node.ParseURLs( job_key, data, referral_url )
            
            if len( parsed_urls ) > 0:
                
                self._my_example_url = parsed_urls[0]
                self._test_fetch_result.Enable()
                
            
            result_lines = [ '*** RESULTS BEGIN ***' ]
            
            result_lines.extend( parsed_urls )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        
    
    def GetExampleData( self ):
        
        return self._my_example_data.GetValue()
        
    
    def GetExampleURL( self ):
        
        if self._my_example_url is not None:
            
            return self._my_example_url
            
        else:
            
            return ''
            
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        formula = self._current_formula
        
        children = self._children.GetValue()
        
        node = ClientParsing.ParseNodeContentLink( name = name, formula = formula, children = children )
        
        return node
        
    
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
        
        self._example_data = ''
        
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
        
        info_st = wx.StaticText( info_panel )
        
        info_st.SetLabelText( message )
        
        info_st.Wrap( 400 )
        
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
        
        static_args_panel.AddF( self._static_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        query_message = 'This query will be executed first.'
        
        query_panel.AddF( wx.StaticText( query_panel, label = query_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        query_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        query_panel.AddF( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        children_message = 'The data returned by the query will be passed to each of these children for content parsing.'
        
        children_panel.AddF( wx.StaticText( children_panel, label = children_message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        children_panel.AddF( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'script name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._test_script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        notebook.AddPage( info_panel, 'info', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
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
        
        script = self.GetValue()
        
        try:
            
            stop_time = HydrusData.GetNow() + 30
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            self._test_script_management.SetJobKey( job_key )
            
            data = self._example_data.GetValue()
            desired_content = 'all'
            
            results = script.Parse( job_key, data, desired_content )
            
            result_lines = [ '*** RESULTS BEGIN ***' ]
            
            result_lines.extend( ( ClientParsing.ConvertContentResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        finally:
            
            job_key.Finish()
            
        
    
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
    
    def __init__( self, parent, string_converter ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        transformations_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._transformations = ClientGUIListCtrl.BetterListCtrl( transformations_panel, 'string_converter_transformations', 7, 35, [ ( '#', 3 ), ( 'transformation', 30 ), ( 'result', -1 ) ], self._ConvertTransformationToListCtrlTuple, delete_key_callback = self._DeleteTransformation, activation_callback = self._EditTransformation )
        
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
        self._example_string.SetValue( string_converter.example_string )
        
        self._transformations.UpdateDatas() # to refresh, now they are all in the list
        
        self._transformations.Sort( 0 )
        
        #
        
        rows = []
        
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( transformations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._example_string.Bind( wx.EVT_TEXT, self.EventUpdate )
        
    
    def _AddTransformation( self ):
        
        transformation_type = ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT
        data = ' extra text'
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation' ) as dlg:
            
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
        
        pretty_number = HydrusData.ConvertIntToPrettyString( number )
        pretty_transformation = ClientParsing.StringConverter.TransformationToUnicode( ( transformation_type, data ) )
        
        string_converter = self._GetValue()
        
        try:
            
            pretty_result = string_converter.Convert( self._example_string.GetValue(), number )
            
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation' ) as dlg:
                
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
            
            wx.MessageBox( 'Please enter an example text that can be converted!' )
            
            raise HydrusExceptions.VetoException()
            
        
        return string_converter
        
    
    class _TransformationPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, transformation_type, data ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._transformation_type = ClientGUICommon.BetterChoice( self )
            
            for t_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_REVERSE ):
                
                self._transformation_type.Append( ClientParsing.transformation_type_str_lookup[ t_type ], t_type )
                
            
            self._data_text = wx.TextCtrl( self )
            self._data_number = wx.SpinCtrl( self, min = 0, max = 65535 )
            self._data_encoding = ClientGUICommon.BetterChoice( self )
            
            for e in ( 'hex', 'base64' ):
                
                self._data_encoding.Append( e, e )
                
            
            #
            
            self._transformation_type.SelectClientData( transformation_type )
            
            self._UpdateDataControls()
            
            #
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_ENCODE ):
                
                self._data_encoding.SelectClientData( data )
                
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
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._transformation_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            #
            
            self._transformation_type.Bind( wx.EVT_CHOICE, self.EventChoice )
            
        
        def _UpdateDataControls( self ):
            
            self._data_text.Disable()
            self._data_number.Disable()
            self._data_encoding.Disable()
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                self._data_encoding.Enable()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT ):
                
                self._data_text.Enable()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END ):
                
                self._data_number.Enable()
                
            
        
        def EventChoice( self, event ):
            
            self._UpdateDataControls()
            
        
        def GetValue( self ):
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                data = self._data_encoding.GetChoice()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT ):
                
                data = self._data_text.GetValue()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END ):
                
                data = self._data_number.GetValue()
                
            else:
                
                data = None
                
            
            return ( transformation_type, data )
            
        
    
class EditStringMatchPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_match ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
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
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._example_string_matches, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
                
                reason = unicode( e )
                
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
            
            wx.MessageBox( 'Please enter an example text that matches the given rules!' )
            
            raise HydrusExceptions.VetoException()
            
        
        return string_match
        
    
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
        
        button_hbox.AddF( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._export_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._import_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.AddF( self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
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
        file_identifier_string_converter = ClientParsing.StringConverter( [ ClientParsing.STRING_TRANSFORMATION_ENCODE, 'hex' ], 'some hash bytes' )
        file_identifier_arg_name = 'md5'
        static_args = {}
        children = []
        
        dlg_title = 'edit file metadata lookup script'
        
        empty_script = ClientParsing.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
        
        panel_class = EditParsingScriptFileLookupPanel
        
        self.AddScript( dlg_title, empty_script, panel_class )
        
    
    def AddScript( self, dlg_title, empty_script, panel_class ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg_edit:
            
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
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
                
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
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text )
                
                self._ImportObject( obj )
                
            except Exception as e:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
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
        self._link_button.SetToolTipString( 'urls found by the script' )
        
        self._cancel_button = wx.BitmapButton( main_panel, bitmap = CC.GlobalBMPs.stop )
        self._cancel_button.Bind( wx.EVT_BUTTON, self.EventCancelButton )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate, id = ID_TIMER_SCRIPT_UPDATE )
        
        self._update_timer = wx.Timer( self, id = ID_TIMER_SCRIPT_UPDATE )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._link_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._cancel_button, CC.FLAGS_VCENTER )
        
        main_panel.AddF( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_panel.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( main_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
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
                    
                
            
        
    
    def TIMEREventUpdate( self, event ):
        
        with self._lock:
            
            self._Update()
            
            if self._job_key is not None:
                
                self._update_timer.Start( 100, wx.TIMER_ONE_SHOT )
                
            
        
    
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
            
            ClientGUIMenus.AppendMenuItem( self, menu, url, 'launch this url in your browser', webbrowser.open, url )
            
        
        HG.client_controller.PopupMenu( self, menu )
        
        
    
    def SetJobKey( self, job_key ):
        
        with self._lock:
            
            self._job_key = job_key
            
        
        self._update_timer.Start( 100, wx.TIMER_ONE_SHOT )
        
    
