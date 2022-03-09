import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'bandwidth rules' )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        # example for later:
        '''
        def sort_call( desired_columns, rule ):
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            sort_time_delta = SafeNoneInt( time_delta )
            
            result = {}
            
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.MAX_ALLOWED ] = max_allowed
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.EVERY ] = sort_time_delta
            
            return result
            
        
        def display_call( desired_columns, rule ):
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                pretty_max_allowed = HydrusData.ToHumanBytes( max_allowed )
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                pretty_max_allowed = '{} requests'.format( HydrusData.ToHumanInt( max_allowed ) )
                
            
            pretty_time_delta = HydrusData.TimeDeltaToPrettyTimeDelta( time_delta )
            
            result = {}
            
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.MAX_ALLOWED ] = pretty_max_allowed
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.EVERY ] = pretty_time_delta
            
            return result
            
'''
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_BANDWIDTH_RULES.ID, 8, self._ConvertRuleToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddDeleteButton()
        
        #
        
        self._listctrl.AddDatas( bandwidth_rules.GetRules() )
        
        self._listctrl.Sort()
        
        #
        
        self.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        rule = ( HC.BANDWIDTH_TYPE_DATA, None, 1024 * 1024 * 100 )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rule' ) as dlg:
            
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
        
        edited_datas = []
        
        for rule in selected_rules:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rule' ) as dlg:
                
                panel = self._EditPanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_rule = panel.GetValue()
                    
                    self._listctrl.DeleteDatas( ( rule, ) )
                    
                    self._listctrl.AddDatas( ( edited_rule, ) )
                    
                    edited_datas.append( edited_rule )
                    
                else:
                    
                    break
                    
                
            
        
        self._listctrl.SelectDatas( edited_datas )
        
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
            
            QP.AddToLayout( hbox, self._max_allowed_bytes, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._max_allowed_requests, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._bandwidth_type, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,' every '), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_CENTER_PERPENDICULAR )
            
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
        
        QP.AddToLayout( hbox, self._spin, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_CENTER_PERPENDICULAR )
        
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
        
    
    def SetValue( self, value: int ):
        
        max_unit = 1024 * 1024 * 1024
        
        unit = 1
        
        while value % 1024 == 0 and unit < max_unit:
            
            value //= 1024
            
            unit *= 1024
            
        
        self._spin.setValue( value )
        self._unit.SetValue( unit )
        
    
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
        
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._none_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
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
        
    
class TextAndPasteCtrl( QW.QWidget ):
    
    def __init__( self, parent, add_callable, allow_empty_input = False ):
        
        self._add_callable = add_callable
        self._allow_empty_input = allow_empty_input
        
        QW.QWidget.__init__( self, parent )
        
        self._text_input = QW.QLineEdit( self )
        self._text_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._text_input, self.EnterText ) )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Paste multiple inputs from the clipboard. Assumes the texts are newline-separated.' )
        
        self.setFocusProxy( self._text_input )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._text_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
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
        
        self._text_input.clear()
        
    
    def GetValue( self ):
        
        return self._text_input.text()
        
    
    def setPlaceholderText( self, text ):
        
        self._text_input.setPlaceholderText( text )
        
    
    def SetValue( self, text ):
        
        self._text_input.setText( text )
        
    
