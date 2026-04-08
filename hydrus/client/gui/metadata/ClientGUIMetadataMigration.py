import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client import ClientTime
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationExporters
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationImporters
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationTest
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters
from hydrus.client.metadata import ClientTags
from hydrus.client.parsing import ClientParsing

class EditSingleFileMetadataRouterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, router: ClientMetadataMigration.SingleFileMetadataRouter, allowed_importer_classes: list, allowed_exporter_classes: list, test_context_factory: ClientGUIMetadataMigrationTest.MigrationTestContextFactory ):
        
        super().__init__( parent )
        
        self._original_router = router
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        self._test_context_factory = test_context_factory
        
        importers = self._original_router.GetImporters()
        string_processor = self._original_router.GetStringProcessor()
        exporter = self._original_router.GetExporter()
        
        #
        
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_SIDECARS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html sidecars help', 'Open the help page for sidecars in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding sidecars.' ) )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._importers_panel = ClientGUICommon.StaticBox( self, 'sources' )
        
        self._importers_list = ClientGUIMetadataMigrationImporters.SingleFileMetadataImportersControl( self._importers_panel, importers, self._allowed_importer_classes, self._test_context_factory )
        
        self._importers_panel.Add( self._importers_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( self._processing_panel, string_processor, self._GetExampleStringProcessorTestData )
        
        st = ClientGUICommon.BetterStaticText( self._processing_panel, 'You can alter all the texts before export here.' )
        
        self._processing_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._exporter_panel = ClientGUICommon.StaticBox( self, 'destination' )
        
        self._exporter_widget = ClientGUIMetadataMigrationExporters.EditSingleFileMetadataExporterWidget( self._exporter_panel, exporter, self._allowed_exporter_classes )
        
        self._exporter_panel.Add( self._exporter_widget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._test_panel = ClientGUICommon.StaticBox( self, 'testing' )
        
        self._test_panel_help_st = ClientGUICommon.BetterStaticText( self._test_panel, 'Add a source and this will show test data.' )
        self._test_notebook = ClientGUICommon.BetterNotebook( self._test_panel )
        
        #
        
        self._test_panel.Add( self._test_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._test_panel.Add( self._test_panel_help_st, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._importers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._exporter_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, vbox, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE )
        QP.AddToLayout( hbox, self._test_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( hbox )
        
        self._importers_list.listBoxChanged.connect( self._UpdateTestPanel )
        self._string_processor_button.valueChanged.connect( self._UpdateTestPanel )
        
        self._UpdateTestPanel()
        
    
    def _ConvertTestRowToDisplayTuple( self, test_row ):
        
        ( importer, test_object ) = test_row
        
        string_processor = self._string_processor_button.GetValue()
        
        test_object_pretty = self._test_context_factory.GetTestObjectString( test_object )
        importer_strings_output = sorted( self._test_context_factory.GetExampleTestStringsForTestObject( importer, test_object ) )
        
        if string_processor.MakesChanges():
            
            processed_strings_output = string_processor.ProcessStrings( importer_strings_output )
            
        else:
            
            processed_strings_output = [ 'no changes' ]
            
        
        pretty_importer_strings_output = ', '.join( importer_strings_output )
        pretty_processed_strings_output = ', '.join( processed_strings_output )
        
        display_tuple = ( test_object_pretty, pretty_importer_strings_output, pretty_processed_strings_output )
        
        return display_tuple
        
    
    def _ConvertTestRowToSortTuple( self, test_row ):
        
        ( importer, test_object ) = test_row
        
        string_processor = self._string_processor_button.GetValue()
        
        test_object_pretty = self._test_context_factory.GetTestObjectString( test_object )
        importer_strings_output = sorted( self._test_context_factory.GetExampleTestStringsForTestObject( importer, test_object ) )
        
        if string_processor.MakesChanges():
            
            processed_strings_output = string_processor.ProcessStrings( importer_strings_output )
            
        else:
            
            processed_strings_output = [ 'no changes' ]
            
        
        sort_tuple = ( test_object_pretty, len( importer_strings_output ), len( processed_strings_output ) )
        
        return sort_tuple
        
    
    def _GetExampleStringProcessorTestData( self ):
        
        example_parsing_context = dict()
        
        importers = self._importers_list.GetData()
        
        test_objects = self._test_context_factory.GetTestObjects()
        
        texts = []
        
        for importer in importers:
            
            texts.extend( self._test_context_factory.GetExampleTestStrings( importer ) )
            
        
        return ClientParsing.ParsingTestData( example_parsing_context, texts )
        
    
    def _GetValue( self ) -> ClientMetadataMigration.SingleFileMetadataRouter:
        
        importers = self._importers_list.GetData()
        
        string_processor = self._string_processor_button.GetValue()
        
        exporter = self._exporter_widget.GetValue()
        
        router = ClientMetadataMigration.SingleFileMetadataRouter( importers = importers, string_processor = string_processor, exporter = exporter )
        
        return router
        
    
    def _UpdateTestPanel( self ):
        
        importers = self._importers_list.GetData()
        
        while self._test_notebook.count() > len( importers ):
            
            last_page_index = self._test_notebook.count() - 1
            
            page = self._test_notebook.widget( last_page_index )
            
            self._test_notebook.removeTab( last_page_index )
            
            page.deleteLater()
            
        
        we_got_importers = len( self._importers_list.GetData() ) > 0
        
        self._test_notebook.setVisible( we_got_importers )
        self._test_panel_help_st.setVisible( not we_got_importers )
        
        for ( i, importer ) in enumerate( self._importers_list.GetData() ):
            
            if self._test_notebook.count() < i + 1:
                
                model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_METADATA_ROUTER_TEST_RESULTS.ID, self._ConvertTestRowToDisplayTuple, self._ConvertTestRowToSortTuple )
                
                list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._test_notebook, 12, model )
                
                self._test_notebook.addTab( list_ctrl, 'init' )
                
            
            page_name = HydrusText.ElideText( HydrusNumbers.IndexToPrettyOrdinalString( i ), 14 )
            
            self._test_notebook.setTabText( i, page_name )
            
            list_ctrl: ClientGUIListCtrl.BetterListCtrlTreeView = self._test_notebook.widget( i )
            
            test_objects = self._test_context_factory.GetTestObjects()
            
            list_ctrl.SetData( [ ( importer, test_object ) for test_object in test_objects ] )
            
        
        self._test_notebook.tabBar().setVisible( self._test_notebook.count() > 1 )
        
    
    def GetValue( self ) -> ClientMetadataMigration.SingleFileMetadataRouter:
        
        router = self._GetValue()
        
        return router
        
    
    def UserIsOKToOK( self ):
        
        router = self._GetValue()
        
        importers = router.GetImporters()
        exporter = router.GetExporter()
        
        if True in ( isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaNotes ) for importer in importers ) and isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT ):
            
            if exporter.GetSeparator() == '\n':
                
                message = 'Hey, you are exporing notes to a .txt file but have selected a "newline" separator to split multiple notes. This will break any notes that have multiple lines--are you sure you do not want to select "||||" (or something else unlikely to appear in your note text) as your separator instead? Another option is to export to JSON instead.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return False
                    
                
            
        
        if True in ( isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT ) for importer in importers ) and isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes ):
            
            txt_importers = [ importer for importer in importers if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT ) ]
            
            if True in ( txt_importer.GetSeparator() == '\n' for txt_importer in txt_importers ):
                
                message = 'Hey, you are importing notes from a .txt file but have selected the "newline" separator to specify where multiple notes split. If any of your notes have multiple lines, they will be broken by this! Are you sure this is how the notes in the .txt are formatted, with a newline separator? If you created these sidecars, it would be better if you used a different separator like "||||" or just went for JSON instead. Are you sure you want to go ahead?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return False
                    
                
            
        
        return True
        
    

