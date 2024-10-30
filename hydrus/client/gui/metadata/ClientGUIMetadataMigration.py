import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientParsing
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
        
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_SIDECARS )
        
        menu_items.append( ( 'normal', 'open the html sidecars help', 'Open the help page for sidecars in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding sidecars.' ) )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._importers_panel = ClientGUICommon.StaticBox( self, 'sources' )
        
        self._importers_list = ClientGUIMetadataMigrationImporters.SingleFileMetadataImportersControl( self._importers_panel, importers, self._allowed_importer_classes )
        
        self._importers_panel.Add( self._importers_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorWidget( self._processing_panel, string_processor, self._GetExampleStringProcessorTestData )
        
        st = ClientGUICommon.BetterStaticText( self._processing_panel, 'You can alter all the texts before export here.' )
        
        self._processing_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._exporter_panel = ClientGUICommon.StaticBox( self, 'destination' )
        
        self._exporter_button = ClientGUIMetadataMigrationExporters.EditSingleFileMetadataExporterPanel( self._exporter_panel, exporter, self._allowed_exporter_classes )
        
        self._exporter_panel.Add( self._exporter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
        importer_strings_output = sorted( self._test_context_factory.GetExampleTestStrings( importer, test_object ) )
        
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
        importer_strings_output = sorted( self._test_context_factory.GetExampleTestStrings( importer, test_object ) )
        
        if string_processor.MakesChanges():
            
            processed_strings_output = string_processor.ProcessStrings( importer_strings_output )
            
        else:
            
            processed_strings_output = [ 'no changes' ]
            
        
        sort_tuple = ( test_object_pretty, len( importer_strings_output ), len( processed_strings_output ) )
        
        return sort_tuple
        
    
    def _GetExampleStringProcessorTestData( self ):
        
        example_parsing_context = dict()
        
        importers = self._importers_list.GetData()
        
        exporter = self._exporter_button.GetValue()
        
        texts = set()
        
        for importer in importers:
            
            texts.update( importer.GetExampleStrings() )
            
        
        texts.update( exporter.GetExampleStrings() )
        
        texts = sorted( texts )
        
        return ClientParsing.ParsingTestData( example_parsing_context, texts )
        
    
    def _GetValue( self ) -> ClientMetadataMigration.SingleFileMetadataRouter:
        
        importers = self._importers_list.GetData()
        
        string_processor = self._string_processor_button.GetValue()
        
        exporter = self._exporter_button.GetValue()
        
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
                
                list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._test_notebook, CGLC.COLUMN_LIST_METADATA_ROUTER_TEST_RESULTS.ID, 11, model )
                
                self._test_notebook.addTab( list_ctrl, 'init' )
                
            
            page_name = HydrusText.ElideText( HydrusNumbers.IndexToPrettyOrdinalString( i ), 14 )
            
            self._test_notebook.setTabText( i, page_name )
            
            list_ctrl = self._test_notebook.widget( i )
            
            test_objects = self._test_context_factory.GetTestObjects()
            
            list_ctrl.SetData( [ ( importer, test_object ) for test_object in test_objects ] )
            
        
        self._test_notebook.tabBar().setVisible( self._test_notebook.count() > 1 )
        
    
    def GetValue( self ) -> ClientMetadataMigration.SingleFileMetadataRouter:
        
        router = self._GetValue()
        
        return router
        
    

def convert_router_to_pretty_string( router: ClientMetadataMigration.SingleFileMetadataRouter ) -> str:
    
    return router.ToString( pretty = True )
    

class SingleFileMetadataRoutersControl( ClientGUIListBoxes.AddEditDeleteListBox ):
    
    def __init__( self, parent: QW.QWidget, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list, test_context_factory: ClientGUIMetadataMigrationTest.MigrationTestContextFactory ):
        
        super().__init__( parent, 5, convert_router_to_pretty_string, self._AddRouter, self._EditRouter )
        
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        self._test_context_factory = test_context_factory
        
        self.AddDatas( routers )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 64 )
        
        self.setMinimumWidth( width )
        
        self.AddImportExportButtons( ( ClientMetadataMigration.SingleFileMetadataRouter, ) )
        
    
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_router = panel.GetValue()
                
                return edited_router
                
            
        
        raise HydrusExceptions.VetoException()
        
    

class SingleFileMetadataRoutersButton( QW.QPushButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list, test_context_factory: ClientGUIMetadataMigrationTest.MigrationTestContextFactory ):
        
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
        
    
    def SetValue( self, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ):
        
        self._routers = routers
        
        self._RefreshLabel()
        
    
