import json
import sys
import traceback
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTemp
from hydrus.core import HydrusText
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.parsing import ClientParsing

class TestPanel( QW.QWidget ):
    
    MAX_CHARS_IN_PREVIEW = 1024 * 64
    
    def __init__( self, parent, object_callable, test_data: ClientParsing.ParsingTestData | None = None ):
        
        super().__init__( parent )
        
        if test_data is None:
            
            test_data = ClientParsing.ParsingTestData( {}, ( '', ) )
            
        
        self._collapse_newlines = True
        
        self._object_callable = object_callable
        
        self._example_parsing_context = ClientGUIStringControls.StringToStringDictButton( self, 'edit example parsing context' )
        
        self._data_preview_notebook = QW.QTabWidget( self )
        
        raw_data_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_raw_description = ClientGUICommon.BetterStaticText( raw_data_panel )
        
        self._copy_button = ClientGUICommon.IconButton( raw_data_panel, CC.global_icons().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy the current example data to the clipboard.' ) )
        
        self._fetch_button = ClientGUICommon.IconButton( raw_data_panel, CC.global_icons().link, self._FetchFromURL )
        self._fetch_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Fetch data from an URL.' ) )
        
        self._paste_button = ClientGUICommon.IconButton( raw_data_panel, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste the current clipboard data into here.' ) )
        
        self._example_data_raw_preview = QW.QPlainTextEdit( raw_data_panel )
        self._example_data_raw_preview.setReadOnly( True )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._example_data_raw_preview, ( 60, 9 ) )
        
        self._example_data_raw_preview.setMinimumWidth( width )
        self._example_data_raw_preview.setMinimumHeight( height )
        
        self._test_parse = ClientGUICommon.BetterButton( self, 'test parse', self.TestParse )
        
        self._results = QW.QPlainTextEdit( self )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._results, ( 80, 12 ) )
        
        self._results.setMinimumWidth( width )
        self._results.setMinimumHeight( height )
        
        #
        
        self._example_parsing_context.SetValue( test_data.parsing_context )
        
        self._example_data_raw = ''
        
        self._results.setPlainText( 'Successfully parsed results will be printed here.' )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_raw_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._fetch_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_raw_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        raw_data_panel.setLayout( vbox )
        
        self._data_preview_notebook.addTab( raw_data_panel, 'raw data' )
        self._data_preview_notebook.setCurrentWidget( raw_data_panel )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._example_parsing_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._data_preview_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._test_parse, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._results, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        if len( test_data.texts ) > 0:
            
            CG.client_controller.CallAfterQtSafe( self, self._SetExampleData, test_data.texts[0] )
            
        
    
    def _Copy( self ):
        
        CG.client_controller.pub( 'clipboard', 'text', self._example_data_raw )
        
    
    def _FetchFromURL( self ):
        
        def qt_code( example_data, example_bytes ):
            
            example_parsing_context = self._example_parsing_context.GetValue()
            
            example_parsing_context[ 'url' ] = url
            example_parsing_context[ 'post_index' ] = '0'
            
            self._example_parsing_context.SetValue( example_parsing_context )
            
            self._SetExampleData( example_data, example_bytes = example_bytes )
            
        
        def do_it( url ):
            
            network_job = ClientNetworkingJobs.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            example_bytes = None
            
            try:
                
                network_job.WaitUntilDone()
                
                example_data = network_job.GetContentText()
                
                example_bytes = network_job.GetContentBytes()
                
            except HydrusExceptions.CancelledException:
                
                example_data = 'fetch cancelled'
                
            except Exception as e:
                
                example_data = 'fetch failed:' + '\n' * 2 + str( e )
                
                HydrusData.ShowException( e )
                
            
            CG.client_controller.CallAfterQtSafe( self, qt_code, example_data, example_bytes )
            
        
        message = 'Enter URL to fetch data for.'
        
        try:
            
            url = ClientGUIDialogsQuick.EnterText( self, message, placeholder = 'url' ).strip()
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if url == '':
            
            return
            
        
        CG.client_controller.CallToThread( do_it, url )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
            try:
                
                raw_bytes = raw_text.decode( 'utf-8' )
                
            except Exception as e:
                
                raw_bytes = None
                
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', str(e) )
            
            return
            
        
        try:
            
            self._SetExampleData( raw_text, example_bytes = raw_bytes )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'UTF-8 text', e )
            
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        self._example_data_raw = example_data
        
        test_parse_ok = True
        looked_like_json = False
        
        if len( example_data ) > 0:
            
            parse_phrase = ''
            good_type_found = True
            
            if HydrusText.LooksLikeJSON( example_data ):
                
                # prioritise this, so if the JSON contains some HTML, it'll overwrite here. decent compromise
                
                looked_like_json = True
                
                parse_phrase = 'looks like JSON'
                
            elif HydrusText.LooksLikeHTML( example_data ):
                
                # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
                
                parse_phrase = 'looks like HTML'
                
            else:
                
                good_type_found = False
                
                if example_bytes is not None:
                    
                    ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                    
                    try:
                        
                        with open( temp_path, 'wb' ) as f:
                            
                            f.write( example_bytes )
                            
                        
                        mime = HydrusFileHandling.GetMime( temp_path )
                        
                    except Exception as e:
                        
                        mime = HC.APPLICATION_UNKNOWN
                        
                    finally:
                        
                        HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                else:
                    
                    mime = HC.APPLICATION_UNKNOWN
                    
                
            
            if good_type_found:
                
                description = HydrusData.ToHumanBytes( len( example_data ) ) + ' total, ' + parse_phrase
                
                example_data_to_show = example_data
                
                if looked_like_json:
                    
                    try:
                        
                        j = CG.client_controller.parsing_cache.GetJSON( example_data )
                        
                        example_data_to_show = json.dumps( j, indent = 4 )
                        
                    except Exception as e:
                        
                        pass
                        
                    
                
                if len( example_data_to_show ) > self.MAX_CHARS_IN_PREVIEW:
                    
                    preview = 'PREVIEW:' + '\n' + str( example_data_to_show[:self.MAX_CHARS_IN_PREVIEW] )
                    
                else:
                    
                    preview = example_data_to_show
                    
                
            else:
                
                if mime in HC.ALLOWED_MIMES:
                    
                    description = 'that looked like a {}!'.format( HC.mime_string_lookup[ mime ] )
                    
                    preview = 'no preview'
                    
                    test_parse_ok = False
                    
                else:
                    
                    description = 'that did not look like a full HTML document, nor JSON, but will try to show it anyway'
                    
                    if len( example_data ) > self.MAX_CHARS_IN_PREVIEW:
                        
                        preview = f'PREVIEW:\n{example_data[:self.MAX_CHARS_IN_PREVIEW]}'
                        
                    else:
                        
                        preview = f'{example_data}'
                        
                    
                
            
        else:
            
            description = 'no example data set yet'
            preview = ''
            
            test_parse_ok = False
            
        
        self._test_parse.setEnabled( test_parse_ok )
        
        self._example_data_raw_description.setText( description )
        self._example_data_raw_preview.setPlainText( preview )
        
    
    def GetExampleParsingContext( self ):
        
        return self._example_parsing_context.GetValue()
        
    
    def GetTestData( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, ( self._example_data_raw, ) )
        
    
    def GetTestDataForChild( self ):
        
        return self.GetTestData()
        
    
    def SetCollapseNewlines( self, value: bool ):
        
        self._collapse_newlines = value
        
    
    def SetExampleData( self, example_data, example_bytes = None ):
        
        self._SetExampleData( example_data, example_bytes = example_bytes )
        
    
    def SetExampleParsingContext( self, example_parsing_context ):
        
        self._example_parsing_context.SetValue( example_parsing_context )
        
    
    def TestParse( self ):
        
        obj = self._object_callable()
        
        test_data = self.GetTestData()
        
        test_text = ''
        
        # change this to be for every text, do a diff panel, whatever
        
        if len( test_data.texts ) > 0:
            
            test_text = test_data.texts[0]
            
        
        if len( test_text ) == 0:
            
            self._results.setPlainText( 'Nothing to parse!' )
            
            return
            
        
        try:
            
            if 'post_index' in test_data.parsing_context:
                
                del test_data.parsing_context[ 'post_index' ]
                
            
            if isinstance( obj, ClientParsing.ParseFormula ):
                
                results_text = obj.ParsePretty( test_data.parsing_context, test_text, self._collapse_newlines )
                
            else:
                
                results_text = obj.ParsePretty( test_data.parsing_context, test_text )
                
            
            self._results.setPlainText( results_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + '\n' + str( etype.__name__ ) + ': ' + str( e ) + '\n' + trace
            
            self._results.setPlainText( message )
            
        
        
    

class TestPanelFormula( TestPanel ):
    
    def GetTestDataForStringProcessor( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        formula = self._object_callable()
        
        try:
            
            formula.SetStringProcessor( ClientStrings.StringProcessor() )
            
            texts = formula.Parse( example_parsing_context, self._example_data_raw, self._collapse_newlines )
            
        except Exception as e:
            
            texts = [ '' ]
            
        
        return ClientParsing.ParsingTestData( example_parsing_context, texts )
        
    
class TestPanelPageParser( TestPanel ):
    
    def __init__( self, parent, object_callable, pre_parsing_converter_callable, test_data = None ):
        
        self._pre_parsing_converter_callable = pre_parsing_converter_callable
        
        super().__init__( parent, object_callable, test_data = test_data )
        
        post_conversion_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_post_conversion_description = ClientGUICommon.BetterStaticText( post_conversion_panel )
        
        self._copy_button_post_conversion = ClientGUICommon.IconButton( post_conversion_panel, CC.global_icons().copy, self._CopyPostConversion )
        self._copy_button_post_conversion.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy the current post conversion data to the clipboard.' ) )
        
        self._refresh_post_conversion_button = ClientGUICommon.IconButton( post_conversion_panel, CC.global_icons().refresh, self._RefreshDataPreviews )
        self._example_data_post_conversion_preview = QW.QPlainTextEdit( post_conversion_panel )
        self._example_data_post_conversion_preview.setReadOnly( True )
        
        #
        
        self._example_data_post_conversion = ''
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_post_conversion_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button_post_conversion, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._refresh_post_conversion_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_post_conversion_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_conversion_panel.setLayout( vbox )
        
        #
        
        self._data_preview_notebook.addTab( post_conversion_panel, 'post pre-parsing conversion' )
        
    
    def _CopyPostConversion( self ):
        
        CG.client_controller.pub( 'clipboard', 'text', self._example_data_post_conversion )
        
    
    def _RefreshDataPreviews( self ):
        
        self._SetExampleData( self._example_data_raw )
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        TestPanel._SetExampleData( self, example_data, example_bytes = example_bytes )
        
        if len( self._example_data_raw ) > 0:
            
            pre_parsing_converter = self._pre_parsing_converter_callable()
            
            if pre_parsing_converter.MakesChanges():
                
                try:
                    
                    post_conversion_example_data = pre_parsing_converter.Convert( self._example_data_raw )
                    
                    if len( post_conversion_example_data ) > self.MAX_CHARS_IN_PREVIEW:
                        
                        preview = 'PREVIEW:' + '\n' + str( post_conversion_example_data[:self.MAX_CHARS_IN_PREVIEW] )
                        
                    else:
                        
                        preview = post_conversion_example_data
                        
                    
                    parse_phrase = 'uncertain data type'
                    
                    # can't just throw this at bs4 to see if it 'works', as it'll just wrap any unparsable string in some bare <html><body><p> tags
                    if HydrusText.LooksLikeHTML( post_conversion_example_data ):
                        
                        parse_phrase = 'looks like HTML'
                        
                    
                    # put this second, so if the JSON contains some HTML, it'll overwrite here. decent compromise
                    if HydrusText.LooksLikeJSON( example_data ):
                        
                        parse_phrase = 'looks like JSON'
                        
                    
                    description = HydrusData.ToHumanBytes( len( post_conversion_example_data ) ) + ' total, ' + parse_phrase
                    
                except Exception as e:
                    
                    post_conversion_example_data = self._example_data_raw
                    
                    etype = type( e )
                    
                    ( etype, value, tb ) = sys.exc_info()
                    
                    trace = ''.join( traceback.format_exception( etype, value, tb ) )
                    
                    message = 'Exception:' + '\n' + str( etype.__name__ ) + ': ' + str( e ) + '\n' + trace
                    
                    preview = message
                    
                    description = 'Could not convert.'
                    
                
            else:
                
                post_conversion_example_data = self._example_data_raw
                
                preview = 'No changes made.'
                
                description = self._example_data_raw_description.text()
                
            
        else:
            
            description = 'no example data set yet'
            preview = ''
            
            post_conversion_example_data = ''
            
        
        self._example_data_post_conversion_description.setText( description )
        
        self._example_data_post_conversion = post_conversion_example_data
        
        self._example_data_post_conversion_preview.setPlainText( preview )
        
    
    def GetTestDataForChild( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, ( self._example_data_post_conversion, ) )
        
    
class TestPanelPageParserSubsidiary( TestPanelPageParser ):
    
    def __init__( self, parent, object_callable, pre_parsing_converter_callable, subsidiary_parser_callable, test_data = None ):
        
        super().__init__( parent, object_callable, pre_parsing_converter_callable, test_data = test_data )
        
        self._subsidiary_parser_callable = subsidiary_parser_callable
        
        post_separation_panel = QW.QWidget( self._data_preview_notebook )
        
        self._example_data_post_separation_description = ClientGUICommon.BetterStaticText( post_separation_panel )
        
        self._copy_button_post_separation = ClientGUICommon.IconButton( post_separation_panel, CC.global_icons().copy, self._CopyPostSeparation )
        self._copy_button_post_separation.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy the current post separation data to the clipboard.' ) )
        
        self._refresh_post_separation_button = ClientGUICommon.IconButton( post_separation_panel, CC.global_icons().refresh, self._RefreshDataPreviews )
        self._example_data_post_separation_preview = QW.QPlainTextEdit( post_separation_panel )
        self._example_data_post_separation_preview.setReadOnly( True )
        
        #
        
        self._example_data_post_separation = []
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._example_data_post_separation_description, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button_post_separation, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._refresh_post_separation_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_data_post_separation_preview, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        post_separation_panel.setLayout( vbox )
        
        #
        
        self._data_preview_notebook.addTab( post_separation_panel, 'post separation' )
        
    
    def _CopyPostSeparation( self ):
        
        joiner = '\n' * 2
        
        CG.client_controller.pub( 'clipboard', 'text', joiner.join( self._example_data_post_separation ) )
        
    
    def _SetExampleData( self, example_data, example_bytes = None ):
        
        TestPanelPageParser._SetExampleData( self, example_data, example_bytes = example_bytes )
        
        if len( self._example_data_post_conversion ) > 0:
            
            subsidiary_parser = typing.cast( ClientParsing.SubsidiaryPageParser, self._subsidiary_parser_callable() )
            
            formula = subsidiary_parser.GetFormula()
            
            try:
                
                example_parsing_context = self._example_parsing_context.GetValue()
                
                separation_example_data = formula.Parse( example_parsing_context, self._example_data_post_conversion, self._collapse_newlines )
                
                joiner = '\n' * 2
                
                preview = joiner.join( separation_example_data )
                
                if len( preview ) > self.MAX_CHARS_IN_PREVIEW:
                    
                    preview = 'PREVIEW:' + '\n' + str( preview[:self.MAX_CHARS_IN_PREVIEW] )
                    
                
                description = HydrusNumbers.ToHumanInt( len( separation_example_data ) ) + ' subsidiary posts parsed'
                
            except Exception as e:
                
                separation_example_data = []
                
                etype = type( e )
                
                ( etype, value, tb ) = sys.exc_info()
                
                trace = ''.join( traceback.format_exception( etype, value, tb ) )
                
                message = 'Exception:' + '\n' + str( etype.__name__ ) + ': ' + str( e ) + '\n' + trace
                
                preview = message
                
                description = 'Could not convert.'
                
            
        else:
            
            description = 'nothing to parse'
            separation_example_data = ''
            
            preview = ''
            
        
        self._example_data_post_separation_description.setText( description )
        
        self._example_data_post_separation = separation_example_data
        
        self._example_data_post_separation_preview.setPlainText( preview )
        
    
    def GetTestDataForChild( self ):
        
        example_parsing_context = self._example_parsing_context.GetValue()
        
        return ClientParsing.ParsingTestData( example_parsing_context, list( self._example_data_post_separation ) )
        
    
    def TestParse( self ):
        
        subsidiary_parser = typing.cast( ClientParsing.SubsidiaryPageParser, self._subsidiary_parser_callable() )
        
        try:
            
            test_data = self.GetTestData()
            
            test_data.parsing_context[ 'post_index' ] = 0
            
            pretty_texts = []
            
            for text in test_data.texts:
                
                if len( text ) == 0:
                    
                    continue
                    
                
                pretty_text = subsidiary_parser.ParsePretty( test_data.parsing_context, text )
                
                pretty_texts.append( pretty_text )
                
            
            separator = '\n' * 2
            
            end_pretty_text = separator.join( pretty_texts )
            
            self._results.setPlainText( end_pretty_text )
            
        except Exception as e:
            
            etype = type( e )
            
            ( etype, value, tb ) = sys.exc_info()
            
            trace = ''.join( traceback.format_exception( etype, value, tb ) )
            
            message = 'Exception:' + '\n' + str( etype.__name__ ) + ': ' + str( e ) + '\n' + trace
            
            self._results.setPlainText( message )
            
        
    
    
