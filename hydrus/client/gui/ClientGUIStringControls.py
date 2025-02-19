import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIStringPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.parsing import ClientParsing

class StringConverterButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, string_converter: ClientStrings.StringConverter ):
        
        super().__init__( parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._example_string_override = None
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string converter', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringConverterPanel( dlg, self._string_converter, example_string_override = self._example_string_override )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_converter.ToString()
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( label ) )
        
        elided_label = HydrusText.ElideText( label, 64 )
        
        self.setText( elided_label )
        
    
    def GetValue( self ) -> ClientStrings.StringConverter:
        
        return self._string_converter
        
    
    def SetExampleString( self, example_string: str ):
        
        self._example_string_override = example_string
        
    
    def SetValue( self, string_converter: ClientStrings.StringConverter ):
        
        self._string_converter = string_converter
        
        self._UpdateLabel()
        
        self.valueChanged.emit()
        
    
class StringMatchButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, string_match: ClientStrings.StringMatch ):
        
        super().__init__( parent, 'edit string match', self._Edit )
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string match', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, self._string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._string_match = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_match.ToString()
        
        self.setText( label )
        
    
    def GetValue( self ) -> ClientStrings.StringMatch:
        
        return self._string_match
        
    
    def SetValue( self, string_match: ClientStrings.StringMatch ):
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    

class StringProcessorButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, string_processor: ClientStrings.StringProcessor, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ] ):
        
        super().__init__( parent, 'edit string processor', self._Edit )
        
        self._string_processor = string_processor
        self._test_data_callable = test_data_callable
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        test_data = self._test_data_callable()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string processor', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringProcessorPanel( dlg, self._string_processor, test_data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._string_processor = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        statements = self._string_processor.GetProcessingStrings()
        
        if len( statements ) == 0:
            
            label = self._string_processor.ToString()
            
        else:
            
            statements = [ HydrusText.ElideText( statement, 64 ) for statement in statements ]
            
            label = '\n'.join( statements )
            
        
        self.setText( label )
        
    
    def GetValue( self ) -> ClientStrings.StringProcessor:
        
        return self._string_processor
        
    
    def SetValue( self, string_processor: ClientStrings.StringProcessor ):
        
        self._string_processor = string_processor
        
        self._UpdateLabel()
        
        self.valueChanged.emit()
        
    

class StringProcessorWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, string_processor: ClientStrings.StringProcessor, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ] ):
        
        super().__init__( parent )
        
        self._edit_button = StringProcessorButton( self, string_processor, test_data_callable )
        
        self._copy_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().copy, self._Copy )
        self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy String Processor to the clipboard.' ) )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste a String Processor from the clipboard.' ) )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._edit_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER )
        
        self.setLayout( hbox )
        
        self._edit_button.valueChanged.connect( self.valueChanged )
        
    
    def _Copy( self ):
        
        string_processor = self.GetValue()
        
        text = string_processor.DumpToString()
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, ClientStrings.StringProcessor ):
            
            self.SetValue( obj )
            
        else:
            
            raise Exception( f'The imported object was wrong for this control! It appeared to be a {HydrusData.GetTypeName( obj )}.' )
            
        
    
    def _Paste( self ):
        
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
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Hydrus Object(s)', e )
            
        
    
    def GetValue( self ) -> ClientStrings.StringProcessor:
        
        return self._edit_button.GetValue()
        
    
    def SetValue( self, string_processor: ClientStrings.StringProcessor ):
        
        self._edit_button.SetValue( string_processor )
        
    

class StringMatchToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict: typing.Dict[ ClientStrings.StringMatch, ClientStrings.StringMatch ], min_height = 10, key_name = 'key' ):
        
        super().__init__( parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.KEY : self._key_name }
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, min_height, model, use_simple_delete = True, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( list( initial_dict.items() ) )
        
        self._listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, data ):
        
        ( key_string_match, value_string_match ) = data
        
        pretty_key = key_string_match.ToString()
        pretty_value = value_string_match.ToString()
        
        return ( pretty_key, pretty_value )
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _Add( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
            
            string_match = ClientStrings.StringMatch()
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                key_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
            
            string_match = ClientStrings.StringMatch()
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                value_string_match = panel.GetValue()
                
                data = ( key_string_match, value_string_match )
                
                self._listctrl.AddData( data, select_sort_and_scroll = True )
                
            
        
    
    def _Edit( self ):
        
        data = self._listctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( key_string_match, value_string_match ) = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, key_string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                key_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, value_string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                value_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        edited_data = ( key_string_match, value_string_match )
        
        self._listctrl.ReplaceData( data, edited_data, sort_and_scroll = True )
        
    
    def GetValue( self ) -> typing.Dict[ str, ClientStrings.StringMatch ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class StringToStringDictButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label ):
        
        super().__init__( parent, label, self._Edit )
        
        self._value = {}
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string dictionary' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = StringToStringDictControl( panel, self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._value = control.GetValue()
                
            
        
    
    def GetValue( self ) -> typing.Dict[ str, str ]:
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
    
class StringToStringDictControl( QW.QWidget ):
    
    columnListContentsChanged = QC.Signal()
    
    def __init__( self, parent, initial_dict: typing.Dict[ str, str ], min_height = 10, key_name = 'key', value_name = 'value', allow_add_delete = True, edit_keys = True ):
        
        super().__init__( parent )
        
        self._key_name = key_name
        self._value_name = value_name
        
        self._edit_keys = edit_keys
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        use_simple_delete = allow_add_delete
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_VALUE.KEY : self._key_name, CGLC.COLUMN_LIST_KEY_TO_VALUE.VALUE : self._value_name }
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_KEY_TO_VALUE.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, min_height, model, use_simple_delete = use_simple_delete, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        self._listctrl.columnListContentsChanged.connect( self.columnListContentsChanged )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        if allow_add_delete:
            
            listctrl_panel.AddButton( 'add', self._Add )
            
        
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        
        if allow_add_delete:
            
            listctrl_panel.AddDeleteButton()
            
        
        #
        
        self._SetValue( initial_dict )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, data ):
        
        ( key, value ) = data
        
        return ( key, value )
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'That {} already exists!'.format( self._key_name ) )
                    
                    return
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._value_name, allow_blank = True ) as dlg_2:
                    
                    if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        value = dlg_2.GetValue()
                        
                        data = ( key, value )
                        
                        self._listctrl.AddData( data, select_sort_and_scroll = True )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        data = self._listctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( key, value ) = data
        
        if self._edit_keys:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_key = dlg.GetValue()
                    
                    if edited_key != key and edited_key in self._GetExistingKeys():
                        
                        ClientGUIDialogsMessage.ShowWarning( self, 'That {} already exists!'.format( self._key_name ) )
                        
                        return
                        
                    
                else:
                    
                    return
                    
                
            
        else:
            
            edited_key = key
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._value_name, default = value, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_value = dlg.GetValue()
                
            else:
                
                return
                
            
        
        edited_data = ( edited_key, edited_value )
        
        self._listctrl.ReplaceData( data, edited_data, sort_and_scroll = True )
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def _SetValue( self, str_to_str_dict: typing.Dict[ str, str ] ):
        
        self._listctrl.SetData( [ ( str( key ), str( value ) ) for ( key, value ) in str_to_str_dict.items() ] )
        
        self._listctrl.Sort()
        
    
    def Clear( self ):
        
        self._listctrl.DeleteDatas( self._listctrl.GetData() )
        
    
    def GetValue( self ) -> typing.Dict[ str, str ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
    def SetValue( self, str_to_str_dict: typing.Dict[ str, str ] ):
        
        self._SetValue( str_to_str_dict )
        
    

class StringToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict: typing.Dict[ str, ClientStrings.StringMatch ], min_height = 10, key_name = 'key' ):
        
        super().__init__( parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.KEY : self._key_name }
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, min_height, model, use_simple_delete = True, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( initial_dict.items() )
        
        self._listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, data ):
        
        ( key, string_match ) = data
        
        pretty_string_match = string_match.ToString()
        
        return ( key, pretty_string_match )
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'That {} already exists!'.format( self._key_name ) )
                    
                    return
                    
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg_2:
                    
                    string_match = ClientStrings.StringMatch()
                    
                    panel = ClientGUIStringPanels.EditStringMatchPanel( dlg_2, string_match )
                    
                    dlg_2.SetPanel( panel )
                    
                    if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                        
                        string_match = panel.GetValue()
                        
                        data = ( key, string_match )
                        
                        self._listctrl.AddData( data, select_sort_and_scroll = True )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        data = self._listctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( key, string_match ) = data
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_key = dlg.GetValue()
                
                if edited_key != key and edited_key in self._GetExistingKeys():
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'That {} already exists!'.format( self._key_name ) )
                    
                    return
                    
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
            
            string_match = ClientStrings.StringMatch()
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        edited_data = ( edited_key, edited_string_match )
        
        self._listctrl.ReplaceData( data, edited_data, sort_and_scroll = True )
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def GetValue( self ) -> typing.Dict[ str, ClientStrings.StringMatch ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    

