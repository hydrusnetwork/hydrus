from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataMigrationCore

class EditSidecarDetailsPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent, 'sidecar filename' )
        
        self._sidecar_ext = 'txt'
        
        self._remove_actual_filename_ext = QW.QCheckBox( self )
        tt = 'If you set this, the actual filename\'s extension will not be used in the sidecar. For a txt sidecar, \'my_image.jpg\' will be matched with \'my_image.txt\'.'
        self._remove_actual_filename_ext.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._suffix = QW.QLineEdit( self )
        tt = 'If you set this, the sidecar will include this extra suffix. For a txt sidecar, \'my_image.jpg\' will be matched with \'my_image.jpg.tags.txt\'.'
        self._suffix.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        string_converter = ClientStrings.StringConverter()
        
        self._filename_string_converter = ClientGUIStringControls.StringConverterButton( self, string_converter )
        
        self._example_input = QW.QLineEdit( self )
        self._example_input.setText( 'my_image.jpg' )
        
        self._example_output = QW.QLineEdit( self )
        self._example_output.setReadOnly( True )
        
        self._example_output.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you only have one sidecar for multiple files, and thus you have some regex that is doing ".*" -> "info.txt" kind of thing, you must not set any accompanying file imports to be deleted or moved after import! The sidecar will be deleted/moved too, and then the next file will not have the sidecar to look at!' ) )
        
        rows = []
        
        rows.append( ( 'remove file .ext?: ', self._remove_actual_filename_ext ) )
        rows.append( ( 'optional suffix: ', self._suffix ) )
        rows.append( ( 'ADVANCED: final sidecar filename conversion: ', self._filename_string_converter ) )
        rows.append( ( 'Test media path: ', self._example_input ) )
        rows.append( ( 'Resulting sidecar path: ', self._example_output ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._remove_actual_filename_ext.clicked.connect( self._UpdateExample )
        self._suffix.textChanged.connect( self._UpdateExample )
        self._filename_string_converter.valueChanged.connect( self._UpdateExample )
        self._example_input.textChanged.connect( self._UpdateExample )
        
    
    def _UpdateExample( self ):
        
        path = self._example_input.text()
        remove_actual_filename_ext = self._remove_actual_filename_ext.isChecked()
        suffix = self._suffix.text()
        
        try:
            
            empty = ClientStrings.StringConverter()
            
            result = ClientMetadataMigrationCore.GetSidecarPath( path, remove_actual_filename_ext, suffix, empty, self._sidecar_ext )
            
            self._filename_string_converter.SetExampleString( result )
            
        except Exception as e:
            
            pass
            
        
        filename_string_converter = self._filename_string_converter.GetValue()
        
        try:
            
            result = ClientMetadataMigrationCore.GetSidecarPath( path, remove_actual_filename_ext, suffix, filename_string_converter, self._sidecar_ext )
            
        except Exception as e:
            
            result = 'Error: {}'.format( e )
            
        
        self._example_output.setText( result )
        
    
    def GetRemoveActualFilenameExt( self ) -> bool:
        
        return self._remove_actual_filename_ext.isChecked()
        
    
    def GetSuffix( self ) -> str:
        
        return self._suffix.text()
        
    
    def GetFilenameStringConverter( self ) -> ClientStrings.StringConverter:
        
        return self._filename_string_converter.GetValue()
        
    
    def SetExampleInput( self, input: str ):
        
        self._example_input.setText( input )
        
        self._UpdateExample()
        
    
    def SetRemoveActualFilenameExt( self, remove_actual_filename_ext: bool ):
        
        self._remove_actual_filename_ext.setChecked( remove_actual_filename_ext )
        
    
    def SetSidecarExt( self, ext: str ):
        
        self._sidecar_ext = ext
        
        self._UpdateExample()
        
    
    def SetSuffix( self, suffix: str ):
        
        self._suffix.setText( suffix )
        
    
    def SetFilenameStringConverter( self, filename_string_converter: ClientStrings.StringConverter ):
        
        self._filename_string_converter.SetValue( filename_string_converter )
        
    

SEPARATOR_NEWLINE = 0
SEPARATOR_CUSTOM = 1
SEPARATOR_FOUR_PIPES = 2

class EditSidecarTXTSeparator( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent, 'sidecar txt separator' )
        
        self._choice = ClientGUICommon.BetterChoice( self )
        
        self._choice.addItem( 'newline', SEPARATOR_NEWLINE )
        self._choice.addItem( 'four pipes (||||)', SEPARATOR_FOUR_PIPES )
        self._choice.addItem( 'custom text', SEPARATOR_CUSTOM )
        
        tt = 'You can separate the "rows" of tags by something other than newlines if you like. If you are parsing multiple multi-line notes, try separating them by four pipes, ||||. If you have/want a CSV list, try a separator of "," or ", ".'
        
        self._choice.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._custom_input = QW.QLineEdit( self )
        
        rows = []
        
        rows.append( ( 'separator: ', self._choice ) )
        rows.append( ( 'custom: ', self._custom_input ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._choice.currentIndexChanged.connect( self._UpdateControls )
        
    
    def _UpdateControls( self ):
        
        value = self._choice.GetValue()
        
        self._custom_input.setEnabled( value == SEPARATOR_CUSTOM )
        
    
    def GetValue( self ):
        
        value = self._choice.GetValue()
        
        if value == SEPARATOR_NEWLINE:
            
            return '\n'
            
        elif value == SEPARATOR_FOUR_PIPES:
            
            return '||||'
            
        else:
            
            return self._custom_input.text()
            
        
    
    def SetValue( self, value: str ):
        
        if value == '\n':
            
            self._choice.SetValue( SEPARATOR_NEWLINE )
            
        elif value == '||||':
            
            self._choice.SetValue( SEPARATOR_FOUR_PIPES )
            
        else:
            
            self._choice.SetValue( SEPARATOR_CUSTOM )
            self._custom_input.setText( value )
            
        
        self._UpdateControls()
        
    
