import os
import threading

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientSerialisable
from hydrus.client import ClientStrings
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUISerialisable
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.parsing import ClientGUIParsing
from hydrus.client.gui.parsing import ClientGUIParsingFormulae
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.parsing import ClientParsing
from hydrus.client.parsing import ClientParsingLegacy
from hydrus.client.parsing import ClientParsingResults

class EditNodes( QW.QWidget ):
    
    def __init__( self, parent, nodes, referral_url_callable, example_data_callable ):
        
        super().__init__( parent )
        
        self._referral_url_callable = referral_url_callable
        self._example_data_callable = example_data_callable
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_NODES.ID, self._ConvertNodeToDisplayTuple, self._ConvertNodeToSortTuple )
        
        self._nodes = ClientGUIListCtrl.BetterListCtrlTreeView( self, 20, model, delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'content node', 'A node that parses the given data for content.', self.AddContentNode ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'link node', 'A node that parses the given data for a link, which it then pursues.', self.AddLinkNode ) )
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_template_items )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy', self.Copy )
        
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self.Paste )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        self._nodes.AddDatas( nodes )
        
        #
        
        vbox = QP.VBoxLayout()
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._duplicate_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._nodes, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
    
    def _ConvertNodeToDisplayTuple( self, node ):
        
        ( name, node_type, produces ) = node.ToPrettyStrings()
        
        return ( name, node_type, produces )
        
    
    _ConvertNodeToSortTuple = _ConvertNodeToDisplayTuple
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for node in self._nodes.GetData( only_selected = True ):
            
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
            
            if isinstance( obj, ( ClientParsing.ContentParser, ClientParsingLegacy.ParseNodeContentLink ) ):
                
                node = obj
                
                self._nodes.AddData( node )
                
            else:
                
                ClientGUIDialogsMessage.ShowWarning( self, f'That was not a script--it was a: {type(obj).__name__}' )
                
            
        
    
    def AddContentNode( self ):
        
        dlg_title = 'edit content node'
        
        empty_node = ClientParsing.ContentParser()
        
        panel_class = ClientGUIParsing.EditContentParserPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddLinkNode( self ):
        
        dlg_title = 'edit link node'
        
        empty_node = ClientParsingLegacy.ParseNodeContentLink()
        
        panel_class = EditParseNodeContentLinkPanel
        
        self.AddNode( dlg_title, empty_node, panel_class )
        
    
    def AddNode( self, dlg_title, empty_node, panel_class ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            referral_url = self._referral_url_callable()
            example_data = self._example_data_callable()
            
            if isinstance( empty_node, ClientParsing.ContentParser ):
                
                panel = panel_class( dlg_edit, empty_node, ClientParsing.ParsingTestData( {}, ( example_data, ) ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                
            else:
                
                panel = panel_class( dlg_edit, empty_node, referral_url, example_data )
                
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_node = panel.GetValue()
                
                self._nodes.AddDatas( new_node )
                
            
        
    
    def Copy( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            CG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def Delete( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._nodes.DeleteSelected()
            
        
    
    def Duplicate( self ):
        
        nodes_to_dupe = self._nodes.GetData( only_selected = True )
        
        for node in nodes_to_dupe:
            
            dupe_node = node.Duplicate()
            
            self._nodes.AddDatas( dupe_node )
            
        
    
    def Edit( self ):
        
        data = self._nodes.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        node = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit node', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            example_data = self._example_data_callable()
            
            if isinstance( node, ClientParsing.ContentParser ):
                
                panel = ClientGUIParsing.EditContentParserPanel( dlg, node, ClientParsing.ParsingTestData( {}, ( example_data, ) ), [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_VETO ] )
                
            elif isinstance( node, ClientParsingLegacy.ParseNodeContentLink ):
                
                panel = EditParseNodeContentLinkPanel( dlg, node, example_data = example_data )
                
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_node = panel.GetValue()
                
                self._nodes.ReplaceData( node, edited_node, sort_and_scroll = True )
                
            
        
    
    def GetValue( self ):
        
        return self._nodes.GetData()
        
    
    def Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Nodes', e )
            
        
    
class EditParseNodeContentLinkPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, node, referral_url = None, example_data = None ):
        
        super().__init__( parent )
        
        if referral_url is None:
            
            referral_url = 'test-url.com/test_query'
            
        
        self._referral_url = referral_url
        
        if example_data is None:
            
            example_data = ''
            
        
        self._my_example_url = None
        
        notebook = QW.QTabWidget( self )
        
        ( name, formula, children ) = node.ToTuple()
        
        #
        
        edit_panel = QW.QWidget( notebook )
        
        self._name = QW.QLineEdit( edit_panel )
        
        self._formula = ClientGUIParsingFormulae.EditFormulaPanel( edit_panel, formula, self.GetTestData )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = QW.QWidget( notebook )
        
        self._example_data = QW.QPlainTextEdit( test_panel )
        
        self._example_data.setMinimumHeight( 200 )
        
        self._example_data.setPlainText( example_data )
        
        self._test_parse = QW.QPushButton( 'test parse', test_panel )
        self._test_parse.clicked.connect( self.EventTestParse )
        
        self._results = QW.QPlainTextEdit( test_panel )
        
        self._results.setMinimumHeight( 200 )
        
        self._test_fetch_result = QW.QPushButton( 'try fetching the first result', test_panel )
        self._test_fetch_result.clicked.connect( self.EventTestFetchResult )
        self._test_fetch_result.setEnabled( False )
        
        self._my_example_data = QW.QPlainTextEdit( test_panel )
        
        #
        
        info_panel = QW.QWidget( notebook )
        
        message = '''This node looks for one or more urls in the data it is given, requests each in turn, and gives the results to its children for further parsing.

If your previous query result responds with links to where the actual content is, use this node to bridge the gap.

The formula should attempt to parse full or relative urls. If the url is relative (like href="/page/123"), it will be appended to the referral url given by this node's parent. It will then attempt to GET them all.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        #
        
        self._name.setText( name )
        
        #
        
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name or description (optional): ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._formula, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_fetch_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._my_example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.setLayout( vbox )
        
        #
        
        notebook.addTab( edit_panel, 'edit' )
        notebook.setCurrentWidget( edit_panel )
        notebook.addTab( test_panel, 'test' )
        notebook.addTab( info_panel, 'info' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        
    
    def EventTestFetchResult( self ):
        
        # this should be published to a job key panel or something so user can see it and cancel if needed
        
        network_job = ClientNetworkingJobs.NetworkJob( 'GET', self._my_example_url, referral_url = self._referral_url )
        
        network_job.OverrideBandwidth()
        
        CG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.CancelledException:
            
            self._my_example_data.setPlainText( 'fetch cancelled' )
            
            return
            
        except HydrusExceptions.NetworkException as e:
            
            self._my_example_data.setPlainText( 'fetch failed' )
            
            raise
            
        
        example_text = network_job.GetContentText()
        
        self._example_data.setPlainText( example_text )
        
    
    def EventTestParse( self ):
        
        def qt_code( parsed_urls ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            if len( parsed_urls ) > 0:
                
                self._my_example_url = parsed_urls[0]
                self._test_fetch_result.setEnabled( True )
                
            
            result_lines = [ '*** ' + HydrusNumbers.ToHumanInt( len( parsed_urls ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( parsed_urls )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = '\n'.join( result_lines )
            
            self._results.setPlainText( results_text )
            
        
        def do_it( node, data, referral_url ):
            
            try:
                
                stop_time = HydrusTime.GetNow() + 30
                
                job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
                
                parsed_urls = node.ParseURLs( job_status, data, referral_url )
                
                CG.client_controller.CallAfter( self, qt_code, parsed_urls )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Parsing problem!', message )
                
            
        
        node = self.GetValue()
        data = self._example_data.toPlainText()
        referral_url = self._referral_url
        
        CG.client_controller.CallToThread( do_it, node, data, referral_url )
        
    
    def GetExampleData( self ):
        
        return self._example_data.toPlainText()
        
    
    def GetExampleURL( self ):
        
        if self._my_example_url is not None:
            
            return self._my_example_url
            
        else:
            
            return ''
            
        
    
    def GetTestData( self ):
        
        return ClientParsing.ParsingTestData( {}, ( self._example_data.toPlainText(), ) )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        formula = self._formula.GetValue()
        
        children = self._children.GetValue()
        
        node = ClientParsingLegacy.ParseNodeContentLink( name = name, formula = formula, children = children )
        
        return node
        
    
class EditParsingScriptFileLookupPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, script ):
        
        super().__init__( parent )
        
        ( name, url, query_type, file_identifier_type, file_identifier_string_converter, file_identifier_arg_name, static_args, children ) = script.ToTuple()
        
        #
        
        notebook = QW.QTabWidget( self )
        
        #
        
        edit_panel = QW.QWidget( notebook )
        
        self._name = QW.QLineEdit( edit_panel )
        
        query_panel = ClientGUICommon.StaticBox( edit_panel, 'query' )
        
        self._url = QW.QLineEdit( query_panel )
        
        self._url.setText( url )
        
        self._query_type = ClientGUICommon.BetterChoice( query_panel )
        
        self._query_type.addItem( 'GET', HC.GET )
        self._query_type.addItem( 'POST', HC.POST )
        
        self._file_identifier_type = ClientGUICommon.BetterChoice( query_panel )
        
        for t in [ ClientParsingLegacy.FILE_IDENTIFIER_TYPE_FILE, ClientParsingLegacy.FILE_IDENTIFIER_TYPE_MD5, ClientParsingLegacy.FILE_IDENTIFIER_TYPE_SHA1, ClientParsingLegacy.FILE_IDENTIFIER_TYPE_SHA256, ClientParsingLegacy.FILE_IDENTIFIER_TYPE_SHA512, ClientParsingLegacy.FILE_IDENTIFIER_TYPE_USER_INPUT ]:
            
            self._file_identifier_type.addItem( ClientParsingLegacy.file_identifier_string_lookup[ t], t )
            
        
        self._file_identifier_string_converter = ClientGUIStringControls.StringConverterButton( query_panel, file_identifier_string_converter )
        
        self._file_identifier_arg_name = QW.QLineEdit( query_panel )
        
        static_args_panel = ClientGUICommon.StaticBox( query_panel, 'static arguments' )
        
        self._static_args = ClientGUIStringControls.StringToStringDictControl( static_args_panel, static_args, min_height = 4 )
        
        children_panel = ClientGUICommon.StaticBox( edit_panel, 'content parsing children' )
        
        self._children = EditNodes( children_panel, children, self.GetExampleURL, self.GetExampleData )
        
        #
        
        test_panel = QW.QWidget( notebook )
        
        self._test_script_management = ScriptManagementControl( test_panel )
        
        self._test_arg = QW.QLineEdit( test_panel )
        
        self._test_arg.setText( 'enter example file path, hex hash, or raw user input here' )
        
        self._fetch_data = QW.QPushButton( 'fetch response', test_panel )
        self._fetch_data.clicked.connect( self.EventFetchData )
        
        self._example_data = QW.QPlainTextEdit( test_panel )
        
        self._example_data.setMinimumHeight( 200 )
        
        self._test_parsing = QW.QPushButton( 'test parse (note if you have \'link\' nodes, they will make their requests)', test_panel )
        self._test_parsing.clicked.connect( self.EventTestParse )
        
        self._results = QW.QPlainTextEdit( test_panel )
        
        self._results.setMinimumHeight( 200 )
        
        #
        
        info_panel = QW.QWidget( notebook )
        
        message = '''This script looks up tags for a single file.

It will download the result of a query that might look something like this:

https://www.file-lookup.com/form.php?q=getsometags&md5=[md5-in-hex]

And pass that html to a number of 'parsing children' that will each look through it in turn and try to find tags.'''
        
        info_st = ClientGUICommon.BetterStaticText( info_panel, label = message )
        
        info_st.setWordWrap( True )
        
        #
        
        self._name.setText( name )
        
        self._query_type.SetValue( query_type )
        self._file_identifier_type.SetValue( file_identifier_type )
        self._file_identifier_arg_name.setText( file_identifier_arg_name )
        
        self._results.setPlainText( 'Successfully parsed results will be printed here.' )
        
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
        
        query_panel.Add( QW.QLabel( query_message, query_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
        query_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        query_panel.Add( static_args_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        children_message = 'The data returned by the query will be passed to each of these children for content parsing.'
        
        children_panel.Add( QW.QLabel( children_message, children_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
        children_panel.Add( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'script name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, children_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        edit_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._test_script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._test_arg, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fetch_data, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parsing, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        test_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, info_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        info_panel.setLayout( vbox )
        
        #
        
        notebook.addTab( edit_panel, 'edit' )
        notebook.setCurrentWidget( edit_panel )
        notebook.addTab( test_panel, 'test' )
        notebook.addTab( info_panel, 'info' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def EventFetchData( self ):
        
        script = self.GetValue()
        
        test_arg = self._test_arg.text()
        
        file_identifier_type = self._file_identifier_type.GetValue()
        
        if file_identifier_type == ClientParsingLegacy.FILE_IDENTIFIER_TYPE_FILE:
            
            if not os.path.exists( test_arg ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'That file does not exist!' )
                
                return
                
            
            file_identifier = test_arg
            
        elif file_identifier_type == ClientParsingLegacy.FILE_IDENTIFIER_TYPE_USER_INPUT:
            
            file_identifier = test_arg
            
        else:
            
            file_identifier = bytes.fromhex( test_arg )
            
        
        try:
            
            stop_time = HydrusTime.GetNow() + 30
            
            job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
            
            self._test_script_management.SetJobStatus( job_status )
            
            parsing_text = script.FetchParsingText( job_status, file_identifier )
            
            try:
                
                self._example_data.setPlainText( parsing_text )
                
            except UnicodeDecodeError:
                
                self._example_data.setPlainText( 'The fetched data, which had length ' + HydrusData.ToHumanBytes( len( parsing_text ) ) + ', did not appear to be displayable text.' )
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            message = 'Could not fetch data!'
            message += '\n' * 2
            message += str( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Could not fetch!', message )
            
        finally:
            
            job_status.Finish()
            
        
    
    def EventTestParse( self ):
        
        def qt_code( parsed_post: ClientParsingResults.ParsedPost ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            result_lines = [ '*** ' + HydrusNumbers.ToHumanInt( len( parsed_post ) ) + ' RESULTS BEGIN ***' ]
            
            result_lines.extend( [ parsed_content.ToString() for parsed_content in parsed_post.parsed_contents ] )
            
            result_lines.append( '*** RESULTS END ***' )
            
            results_text = '\n'.join( result_lines )
            
            self._results.setPlainText( results_text )
            
        
        def do_it( script, job_status, data ):
            
            try:
                
                parsed_post = script.Parse( job_status, data )
                
                CG.client_controller.CallAfter( self, qt_code, parsed_post )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                message = 'Could not parse!'
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', message )
                
            finally:
                
                job_status.Finish()
                
            
        
        script = self.GetValue()
        
        stop_time = HydrusTime.GetNow() + 30
        
        job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
        
        self._test_script_management.SetJobStatus( job_status )
        
        data = self._example_data.toPlainText()
        
        CG.client_controller.CallToThread( do_it, script, job_status, data )
        
    
    def GetExampleData( self ):
        
        return self._example_data.toPlainText()
        
    
    def GetExampleURL( self ):
        
        return self._url.text()
        
    
    def GetValue( self ):
        
        name = self._name.text()
        url = self._url.text()
        query_type = self._query_type.GetValue()
        file_identifier_type = self._file_identifier_type.GetValue()
        file_identifier_string_converter = self._file_identifier_string_converter.GetValue()
        file_identifier_arg_name = self._file_identifier_arg_name.text()
        static_args = self._static_args.GetValue()
        children = self._children.GetValue()
        
        script = ClientParsingLegacy.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children )
        
        return script
        
    
class ManageParsingScriptsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    SCRIPT_TYPES = []
    
    SCRIPT_TYPES.append( HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_PARSING_SCRIPTS.ID, self._ConvertScriptToDisplayTuple, self._ConvertScriptToSortTuple )
        
        self._scripts = ClientGUIListCtrl.BetterListCtrlTreeView( self, 20, model, delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'file lookup script', 'A script that fetches content for a known file.', self.AddFileLookupScript ) )
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_template_items )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to clipboard', 'Serialise the script and put it on your clipboard.', self.ExportToClipboard ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to png', 'Serialise the script and encode it to an image file you can easily share with other hydrus users.', self.ExportToPNG ) )
        
        self._export_button = ClientGUIMenuButton.MenuButton( self, 'export', menu_template_items )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from clipboard', 'Load a script from text in your clipboard.', self.ImportFromClipboard ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from png', 'Load a script from an encoded png.', self.ImportFromPNG ) )
        
        self._import_button = ClientGUIMenuButton.MenuButton( self, 'import', menu_template_items )
        
        self._duplicate_button = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        scripts = []
        
        for script_type in self.SCRIPT_TYPES:
            
            scripts.extend( CG.client_controller.Read( 'serialisable_named', script_type ) )
            
        
        self._scripts.SetData( scripts )
        
        #
        
        vbox = QP.VBoxLayout()
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._export_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._import_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._duplicate_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._scripts, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertScriptToDisplayTuple( self, script ):
        
        ( name, query_type, script_type, produces ) = script.ToPrettyStrings()
        
        return ( name, query_type, script_type, produces )
        
    
    _ConvertScriptToSortTuple = _ConvertScriptToDisplayTuple
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for script in self._scripts.GetData( only_selected = True ):
            
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
            
            if isinstance( obj, ClientParsingLegacy.ParseRootFileLookup ):
                
                script = obj
                
                self._scripts.SetNonDupeName( script )
                
                self._scripts.AddData( script )
                
            else:
                
                ClientGUIDialogsMessage.ShowWarning( self, f'That was not a script--it was a: {type(obj).__name__}' )
                
            
        
    
    def AddFileLookupScript( self ):
        
        name = 'new script'
        url = ''
        query_type = HC.GET
        file_identifier_type = ClientParsingLegacy.FILE_IDENTIFIER_TYPE_MD5
        file_identifier_string_converter = ClientStrings.StringConverter( ( ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_HEX_UTF8 ), ), 'some hash bytes' )
        file_identifier_arg_name = 'md5'
        static_args = {}
        children = []
        
        dlg_title = 'edit file metadata lookup script'
        
        empty_script = ClientParsingLegacy.ParseRootFileLookup( name, url = url, query_type = query_type, file_identifier_type = file_identifier_type, file_identifier_string_converter = file_identifier_string_converter, file_identifier_arg_name = file_identifier_arg_name, static_args = static_args, children = children)
        
        panel_class = EditParsingScriptFileLookupPanel
        
        self.AddScript( dlg_title, empty_script, panel_class )
        
    
    def AddScript( self, dlg_title, empty_script, panel_class ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg_edit:
            
            panel = panel_class( dlg_edit, empty_script )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_script = panel.GetValue()
                
                self._scripts.SetNonDupeName( new_script )
                
                self._scripts.AddData( new_script )
                
            
        
    
    def CommitChanges( self ):
        
        scripts = self._scripts.GetData()
        
        CG.client_controller.Write( 'serialisables_overwrite', self.SCRIPT_TYPES, scripts )
        
    
    def Delete( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._scripts.DeleteSelected()
            
        
    
    def Duplicate( self ):
        
        scripts_to_dupe = self._scripts.GetData( only_selected = True )
        
        for script in scripts_to_dupe:
            
            dupe_script = script.Duplicate()
            
            self._scripts.SetNonDupeName( dupe_script )
            
            self._scripts.AddData( dupe_script )
            
        
    
    def Edit( self ):
        
        data = self._scripts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        script = data
        
        if isinstance( script, ClientParsingLegacy.ParseRootFileLookup ):
            
            panel_class = EditParsingScriptFileLookupPanel
            
            dlg_title = 'edit file lookup script'
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            original_name = script.GetName()
            
            panel = panel_class( dlg, script )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_script = panel.GetValue()
                
                if edited_script.GetName() != original_name:
                    
                    self._scripts.SetNonDupeName( edited_script )
                    
                
                self._scripts.ReplaceData( script, edited_script, sort_and_scroll = True )
                
            
        
    
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
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Parsing Scripts', e )
            
        
    
    def ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png with the encoded script', wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
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
                    
                
            
        
    

class ScriptManagementControl( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._job_status = None
        
        self._lock = threading.Lock()
        
        self._recent_urls = []
        
        main_panel = ClientGUICommon.StaticBox( self, 'script control' )
        
        self._status = ClientGUICommon.BetterStaticText( main_panel )
        self._gauge = ClientGUICommon.Gauge( main_panel )
        
        self._status.setWordWrap( True )
        
        self._link_button = ClientGUICommon.IconButton( main_panel, CC.global_icons().link, self.LinkButton )
        self._link_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'urls found by the script' ) )
        
        self._cancel_button = ClientGUICommon.IconButton( main_panel, CC.global_icons().stop, self.CancelButton )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._link_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        main_panel.Add( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, main_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        #
        
        self._Reset()
        
    
    def _Reset( self ):
        
        self._status.clear()
        self._gauge.SetRange( 1 )
        self._gauge.SetValue( 0 )
        
        self._link_button.setEnabled( False )
        self._cancel_button.setEnabled( False )
        
    
    def _Update( self ):
        
        if self._job_status is None:
            
            self._Reset()
            
        else:
            
            if self._job_status.HasVariable( 'script_status' ):
                
                status = self._job_status.GetIfHasVariable( 'script_status' )
                
            else:
                
                status = ''
                
            
            self._status.setText( status )
            
            if self._job_status.HasVariable( 'script_gauge' ):
                
                ( value, range ) = self._job_status.GetIfHasVariable( 'script_gauge' )
                
            else:
                
                ( value, range ) = ( 0, 1 )
                
            
            self._gauge.SetRange( range )
            self._gauge.SetValue( value )
            
            urls = self._job_status.GetURLs()
            
            if len( urls ) == 0:
                
                if self._link_button.isEnabled():
                    
                    self._link_button.setEnabled( False )
                    
                
            else:
                
                if not self._link_button.isEnabled():
                    
                    self._link_button.setEnabled( True )
                    
                
            
            if self._job_status.IsDone():
                
                if self._cancel_button.isEnabled():
                    
                    self._cancel_button.setEnabled( False )
                    
                
            else:
                
                if not self._cancel_button.isEnabled():
                    
                    self._cancel_button.setEnabled( True )
                    
                
            
        
    
    def TIMERUIUpdate( self ):
        
        with self._lock:
            
            self._Update()
            
            if self._job_status is None:
                
                CG.client_controller.gui.UnregisterUIUpdateWindow( self )
                
            
        
    
    def CancelButton( self ):
        
        with self._lock:
            
            if self._job_status is not None:
                
                self._job_status.Cancel()
                
            
        
    
    def LinkButton( self ):
        
        with self._lock:
            
            if self._job_status is None:
                
                return
                
            
            urls = self._job_status.GetURLs()
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        open_submenu = ClientGUIMenus.GenerateMenu( menu )
        copy_submenu = ClientGUIMenus.GenerateMenu( menu )
        
        for url in urls:
            
            ClientGUIMenus.AppendMenuItem( open_submenu, url, 'launch this url in your browser', ClientPaths.LaunchURLInWebBrowser, url )
            ClientGUIMenus.AppendMenuItem( copy_submenu, url, 'copy this url to your clipboard', CG.client_controller.pub, 'clipboard', 'text', url )
            
        
        ClientGUIMenus.AppendMenu( menu, open_submenu, 'open' )
        ClientGUIMenus.AppendMenu( menu, copy_submenu, 'copy' )
        
        CGC.core().PopupMenu( self, menu )
        
        
    
    def SetJobStatus( self, job_status ):
        
        with self._lock:
            
            self._job_status = job_status
            
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
