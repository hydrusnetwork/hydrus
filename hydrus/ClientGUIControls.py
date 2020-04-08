from . import ClientConstants as CC
from . import ClientGUICommon
from . import ClientGUICore as CGC
from . import ClientGUIDialogs
from . import ClientGUIFunctions
from . import ClientGUIListCtrl
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientParsing
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusText
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'bandwidth rules' )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'max allowed', 14 ), ( 'every', 16 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'bandwidth_rules', 8, 10, columns, self._ConvertRuleToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( bandwidth_rules.GetRules() )
        
        self._listctrl.Sort( 0 )
        
        #
        
        self.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        rule = ( HC.BANDWIDTH_TYPE_DATA, None, 1024 * 1024 * 100 )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
            
            panel = self._EditPanel( dlg, rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_rule = panel.GetValue()
                
                self._listctrl.AddDatas( ( new_rule, ) )
                
                self._listctrl.Sort()
                
            
        
    
    def _ConvertRuleToListCtrlTuples( self, rule ):
        
        ( bandwidth_type, time_delta, max_allowed ) = rule
        
        pretty_time_delta = HydrusData.TimeDeltaToPrettyTimeDelta( time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            pretty_max_allowed = HydrusData.ToHumanBytes( max_allowed )
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            pretty_max_allowed = HydrusData.ToHumanInt( max_allowed ) + ' requests'
            
        
        sort_time_delta = ClientGUIListCtrl.SafeNoneInt( time_delta )
        
        sort_tuple = ( max_allowed, sort_time_delta )
        display_tuple = ( pretty_max_allowed, pretty_time_delta )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        selected_rules = self._listctrl.GetData( only_selected = True )
        
        for rule in selected_rules:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
                
                panel = self._EditPanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_rule = panel.GetValue()
                    
                    self._listctrl.DeleteDatas( ( rule, ) )
                    
                    self._listctrl.AddDatas( ( edited_rule, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._listctrl.Sort()
        
    
    def GetValue( self ):
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        for rule in self._listctrl.GetData():
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            bandwidth_rules.AddRule( bandwidth_type, time_delta, max_allowed )
            
        
        return bandwidth_rules
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, rule ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._bandwidth_type = ClientGUICommon.BetterChoice( self )
            
            self._bandwidth_type.addItem( 'data', HC.BANDWIDTH_TYPE_DATA )
            self._bandwidth_type.addItem( 'requests', HC.BANDWIDTH_TYPE_REQUESTS )
            
            self._bandwidth_type.currentIndexChanged.connect( self._UpdateEnabled )
            
            self._max_allowed_bytes = BytesControl( self )
            self._max_allowed_requests = QP.MakeQSpinBox( self, min=1, max=1048576 )
            
            self._time_delta = ClientGUITime.TimeDeltaButton( self, min = 1, days = True, hours = True, minutes = True, seconds = True, monthly_allowed = True )
            
            #
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            self._bandwidth_type.SetValue( bandwidth_type )
            
            self._time_delta.SetValue( time_delta )
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.SetValue( max_allowed )
                
            else:
                
                self._max_allowed_requests.setValue( max_allowed )
                
            
            self._UpdateEnabled()
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._max_allowed_bytes, CC.FLAGS_VCENTER )
            QP.AddToLayout( hbox, self._max_allowed_requests, CC.FLAGS_VCENTER )
            QP.AddToLayout( hbox, self._bandwidth_type, CC.FLAGS_VCENTER )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' every '), CC.FLAGS_VCENTER )
            QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_VCENTER )
            
            self.widget().setLayout( hbox )
            
        
        def _UpdateEnabled( self ):
            
            bandwidth_type = self._bandwidth_type.GetValue()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.show()
                self._max_allowed_requests.hide()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                self._max_allowed_bytes.hide()
                self._max_allowed_requests.show()
            
            
        def GetValue( self ):
            
            bandwidth_type = self._bandwidth_type.GetValue()
            
            time_delta = self._time_delta.GetValue()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                max_allowed = self._max_allowed_bytes.GetValue()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                max_allowed = self._max_allowed_requests.value()
                
            
            return ( bandwidth_type, time_delta, max_allowed )
            
        
    
class BytesControl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, initial_value = 65536 ):
        
        QW.QWidget.__init__( self, parent )
        
        self._spin = QP.MakeQSpinBox( self, min=0, max=1048576 )
        
        self._unit = ClientGUICommon.BetterChoice( self )
        
        self._unit.addItem( 'B', 1 )
        self._unit.addItem( 'KB', 1024 )
        self._unit.addItem( 'MB', 1024 * 1024 )
        self._unit.addItem( 'GB', 1024 * 1024 * 1024 )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._spin, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
        self._spin.valueChanged.connect( self._HandleValueChanged )
        self._unit.currentIndexChanged.connect( self._HandleValueChanged )
        
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
              
    
    def GetSeparatedValue( self ):
        
        return (self._spin.value(), self._unit.GetValue())
        
    
    def GetValue( self ):
        
        return self._spin.value() * self._unit.GetValue()
        
    
    def SetSeparatedValue( self, value, unit ):
        
        return (self._spin.setValue( value ), self._unit.SetValue( unit ))
        
    
    def SetValue( self, value ):
        
        max_unit = 1024 * 1024 * 1024
        
        unit = 1
        
        while value % 1024 == 0 and unit < max_unit:
            
            value //= 1024
            
            unit *= 1024
            
        
        self._spin.setValue( value )
        self._unit.SetValue( unit )
        
    
class EditStringConverterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_converter, example_string_override = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        transformations_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( '#', 3 ), ( 'transformation', 30 ), ( 'result', -1 ) ]
        
        self._transformations = ClientGUIListCtrl.BetterListCtrl( transformations_panel, 'string_converter_transformations', 7, 35, columns, self._ConvertTransformationToListCtrlTuples, delete_key_callback = self._DeleteTransformation, activation_callback = self._EditTransformation )
        
        transformations_panel.SetListCtrl( self._transformations )
        
        transformations_panel.AddButton( 'add', self._AddTransformation )
        transformations_panel.AddButton( 'edit', self._EditTransformation, enabled_only_on_selection = True )
        transformations_panel.AddDeleteButton()
        
        transformations_panel.AddSeparator()
        
        transformations_panel.AddButton( 'move up', self._MoveUp, enabled_check_func = self._CanMoveUp )
        transformations_panel.AddButton( 'move down', self._MoveDown, enabled_check_func = self._CanMoveDown )
        
        self._example_string = QW.QLineEdit( self )
        
        #
        
        self._transformations.AddDatas( [ ( i + 1, transformation_type, data ) for ( i, ( transformation_type, data ) ) in enumerate( string_converter.transformations ) ] )
        
        if example_string_override is None:
            
            self._example_string.setText( string_converter.example_string )
            
        else:
            
            self._example_string.setText( example_string_override )
            
        
        self._transformations.UpdateDatas() # to refresh, now they are all in the list
        
        self._transformations.Sort( 0 )
        
        #
        
        rows = []
        
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, transformations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._example_string.textChanged.connect( self.EventUpdate )
        
    
    def _AddTransformation( self ):
        
        transformation_type = ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT
        data = 'extra text'
        
        try:
            
            string_converter = self._GetValue()
            
            example_string_at_this_point = string_converter.Convert( self._example_string.text() )
            
        except:
            
            example_string_at_this_point = self._example_string.text()
            
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = self._TransformationPanel( dlg, transformation_type, data, example_string_at_this_point )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                number = self._transformations.topLevelItemCount() + 1
                
                ( transformation_type, data ) = panel.GetValue()
                
                enumerated_transformation = ( number, transformation_type, data )
                
                self._transformations.AddDatas( ( enumerated_transformation, ) )
                
            
        
        self._transformations.UpdateDatas() # need to refresh string after the insertion, so the new row can be included in the parsing calcs
        
        self._transformations.Sort()
        
    
    def _CanMoveDown( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        if len( selected_data ) == 1:
            
            ( number, transformation_type, data ) = selected_data[0]
            
            if number < self._transformations.topLevelItemCount():
                
                return True
                
            
        
        return False
        
    
    def _CanMoveUp( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        if len( selected_data ) == 1:
            
            ( number, transformation_type, data ) = selected_data[0]
            
            if number > 1:
                
                return True
                
            
        
        return False
        
    
    def _ConvertTransformationToListCtrlTuples( self, transformation ):
        
        ( number, transformation_type, data ) = transformation
        
        pretty_number = HydrusData.ToHumanInt( number )
        pretty_transformation = ClientParsing.StringConverter.TransformationToString( ( transformation_type, data ) )
        
        string_converter = self._GetValue()
        
        try:
            
            pretty_result = ClientParsing.MakeParsedTextPretty( string_converter.Convert( self._example_string.text(), number ) )
            
        except HydrusExceptions.StringConvertException as e:
            
            pretty_result = str( e )
            
        
        display_tuple = ( pretty_number, pretty_transformation, pretty_result )
        sort_tuple = ( number, number, number )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteTransformation( self ):
        
        if len( self._transformations.GetData( only_selected = True ) ) > 0:
            
            text = 'Delete all selected?'
            
            from . import ClientGUIDialogsQuick
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result == QW.QDialog.Accepted:
                
                self._transformations.DeleteSelected()
                
            
        
        # now we need to shuffle up any missing numbers
        
        num_rows = self._transformations.topLevelItemCount()
        
        i = 1
        search_i = i
        
        while i <= num_rows:
            
            try:
                
                transformation = self._GetTransformation( search_i )
                
                if search_i != i:
                    
                    self._transformations.DeleteDatas( ( transformation, ) )
                    
                    ( search_i, transformation_type, data ) = transformation
                    
                    transformation = ( i, transformation_type, data )
                    
                    self._transformations.AddDatas( ( transformation, ) )
                    
                
                i += 1
                search_i = i
                
            except HydrusExceptions.DataMissing:
                
                search_i += 1
                
            
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _EditTransformation( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        for enumerated_transformation in selected_data:
            
            ( number, transformation_type, data ) = enumerated_transformation
            
            try:
                
                string_converter = self._GetValue()
                
                example_string_at_this_point = string_converter.Convert( self._example_string.text(), number - 1 )
                
            except:
                
                example_string_at_this_point = self._example_string.text()
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = self._TransformationPanel( dlg, transformation_type, data, example_string_at_this_point )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._transformations.DeleteDatas( ( enumerated_transformation, ) )
                    
                    ( transformation_type, data ) = panel.GetValue()
                    
                    enumerated_transformation = ( number, transformation_type, data )
                    
                    self._transformations.AddDatas( ( enumerated_transformation, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _GetTransformation( self, desired_number ):
        
        for transformation in self._transformations.GetData():
            
            ( number, transformation_type, data ) = transformation
            
            if number == desired_number:
                
                return transformation
                
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetValue( self ):
        
        enumerated_transformations = list( self._transformations.GetData() )
        
        enumerated_transformations.sort()
        
        transformations = [ ( transformation_type, data ) for ( number, transformation_type, data ) in enumerated_transformations ]
        
        example_string = self._example_string.text()
        
        string_converter = ClientParsing.StringConverter( transformations, example_string )
        
        return string_converter
        
    
    def _MoveDown( self ):
        
        selected_transformation = self._transformations.GetData( only_selected = True )[0]
        
        ( number, transformation_type, data ) = selected_transformation
        
        swap_transformation = self._GetTransformation( number + 1 )
        
        self._SwapTransformations( selected_transformation, swap_transformation )
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _MoveUp( self ):
        
        selected_transformation = self._transformations.GetData( only_selected = True )[0]
        
        ( number, transformation_type, data ) = selected_transformation
        
        swap_transformation = self._GetTransformation( number - 1 )
        
        self._SwapTransformations( selected_transformation, swap_transformation )
        
        self._transformations.UpdateDatas()
        
        self._transformations.Sort()
        
    
    def _SwapTransformations( self, one, two ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        one_selected = one in selected_data
        two_selected = two in selected_data
        
        self._transformations.DeleteDatas( ( one, two ) )
        
        ( number_1, transformation_type_1, data_1 ) = one
        ( number_2, transformation_type_2, data_2 ) = two
        
        one = ( number_2, transformation_type_1, data_1 )
        two = ( number_1, transformation_type_2, data_2 )
        
        self._transformations.AddDatas( ( one, two ) )
        
        if one_selected:
            
            self._transformations.SelectDatas( ( one, ) )
            
        
        if two_selected:
            
            self._transformations.SelectDatas( ( two, ) )
            
        
    
    def EventUpdate( self, text ):
        
        self._transformations.UpdateDatas()
        
    
    def GetValue( self ):
        
        string_converter = self._GetValue()
        
        try:
            
            string_converter.Convert( self._example_string.text() )
            
        except HydrusExceptions.StringConvertException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that can be converted!' )
            
        
        return string_converter
        
    
    class _TransformationPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, transformation_type, data, example_text ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._transformation_type = ClientGUICommon.BetterChoice( self )
            
            for t_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_REVERSE, ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._transformation_type.addItem( ClientParsing.transformation_type_str_lookup[ t_type ], t_type )
                
            
            self._example_string = QW.QLineEdit( self )
            
            min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._example_string, 96 )
            
            self._example_string.setMinimumWidth( min_width )
            
            self._example_string.setText( example_text )
            
            self._example_transformation = QW.QLineEdit( self )
            
            #
            
            self._example_string.setReadOnly( True )
            self._example_transformation.setReadOnly( True )
            
            self._data_text = QW.QLineEdit( self )
            self._data_number = QP.MakeQSpinBox( self, min=0, max=65535 )
            self._data_encoding = ClientGUICommon.BetterChoice( self )
            self._data_regex_repl = QW.QLineEdit( self )
            self._data_date_link = ClientGUICommon.BetterHyperLink( self, 'link to date info', 'https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior' )
            self._data_timezone_decode = ClientGUICommon.BetterChoice( self )
            self._data_timezone_encode = ClientGUICommon.BetterChoice( self )
            self._data_timezone_offset = QP.MakeQSpinBox( self, min=-86400, max=86400 )
            
            for e in ( 'hex', 'base64', 'url percent encoding' ):
                
                self._data_encoding.addItem( e, e )
                
            
            self._data_timezone_decode.addItem( 'UTC', HC.TIMEZONE_GMT )
            self._data_timezone_decode.addItem( 'Local', HC.TIMEZONE_LOCAL )
            self._data_timezone_decode.addItem( 'Offset', HC.TIMEZONE_OFFSET )
            
            self._data_timezone_encode.addItem( 'UTC', HC.TIMEZONE_GMT )
            self._data_timezone_encode.addItem( 'Local', HC.TIMEZONE_LOCAL )
            
            #
            
            self._transformation_type.SetValue( transformation_type )
            
            self._data_number.setValue( 1 )
            
            #
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_ENCODE ):
                
                self._data_encoding.SetValue( data )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                ( pattern, repl ) = data
                
                self._data_text.setText( pattern )
                self._data_regex_repl.setText( repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                ( phrase, timezone_type, timezone_offset ) = data
                
                self._data_text.setText( phrase )
                self._data_timezone_decode.SetValue( timezone_type )
                self._data_timezone_offset.setValue( timezone_offset )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE:
                
                ( phrase, timezone_type ) = data
                
                self._data_text.setText( phrase )
                self._data_timezone_encode.SetValue( timezone_type )
                
            elif data is not None:
                
                if isinstance( data, int ):
                    
                    self._data_number.setValue( data )
                    
                else:
                    
                    self._data_text.setText( data )
                    
                
            
            #
            
            rows = []
            
            # This mess needs to be all replaced with a nice QFormLayout subclass that can do row hide/show
            # or just a whole separate panel for each transformation type, but w/e
            
            self._data_text_label = ClientGUICommon.BetterStaticText( self, 'string data: ' )
            self._data_number_label = ClientGUICommon.BetterStaticText( self, 'number data: ' )
            self._data_encoding_label = ClientGUICommon.BetterStaticText( self, 'encoding data: ' )
            self._data_regex_repl_label = ClientGUICommon.BetterStaticText( self, 'regex replacement: ' )
            self._data_date_link_label = ClientGUICommon.BetterStaticText( self, 'date info: ' )
            self._data_timezone_decode_label = ClientGUICommon.BetterStaticText( self, 'date decode timezone: ' )
            self._data_timezone_offset_label = ClientGUICommon.BetterStaticText( self, 'timezone offset: ' )
            self._data_timezone_encode_label = ClientGUICommon.BetterStaticText( self, 'date encode timezone: ' )
            
            rows.append( ( 'example string: ', self._example_string ) )
            rows.append( ( 'transformed string: ', self._example_transformation ) )
            rows.append( ( 'transformation type: ', self._transformation_type ) )
            rows.append( ( self._data_text_label, self._data_text ) )
            rows.append( ( self._data_number_label, self._data_number ) )
            rows.append( ( self._data_encoding_label, self._data_encoding ) )
            rows.append( ( self._data_regex_repl_label, self._data_regex_repl ) )
            rows.append( ( self._data_date_link_label, self._data_date_link ) )
            rows.append( ( self._data_timezone_decode_label, self._data_timezone_decode ) )
            rows.append( ( self._data_timezone_offset_label, self._data_timezone_offset ) )
            rows.append( ( self._data_timezone_encode_label, self._data_timezone_encode ) )
            
            self._control_gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._control_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.widget().setLayout( vbox )
            
            self._UpdateDataControls()
            
            #
            
            self._transformation_type.currentIndexChanged.connect( self._UpdateDataControls )
            self._transformation_type.currentIndexChanged.connect( self._UpdateExampleText )
            
            self._data_text.textEdited.connect( self._UpdateExampleText )
            self._data_number.valueChanged.connect( self._UpdateExampleText )
            self._data_encoding.currentIndexChanged.connect( self._UpdateExampleText )
            self._data_regex_repl.textEdited.connect( self._UpdateExampleText )
            self._data_timezone_decode.currentIndexChanged.connect( self._UpdateExampleText )
            self._data_timezone_offset.valueChanged.connect( self._UpdateExampleText )
            self._data_timezone_encode.currentIndexChanged.connect( self._UpdateExampleText )
            
            self._data_timezone_decode.currentIndexChanged.connect( self._UpdateDataControls )
            self._data_timezone_encode.currentIndexChanged.connect( self._UpdateDataControls )
            
            self._UpdateExampleText()
            
        
        def _UpdateDataControls( self ):
            
            self._data_text_label.setVisible( False )
            self._data_number_label.setVisible( False )
            self._data_encoding_label.setVisible( False )
            self._data_regex_repl_label.setVisible( False )
            self._data_date_link_label.setVisible( False )
            self._data_timezone_decode_label.setVisible( False )
            self._data_timezone_offset_label.setVisible( False )
            self._data_timezone_encode_label.setVisible( False )
            
            self._data_text.setVisible( False )
            self._data_number.setVisible( False )
            self._data_encoding.setVisible( False )
            self._data_regex_repl.setVisible( False )
            self._data_date_link.setVisible( False )
            self._data_timezone_decode.setVisible( False )
            self._data_timezone_offset.setVisible( False )
            self._data_timezone_encode.setVisible( False )
            
            transformation_type = self._transformation_type.GetValue()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                self._data_encoding_label.setVisible( True )
                self._data_encoding.setVisible( True )
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE, ClientParsing.STRING_TRANSFORMATION_REGEX_SUB ):
                
                self._data_text_label.setVisible( True )
                self._data_text.setVisible( True )
                
                data_text_label = 'string data: '
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT:
                    
                    data_text_label = 'text to prepend: '
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT:
                    
                    data_text_label = 'text to append: '
                    
                elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE ):
                    
                    self._data_date_link_label.setVisible( True )
                    self._data_date_link.setVisible( True )
                    
                    if transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                        
                        data_text_label = 'date decode phrase: '
                        
                        self._data_timezone_decode_label.setVisible( True )
                        self._data_timezone_decode.setVisible( True )
                        
                        if self._data_timezone_decode.GetValue() == HC.TIMEZONE_OFFSET:
                            
                            self._data_timezone_offset_label.setVisible( True )
                            self._data_timezone_offset.setVisible( True )
                            
                        
                    elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE:
                        
                        data_text_label = 'date encode phrase: '
                        
                        self._data_timezone_encode_label.setVisible( True )
                        self._data_timezone_encode.setVisible( True )
                        
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                    
                    data_text_label = 'regex pattern: '
                    
                    self._data_regex_repl_label.setVisible( True )
                    self._data_regex_repl.setVisible( True )
                    
                
                self._data_text_label.setText( data_text_label )
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._data_number_label.setVisible( True )
                self._data_number.setVisible( True )
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION:
                    
                    self._data_number.setMinimum( -65535 )
                    
                else:
                    
                    self._data_number.setMinimum( 0 )
                    
                
                data_number_label = 'number data: '
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING:
                    
                    data_number_label = 'characters to remove: '
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END:
                    
                    data_number_label = 'characters to remove: '
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING:
                    
                    data_number_label = 'characters to take: '
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END:
                    
                    data_number_label = 'characters to take: '
                    
                elif transformation_type == ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION:
                    
                    data_number_label = 'number to add: '
                    
                
                self._data_number_label.setText( data_number_label )
                
            
        
        def _UpdateExampleText( self ):
            
            try:
                
                transformations = [ self.GetValue() ]
                
                example_string = self._example_string.text()
                
                string_converter = ClientParsing.StringConverter( transformations, example_string )
                
                example_transformation = string_converter.Convert( example_string )
                
                try:
                    
                    self._example_transformation.setText( str( example_transformation ) )
                    
                except:
                    
                    self._example_transformation.setText( repr( example_transformation ) )
                    
                
            except Exception as e:
                
                self._example_transformation.setText( str( e ) )
                
            
        
        def GetValue( self ):
            
            transformation_type = self._transformation_type.GetValue()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                data = self._data_encoding.GetValue()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT ):
                
                data = self._data_text.text()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                data = self._data_number.value()
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                pattern = self._data_text.text()
                repl = self._data_regex_repl.text()
                
                data = ( pattern, repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                phrase = self._data_text.text()
                timezone_time = self._data_timezone_decode.GetValue()
                timezone_offset = self._data_timezone_offset.value()
                
                data = ( phrase, timezone_time, timezone_offset )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE:
                
                phrase = self._data_text.text()
                timezone_time = self._data_timezone_encode.GetValue()
                
                data = ( phrase, timezone_time )
                
            else:
                
                data = None
                
            
            return ( transformation_type, data )
            
        
    
class EditStringMatchPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_match = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if string_match is None:
            
            string_match = ClientParsing.StringMatch()
            
        
        self._match_type = ClientGUICommon.BetterChoice( self )
        
        self._match_type.addItem( 'any characters', ClientParsing.STRING_MATCH_ANY )
        self._match_type.addItem( 'fixed characters', ClientParsing.STRING_MATCH_FIXED )
        self._match_type.addItem( 'character set', ClientParsing.STRING_MATCH_FLEXIBLE )
        self._match_type.addItem( 'regex', ClientParsing.STRING_MATCH_REGEX )
        
        self._match_value_text_input = QW.QLineEdit( self )
        
        self._match_value_flexible_input = ClientGUICommon.BetterChoice( self )
        
        self._match_value_flexible_input.addItem( 'alphabetic characters (a-zA-Z)', ClientParsing.ALPHA )
        self._match_value_flexible_input.addItem( 'alphanumeric characters (a-zA-Z0-9)', ClientParsing.ALPHANUMERIC )
        self._match_value_flexible_input.addItem( 'numeric characters (0-9)', ClientParsing.NUMERIC )
        
        self._min_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        self._max_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        
        self._example_string = QW.QLineEdit( self )
        
        self._example_string_matches = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self.SetValue( string_match )
        
        #
        
        rows = []
        
        rows.append( ( 'match type: ', self._match_type ) )
        rows.append( ( 'match text: ', self._match_value_text_input ) )
        rows.append( ( 'match value (character set): ', self._match_value_flexible_input ) )
        rows.append( ( 'minimum allowed number of characters: ', self._min_chars ) )
        rows.append( ( 'maximum allowed number of characters: ', self._max_chars ) )
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_string_matches, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._match_type.currentIndexChanged.connect( self._UpdateControls )
        self._match_value_text_input.textChanged.connect( self._UpdateControls )
        self._match_value_flexible_input.currentIndexChanged.connect( self._UpdateControls )
        self._min_chars.valueChanged.connect( self._UpdateControls )
        self._max_chars.valueChanged.connect( self._UpdateControls )
        self._example_string.textChanged.connect( self._UpdateControls )
        
    
    def _GetValue( self ):
        
        match_type = self._match_type.GetValue()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            match_value = ''
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            match_value = self._match_value_flexible_input.GetValue()
            
        else:
            
            match_value = self._match_value_text_input.text()
            
        
        min_chars = self._min_chars.GetValue()
        max_chars = self._max_chars.GetValue()
        
        example_string = self._example_string.text()
        
        string_match = ClientParsing.StringMatch( match_type = match_type, match_value = match_value, min_chars = min_chars, max_chars = max_chars, example_string = example_string )
        
        return string_match
        
    
    def _UpdateControls( self ):
        
        match_type = self._match_type.GetValue()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            self._match_value_text_input.setEnabled( False )
            self._match_value_flexible_input.setEnabled( False )
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_text_input.setEnabled( False )
            self._match_value_flexible_input.setEnabled( True )
            
        else:
            
            self._match_value_text_input.setEnabled( True )
            self._match_value_flexible_input.setEnabled( False )
            
        
        if match_type == ClientParsing.STRING_MATCH_FIXED:
            
            self._min_chars.SetValue( None )
            self._max_chars.SetValue( None )
            
            self._min_chars.setEnabled( False )
            self._max_chars.setEnabled( False )
            
            self._example_string.blockSignals( True ) # Temporarily block the text changed signal here so we won't end up in infinite recursion
            self._example_string.setText( self._match_value_text_input.text() )
            self._example_string.blockSignals( False )
            
            self._example_string_matches.setText( '' )
            
        else:
            
            self._min_chars.setEnabled( True )
            self._max_chars.setEnabled( True )
            
            string_match = self._GetValue()
            
            try:
                
                string_match.Test( self._example_string.text() )
                
                self._example_string_matches.setText( 'Example matches ok!' )
                self._example_string_matches.setObjectName( 'HydrusValid' )
                self._example_string_matches.style().polish( self._example_string_matches )
                
            except HydrusExceptions.StringMatchException as e:
                
                reason = str( e )
                
                self._example_string_matches.setText( 'Example does not match - '+reason )
                self._example_string_matches.setObjectName( 'HydrusInvalid' )
                self._example_string_matches.style().polish( self._example_string_matches )
                
            
        
    
    def GetValue( self ):
        
        string_match = self._GetValue()
        
        try:
            
            string_match.Test( self._example_string.text() )
            
        except HydrusExceptions.StringMatchException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that matches the given rules!' )
            
        
        return string_match
        
    
    def SetValue( self, string_match ):
        
        ( match_type, match_value, min_chars, max_chars, example_string ) = string_match.ToTuple()
        
        self._match_type.SetValue( match_type )
        
        if match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_flexible_input.SetValue( match_value )
            
        else:
            
            self._match_value_flexible_input.SetValue( ClientParsing.ALPHA )
            
            self._match_value_text_input.setText( match_value )
            
        
        self._min_chars.SetValue( min_chars )
        self._max_chars.SetValue( max_chars )
        
        self._example_string.setText( example_string )
        
        self._UpdateControls()
        
    
class NoneableBytesControl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, initial_value = 65536, none_label = 'no limit' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._bytes = BytesControl( self )
        
        self._none_checkbox = QW.QCheckBox( none_label, self )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_SIZER_VCENTER )
        QP.AddToLayout( hbox, self._none_checkbox, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
        #
        
        self._none_checkbox.clicked.connect( self._UpdateEnabled )
        
        self._bytes.valueChanged.connect( self._HandleValueChanged )
        self._none_checkbox.clicked.connect( self._HandleValueChanged )
        
    
    def _UpdateEnabled( self ):
        
        if self._none_checkbox.isChecked():
            
            self._bytes.setEnabled( False )
            
        else:
            
            self._bytes.setEnabled( True )
            
        
    
    def _HandleValueChanged( self ):
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        if self._none_checkbox.isChecked():
            
            return None
            
        else:
            
            return self._bytes.GetValue()
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._none_checkbox.setChecked( True )
            
        else:
            
            self._none_checkbox.setChecked( False )
            
            self._bytes.SetValue( value )
            
        
        self._UpdateEnabled()
        
    
class NetworkJobControl( QW.QFrame ):
    
    def __init__( self, parent ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        self._network_job = None
        self._download_started = False
        
        self._auto_override_bandwidth_rules = False
        
        self._left_text = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._right_text = ClientGUICommon.BetterStaticText( self )
        self._right_text.setAlignment( QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        
        self._last_right_min_width = 0
        
        self._gauge = ClientGUICommon.Gauge( self )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().cog, self._ShowCogMenu )
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, self.Cancel )
        
        #
        
        self._Update()
        
        #
        
        st_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( st_hbox, self._left_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( st_hbox, self._right_text, CC.FLAGS_VCENTER )
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, st_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cog_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
    
    def _ShowCogMenu( self ):
        
        menu = QW.QMenu()
        
        if self._network_job is not None:
            
            if self._network_job.CurrentlyWaitingOnConnectionError():
                
                ClientGUIMenus.AppendMenuItem( menu, 'reattempt connection now', 'Stop waiting on a connection error and reattempt the job now.', self._network_job.OverrideConnectionErrorWait )
                
            
            if self._network_job.CurrentlyWaitingOnServersideBandwidth():
                
                ClientGUIMenus.AppendMenuItem( menu, 'reattempt request now (server reports low bandwidth)', 'Stop waiting on a serverside bandwidth delay and reattempt the job now.', self._network_job.OverrideServersideBandwidthWait )
                
            
            if self._network_job.ObeysBandwidth():
                
                ClientGUIMenus.AppendMenuItem( menu, 'override bandwidth rules for this job', 'Tell the current job to ignore existing bandwidth rules and go ahead anyway.', self._network_job.OverrideBandwidth )
                
            
            if not self._network_job.TokensOK():
                
                ClientGUIMenus.AppendMenuItem( menu, 'override gallery slot requirements for this job', 'Force-allow this download to proceed, ignoring the normal gallery wait times.', self._network_job.OverrideToken )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'auto-override bandwidth rules for all jobs here after five seconds', 'Ignore existing bandwidth rules for all jobs under this control, instead waiting a flat five seconds.', self._auto_override_bandwidth_rules, self.FlipAutoOverrideBandwidth )
        
        CGC.core().PopupMenu( self._cog_button, menu )
        
    
    def _OverrideBandwidthIfAppropriate( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            return
            
        else:
            
            if self._auto_override_bandwidth_rules and HydrusData.TimeHasPassed( self._network_job.GetCreationTime() + 5 ):
                
                self._network_job.OverrideBandwidth()
                
            
        
    
    def _Update( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            self._left_text.setText( '' )
            self._right_text.setText( '' )
            self._gauge.SetRange( 1 )
            self._gauge.SetValue( 0 )
            
            can_cancel = False
            
        else:
            
            if self._network_job.IsDone():
                
                can_cancel = False
                
            else:
                
                can_cancel = True
                
            
            ( status_text, current_speed, bytes_read, bytes_to_read ) = self._network_job.GetStatus()
            
            self._left_text.setText( status_text )
            
            if not self._download_started and current_speed > 0:
                
                self._download_started = True
                
            
            speed_text = ''
            
            if self._download_started and not self._network_job.HasError():
                
                if bytes_read is not None:
                    
                    if bytes_to_read is not None and bytes_read != bytes_to_read:
                        
                        speed_text += HydrusData.ConvertValueRangeToBytes( bytes_read, bytes_to_read )
                        
                    else:
                        
                        speed_text += HydrusData.ToHumanBytes( bytes_read )
                        
                    
                
                if current_speed != bytes_to_read: # if it is a real quick download, just say its size
                    
                    speed_text += ' ' + HydrusData.ToHumanBytes( current_speed ) + '/s'
                    
                
            
            self._right_text.setText( speed_text )
            
            right_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._right_text, len( speed_text ) )
            
            right_min_width = right_width
            
            if right_min_width != self._last_right_min_width:
                
                self._last_right_min_width = right_min_width
                
                self._right_text.setMinimumWidth( right_min_width )
                
            
            self._gauge.SetRange( bytes_to_read )
            self._gauge.SetValue( bytes_read )
            
        
        if can_cancel:
            
            if not self._cancel_button.isEnabled():
                
                self._cancel_button.setEnabled( True )
                
            
        else:
            
            if self._cancel_button.isEnabled():
                
                self._cancel_button.setEnabled( False )
                
            
        
    
    def Cancel( self ):
        
        if self._network_job is not None:
            
            self._network_job.Cancel( 'Cancelled by user.' )
            
        
    
    def ClearNetworkJob( self ):
        
        self.SetNetworkJob( None )
        
    
    def FlipAutoOverrideBandwidth( self ):
        
        self._auto_override_bandwidth_rules = not self._auto_override_bandwidth_rules
        
    
    def SetNetworkJob( self, network_job ):
        
        if network_job is None:
            
            if self._network_job is not None:
                
                self._network_job = None
                
                self._Update()
                
                HG.client_controller.gui.UnregisterUIUpdateWindow( self )
                
            
        else:
            
            if self._network_job != network_job:
                
                self._network_job = network_job
                self._download_started = False
                
                HG.client_controller.gui.RegisterUIUpdateWindow( self )
                
            
        
    
    def TIMERUIUpdate( self ):
        
        self._OverrideBandwidthIfAppropriate()
        
        if HG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
class StringConverterButton( ClientGUICommon.BetterButton ):
    
    stringConverterUpdate = QC.Signal()
    
    def __init__( self, parent, string_converter ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._example_string_override = None
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string converter', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditStringConverterPanel( dlg, self._string_converter, example_string_override = self._example_string_override )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        self.stringConverterUpdate.emit()
        
    
    def _UpdateLabel( self ):
        
        num_rules = len( self._string_converter.transformations )
        
        if num_rules == 0:
            
            label = 'no string transformations'
            
        else:
            
            label = HydrusData.ToHumanInt( num_rules ) + ' string transformations'
            
        
        self.setText( label )
        
    
    def GetValue( self ):
        
        return self._string_converter
        
    
    def SetExampleString( self, example_string ):
        
        self._example_string_override = example_string
        
    
    def SetValue( self, string_converter ):
        
        self._string_converter = string_converter
        
        self._UpdateLabel()
        
    
class StringMatchButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_match ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string match', self._Edit )
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string match', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditStringMatchPanel( dlg, self._string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._string_match = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_match.ToString()
        
        self.setText( label )
        
    
    def GetValue( self ):
        
        return self._string_match
        
    
    def SetValue( self, string_match ):
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
class StringMatchToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( self._key_name, 20 ), ( 'matching', -1 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'key_to_string_match', min_height, 36, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
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
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
            
            string_match = ClientParsing.StringMatch()
            
            panel = EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
            
            string_match = ClientParsing.StringMatch()
            
            panel = EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value_string_match = panel.GetValue()
                
                data = ( key_string_match, value_string_match )
                
                self._listctrl.AddDatas( ( data, ) )
                
            
        
    
    def _Edit( self ):
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key_string_match, value_string_match ) = data
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
                
                panel = EditStringMatchPanel( dlg, key_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    key_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                
                panel = EditStringMatchPanel( dlg, value_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    value_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            edited_data = ( key_string_match, value_string_match )
            
            self._listctrl.AddDatas( ( edited_data, ) )
            
        
        self._listctrl.Sort()
        
    
    def GetValue( self ):
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class StringToStringDictButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._value = {}
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string dictionary' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = StringToStringDictControl( panel, self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._value = control.GetValue()
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
    
class StringToStringDictControl( QW.QWidget ):
    
    listCtrlChanged = QC.Signal()
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key', value_name = 'value', allow_add_delete = True, edit_keys = True ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        self._value_name = value_name
        
        self._edit_keys = edit_keys
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( self._key_name, 20 ), ( self._value_name, -1 ) ]
        
        use_simple_delete = allow_add_delete
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'key_to_value', min_height, 36, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = use_simple_delete, activation_callback = self._Edit )
        self._listctrl.listCtrlChanged.connect( self.listCtrlChanged )
        
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
            
        
        self._listctrl.Sort()
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def GetValue( self ):
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class StringToStringMatchDictControl( QW.QWidget ):
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._key_name = key_name
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( self._key_name, 20 ), ( 'matching', -1 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'key_to_string_match', min_height, 36, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
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
                    
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                    
                    string_match = ClientParsing.StringMatch()
                    
                    panel = EditStringMatchPanel( dlg, string_match )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        string_match = panel.GetValue()
                        
                        data = ( key, string_match )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Edit( self ):
        
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
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                
                string_match = ClientParsing.StringMatch()
                
                panel = EditStringMatchPanel( dlg, string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            edited_data = ( edited_key, edited_string_match )
            
            self._listctrl.AddDatas( ( edited_data, ) )
            
        
        self._listctrl.Sort()
        
    
    def _GetExistingKeys( self ):
        
        return { key for ( key, value ) in self._listctrl.GetData() }
        
    
    def GetValue( self ):
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class TextAndPasteCtrl( QW.QWidget ):
    
    def __init__( self, parent, add_callable, allow_empty_input = False ):
        
        self._add_callable = add_callable
        self._allow_empty_input = allow_empty_input
        
        QW.QWidget.__init__( self, parent )
        
        self._text_input = QW.QLineEdit( self )
        self._text_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._text_input, self.EnterText ) )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste multiple inputs from the clipboard. Assumes the texts are newline-separated.' )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._text_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            texts = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            if not self._allow_empty_input:
                
                texts = [ text for text in texts if text != '' ]
                
            
            if len( texts ) > 0:
                
                self._add_callable( texts )
                
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
    
    def EnterText( self ):
        
        text = self._text_input.text()
        
        text = HydrusText.StripIOInputLine( text )
        
        if text == '' and not self._allow_empty_input:
            
            return
            
        
        self._add_callable( ( text, ) )
        
        self._text_input.setText( '' )
        
    
    def GetValue( self ):
        
        return self._text_input.text()
        
    
    def setPlaceholderText( self, text ):
        
        self._text_input.setPlaceholderText( text )
        
    
    def SetValue( self, text ):
        
        self._text_input.setText( text )
        
    
