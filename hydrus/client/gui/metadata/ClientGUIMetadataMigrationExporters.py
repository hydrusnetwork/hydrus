import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientParsing
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataMigrationExporters

choice_tuple_label_lookup = {
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags : 'a file\'s tags',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs : 'a file\'s URLs',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT : 'a .txt sidecar',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON : 'a .json sidecar'
}

choice_tuple_description_lookup = {
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags : 'The tags that a file has on a particular service.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs : 'The known URLs that a file has.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT : 'A list of raw newline-separated texts in a .txt file.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON : 'Strings somewhere in a JSON file.'
}

def SelectClass( win: QW.QWidget, allowed_exporter_classes: list ):
    
    choice_tuples = [ ( choice_tuple_label_lookup[ c ], c, choice_tuple_description_lookup[ c ] ) for c in allowed_exporter_classes ]
    
    message = 'Which kind of destination are we going to use?'
    
    exporter_class = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Which type?', choice_tuples, message = message )
    
    return exporter_class
    

class EditSingleFileMetadataExporterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, exporter: ClientMetadataMigrationExporters.SingleFileMetadataExporter, allowed_exporter_classes: list ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_exporter = exporter
        self._allowed_exporter_classes = allowed_exporter_classes
        
        self._current_exporter_class = type( exporter )
        self._service_key = CC.COMBINED_TAG_SERVICE_KEY
        
        #
        
        self._change_type_button = ClientGUICommon.BetterButton( self, 'change type', self._ChangeType )
        
        #
        
        self._service_selection_panel = QW.QWidget( self )
        
        self._service_selection_button = ClientGUICommon.BetterButton( self._service_selection_panel, 'service', self._SelectService )
        
        hbox = ClientGUICommon.WrapInText( self._service_selection_button, self._service_selection_panel, 'tag service: ' )
        
        self._service_selection_panel.setLayout( hbox )
        
        #
        
        self._sidecar_help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowSidecarHelp )
        
        self._nested_object_names_panel = QW.QWidget( self )
        
        self._nested_object_names_list = ClientGUIListBoxes.QueueListBox( self, 4, str, self._AddObjectName, self._EditObjectName )
        tt = 'If you leave this empty, the strings will be exported as a simple list. If you set it as [files,tags], the exported string list will be placed under nested objects with keys "files"->"tags". Note that this will also update an existing file, so, if you are feeling clever, you can have multiple routers writing tags and URLs to different destinations in the same file!'
        self._nested_object_names_list.setToolTip( tt )
        
        vbox = QP.VBoxLayout()
        
        message = 'JSON Objects structure'
        
        st = ClientGUICommon.BetterStaticText( self._nested_object_names_panel, message )
        
        st.setToolTip( self._nested_object_names_list.toolTip() )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._nested_object_names_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._nested_object_names_panel.setLayout( vbox )
        
        #
        
        self._suffix_panel = QW.QWidget( self )
        
        self._suffix = QW.QLineEdit( self )
        tt = 'If you set this to "tags", the exported filename will be (file filename).tags.ext, where ext is .txt/.json/.xml etc... . Leave blank to just export to (file filename).ext.'
        self._suffix.setToolTip( tt )
        
        hbox = ClientGUICommon.WrapInText( self._suffix, self._suffix_panel, 'filename suffix: ' )
        
        self._suffix_panel.setLayout( hbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._change_type_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._service_selection_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sidecar_help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._nested_object_names_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._suffix_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        self._SetValue( exporter )
        
    
    def _AddObjectName( self ):
        
        object_name = ''
        
        return self._EditObjectName( object_name )
        
    
    def _ChangeType( self ):
        
        allowed_exporter_classes = list( self._allowed_exporter_classes )
        if self._current_exporter_class in allowed_exporter_classes:
            
            allowed_exporter_classes.remove( self._current_exporter_class )
            
        
        if len( allowed_exporter_classes ) == 0:
            
            message = 'Sorry, you can only have this one!'
            
            QW.QMessageBox.information( self, 'Information', message )
            
        
        try:
            
            exporter_class = SelectClass( self, allowed_exporter_classes )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        exporter = exporter_class()
        
        # it is nice to preserve old values as we flip from one type to another. more pleasant that making the user cancel and re-open
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
            
            exporter.SetServiceKey( self._service_key )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs ):
            
            pass
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT ):
            
            exporter.SetSuffix( self._suffix.text() )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ):
            
            exporter.SetSuffix( self._suffix.text() )
            
            exporter.SetNestedObjectNames( self._nested_object_names_list.GetData() )
            
        
        self._SetValue( exporter )
        
    
    def _EditObjectName( self, object_name ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the JSON Object name', default = object_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                object_name = dlg.GetValue()
                
                return object_name
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _GetExampleTestData( self ):
        
        example_parsing_context = dict()
        
        exporter = self._GetValue()
        
        texts = sorted( exporter.GetExampleStrings() )
        
        return ClientParsing.ParsingTestData( example_parsing_context, texts )
        
    
    def _GetValue( self ) -> ClientMetadataMigrationExporters.SingleFileMetadataExporter:
        
        if self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key = self._service_key )
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs()
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT:
            
            suffix = self._suffix.text()
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT( suffix = suffix )
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON:
            
            suffix = self._suffix.text()
            
            nested_object_names = self._nested_object_names_list.GetData()
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( suffix = suffix, nested_object_names = nested_object_names )
            
        else:
            
            raise Exception( 'Did not understand the current exporter type!' )
            
        
        return exporter
        
    
    def _SelectService( self ):
        
        service_key = ClientGUIDialogsQuick.SelectServiceKey( service_types = HC.ALL_TAG_SERVICES, unallowed = [ self._service_key ] )
        
        if service_key is None:
            
            return
            
        
        self._service_key = service_key
        
        self._UpdateServiceKeyButtonLabel()
        
    
    def _SetValue( self, exporter: ClientMetadataMigrationExporters.SingleFileMetadataExporter ):
        
        self._current_exporter_class = type( exporter )
        
        self._change_type_button.setText( choice_tuple_label_lookup[ self._current_exporter_class ] )
        
        self._service_selection_panel.setVisible( False )
        self._sidecar_help_button.setVisible( False )
        self._nested_object_names_panel.setVisible( False )
        self._suffix_panel.setVisible( False )
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
            
            self._service_key = exporter.GetServiceKey()
            
            self._UpdateServiceKeyButtonLabel()
            
            self._service_selection_panel.setVisible( True )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs ):
            
            pass
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ):
            
            self._sidecar_help_button.setVisible( True )
            
            suffix = exporter.GetSuffix()
            
            self._suffix.setText( suffix )
            
            self._suffix_panel.setVisible( True )
            
            if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ):
                
                nested_object_names = exporter.GetNestedObjectNames()
                
                self._nested_object_names_list.Clear()
                
                self._nested_object_names_list.AddDatas( nested_object_names )
                
                self._nested_object_names_panel.setVisible( True )
                
            
        else:
            
            raise Exception( 'Did not understand the new exporter type!' )
            
        
    
    def _ShowSidecarHelp( self ):
        
        message = 'Sidecars are typically named just as their associated file but with the additional extension. \'image.jpg\' makes \'image.jpg.txt\', and so on.'
        message += os.linesep * 2
        message += 'Sidecar exporters will overwrite whatever is at their set destination, so be careful if you intend to set up multiple simultaneous exports, or the second will overwrite the first. You can safely export to two or more different locations in the same .json file, but if you export to .txt, use the \'suffix\' control to export to different files.'
        message += os.linesep * 2
        message += 'If there is no content to write, no new file will be created.'
        
        QW.QMessageBox.information( self, 'Sidecars', message )
        
    
    def _UpdateServiceKeyButtonLabel( self ):
        
        try:
            
            name = HG.client_controller.services_manager.GetName( self._service_key )
            
        except HydrusExceptions.DataMissing:
            
            name = 'unknown'
            
        
        self._service_selection_button.setText( name )
        
    
    def GetValue( self ) -> ClientMetadataMigrationExporters.SingleFileMetadataExporter:
        
        exporter = self._GetValue()
        
        return exporter
        
    

class SingleFileMetadataExporterButton( QW.QPushButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, exporter: ClientMetadataMigrationExporters.SingleFileMetadataExporter, allowed_exporter_classes: list ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._exporter = exporter
        self._allowed_exporter_classes = allowed_exporter_classes
        
        self._RefreshLabel()
        
        self.clicked.connect( self._Edit )
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit metadata migration exporter' ) as dlg:
            
            panel = EditSingleFileMetadataExporterPanel( dlg, self._exporter, self._allowed_exporter_classes )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value = panel.GetValue()
                
                self.SetValue( value )
                
                self.valueChanged.emit()
                
            
        
    
    def _RefreshLabel( self ):
        
        text = self._exporter.ToString()
        
        elided_text = HydrusText.ElideText( text, 64 )
        
        self.setText( elided_text )
        self.setToolTip( text )
        
    
    def GetValue( self ):
        
        return self._exporter
        
    
    def SetValue( self, exporter: ClientMetadataMigrationExporters.SingleFileMetadataExporter ):
        
        self._exporter = exporter
        
        self._RefreshLabel()
        
    
