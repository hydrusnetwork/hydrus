import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientParsing
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUIMetadataMigrationCommon
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataMigrationExporters

choice_tuple_label_lookup = {
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes : 'a file\'s notes',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags : 'a file\'s tags',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs : 'a file\'s URLs',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps : 'a file\'s timestamps',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT : 'a .txt sidecar',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON : 'a .json sidecar'
}

choice_tuple_description_lookup = {
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes : 'The notes that a file has.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags : 'The tags that a file has on a particular service.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs : 'The known URLs that a file has.',
    ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps : 'A recorded timestamp the file has.',
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
        self._service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        
        #
        
        self._change_type_button = ClientGUICommon.BetterButton( self, 'change type', self._ChangeType )
        
        #
        
        self._service_selection_panel = QW.QWidget( self )
        
        self._service_selection_button = ClientGUICommon.BetterButton( self._service_selection_panel, 'service', self._SelectService )
        
        hbox = ClientGUICommon.WrapInText( self._service_selection_button, self._service_selection_panel, 'tag service: ' )
        
        self._service_selection_panel.setLayout( hbox )
        
        #
        
        self._timestamp_data_stub_panel = ClientGUICommon.StaticBox( self, 'timestamp type' )
        
        self._timestamp_data_stub = ClientGUITime.TimestampDataStubCtrl( self._timestamp_data_stub_panel )
        
        self._timestamp_data_stub_panel.Add( self._timestamp_data_stub, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
        
        self._txt_separator_panel = ClientGUIMetadataMigrationCommon.EditSidecarTXTSeparator( self )
        
        #
        
        self._sidecar_panel = ClientGUIMetadataMigrationCommon.EditSidecarDetailsPanel( self )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._change_type_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._service_selection_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._timestamp_data_stub_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sidecar_help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._nested_object_names_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._txt_separator_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sidecar_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        try:
            
            exporter_class = SelectClass( self, allowed_exporter_classes )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        exporter = exporter_class()
        
        # it is nice to preserve old values as we flip from one type to another. more pleasant than making the user cancel and re-open
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ):
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            
            exporter.SetRemoveActualFilenameExt( remove_actual_filename_ext )
            exporter.SetSuffix( suffix )
            exporter.SetFilenameStringConverter( filename_string_converter )
            
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
            
            exporter.SetServiceKey( self._service_key )
            
        elif isinstance( exporter, ( ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs ) ):
            
            pass
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps ):
            
            exporter.SetTimestampDataStub( self._timestamp_data_stub.GetValue() )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT ):
            
            exporter.SetSeparator( self._txt_separator_panel.GetValue() )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ):
            
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
            
            try:
                
                CG.client_controller.services_manager.GetName( self._service_key )
                
            except HydrusExceptions.DataMissing:
                
                raise HydrusExceptions.VetoException( 'Sorry, your exporter needs a valid tag service! The selected one is missing!' )
                
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key = self._service_key )
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs()
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps()
            
            exporter.SetTimestampDataStub( self._timestamp_data_stub.GetValue() )
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes:
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes()
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT:
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            separator = self._txt_separator_panel.GetValue()
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT( remove_actual_filename_ext = remove_actual_filename_ext, suffix = suffix, filename_string_converter = filename_string_converter, separator = separator )
            
        elif self._current_exporter_class == ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON:
            
            remove_actual_filename_ext = self._sidecar_panel.GetRemoveActualFilenameExt()
            suffix = self._sidecar_panel.GetSuffix()
            filename_string_converter = self._sidecar_panel.GetFilenameStringConverter()
            
            nested_object_names = self._nested_object_names_list.GetData()
            
            exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON( remove_actual_filename_ext = remove_actual_filename_ext, suffix = suffix, filename_string_converter = filename_string_converter, nested_object_names = nested_object_names )
            
        else:
            
            raise Exception( 'Did not understand the current exporter type!' )
            
        
        return exporter
        
    
    def _SelectService( self ):
        
        service_key = ClientGUIDialogsQuick.SelectServiceKey( service_types = HC.REAL_TAG_SERVICES, unallowed = [ self._service_key ] )
        
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
        self._txt_separator_panel.setVisible( False )
        self._sidecar_panel.setVisible( False )
        self._timestamp_data_stub_panel.setVisible( False )
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterSidecar ):
            
            self._sidecar_help_button.setVisible( True )
            
            remove_actual_filename_ext = exporter.GetRemoveActualFilenameExt()
            suffix = exporter.GetSuffix()
            filename_string_converter = exporter.GetFilenameStringConverter()
            
            self._sidecar_panel.SetRemoveActualFilenameExt( remove_actual_filename_ext )
            self._sidecar_panel.SetSuffix( suffix )
            self._sidecar_panel.SetFilenameStringConverter( filename_string_converter )
            
            self._sidecar_panel.setVisible( True )
            
        
        if isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags ):
            
            self._service_key = exporter.GetServiceKey()
            
            self._UpdateServiceKeyButtonLabel()
            
            self._service_selection_panel.setVisible( True )
            
            if not CG.client_controller.services_manager.ServiceExists( self._service_key ):
                
                message = 'Hey, the tag service for your exporter does not seem to exist! Maybe it was deleted. Please select a new one that does.'
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
        elif isinstance( exporter, ( ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaNotes, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaURLs ) ):
            
            pass
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTimestamps ):
            
            self._timestamp_data_stub.SetValue( exporter.GetTimestampDataStub() )
            
            self._timestamp_data_stub_panel.setVisible( True )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterTXT ):
            
            self._sidecar_panel.SetSidecarExt( 'txt' )
            self._sidecar_panel.SetExampleInput( '01234564789abcdef.jpg' )
            
            self._txt_separator_panel.SetValue( exporter.GetSeparator() )
            
            self._txt_separator_panel.setVisible( True )
            
        elif isinstance( exporter, ClientMetadataMigrationExporters.SingleFileMetadataExporterJSON ):
            
            self._sidecar_panel.SetSidecarExt( 'json' )
            self._sidecar_panel.SetExampleInput( '01234564789abcdef.jpg' )
            
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
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _UpdateServiceKeyButtonLabel( self ):
        
        try:
            
            name = CG.client_controller.services_manager.GetName( self._service_key )
            
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
        
    
