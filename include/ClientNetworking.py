import ClientConstants as CC
import ClientNetworkingDomain
import collections
import cPickle
import cStringIO
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import itertools
import os
import random
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import threading
import time
import traceback
import urllib
import urlparse
import yaml

urllib3.disable_warnings( InsecureRequestWarning )

def CombineGETURLWithParameters( url, params_dict ):
    
    def make_safe( text ):
        
        # convert unicode to raw bytes
        # quote that to be url-safe, ignoring the default '/' 'safe' character
        
        return urllib.quote( HydrusData.ToByteString( text ), '' )
        
    
    request_string = '&'.join( ( make_safe( key ) + '=' + make_safe( value ) for ( key, value ) in params_dict.items() ) )
    
    return url + '?' + request_string
    
def ConvertStatusCodeAndDataIntoExceptionInfo( status_code, data, is_hydrus_service = False ):
    
    error_text = data
    
    if len( error_text ) > 1024:
        
        large_chunk = error_text[:4096]
        
        smaller_chunk = large_chunk[:256]
        
        HydrusData.DebugPrint( large_chunk )
        
        error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
        error_text += os.linesep
        error_text += smaller_chunk
        
    
    if status_code == 304:
        
        eclass = HydrusExceptions.NotModifiedException
        
    elif status_code == 401:
        
        eclass = HydrusExceptions.PermissionException
        
    elif status_code == 403:
        
        eclass = HydrusExceptions.ForbiddenException
        
    elif status_code == 404:
        
        eclass = HydrusExceptions.NotFoundException
        
    elif status_code == 419:
        
        eclass = HydrusExceptions.SessionException
        
    elif status_code == 426:
        
        eclass = HydrusExceptions.NetworkVersionException
        
    elif status_code == 509:
        
        eclass = HydrusExceptions.BandwidthException
        
    elif status_code >= 500:
        
        if is_hydrus_service and status_code == 503:
            
            eclass = HydrusExceptions.ServerBusyException
            
        else:
            
            eclass = HydrusExceptions.ServerException
            
        
    else:
        
        eclass = HydrusExceptions.NetworkException
        
    
    e = eclass( error_text )
    
    return ( e, error_text )
    
class NetworkBandwidthManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER
    SERIALISABLE_NAME = 'Bandwidth Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_bandwidth_trackers = collections.defaultdict( HydrusNetworking.BandwidthTracker )
        self._network_contexts_to_bandwidth_rules = collections.defaultdict( HydrusNetworking.BandwidthRules )
        
        for context_type in [ CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_DOWNLOADER, CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD ]:
            
            self._network_contexts_to_bandwidth_rules[ NetworkContext( context_type ) ] = HydrusNetworking.BandwidthRules()
            
        
    
    def _CanStartRequest( self, network_contexts ):
        
        for network_context in network_contexts:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            if not bandwidth_rules.CanStartRequest( bandwidth_tracker ):
                
                return False
                
            
        
        return True
        
    
    def _GetRules( self, network_context ):
        
        if network_context not in self._network_contexts_to_bandwidth_rules:
            
            network_context = NetworkContext( network_context.context_type ) # i.e. the default
            
        
        return self._network_contexts_to_bandwidth_rules[ network_context ]
        
    
    def _GetSerialisableInfo( self ):
        
        # note this discards ephemeral network contexts, which have page_key-specific identifiers and are temporary, not meant to be hung onto forever, and are generally invisible to the user
        all_serialisable_trackers = [ ( network_context.GetSerialisableTuple(), tracker.GetSerialisableTuple() ) for ( network_context, tracker ) in self._network_contexts_to_bandwidth_trackers.items() if not network_context.IsEphemeral() ]
        all_serialisable_rules = [ ( network_context.GetSerialisableTuple(), rules.GetSerialisableTuple() ) for ( network_context, rules ) in self._network_contexts_to_bandwidth_rules.items() ]
        
        return ( all_serialisable_trackers, all_serialisable_rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( all_serialisable_trackers, all_serialisable_rules ) = serialisable_info
        
        for ( serialisable_network_context, serialisable_tracker ) in all_serialisable_trackers:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            tracker = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tracker )
            
            self._network_contexts_to_bandwidth_trackers[ network_context ] = tracker
            
        
        for ( serialisable_network_context, serialisable_rules ) in all_serialisable_rules:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rules )
            
            self._network_contexts_to_bandwidth_rules[ network_context ] = rules
            
        
    
    def _ReportRequestUsed( self, network_contexts ):
        
        for network_context in network_contexts:
            
            self._network_contexts_to_bandwidth_trackers[ network_context ].ReportRequestUsed()
            
        
        self._SetDirty()
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def CanContinueDownload( self, network_contexts ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanContinueDownload( bandwidth_tracker ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanDoWork( self, network_contexts, expected_requests = 3, expected_bytes = 1048576, threshold = 30 ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanDoWork( bandwidth_tracker, expected_requests = expected_requests, expected_bytes = expected_bytes, threshold = threshold ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanStartRequest( self, network_contexts ):
        
        with self._lock:
            
            return self._CanStartRequest( network_contexts )
            
        
    
    def DeleteRules( self, network_context ):
        
        with self._lock:
            
            if network_context.context_data is None:
                
                return # can't delete 'default' network contexts
                
            else:
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            
            self._SetDirty()
            
        
    
    def DeleteHistory( self, network_contexts ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_bandwidth_trackers:
                    
                    del self._network_contexts_to_bandwidth_trackers[ network_context ]
                    
                    if network_context == GLOBAL_NETWORK_CONTEXT:
                        
                        # just to reset it, so we have a 0 global context at all times
                        self._network_contexts_to_bandwidth_trackers[ GLOBAL_NETWORK_CONTEXT ] = HydrusNetworking.BandwidthTracker()
                        
                    
                
            
            self._SetDirty()
            
        
    
    def GetDefaultRules( self ):
        
        with self._lock:
            
            result = []
            
            for ( network_context, bandwidth_rules ) in self._network_contexts_to_bandwidth_rules.items():
                
                if network_context.IsDefault():
                    
                    result.append( ( network_context, bandwidth_rules ) )
                    
                
            
            return result
            
        
    
    def GetCurrentMonthSummary( self, network_context ):
        
        with self._lock:
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            return bandwidth_tracker.GetCurrentMonthSummary()
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self, network_context ):
        
        with self._lock:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            return bandwidth_rules.GetBandwidthStringsAndGaugeTuples( bandwidth_tracker )
            
        
    
    def GetNetworkContextsForUser( self, history_time_delta_threshold = None ):
        
        with self._lock:
            
            result = set()
            
            for ( network_context, bandwidth_tracker ) in self._network_contexts_to_bandwidth_trackers.items():
                
                if network_context.IsDefault() or network_context.IsEphemeral():
                    
                    continue
                    
                
                if network_context != GLOBAL_NETWORK_CONTEXT and history_time_delta_threshold is not None:
                    
                    if bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, history_time_delta_threshold ) == 0:
                        
                        continue
                        
                    
                
                result.add( network_context )
                
            
            return result
            
        
    
    def GetRules( self, network_context ):
        
        with self._lock:
            
            return self._GetRules( network_context )
            
        
    
    def GetTracker( self, network_context ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_bandwidth_trackers:
                
                return self._network_contexts_to_bandwidth_trackers[ network_context ]
                
            else:
                
                return HydrusNetworking.BandwidthTracker()
                
            
        
    
    def GetWaitingEstimate( self, network_contexts ):
        
        with self._lock:
            
            estimates = []
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                estimates.append( bandwidth_rules.GetWaitingEstimate( bandwidth_tracker ) )
                
            
            if len( estimates ) == 0:
                
                return 0
                
            else:
                
                return max( estimates )
                
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def ReportDataUsed( self, network_contexts, num_bytes ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                self._network_contexts_to_bandwidth_trackers[ network_context ].ReportDataUsed( num_bytes )
                
            
            self._SetDirty()
            
        
    
    def ReportRequestUsed( self, network_contexts ):
        
        with self._lock:
            
            self._ReportRequestUsed( network_contexts )
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetRules( self, network_context, bandwidth_rules ):
        
        with self._lock:
            
            if len( bandwidth_rules.GetRules() ) == 0:
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            else:
                
                self._network_contexts_to_bandwidth_rules[ network_context ] = bandwidth_rules
                
            
            self._SetDirty()
            
        
    
    def TryToStartRequest( self, network_contexts ):
        
        # this wraps canstart and reportrequest in one transaction to stop 5/1 rq/s happening due to race condition
        
        with self._lock:
            
            if not self._CanStartRequest( network_contexts ):
                
                return False
                
            
            self._ReportRequestUsed( network_contexts )
            
            return True
            
        
    
    def UsesDefaultRules( self, network_context ):
        
        with self._lock:
            
            return network_context not in self._network_contexts_to_bandwidth_rules
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER ] = NetworkBandwidthManager

class NetworkContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT
    SERIALISABLE_NAME = 'Network Context'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, context_type = None, context_data = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.context_type = context_type
        self.context_data = context_data
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.context_type, self.context_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return self.ToUnicode()
        
    
    def _GetSerialisableInfo( self ):
        
        if self.context_data is None:
            
            serialisable_context_data = self.context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                serialisable_context_data = self.context_data
                
            else:
                
                serialisable_context_data = self.context_data.encode( 'hex' )
                
            
        
        return ( self.context_type, serialisable_context_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.context_type, serialisable_context_data ) = serialisable_info
        
        if serialisable_context_data is None:
            
            self.context_data = serialisable_context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                self.context_data = serialisable_context_data
                
            else:
                
                self.context_data = serialisable_context_data.decode( 'hex' )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( context_type, serialisable_context_data ) = old_serialisable_info
            
            if serialisable_context_data is not None:
                
                # unicode subscription names were erroring on the hex call
                if context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                    
                    context_data = serialisable_context_data.decode( 'hex' )
                    
                    serialisable_context_data = context_data
                    
                
            
            new_serialisable_info = ( context_type, serialisable_context_data )
            
            return ( 2, new_serialisable_info )
            
        
    
    def IsDefault( self ):
        
        return self.context_data is None and self.context_type != CC.NETWORK_CONTEXT_GLOBAL
        
    
    def IsEphemeral( self ):
        
        return self.context_type in ( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD )
        
    
    def ToUnicode( self ):
        
        if self.context_data is None:
            
            if self.context_type == CC.NETWORK_CONTEXT_GLOBAL:
                
                return 'global'
                
            else:
                
                return CC.network_context_type_string_lookup[ self.context_type ] + ' default'
                
            
        else:
            
            if self.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = self.context_data
                
                services_manager = HG.client_controller.services_manager
                
                if services_manager.ServiceExists( service_key ):
                    
                    name = HG.client_controller.services_manager.GetName( service_key )
                    
                else:
                    
                    name = 'unknown service--probably deleted or an unusual test'
                    
                
            else:
                
                name = HydrusData.ToUnicode( self.context_data )
                
            
            return CC.network_context_type_string_lookup[ self.context_type ] + ': ' + name
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT ] = NetworkContext

GLOBAL_NETWORK_CONTEXT = NetworkContext( CC.NETWORK_CONTEXT_GLOBAL )

class NetworkEngine( object ):
    
    MAX_JOBS = 10 # turn this into an option
    
    def __init__( self, controller, bandwidth_manager, session_manager, domain_manager, login_manager ):
        
        self.controller = controller
        
        self.bandwidth_manager = bandwidth_manager
        self.session_manager = session_manager
        self.domain_manager = domain_manager
        self.login_manager = login_manager
        
        self.bandwidth_manager.engine = self
        self.session_manager.engine = self
        self.domain_manager.engine = self
        self.login_manager.engine = self
        
        self._lock = threading.Lock()
        
        self._new_work_to_do = threading.Event()
        
        self._jobs_awaiting_validity = []
        self._current_validation_process = None
        self._jobs_bandwidth_throttled = []
        self._jobs_login_throttled = []
        self._current_login_process = None
        self._jobs_ready_to_start = []
        self._jobs_downloading = []
        
        self._pause_all_new_network_traffic = self.controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        
        self._is_running = False
        self._is_shutdown = False
        self._local_shutdown = False
        
    
    def AddJob( self, job ):
        
        with self._lock:
            
            job.engine = self
            
            self._jobs_awaiting_validity.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def IsRunning( self ):
        
        with self._lock:
            
            return self._is_running
            
        
    
    def IsShutdown( self ):
        
        with self._lock:
            
            return self._is_shutdown
            
        
    
    def MainLoop( self ):
        
        def ProcessValidationJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif not job.IsValid():
                
                if job.CanValidateInPopup():
                    
                    if self._current_validation_process is None:
                        
                        validation_process = job.GenerateValidationPopupProcess()
                        
                        self.controller.CallToThread( validation_process.Start )
                        
                        self._current_validation_process = validation_process
                        
                        job.SetStatus( u'validation presented to user\u2026' )
                        
                    else:
                        
                        job.SetStatus( u'waiting in user validation queue\u2026' )
                        
                        job.Sleep( 5 )
                        
                    
                    return True
                    
                else:
                    
                    error_text = u'network context not currently valid!'
                    
                    job.SetError( HydrusExceptions.ValidationException( error_text ), error_text )
                    
                    return False
                    
                
            else:
                
                self._jobs_bandwidth_throttled.append( job )
                
                return False
                
            
        
        def ProcessCurrentValidationJob():
            
            if self._current_validation_process is not None:
                
                if self._current_validation_process.IsDone():
                    
                    self._current_validation_process = None
                    
                
            
        
        def ProcessBandwidthJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif not job.BandwidthOK():
                
                return True
                
            else:
                
                self._jobs_login_throttled.append( job )
                
                return False
                
            
        
        def ProcessLoginJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif job.NeedsLogin():
                
                try:
                    
                    job.CheckCanLogin()
                    
                except Exception as e:
                    
                    job.SetError( e, HydrusData.ToUnicode( e ) )
                    
                    return False
                    
                
                if self._current_login_process is None:
                    
                    login_process = job.GenerateLoginProcess()
                    
                    self.controller.CallToThread( login_process.Start )
                    
                    self._current_login_process = login_process
                    
                    job.SetStatus( u'logging in\u2026' )
                    
                else:
                    
                    job.SetStatus( u'waiting in login queue\u2026' )
                    
                    job.Sleep( 5 )
                    
                
                return True
                
            else:
                
                self._jobs_ready_to_start.append( job )
                
                return False
                
            
        
        def ProcessCurrentLoginJob():
            
            if self._current_login_process is not None:
                
                if self._current_login_process.IsDone():
                    
                    self._current_login_process = None
                    
                
            
        
        def ProcessReadyJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif len( self._jobs_downloading ) < self.MAX_JOBS:
                
                if self._pause_all_new_network_traffic:
                    
                    job.SetStatus( u'all new network traffic is paused\u2026' )
                    
                    return True
                    
                else:
                    
                    self.controller.CallToThread( job.Start )
                    
                    self._jobs_downloading.append( job )
                    
                    return False
                    
                
            else:
                
                job.SetStatus( u'waiting for download slot\u2026' )
                
                return True
                
            
        
        def ProcessDownloadingJob( job ):
            
            if job.IsDone():
                
                return False
                
            else:
                
                return True
                
            
        
        self._is_running = True
        
        while not ( self._local_shutdown or self.controller.ModelIsShutdown() ):
            
            with self._lock:
                
                self._jobs_awaiting_validity = filter( ProcessValidationJob, self._jobs_awaiting_validity )
                
                ProcessCurrentValidationJob()
                
                self._jobs_bandwidth_throttled = filter( ProcessBandwidthJob, self._jobs_bandwidth_throttled )
                
                self._jobs_login_throttled = filter( ProcessLoginJob, self._jobs_login_throttled )
                
                ProcessCurrentLoginJob()
                
                self._jobs_ready_to_start = filter( ProcessReadyJob, self._jobs_ready_to_start )
                
                self._jobs_downloading = filter( ProcessDownloadingJob, self._jobs_downloading )
                
            
            # we want to catch the rollover of the second for bandwidth jobs
            
            now_with_subsecond = time.time()
            subsecond_part = now_with_subsecond % 1
            
            time_until_next_second = 1.0 - subsecond_part
            
            self._new_work_to_do.wait( time_until_next_second )
            
            self._new_work_to_do.clear()
            
        
        self._is_running = False
        
        self._is_shutdown = True
        
    
    def PausePlayNewJobs( self ):
        
        self._pause_all_new_network_traffic = not self._pause_all_new_network_traffic
        
        self.controller.new_options.SetBoolean( 'pause_all_new_network_traffic', self._pause_all_new_network_traffic )
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
        self._new_work_to_do.set()
        
    
class NetworkJob( object ):
    
    IS_HYDRUS_SERVICE = False
    
    def __init__( self, method, url, body = None, referral_url = None, temp_path = None ):
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network Job: ' + method + ' ' + url )
            
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        self._body = body
        self._referral_url = referral_url
        self._temp_path = temp_path
        
        self._files = None
        self._for_login = False
        
        self._current_connection_attempt_number = 1
        
        self._additional_headers = {}
        
        self._creation_time = HydrusData.GetNow()
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._wake_time = 0
        
        self._content_type = None
        
        self._stream_io = cStringIO.StringIO()
        
        self._error_exception = Exception( 'Exception not initialised.' ) # PyLint hint, wew
        self._error_exception = None
        self._error_text = None
        
        self._is_done_event = threading.Event()
        
        self._is_done = False
        self._is_cancelled = False
        self._bandwidth_manual_override = False
        
        self._last_time_ongoing_bandwidth_failed = 0
        
        self._status_text = u'initialising\u2026'
        self._num_bytes_read = 0
        self._num_bytes_to_read = 1
        
        self._network_contexts = self._GenerateNetworkContexts()
        
        ( self._session_network_context, self._login_network_context ) = self._GenerateSpecificNetworkContexts()
        
    
    def _CanReattemptRequest( self ):
        
        if self._method == 'GET':
            
            max_attempts_allowed = 5
            
        elif self._method == 'POST':
            
            max_attempts_allowed = 1
            
        
        return self._current_connection_attempt_number <= max_attempts_allowed
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( GLOBAL_NETWORK_CONTEXT )
        
        domain = ClientNetworkingDomain.ConvertURLIntoDomain( self._url )
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain )
        
        network_contexts.extend( ( NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain ) for domain in domains ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we always store cookies in the larger session
        # but we can login to a specific subdomain
        
        domain = ClientNetworkingDomain.ConvertURLIntoDomain( self._url )
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( domain )
        
        session_network_context = NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domains[-1] )
        login_network_context = NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
        return ( session_network_context, login_network_context )
        
    
    def _SendRequestAndGetResponse( self ):
        
        with self._lock:
            
            session = self._GetSession()
            
            method = self._method
            url = self._url
            data = self._body
            files = self._files
            
            headers = self.engine.domain_manager.GetHeaders( self._network_contexts )
            
            if self.IS_HYDRUS_SERVICE:
                
                headers[ 'User-Agent' ] = 'hydrus client/' + str( HC.NETWORK_VERSION )
                
            
            if self._referral_url is not None:
                
                headers[ 'referer' ] = self._referral_url
                
            
            for ( key, value ) in self._additional_headers.items():
                
                headers[ key ] = value
                
            
            self._status_text = u'sending request\u2026'
            
        
        connect_timeout = HG.client_controller.new_options.GetInteger( 'network_timeout' )
        
        read_timeout = connect_timeout * 6
        
        response = session.request( method, url, data = data, files = files, headers = headers, stream = True, timeout = ( connect_timeout, read_timeout ) )
        
        return response
        
    
    def _GetSession( self ):
        
        return self.engine.session_manager.GetSession( self._session_network_context )
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _IsDone( self ):
        
        if self._is_done:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _ObeysBandwidth( self ):
        
        return not ( self._method == 'POST' or self._bandwidth_manual_override or self._for_login )
        
    
    def _OngoingBandwidthOK( self ):
        
        now = HydrusData.GetNow()
        
        if now == self._last_time_ongoing_bandwidth_failed: # it won't have changed, so no point spending any cpu checking
            
            return False
            
        else:
            
            result = self.engine.bandwidth_manager.CanContinueDownload( self._network_contexts )
            
            if not result:
                
                self._last_time_ongoing_bandwidth_failed = now
                
            
            return result
            
        
    
    def _ReadResponse( self, response, stream_dest, max_allowed = None ):
        
        with self._lock:
            
            if 'content-length' in response.headers:
            
                self._num_bytes_to_read = int( response.headers[ 'content-length' ] )
                
                if max_allowed is not None and self._num_bytes_to_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url ' + self._url + ' looks too large!' )
                    
                
            else:
                
                self._num_bytes_to_read = None
                
            
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            if self._IsCancelled():
                
                return
                
            
            stream_dest.write( chunk )
            
            chunk_length = len( chunk )
            
            with self._lock:
                
                self._num_bytes_read += chunk_length
                
                if max_allowed is not None and self._num_bytes_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url ' + self._url + ' was too large!' )
                    
                
            
            self._ReportDataUsed( chunk_length )
            self._WaitOnOngoingBandwidth()
            
            if HG.view_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        if self._num_bytes_to_read is not None and self._num_bytes_read < self._num_bytes_to_read * 0.8:
            
            raise HydrusExceptions.NetworkException( 'Did not read enough data! Was expecting ' + HydrusData.ConvertIntToBytes( self._num_bytes_to_read ) + ' but only got ' + HydrusData.ConvertIntToBytes( self._num_bytes_read ) + '.' )
            
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
        self.engine.bandwidth_manager.ReportDataUsed( self._network_contexts, num_bytes )
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._error_exception = e
        self._error_text = error
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
        self._is_done_event.set()
        
    
    def _Sleep( self, seconds ):
        
        self._wake_time = HydrusData.GetNow() + seconds
        
    
    def _WaitOnOngoingBandwidth( self ):
        
        while not self._OngoingBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.1 )
            
        
    
    def AddAdditionalHeader( self, key, value ):
        
        with self._lock:
            
            self._additional_headers[ key ] = value
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._ObeysBandwidth():
                
                result = self.engine.bandwidth_manager.TryToStartRequest( self._network_contexts )
                
                if result:
                    
                    self._bandwidth_tracker.ReportRequestUsed()
                    
                else:
                    
                    waiting_duration = self.engine.bandwidth_manager.GetWaitingEstimate( self._network_contexts )
                    
                    if waiting_duration < 2:
                        
                        self._status_text = u'bandwidth free imminently\u2026'
                        
                    else:
                        
                        pending_timestamp = HydrusData.GetNow() + waiting_duration
                        
                        waiting_str = HydrusData.ConvertTimestampToPrettyPending( pending_timestamp )
                        
                        self._status_text = u'bandwidth free in ' + waiting_str + u'\u2026'
                        
                    
                    if waiting_duration > 1200:
                        
                        self._Sleep( 30 )
                        
                    elif waiting_duration > 120:
                        
                        self._Sleep( 10 )
                        
                    elif waiting_duration > 10:
                        
                        self._Sleep( 1 )
                        
                    
                
                return result
                
            else:
                
                self._bandwidth_tracker.ReportRequestUsed()
                
                self.engine.bandwidth_manager.ReportRequestUsed( self._network_contexts )
                
                return True
                
            
        
    
    def Cancel( self ):
        
        with self._lock:
            
            self._status_text = 'cancelled!'
            
            self._SetCancelled()
            
        
    
    def CanValidateInPopup( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.CanValidateInPopup( self._network_contexts )
            
        
    
    def CheckCanLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise HydrusExceptions.LoginException( 'Login jobs should not be asked if they can login!' )
                
            else:
                
                return self.engine.login_manager.CheckCanLogin( self._login_network_context )
                
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked to generate login processes!' )
                
            else:
                
                return self.engine.login_manager.GenerateLoginProcess( self._login_network_context )
                
            
        
    
    def GenerateValidationPopupProcess( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.GenerateValidationPopupProcess( self._network_contexts )
            
        
    
    def GetContent( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetContentType( self ):
        
        with self._lock:
            
            return self._content_type
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetErrorException( self ):
        
        with self._lock:
            
            return self._error_exception
            
        
    
    def GetErrorText( self ):
        
        with self._lock:
            
            return self._error_text
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list( self._network_contexts )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._status_text, self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), self._num_bytes_read, self._num_bytes_to_read )
            
        
    
    def GetTotalDataUsed( self ):
        
        with self._lock:
            
            return self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
            
        
    
    def HasError( self ):
        
        with self._lock:
            
            return self._error_exception is not None
            
        
    
    def IsAsleep( self ):
        
        with self._lock:
            
            return not HydrusData.TimeHasPassed( self._wake_time )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._IsDone()
            
        
    
    def IsValid( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.IsValid( self._network_contexts )
            
        
    
    def NeedsLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                return False
                
            else:
                
                return self.engine.login_manager.NeedsLogin( self._login_network_context )
                
            
        
    
    def NoEngineYet( self ):
        
        return self.engine is None
        
    
    def ObeysBandwidth( self ):
        
        return self._ObeysBandwidth()
        
    
    def OverrideBandwidth( self ):
        
        with self._lock:
            
            self._bandwidth_manual_override = True
            
            self._wake_time = 0
            
        
    
    def SetError( self, e, error ):
        
        with self._lock:
            
            self._SetError( e, error )
            
        
    
    def SetFiles( self, files ):
        
        with self._lock:
            
            self._files = files
            
        
    
    def SetForLogin( self, for_login ):
        
        with self._lock:
            
            self._for_login = for_login
            
        
    
    def SetStatus( self, text ):
        
        with self._lock:
            
            self._status_text = text
            
        
    
    def Sleep( self, seconds ):
        
        with self._lock:
            
            self._Sleep( seconds )
            
        
    
    def Start( self ):
        
        try:
            
            request_completed = False
            
            while not request_completed:
                
                try:
                    
                    response = self._SendRequestAndGetResponse()
                    
                    with self._lock:
                        
                        if self._body is not None:
                            
                            self._ReportDataUsed( len( self._body ) )
                            
                        
                    
                    if response.ok:
                        
                        with self._lock:
                            
                            self._status_text = u'downloading\u2026'
                            
                        
                        if self._temp_path is None:
                            
                            self._ReadResponse( response, self._stream_io, 104857600 )
                            
                        else:
                            
                            with open( self._temp_path, 'wb' ) as f:
                                
                                self._ReadResponse( response, f )
                                
                            
                        
                        with self._lock:
                            
                            self._status_text = 'done!'
                            
                        
                    else:
                        
                        with self._lock:
                            
                            self._status_text = str( response.status_code ) + ' - ' + str( response.reason )
                            
                        
                        self._ReadResponse( response, self._stream_io )
                        
                        with self._lock:
                            
                            self._stream_io.seek( 0 )
                            
                            data = self._stream_io.read()
                            
                            ( e, error_text ) = ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data, self.IS_HYDRUS_SERVICE )
                            
                            self._SetError( e, error_text )
                            
                        
                    
                    if 'Content-Type' in response.headers:
                        
                        self._content_type = response.headers[ 'Content-Type' ]
                        
                    
                    request_completed = True
                    
                except requests.exceptions.ChunkedEncodingError:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Unable to complete request--it broke mid-way!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'connection broke mid-request--retrying'
                        
                    
                    time.sleep( 3 )
                    
                except requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Could not connect!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'connection failed--retrying'
                        
                    
                    time.sleep( 3 )
                    
                except requests.exceptions.ReadTimeout:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Connection successful, but reading response timed out!' )
                        
                    
                    with self._lock:
                        
                        self._status_text = u'read timed out--retrying'
                        
                    
                    time.sleep( 3 )
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                self._status_text = 'unexpected error!'
                
                trace = traceback.format_exc()
                
                HydrusData.Print( trace )
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
    def WaitUntilDone( self ):
        
        while True:
            
            self._is_done_event.wait( 5 )
            
            if self.IsDone():
                
                break
                
            
        
        with self._lock:
            
            if self.engine.controller.ModelIsShutdown():
                
                raise HydrusExceptions.ShutdownException()
                
            elif self._error_exception is not None:
                
                if isinstance( self._error_exception, Exception ):
                    
                    raise self._error_exception
                    
                else:
                    
                    raise Exception( 'Problem in network error handling.' )
                    
                
            elif self._IsCancelled():
                
                if self._method == 'POST':
                    
                    message = 'Upload cancelled!'
                    
                else:
                    
                    message = 'Download cancelled!'
                    
                
                raise HydrusExceptions.CancelledException( message )
                
            
        
    
class NetworkJobDownloader( NetworkJob ):
    
    def __init__( self, downloader_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_key = downloader_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER, self._downloader_key ) )
        
        return network_contexts
        
    
class NetworkJobDownloaderQuery( NetworkJobDownloader ):
    
    def __init__( self, downloader_page_key, downloader_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJobDownloader.__init__( self, downloader_key, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, self._downloader_page_key ) )
        
        return network_contexts
        
    
class NetworkJobDownloaderQueryTemporary( NetworkJob ):
    
    def __init__( self, downloader_page_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, self._downloader_page_key ) )
        
        return network_contexts
        
    
