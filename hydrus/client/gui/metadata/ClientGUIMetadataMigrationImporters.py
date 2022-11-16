import json
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientParsing
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationCommon
from hydrus.client.gui.parsing import ClientGUIParsingFormulae
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataMigrationImporters

choice_tuple_label_lookup = {
    ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags : 'a file\'s tags',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs : 'a file\'s URLs',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT : 'a .txt sidecar',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON : 'a .json sidecar'
}

choice_tuple_description_lookup = {
    ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags : 'The tags that a file has on a particular service.',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs : 'The known URLs that a file has.',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT : 'A list of raw newline-separated texts in a .txt file.',
    ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON : 'Strings somewhere in a JSON file.'
}

def SelectClass( win: QW.QWidget, allowed_importer_classes: list ):
    
    choice_tuples = [ ( choice_tuple_label_lookup[ c ], c, choice_tuple_description_lookup[ c ] ) for c in allowed_importer_classes ]
    
    message = 'Which kind of source are we going to use?'
    
    importer_class = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Which type?', choice_tuples, message = message )
    
    return importer_class
    

class EditSingleFileMetadataImporterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter, allowed_importer_classes: list ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_importer = importer
        self._allowed_importer_classes = allowed_importer_classes
        
        self._current_importer_class = type( importer )
        self._service_key = CC.COMBINED_TAG_SERVICE_KEY
        self._json_parsing_formula = ClientParsing.ParseFormulaJSON()
        
        string_processor = importer.GetStringProcessor()
        
        #
        
        self._change_type_button = ClientGUICommon.BetterButton( self, 'change type', self._ChangeType )
        
        #
        
        self._service_selection_panel = QW.QWidget( self )
        
        self._service_selection_button = ClientGUICommon.BetterButton( self, 'service', self._SelectService )
        
        hbox = ClientGUICommon.WrapInText( self._service_selection_button, self._service_selection_panel, 'tag service: ' )
        
        self._service_selection_panel.setLayout( hbox )
        
        #
        
        self._json_parsing_formula_panel = QW.QWidget( self )
        
        self._json_parsing_formula_button = ClientGUICommon.BetterButton( self, 'edit parsing formula', self._EditJSONParsingFormula )
        
        hbox = ClientGUICommon.WrapInText( self._json_parsing_formula_button, self._json_parsing_formula_panel, 'json parsing formula: ' )
        
        self._json_parsing_formula_panel.setLayout( hbox )
        
        #
        
        self._sidecar_panel = ClientGUIMetadataMigrationCommon.EditSidecarDetailsPanel( self )
        
        #
        
        self._string_processor_panel = QW.QWidget( self )
        
        self._string_processor_button = ClientGUIStringControls.StringProcessorButton( self, string_processor, self._GetExampleTestData )
        tt = 'You can alter the texts that come in through this source here.'
        self._string_processor_button.setToolTip( tt )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self._string_processor_panel, 'You can alter the texts that come in through this source here.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._string_processor_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._string_processor_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._change_type_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._service_selection_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._json_parsing_formula_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sidecar_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._string_processor_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        self._SetValue( importer )
        
    
    def _ChangeType( self ):
        
        allowed_importer_classes = list( self._allowed_importer_classes )
        if self._current_importer_class in allowed_importer_classes:
            
            allowed_importer_classes.remove( self._current_importer_class )
            
        
        if len( allowed_importer_classes ) == 0:
            
            message = 'Sorry, you can only have this one!'
            
            QW.QMessageBox.information( self, 'Information', message )
            
        
        try:
            
            importer_class = SelectClass( self, allowed_importer_classes )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        string_processor = self._string_processor_button.GetValue()
        
        importer = importer_class( string_processor )
        
        # it is nice to preserve old values as we flip from one type to another. more pleasant that making the user cancel and re-open
        
        if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar ):
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            
            importer.SetRemoveActualFilenameExt( remove_actual_filename_ext )
            importer.SetSuffix( suffix )
            importer.SetFilenameStringConverter( filename_string_converter )
            
        
        if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags ):
            
            importer.SetServiceKey( self._service_key )
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs ):
            
            pass
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT ):
            
            pass
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON ):
            
            importer.SetJSONParsingFormula( self._json_parsing_formula )
            
        
        self._SetValue( importer )
        
    
    def _EditJSONParsingFormula( self ):
        
        test_data = self._GetExampleTestData()
        
        dlg_title = 'edit formula'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, dlg_title, frame_key = 'deeply_nested_dialog' ) as dlg:
            
            collapse_newlines = False
            
            panel = ClientGUIParsingFormulae.EditJSONFormulaPanel( dlg, collapse_newlines, self._json_parsing_formula, test_data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._json_parsing_formula = panel.GetValue()
                
            
        
    
    def _GetExampleTestData( self ):
        
        example_parsing_context = dict()
        
        importer = self._GetValue()
        
        texts = sorted( importer.GetExampleStrings() )
        
        return ClientParsing.ParsingTestData( example_parsing_context, [ json.dumps( texts ) ] )
        
    
    def _GetValue( self ) -> ClientMetadataMigrationImporters.SingleFileMetadataImporter:
        
        string_processor = self._string_processor_button.GetValue()
        
        if self._current_importer_class == ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags:
            
            importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags( string_processor = string_processor, service_key = self._service_key )
            
        elif self._current_importer_class == ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs:
            
            importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs( string_processor = string_processor )
            
        elif self._current_importer_class == ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT:
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            
            importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT( string_processor = string_processor, remove_actual_filename_ext = remove_actual_filename_ext, suffix = suffix, filename_string_converter = filename_string_converter )
            
        elif self._current_importer_class == ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON:
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            
            importer = ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON( string_processor = string_processor, remove_actual_filename_ext = remove_actual_filename_ext, suffix = suffix, filename_string_converter = filename_string_converter, json_parsing_formula = self._json_parsing_formula )
            
        else:
            
            raise Exception( 'Did not understand the current importer type!' )
            
        
        return importer
        
    
    def _SelectService( self ):
        
        service_key = ClientGUIDialogsQuick.SelectServiceKey( service_types = HC.ALL_TAG_SERVICES, unallowed = [ self._service_key ] )
        
        if service_key is None:
            
            return
            
        
        self._service_key = service_key
        
        self._UpdateServiceKeyButtonLabel()
        
    
    def _SetValue( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter ):
        
        self._current_importer_class = type( importer )
        
        self._change_type_button.setText( choice_tuple_label_lookup[ self._current_importer_class ] )
        
        string_processor = importer.GetStringProcessor()
        
        self._string_processor_button.SetValue( string_processor )
        
        self._service_selection_panel.setVisible( False )
        self._json_parsing_formula_panel.setVisible( False )
        self._sidecar_panel.setVisible( False )
        
        if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterSidecar ):
            
            remove_actual_filename_ext = importer.GetRemoveActualFilenameExt()
            suffix = importer.GetSuffix()
            filename_string_converter = importer.GetFilenameStringConverter()
            
            self._sidecar_panel.SetRemoveActualFilenameExt( remove_actual_filename_ext )
            self._sidecar_panel.SetSuffix( suffix )
            self._sidecar_panel.SetFilenameStringConverter( filename_string_converter )
            
            self._sidecar_panel.setVisible( True )
            
        
        if isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaTags ):
            
            self._service_key = importer.GetServiceKey()
            
            self._UpdateServiceKeyButtonLabel()
            
            self._service_selection_panel.setVisible( True )
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterMediaURLs ):
            
            pass
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT ):
            
            self._sidecar_panel.SetSidecarExt( 'txt' )
            self._sidecar_panel.SetExampleInput( 'my_image.jpg' )
            
        elif isinstance( importer, ClientMetadataMigrationImporters.SingleFileMetadataImporterJSON ):
            
            self._sidecar_panel.SetSidecarExt( 'json' )
            self._sidecar_panel.SetExampleInput( 'my_image.jpg' )
            
            self._json_parsing_formula = importer.GetJSONParsingFormula()
            
            self._json_parsing_formula_panel.setVisible( True )
            
        else:
            
            raise Exception( 'Did not understand the new importer type!' )
            
        
    
    def _UpdateServiceKeyButtonLabel( self ):
        
        try:
            
            name = HG.client_controller.services_manager.GetName( self._service_key )
            
        except HydrusExceptions.DataMissing:
            
            name = 'unknown'
            
        
        self._service_selection_button.setText( name )
        
    
    def GetValue( self ) -> ClientMetadataMigrationImporters.SingleFileMetadataImporter:
        
        importer = self._GetValue()
        
        return importer
        
    

