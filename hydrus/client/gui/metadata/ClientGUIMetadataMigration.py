import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientParsing
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationExporters
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationImporters
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters

class EditSingleFileMetadataRouterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, router: ClientMetadataMigration.SingleFileMetadataRouter, allowed_importer_classes: list, allowed_exporter_classes: list ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_router = router
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        
        importers = self._original_router.GetImporters()
        string_processor = self._original_router.GetStringProcessor()
        exporter = self._original_router.GetExporter()
        
        #
        
        self._importers_panel = ClientGUICommon.StaticBox( self, 'sources' )
        
        self._importers_list = ClientGUIMetadataMigrationImporters.SingleFileMetadataImportersControl( self._importers_panel, importers, self._allowed_importer_classes )
        
        self._importers_panel.Add( self._importers_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( self._processing_panel, string_processor, self._GetExampleStringProcessorTestData )
        
        st = ClientGUICommon.BetterStaticText( self._processing_panel, 'You can alter all the texts before export here.' )
        
        self._processing_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._processing_panel.Add( self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._exporter_panel = ClientGUICommon.StaticBox( self, 'destination' )
        
        self._exporter_button = ClientGUIMetadataMigrationExporters.EditSingleFileMetadataExporterPanel( self._exporter_panel, exporter, self._allowed_exporter_classes )
        
        self._exporter_panel.Add( self._exporter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._importers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._exporter_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
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
        
    
    def GetValue( self ) -> ClientMetadataMigration.SingleFileMetadataRouter:
        
        router = self._GetValue()
        
        return router
        
    

def convert_router_to_pretty_string( router: ClientMetadataMigration.SingleFileMetadataRouter ) -> str:
    
    return router.ToString( pretty = True )
    

class SingleFileMetadataRoutersControl( ClientGUIListBoxes.AddEditDeleteListBox ):
    
    def __init__( self, parent: QW.QWidget, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list ):
        
        ClientGUIListBoxes.AddEditDeleteListBox.__init__( self, parent, 5, convert_router_to_pretty_string, self._AddRouter, self._EditRouter )
        
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        
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
            
            panel = EditSingleFileMetadataRouterPanel( self, router, self._allowed_importer_classes, self._allowed_exporter_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_router = panel.GetValue()
                
                return edited_router
                
            
        
        raise HydrusExceptions.VetoException()
        
    

class SingleFileMetadataRoutersButton( QW.QPushButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], allowed_importer_classes: list, allowed_exporter_classes: list ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._routers = routers
        self._allowed_importer_classes = allowed_importer_classes
        self._allowed_exporter_classes = allowed_exporter_classes
        
        self._RefreshLabel()
        
        self.clicked.connect( self._Edit )
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration routers' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = SingleFileMetadataRoutersControl( panel, self._routers, self._allowed_importer_classes, self._allowed_exporter_classes )
            
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
            
            text = '{} sidecar actions'.format( HydrusData.ToHumanInt( len( self._routers ) ) )
            
        
        elided_text = HydrusText.ElideText( text, 64 )
        
        self.setText( elided_text )
        self.setToolTip( text )
        
    
    def GetValue( self ):
        
        return self._routers
        
    
    def SetValue( self, routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ):
        
        self._routers = routers
        
        self._RefreshLabel()
        
    
