import ClientConstants as CC
import ClientDownloading
import ClientImporting
import ClientNetworking
import ClientRatings
import ClientThreading
import hashlib
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNetwork
import HydrusNetworking
import HydrusSerialisable
import json
import os
import threading
import time
import traceback
import wx

def GenerateDefaultServiceDictionary( service_type ):
    
    dictionary = HydrusSerialisable.SerialisableDictionary()
    
    if service_type in HC.REMOTE_SERVICES:
        
        dictionary[ 'credentials' ] = HydrusNetwork.Credentials( 'hostname', 80 )
        dictionary[ 'no_requests_reason' ] = ''
        dictionary[ 'no_requests_until' ] = 0
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            dictionary[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( HydrusNetwork.Account.GenerateUnknownAccount() )
            dictionary[ 'next_account_sync' ] = 0
            
            if service_type in HC.REPOSITORIES:
                
                dictionary[ 'metadata' ] = HydrusNetwork.Metadata()
                dictionary[ 'paused' ] = False
                dictionary[ 'tag_archive_sync' ] = []
                
            
        
        if service_type == HC.IPFS:
            
            dictionary[ 'credentials' ] = HydrusNetwork.Credentials( '127.0.0.1', 5001 )
            dictionary[ 'multihash_prefix' ] = ''
            
        
    
    if service_type == HC.LOCAL_TAG:
        
        dictionary[ 'tag_archive_sync' ] = []
        
    
    if service_type == HC.LOCAL_BOORU:
        
        dictionary[ 'port' ] = None
        dictionary[ 'upnp_port' ] = None
        dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
        dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
        
    
    if service_type in HC.RATINGS_SERVICES:
        
        dictionary[ 'shape' ] = ClientRatings.CIRCLE
        dictionary[ 'colours' ] = []
        
        if service_type == HC.LOCAL_RATING_LIKE:
            
            dictionary[ 'colours' ] = ClientRatings.default_like_colours.items()
            
        elif service_type == HC.LOCAL_RATING_NUMERICAL:
            
            dictionary[ 'colours' ] = ClientRatings.default_numerical_colours.items()
            dictionary[ 'num_stars' ] = 5
            dictionary[ 'allow_zero' ]= True
            
        
    
    return dictionary
    
def GenerateService( service_key, service_type, name, dictionary = None ):
    
    if dictionary is None:
        
        dictionary = GenerateDefaultServiceDictionary( service_type )
        
    
    if service_type == HC.LOCAL_TAG:
        
        cl = ServiceLocalTag
        
    elif service_type == HC.LOCAL_RATING_LIKE:
        
        cl = ServiceLocalRatingLike
        
    elif service_type == HC.LOCAL_RATING_NUMERICAL:
        
        cl = ServiceLocalRatingNumerical
        
    elif service_type in HC.REPOSITORIES:
        
        cl = ServiceRepository
        
    elif service_type in HC.RESTRICTED_SERVICES:
        
        cl = ServiceRestricted
        
    elif service_type == HC.IPFS:
        
        cl = ServiceIPFS
        
    elif service_type in HC.REMOTE_SERVICES:
        
        cl = ServiceRemote
        
    elif service_type == HC.LOCAL_BOORU:
        
        cl = ServiceLocalBooru
        
    else:
        
        cl = Service
        
    
    return cl( service_key, service_type, name, dictionary )
    
class Service( object ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        if dictionary is None:
            
            dictionary = GenerateDefaultServiceDictionary( service_type )
            
        
        self._service_key = service_key
        self._service_type = service_type
        self._name = name
        
        self._dirty = False
        self._lock = threading.Lock()
        
        self._LoadFromDictionary( dictionary )
        
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def _GetFunctionalStatus( self ):
        
        return ( True, 'service is functional' )
        
    
    def _GetSerialisableDictionary( self ):
        
        return HydrusSerialisable.SerialisableDictionary()
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        pass
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        HG.client_controller.pub( 'service_updated', self )
        
    
    def Duplicate( self ):
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            duplicate = GenerateService( self._service_key, self._service_type, self._name, dictionary )
            
            return duplicate
            
        
    
    def GetSerialisableDictionary( self ):
        
        with self._lock:
            
            self._dirty = False
            
            return self._GetSerialisableDictionary()
            
        
    
    def GetName( self ):
        
        with self._lock:
            
            return self._name
            
        
    
    def GetServiceKey( self ):
        
        with self._lock:
            
            return self._service_key
            
        
    
    def GetServiceType( self ):
        
        with self._lock:
            
            return self._service_type
            
        
    
    def GetStatusString( self ):
        
        with self._lock:
            
            ( functional, status ) = self._GetFunctionalStatus()
            
            if not functional:
                
                return 'service not functional: ' + status
                
            else:
                
                return status
                
            
        
    
    def IsDirty( self ):
        
        return self._dirty
        
    
    def IsFunctional( self ):
        
        with self._lock:
            
            ( functional, status ) = self._GetFunctionalStatus()
            
            return functional
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetName( self, name ):
        
        with self._lock:
            
            self._name = name
            
        
    
    def ToTuple( self ):
        
        dictionary = self._GetSerialisableDictionary()
        
        return ( self._service_key, self._service_type, self._name, dictionary )
        
    
class ServiceLocalBooru( Service ):
    
    def _GetFunctionalStatus( self ):
        
        if not self._bandwidth_rules.CanStartRequest( self._bandwidth_tracker ):
            
            return ( False, 'bandwidth exceeded' )
            
        
        return Service._GetFunctionalStatus( self )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'port' ] = self._port
        dictionary[ 'upnp_port' ] = self._upnp_port
        dictionary[ 'bandwidth_tracker' ] = self._bandwidth_tracker
        dictionary[ 'bandwidth_rules' ] = self._bandwidth_rules
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._port = dictionary[ 'port' ]
        self._upnp_port = dictionary[ 'upnp_port' ]
        self._bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
        self._bandwidth_rules = dictionary[ 'bandwidth_rules' ]
        
        # this should support the same serverservice interface so we can just toss it at the regular serverengine and all the bandwidth will work ok
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            return self._bandwidth_rules.CanStartRequest( self._bandwidth_tracker )
            
        
    
    def GetUPnPPort( self ):
        
        with self._lock:
            
            return self._upnp_port
            
        
    
    def GetPort( self ):
        
        with self._lock:
            
            return self._port
            
        
    
    def ReportDataUsed( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportDataUsed( num_bytes )
            
        
    
    def ReportRequestUsed( self ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportRequestUsed()
            
        
    
class ServiceLocalTag( Service ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'tag_archive_sync' ] = self._tag_archive_sync.items()
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._tag_archive_sync = dict( dictionary[ 'tag_archive_sync' ] )
        
    
    def GetTagArchiveSync( self ):
        
        with self._lock:
            
            return self._tag_archive_sync
            
        
    
class ServiceLocalRating( Service ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'shape' ] = self._shape
        dictionary[ 'colours' ] = self._colours.items()
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._shape = dictionary[ 'shape' ]
        self._colours = dict( dictionary[ 'colours' ] )
        
    
    def GetColour( self, rating_state ):
        
        with self._lock:
            
            return self._colours[ rating_state ]
            
        
    
    def GetShape( self ):
        
        with self._lock:
            
            return self._shape
            
        
    
class ServiceLocalRatingLike( ServiceLocalRating ):
    
    pass
    
class ServiceLocalRatingNumerical( ServiceLocalRating ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceLocalRating._GetSerialisableDictionary( self )
        
        dictionary[ 'num_stars' ] = self._num_stars
        dictionary[ 'allow_zero' ] = self._allow_zero
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceLocalRating._LoadFromDictionary( self, dictionary )
        
        self._num_stars = dictionary[ 'num_stars' ]
        self._allow_zero = dictionary[ 'allow_zero' ]
        
    
    def AllowZero( self ):
        
        with self._lock:
            
            return self._allow_zero
            
        
    
    def GetNumStars( self ):
        
        with self._lock:
            
            return self._num_stars
            
        
    
class ServiceRemote( Service ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        Service.__init__( self, service_key, service_type, name, dictionary = dictionary )
        
        self.network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        
    
    def _DelayFutureRequests( self, reason, duration = None ):
        
        if duration is None:
            
            duration = self._GetErrorWaitPeriod()
            
        
        next_no_requests_until = HydrusData.GetNow() + duration
        
        if next_no_requests_until > self._no_requests_until:
            
            self._no_requests_reason = reason
            self._no_requests_until = HydrusData.GetNow() + duration
            
        
        self._SetDirty()
        
    
    def _GetBaseURL( self ):
        
        ( host, port ) = self._credentials.GetAddress()
        
        base_url = 'https://' + host + ':' + str( port ) + '/'
        
        return base_url
        
    
    def _GetErrorWaitPeriod( self ):
        
        return 3600 * 4
        
    
    def _GetFunctionalStatus( self ):
        
        if not HydrusData.TimeHasPassed( self._no_requests_until ):
            
            return ( False, self._no_requests_reason + ' - next request ' + HydrusData.ConvertTimestampToPrettyPending( self._no_requests_until ) )
            
        
        example_nj = ClientNetworking.NetworkJobHydrus( self._service_key, 'GET', self._GetBaseURL() )
        
        can_start = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts() )
        
        if not can_start:
            
            return ( False, 'bandwidth exceeded' )
            
        
        return Service._GetFunctionalStatus( self )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'credentials' ] = self._credentials
        dictionary[ 'no_requests_reason' ] = self._no_requests_reason
        dictionary[ 'no_requests_until' ] = self._no_requests_until
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._credentials = dictionary[ 'credentials' ]
        self._no_requests_reason = dictionary[ 'no_requests_reason' ]
        self._no_requests_until = dictionary[ 'no_requests_until' ]
        
    
    def DelayFutureRequests( self, reason, duration = None ):
        
        with self._lock:
            
            self._DelayFutureRequests( reason, duration = None )
            
        
    
    def GetBandwidthCurrentMonthSummary( self ):
        
        with self._lock:
            
            return HG.client_controller.network_engine.bandwidth_manager.GetCurrentMonthSummary( self.network_context )
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self ):
        
        with self._lock:
            
            return HG.client_controller.network_engine.bandwidth_manager.GetBandwidthStringsAndGaugeTuples( self.network_context )
            
        
    
    def GetBaseURL( self ):
        
        with self._lock:
            
            return self._GetBaseURL()
            
        
    
    def GetCredentials( self ):
        
        with self._lock:
            
            return self._credentials
            
        
    
    def SetCredentials( self, credentials ):
        
        with self._lock:
            
            self._credentials = credentials
            
            self._SetDirty()
            
        
    
class ServiceRestricted( ServiceRemote ):
    
    def _DealWithAccountError( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        self._next_account_sync = HydrusData.GetNow()
        
        self._SetDirty()
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
    
    def _DealWithFundamentalNetworkError( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        self._next_account_sync = HydrusData.GetNow() + HC.UPDATE_DURATION * 10
        
        self._SetDirty()
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
    
    def _GetErrorWaitPeriod( self ):
        
        if self._account.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ):
            
            return 900
            
        else:
            
            return HC.UPDATE_DURATION
            
        
    
    def _GetFunctionalStatus( self, ignore_account = False ):
        
        if not self._credentials.HasAccessKey():
            
            return ( False, 'this service has no access key set' )
            
        
        if not ignore_account and not self._account.IsFunctional():
            
            return ( False, 'account problem: ' + self._account.GetStatusString() )
            
        
        return ServiceRemote._GetFunctionalStatus( self )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( self._account )
        dictionary[ 'next_account_sync' ] = self._next_account_sync
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRemote._LoadFromDictionary( self, dictionary )
        
        self._account = HydrusNetwork.Account.GenerateAccountFromSerialisableTuple( dictionary[ 'account' ] )
        self._next_account_sync = dictionary[ 'next_account_sync' ]
        
    
    def GetAccount( self ):
        
        with self._lock:
            
            return self._account
            
        
    
    def GetNextAccountSyncStatus( self ):
        
        return 'next account sync ' + HydrusData.ConvertTimestampToPrettyPending( self._next_account_sync )
        
    
    def HasPermission( self, content_type, action ):
        
        with self._lock:
            
            return self._account.HasPermission( content_type, action )
            
        
    
    def IsDirty( self ):
        
        if ServiceRemote.IsDirty( self ):
            
            return True
            
        
        return self._account.IsDirty()
        
    
    def IsFunctional( self, ignore_account = False ):
        
        with self._lock:
            
            ( functional, status ) = self._GetFunctionalStatus( ignore_account = ignore_account )
            
            return functional
            
        
    
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            if method == HC.GET:
                
                query = HydrusNetwork.DumpToGETQuery( request_args )
                
                body = ''
                
                content_type = None
                
            elif method == HC.POST:
                
                query = ''
                
                if command == 'file':
                    
                    content_type = HC.APPLICATION_OCTET_STREAM
                    
                    body = request_args[ 'file' ]
                    
                    del request_args[ 'file' ]
                    
                else:
                    
                    content_type = HC.APPLICATION_JSON
                    
                    body = HydrusNetwork.DumpToBodyString( request_args )
                    
                
            
            if query != '':
                
                command_and_query = command + '?' + query
                
            else:
                
                command_and_query = command
                
            
            url = self.GetBaseURL() + command_and_query
            
            if method == HC.GET:
                
                method = 'GET'
                
            elif method == HC.POST:
                
                method = 'POST'
                
            
            network_job = ClientNetworking.NetworkJobHydrus( self._service_key, method, url, body = body, temp_path = temp_path )
            
            if command in ( '', 'access_key', 'access_key_verification' ):
                
                # don't try to establish a session key for these requests
                network_job.SetForLogin( True )
                
                if command == 'access_key_verification':
                    
                    network_job.AddAdditionalHeader( 'Hydrus-Key', self._credentials.GetAccessKey().encode( 'hex' ) )
                    
                
            
            if content_type is not None:
                
                network_job.AddAdditionalHeader( 'Content-Type', HC.mime_string_lookup[ content_type ] )
                
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            content = network_job.GetContent()
            
            content_type = network_job.GetContentType()
            
            if content_type == 'application/json':
                
                response = HydrusNetwork.ParseBodyString( content )
                
                if command == 'account' and 'account' in response:
                    
                    data_used = network_job.GetTotalDataUsed()
                    
                    account = response[ 'account' ]
                    
                    # because the account was one behind when it was serialised! mostly do this just to sync up nicely with the service bandwidth tracker
                    account.ReportDataUsed( data_used )
                    account.ReportRequestUsed()
                    
                
            else:
                
                response = content
                
            
            return response
            
        except Exception as e:
            
            with self._lock:
                
                if isinstance( e, HydrusExceptions.ServerBusyException ):
                    
                    self._DelayFutureRequests( 'server was busy', 5 * 60 )
                    
                elif isinstance( e, HydrusExceptions.SessionException ):
                    
                    HG.client_controller.network_engine.session_manager.ClearSession( self.network_context )
                    
                elif isinstance( e, HydrusExceptions.PermissionException ):
                    
                    self._DealWithAccountError()
                    
                elif isinstance( e, HydrusExceptions.ForbiddenException ):
                    
                    self._DealWithAccountError()
                    
                elif isinstance( e, HydrusExceptions.NetworkVersionException ):
                    
                    self._DealWithFundamentalNetworkError()
                    
                elif isinstance( e, HydrusExceptions.NotFoundException ):
                    
                    self._DelayFutureRequests( 'got an unexpected 404', HC.UPDATE_DURATION )
                    
                elif isinstance( e, HydrusExceptions.BandwidthException ):
                    
                    self._DelayFutureRequests( 'service has exceeded bandwidth', HC.UPDATE_DURATION * 5 )
                    
                else:
                    
                    self._DelayFutureRequests( HydrusData.ToUnicode( e ) )
                    
                
                
            
            raise
            
        
    
    def SetClean( self ):
        
        ServiceRemote.SetClean( self )
        
        self._account.SetClean()
        
    
    def SyncAccount( self, force = False ):
        
        with self._lock:
            
            name = self._name
            
            if force:
                
                do_it = True
                
                if force:
                    
                    self._no_requests_until = 0
                    
                
            else:
                
                do_it = HydrusData.TimeHasPassed( self._next_account_sync )
                
            
        
        if do_it:
            
            try:
                
                response = self.Request( HC.GET, 'account' )
                
                with self._lock:
                    
                    self._account = response[ 'account' ]
                    
                    if force:
                        
                        self._no_requests_until = 0
                        
                    
                
                HG.client_controller.pub( 'notify_new_permissions' )
                
            except HydrusExceptions.NetworkException as e:
                
                HydrusData.Print( 'Failed to refresh account for ' + name + ':' )
                
                HydrusData.Print( e )
                
                if force:
                    
                    raise
                    
                
            except Exception:
                
                HydrusData.Print( 'Failed to refresh account for ' + name + ':' )
                
                HydrusData.Print( traceback.format_exc() )
                
                if force:
                    
                    raise
                    
                
            finally:
                
                with self._lock:
                    
                    self._next_account_sync = HydrusData.GetNow() + HC.UPDATE_DURATION * 5
                    
                    self._SetDirty()
                    
                    HG.client_controller.pub( 'important_dirt_to_clean' )
                    
                
            
        
    
class ServiceRepository( ServiceRestricted ):
    
    def _CanSync( self ):
        
        if self._paused:
            
            return False
            
        
        if HG.client_controller.options[ 'pause_repo_sync' ]:
            
            return False
            
        
        ( result, reason ) = self._GetFunctionalStatus()
        
        return result
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRestricted._GetSerialisableDictionary( self )
        
        dictionary[ 'metadata' ] = self._metadata
        dictionary[ 'paused' ] = self._paused
        dictionary[ 'tag_archive_sync' ] = self._tag_archive_sync.items()
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRestricted._LoadFromDictionary( self, dictionary )
        
        self._metadata = dictionary[ 'metadata' ]
        self._paused = dictionary[ 'paused' ]
        self._tag_archive_sync = dict( dictionary[ 'tag_archive_sync' ] )
        
    
    def CanDoIdleShutdownWork( self ):
        
        with self._lock:
            
            if not self._CanSync():
                
                return False
                
            
            service_key = self._service_key
            
        
        ( download_value, processing_value, range ) = HG.client_controller.Read( 'repository_progress', service_key )
        
        return processing_value < range
        
    
    def GetNextUpdateDueString( self ):
        
        with self._lock:
            
            return self._metadata.GetNextUpdateDueString( from_client = True )
            
        
    
    def GetTagArchiveSync( self ):
        
        with self._lock:
            
            return self._tag_archive_sync
            
        
    
    def GetUpdateHashes( self ):
        
        with self._lock:
            
            return self._metadata.GetUpdateHashes()
            
        
    
    def GetUpdateInfo( self ):
        
        with self._lock:
            
            return self._metadata.GetUpdateInfo()
            
        
    
    def IsPaused( self ):
        
        with self._lock:
            
            return self._paused
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            self._SetDirty()
            
            HG.client_controller.pub( 'important_dirt_to_clean' )
            
            if not self._paused:
                
                HG.client_controller.pub( 'notify_new_permissions' )
                
            
        
    
    def Reset( self ):
        
        with self._lock:
            
            self._no_requests_reason = ''
            self._no_requests_until = 0
            
            self._account = HydrusNetwork.Account.GenerateUnknownAccount()
            self._next_account_sync = 0
            
            self._metadata = HydrusNetwork.Metadata()
            
            self._SetDirty()
            
            HG.client_controller.pub( 'important_dirt_to_clean' )
            
            HG.client_controller.Write( 'reset_repository', self )
            
        
    
    def Sync( self, only_process_when_idle = False, stop_time = None ):
        
        try:
            
            self.SyncDownloadMetadata()
            
            self.SyncDownloadUpdates( stop_time )
            
            self.SyncProcessUpdates( only_process_when_idle, stop_time )
            
            self.SyncThumbnails( stop_time )
            
        finally:
            
            if self.IsDirty():
                
                HG.client_controller.pub( 'important_dirt_to_clean' )
                
            
        
    
    def SyncDownloadUpdates( self, stop_time ):
        
        with self._lock:
            
            if not self._CanSync():
                
                return
                
            
            name = self._name
            service_key = self._service_key
            
        
        update_hashes = HG.client_controller.Read( 'missing_repository_update_hashes', service_key )
        
        if len( update_hashes ) > 0:
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_key.SetVariable( 'popup_title', name + ' sync: downloading updates' )
                
                HG.client_controller.pub( 'message', job_key )
                
                for ( i, update_hash ) in enumerate( update_hashes ):
                    
                    status = 'update ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( update_hashes ) )
                    
                    HG.client_controller.pub( 'splash_set_status_text', status, print_to_log = False )
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( update_hashes ) ) )
                    
                    with self._lock:
                        
                        if not self._CanSync():
                            
                            return
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', 3 * 60 )
                            
                        
                        return
                        
                    
                    try:
                        
                        update_network_string = self.Request( HC.GET, 'update', { 'update_hash' : update_hash } )
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        HydrusData.Print( 'Attempting to download an update for ' + name + ' resulted in a network error:' )
                        
                        HydrusData.Print( e )
                        
                        return
                        
                    
                    update_network_string_hash = hashlib.sha256( update_network_string ).digest()
                    
                    if update_network_string_hash != update_hash:
                        
                        with self._lock:
                            
                            self._paused = True
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'Update ' + update_hash.encode( 'hex' ) + ' downloaded from the ' + self._name + ' repository had hash ' + update_network_string_hash.encode( 'hex' ) + '! This is a serious error!'
                        message += os.linesep * 2
                        message += 'The repository has been paused for now. Please look into what could be wrong and report this to the hydrus dev.'
                        
                        HydrusData.ShowText( message )
                        
                        return
                        
                    
                    try:
                        
                        update = HydrusSerialisable.CreateFromNetworkString( update_network_string )
                        
                    except Exception as e:
                        
                        with self._lock:
                            
                            self._paused = True
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'Update ' + update_hash.encode( 'hex' ) + ' downloaded from the ' + self._name + ' repository failed to load! This is a serious error!'
                        message += os.linesep * 2
                        message += 'The repository has been paused for now. Please look into what could be wrong and report this to the hydrus dev.'
                        
                        HydrusData.ShowText( message )
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    
                    if isinstance( update, HydrusNetwork.DefinitionsUpdate ):
                        
                        mime = HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS
                        
                    elif isinstance( update, HydrusNetwork.ContentUpdate ):
                        
                        mime = HC.APPLICATION_HYDRUS_UPDATE_CONTENT
                        
                    else:
                        
                        with self._lock:
                            
                            self._paused = True
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'Update ' + update_hash.encode( 'hex' ) + ' downloaded from the ' + self._name + ' was not a valid update--it was a ' + repr( update ) + '! This is a serious error!'
                        message += os.linesep * 2
                        message += 'The repository has been paused for now. Please look into what could be wrong and report this to the hydrus dev.'
                        
                        HydrusData.ShowText( message )
                        
                        return
                        
                    
                    try:
                        
                        HG.client_controller.WriteSynchronous( 'import_update', update_network_string, update_hash, mime )
                        
                    except Exception as e:
                        
                        with self._lock:
                            
                            self._paused = True
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'While downloading updates for the ' + self._name + ' repository, an update failed to import! The error follows:'
                        
                        HydrusData.ShowText( message )
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    
                
                job_key.SetVariable( 'popup_text_1', 'finished' )
                job_key.DeleteVariable( 'popup_gauge_1' )
                
            finally:
                
                job_key.Finish()
                job_key.Delete( 5 )
                
            
        
    
    def SyncDownloadMetadata( self ):
        
        with self._lock:
            
            if not self._CanSync():
                
                return
                
            
            do_it = self._metadata.UpdateDue( from_client = True )
            
            next_update_index = self._metadata.GetNextUpdateIndex()
            
            service_key = self._service_key
            
            name = self._name
            
        
        if do_it:
            
            try:
                
                response = self.Request( HC.GET, 'metadata', { 'since' : next_update_index } )
                
                metadata_slice = response[ 'metadata_slice' ]
                
            except HydrusExceptions.NetworkException as e:
                
                HydrusData.Print( 'Attempting to download metadata for ' + name + ' resulted in a network error:' )
                
                HydrusData.Print( e )
                
                return
                
            
            HG.client_controller.WriteSynchronous( 'associate_repository_update_hashes', service_key, metadata_slice )
            
            with self._lock:
                
                self._metadata.UpdateFromSlice( metadata_slice )
                
                self._SetDirty()
                
            
        
    
    def SyncProcessUpdates( self, only_when_idle = False, stop_time = None ):
        
        with self._lock:
            
            if not self._CanSync():
                
                return
                
            
        
        if only_when_idle and not HG.client_controller.CurrentlyIdle():
            
            return
            
        
        try:
            
            ( did_some_work, did_everything ) = HG.client_controller.WriteSynchronous( 'process_repository', self._service_key, only_when_idle, stop_time )
            
            if did_some_work:
                
                with self._lock:
                    
                    self._SetDirty()
                    
                
            
            if not did_everything:
                
                time.sleep( 3 ) # stop spamming of repo sync daemon from bringing this up again too quick
                
            
        except Exception as e:
            
            with self._lock:
                
                message = 'While processing updates for the ' + self._name + ' repository, an update failed to import! The error follows:'
                
                HydrusData.ShowText( message )
                
                HydrusData.ShowException( e )
                
                self._paused = True
                
                self._SetDirty()
                
            
            HG.client_controller.pub( 'important_dirt_to_clean' )
            
        
    
    def SyncThumbnails( self, stop_time ):
        
        with self._lock:
            
            if not self._CanSync():
                
                return
                
            
            name = self._name
            service_key = self._service_key
            
        
        thumbnail_hashes = HG.client_controller.Read( 'missing_thumbnail_hashes', service_key )
        
        num_to_do = len( thumbnail_hashes )
        
        if num_to_do > 0:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_key.SetVariable( 'popup_title', name + ' sync: downloading thumbnails' )
                
                HG.client_controller.pub( 'message', job_key )
                
                for ( i, thumbnail_hash ) in enumerate( thumbnail_hashes ):
                    
                    status = 'thumbnail ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do )
                    
                    HG.client_controller.pub( 'splash_set_status_text', status, print_to_log = False )
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( i + 1, num_to_do ) )
                    
                    with self._lock:
                        
                        if not self._CanSync():
                            
                            break
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', 3 * 60 )
                            
                        
                        return
                        
                    
                    try:
                        
                        thumbnail = self.Request( HC.GET, 'thumbnail', { 'hash' : thumbnail_hash } )
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        HydrusData.Print( 'Attempting to download a thumbnail for ' + name + ' resulted in a network error:' )
                        
                        HydrusData.Print( e )
                        
                        return
                        
                    
                    client_files_manager.AddFullSizeThumbnail( thumbnail_hash, thumbnail )
                    
                
                job_key.SetVariable( 'popup_text_1', 'finished' )
                job_key.DeleteVariable( 'popup_gauge_1' )
                
            finally:
                
                job_key.Finish()
                job_key.Delete( 5 )
                
            
        
    
