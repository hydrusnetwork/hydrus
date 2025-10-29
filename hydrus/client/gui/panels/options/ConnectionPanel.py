from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.networking import ClientNetworkingSessions

class ConnectionPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        general = ClientGUICommon.StaticBox( self, 'general' )
        
        if self._new_options.GetBoolean( 'advanced_mode' ):
            
            network_timeout_min = 1
            network_timeout_max = 86400 * 30
            
            error_wait_time_min = 1
            error_wait_time_max = 86400 * 30
            
            max_network_jobs_max = 1000
            
            max_network_jobs_per_domain_max = 100
            
        else:
            
            network_timeout_min = 3
            network_timeout_max = 600
            
            error_wait_time_min = 3
            error_wait_time_max = 1800
            
            max_network_jobs_max = 30
            
            max_network_jobs_per_domain_max = 5
            
        
        self._max_connection_attempts_allowed = ClientGUICommon.BetterSpinBox( general, min = 1, max = 10 )
        self._max_connection_attempts_allowed.setToolTip( ClientGUIFunctions.WrapToolTip( 'This refers to timeouts when actually making the initial connection.' ) )
        
        self._max_request_attempts_allowed_get = ClientGUICommon.BetterSpinBox( general, min = 1, max = 10 )
        self._max_request_attempts_allowed_get.setToolTip( ClientGUIFunctions.WrapToolTip( 'This refers to timeouts when waiting for a response to our GET requests, whether that is the start or an interruption part way through.' ) )
        
        self._network_timeout = ClientGUICommon.BetterSpinBox( general, min = network_timeout_min, max = network_timeout_max )
        self._network_timeout.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a network connection cannot be made in this duration or, once started, it experiences inactivity for six times this duration, it will be considered dead and retried or abandoned.' ) )
        
        self._connection_error_wait_time = ClientGUICommon.BetterSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
        self._connection_error_wait_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a network connection times out as above, it will wait increasing multiples of this base time before retrying.' ) )
        
        self._serverside_bandwidth_wait_time = ClientGUICommon.BetterSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
        self._serverside_bandwidth_wait_time.setToolTip( ClientGUIFunctions.WrapToolTip( 'If a server returns a failure status code indicating it is short on bandwidth, and the server does not give a Retry-After header response, the network job will wait increasing multiples of this base time before retrying.' ) )
        
        self._domain_network_infrastructure_error_velocity = ClientGUITime.VelocityCtrl( general, 0, 100, 30, hours = True, minutes = True, seconds = True, per_phrase = 'within', unit = 'errors' )
        
        self._max_network_jobs = ClientGUICommon.BetterSpinBox( general, min = 1, max = max_network_jobs_max )
        self._max_network_jobs_per_domain = ClientGUICommon.BetterSpinBox( general, min = 1, max = max_network_jobs_per_domain_max )
        
        self._set_requests_ca_bundle_env = QW.QCheckBox( general )
        self._set_requests_ca_bundle_env.setToolTip( ClientGUIFunctions.WrapToolTip( 'Just testing something here; ignore unless hydev asks you to use it please. Requires restart. Note: this breaks the self-signed certificates of hydrus services.' ) )
        
        self._do_not_verify_regular_https = QW.QCheckBox( general )
        self._do_not_verify_regular_https.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will not verify any HTTPS traffic. This tech is important for security, so only enable this mode temporarily, to test out unusual situations.' ) )
        
        #
        
        proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
        
        if ClientNetworkingSessions.SOCKS_PROXY_OK:
            
            default_text = 'socks5://ip:port'
            
        else:
            
            default_text = 'http://ip:port'
            
        
        self._http_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, default_text )
        self._https_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, default_text )
        self._no_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel, '' )
        
        #
        
        self._set_requests_ca_bundle_env.setChecked( self._new_options.GetBoolean( 'set_requests_ca_bundle_env' ) )
        self._do_not_verify_regular_https.setChecked( not self._new_options.GetBoolean( 'verify_regular_https' ) )
        
        self._http_proxy.SetValue( self._new_options.GetNoneableString( 'http_proxy' ) )
        self._https_proxy.SetValue( self._new_options.GetNoneableString( 'https_proxy' ) )
        self._no_proxy.SetValue( self._new_options.GetNoneableString( 'no_proxy' ) )
        
        self._max_connection_attempts_allowed.setValue( self._new_options.GetInteger( 'max_connection_attempts_allowed' ) )
        self._max_request_attempts_allowed_get.setValue( self._new_options.GetInteger( 'max_request_attempts_allowed_get' ) )
        self._network_timeout.setValue( self._new_options.GetInteger( 'network_timeout' ) )
        self._connection_error_wait_time.setValue( self._new_options.GetInteger( 'connection_error_wait_time' ) )
        self._serverside_bandwidth_wait_time.setValue( self._new_options.GetInteger( 'serverside_bandwidth_wait_time' ) )
        
        number = self._new_options.GetInteger( 'domain_network_infrastructure_error_number' )
        time_delta = self._new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
        
        self._domain_network_infrastructure_error_velocity.SetValue( ( number, time_delta ) )
        
        self._max_network_jobs.setValue( self._new_options.GetInteger( 'max_network_jobs' ) )
        self._max_network_jobs_per_domain.setValue( self._new_options.GetInteger( 'max_network_jobs_per_domain' ) )
        
        #
        
        if self._new_options.GetBoolean( 'advanced_mode' ):
            
            label = 'As you are in advanced mode, these options have very low and high limits. Be very careful about lowering delay time or raising max number of connections too far, as things will break.'
            
            st = ClientGUICommon.BetterStaticText( general, label = label )
            st.setObjectName( 'HydrusWarning' )
            
            st.setWordWrap( True )
            
            general.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        rows = []
        
        rows.append( ( 'max connection attempts allowed per request: ', self._max_connection_attempts_allowed ) )
        rows.append( ( 'max retries allowed per request: ', self._max_request_attempts_allowed_get ) )
        rows.append( ( 'network timeout (seconds): ', self._network_timeout ) )
        rows.append( ( 'connection error retry wait (seconds): ', self._connection_error_wait_time ) )
        rows.append( ( 'serverside bandwidth retry wait (seconds): ', self._serverside_bandwidth_wait_time ) )
        rows.append( ( 'Halt new jobs as long as this many network infrastructure errors on their domain (0 for never wait): ', self._domain_network_infrastructure_error_velocity ) )
        rows.append( ( 'max number of simultaneous active network jobs: ', self._max_network_jobs ) )
        rows.append( ( 'max number of simultaneous active network jobs per domain: ', self._max_network_jobs_per_domain ) )
        rows.append( ( 'DEBUG: set the REQUESTS_CA_BUNDLE env to certifi cacert.pem on program start:', self._set_requests_ca_bundle_env ) )
        rows.append( ( 'DEBUG: do not verify regular https traffic:', self._do_not_verify_regular_https ) )
        
        gridbox = ClientGUICommon.WrapInGrid( general, rows )
        
        general.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        text = 'PROTIP: Use a system-wide VPN or other software to handle this externally if you can. This tech is old and imperfect.'
        text += '\n' * 2
        text += 'Enter strings such as "http://ip:port" or "http://user:pass@ip:port" to use for http and https traffic. It should take effect immediately on dialog ok. Note that you have to enter "http://", not "https://" (an HTTP proxy forwards your traffic, which when you talk to an https:// address will be encrypted, but it does not wrap that in an extra layer of encryption itself).'
        text += '\n' * 2
        text += '"NO_PROXY" DOES NOT WORK UNLESS YOU HAVE A CUSTOM BUILD OF REQUESTS, SORRY! no_proxy takes the form of comma-separated hosts/domains, just as in curl or the NO_PROXY environment variable. When http and/or https proxies are set, they will not be used for these.'
        text += '\n' * 2
        
        if ClientNetworkingSessions.SOCKS_PROXY_OK:
            
            text += 'It looks like you have SOCKS support! You should also be able to enter (socks4 or) "socks5://ip:port".'
            text += '\n'
            text += 'Use socks4a or socks5h to force remote DNS resolution, on the proxy server.'
            
        else:
            
            text += 'It does not look like you have SOCKS support! If you want it, try adding "pysocks" (or "requests[socks]")!'
            
        
        st = ClientGUICommon.BetterStaticText( proxy_panel, text )
        
        st.setWordWrap( True )
        
        proxy_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'http: ', self._http_proxy ) )
        rows.append( ( 'https: ', self._https_proxy ) )
        rows.append( ( 'no_proxy: ', self._no_proxy ) )
        
        gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
        
        proxy_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, general, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'set_requests_ca_bundle_env', self._set_requests_ca_bundle_env.isChecked() )
        self._new_options.SetBoolean( 'verify_regular_https', not self._do_not_verify_regular_https.isChecked() )
        
        self._new_options.SetNoneableString( 'http_proxy', self._http_proxy.GetValue() )
        self._new_options.SetNoneableString( 'https_proxy', self._https_proxy.GetValue() )
        self._new_options.SetNoneableString( 'no_proxy', self._no_proxy.GetValue() )
        
        self._new_options.SetInteger( 'max_connection_attempts_allowed', self._max_connection_attempts_allowed.value() )
        self._new_options.SetInteger( 'max_request_attempts_allowed_get', self._max_request_attempts_allowed_get.value() )
        self._new_options.SetInteger( 'network_timeout', self._network_timeout.value() )
        self._new_options.SetInteger( 'connection_error_wait_time', self._connection_error_wait_time.value() )
        self._new_options.SetInteger( 'serverside_bandwidth_wait_time', self._serverside_bandwidth_wait_time.value() )
        
        ( number, time_delta ) = self._domain_network_infrastructure_error_velocity.GetValue()
        
        self._new_options.SetInteger( 'domain_network_infrastructure_error_number', number )
        self._new_options.SetInteger( 'domain_network_infrastructure_error_time_delta', time_delta )
        
        self._new_options.SetInteger( 'max_network_jobs', self._max_network_jobs.value() )
        self._new_options.SetInteger( 'max_network_jobs_per_domain', self._max_network_jobs_per_domain.value() )
        
    
