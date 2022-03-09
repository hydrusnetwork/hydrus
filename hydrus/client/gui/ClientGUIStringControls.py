import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientParsing
from hydrus.client import ClientStrings
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIStringPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon

class StringConverterButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, string_converter: ClientStrings.StringConverter ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._example_string_override = None
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string converter', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringConverterPanel( dlg, self._string_converter, example_string_override = self._example_string_override )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_converter.ToString()
        
        self.setToolTip( label )
        
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
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string match', self._Edit )
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string match', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, self._string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
    
    def __init__( self, parent, string_processor: ClientStrings.StringProcessor, test_data_callable: typing.Callable[ [], ClientParsing.ParsingTestData ] ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string processor', self._Edit )
        
        self._string_processor = string_processor
        self._test_data_callable = test_data_callable
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        test_data = self._test_data_callable()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string processor', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = ClientGUIStringPanels.EditStringProcessorPanel( dlg, self._string_processor, test_data )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._string_processor = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        statements = self._string_processor.GetProcessingStrings()
        
        if len( statements ) == 0:
            
            label = self._string_processor.ToString()
            
        else:
            
            statements = [ HydrusText.ElideText( statement, 64 ) for statement in statements ]
            
            label = os.linesep.join( statements )
            
        
        self.setText( label )
        
    
    def GetValue( self ) -> ClientStrings.StringProcessor:
        
        return self._string_processor
        
    
    def SetValue( self, string_processor: ClientStrings.StringProcessor ):
        
        self._string_processor = string_processor
        
        self._UpdateLabel()
        
    
class StringMatchToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict: typing.Dict[ ClientStrings.StringMatch, ClientStrings.StringMatch ], min_height = 10, key_name = 'key' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.KEY : self._key_name }
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.ID, min_height, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( list(initial_dict.items()) )
        
        self._listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key_string_match, value_string_match ) = data
        
        pretty_key = key_string_match.ToString()
        pretty_value = value_string_match.ToString()
        
        display_tuple = ( pretty_key, pretty_value )
        sort_tuple = ( pretty_key, pretty_value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
            
            string_match = ClientStrings.StringMatch()
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
            
            string_match = ClientStrings.StringMatch()
            
            panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value_string_match = panel.GetValue()
                
                data = ( key_string_match, value_string_match )
                
                self._listctrl.AddDatas( ( data, ) )
                
            
        
    
    def _Edit( self ):
        
        edited_datas = []
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key_string_match, value_string_match ) = data
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
                
                panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, key_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    key_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
                
                panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, value_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    value_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            edited_data = ( key_string_match, value_string_match )
            
            self._listctrl.AddDatas( ( edited_data, ) )
            
            edited_datas.append( edited_data )
            
        
        self._listctrl.SelectDatas( edited_datas )
        
        self._listctrl.Sort()
        
    
    def GetValue( self ) -> typing.Dict[ str, ClientStrings.StringMatch ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class StringToStringDictButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._value = {}
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit string dictionary' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = StringToStringDictControl( panel, self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._value = control.GetValue()
                
            
        
    
    def GetValue( self ) -> typing.Dict[ str, str ]:
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
    
class StringToStringDictControl( QW.QWidget ):
    
    columnListContentsChanged = QC.Signal()
    
    def __init__( self, parent, initial_dict: typing.Dict[ str, str ], min_height = 10, key_name = 'key', value_name = 'value', allow_add_delete = True, edit_keys = True ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        self._value_name = value_name
        
        self._edit_keys = edit_keys
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        use_simple_delete = allow_add_delete
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_VALUE.KEY : self._key_name }
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_KEY_TO_VALUE.ID, min_height, self._ConvertDataToListCtrlTuples, use_simple_delete = use_simple_delete, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        self._listctrl.columnListContentsChanged.connect( self.columnListContentsChanged )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        if allow_add_delete:
            
            listctrl_panel.AddButton( 'add', self._Add )
            
        
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        
        if allow_add_delete:
            
            listctrl_panel.AddDeleteButton()
            
        
        #
        
        self._listctrl.AddDatas( list(initial_dict.items()) )
        
        self._listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key, value ) = data
        
        display_tuple = ( key, value )
        sort_tuple = ( key, value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    QW.QMessageBox.warning( self, 'Warning', 'That {} already exists!'.format( self._key_name ) )
                    
                    return
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._value_name, allow_blank = True ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        value = dlg.GetValue()
                        
                        data = ( key, value )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        edited_datas = []
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key, value ) = data
            
            if self._edit_keys:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        edited_key = dlg.GetValue()
                        
                        if edited_key != key and edited_key in self._GetExistingKeys():
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That {} already exists!'.format( self._key_name ) )
                            
                            break
                            
                        
                    else:
                        
                        break
                        
                    
                
            else:
                
                edited_key = key
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._value_name, default = value, allow_blank = True ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_value = dlg.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            edited_data = ( edited_key, edited_value )
            
            self._listctrl.AddDatas( ( edited_data, ) )
            
            edited_datas.append( edited_data )
            
        
        self._listctrl.SelectDatas( edited_datas )
        
        self._listctrl.Sort()
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def GetValue( self ) -> typing.Dict[ str, str ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class StringToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict: typing.Dict[ str, ClientStrings.StringMatch ], min_height = 10, key_name = 'key' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        column_types_to_name_overrides = { CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.KEY : self._key_name }
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_KEY_TO_STRING_MATCH.ID, min_height, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit, column_types_to_name_overrides = column_types_to_name_overrides )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( initial_dict.items() )
        
        self._listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key, string_match ) = data
        
        pretty_string_match = string_match.ToString()
        
        display_tuple = ( key, pretty_string_match )
        sort_tuple = ( key, pretty_string_match )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    QW.QMessageBox.warning( self, 'Warning', 'That {} already exists!'.format( self._key_name ) )
                    
                    return
                    
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
                    
                    string_match = ClientStrings.StringMatch()
                    
                    panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        string_match = panel.GetValue()
                        
                        data = ( key, string_match )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        edited_datas = []
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key, string_match ) = data
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_key = dlg.GetValue()
                    
                    if edited_key != key and edited_key in self._GetExistingKeys():
                        
                        QW.QMessageBox.warning( self, 'Warning', 'That {} already exists!'.format( self._key_name ) )
                        
                        break
                        
                    
                else:
                    
                    break
                    
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit match' ) as dlg:
                
                string_match = ClientStrings.StringMatch()
                
                panel = ClientGUIStringPanels.EditStringMatchPanel( dlg, string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            edited_data = ( edited_key, edited_string_match )
            
            self._listctrl.AddDatas( ( edited_data, ) )
            
            edited_datas.append( edited_data )
            
        
        self._listctrl.SelectDatas( edited_datas )
        
        self._listctrl.Sort()
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def GetValue( self ) -> typing.Dict[ str, ClientStrings.StringMatch ]:
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    

