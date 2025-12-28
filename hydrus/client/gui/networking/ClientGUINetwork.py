import collections
import collections.abc
import http.cookiejar
import json

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICharts
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIBandwidth
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.networking import ClientNetworking
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingJobs

class EditBandwidthRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, bandwidth_rules: HydrusNetworking.BandwidthRules, summary ):
        
        super().__init__( parent )
        
        self._bandwidth_rules_ctrl = ClientGUIBandwidth.BandwidthRulesCtrl( self, bandwidth_rules )
        
        vbox = QP.VBoxLayout()
        
        intro = 'A network job exists in several contexts. It must wait for all those contexts to have free bandwidth before it can work.'
        intro += '\n' * 2
        intro += 'You are currently editing:'
        intro += '\n' * 2
        intro += summary
        
        st = ClientGUICommon.BetterStaticText( self, intro )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._bandwidth_rules_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> HydrusNetworking.BandwidthRules:
        
        return self._bandwidth_rules_ctrl.GetValue()
        
    
class EditCookiePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, name: str, value: str, domain: str, path: str, expires: int | None ):
        
        super().__init__( parent )
        
        self._name = QW.QLineEdit( self )
        self._value = QW.QLineEdit( self )
        self._domain = QW.QLineEdit( self )
        self._path = QW.QLineEdit( self )
        
        expires_panel = ClientGUICommon.StaticBox( self, 'expires' )
        
        self._expires_st = ClientGUICommon.BetterStaticText( expires_panel )
        self._expires_st_utc = ClientGUICommon.BetterStaticText( expires_panel )
        
        self._set_expires_button = ClientGUICommon.BetterButton( expires_panel, 'set expires as a delta from now', self._SetExpires )
        
        #
        
        self._name.setText( name )
        self._value.setText( value )
        self._domain.setText( domain )
        self._path.setText( path )
        
        self._expires = expires
        
        #
        
        rows = []
        
        rows.append( ( 'Actual expires as UTC Timestamp: ', self._expires_st_utc ) )
        
        gridbox = ClientGUICommon.WrapInGrid( expires_panel, rows )
        
        expires_panel.Add( self._expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        expires_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        expires_panel.Add( self._set_expires_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'value: ', self._value ) )
        rows.append( ( 'domain: ', self._domain ) )
        rows.append( ( 'path: ', self._path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, expires_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateExpiresText()
        
    
    def _SetExpires( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit time delta' ) as dlg:
            
            now_at_dialog_boot = HydrusTime.GetNow()
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUITime.TimeDeltaWidget( panel, min = 1200, days = True, hours = True, minutes = True, seconds = True, monthly_allowed = False, max_days = 366 * 200 )
            
            if self._expires is None:
                
                time_delta = 86400 * 30
                
            else:
                
                time_delta = self._expires - now_at_dialog_boot
                
                if time_delta < 0:
                    
                    time_delta = 86400 * 30
                    
                
            
            control.SetValue( time_delta )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_time_delta = panel.GetValue()
                
                expires = now_at_dialog_boot + edited_time_delta
                
                self._expires = expires
                
                self._UpdateExpiresText()
                
            
        
    
    def _UpdateExpiresText( self ):
        
        self._expires_st.setText( HydrusTime.TimestampToPrettyExpires(self._expires) )
        self._expires_st_utc.setText( str(self._expires) )
        
    
    def GetValue( self ):
        
        name = self._name.text().strip()
        value = self._value.text().strip()
        domain = self._domain.text().strip()
        path = self._path.text().strip()
        expires = self._expires
        
        for ( var, var_name ) in [
            ( name, 'name' ),
            ( value, 'value' ),
            ( domain, 'domain' ),
            ( path, 'path' )
        ]:
            
            if len( var.splitlines() ) != 1:
                
                raise HydrusExceptions.VetoException( f'Hey, it looks like the "{var_name}" has a newline!' )
                
            
        
        return ( name, value, domain, path, expires )
        
    
class EditNetworkContextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_context: ClientNetworkingContexts.NetworkContext, limited_types = None, allow_default = True ):
        
        super().__init__( parent )
        
        if limited_types is None:
            
            limited_types = ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_WATCHER_PAGE )
            
        
        self._context_type = ClientGUICommon.BetterChoice( self )
        
        for ct in limited_types:
            
            self._context_type.addItem( CC.network_context_type_string_lookup[ ct], ct )
            
        
        self._context_type_info = ClientGUICommon.BetterStaticText( self )
        
        self._context_data_text = QW.QLineEdit( self )
        
        self._context_data_services = ClientGUICommon.BetterChoice( self )
        
        for service in CG.client_controller.services_manager.GetServices( HC.REPOSITORIES ):
            
            self._context_data_services.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._context_data_subscriptions = ClientGUICommon.BetterChoice( self )
        
        self._context_data_none = QW.QCheckBox( 'No specific data--acts as default.', self )
        
        if not allow_default:
            
            self._context_data_none.setVisible( False )
            
        
        names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY )
        
        for name in names:
            
            self._context_data_subscriptions.addItem( name, name )
            
        
        #
        
        self._context_type.SetValue( network_context.context_type )
        
        self._Update()
        
        context_type = network_context.context_type
        
        if network_context.context_data is None:
            
            self._context_data_none.setChecked( True )
            
        else:
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                self._context_data_text.setText( network_context.context_data )
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                self._context_data_services.SetValue( network_context.context_data )
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                self._context_data_subscriptions.SetValue( network_context.context_data )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._context_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_type_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_services, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_none, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._context_type.currentIndexChanged.connect( self._Update )
        
    
    def _Update( self ):
        
        self._context_type_info.setText( CC.network_context_type_description_lookup[self._context_type.GetValue()] )
        
        context_type = self._context_type.GetValue()
        
        self._context_data_text.setEnabled( False )
        self._context_data_services.setEnabled( False )
        self._context_data_subscriptions.setEnabled( False )
        
        if context_type in ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_WATCHER_PAGE ):
            
            self._context_data_none.setChecked( True )
            
        else:
            
            self._context_data_none.setChecked( False )
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                self._context_data_text.setEnabled( True )
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                self._context_data_services.setEnabled( True )
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                self._context_data_subscriptions.setEnabled( True )
                
            
        
    
    def GetValue( self ) -> ClientNetworkingContexts.NetworkContext:
        
        context_type = self._context_type.GetValue()
        
        if self._context_data_none.isChecked():
            
            context_data = None
            
        else:
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                context_data = self._context_data_text.text()
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                context_data = self._context_data_services.GetValue()
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                context_data = self._context_data_subscriptions.GetValue()
                
            
        
        return ClientNetworkingContexts.NetworkContext( context_type, context_data )
        
    
class EditNetworkContextCustomHeadersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, network_contexts_to_custom_header_dicts ):
        
        super().__init__( parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_NETWORK_CONTEXTS_CUSTOM_HEADERS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 15, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'add', self._Add )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._list_ctrl_panel.AddDeleteButton()
        self._list_ctrl_panel.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        
        #
        
        datas = []
        
        for ( network_context, custom_header_dict ) in list(network_contexts_to_custom_header_dicts.items()):
            
            for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                
                data = ( network_context, ( key, value ), approved, reason )
                
                datas.append( data )
                
            
        
        self._list_ctrl.SetData( datas )
        
        self._list_ctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'hostname.com' )
        key = 'Authorization'
        value = 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='
        approved = ClientNetworkingDomain.VALID_APPROVED
        reason = 'EXAMPLE REASON: HTTP header login--needed for access.'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit header' ) as dlg:
            
            panel = self._EditPanel( dlg, network_context, key, value, approved, reason )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( network_context, key, value, approved, reason ) = panel.GetValue()
                
                data = ( network_context, ( key, value ), approved, reason )
                
                self._list_ctrl.AddData( data, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertDataToDisplayTuple( self, data ):
        
        ( network_context, ( key, value ), approved, reason ) = data
        
        pretty_network_context = network_context.ToString()
        
        pretty_key_value = key + ': ' + value
        
        pretty_approved = ClientNetworkingDomain.valid_str_lookup[ approved ]
        
        pretty_reason = reason
        
        display_tuple = ( pretty_network_context, pretty_key_value, pretty_approved, pretty_reason )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, data ):
        
        ( network_context, ( key, value ), approved, reason ) = data
        
        pretty_network_context = network_context.ToString()
        
        pretty_approved = ClientNetworkingDomain.valid_str_lookup[ approved ]
        
        sort_tuple = ( pretty_network_context, ( key, value ), pretty_approved, reason )
        
        return sort_tuple
        
    
    def _Duplicate( self ):
        
        existing_keys = { key for ( network_context, ( key, value ), approved, reason ) in self._list_ctrl.GetData() }
        
        datas = self._list_ctrl.GetData( only_selected = True )
        
        rows_to_add = []
        
        for ( network_context, ( key, value ), approved, reason ) in datas:
            
            key = HydrusData.GetNonDupeName( key, existing_keys )
            
            existing_keys.add( key )
            
            rows_to_add.append( ( network_context, ( key, value ), approved, reason ) )
            
        
        self._list_ctrl.AddDatas( rows_to_add, select_sort_and_scroll = True )
        
    
    def _Edit( self ):
        
        data = self._list_ctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( network_context, ( key, value ), approved, reason ) = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit header' ) as dlg:
            
            panel = self._EditPanel( dlg, network_context, key, value, approved, reason )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( network_context, key, value, approved, reason ) = panel.GetValue()
                
                new_data = ( network_context, ( key, value ), approved, reason )
                
                self._list_ctrl.ReplaceData( data, new_data, sort_and_scroll = True )
                
            
        
    
    def GetValue( self ):
        
        network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        for ( network_context, ( key, value ), approved, reason ) in self._list_ctrl.GetData():
            
            network_contexts_to_custom_header_dicts[ network_context ][ key ] = ( value, approved, reason )
            
        
        return network_contexts_to_custom_header_dicts
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent: QW.QWidget, network_context: ClientNetworkingContexts.NetworkContext, key: str, value: str, approved: int, reason: str ):
            
            super().__init__( parent )
            
            self._network_context = NetworkContextButton( self, network_context, limited_types = ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOMAIN ), allow_default = False )
            
            self._key = QW.QLineEdit( self )
            self._value = QW.QLineEdit( self )
            
            self._approved = ClientGUICommon.BetterChoice( self )
            
            for a in ( ClientNetworkingDomain.VALID_APPROVED, ClientNetworkingDomain.VALID_DENIED, ClientNetworkingDomain.VALID_UNKNOWN ):
                
                self._approved.addItem( ClientNetworkingDomain.valid_str_lookup[ a], a )
                
            
            self._reason = QW.QLineEdit( self )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._reason, 60 )
            self._reason.setMinimumWidth( width )
            
            #
            
            self._key.setText( key )
            
            self._value.setText( value )
            
            self._approved.SetValue( approved )
            
            self._reason.setText( reason )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._network_context, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._key, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._approved, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._reason, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.widget().setLayout( vbox )
            
        
        def GetValue( self ):
            
            network_context = self._network_context.GetValue()
            key = self._key.text().strip()
            value = self._value.text().strip()
            approved = self._approved.GetValue()
            reason = self._reason.text()
            
            for ( var, var_name ) in [
                ( key, 'key' ),
                ( value, 'value' )
            ]:
                
                if len( var.splitlines() ) != 1:
                    
                    raise HydrusExceptions.VetoException( f'Hey, it looks like the "{var_name}" has a newline!' )
                    
                
            
            return ( network_context, key, value, approved, reason )
            
        
    
class NetworkContextButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, network_context, limited_types = None, allow_default = True ):
        
        super().__init__( parent, network_context.ToString(), self._Edit )
        
        self._network_context = network_context
        self._limited_types = limited_types
        self._allow_default = allow_default
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit network context' ) as dlg:
            
            panel = EditNetworkContextPanel( dlg, self._network_context, limited_types = self._limited_types, allow_default = self._allow_default )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._network_context = panel.GetValue()
                
                self._Update()
                
            
        
    
    def _Update( self ):
        
        self.setText( self._network_context.ToString() )
        
    
    def GetValue( self ):
        
        return self._network_context
        
    
    def SetValue( self, network_context ):
        
        self._network_context = network_context
        
        self._Update()
        
    
class ReviewAllBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        super().__init__( parent )
        
        self._history_time_delta_threshold = ClientGUITime.TimeDeltaButton( self, days = True, hours = True, minutes = True, seconds = True )
        self._history_time_delta_threshold.timeDeltaChanged.connect( self.EventTimeDeltaChanged )
        
        self._history_time_delta_none = QW.QCheckBox( 'show all', self )
        self._history_time_delta_none.clicked.connect( self.EventTimeDeltaChanged )
        
        self._bandwidths_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_BANDWIDTH_REVIEW.ID, self._ConvertNetworkContextsToDisplayTuple, self._ConvertNetworkContextsToSortTuple )
        
        self._bandwidths = ClientGUIListCtrl.BetterListCtrlTreeView( self._bandwidths_panel, 20, model, activation_callback = self.ShowNetworkContext )
        
        self._bandwidths_panel.SetListCtrl( self._bandwidths )
        
        self._bandwidths_panel.AddButton( 'see more detail', self.ShowNetworkContext, enabled_only_on_selection = True )
        self._bandwidths_panel.AddButton( 'delete selected history', self._DeleteNetworkContexts, enabled_only_on_selection = True )
        
        self._bandwidths_panel.NewButtonRow()
        
        self._bandwidths_panel.AddButton( 'edit default bandwidth rules', self._EditDefaultBandwidthRules )
        self._bandwidths_panel.AddButton( 'reset default bandwidth rules', self._ResetDefaultBandwidthRules )
        self._bandwidths_panel.AddIconButton( CC.global_icons().help, self._ShowDefaultRulesHelp )
        
        #
        
        last_review_bandwidth_search_distance = self._controller.new_options.GetNoneableInteger( 'last_review_bandwidth_search_distance' )
        
        if last_review_bandwidth_search_distance is None:
            
            self._history_time_delta_threshold.SetValue( 86400 * 7 )
            self._history_time_delta_threshold.setEnabled( False )
            
            self._history_time_delta_none.setChecked( True )
            
        else:
            
            self._history_time_delta_threshold.SetValue( last_review_bandwidth_search_distance )
            
        
        self._bandwidths.Sort()
        
        self._update_job = CG.client_controller.CallRepeatingQtSafe( self, 0.5, 5.0, 'repeating all bandwidth status update', self._Update )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'Show network contexts with usage in the past: '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._history_time_delta_threshold, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._history_time_delta_none, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        label = 'Every context normally relies on the respective default bandwidth rules for its type. Double-click any row to see more detail or override the defaults with specific rules.'
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._bandwidths_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertNetworkContextsToDisplayTuple( self, network_context ):
        
        bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( network_context )
        
        has_rules = not self._controller.network_engine.bandwidth_manager.UsesDefaultRules( network_context )
        
        current_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        day_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 86400 )
        day_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 86400 )
        
        month_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None )
        month_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
        
        if self._history_time_delta_none.isChecked():
            
            search_usage_requests = bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_REQUESTS )
            search_usage_data = bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_DATA )
            
        else:
            
            search_delta = self._history_time_delta_threshold.GetValue()
            
            search_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, search_delta )
            search_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, search_delta )
            
        
        pretty_search_usage = HydrusData.ToHumanBytes( search_usage_data ) + ' in ' + HydrusNumbers.ToHumanInt( search_usage_requests ) + ' requests'
        
        pretty_network_context = network_context.ToString()
        pretty_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        
        if current_usage == 0:
            
            pretty_current_usage = ''
            
        else:
            
            pretty_current_usage = HydrusData.ToHumanBytes( current_usage ) + '/s'
            
        
        pretty_day_usage = HydrusData.ToHumanBytes( day_usage_data ) + ' in ' + HydrusNumbers.ToHumanInt( day_usage_requests ) + ' requests'
        pretty_month_usage = HydrusData.ToHumanBytes( month_usage_data ) + ' in ' + HydrusNumbers.ToHumanInt( month_usage_requests ) + ' requests'
        
        if network_context == ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT:
            
            pretty_has_rules = 'n/a'
            
        elif has_rules:
            
            pretty_has_rules = 'yes'
            
        else:
            
            pretty_has_rules = ''
            
        
        ( waiting_estimate, network_context_gumpf ) = self._controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( [ network_context ] )
        
        if waiting_estimate > 0:
            
            pretty_blocked = HydrusTime.TimeDeltaToPrettyTimeDelta( waiting_estimate )
            
        else:
            
            pretty_blocked = ''
            
        
        display_tuple = ( pretty_network_context, pretty_context_type, pretty_current_usage, pretty_day_usage, pretty_search_usage, pretty_month_usage, pretty_has_rules, pretty_blocked )
        
        return display_tuple
        
    
    def _ConvertNetworkContextsToSortTuple( self, network_context: ClientNetworkingContexts.NetworkContext ):
        
        bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( network_context )
        
        has_rules = not self._controller.network_engine.bandwidth_manager.UsesDefaultRules( network_context )
        
        sortable_network_context = network_context.GetSortable()
        sortable_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        current_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        day_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 86400 )
        day_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 86400 )
        
        day_usage = ( day_usage_data, day_usage_requests )
        
        month_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None )
        month_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
        
        month_usage = ( month_usage_data, month_usage_requests )
        
        if self._history_time_delta_none.isChecked():
            
            search_usage_requests = bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_REQUESTS )
            search_usage_data = bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_DATA )
            
        else:
            
            search_delta = self._history_time_delta_threshold.GetValue()
            
            search_usage_requests = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, search_delta )
            search_usage_data = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, search_delta )
            
        
        search_usage = ( search_usage_data, search_usage_requests )
        
        ( waiting_estimate, network_context_gumpf ) = self._controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( [ network_context ] )
        
        sort_tuple = ( sortable_network_context, sortable_context_type, current_usage, day_usage, search_usage, month_usage, has_rules, waiting_estimate )
        
        return sort_tuple
        
    
    def _DeleteNetworkContexts( self ):
        
        selected_network_contexts = self._bandwidths.GetData( only_selected = True )
        
        if len( selected_network_contexts ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Are you sure? This will delete all bandwidth record for the selected network contexts.' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._controller.network_engine.bandwidth_manager.DeleteHistory( selected_network_contexts )
                
                self._update_job.Wake()
                
            
        
    
    def _EditDefaultBandwidthRules( self ):
        
        network_contexts_and_bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetDefaultRules()
        
        choice_tuples = [ ( 'global', ( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, self._controller.network_engine.bandwidth_manager.GetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ) ) ) ]
        
        choice_tuples.extend( [ ( network_context.ToString() + ' (' + str( len( bandwidth_rules.GetRules() ) ) + ' rules)', ( network_context, bandwidth_rules ) ) for ( network_context, bandwidth_rules ) in network_contexts_and_bandwidth_rules ] )
        
        try:
            
            ( network_context, bandwidth_rules ) = ClientGUIDialogsQuick.SelectFromList( self, 'select network context', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit bandwidth rules for ' + network_context.ToString() ) as dlg_2:
            
            summary = network_context.GetSummary()
            
            panel = EditBandwidthRulesPanel( dlg_2, bandwidth_rules, summary )
            
            dlg_2.SetPanel( panel )
            
            if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                
                bandwidth_rules = panel.GetValue()
                
                self._controller.network_engine.bandwidth_manager.SetRules( network_context, bandwidth_rules )
                
            
        
    
    def _ResetDefaultBandwidthRules( self ):
        
        message = 'Reset your \'default\' and \'global\' bandwidth rules to default?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            ClientDefaults.SetDefaultBandwidthManagerRules( self._controller.network_engine.bandwidth_manager )
            
        
    
    def _ShowDefaultRulesHelp( self ):
        
        help_text = 'Network requests act in multiple contexts. Most use the \'global\' and \'web domain\' network contexts, but a downloader page or subscription will also add a special label for itself. Each context can have its own set of bandwidth rules.'
        help_text += '\n' * 2
        help_text += 'If a network context does not have some specific rules set up, it will fall back to its respective default. It is possible for a default to not have any rules. If you want to set general policy, like "Never download more than 1GB/day from any individual website," or "Limit the entire client to 2MB/s," do it through \'global\' and the defaults.'
        help_text += '\n' * 2
        help_text += 'All contexts\' rules are consulted and have to pass before a request can do work. If you set a 2MB/s limit on a website domain and a 64KB/s limit on global, your download will only ever run at 64KB/s (and it fact it will probably run much slower, since everything shares the global context!). To make sense, network contexts with broader scope should have more lenient rules.'
        help_text += '\n' * 2
        help_text += 'There are two special ephemeral \'instance\' contexts, for downloaders and thread watchers. These represent individual queries, either a single gallery search or a single watched thread. It can be useful to set default rules for these so your searches will gather a fast initial sample of results in the first few minutes--so you can make sure you are happy with them--but otherwise trickle the rest in over time. This keeps your CPU and other bandwidth limits less hammered and helps to avoid accidental downloads of many thousands of small bad files or a few hundred gigantic files all in one go.'
        help_text += '\n' * 2
        help_text += 'Please note that this system bases its calendar dates on UTC time (it helps servers and clients around the world stay in sync a bit easier). This has no bearing on what, for instance, the \'past 24 hours\' means, but monthly transitions may occur a few hours off whatever your midnight is.'
        help_text += '\n' * 2
        help_text += 'If you do not understand what is going on here, you can safely leave it alone. The default settings make for a _reasonable_ and polite profile that will not accidentally cause you to download way too much in one go or piss off servers by being too aggressive. If you want to throttle your client, the simplest way is to add a simple rule like \'500MB per day\' to the global context.'
        
        ClientGUIDialogsMessage.ShowInformation( self, help_text )
        
    
    def _Update( self ):
        
        if self._history_time_delta_none.isChecked():
            
            history_time_delta_threshold = None
            
        else:
            
            history_time_delta_threshold = self._history_time_delta_threshold.GetValue()
            
        
        network_contexts = self._controller.network_engine.bandwidth_manager.GetNetworkContextsForUser( history_time_delta_threshold )
        
        self._bandwidths.SetData( network_contexts )
        
    
    def EventTimeDeltaChanged( self ):
        
        if self._history_time_delta_none.isChecked():
            
            self._history_time_delta_threshold.setEnabled( False )
            
            last_review_bandwidth_search_distance = None
            
        else:
            
            self._history_time_delta_threshold.setEnabled( True )
            
            last_review_bandwidth_search_distance = self._history_time_delta_threshold.GetValue()
            
        
        self._controller.new_options.SetNoneableInteger( 'last_review_bandwidth_search_distance', last_review_bandwidth_search_distance )
        
        self._update_job.Wake()
        
    
    def ShowNetworkContext( self ):
        
        for network_context in self._bandwidths.GetData( only_selected = True ):
            
            parent = self.window().parentWidget()
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( parent, 'review bandwidth for ' + network_context.ToString() )
            
            panel = ReviewNetworkContextBandwidthPanel( frame, self._controller, network_context )
            
            frame.SetPanel( panel )
            
        
    
class ReviewNetworkContextBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller", network_context ):
        
        self._controller = controller
        
        super().__init__( parent )
        
        self._network_context = network_context
        
        self._bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetRules( self._network_context )
        self._bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( self._network_context )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'description' )
        
        description = CC.network_context_type_description_lookup[ self._network_context.context_type ]
        
        self._name = ClientGUICommon.BetterStaticText( info_panel, label = self._network_context.ToString() )
        self._description = ClientGUICommon.BetterStaticText( info_panel, label = description )
        
        #
        
        usage_panel = ClientGUICommon.StaticBox( self, 'usage' )
        
        self._current_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        self._all_time_usage = ClientGUICommon.BetterStaticText( usage_panel )
        
        self._time_delta_usage_bandwidth_type = ClientGUICommon.BetterChoice( usage_panel )
        self._time_delta_usage_time_delta = ClientGUITime.TimeDeltaButton( usage_panel, days = True, hours = True, minutes = True, seconds = True )
        self._time_delta_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        #
        
        rules_panel = ClientGUICommon.StaticBox( self, 'rules' )
        
        self._uses_default_rules_st = ClientGUICommon.BetterStaticText( rules_panel )
        self._uses_default_rules_st.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignHCenter )
        
        self._rules_rows_panel = QW.QWidget( rules_panel )
        
        vbox = QP.VBoxLayout()
        
        self._rules_rows_panel.setLayout( vbox )
        
        self._last_fetched_rule_rows = set()
        self._rule_widgets = []
        
        self._use_default_rules_button = ClientGUICommon.BetterButton( rules_panel, 'use default rules', self._UseDefaultRules )
        self._edit_rules_button = ClientGUICommon.BetterButton( rules_panel, 'edit rules', self._EditRules )
        
        #
        
        self._time_delta_usage_time_delta.SetValue( 86400 )
        
        for bandwidth_type in ( HC.BANDWIDTH_TYPE_DATA, HC.BANDWIDTH_TYPE_REQUESTS ):
            
            self._time_delta_usage_bandwidth_type.addItem( HC.bandwidth_type_string_lookup[ bandwidth_type], bandwidth_type )
            
        
        self._time_delta_usage_bandwidth_type.SetValue( HC.BANDWIDTH_TYPE_DATA )
        
        monthly_usage = self._bandwidth_tracker.GetMonthlyDataUsage()
        
        if len( monthly_usage ) > 0:
            
            if ClientGUICharts.QT_CHARTS_OK:
                
                self._barchart_canvas = ClientGUICharts.BarChartBandwidthHistory( usage_panel, monthly_usage )
                
                self._barchart_canvas.setMinimumSize( 640, 480 )
                
            else:
                
                self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'QtCharts not available, so no bandwidth chart here.' )
                
            
        else:
            
            self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'No usage yet, so no usage history to show.' )
            
        
        #
        
        info_panel.Add( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._time_delta_usage_bandwidth_type, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(usage_panel,' in the past '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time_delta_usage_time_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time_delta_usage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        usage_panel.Add( self._current_usage_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.Add( self._all_time_usage, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.Add( self._barchart_canvas, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._edit_rules_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._use_default_rules_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rules_panel.Add( self._uses_default_rules_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        rules_panel.Add( self._rules_rows_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        rules_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, usage_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._rules_job = CG.client_controller.CallRepeatingQtSafe( self, 0.0, 5.0, 'repeating bandwidth rules update', self._UpdateRules )
        
        self._update_job = CG.client_controller.CallRepeatingQtSafe( self, 0.0, 1.0, 'repeating bandwidth status update', self._Update )
        
    
    def _EditRules( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit bandwidth rules for ' + self._network_context.ToString() ) as dlg:
            
            summary = self._network_context.GetSummary()
            
            panel = EditBandwidthRulesPanel( dlg, self._bandwidth_rules, summary )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._bandwidth_rules = panel.GetValue()
                
                self._controller.network_engine.bandwidth_manager.SetRules( self._network_context, self._bandwidth_rules )
                
                self._rules_job.Wake()
                
            
        
    
    def _Update( self ):
        
        current_usage = self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1, for_user = True )
        
        pretty_current_usage = 'Current usage: ' + HydrusData.ToHumanBytes( current_usage ) + '/s'
        
        self._current_usage_st.setText( pretty_current_usage )
        
        #
        
        search_usage_requests = self._bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_REQUESTS )
        search_usage_data = self._bandwidth_tracker.GetAllUsage( HC.BANDWIDTH_TYPE_DATA )
        
        all_time_pretty_search_usage = f'All time usage: {HydrusData.ToHumanBytes( search_usage_data )} in {HydrusNumbers.ToHumanInt( search_usage_requests )} requests'
        
        self._all_time_usage.setText( all_time_pretty_search_usage )
        
        #
        
        bandwidth_type = self._time_delta_usage_bandwidth_type.GetValue()
        time_delta = self._time_delta_usage_time_delta.GetValue()
        
        time_delta_usage = self._bandwidth_tracker.GetUsage( bandwidth_type, time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            converter = HydrusData.ToHumanBytes
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            converter = HydrusNumbers.ToHumanInt
            
        
        pretty_time_delta_usage = ': ' + converter( time_delta_usage )
        
        self._time_delta_usage_st.setText( pretty_time_delta_usage )
        
    
    def _UpdateRules( self ):
        
        if self._network_context.IsDefault() or self._network_context == ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT:
            
            if not self._use_default_rules_button.isHidden():
                
                self._uses_default_rules_st.hide()
                self._use_default_rules_button.hide()
                
            
        else:
            
            if self._controller.network_engine.bandwidth_manager.UsesDefaultRules( self._network_context ):
                
                self._uses_default_rules_st.setText( 'uses default rules' )
                
                self._edit_rules_button.setText( 'set specific rules' )
                
                if not self._use_default_rules_button.isHidden():
                    
                    self._use_default_rules_button.hide()
                    
                
            else:
                
                self._uses_default_rules_st.setText( 'has its own rules' )
                
                self._edit_rules_button.setText( 'edit rules' )
                
                if self._use_default_rules_button.isHidden():
                    
                    self._use_default_rules_button.show()
                    
                
            
        
        rule_rows = self._bandwidth_rules.GetBandwidthStringsAndGaugeTuples( self._bandwidth_tracker, threshold = 0 )
        
        if rule_rows != self._last_fetched_rule_rows:
            
            self._last_fetched_rule_rows = rule_rows
            
            vbox = self._rules_rows_panel.layout()
            
            for rule_widget in self._rule_widgets:
                
                vbox.removeWidget( rule_widget )
                
                rule_widget.deleteLater()
                
            
            self._rule_widgets = []
            
            for ( status, ( v, r ) ) in rule_rows:
                
                tg = ClientGUICommon.TextAndGauge( self._rules_rows_panel )
                
                tg.SetValue( status, v, r )
                
                self._rule_widgets.append( tg )
                
                QP.AddToLayout( vbox, tg, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
        
    
    def _UseDefaultRules( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Are you sure you want to revert to using the default rules for this context?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._controller.network_engine.bandwidth_manager.DeleteRules( self._network_context )
            
            self._bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetRules( self._network_context )
            
            self._rules_job.Wake()
            
        
    
class ReviewNetworkJobs( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        super().__init__( parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_NETWORK_JOBS_REVIEW.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self._list_ctrl_panel, 20, model )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        
        # button to stop jobs en-masse
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        self._refresh_time_delta = ClientGUITime.NoneableTimeDeltaWidget( self._list_ctrl_panel, 0.25, 'auto-refresh', none_phrase = 'manual refresh', min = 0.05, days = False, hours = False, minutes = True, seconds = True, milliseconds = True )
        self._refresh_time_delta.SetValue( None )
        
        #
        
        self._list_ctrl.Sort()
        
        self._RefreshSnapshot()
        
        #
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, label = 'right-click a job for more debug info!' )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._refresh_time_delta, CC.FLAGS_ON_RIGHT )
        
        self._refresh_time_delta.timeDeltaChanged.connect( self._RefreshTimeDeltaChanged )
        
        self._refresh_timer = QC.QTimer( self )
        self._refresh_timer.timeout.connect( self._RefreshSnapshot )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertDataToDisplayTuple( self, job_row ):
        
        network_engine_status: int = job_row[0]
        job: ClientNetworkingJobs.NetworkJob = job_row[1]
        
        position = network_engine_status
        url = job.GetURL()
        ( status, current_speed, num_bytes_read, num_bytes_to_read ) = job.GetStatus()
        
        pretty_position = ClientNetworking.job_status_str_lookup[ position ]
        pretty_url = url
        pretty_status = status
        pretty_current_speed = HydrusData.ToHumanBytes( current_speed ) + '/s'
        pretty_progress = HydrusData.ConvertValueRangeToBytes( num_bytes_read, num_bytes_to_read )
        
        display_tuple = ( pretty_position, pretty_url, pretty_status, pretty_current_speed, pretty_progress )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, job_row ):
        
        network_engine_status: int = job_row[0]
        job: ClientNetworkingJobs.NetworkJob = job_row[1]
        
        position = network_engine_status
        url = job.GetURL()
        ( status, current_speed, num_bytes_read, num_bytes_to_read ) = job.GetStatus()
        progress = ( num_bytes_read, num_bytes_to_read if num_bytes_to_read is not None else 0 )
        
        sort_tuple = ( position, url, status, current_speed, progress )
        
        return sort_tuple
        
    
    def _RefreshSnapshot( self ):
        
        job_rows = self._controller.network_engine.GetJobsSnapshot()
        
        self._list_ctrl.SetData( job_rows )
        
    
    def _RefreshTimeDeltaChanged( self ):
        
        value = self._refresh_time_delta.GetValue()
        
        if value is None:
            
            self._refresh_timer.stop()
            
        else:
            
            self._refresh_timer.start( int( value * 1000 ) )
            
        
    
    def _GetListCtrlMenu( self ):
        
        data = self._list_ctrl.GetData( only_selected = True )
        
        if len( data ) != 1:
            
            raise HydrusExceptions.DataMissing()
            
        
        network_job: ClientNetworkingJobs.NetworkJob = data[0][1]
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        submenu = ClientGUIMenus.GenerateMenu( menu )
        
        network_contexts = network_job.GetNetworkContexts()
        
        bandwidth_manager = self._controller.network_engine.bandwidth_manager
        
        for network_context in network_contexts:
            
            label = network_context.ToString()
            
            ( waiting_estimate, gumpf ) = bandwidth_manager.GetWaitingEstimateAndContext( [ network_context ] )
            
            if waiting_estimate > 0:
                
                label = f'{label} ({HydrusTime.TimeDeltaToPrettyTimeDelta( waiting_estimate )})'
                
            else:
                
                label = f'{label} (bandwidth ok)'
                
            
            ClientGUIMenus.AppendMenuLabel( submenu, label )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'network contexts' )
        
        ClientGUIMenus.AppendMenuLabel( menu, f'domain ok: {network_job.DomainOK()}' )
        ClientGUIMenus.AppendMenuLabel( menu, f'waiting on connection error: {network_job.CurrentlyWaitingOnConnectionError()}' )
        ClientGUIMenus.AppendMenuLabel( menu, f'waiting on serverside bandwidth: {network_job.CurrentlyWaitingOnServersideBandwidth()}' )
        ClientGUIMenus.AppendMenuLabel( menu, f'obeys bandwidth: {network_job.ObeysBandwidth()}' )
        ClientGUIMenus.AppendMenuLabel( menu, f'tokens ok: {network_job.TokensOK()}' )
        
        return menu
        
    
class ReviewNetworkSessionsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, session_manager ):
        
        super().__init__( parent )
        
        self._session_manager = session_manager
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REVIEW_NETWORK_SESSIONS.ID, self._ConvertNetworkContextToDisplayTuple, self._ConvertNetworkContextToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, 32, model, delete_key_callback = self._Clear, activation_callback = self._Review )
        
        self._listctrl.Sort()
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'create new', self._Add )
        listctrl_panel.AddButton( 'review', self._Review, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'clear', self._Clear, enabled_only_on_selection = True )
        listctrl_panel.AddSeparator()
        listctrl_panel.AddButton( 'refresh', self._Update )
        listctrl_panel.NewButtonRow()
        listctrl_panel.AddButton( 'export to clipboard', self._ExportToClipboard, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'import from clipboard', self._ImportFromClipboard )
        listctrl_panel.AddButton( 'import cookies.txt (drag and drop also works!)', self._ImportCookiesTXT )
        
        listctrl_panel.installEventFilter( ClientGUIDragDrop.FileDropTarget( listctrl_panel, filenames_callable = self._ImportCookiesTXTPaths ) )
        
        self._show_empty = QW.QCheckBox( 'show empty', self )
        
        #
        
        self._Update()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._show_empty, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._show_empty.clicked.connect( self._Update )
        
    
    def _Add( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'enter new network context' ) as dlg:
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'example.com' )
            
            panel = EditNetworkContextPanel( dlg, network_context, limited_types = ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS ), allow_default = False )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                network_context = panel.GetValue()
                
                self._AddNetworkContext( network_context )
                
            
        
        self._show_empty.setChecked( True )
        
        self._Update()
        
    
    def _AddNetworkContext( self, network_context ):
        
        # this establishes a bare session
        
        self._session_manager.GetSession( network_context )
        
    
    def _Clear( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear these sessions? This will delete them completely.' )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        for network_context in self._listctrl.GetData( only_selected = True ):
            
            self._session_manager.ClearSession( network_context )
            
        
        self._Update()
        
    
    def _ConvertNetworkContextToDisplayTuple( self, network_context ):
        
        session = self._session_manager.GetSession( network_context )
        
        pretty_network_context = network_context.ToString()
        
        number_of_cookies = len( session.cookies )
        pretty_number_of_cookies = HydrusNumbers.ToHumanInt( number_of_cookies )
        
        expires_numbers = [ c.expires for c in session.cookies if c.expires is not None ]
        
        if len( expires_numbers ) == 0:
            
            if number_of_cookies > 0:
                
                pretty_expiry = 'session'
                
            else:
                
                pretty_expiry = ''
                
            
        else:
            
            try:
                
                expiry = max( expires_numbers )
                pretty_expiry = HydrusTime.TimestampToPrettyExpires( expiry )
                
            except:
                
                pretty_expiry = 'Unusual expiry numbers'
                
            
        
        display_tuple = ( pretty_network_context, pretty_number_of_cookies, pretty_expiry )
        
        return display_tuple
        
    
    def _ConvertNetworkContextToSortTuple( self, network_context ):
        
        session = self._session_manager.GetSession( network_context )
        
        pretty_network_context = network_context.ToString()
        
        number_of_cookies = len( session.cookies )
        
        expires_numbers = [ c.expires for c in session.cookies if c.expires is not None ]
        
        if len( expires_numbers ) == 0:
            
            if number_of_cookies > 0:
                
                expiry = 0
                
            else:
                
                expiry = -1
                
            
        else:
            
            try:
                
                expiry = max( expires_numbers )
                
            except:
                
                expiry = -1
                
            
        
        sort_tuple = ( pretty_network_context, number_of_cookies, expiry )
        
        return sort_tuple
        
    
    def _ExportToClipboard( self ):
        
        all_cookies = []
        
        network_contexts = self._listctrl.GetData( only_selected = True )
        
        for network_context in network_contexts:
            
            session = self._session_manager.GetSession( network_context )
            
            if len( session.cookies ) > 0:
                
                all_cookies.extend( session.cookies )
                
            
        
        if len( all_cookies ) == 0:
            
            return
            
        
        cookie_data_flat = [ [ cookie.name, cookie.value, cookie.domain, cookie.path, cookie.expires ] for cookie in all_cookies ]
        
        json_text = json.dumps( cookie_data_flat )
        
        CG.client_controller.pub( 'clipboard', 'text', json_text )
        
    
    # this method is thanks to a user's contribution!
    def _ImportCookiesTXT( self ):
        
        with QP.FileDialog( self, 'select cookies.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen ) as f_dlg:
            
            if f_dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = f_dlg.GetPath()
                
                self._ImportCookiesTXTPaths( ( path, ) )
                
            
        
    
    def _ImportCookiesTXTPaths( self, paths ):
        
        num_added = 0
        
        for path in paths:
            
            cj = http.cookiejar.MozillaCookieJar()
            
            try:
                
                cj.load( path, ignore_discard = True, ignore_expires = True )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', 'It looks like that cookies.txt failed to load. Unfortunately, not all formats are supported.' )
                
                return
                
            
            for cookie in cj:
                
                session = self._session_manager.GetSessionForDomain( cookie.domain )
                
                session.cookies.set_cookie( cookie )
                
                num_added += 1
                
            
        
        ClientGUIDialogsMessage.ShowInformation( self, f'Added {HydrusNumbers.ToHumanInt(num_added)} cookies!' )
        
        self._Update()
        
    
    def _ImportFromClipboard( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
            
            return
            
        
        try:
            
            cookie_data_flat = json.loads( raw_text )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Did not understand what was in the clipboard!', str(e) )
            
            return
            
        
        try:
            
            if len( cookie_data_flat ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'There were no cookies in the clipboard!' )
                
                return
                
            
            domains = sorted( { domain for ( name, value, domain, path, expires ) in cookie_data_flat } )
            
            message = f'About to import {HydrusNumbers.ToHumanInt(len(cookie_data_flat))} cookies for the domains {HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( domains )} Is that ok?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message = message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            num_added = 0
            
            for ( name, value, domain, path, expires ) in cookie_data_flat:
                
                version = 0
                port = None
                port_specified = False
                domain_specified = True
                domain_initial_dot = domain.startswith( '.' )
                path_specified = True
                secure = False
                discard = False
                comment = None
                comment_url = None
                rest = {}
                
                cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
                
                session = self._session_manager.GetSessionForDomain( cookie.domain )
                
                session.cookies.set_cookie( cookie )
                
                num_added += 1
                
            
            ClientGUIDialogsMessage.ShowInformation( self, f'Added {HydrusNumbers.ToHumanInt(num_added)} cookies!' )
            
            self._Update()
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Had trouble importing what was in the clipboard!', str(e) )
            
            return
            
        
    
    def _Review( self ):
        
        for network_context in self._listctrl.GetData( only_selected = True ):
            
            parent = self.window().parentWidget()
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( parent, 'review session for ' + network_context.ToString() )
            
            panel = ReviewNetworkSessionPanel( frame, self._session_manager, network_context )
            
            frame.SetPanel( panel )
            
        
    
    def _Update( self ):
        
        network_contexts = [ network_context for network_context in self._session_manager.GetNetworkContexts() if network_context.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS ) ]
        
        if not self._show_empty.isChecked():
            
            non_empty_network_contexts = []
            
            for network_context in network_contexts:
                
                session = self._session_manager.GetSession( network_context )
                
                if len( session.cookies ) > 0:
                    
                    non_empty_network_contexts.append( network_context )
                    
                
            
            network_contexts = non_empty_network_contexts
            
        
        self._listctrl.SetData( network_contexts )
        
    

class ReviewNetworkSessionPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, session_manager, network_context: ClientNetworkingContexts.NetworkContext ):
        
        super().__init__( parent )
        
        self._session_manager = session_manager
        self._network_context = network_context
        
        self._session = self._session_manager.GetSession( self._network_context )
        
        self._description = ClientGUICommon.BetterStaticText( self, network_context.ToString() )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REVIEW_NETWORK_SESSION.ID, self._ConvertCookieToDisplayTuple, self._ConvertCookieToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( listctrl_panel, 8, model, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._listctrl.Sort()
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        listctrl_panel.AddDeleteButton()
        listctrl_panel.AddSeparator()
        listctrl_panel.AddButton( 'refresh', self._Update )
        listctrl_panel.NewButtonRow()
        listctrl_panel.AddButton( 'export to clipboard', self._ExportToClipboard, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'import from clipboard', self._ImportFromClipboard )
        listctrl_panel.AddButton( 'import cookies.txt (drag and drop also works!)', self._ImportCookiesTXT )
        
        listctrl_panel.installEventFilter( ClientGUIDragDrop.FileDropTarget( listctrl_panel, filenames_callable = self._ImportCookiesTXTPaths ) )
        
        #
        
        self._Update()
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'The hydrus network engine keeps cookies in second-level-domain-separated silos. If you create/edit a cookie for example.com in the panel for site.com, it will not get sent anywhere! Make sure to export/import or whatever you need to do to migrate it.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._description, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit cookie' ) as dlg:
            
            name = 'name'
            value = '123'
            
            if self._network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                domain = '.' + self._network_context.context_data
                
            else:
                
                domain = 'service domain'
                
            
            path = '/'
            expires = HydrusTime.GetNow() + 30 * 86400
            
            panel = EditCookiePanel( dlg, name, value, domain, path, expires )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( name, value, domain, path, expires ) = panel.GetValue()
                
                self._SetCookie( name, value, domain, path, expires )
                
                self._session_manager.SetSessionDirty( self._network_context )
                
            
        
        self._Update()
        
    
    def _ConvertCookieToDisplayTuple( self, cookie ):
        
        name = cookie.name
        pretty_name = name
        
        value = cookie.value
        pretty_value = value
        
        domain = cookie.domain
        pretty_domain = domain
        
        path = cookie.path
        pretty_path = path
        
        expiry = cookie.expires
        
        if expiry is None:
            
            pretty_expiry = 'session'
            
        else:
            
            pretty_expiry = HydrusTime.TimestampToPrettyExpires( expiry )
            
        
        display_tuple = ( pretty_name, pretty_value, pretty_domain, pretty_path, pretty_expiry )
        
        return display_tuple
        
    
    def _ConvertCookieToSortTuple( self, cookie ):
        
        name = cookie.name
        
        value = cookie.value
        
        domain = cookie.domain
        
        path = cookie.path
        
        expiry = cookie.expires
        
        sort_expiry = ClientGUIListCtrl.SafeNoneInt( expiry )
        
        sort_tuple = ( name, value, domain, path, sort_expiry )
        
        return sort_tuple
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Delete all selected cookies?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            for cookie in self._listctrl.GetData( only_selected = True ):
                
                domain = cookie.domain
                path = cookie.path
                name = cookie.name
                
                self._session.cookies.clear( domain, path, name )
                
                self._session_manager.SetSessionDirty( self._network_context )
                
            
            self._Update()
            
        
    
    def _Edit( self ):
        
        for cookie in self._listctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit cookie' ) as dlg:
                
                name = cookie.name
                value = cookie.value
                domain = cookie.domain
                path = cookie.path
                expires = cookie.expires
                
                panel = EditCookiePanel( dlg, name, value, domain, path, expires )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    ( name, value, domain, path, expires ) = panel.GetValue()
                    
                    self._SetCookie( name, value, domain, path, expires )
                    
                    self._session_manager.SetSessionDirty( self._network_context )
                    
                else:
                    
                    break
                    
                
            
        
        self._Update()
        
    
    def _ExportToClipboard( self ):
        
        cookies = self._listctrl.GetData( only_selected = True )
        
        if len( cookies ) == 0:
            
            return
            
        
        cookie_data_flat = [ [ cookie.name, cookie.value, cookie.domain, cookie.path, cookie.expires ] for cookie in cookies ]
        
        json_text = json.dumps( cookie_data_flat )
        
        CG.client_controller.pub( 'clipboard', 'text', json_text )
        
    
    # these methods are thanks to user's contribution!
    def _ImportCookiesTXT( self ):
        
        with QP.FileDialog( self, 'select cookies.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen ) as f_dlg:
            
            if f_dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = f_dlg.GetPath()
                
                self._ImportCookiesTXTPaths( ( path, ) )
                
            
        
    
    def _ImportCookiesTXTPaths( self, paths ):
        
        num_added = 0
        
        for path in paths:
            
            cj = http.cookiejar.MozillaCookieJar()
            
            try:
                
                cj.load( path, ignore_discard = True, ignore_expires = True )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', 'It looks like that cookies.txt failed to load. Unfortunately, not all formats are supported.' )
                
                return
                
            
            for cookie in cj:
                
                self._session.cookies.set_cookie( cookie )
                
                num_added += 1
                
            
        
        ClientGUIDialogsMessage.ShowInformation( self, f'Added {HydrusNumbers.ToHumanInt(num_added)} cookies!' )
        
        self._Update()
        
    
    def _ImportFromClipboard( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
            
            return
            
        
        try:
            
            cookie_data_flat = json.loads( raw_text )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Did not understand what was in the clipboard!', str(e) )
            
            return
            
        
        try:
            
            cookie_data_flat_domain_filtered = cookie_data_flat
            
            if self._network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                my_domain = self._network_context.context_data
                
                cookie_data_flat_domain_filtered = [ ( name, value, domain, path, expires ) for ( name, value, domain, path, expires ) in cookie_data_flat if domain.endswith( my_domain ) ]
                
            
            if len( cookie_data_flat ) != len( cookie_data_flat_domain_filtered ):
                
                text = f'Of the {HydrusNumbers.ToHumanInt(len(cookie_data_flat))} cookies in your clipboard, {HydrusNumbers.ToHumanInt(len( cookie_data_flat_domain_filtered ))} match this domain. What do you want to import?'
                
                if len( cookie_data_flat_domain_filtered ) == 0:
                    
                    yes_label = 'nothing to import--bail out now'
                    
                else:
                    
                    yes_label = 'import only the matching cookies'
                    
                
                ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, text, yes_label = yes_label, no_label = 'import everything--I intend to rename the domains', check_for_cancelled = True )
                
                if was_cancelled:
                    
                    return
                    
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    if len( cookie_data_flat_domain_filtered ) == 0:
                        
                        return
                        
                    
                    cookie_data_flat = cookie_data_flat_domain_filtered
                    
                
            
            if len( cookie_data_flat ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'There were no cookies in the clipboard for this domain!' )
                
                return
                
            
            domains = sorted( { domain for ( name, value, domain, path, expires ) in cookie_data_flat } )
            
            message = f'About to import {HydrusNumbers.ToHumanInt(len(cookie_data_flat))} cookies for the domains {HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( domains, no_trailing_whitespace = True )}. Is that ok?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message = message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            num_added = 0
            
            for ( name, value, domain, path, expires ) in cookie_data_flat:
                
                self._SetCookie( name, value, domain, path, expires )
                
                num_added += 1
                
            
            ClientGUIDialogsMessage.ShowInformation( self, f'Added {HydrusNumbers.ToHumanInt(num_added)} cookies!' )
            
            self._Update()
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Had trouble importing what was in the clipboard!', str(e) )
            
            return
            
        
    
    def _SetCookie( self, name, value, domain, path, expires ):
        
        version = 0
        port = None
        port_specified = False
        domain_specified = True
        domain_initial_dot = domain.startswith( '.' )
        path_specified = True
        secure = False
        discard = False
        comment = None
        comment_url = None
        rest = {}
        
        cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
        
        self._session.cookies.set_cookie( cookie )
        
    
    def _Update( self ):
        
        self._session = self._session_manager.GetSession( self._network_context )
        
        cookies = list( self._session.cookies )
        
        self._listctrl.SetData( cookies )
        
    