class ServiceIPFS( ServiceRemote ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'multihash_prefix' ] = self._multihash_prefix
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRemote._LoadFromDictionary( self, dictionary )
        
        self._multihash_prefix = dictionary[ 'multihash_prefix' ]
        
    
    def _ConvertMultihashToURLTree( self, name, size, multihash ):
        
        api_base_url = self._GetAPIBaseURL()
        
        links_url = api_base_url + 'object/links/' + multihash
        
        network_job = ClientNetworking.NetworkJob( 'GET', links_url )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        data = network_job.GetContent()
        
        links_json = json.loads( data )
        
        is_directory = False
        
        if 'Links' in links_json:
            
            for link in links_json[ 'Links' ]:
                
                if link[ 'Name' ] != '':
                    
                    is_directory = True
                    
                
            
        
        if is_directory:
            
            children = []
            
            for link in links_json[ 'Links' ]:
                
                subname = link[ 'Name' ]
                subsize = link[ 'Size' ]
                submultihash = link[ 'Hash' ]
                
                children.append( self._ConvertMultihashToURLTree( subname, subsize, submultihash ) )
                
            
            if size is None:
                
                size = sum( ( subsize for ( type_gumpf, subname, subsize, submultihash ) in children ) )
                
            
            return ( 'directory', name, size, children )
            
        else:
            
            url = api_base_url + 'cat/' + multihash
            
            return ( 'file', name, size, url )
            
        
    
    def _GetAPIBaseURL( self ):
        
        ( host, port ) = self._credentials.GetAddress()
        
        api_base_url = 'http://' + host + ':' + str( port ) + '/api/v0/'
        
        return api_base_url
        
    
    def GetDaemonVersion( self ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'version'
        
        network_job = ClientNetworking.NetworkJob( 'GET', url )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        data = network_job.GetContent()
        
        j = json.loads( data )
        
        return j[ 'Version' ]
        
    
    def GetMultihashPrefix( self ):
        
        with self._lock:
            
            return self._multihash_prefix
            
        
    
    def ImportFile( self, multihash ):
        
        def on_wx_select_tree( job_key, url_tree ):
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogSelectFromURLTree( None, url_tree ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    urls = dlg.GetURLs()
                    
                    if len( urls ) > 0:
                        
                        HG.client_controller.CallToThread( ClientImporting.THREADDownloadURLs, job_key, urls, multihash )
                        
                    
                
            
        
        def off_wx():
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_text_1', 'Looking up multihash information' )
            
            HG.client_controller.pub( 'message', job_key )
            
            with self._lock:
                
                url_tree = self._ConvertMultihashToURLTree( multihash, None, multihash )
                
            
            if url_tree[0] == 'file':
                
                url = url_tree[3]
                
                HG.client_controller.CallToThread( ClientImporting.THREADDownloadURL, job_key, url, multihash )
                
            else:
                
                job_key.SetVariable( 'popup_text_1', 'Waiting for user selection' )
                
                wx.CallAfter( on_wx_select_tree, job_key, url_tree )
                
            
        
        HG.client_controller.CallToThread( off_wx )
        
    
    def PinDirectory( self, hashes, note ):
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'creating ipfs directory on ' + self._name )
        
        HG.client_controller.pub( 'message', job_key )
        
        try:
            
            file_info = []
            
            hashes = list( hashes )
            
            hashes.sort()
            
            for ( i, hash ) in enumerate( hashes ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                job_key.SetVariable( 'popup_text_1', 'pinning files: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( hashes ) ) )
                job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( hashes ) ) )
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                mime = media_result.GetMime()
                
                result = HG.client_controller.Read( 'service_filenames', self._service_key, { hash } )
                
                if len( result ) == 0:
                    
                    multihash = self.PinFile( hash, mime )
                    
                else:
                    
                    ( multihash, ) = result
                    
                
                file_info.append( ( hash, mime, multihash ) )
                
            
            with self._lock:
                
                api_base_url = self._GetAPIBaseURL()
                
            
            url = api_base_url + 'object/new?arg=unixfs-dir'
            
            network_job = ClientNetworking.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            data = network_job.GetContent()
            
            response_json = json.loads( data )
            
            for ( i, ( hash, mime, multihash ) ) in enumerate( file_info ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                job_key.SetVariable( 'popup_text_1', 'creating directory: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( file_info ) ) )
                job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( file_info ) ) )
                
                object_multihash = response_json[ 'Hash' ]
                
                filename = hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ]
                
                url = api_base_url + 'object/patch/add-link?arg=' + object_multihash + '&arg=' + filename + '&arg=' + multihash
                
                network_job = ClientNetworking.NetworkJob( 'GET', url )
                
                network_job.OverrideBandwidth()
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                network_job.WaitUntilDone()
                
                data = network_job.GetContent()
                
                response_json = json.loads( data )
                
            
            directory_multihash = response_json[ 'Hash' ]
            
            url = api_base_url + 'pin/add?arg=' + directory_multihash
            
            network_job = ClientNetworking.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            content_update_row = ( hashes, directory_multihash, note )
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
            
            HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            with self._lock:
                
                text = self._multihash_prefix + directory_multihash
                
            
            job_key.SetVariable( 'popup_clipboard', ( 'copy multihash to clipboard', text ) )
            
            job_key.Finish()
            
            return directory_multihash
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            job_key.SetVariable( 'popup_text_1', 'error' )
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            job_key.Cancel()
            
        
    
    def PinFile( self, hash, mime ):
        
        mime_string = HC.mime_string_lookup[ mime ]
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'add'
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        files = { 'path' : ( hash.encode( 'hex' ), open( path, 'rb' ), mime_string ) }
        
        network_job = ClientNetworking.NetworkJob( 'GET', url )
        
        network_job.SetFiles( files )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        data = network_job.GetContent()
        
        j = json.loads( data )
        
        multihash = j[ 'Hash' ]
        
        ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
        
        file_info_manager = media_result.GetFileInfoManager()
        
        content_update_row = ( file_info_manager, multihash )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
        return multihash
        
    
    def UnpinDirectory( self, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'pin/rm/' + multihash
        
        network_job = ClientNetworking.NetworkJob( 'GET', url )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_DELETE, multihash ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
    
    def UnpinFile( self, hash, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'pin/rm/' + multihash
        
        try:
            
            network_job = ClientNetworking.NetworkJob( 'GET', url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.NetworkException as e:
            
            if 'not pinned' not in HydrusData.ToUnicode( e ):
                
                raise
                
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash } ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
    
