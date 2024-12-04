from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIBytes
from hydrus.client.gui.widgets import ClientGUICommon

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        super().__init__( parent, 'bandwidth rules' )
        
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
                
                pretty_max_allowed = '{} requests'.format( HydrusNumbers.ToHumanInt( max_allowed ) )
                
            
            pretty_time_delta = HydrusTime.TimeDeltaToPrettyTimeDelta( time_delta )
            
            result = {}
            
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.MAX_ALLOWED ] = pretty_max_allowed
            result[ CGLC.COLUMN_LIST_BANDWIDTH_RULES.EVERY ] = pretty_time_delta
            
            return result
            
'''
        
        model = ClientGUIListCtrl.HydrusListItemModelBridge( self, CGLC.COLUMN_LIST_BANDWIDTH_RULES.ID, self._ConvertRuleToListCtrlTuples )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, 8, model, use_simple_delete = True, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
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
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_rule = panel.GetValue()
                
                self._listctrl.AddDatas( ( new_rule, ) )
                
                self._listctrl.Sort()
                
            
        
    
    def _ConvertRuleToListCtrlTuples( self, rule ):
        
        ( bandwidth_type, time_delta, max_allowed ) = rule
        
        pretty_time_delta = HydrusTime.TimeDeltaToPrettyTimeDelta( time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            pretty_max_allowed = HydrusData.ToHumanBytes( max_allowed )
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            pretty_max_allowed = HydrusNumbers.ToHumanInt( max_allowed ) + ' requests'
            
        
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
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
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
            
            super().__init__( parent )
            
            self._bandwidth_type = ClientGUICommon.BetterChoice( self )
            
            self._bandwidth_type.addItem( 'data', HC.BANDWIDTH_TYPE_DATA )
            self._bandwidth_type.addItem( 'requests', HC.BANDWIDTH_TYPE_REQUESTS )
            
            self._bandwidth_type.currentIndexChanged.connect( self._UpdateEnabled )
            
            self._max_allowed_bytes = ClientGUIBytes.BytesControl( self )
            self._max_allowed_requests = ClientGUICommon.BetterSpinBox( self, min=1, max=1048576 )
            
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
            
        
    