def convert_importer_to_pretty_string( importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter ) -> str:
    
    return importer.ToString()
    

class SingleFileMetadataImportersControl( ClientGUIListBoxes.AddEditDeleteListBox ):
    
    def __init__( self, parent: QW.QWidget, importers: typing.Collection[ ClientMetadataMigrationImporters.SingleFileMetadataImporter ], allowed_importer_classes: list ):
        
        ClientGUIListBoxes.AddEditDeleteListBox.__init__( self, parent, 5, convert_importer_to_pretty_string, self._AddImporter, self._EditImporter )
        
        self._allowed_importer_classes = allowed_importer_classes
        
        self.AddDatas( importers )
        
    
    def _AddImporter( self ):
        
        try:
            
            importer_class = SelectClass( self, self._allowed_importer_classes )
            
        except HydrusExceptions.CancelledException:
            
            raise HydrusExceptions.VetoException()
            
        
        string_processor = ClientStrings.StringProcessor()
        
        importer = importer_class( string_processor )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration source' ) as dlg:
            
            panel = EditSingleFileMetadataImporterPanel( self, importer, self._allowed_importer_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                importer = panel.GetValue()
                
                return importer
                
            
        
        raise HydrusExceptions.VetoException()
        
    
    def _EditImporter( self, importer: ClientMetadataMigrationImporters.SingleFileMetadataImporter ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration source' ) as dlg:
            
            panel = EditSingleFileMetadataImporterPanel( self, importer, self._allowed_importer_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_importer = panel.GetValue()
                
                return edited_importer
                
            
        
        raise HydrusExceptions.VetoException()
        
    