def convert_router_to_pretty_string( router: ClientMetadataMigration.SingleFileMetadataRouter ) -> str:
    
    return router.ToString( pretty = True )
    

class SingleFileMetadataRoutersControl( ClientGUIListBoxes.AddEditDeleteListBox ):
    
    def __init__( self, parent: QW.QWidget, routers: collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list, test_context_factory: ClientGUIMetadataMigrationTest.MigrationTestContextFactory ):
        
        super().__init__( parent, 5, convert_router_to_pretty_string, self._AddRouter, self._EditRouter )
        
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        self._test_context_factory = test_context_factory
        
        self.AddDatas( routers )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 64 )
        
        self.setMinimumWidth( width )
        
        self.AddImportExportButtons( ( ClientMetadataMigration.SingleFileMetadataRouter, ) )
        
        #
        
        jobs = []
        
        if ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON in allowed_exporter_classes:
            
            template_routers = []
            
            if ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaNotes in allowed_importer_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaNotes() ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'notes' ] )
                    )
                )
                
            
            if ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs in allowed_importer_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs() ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'urls' ] )
                    )
                )
                
            
            if ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags in allowed_importer_classes:
                
                for tag_service in CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ):
                    
                    template_routers.append(
                        ClientMetadataMigration.SingleFileMetadataRouter(
                            importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = tag_service.GetServiceKey(), tag_display_type = ClientTags.TAG_DISPLAY_STORAGE ) ],
                            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'tags', 'storage', tag_service.GetName() ] )
                        )
                    )
                    
                    template_routers.append(
                        ClientMetadataMigration.SingleFileMetadataRouter(
                            importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( service_key = tag_service.GetServiceKey(), tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ],
                            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'tags', 'display', tag_service.GetName() ] )
                        )
                    )
                    
                
            
            # timestamps
            
            if ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps in allowed_importer_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_ARCHIVED ) ) ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'times', 'archived' ] )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_IMPORTED, location = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) ) ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'times', 'imported' ] )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_MEDIA_VIEWER ) ) ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'times', 'last_viewed_media_viewer' ] )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_PREVIEW ) ) ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( nested_object_names = [ 'times', 'last_viewed_preview_viewer' ] )
                    )
                )
                
            
            if len( template_routers ) > 0:
                
                jobs.append( ( 'easy one-click JSON that covers the basics', 'this will export all notes, urls, tags, and basic times as they are currently defined', template_routers ) )
                
            
        
        if ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON in allowed_importer_classes:
            
            template_routers = []
            
            if ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes in allowed_exporter_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'notes' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes()
                    )
                )
                
            
            if ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs in allowed_exporter_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'urls' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs()
                    )
                )
                
            
            if ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags in allowed_exporter_classes:
                
                for tag_service in CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ):
                    
                    template_routers.append(
                        ClientMetadataMigration.SingleFileMetadataRouter(
                            importers = [
                                ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                    json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                        parse_rules = [
                                            ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'tags' ) ),
                                            ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'storage' ) ),
                                            ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = tag_service.GetName() ) ),
                                            ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                        ],
                                        content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                    )
                                )
                            ],
                            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key = tag_service.GetServiceKey() )
                        )
                    )
                    
                
            
            # timestamps
            
            if ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps in allowed_exporter_classes:
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'times' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'archived' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData.STATICSimpleStub( HC.TIMESTAMP_TYPE_ARCHIVED ) )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'times' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'imported' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_IMPORTED, location = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'times' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'last_viewed_media_viewer' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_MEDIA_VIEWER ) )
                    )
                )
                
                template_routers.append(
                    ClientMetadataMigration.SingleFileMetadataRouter(
                        importers = [
                            ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON(
                                json_parsing_formula = ClientParsing.ParseFormulaJSON(
                                    parse_rules = [
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'times' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'last_viewed_preview_viewer' ) ),
                                        ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                                    ],
                                    content_to_fetch = ClientParsing.JSON_CONTENT_STRING
                                )
                            )
                        ],
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps( timestamp_data_stub = ClientTime.TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_PREVIEW ) )
                    )
                )
                
            
            if len( template_routers ) > 0:
                
                jobs.append( ( 'easy one-click JSON that covers the basics', 'this will import all notes, urls, tags, and basic times as they are currently defined. it will match the easy-export JSON and if tag service names match up, tags will work too', template_routers ) )
                
            
        
        if len( jobs ) > 0:
            
            menu_template_items = [ ClientGUIMenuButton.MenuTemplateItemCall( label, description, self.AddDatas, templates ) for ( label, description, templates ) in jobs ]
            
            #
            
            self._templates_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().star, menu_template_items )
            
            QP.AddToLayout( self._buttons_hbox, self._templates_button, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
    
    def _AddRouter( self ):
        
        exporter = self._allowed_exporter_classes[0]()
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
            
            if not CG.client_controller.services_manager.ServiceExists( exporter.GetServiceKey() ):
                
                exporter.SetServiceKey( CG.client_controller.services_manager.GetDefaultLocalTagService().GetServiceKey() )
                
            
        
        router = ClientMetadataMigration.SingleFileMetadataRouter( exporter = exporter )
        
        return self._EditRouter( router )
        
    
    def _CheckImportObjectCustom( self, router: ClientMetadataMigration.SingleFileMetadataRouter ):
        
        exporter = router.GetExporter()
        
        router_is_exporting_to_sidecars = isinstance( router.GetExporter(), ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar )
        i_am_exporting_to_sidecars = True in ( issubclass( c, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ) for c in self._allowed_exporter_classes )
        
        if router_is_exporting_to_sidecars != i_am_exporting_to_sidecars:
            
            if i_am_exporting_to_sidecars:
                
                message = 'I take routers that export to sidecars, these new router(s) import from them!'
                
            else:
                
                message = 'I take routers that import from sidecars, these new router(s) export to them!'
                
            
            raise HydrusExceptions.VetoException( message )
            
        
        if not isinstance( exporter, tuple( self._allowed_exporter_classes ) ):
            
            raise HydrusExceptions.VetoException( 'Exporter was {}, I only allow {}.'.format( type( exporter ).__name__, [ c.__name__ for c in self._allowed_exporter_classes ] ) )
            
        
        for importer in router.GetImporters():
            
            if not isinstance( importer, tuple( self._allowed_importer_classes ) ):
                
                raise HydrusExceptions.VetoException( 'Importer was {}, I only allow {}.'.format( type( importer ).__name__, [ c.__name__ for c in self._allowed_importer_classes ] ) )
                
            
        
    
    def _EditRouter( self, router: ClientMetadataMigration.SingleFileMetadataRouter ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration router' ) as dlg:
            
            panel = EditSingleFileMetadataRouterPanel( self, router, self._allowed_importer_classes, self._allowed_exporter_classes, self._test_context_factory )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_router = panel.GetValue()
                
                return edited_router
                
            
        
        raise HydrusExceptions.VetoException()
        
    

class SingleFileMetadataRoutersButton( QW.QPushButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, routers: collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list, test_context_factory: ClientGUIMetadataMigrationTest.MigrationTestContextFactory ):
        
        super().__init__( parent )
        
        self._routers = routers
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        self._test_context_factory = test_context_factory
        
        self._RefreshLabel()
        
        self.clicked.connect( self._Edit )
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration routers' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = SingleFileMetadataRoutersControl( panel, self._routers, self._allowed_importer_classes, self._allowed_exporter_classes, self._test_context_factory )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                value = control.GetData()
                
                self.SetValue( value )
                
                self.valueChanged.emit()
                
            
        
    
    def _RefreshLabel( self ):
        
        if len( self._routers ) == 0:
            
            text = 'no sidecars'
            
        elif len( self._routers ) == 1:
            
            ( router, ) = self._routers
            
            text = router.ToString( pretty = True )
            
        else:
            
            text = '{} sidecar actions'.format( HydrusNumbers.ToHumanInt( len( self._routers ) ) )
            
        
        elided_text = HydrusText.ElideText( text, 64 )
        
        self.setText( elided_text )
        self.setToolTip( ClientGUIFunctions.WrapToolTip( text ) )
        
    
    def GetValue( self ):
        
        return self._routers
        
    
    def SetValue( self, routers: collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ):
        
        self._routers = routers
        
        self._RefreshLabel()
        
    
