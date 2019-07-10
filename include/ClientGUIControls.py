from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIFunctions
from . import ClientGUIListCtrl
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUIShortcuts
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientParsing
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusText
import os
import wx

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
            
            if dlg.ShowModal() == wx.ID_OK:
                
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
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
            
            self._bandwidth_type.Append( 'data', HC.BANDWIDTH_TYPE_DATA )
            self._bandwidth_type.Append( 'requests', HC.BANDWIDTH_TYPE_REQUESTS )
            
            self._bandwidth_type.Bind( wx.EVT_CHOICE, self.EventBandwidth )
            
            self._max_allowed_bytes = BytesControl( self )
            self._max_allowed_requests = wx.SpinCtrl( self, min = 1, max = 1048576 )
            
            self._time_delta = ClientGUITime.TimeDeltaButton( self, min = 1, days = True, hours = True, minutes = True, seconds = True, monthly_allowed = True )
            
            #
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            self._bandwidth_type.SelectClientData( bandwidth_type )
            
            self._time_delta.SetValue( time_delta )
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.SetValue( max_allowed )
                
            else:
                
                self._max_allowed_requests.SetValue( max_allowed )
                
            
            self._UpdateEnabled()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._max_allowed_bytes, CC.FLAGS_VCENTER )
            hbox.Add( self._max_allowed_requests, CC.FLAGS_VCENTER )
            hbox.Add( self._bandwidth_type, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, ' every ' ), CC.FLAGS_VCENTER )
            hbox.Add( self._time_delta, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
        
        def _UpdateEnabled( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.Show()
                self._max_allowed_requests.Hide()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                self._max_allowed_bytes.Hide()
                self._max_allowed_requests.Show()
                
            
            self.Layout()
            
        
        def EventBandwidth( self, event ):
            
            self._UpdateEnabled()
            
        
        def GetValue( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            time_delta = self._time_delta.GetValue()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                max_allowed = self._max_allowed_bytes.GetValue()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                max_allowed = self._max_allowed_requests.GetValue()
                
            
            return ( bandwidth_type, time_delta, max_allowed )
            
        
    
class BytesControl( wx.Panel ):
    
    def __init__( self, parent, initial_value = 65536 ):
        
        wx.Panel.__init__( self, parent )
        
        self._spin = wx.SpinCtrl( self, min = 0, max = 1048576 )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._spin, 12 )
        
        self._spin.SetSize( ( width, -1 ) )
        
        self._unit = ClientGUICommon.BetterChoice( self )
        
        self._unit.Append( 'B', 1 )
        self._unit.Append( 'KB', 1024 )
        self._unit.Append( 'MB', 1024 * 1024 )
        self._unit.Append( 'GB', 1024 * 1024 * 1024 )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._spin, CC.FLAGS_VCENTER )
        hbox.Add( self._unit, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def Bind( self, event_type, callback ):
        
        self._spin.Bind( wx.EVT_SPINCTRL, callback )
        
        self._unit.Bind( wx.EVT_CHOICE, callback )
        
    
    def Disable( self ):
        
        self._spin.Disable()
        self._unit.Disable()
        
    
    def Enable( self ):
        
        self._spin.Enable()
        self._unit.Enable()
        
    
    def GetSeparatedValue( self ):
        
        return ( self._spin.GetValue(), self._unit.GetChoice() )
        
    
    def GetValue( self ):
        
        return self._spin.GetValue() * self._unit.GetChoice()
        
    
    def SetSeparatedValue( self, value, unit ):
        
        return ( self._spin.SetValue( value ), self._unit.SelectClientData( unit ) )
        
    
    def SetValue( self, value ):
        
        max_unit = 1024 * 1024 * 1024
        
        unit = 1
        
        while value % 1024 == 0 and unit < max_unit:
            
            value //= 1024
            
            unit *= 1024
            
        
        self._spin.SetValue( value )
        self._unit.SelectClientData( unit )
        
    
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
        
        self._example_string = wx.TextCtrl( self )
        
        #
        
        self._transformations.AddDatas( [ ( i + 1, transformation_type, data ) for ( i, ( transformation_type, data ) ) in enumerate( string_converter.transformations ) ] )
        
        if example_string_override is None:
            
            self._example_string.SetValue( string_converter.example_string )
            
        else:
            
            self._example_string.SetValue( example_string_override )
            
        
        self._transformations.UpdateDatas() # to refresh, now they are all in the list
        
        self._transformations.Sort( 0 )
        
        #
        
        rows = []
        
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( transformations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._example_string.Bind( wx.EVT_TEXT, self.EventUpdate )
        
    
    def _AddTransformation( self ):
        
        transformation_type = ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT
        data = ' extra text'
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = self._TransformationPanel( dlg, transformation_type, data )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                number = self._transformations.GetItemCount() + 1
                
                ( transformation_type, data ) = panel.GetValue()
                
                enumerated_transformation = ( number, transformation_type, data )
                
                self._transformations.AddDatas( ( enumerated_transformation, ) )
                
            
        
        self._transformations.UpdateDatas() # need to refresh string after the insertion, so the new row can be included in the parsing calcs
        
        self._transformations.Sort()
        
    
    def _CanMoveDown( self ):
        
        selected_data = self._transformations.GetData( only_selected = True )
        
        if len( selected_data ) == 1:
            
            ( number, transformation_type, data ) = selected_data[0]
            
            if number < self._transformations.GetItemCount():
                
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
            
            pretty_result = ClientParsing.MakeParsedTextPretty( string_converter.Convert( self._example_string.GetValue(), number ) )
            
        except HydrusExceptions.StringConvertException as e:
            
            pretty_result = str( e )
            
        
        display_tuple = ( pretty_number, pretty_transformation, pretty_result )
        sort_tuple = ( number, number, number )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteTransformation( self ):
        
        if len( self._transformations.GetData( only_selected = True ) ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Delete all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._transformations.DeleteSelected()
                    
                
            
        
        # now we need to shuffle up any missing numbers
        
        num_rows = self._transformations.GetItemCount()
        
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit transformation', frame_key = 'deeply_nested_dialog' ) as dlg:
                
                panel = self._TransformationPanel( dlg, transformation_type, data )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
        
        example_string = self._example_string.GetValue()
        
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
            
        
    
    def EventUpdate( self, event ):
        
        self._transformations.UpdateDatas()
        
    
    def GetValue( self ):
        
        string_converter = self._GetValue()
        
        try:
            
            string_converter.Convert( self._example_string.GetValue() )
            
        except HydrusExceptions.StringConvertException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that can be converted!' )
            
        
        return string_converter
        
    
    class _TransformationPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, transformation_type, data ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._transformation_type = ClientGUICommon.BetterChoice( self )
            
            for t_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_REVERSE, ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._transformation_type.Append( ClientParsing.transformation_type_str_lookup[ t_type ], t_type )
                
            
            self._data_text = wx.TextCtrl( self )
            self._data_number = wx.SpinCtrl( self, min = 0, max = 65535 )
            self._data_encoding = ClientGUICommon.BetterChoice( self )
            self._data_regex_pattern = wx.TextCtrl( self )
            self._data_regex_repl = wx.TextCtrl( self )
            self._data_date_link = ClientGUICommon.BetterHyperLink( self, 'link to date info', 'https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior' )
            self._data_timezone = ClientGUICommon.BetterChoice( self )
            self._data_timezone_offset = wx.SpinCtrl( self, min = -86400, max = 86400 )
            
            for e in ( 'hex', 'base64' ):
                
                self._data_encoding.Append( e, e )
                
            
            self._data_timezone.Append( 'GMT', HC.TIMEZONE_GMT )
            self._data_timezone.Append( 'Local', HC.TIMEZONE_LOCAL )
            self._data_timezone.Append( 'Offset', HC.TIMEZONE_OFFSET )
            
            #
            
            self._transformation_type.SelectClientData( transformation_type )
            
            self._UpdateDataControls()
            
            #
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_DECODE, ClientParsing.STRING_TRANSFORMATION_ENCODE ):
                
                self._data_encoding.SelectClientData( data )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                ( pattern, repl ) = data
                
                self._data_regex_pattern.SetValue( pattern )
                self._data_regex_repl.SetValue( repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                ( phrase, timezone_type, timezone_offset ) = data
                
                self._data_text.SetValue( phrase )
                self._data_timezone.SelectClientData( timezone_type )
                self._data_timezone_offset.SetValue( timezone_offset )
                
            elif data is not None:
                
                if isinstance( data, int ):
                    
                    self._data_number.SetValue( data )
                    
                else:
                    
                    self._data_text.SetValue( data )
                    
                
            
            #
            
            rows = []
            
            rows.append( ( 'string data: ', self._data_text ) )
            rows.append( ( 'number data: ', self._data_number ) )
            rows.append( ( 'encoding data: ', self._data_encoding ) )
            rows.append( ( 'regex pattern: ', self._data_regex_pattern ) )
            rows.append( ( 'regex replacement: ', self._data_regex_repl ) )
            rows.append( ( 'date info: ', self._data_date_link ) )
            rows.append( ( 'date timezone: ', self._data_timezone ) )
            rows.append( ( 'timezone offset: ', self._data_timezone_offset ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._transformation_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            #
            
            self._transformation_type.Bind( wx.EVT_CHOICE, self.EventChoice )
            self._data_timezone.Bind( wx.EVT_CHOICE, self.EventChoice )
            
        
        def _UpdateDataControls( self ):
            
            self._data_text.Disable()
            self._data_number.Disable()
            self._data_encoding.Disable()
            self._data_regex_pattern.Disable()
            self._data_regex_repl.Disable()
            self._data_timezone.Disable()
            self._data_timezone_offset.Disable()
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                self._data_encoding.Enable()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_DATE_DECODE ):
                
                self._data_text.Enable()
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                    
                    self._data_timezone.Enable()
                    
                    if self._data_timezone.GetChoice() == HC.TIMEZONE_OFFSET:
                        
                        self._data_timezone_offset.Enable()
                        
                    
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                self._data_number.Enable()
                
                if transformation_type == ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION:
                    
                    self._data_number.SetMin( -65535 )
                    
                else:
                    
                    self._data_number.SetMin( 0 )
                    
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                self._data_regex_pattern.Enable()
                self._data_regex_repl.Enable()
                
            
        
        def EventChoice( self, event ):
            
            self._UpdateDataControls()
            
        
        def GetValue( self ):
            
            transformation_type = self._transformation_type.GetChoice()
            
            if transformation_type in ( ClientParsing.STRING_TRANSFORMATION_ENCODE, ClientParsing.STRING_TRANSFORMATION_DECODE ):
                
                data = self._data_encoding.GetChoice()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT ):
                
                data = self._data_text.GetValue()
                
            elif transformation_type in ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION ):
                
                data = self._data_number.GetValue()
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_REGEX_SUB:
                
                pattern = self._data_regex_pattern.GetValue()
                repl = self._data_regex_repl.GetValue()
                
                data = ( pattern, repl )
                
            elif transformation_type == ClientParsing.STRING_TRANSFORMATION_DATE_DECODE:
                
                phrase = self._data_text.GetValue()
                timezone_time = self._data_timezone.GetChoice()
                timezone_offset = self._data_timezone_offset.GetValue()
                
                data = ( phrase, timezone_time, timezone_offset )
                
            else:
                
                data = None
                
            
            return ( transformation_type, data )
            
        
    
class EditStringMatchPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, string_match = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if string_match is None:
            
            string_match = ClientParsing.StringMatch()
            
        
        self._match_type = ClientGUICommon.BetterChoice( self )
        
        self._match_type.Append( 'any characters', ClientParsing.STRING_MATCH_ANY )
        self._match_type.Append( 'fixed characters', ClientParsing.STRING_MATCH_FIXED )
        self._match_type.Append( 'character set', ClientParsing.STRING_MATCH_FLEXIBLE )
        self._match_type.Append( 'regex', ClientParsing.STRING_MATCH_REGEX )
        
        self._match_value_text_input = wx.TextCtrl( self )
        
        self._match_value_flexible_input = ClientGUICommon.BetterChoice( self )
        
        self._match_value_flexible_input.Append( 'alphabetic characters (a-zA-Z)', ClientParsing.ALPHA )
        self._match_value_flexible_input.Append( 'alphanumeric characters (a-zA-Z0-9)', ClientParsing.ALPHANUMERIC )
        self._match_value_flexible_input.Append( 'numeric characters (0-9)', ClientParsing.NUMERIC )
        
        self._min_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        self._max_chars = ClientGUICommon.NoneableSpinCtrl( self, min = 1, max = 65535, unit = 'characters', none_phrase = 'no limit' )
        
        self._example_string = wx.TextCtrl( self )
        
        self._example_string_matches = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self.SetValue( string_match )
        
        #
        
        rows = []
        
        rows.append( ( 'match type: ', self._match_type ) )
        rows.append( ( 'match text: ', self._match_value_text_input ) )
        rows.append( ( 'match value (character set): ', self._match_value_flexible_input ) )
        rows.append( ( 'minumum allowed number of characters: ', self._min_chars ) )
        rows.append( ( 'maximum allowed number of characters: ', self._max_chars ) )
        rows.append( ( 'example string: ', self._example_string ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._example_string_matches, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._match_type.Bind( wx.EVT_CHOICE, self.EventUpdate )
        self._match_value_text_input.Bind( wx.EVT_TEXT, self.EventUpdate )
        self._match_value_flexible_input.Bind( wx.EVT_CHOICE, self.EventUpdate )
        self._min_chars.Bind( wx.EVT_SPINCTRL, self.EventUpdate )
        self._max_chars.Bind( wx.EVT_SPINCTRL, self.EventUpdate )
        self._example_string.Bind( wx.EVT_TEXT, self.EventUpdate )
        
    
    def _GetValue( self ):
        
        match_type = self._match_type.GetChoice()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            match_value = ''
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            match_value = self._match_value_flexible_input.GetChoice()
            
        else:
            
            match_value = self._match_value_text_input.GetValue()
            
        
        min_chars = self._min_chars.GetValue()
        max_chars = self._max_chars.GetValue()
        
        example_string = self._example_string.GetValue()
        
        string_match = ClientParsing.StringMatch( match_type = match_type, match_value = match_value, min_chars = min_chars, max_chars = max_chars, example_string = example_string )
        
        return string_match
        
    
    def _UpdateControls( self ):
        
        match_type = self._match_type.GetChoice()
        
        if match_type == ClientParsing.STRING_MATCH_ANY:
            
            self._match_value_text_input.Disable()
            self._match_value_flexible_input.Disable()
            
        elif match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_text_input.Disable()
            self._match_value_flexible_input.Enable()
            
        else:
            
            self._match_value_text_input.Enable()
            self._match_value_flexible_input.Disable()
            
        
        if match_type == ClientParsing.STRING_MATCH_FIXED:
            
            self._min_chars.SetValue( None )
            self._max_chars.SetValue( None )
            
            self._min_chars.Disable()
            self._max_chars.Disable()
            
            self._example_string.ChangeValue( self._match_value_text_input.GetValue() )
            
            self._example_string_matches.SetLabelText( '' )
            
        else:
            
            self._min_chars.Enable()
            self._max_chars.Enable()
            
            string_match = self._GetValue()
            
            try:
                
                string_match.Test( self._example_string.GetValue() )
                
                self._example_string_matches.SetLabelText( 'Example matches ok!' )
                self._example_string_matches.SetForegroundColour( ( 0, 128, 0 ) )
                
            except HydrusExceptions.StringMatchException as e:
                
                reason = str( e )
                
                self._example_string_matches.SetLabelText( 'Example does not match - ' + reason )
                self._example_string_matches.SetForegroundColour( ( 128, 0, 0 ) )
                
            
        
    
    def EventUpdate( self, event ):
        
        self._UpdateControls()
        
        event.Skip()
        
    
    def GetValue( self ):
        
        string_match = self._GetValue()
        
        try:
            
            string_match.Test( self._example_string.GetValue() )
            
        except HydrusExceptions.StringMatchException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example text that matches the given rules!' )
            
        
        return string_match
        
    
    def SetValue( self, string_match ):
        
        ( match_type, match_value, min_chars, max_chars, example_string ) = string_match.ToTuple()
        
        self._match_type.SelectClientData( match_type )
        
        if match_type == ClientParsing.STRING_MATCH_FLEXIBLE:
            
            self._match_value_flexible_input.SelectClientData( match_value )
            
        else:
            
            self._match_value_flexible_input.SelectClientData( ClientParsing.ALPHA )
            
            self._match_value_text_input.SetValue( match_value )
            
        
        self._min_chars.SetValue( min_chars )
        self._max_chars.SetValue( max_chars )
        
        self._example_string.SetValue( example_string )
        
        self._UpdateControls()
        
    
class NoneableBytesControl( wx.Panel ):
    
    def __init__( self, parent, initial_value = 65536, none_label = 'no limit' ):
        
        wx.Panel.__init__( self, parent )
        
        self._bytes = BytesControl( self )
        
        self._none_checkbox = wx.CheckBox( self, label = none_label )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._bytes, CC.FLAGS_SIZER_VCENTER )
        hbox.Add( self._none_checkbox, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        #
        
        self._none_checkbox.Bind( wx.EVT_CHECKBOX, self.EventNoneChecked )
        
    
    def _UpdateEnabled( self ):
        
        if self._none_checkbox.GetValue():
            
            self._bytes.Disable()
            
        else:
            
            self._bytes.Enable()
            
        
    
    def EventNoneChecked( self, event ):
        
        self._UpdateEnabled()
        
    
    def Bind( self, event_type, callback ):
        
        self._bytes.Bind( wx.EVT_SPINCTRL, callback )
        
        self._none_checkbox.Bind( wx.EVT_CHECKBOX, callback )
        
    
    def GetValue( self ):
        
        if self._none_checkbox.GetValue():
            
            return None
            
        else:
            
            return self._bytes.GetValue()
            
        
    
    def SetToolTip( self, text ):
        
        wx.Panel.SetToolTip( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._none_checkbox.SetValue( True )
            
        else:
            
            self._none_checkbox.SetValue( False )
            
            self._bytes.SetValue( value )
            
        
        self._UpdateEnabled()
        
    
class NetworkJobControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._network_job = None
        self._download_started = False
        
        self._auto_override_bandwidth_rules = False
        
        self._left_text = ClientGUICommon.BetterStaticText( self, style = wx.ST_ELLIPSIZE_END )
        self._right_text = ClientGUICommon.BetterStaticText( self, style = wx.ALIGN_RIGHT )
        
        self._last_right_min_width = ( -1, -1 )
        
        self._gauge = ClientGUICommon.Gauge( self )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.cog, self._ShowCogMenu )
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.stop, self.Cancel )
        
        #
        
        self._Update()
        
        #
        
        st_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st_hbox.Add( self._left_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        st_hbox.Add( self._right_text, CC.FLAGS_VCENTER )
        
        left_vbox = wx.BoxSizer( wx.VERTICAL )
        
        left_vbox.Add( st_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        left_vbox.Add( self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        hbox.Add( self._cog_button, CC.FLAGS_VCENTER )
        hbox.Add( self._cancel_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def _ShowCogMenu( self ):
        
        menu = wx.Menu()
        
        if self._network_job is not None:
            
            if self._network_job.ObeysBandwidth():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'override bandwidth rules for this job', 'Tell the current job to ignore existing bandwidth rules and go ahead anyway.', self._network_job.OverrideBandwidth )
                
            
            if not self._network_job.TokensOK():
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'override gallery slot requirements for this job', 'Force-allow this download to proceed, ignoring the normal gallery wait times.', self._network_job.OverrideToken )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuCheckItem( self, menu, 'auto-override bandwidth rules for all jobs here after five seconds', 'Ignore existing bandwidth rules for all jobs under this control, instead waiting a flat five seconds.', self._auto_override_bandwidth_rules, self.FlipAutoOverrideBandwidth )
        
        HG.client_controller.PopupMenu( self._cog_button, menu )
        
    
    def _OverrideBandwidthIfAppropriate( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            return
            
        else:
            
            if self._auto_override_bandwidth_rules and HydrusData.TimeHasPassed( self._network_job.GetCreationTime() + 5 ):
                
                self._network_job.OverrideBandwidth()
                
            
        
    
    def _Update( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            self._left_text.SetLabelText( '' )
            self._right_text.SetLabelText( '' )
            self._gauge.SetRange( 1 )
            self._gauge.SetValue( 0 )
            
            can_cancel = False
            
        else:
            
            if self._network_job.IsDone():
                
                can_cancel = False
                
            else:
                
                can_cancel = True
                
            
            ( status_text, current_speed, bytes_read, bytes_to_read ) = self._network_job.GetStatus()
            
            self._left_text.SetLabelText( status_text )
            
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
                    
                
            
            self._right_text.SetLabelText( speed_text )
            
            right_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._right_text, len( speed_text ) )
            
            right_min_size = ( right_width, -1 )
            
            if right_min_size != self._last_right_min_width:
                
                self._last_right_min_width = right_min_size
                
                self._right_text.SetMinSize( right_min_size )
                
                self.Layout()
                
            
            self._gauge.SetRange( bytes_to_read )
            self._gauge.SetValue( bytes_read )
            
        
        if can_cancel:
            
            if not self._cancel_button.IsEnabled():
                
                self._cancel_button.Enable()
                
            
        else:
            
            if self._cancel_button.IsEnabled():
                
                self._cancel_button.Disable()
                
            
        
    
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
            
        
    
( StringConverterEvent, EVT_STRING_CONVERTER ) = wx.lib.newevent.NewCommandEvent()

class StringConverterButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, string_converter ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'edit string converter', self._Edit )
        
        self._string_converter = string_converter
        
        self._example_string_override = None
        
        self._UpdateLabel()
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string converter', frame_key = 'deeply_nested_dialog' ) as dlg:
            
            panel = EditStringConverterPanel( dlg, self._string_converter, example_string_override = self._example_string_override )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._string_converter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
        wx.QueueEvent( self.GetEventHandler(), StringConverterEvent( -1 ) )
        
    
    def _UpdateLabel( self ):
        
        num_rules = len( self._string_converter.transformations )
        
        if num_rules == 0:
            
            label = 'no string transformations'
            
        else:
            
            label = HydrusData.ToHumanInt( num_rules ) + ' string transformations'
            
        
        self.SetLabelText( label )
        
    
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
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._string_match = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        label = self._string_match.ToString()
        
        self.SetLabelText( label )
        
    
    def GetValue( self ):
        
        return self._string_match
        
    
    def SetValue( self, string_match ):
        
        self._string_match = string_match
        
        self._UpdateLabel()
        
    
class StringMatchToStringMatchDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key' ):
        
        wx.Panel.__init__( self, parent )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
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
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key_string_match = panel.GetValue()
                
            else:
                
                return
                
            
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
            
            string_match = ClientParsing.StringMatch()
            
            panel = EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                value_string_match = panel.GetValue()
                
                data = ( key_string_match, value_string_match )
                
                self._listctrl.AddDatas( ( data, ) )
                
            
        
    
    def _Edit( self ):
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key_string_match, value_string_match ) = data
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit ' + self._key_name ) as dlg:
                
                panel = EditStringMatchPanel( dlg, key_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    key_string_match = panel.GetValue()
                    
                else:
                    
                    break
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                
                panel = EditStringMatchPanel( dlg, value_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._value = control.GetValue()
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
    
class StringToStringDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key', value_name = 'value', allow_add_delete = True, edit_keys = True ):
        
        wx.Panel.__init__( self, parent )
        
        self._key_name = key_name
        self._value_name = value_name
        
        self._edit_keys = edit_keys
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( self._key_name, 20 ), ( self._value_name, -1 ) ]
        
        use_simple_delete = allow_add_delete
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'key_to_value', min_height, 36, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = use_simple_delete, activation_callback = self._Edit )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key, value ) = data
        
        display_tuple = ( key, value )
        sort_tuple = ( key, value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    wx.MessageBox( 'That ' + self._key_name + ' already exists!' )
                    
                    return
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._value_name, allow_blank = True ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        value = dlg.GetValue()
                        
                        data = ( key, value )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key, value ) = data
            
            if self._edit_keys:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        edited_key = dlg.GetValue()
                        
                        if edited_key != key and edited_key in self._GetExistingKeys():
                            
                            wx.MessageBox( 'That ' + self._key_name + ' already exists!' )
                            
                            break
                            
                        
                    else:
                        
                        break
                        
                    
                
            else:
                
                edited_key = key
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._value_name, default = value, allow_blank = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
        
    
class StringToStringMatchDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict, min_height = 10, key_name = 'key' ):
        
        wx.Panel.__init__( self, parent )
        
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
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key, string_match ) = data
        
        pretty_string_match = string_match.ToString()
        
        display_tuple = ( key, pretty_string_match )
        sort_tuple = ( key, pretty_string_match )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the ' + self._key_name, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key = dlg.GetValue()
                
                if key in self._GetExistingKeys():
                    
                    wx.MessageBox( 'That ' + self._key_name + ' already exists!' )
                    
                    return
                    
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                    
                    string_match = ClientParsing.StringMatch()
                    
                    panel = EditStringMatchPanel( dlg, string_match )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        string_match = panel.GetValue()
                        
                        data = ( key, string_match )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Edit( self ):
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key, string_match ) = data
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the ' + self._key_name, default = key, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_key = dlg.GetValue()
                    
                    if edited_key != key and edited_key in self._GetExistingKeys():
                        
                        wx.MessageBox( 'That ' + self._key_name + ' already exists!' )
                        
                        break
                        
                    
                else:
                    
                    break
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit match' ) as dlg:
                
                string_match = ClientParsing.StringMatch()
                
                panel = EditStringMatchPanel( dlg, string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
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
        
    
class TextAndPasteCtrl( wx.Panel ):
    
    def __init__( self, parent, add_callable, allow_empty_input = False ):
        
        self._add_callable = add_callable
        self._allow_empty_input = allow_empty_input
        
        wx.Panel.__init__( self, parent )
        
        self._text_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        self._text_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.paste, self._Paste )
        self._paste_button.SetToolTip( 'Paste multiple inputs from the clipboard. Assumes the texts are newline-separated.' )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._text_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        try:
            
            texts = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            if not self._allow_empty_input:
                
                texts = [ text for text in texts if text != '' ]
                
            
            if len( texts ) > 0:
                
                self._add_callable( texts )
                
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            text = self._text_input.GetValue()
            
            text = HydrusText.StripIOInputLine( text )
            
            if text == '' and not self._allow_empty_input:
                
                return
                
            
            self._add_callable( ( text, ) )
            
            self._text_input.SetValue( '' )
            
        else:
            
            event.Skip()
            
        
    
    def GetValue( self ):
        
        return self._text_input.GetValue()
        
    
    def SetValue( self, text ):
        
        self._text_input.SetValue( text )
        
    
