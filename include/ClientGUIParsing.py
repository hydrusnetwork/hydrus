import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusParsing
import HydrusSerialisable
import HydrusTags
import os
import wx

class EditHTMLTagRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, rule ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( name, attrs, index ) = rule
        
        self._name = wx.TextCtrl( self )
        
        self._attrs = ClientGUICommon.EditStringToStringDict( self, attrs )
        
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
        
        self._add_rule = wx.Button( edit_panel, label = 'add' )
        self._add_rule.Bind( wx.EVT_BUTTON, self.EventAdd )
        
        self._edit_rule = wx.Button( edit_panel, label = 'edit' )
        self._edit_rule.Bind( wx.EVT_BUTTON, self.EventEdit )
        
        self._move_rule_up = wx.Button( edit_panel, label = u'\u2191' )
        self._move_rule_up.Bind( wx.EVT_BUTTON, self.EventMoveUp )
        
        self._delete_rule = wx.Button( edit_panel, label = 'X' )
        self._delete_rule.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._move_rule_down = wx.Button( edit_panel, label = u'\u2193' )
        self._move_rule_down.Bind( wx.EVT_BUTTON, self.EventMoveDown )
        
        self._content_rule = wx.TextCtrl( edit_panel )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._example_data.SetValue( example_data )
        
        self._run_test = wx.Button( test_panel, label = 'test parse' )
        self._run_test.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        ( tag_rules, content_rule ) = formula.ToTuple()
        
        for rule in tag_rules:
            
            pretty_rule = HydrusParsing.RenderTagRule( rule )
            
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
        
        message = 'The html will be searched recursively by each rule in turn and then the attribute of the final tags will be returned.'
        message += os.linesep * 2
        message += 'So, to find the \'src\' of the first <img> tag beneath all <span> tags with the class \'content\', use:'
        message += os.linesep * 2
        message += 'all span tags with class=content'
        message += os.linesep
        message += '1st img tag'
        message += os.linesep
        message += 'attribute: src'
        message += os.linesep * 2
        message += 'Leave the attribute blank to fetch the string of the tag (i.e. <p>This part</p>).'
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( wx.StaticText( edit_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( tag_rules_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( ae_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( ClientGUICommon.WrapInText( self._content_rule, edit_panel, 'attribute to fetch: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._run_test, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def EventAdd( self, event ):
        
        dlg_title = 'edit tag rule'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
            
            new_rule = ( 'a', {}, None )
            
            panel = EditHTMLTagRulePanel( dlg, new_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                rule = panel.GetValue()
                
                pretty_rule = HydrusParsing.RenderTagRule( rule )
                
                self._tag_rules.Append( pretty_rule, rule )
                
            
        
    
    def EventDelete( self, event ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if self._tag_rules.GetCount() == 1:
                
                wx.MessageBox( 'A parsing formula needs at least one tag rule!' )
                
            else:
                
                self._tag_rules.Delete( selection )
                
            
        
    
    def EventEdit( self, event ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            rule = self._tag_rules.GetClientData( selection )
            
            dlg_title = 'edit tag rule'
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
                
                panel = EditHTMLTagRulePanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    rule = panel.GetValue()
                    
                    pretty_rule = HydrusParsing.RenderTagRule( rule )
                    
                    self._tag_rules.SetString( selection, pretty_rule )
                    self._tag_rules.SetClientData( selection, rule )
                    
                
            
        
    
    def EventMoveDown( self, event ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection + 1 < self._tag_rules.GetCount():
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection + 1, rule )
            
        
    
    def EventMoveUp( self, event ):
        
        selection = self._tag_rules.GetSelection()
        
        if selection != wx.NOT_FOUND and selection > 0:
            
            pretty_rule = self._tag_rules.GetString( selection )
            rule = self._tag_rules.GetClientData( selection )
            
            self._tag_rules.Delete( selection )
            
            self._tag_rules.Insert( pretty_rule, selection - 1, rule )
            
        
    
    def EventTestParse( self, event ):
        
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
            
        
    
    def GetValue( self ):
        
        tags_rules = [ self._tag_rules.GetClientData( i ) for i in range( self._tag_rules.GetCount() ) ]
        content_rule = self._content_rule.GetValue()
        
        if content_rule == '':
            
            content_rule = None
            
        
        formula = HydrusParsing.ParseFormulaHTML( tags_rules, content_rule )
        
        return formula
        
    
class EditNodes( wx.Panel ):
    
    def __init__( self, parent, nodes, example_data_callable ):
        
        wx.Panel.__init__( self, parent )
        
        self._example_data_callable = example_data_callable
        
        self._nodes = ClientGUICommon.SaneListCtrl( self, 200, [ ( 'name', 120 ), ( 'node type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit, use_display_tuple_for_sort = True )
        
        self._add_button = wx.Button( self, label = 'add' )
        self._add_button.Bind( wx.EVT_BUTTON, self.EventAdd )
        
        self._copy_button = wx.Button( self, label = 'copy' )
        self._copy_button.Bind( wx.EVT_BUTTON, self.EventCopy )
        
        self._paste_button = wx.Button( self, label = 'paste' )
        self._paste_button.Bind( wx.EVT_BUTTON, self.EventPaste )
        
        self._duplicate_button = wx.Button( self, label = 'duplicate' )
        self._duplicate_button.Bind( wx.EVT_BUTTON, self.EventDuplicate )
        
        self._edit_button = wx.Button( self, label = 'edit' )
        self._edit_button.Bind( wx.EVT_BUTTON, self.EventEdit )
        
        self._delete_button = wx.Button( self, label = 'delete' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        #
        
        for node in nodes:
            
            ( display_tuple, data_tuple ) = self._ConvertNodeToTuples( node )
            
            self._nodes.Append( display_tuple, data_tuple )
            
        
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
        
        return ( ( name, node_type, produces ), ( node, node_type, produces ) )
        
    
    def Add( self ):
        
        with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'select the node type', [ 'content', 'link' ] ) as dlg_type:
            
            if dlg_type.ShowModal() == wx.ID_OK:
                
                node_type_string = dlg_type.GetString()
                
                if node_type_string == 'content':
                    
                    empty_node = HydrusParsing.ParseNodeContent()
                    
                    panel_class = EditParseNodeContentPanel
                    
                elif node_type_string == 'link':
                    
                    empty_node = HydrusParsing.ParseNodeContentLink()
                    
                    panel_class = EditParseNodeContentLinkPanel
                    
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit node' ) as dlg_edit:
                    
                    example_data = self._example_data_callable()
                    
                    panel = panel_class( dlg_edit, empty_node, example_data )
                    
                    dlg_edit.SetPanel( panel )
                    
                    if dlg_edit.ShowModal() == wx.ID_OK:
                        
                        new_node = panel.GetValue()
                        
                        ( display_tuple, data_tuple ) = self._ConvertNodeToTuples( new_node )
                        
                        self._nodes.Append( display_tuple, data_tuple )
                        
                    
                
            
        
    
    def Copy( self ):
        
        for i in self._nodes.GetAllSelected():
            
            ( node, node_type, produces ) = self._nodes.GetClientData( i )
            
            node_json = node.DumpToString()
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', node_json )
            
        
    
    def Delete( self ):
        
        self._nodes.RemoveAllSelected()
        
    
    def Duplicate( self ):
        
        nodes_to_dupe = []
        
        for i in self._nodes.GetAllSelected():
            
            ( node, node_type, produces ) = self._nodes.GetClientData( i )
            
            nodes_to_dupe.append( node )
            
        
        for node in nodes_to_dupe:
            
            dupe_node = node.Duplicate()
            
            ( display_tuple, data_tuple ) = self._ConvertNodeToTuples( dupe_node )
            
            self._nodes.Append( display_tuple, data_tuple )
            
        
    
    def Edit( self ):
        
        for i in self._nodes.GetAllSelected():
            
            ( node, node_type, produces ) = self._nodes.GetClientData( i )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit node' ) as dlg:
                
                if isinstance( node, HydrusParsing.ParseNodeContent):
                    
                    panel_class = EditParseNodeContentPanel
                    
                elif isinstance( node, HydrusParsing.ParseNodeContentLink ):
                    
                    panel_class = EditParseNodeContentLinkPanel
                    
                
                panel = panel_class( dlg, node )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_node = panel.GetValue()
                    
                    ( display_tuple, data_tuple ) = self._ConvertNodeToTuples( edited_node )
                    
                    self._nodes.UpdateRow( i, display_tuple, data_tuple )
                    
                
                
            
        
    
    def GetValue( self ):
        
        nodes = [ node for ( node, node_type, produces ) in self._nodes.GetClientData() ]
        
        return nodes
        
    
    def Paste( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text )
                
                if isinstance( obj, ( HydrusParsing.ParseNodeContent, HydrusParsing.ParseNodeContentLink ) ):
                    
                    node = obj
                    
                    ( display_tuple, data_tuple ) = self._ConvertNodeToTuples( node )
                    
                    self._nodes.Append( display_tuple, data_tuple )
                    
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventAdd( self, event ):
        
        self.Add()
        
    
    def EventCopy( self, event ):
        
        self.Copy()
        
    
    def EventDelete( self, event ):
        
        self.Delete()
        
    
    def EventDuplicate( self, event ):
        
        self.Duplicate()
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def EventPaste( self, event ):
        
        self.Paste()
        
    
class EditParseNodeContentPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if example_data is None:
            
            example_data = ''
            
        
        notebook = wx.Notebook( self )
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        content_panel = ClientGUICommon.StaticBox( edit_panel, 'content type' )
        
        self._content_type = ClientGUICommon.BetterChoice( content_panel )
        
        self._content_type.Append( 'tags', HC.CONTENT_TYPE_MAPPINGS )
        
        # bind an event here when I add new content types that will dynamically hide/show the namespace/rating stuff and relayout as needed
        # it should have a forced name or something. whatever we'll use to discriminate between rating services on 'import options - ratings'
        # (this probably means sending and EditPanel size changed event or whatever)
        
        self._namespace = wx.TextCtrl( content_panel )
        
        formula_panel = ClientGUICommon.StaticBox( edit_panel, 'formula' )
        
        self._formula_description = wx.TextCtrl( formula_panel, style = wx.TE_MULTILINE )
        
        self._formula_description.SetMinSize( ( -1, 200 ) )
        
        self._formula_description.Disable()
        
        self._edit_formula = wx.Button( formula_panel, label = 'edit formula' )
        self._edit_formula.Bind( wx.EVT_BUTTON, self.EventEditFormula )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._test_parse = wx.Button( test_panel, label = 'test parse' )
        self._test_parse.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        ( name, content_type, self._current_formula, additional_info ) = node.ToTuple()
        
        self._name.SetValue( name )
        
        self._content_type.SelectClientData( content_type )
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            self._namespace.SetValue( additional_info )
            
        
        self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
        
        self._example_data.SetValue( example_data )
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        # hide namespace, ratings additional info, as needed
        # since I do it as a gridbox right now, this needs to be rewritten
        
        #
        
        rows = []
        
        rows.append( ( 'content type: ', self._content_type ) )
        rows.append( ( 'namespace: ', self._namespace ) )
        
        gridbox = ClientGUICommon.WrapInGrid( content_panel, rows )
        
        content_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        formula_panel.AddF( self._formula_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        formula_panel.AddF( self._edit_formula, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( formula_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.SetSizer( vbox )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def EventEditFormula( self, event ):
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
            
            example_data = self._example_data.GetValue()
            
            panel = EditHTMLFormulaPanel( dlg, self._current_formula, example_data )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._current_formula = panel.GetValue()
                
                self._formula_description.SetValue( self._current_formula.ToPrettyMultilineString() )
                
            
        
    
    def EventTestParse( self, event ):
        
        node = self.GetValue()
        
        try:
            
            data = self._example_data.GetValue()
            url = 'test-url.com/test_query'
            desired_content = 'all'
            
            results = node.Parse( data, url, desired_content )
            
            result_lines = [ '*** RESULTS BEGIN ***' ]
            
            result_lines.extend( ( HydrusParsing.ConvertContentResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        content_type = self._content_type.GetChoice()
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            additional_info = self._namespace.GetValue()
            
        
        formula = self._current_formula
        
        node = HydrusParsing.ParseNodeContent( name = name, content_type = content_type, formula = formula, additional_info = additional_info )
        
        return node
        
    
class EditParseNodeContentLinkPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, example_data = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if example_data is None:
            
            example_data = ''
            
        
    
class EditParsingScriptFileLookupPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, script ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( name, example_url, query_type, file_identifier_type, file_identifier_encoding, file_identifier_arg_name, static_args, children ) = script.ToTuple()
        
        #
        
        notebook = wx.Notebook( self )
        
        #
        
        edit_panel = wx.Panel( notebook )
        
        edit_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._name = wx.TextCtrl( edit_panel )
        
        query_panel = ClientGUICommon.StaticBox( edit_panel, 'query' )
        
        self._query_type = ClientGUICommon.BetterChoice( query_panel )
        
        self._query_type.Append( 'GET', HC.GET )
        self._query_type.Append( 'POST', HC.POST )
        
        self._file_identifier_type = ClientGUICommon.BetterChoice( query_panel )
        
        for t in [ HydrusParsing.FILE_IDENTIFIER_TYPE_FILE, HydrusParsing.FILE_IDENTIFIER_TYPE_MD5, HydrusParsing.FILE_IDENTIFIER_TYPE_SHA1, HydrusParsing.FILE_IDENTIFIER_TYPE_SHA256, HydrusParsing.FILE_IDENTIFIER_TYPE_SHA512, HydrusParsing.FILE_IDENTIFIER_TYPE_USER_INPUT ]:
            
            self._file_identifier_type.Append( HydrusParsing.file_identifier_string_lookup[ t ], t )
            
        
        self._file_identifier_encoding = ClientGUICommon.BetterChoice( query_panel )
        
        for e in [ HC.ENCODING_RAW, HC.ENCODING_HEX, HC.ENCODING_BASE64 ]:
            
            self._file_identifier_encoding.Append( HC.encoding_string_lookup[ e ], e )
            
        
        self._file_identifier_arg_name = wx.TextCtrl( query_panel )
        
        static_args_panel = ClientGUICommon.StaticBox( query_panel, 'static arguments' )
        
        self._static_args = ClientGUICommon.EditStringToStringDict( static_args_panel, static_args )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleData )
        
        #
        
        test_panel = wx.Panel( notebook )
        
        test_panel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._example_data = ''
        
        self._test_url = wx.TextCtrl( test_panel )
        
        self._test_url.SetValue( example_url )
        
        self._test_arg = wx.TextCtrl( test_panel )
        
        self._test_arg.SetValue( 'enter example file path, hex hash, or raw user input here' )
        
        self._fetch_data = wx.Button( test_panel, label = 'fetch response' )
        self._fetch_data.Bind( wx.EVT_BUTTON, self.EventFetchData )
        
        self._example_data = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._example_data.SetMinSize( ( -1, 200 ) )
        
        self._test_parsing = wx.Button( test_panel, label = 'test parse' )
        self._test_parsing.Bind( wx.EVT_BUTTON, self.EventTestParse )
        
        self._results = wx.TextCtrl( test_panel, style = wx.TE_MULTILINE )
        
        self._results.SetMinSize( ( -1, 200 ) )
        
        #
        
        self._name.SetValue( name )
        
        self._query_type.SelectClientData( query_type )
        self._file_identifier_type.SelectClientData( file_identifier_type )
        self._file_identifier_encoding.SelectClientData( file_identifier_encoding )
        self._file_identifier_arg_name.SetValue( file_identifier_arg_name )
        
        self._results.SetValue( 'Successfully parsed results will be printed here.' )
        
        #
        
        rows = []
        
        rows.append( ( 'query type: ', self._query_type ) )
        rows.append( ( 'file identifier type: ', self._file_identifier_type ) )
        rows.append( ( 'file identifier encoding: ', self._file_identifier_encoding ) )
        rows.append( ( 'file identifier GET/POST argument name: ', self._file_identifier_arg_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( query_panel, rows )
        
        static_args_panel.AddF( self._static_args, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
        
        vbox.AddF( self._test_url, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.SetSizer( vbox )
        
        #
        
        notebook.AddPage( edit_panel, 'edit', select = True )
        notebook.AddPage( test_panel, 'test', select = False )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def EventFetchData( self, event ):
        
        example_for_now = '''<p>This is just an example for now!</p>

<ul id="tag-sidebar"><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=1girl">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=1girl">1girl</a> <span style='color: #a0a0a0;'>1946847</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=anus">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=anus">anus</a> <span style='color: #a0a0a0;'>82016</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=areolae">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=areolae">areolae</a> <span style='color: #a0a0a0;'>93162</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=ass">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=ass">ass</a> <span style='color: #a0a0a0;'>312664</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=bare_shoulders">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=bare_shoulders">bare shoulders</a> <span style='color: #a0a0a0;'>212219</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=black-framed_glasses">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=black-framed_glasses">black-framed glasses</a> <span style='color: #a0a0a0;'>1470</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=blush">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=blush">blush</a> <span style='color: #a0a0a0;'>1117240</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=breasts">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=breasts">breasts</a> <span style='color: #a0a0a0;'>1246474</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=brown_eyes">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=brown_eyes">brown eyes</a> <span style='color: #a0a0a0;'>387263</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=brown_hair">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=brown_hair">brown hair</a> <span style='color: #a0a0a0;'>671702</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=gradient_background">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=gradient_background">gradient background</a> <span style='color: #a0a0a0;'>72923</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=hair_bun">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=hair_bun">hair bun</a> <span style='color: #a0a0a0;'>16962</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=hairpin">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=hairpin">hairpin</a> <span style='color: #a0a0a0;'>10698</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=looking_at_viewer">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=looking_at_viewer">looking at viewer</a> <span style='color: #a0a0a0;'>502725</span></li><li class="tag-type-character"><a href="index.php?page=wiki&amp;s=list&amp;search=mei_%28overwatch%29">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=mei_%28overwatch%29">mei (overwatch)</a> <span style='color: #a0a0a0;'>916</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=nipples">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=nipples">nipples</a> <span style='color: #a0a0a0;'>480016</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=on_side">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=on_side">on side</a> <span style='color: #a0a0a0;'>25304</span></li><li class="tag-type-copyright"><a href="index.php?page=wiki&amp;s=list&amp;search=overwatch">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=overwatch">overwatch</a> <span style='color: #a0a0a0;'>6773</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=pants_down">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=pants_down">pants down</a> <span style='color: #a0a0a0;'>2368</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=pussy">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=pussy">pussy</a> <span style='color: #a0a0a0;'>288434</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=shirt_lift">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=shirt_lift">shirt lift</a> <span style='color: #a0a0a0;'>45320</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=side_boob">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=side_boob">side boob</a> <span style='color: #a0a0a0;'>204</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=solo">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=solo">solo</a> <span style='color: #a0a0a0;'>1551410</span></li><li class="tag-type-general"><a href="index.php?page=wiki&amp;s=list&amp;search=zetxsuna">?</a> <a href="index.php?page=post&amp;s=list&amp;tags=zetxsuna">zetxsuna</a> <span style='color: #a0a0a0;'>10</span></li></ul><br /><div id="stats">'''
        
        self._example_data.SetValue( example_for_now )
        
        return
        
        script = self.GetValue()
        
        test_url = self._test_url.GetValue()
        test_arg = self._test_arg.GetValue()
        
        file_identifier_type = self._file_identifier_type.GetChoice()
        
        if file_identifier_type == HydrusParsing.FILE_IDENTIFIER_TYPE_FILE:
            
            if not os.path.exists( test_arg ):
                
                wx.MessageBox( 'That file does not exist!' )
                
                return
                
            
            with open( test_arg, 'rb' ) as f:
                
                file_identifier = f.read()
                
            
        elif file_identifier_type == HydrusParsing.FILE_IDENTIFIER_TYPE_USER_INPUT:
            
            file_identifier = test_arg
            
        else:
            
            file_identifier = test_arg.decode( 'hex' )
            
        
        try:
            
            example_data = script.FetchData( test_url, file_identifier )
            
            self._example_data.SetValue( example_data )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not fetch data!'
            message += os.linesep * 2
            message += HydrusData.ToUnicode( e )
            
            wx.MessageBox( message )
            
        
    
    def EventTestParse( self, event ):
        
        script = self.GetValue()
        
        try:
            
            data = self._example_data.GetValue()
            url = self._test_url.GetValue()
            desired_content = 'all'
            
            results = script.Parse( data, url, desired_content )
            
            result_lines = [ '*** RESULTS BEGIN ***' ]
            
            result_lines.extend( ( HydrusParsing.ConvertContentResultToPrettyString( result ) for result in results ) )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = os.linesep.join( result_lines )
            
            self._results.SetValue( results_text )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not parse!'
            
            wx.MessageBox( message )
            
        
    
    def GetExampleData( self ):
        
        return self._example_data.GetValue()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        example_url = self._test_url.GetValue()
        query_type = self._query_type.GetChoice()
        file_identifier_type = self._file_identifier_type.GetChoice()
        file_identifier_encoding = self._file_identifier_encoding.GetChoice()
        file_identifier_arg_name = self._file_identifier_arg_name.GetValue()
        static_args = self._static_args.GetValue()
        children = self._children.GetValue()
        
        script = HydrusParsing.ParseRootFileLookup( name, example_url = example_url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_encoding = file_identifier_encoding, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children )
        
        return script
        
    
class ManageParsingScriptsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._scripts = ClientGUICommon.SaneListCtrl( self, 200, [ ( 'name', 140 ), ( 'query type', 80 ), ( 'script type', 80 ), ( 'produces', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit, use_display_tuple_for_sort = True )
        
        self._add_button = wx.Button( self, label = 'add' )
        self._add_button.Bind( wx.EVT_BUTTON, self.EventAdd )
        
        self._copy_button = wx.Button( self, label = 'copy' )
        self._copy_button.Bind( wx.EVT_BUTTON, self.EventCopy )
        
        self._paste_button = wx.Button( self, label = 'paste' )
        self._paste_button.Bind( wx.EVT_BUTTON, self.EventPaste )
        
        self._duplicate_button = wx.Button( self, label = 'duplicate' )
        self._duplicate_button.Bind( wx.EVT_BUTTON, self.EventDuplicate )
        
        self._edit_button = wx.Button( self, label = 'edit' )
        self._edit_button.Bind( wx.EVT_BUTTON, self.EventEdit )
        
        self._delete_button = wx.Button( self, label = 'delete' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        #
        
        scripts = [] # fetch all scripts from the db, populate listctrl using name column's data to store the script itself or w/e
        
        for script in scripts:
            
            ( display_tuple, data_tuple ) = self._ConvertScriptToTuples( script )
            
            self._scripts.Append( display_tuple, data_tuple )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._copy_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._paste_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._duplicate_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._edit_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox.AddF( self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertScriptToTuples( self, script ):
        
        ( name, query_type, script_type, produces ) = script.ToPrettyStrings()
        
        return ( ( name, query_type, script_type, produces ), ( script, query_type, script_type, produces ) )
        
    
    def _SetNonDupeName( self, script ):
        
        name = script.GetName()
        
        current_names = { script.GetName() for ( script, query_type, script_type, produces ) in self._scripts.GetClientData() }
        
        if name in current_names:
            
            i = 1
            
            original_name = name
            
            while name in current_names:
                
                name = original_name + ' (' + str( i ) + ')'
                
                i += 1
                
            
            script.SetName( name )
            
        
    
    def Add( self ):
        
        with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'select the script type', [ 'file lookup' ] ) as dlg_type:
            
            if dlg_type.ShowModal() == wx.ID_OK:
                
                script_type_string = dlg_type.GetString()
                
                if script_type_string == 'file lookup':
                    
                    name = 'new script'
                    example_url = 'enter example url here'
                    query_type = HC.GET
                    file_identifier_type = HydrusParsing.FILE_IDENTIFIER_TYPE_MD5
                    file_identifier_encoding = HC.ENCODING_BASE64
                    file_identifier_arg_name = 'md5'
                    static_args = {}
                    children = []
                    
                    empty_script = HydrusParsing.ParseRootFileLookup( name, example_url = example_url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_encoding = file_identifier_encoding, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
                    
                    panel_class = EditParsingScriptFileLookupPanel
                    
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit script' ) as dlg_edit:
                    
                    panel = panel_class( dlg_edit, empty_script )
                    
                    dlg_edit.SetPanel( panel )
                    
                    if dlg_edit.ShowModal() == wx.ID_OK:
                        
                        new_script = panel.GetValue()
                        
                        self._SetNonDupeName( new_script )
                        
                        ( display_tuple, data_tuple ) = self._ConvertScriptToTuples( new_script )
                        
                        self._scripts.Append( display_tuple, data_tuple )
                        
                    
                
            
        
    
    def CommitChanges( self ):
        
        scripts = [ script for ( script, query_type, script_type, produces ) in self._scripts.GetClientData() ]
        
        # save them to db
        # this should completely delete and replace the old stuff in the db to allow for renames
        
    
    def Copy( self ):
        
        for i in self._scripts.GetAllSelected():
            
            ( script, query_type, script_type, produces ) = self._scripts.GetClientData( i )
            
            script_json = script.DumpToString()
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', script_json )
            
        
    
    def Delete( self ):
        
        self._scripts.RemoveAllSelected()
        
    
    def Duplicate( self ):
        
        scripts_to_dupe = []
        
        for i in self._scripts.GetAllSelected():
            
            ( script, query_type, script_type, produces ) = self._scripts.GetClientData( i )
            
            scripts_to_dupe.append( script )
            
        
        for script in scripts_to_dupe:
            
            dupe_script = script.Duplicate()
            
            self._SetNonDupeName( dupe_script )
            
            ( display_tuple, data_tuple ) = self._ConvertScriptToTuples( dupe_script )
            
            self._scripts.Append( display_tuple, data_tuple )
            
        
    
    def Edit( self ):
        
        for i in self._scripts.GetAllSelected():
            
            ( script, query_type, script_type, produces ) = self._scripts.GetClientData( i )
            
            if isinstance( script, HydrusParsing.ParseRootFileLookup ):
                
                panel_class = EditParsingScriptFileLookupPanel
                
                dlg_title = 'edit file lookup script'
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, dlg_title ) as dlg:
                
                original_name = script.GetName()
                
                panel = panel_class( dlg, script )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_script = panel.GetValue()
                    
                    name = edited_script.GetName()
                    
                    if name != original_name:
                        
                        self._SetNonDupeName( edited_script )
                        
                    
                    ( display_tuple, data_tuple ) = self._ConvertScriptToTuples( edited_script )
                    
                    self._scripts.UpdateRow( i, display_tuple, data_tuple )
                    
                
                
            
        
    
    def Paste( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text )
                
                if isinstance( obj, HydrusParsing.ParseRootFileLookup ):
                    
                    script = obj
                    
                    self._SetNonDupeName( script )
                    
                    ( display_tuple, data_tuple ) = self._ConvertScriptToTuples( script )
                    
                    self._scripts.Append( display_tuple, data_tuple )
                    
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventAdd( self, event ):
        
        self.Add()
        
    
    def EventCopy( self, event ):
        
        self.Copy()
        
    
    def EventDelete( self, event ):
        
        self.Delete()
        
    
    def EventDuplicate( self, event ):
        
        self.Duplicate()
        
    
    def EventEdit( self, event ):
        
        self.Edit()
        
    
    def EventPaste( self, event ):
        
        self.Paste()
        
    