class NetworkJobSubscription( NetworkJobDownloader ):
    
    def __init__( self, subscription_key, downloader_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._subscription_key = subscription_key
        
        NetworkJobDownloader.__init__( self, downloader_key, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
class NetworkJobSubscriptionTemporary( NetworkJob ):
    
    # temporary because we will move to the downloader_key stuff when that is available
    
    def __init__( self, subscription_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._subscription_key = subscription_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
class NetworkJobHydrus( NetworkJob ):
    
    IS_HYDRUS_SERVICE = True
    
    def __init__( self, service_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._service_key = service_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _CheckHydrusVersion( self, service_type, response ):
        
        service_string = HC.service_string_lookup[ service_type ]
        
        headers = response.headers
        
        if 'server' not in headers or service_string not in headers[ 'server' ]:
            
            raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
            
        
        server_header = headers[ 'server' ]
        
        ( service_string_gumpf, network_version ) = server_header.split( '/' )
        
        network_version = int( network_version )
        
        if network_version != HC.NETWORK_VERSION:
            
            if network_version > HC.NETWORK_VERSION:
                
                message = 'Your client is out of date; please download the latest release.'
                
            else:
                
                message = 'The server is out of date; please ask its admin to update to the latest release.'
                
            
            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + str( network_version ) + ', whereas your client\'s is ' + str( HC.NETWORK_VERSION ) + '! ' + message )
            
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we store cookies on and login to the same hydrus-specific context
        
        session_network_context = NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        login_network_context = session_network_context
        
        return ( session_network_context, login_network_context )
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportDataUsed( num_bytes )
            
        
        NetworkJob._ReportDataUsed( self, num_bytes )
        
    
    def _SendRequestAndGetResponse( self ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportRequestUsed()
            
        
        response = NetworkJob._SendRequestAndGetResponse( self )
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            self._CheckHydrusVersion( service_type, response )
            
        
        return response
        
    
class NetworkJobThreadWatcher( NetworkJob ):
    
    def __init__( self, thread_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._thread_key = thread_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD, self._thread_key ) )
        
        return network_contexts
        
    
class NetworkSessionManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER
    SERIALISABLE_NAME = 'Session Manager'
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 60
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_sessions = {}
        
        self._network_contexts_to_session_timeouts = {}
        
    
    def _GenerateSession( self, network_context ):
        
        session = requests.Session()
        
        if network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
            
            session.verify = False
            
        
        return session
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_contexts_to_sessions = [ ( network_context.GetSerialisableTuple(), cPickle.dumps( session ) ) for ( network_context, session ) in self._network_contexts_to_sessions.items() ]
        
        return serialisable_network_contexts_to_sessions
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_network_contexts_to_sessions = serialisable_info
        
        for ( serialisable_network_context, pickled_session ) in serialisable_network_contexts_to_sessions:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            session = cPickle.loads( str( pickled_session ) )
            
            session.cookies.clear_session_cookies()
            
            self._network_contexts_to_sessions[ network_context ] = session
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def ClearSession( self, network_context ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_sessions:
                
                del self._network_contexts_to_sessions[ network_context ]
                
                self._SetDirty()
                
            
        
    
    def GetSession( self, network_context ):
        
        with self._lock:
            
            # just in case one of these slips through somehow
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                second_level_domain = ClientNetworkingDomain.ConvertDomainIntoSecondLevelDomain( network_context.context_data )
                
                network_context = NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, second_level_domain )
                
            
            if network_context not in self._network_contexts_to_sessions:
                
                self._network_contexts_to_sessions[ network_context ] = self._GenerateSession( network_context )
                
            
            session = self._network_contexts_to_sessions[ network_context ]
            
            #
            
            if network_context not in self._network_contexts_to_session_timeouts:
                
                self._network_contexts_to_session_timeouts[ network_context ] = 0
                
            
            if HydrusData.TimeHasPassed( self._network_contexts_to_session_timeouts[ network_context ] ):
                
                session.cookies.clear_session_cookies()
                
            
            self._network_contexts_to_session_timeouts[ network_context ] = HydrusData.GetNow() + self.SESSION_TIMEOUT
            
            #
            
            # tumblr can't into ssl for some reason, and the data subdomain they use has weird cert properties, looking like amazon S3
            # perhaps it is inward-facing somehow? whatever the case, let's just say fuck it for tumblr
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN and network_context.context_data == 'tumblr.com':
                
                session.verify = False
                
            
            #
            
            self._SetDirty()
            
            return session
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER ] = NetworkSessionManager
