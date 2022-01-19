import hashlib
import json
import os
import random
import threading
import time
import traceback
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNATPunch
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientFiles
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import QtPorting as QP
from hydrus.client.importing import ClientImporting
from hydrus.client.metadata import ClientRatings
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

SHORT_DELAY_PERIOD = 50000
ACCOUNT_SYNC_PERIOD = 250000

def GenerateDefaultServiceDictionary( service_type ):
    
    dictionary = HydrusSerialisable.SerialisableDictionary()
    
    if service_type in HC.REMOTE_SERVICES:
        
        dictionary[ 'credentials' ] = HydrusNetwork.Credentials( 'hostname', 45871 )
        dictionary[ 'no_requests_reason' ] = ''
        dictionary[ 'no_requests_until' ] = 0
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            dictionary[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( HydrusNetwork.Account.GenerateUnknownAccount() )
            dictionary[ 'next_account_sync' ] = 0
            dictionary[ 'network_sync_paused' ] = False
            dictionary[ 'service_options' ] = HydrusSerialisable.SerialisableDictionary()
            
            if service_type in HC.REPOSITORIES:
                
                dictionary[ 'metadata' ] = HydrusNetwork.Metadata()
                dictionary[ 'do_a_full_metadata_resync' ] = False
                
                dictionary[ 'update_downloading_paused' ] = False
                dictionary[ 'update_processing_paused' ] = False
                
                content_types = tuple( HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service_type ] )
                
                dictionary[ 'update_processing_content_types_paused' ] = [ [ content_type, False ] for content_type in content_types ]
                
            
        
        if service_type == HC.IPFS:
            
            dictionary[ 'credentials' ] = HydrusNetwork.Credentials( '127.0.0.1', 5001 )
            dictionary[ 'multihash_prefix' ] = ''
            dictionary[ 'use_nocopy' ] = False
            dictionary[ 'nocopy_abs_path_translations' ] = {}
            
        
    
    if service_type in ( HC.LOCAL_BOORU, HC.CLIENT_API_SERVICE ):
        
        dictionary[ 'port' ] = None
        dictionary[ 'upnp_port' ] = None
        dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
        dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
        
        dictionary[ 'support_cors' ] = False
        dictionary[ 'log_requests' ] = False
        
        dictionary[ 'external_scheme_override' ] = None
        dictionary[ 'external_host_override' ] = None
        dictionary[ 'external_port_override' ] = None
        
        if service_type == HC.LOCAL_BOORU:
            
            allow_non_local_connections = True
            
        elif service_type == HC.CLIENT_API_SERVICE:
            
            allow_non_local_connections = False
            
        
        dictionary[ 'allow_non_local_connections' ] = allow_non_local_connections
        dictionary[ 'use_https' ] = False
        
    
    if service_type in HC.RATINGS_SERVICES:
        
        dictionary[ 'shape' ] = ClientRatings.CIRCLE
        dictionary[ 'colours' ] = []
        
        from hydrus.client.gui import ClientGUIRatings
        
        if service_type == HC.LOCAL_RATING_LIKE:
            
            dictionary[ 'colours' ] = list( ClientGUIRatings.default_like_colours.items() )
            
        elif service_type == HC.LOCAL_RATING_NUMERICAL:
            
            dictionary[ 'colours' ] = list( ClientGUIRatings.default_numerical_colours.items() )
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
        
    elif service_type == HC.CLIENT_API_SERVICE:
        
        cl = ServiceClientAPI
        
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
    
    def _CheckFunctional( self ):
        
        pass
        
    
    def _GetSerialisableDictionary( self ):
        
        return HydrusSerialisable.SerialisableDictionary()
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        default_dictionary = GenerateDefaultServiceDictionary( self._service_type )
        
        for ( key, value ) in default_dictionary.items():
            
            if key not in dictionary:
                
                dictionary[ key ] = value
                
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
        HG.client_controller.pub( 'service_updated', self )
        
    
    def CheckFunctional( self ) -> bool:
        
        with self._lock:
            
            self._CheckFunctional()
            
        
    
    def Duplicate( self ) -> 'Service':
        
        with self._lock:
            
            dictionary = self._GetSerialisableDictionary()
            
            duplicate = GenerateService( self._service_key, self._service_type, self._name, dictionary )
            
            return duplicate
            
        
    
    def GetSerialisableDictionary( self ) -> HydrusSerialisable.SerialisableDictionary:
        
        with self._lock:
            
            self._dirty = False
            
            return self._GetSerialisableDictionary()
            
        
    
    def GetName( self ) -> str:
        
        with self._lock:
            
            return self._name
            
        
    
    def GetServiceKey( self ) -> bytes:
        
        with self._lock:
            
            return self._service_key
            
        
    
    def GetServiceType( self ) -> int:
        
        with self._lock:
            
            return self._service_type
            
        
    
    def GetStatusInfo( self ) -> typing.Tuple[ bool, str ]:
        
        with self._lock:
            
            try:
                
                self._CheckFunctional()
                
                return ( True, 'service is functional' )
                
            except Exception as e:
                
                return ( False, str( e ) )
                
            
        
    
    def IsDirty( self ) -> bool:
        
        with self._lock:
            
            return self._dirty
            
        
    
    def IsFunctional( self ) -> bool:
        
        with self._lock:
            
            try:
                
                self._CheckFunctional()
                
                return True
                
            except:
                
                return False
                
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetName( self, name ):
        
        with self._lock:
            
            self._name = name
            
        
    
    def ToTuple( self ) -> tuple:
        
        dictionary = self._GetSerialisableDictionary()
        
        return ( self._service_key, self._service_type, self._name, dictionary )
        
    
class ServiceLocalServerService( Service ):
    
    def _CheckFunctional( self ):
        
        if not self._bandwidth_rules.CanStartRequest( self._bandwidth_tracker ):
            
            raise HydrusExceptions.BandwidthException( 'bandwidth exceeded' )
            
        
        Service._CheckFunctional( self )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'port' ] = self._port
        dictionary[ 'upnp_port' ] = self._upnp_port
        dictionary[ 'allow_non_local_connections' ] = self._allow_non_local_connections
        dictionary[ 'support_cors' ] = self._support_cors
        dictionary[ 'log_requests' ] = self._log_requests
        dictionary[ 'bandwidth_tracker' ] = self._bandwidth_tracker
        dictionary[ 'bandwidth_rules' ] = self._bandwidth_rules
        dictionary[ 'external_scheme_override' ] = self._external_scheme_override
        dictionary[ 'external_host_override' ] = self._external_host_override
        dictionary[ 'external_port_override' ] = self._external_port_override
        dictionary[ 'use_https' ] = self._use_https
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._port = dictionary[ 'port' ]
        self._upnp_port = dictionary[ 'upnp_port' ]
        self._allow_non_local_connections = dictionary[ 'allow_non_local_connections' ]
        self._support_cors = dictionary[ 'support_cors' ]
        self._log_requests = dictionary[ 'log_requests' ]
        self._bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
        self._bandwidth_rules = dictionary[ 'bandwidth_rules' ]
        self._external_scheme_override = dictionary[ 'external_scheme_override' ]
        self._external_host_override = dictionary[ 'external_host_override' ]
        self._external_port_override = dictionary[ 'external_port_override' ]
        self._use_https = dictionary[ 'use_https' ]
        
        # this should support the same serverservice interface so we can just toss it at the regular serverengine and all the bandwidth will work ok
        
    
    def AllowsNonLocalConnections( self ):
        
        with self._lock:
            
            return self._allow_non_local_connections
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            return self._bandwidth_rules.CanStartRequest( self._bandwidth_tracker )
            
        
    
    def GetUPnPPort( self ):
        
        with self._lock:
            
            return self._upnp_port
            
        
    
    def GetPort( self ):
        
        with self._lock:
            
            return self._port
            
        
    
    def LogsRequests( self ):
        
        with self._lock:
            
            return self._log_requests
            
        
    
    def ReportDataUsed( self, num_bytes ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportDataUsed( num_bytes )
            
        
    
    def ReportRequestUsed( self ):
        
        with self._lock:
            
            self._bandwidth_tracker.ReportRequestUsed()
            
        
    
    def SupportsCORS( self ):
        
        with self._lock:
            
            return self._support_cors
            
        
    
    def UseHTTPS( self ):
        
        with self._lock:
            
            return self._use_https
            
        
    
class ServiceLocalBooru( ServiceLocalServerService ):
    
    def GetExternalShareURL( self, share_key ):
        
        if self._use_https:
            
            scheme = 'https'
            
        else:
            
            scheme = 'http'
            
        
        if self._external_scheme_override is not None:
            
            scheme = self._external_scheme_override
            
        
        if self._external_host_override is None:
            
            host = HydrusNATPunch.GetExternalIP()
            
        else:
            
            host = self._external_host_override
            
        
        if self._external_port_override is None:
            
            if self._upnp_port is None:
                
                port = ':{}'.format( self._port )
                
            else:
                
                port = ':{}'.format( self._upnp_port )
                
            
        else:
            
            port = self._external_port_override
            
            if port != '':
                
                port = ':{}'.format( port )
                
            
        
        url = '{}://{}{}/gallery?share_key={}'.format( scheme, host, port, share_key.hex() )
        
        return url
        
    
    def GetInternalShareURL( self, share_key ):
        
        internal_ip = '127.0.0.1'
        internal_port = self._port
        
        if self._use_https:
            
            scheme = 'https'
            
        else:
            
            scheme = 'http'
            
        
        url = '{}://{}:{}/gallery?share_key={}'.format( scheme, internal_ip, internal_port, share_key.hex() )
        
        return url
        
    
class ServiceClientAPI( ServiceLocalServerService ):
    
    pass
    
class ServiceLocalTag( Service ):
    
    pass
    
class ServiceLocalRating( Service ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'shape' ] = self._shape
        dictionary[ 'colours' ] = list(self._colours.items())
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._shape = dictionary[ 'shape' ]
        self._colours = dict( dictionary[ 'colours' ] )
        
    
    def ConvertRatingToString( self, rating: typing.Optional[ float ] ):
        
        raise NotImplementedError()
        
    
    def GetColour( self, rating_state ):
        
        with self._lock:
            
            return self._colours[ rating_state ]
            
        
    
    def GetShape( self ):
        
        with self._lock:
            
            return self._shape
            
        
    
class ServiceLocalRatingLike( ServiceLocalRating ):
    
    def ConvertRatingToString( self, rating: typing.Optional[ float ] ):
        
        if rating is None:
            
            return 'not set'
            
        elif isinstance( rating, ( float, int ) ):
            
            if rating < 0.5:
                
                return 'dislike'
                
            elif rating >= 0.5:
                
                return 'like'
                
            
        
        return 'unknown'
        
    
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
            
        
    
    def ConvertRatingToStars( self, rating: float ) -> int:
        
        if self._allow_zero:
            
            stars = int( round( rating * self._num_stars ) )
            
        else:
            
            stars = int( round( rating * ( self._num_stars - 1 ) ) ) + 1
            
        
        return stars
        
    
    def ConvertRatingToString( self, rating: typing.Optional[ float ] ):
        
        if rating is None:
            
            return 'not set'
            
        elif isinstance( rating, float ):
            
            rating_value = self.ConvertRatingToStars( rating )
            rating_range = self._num_stars
            
            return HydrusData.ConvertValueRangeToPrettyString( rating_value, rating_range )
            
        
        return 'unknown'
        
    
    def ConvertStarsToRating( self, stars: int ) -> float:
        
        if self._allow_zero:
            
            rating = stars / self._num_stars
            
        else:
            
            rating = ( stars - 1 ) / ( self._num_stars - 1 )
            
        
        return rating
        
    
    def GetNumStars( self ):
        
        with self._lock:
            
            return self._num_stars
            
        
    
    def GetOneStarValue( self ):
        
        num_choices = self._num_stars
        
        if self._allow_zero:
            
            num_choices += 1
            
        
        one_star_value = 1.0 / ( num_choices - 1 )
        
        return one_star_value
        
    
class ServiceRemote( Service ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        Service.__init__( self, service_key, service_type, name, dictionary = dictionary )
        
        self.network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        
    
    def _DelayFutureRequests( self, reason, duration = None ):
        
        if reason == '':
            
            reason = 'unknown error'
            
        
        if duration is None:
            
            duration = self._GetErrorWaitPeriod()
            
        
        next_no_requests_until = HydrusData.GetNow() + duration
        
        if next_no_requests_until > self._no_requests_until:
            
            self._no_requests_reason = reason
            self._no_requests_until = HydrusData.GetNow() + duration
            
        
        self._SetDirty()
        
    
    def _GetBaseURL( self ):
        
        full_host = self._credentials.GetPortedAddress()
        
        base_url = 'https://{}/'.format( full_host )
        
        return base_url
        
    
    def _GetErrorWaitPeriod( self ):
        
        return 3600 * 4
        
    
    def _CheckFunctional( self, including_external_communication = True, including_bandwidth = True ):
        
        if including_external_communication:
            
            self._CheckCanCommunicateExternally( including_bandwidth = including_bandwidth )
            
        
        Service._CheckFunctional( self )
        
    
    def _CheckCanCommunicateExternally( self, including_bandwidth = True ):
        
        if not HydrusData.TimeHasPassed( self._no_requests_until ):
            
            raise HydrusExceptions.InsufficientCredentialsException( self._no_requests_reason + ' - next request ' + ClientData.TimestampToPrettyTimeDelta( self._no_requests_until ) )
            
        
        if including_bandwidth:
            
            example_nj = ClientNetworkingJobs.NetworkJobHydrus( self._service_key, 'GET', self._GetBaseURL() )
            
            can_start = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), threshold = 60 )
            
            if not can_start:
                
                raise HydrusExceptions.BandwidthException( 'bandwidth exceeded' )
                
            
        
    
    def _CredentialsAreChanging( self ):
        
        pass
        
    
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
            
        
    
    def SetCredentials( self, credentials: HydrusNetwork.Credentials ):
        
        with self._lock:
            
            if credentials.DumpToString() != self._credentials.DumpToString():
                
                self._CredentialsAreChanging()
                
            
            self._credentials = credentials
            
            self._SetDirty()
            
        
    
class ServiceRestricted( ServiceRemote ):
    
    def _DealWithAccountError( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        HG.client_controller.pub( 'notify_account_sync_due' )
        
        self._next_account_sync = HydrusData.GetNow()
        
        HG.client_controller.network_engine.session_manager.ClearSession( self.network_context )
        
        self._SetDirty()
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
    
    def _DealWithFundamentalNetworkError( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        self._next_account_sync = HydrusData.GetNow() + ACCOUNT_SYNC_PERIOD
        
        self._SetDirty()
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
    
    def _GetErrorWaitPeriod( self ):
        
        if self._account.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ):
            
            return 900
            
        else:
            
            return SHORT_DELAY_PERIOD
            
        
    
    def _CanSyncAccount( self, including_external_communication = True ):
        
        try:
            
            self._CheckFunctional( including_external_communication = including_external_communication, including_account = False )
            
            return True
            
        except:
            
            return False
            
        
    
    def _CheckFunctional( self, including_external_communication = True, including_bandwidth = True, including_account = True ):
        
        if self._network_sync_paused:
            
            raise HydrusExceptions.ConflictException( 'Repository is paused!' )
            
        
        if including_account:
            
            self._account.CheckFunctional()
            
        
        ServiceRemote._CheckFunctional( self, including_external_communication = including_external_communication, including_bandwidth = including_bandwidth )
        
    
    def _CheckCanCommunicateExternally( self, including_bandwidth = True ):
        
        if not self._credentials.HasAccessKey():
            
            raise HydrusExceptions.MissingCredentialsException( 'this service has no access key set' )
            
        
        ServiceRemote._CheckCanCommunicateExternally( self, including_bandwidth = including_bandwidth )
        
    
    def _CredentialsAreChanging( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        self._next_account_sync = HydrusData.GetNow()
        
        self._SetDirty()
        
        HG.client_controller.pub( 'notify_account_sync_due' )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( self._account )
        dictionary[ 'next_account_sync' ] = self._next_account_sync
        dictionary[ 'network_sync_paused' ] = self._network_sync_paused
        dictionary[ 'service_options' ] = self._service_options
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRemote._LoadFromDictionary( self, dictionary )
        
        self._account = HydrusNetwork.Account.GenerateAccountFromSerialisableTuple( dictionary[ 'account' ] )
        self._next_account_sync = dictionary[ 'next_account_sync' ]
        
        if 'network_sync_paused' not in dictionary:
            
            network_sync_paused = False
            
            if 'paused' in dictionary:
                
                network_sync_paused = dictionary[ 'paused' ]
                
            
            dictionary[ 'network_sync_paused' ] = network_sync_paused
            
        
        self._network_sync_paused = dictionary[ 'network_sync_paused' ]
        
        if 'service_options' not in dictionary:
            
            dictionary[ 'service_options' ] = HydrusSerialisable.SerialisableDictionary()
            
        
        self._service_options = dictionary[ 'service_options' ]
        
    
    def _SetNewServiceOptions( self, service_options ):
        
        self._service_options = service_options
        
    
    def CanSyncAccount( self, including_external_communication = True ):
        
        with self._lock:
            
            return self._CanSyncAccount( including_external_communication = including_external_communication )
            
        
    
    def CheckFunctional( self, including_external_communication = True, including_bandwidth = True, including_account = True ):
        
        with self._lock:
            
            self._CheckFunctional( including_external_communication = including_external_communication, including_bandwidth = including_bandwidth, including_account = including_account )
            
        
    
    def GetAccount( self ):
        
        with self._lock:
            
            return self._account
            
        
    
    def GetNextAccountSyncStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_account_sync ):
            
            s = 'imminently'
            
        else:
            
            s = ClientData.TimestampToPrettyTimeDelta( self._next_account_sync )
            
        
        return 'next account sync ' + s
        
    
    def GetStatusInfo( self ) -> typing.Tuple[ bool, str ]:
        
        with self._lock:
            
            try:
                
                self._CheckFunctional( including_account = False )
                
                return ( True, 'service is functional' )
                
            except Exception as e:
                
                return ( False, str( e ) )
                
            
        
    
    def HasPermission( self, content_type, action ):
        
        with self._lock:
            
            return self._account.HasPermission( content_type, action )
            
        
    
    def IsDirty( self ):
        
        if ServiceRemote.IsDirty( self ):
            
            return True
            
        
        with self._lock:
            
            return self._account.IsDirty()
            
        
    
    def IsFunctional( self, including_external_communication = True, including_bandwidth = True, including_account = True ):
        
        with self._lock:
            
            try:
                
                self._CheckFunctional( including_external_communication = including_external_communication, including_bandwidth = including_bandwidth, including_account = including_account )
                
                return True
                
            except:
                
                return False
                
            
        
    
    def IsPausedNetworkSync( self ):
        
        with self._lock:
            
            return self._network_sync_paused
            
        
    
    def PausePlayNetworkSync( self ):
        
        with self._lock:
            
            self._network_sync_paused = not self._network_sync_paused
            
            self._SetDirty()
            
            paused = self._network_sync_paused
            
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            HG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            if method == HC.GET:
                
                query = HydrusNetworkVariableHandling.DumpToGETQuery( request_args )
                
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
                    
                    body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( request_args )
                    
                
            
            if query != '':
                
                command_and_query = command + '?' + query
                
            else:
                
                command_and_query = command
                
            
            url = self.GetBaseURL() + command_and_query
            
            if method == HC.GET:
                
                method = 'GET'
                
            elif method == HC.POST:
                
                method = 'POST'
                
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( self._service_key, method, url, body = body, temp_path = temp_path )
            
            if command not in ( 'update', 'metadata', 'file', 'thumbnail' ):
                
                network_job.OverrideBandwidth()
                network_job.OnlyTryConnectionOnce()
                
            
            if command in ( '', 'access_key', 'access_key_verification' ):
                
                # don't try to establish a session key for these requests
                network_job.SetForLogin( True )
                
                if command == 'access_key_verification':
                    
                    network_job.AddAdditionalHeader( 'Hydrus-Key', self._credentials.GetAccessKey().hex() )
                    
                
            
            if content_type is not None:
                
                network_job.AddAdditionalHeader( 'Content-Type', HC.mime_mimetype_string_lookup[ content_type ] )
                
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            network_bytes = network_job.GetContentBytes()
            
            content_type = network_job.GetContentType()
            
            if content_type is not None and content_type.startswith( 'application/json' ):
                
                parsed_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
                
                if command == 'account' and 'account' in parsed_args:
                    
                    data_used = network_job.GetTotalDataUsed()
                    
                    account = parsed_args[ 'account' ]
                    
                    # because the account was one behind when it was serialised! mostly do this just to sync up nicely with the service bandwidth tracker
                    account.ReportDataUsed( data_used )
                    account.ReportRequestUsed()
                    
                
                response = parsed_args
                
            else:
                
                response = network_bytes
                
            
            return response
            
        except Exception as e:
            
            with self._lock:
                
                if isinstance( e, HydrusExceptions.ServerBusyException ):
                    
                    self._DelayFutureRequests( 'server was busy', 5 * 60 )
                    
                elif isinstance( e, HydrusExceptions.SessionException ):
                    
                    HG.client_controller.network_engine.session_manager.ClearSession( self.network_context )
                    
                elif isinstance( e, ( HydrusExceptions.MissingCredentialsException, HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ConflictException ) ):
                    
                    self._DealWithAccountError()
                    
                elif isinstance( e, HydrusExceptions.NetworkVersionException ):
                    
                    self._DealWithFundamentalNetworkError()
                    
                elif isinstance( e, HydrusExceptions.NotFoundException ):
                    
                    self._DelayFutureRequests( 'got an unexpected 404', SHORT_DELAY_PERIOD )
                    
                elif isinstance( e, HydrusExceptions.BandwidthException ):
                    
                    self._DelayFutureRequests( 'service has exceeded bandwidth', ACCOUNT_SYNC_PERIOD )
                    
                else:
                    
                    self._DelayFutureRequests( str( e ) )
                    
                
            
            raise
            
        
    
    def SetAccountRefreshDueNow( self ):
        
        with self._lock:
            
            self._next_account_sync = HydrusData.GetNow() - 1
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'notify_account_sync_due' )
        
    
    def SetClean( self ):
        
        ServiceRemote.SetClean( self )
        
        self._account.SetClean()
        
    
    def SyncAccount( self, force = False ):
        
        with self._lock:
            
            ( original_message, original_message_created ) = self._account.GetMessageAndTimestamp()
            
            name = self._name
            
            if force:
                
                do_it = True
                
                self._no_requests_until = 0
                
                self._account = HydrusNetwork.Account.GenerateUnknownAccount()
                
            else:
                
                if not self._CanSyncAccount():
                    
                    do_it = False
                    
                    self._next_account_sync = HydrusData.GetNow() + SHORT_DELAY_PERIOD
                    
                    self._SetDirty()
                    
                else:
                    
                    do_it = HydrusData.TimeHasPassed( self._next_account_sync )
                    
                
            
        
        if do_it:
            
            try:
                
                account_response = self.Request( HC.GET, 'account' )
                
                with self._lock:
                    
                    self._account = account_response[ 'account' ]
                    
                    ( message, message_created ) = self._account.GetMessageAndTimestamp()
                    
                    if message != '' and message_created != original_message_created and not HydrusData.TimeHasPassed( message_created + ( 86400 * 5 ) ):
                        
                        m = 'New message for your account on {}:'.format( self._name )
                        m += os.linesep * 2
                        m += message
                        
                        HydrusData.ShowText( m )
                        
                    
                    if force:
                        
                        self._no_requests_until = 0
                        
                    
                
                try:
                    
                    options_response = self.Request( HC.GET, 'options' )
                    
                    with self._lock:
                        
                        service_options = options_response[ 'service_options' ]
                        
                        self._SetNewServiceOptions( service_options )
                        
                    
                except HydrusExceptions.SerialisationException:
                    
                    pass
                    
                
            except ( HydrusExceptions.CancelledException, HydrusExceptions.NetworkException ) as e:
                
                HydrusData.Print( 'Failed to refresh account for {}:'.format( name ) )
                
                HydrusData.Print( e )
                
                if force:
                    
                    raise
                    
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except Exception:
                
                HydrusData.Print( 'Failed to refresh account for {}:'.format( name ) )
                
                HydrusData.Print( traceback.format_exc() )
                
                if force:
                    
                    raise
                    
                
            finally:
                
                with self._lock:
                    
                    self._next_account_sync = HydrusData.GetNow() + ACCOUNT_SYNC_PERIOD
                    
                    self._SetDirty()
                    
                
                HG.client_controller.pub( 'notify_new_permissions' )
                HG.client_controller.pub( 'important_dirt_to_clean' )
                
            
        
    
class ServiceRepository( ServiceRestricted ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        ServiceRestricted.__init__( self, service_key, service_type, name, dictionary = dictionary )
        
        self._sync_remote_lock = threading.Lock()
        self._sync_processing_lock = threading.Lock()
        
        self._is_mostly_caught_up = None
        
    
    def _CanSyncDownload( self ):
        
        try:
            
            self._CheckFunctional()
            
            return not self._update_downloading_paused
            
        except:
            
            return False
            
        
    
    def _CanSyncProcess( self ):
        
        return not ( self._update_processing_paused or HC.options[ 'pause_repo_sync' ] )
        
    
    def _CheckFunctional( self, including_external_communication = True, including_bandwidth = True, including_account = True ):
        
        if HG.client_controller.options[ 'pause_repo_sync' ]:
            
            raise HydrusExceptions.ConflictException( 'All repositories are paused!' )
            
        
        ServiceRestricted._CheckFunctional( self, including_external_communication = including_external_communication, including_bandwidth = including_bandwidth, including_account = including_account )
        
    
    def _DealWithFundamentalNetworkError( self ):
        
        self._update_downloading_paused = True
        self._do_a_full_metadata_resync = True
        
        ServiceRestricted._DealWithFundamentalNetworkError( self )
        
    
    def _GetContentTypesWeAreProcessing( self ):
        
        content_types = { content_type for ( content_type, paused ) in self._update_processing_content_types_paused.items() if not paused }
        content_types.add( HC.CONTENT_TYPE_DEFINITIONS )
        
        return content_types
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRestricted._GetSerialisableDictionary( self )
        
        dictionary[ 'metadata' ] = self._metadata
        dictionary[ 'do_a_full_metadata_resync' ] = self._do_a_full_metadata_resync
        dictionary[ 'update_downloading_paused' ] = self._update_downloading_paused
        dictionary[ 'update_processing_paused' ] = self._update_processing_paused
        dictionary[ 'update_processing_content_types_paused' ] = list( self._update_processing_content_types_paused.items() )
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRestricted._LoadFromDictionary( self, dictionary )
        
        self._metadata = dictionary[ 'metadata' ]
        
        if 'do_a_full_metadata_resync' not in dictionary:
            
            dictionary[ 'do_a_full_metadata_resync' ] = False
            
        
        self._do_a_full_metadata_resync = dictionary[ 'do_a_full_metadata_resync' ]
        
        if 'paused' in dictionary:
            
            paused = dictionary[ 'paused' ]
            
            del dictionary[ 'paused' ]
            
            dictionary[ 'update_downloading_paused' ] = paused
            dictionary[ 'update_processing_paused' ] = paused
            
        
        if 'update_downloading_paused' not in dictionary:
            
            dictionary[ 'update_downloading_paused' ] = False
            
        
        if 'update_processing_paused' not in dictionary:
            
            dictionary[ 'update_processing_paused' ] = False
            
        
        self._update_downloading_paused = dictionary[ 'update_downloading_paused' ]
        self._update_processing_paused = dictionary[ 'update_processing_paused' ]
        
        if 'update_processing_content_types_paused' not in dictionary:
            
            content_types = tuple( HC.SERVICE_TYPES_TO_CONTENT_TYPES[ self._service_type ] )
            
            dictionary[ 'update_processing_content_types_paused' ] = [ [ content_type, False ] for content_type in content_types ]
            
        
        self._update_processing_content_types_paused = dict( dictionary[ 'update_processing_content_types_paused' ] )
        
    
    def _LogFinalRowSpeed( self, precise_timestamp, total_rows, row_name ):
        
        if total_rows == 0:
            
            return
            
        
        it_took = HydrusData.GetNowPrecise() - precise_timestamp
        
        rows_s = HydrusData.ToHumanInt( int( total_rows / it_took ) )
        
        summary = '{} processed {} {} at {} rows/s'.format( self._name, HydrusData.ToHumanInt( total_rows ), row_name, rows_s )
        
        HydrusData.Print( summary )
        
    
    def _ReportOngoingRowSpeed( self, job_key, rows_done, total_rows, precise_timestamp, rows_done_in_last_packet, row_name ):
        
        it_took = HydrusData.GetNowPrecise() - precise_timestamp
        
        rows_s = HydrusData.ToHumanInt( int( rows_done_in_last_packet / it_took ) )
        
        popup_message = '{} {}: processing at {} rows/s'.format( row_name, HydrusData.ConvertValueRangeToPrettyString( rows_done, total_rows ), rows_s )
        
        HG.client_controller.frame_splash_status.SetText( popup_message, print_to_log = False )
        job_key.SetVariable( 'popup_text_2', popup_message )
        
    
    def _SetNewServiceOptions( self, service_options ):
        
        if 'update_period' in service_options and 'update_period' in self._service_options and service_options[ 'update_period' ] != self._service_options[ 'update_period' ]:
            
            update_period = service_options[ 'update_period' ]
            
            self._metadata.CalculateNewNextUpdateDue( update_period )
            
        
        ServiceRestricted._SetNewServiceOptions( self, service_options )
        
    
    def _SyncDownloadMetadata( self ):
        
        with self._lock:
            
            if not self._CanSyncDownload():
                
                return
                
            
            do_a_full_metadata_resync = self._do_a_full_metadata_resync
            
            if self._do_a_full_metadata_resync:
                
                do_it = True
                
                next_update_index = 0
                
            else:
                
                do_it = self._metadata.UpdateDue( from_client = True )
                
                next_update_index = self._metadata.GetNextUpdateIndex()
                
            
            service_key = self._service_key
            
            name = self._name
            
        
        if do_it:
            
            try:
                
                response = self.Request( HC.GET, 'metadata', { 'since' : next_update_index } )
                
                metadata_slice = response[ 'metadata_slice' ]
                
            except HydrusExceptions.CancelledException as e:
                
                self._DelayFutureRequests( str( e ) )
                
                return
                
            except HydrusExceptions.NetworkException as e:
                
                HydrusData.Print( 'Attempting to download metadata for ' + name + ' resulted in a network error:' )
                
                HydrusData.Print( e )
                
                return
                
            
            if do_a_full_metadata_resync:
                
                HG.client_controller.WriteSynchronous( 'set_repository_update_hashes', service_key, metadata_slice )
                
            else:
                
                HG.client_controller.WriteSynchronous( 'associate_repository_update_hashes', service_key, metadata_slice )
                
            
            with self._lock:
                
                if self._do_a_full_metadata_resync:
                    
                    self._metadata = HydrusNetwork.Metadata()
                    
                    self._do_a_full_metadata_resync = False
                    
                
                self._metadata.UpdateFromSlice( metadata_slice )
                
                self._is_mostly_caught_up = None
                
                self._SetDirty()
                
            
        
    
    def _SyncDownloadUpdates( self, stop_time ):
        
        with self._lock:
            
            if not self._CanSyncDownload():
                
                return
                
            
            name = self._name
            service_key = self._service_key
            
        
        update_hashes = HG.client_controller.Read( 'missing_repository_update_hashes', service_key )
        
        if len( update_hashes ) > 0:
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_key.SetStatusTitle( name + ' sync: downloading updates' )
                
                HG.client_controller.pub( 'message', job_key )
                
                for ( i, update_hash ) in enumerate( update_hashes ):
                    
                    status = 'update ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( update_hashes ) )
                    
                    HG.client_controller.frame_splash_status.SetText( status, print_to_log = False )
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( update_hashes ) ) )
                    
                    with self._lock:
                        
                        if not self._CanSyncDownload():
                            
                            return
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', 3 * 60 )
                            
                        
                        return
                        
                    
                    try:
                        
                        update_network_string = self.Request( HC.GET, 'update', { 'update_hash' : update_hash } )
                        
                    except HydrusExceptions.CancelledException as e:
                        
                        self._DelayFutureRequests( str( e ) )
                        
                        return
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        self._DelayFutureRequests( str( e ) )
                        
                        HydrusData.Print( 'Attempting to download an update for ' + name + ' resulted in a network error:' )
                        
                        HydrusData.Print( e )
                        
                        return
                        
                    
                    update_network_string_hash = hashlib.sha256( update_network_string ).digest()
                    
                    if update_network_string_hash != update_hash:
                        
                        # this is the weird update problem, seems to be network related
                        # throwing a whole hullabaloo about it only caused problems, as the real fix was 'unpause it, try again'
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'had an unusual update response' )
                            
                        
                        return
                        
                    
                    try:
                        
                        update = HydrusSerialisable.CreateFromNetworkBytes( update_network_string )
                        
                    except Exception as e:
                        
                        with self._lock:
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'Update ' + update_hash.hex() + ' downloaded from the ' + self._name + ' repository failed to load! This is a serious error!'
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
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'Update ' + update_hash.hex() + ' downloaded from the ' + self._name + ' was not a valid update--it was a ' + repr( update ) + '! This is a serious error!'
                        message += os.linesep * 2
                        message += 'The repository has been paused for now. Please look into what could be wrong and report this to the hydrus dev.'
                        
                        HydrusData.ShowText( message )
                        
                        return
                        
                    
                    try:
                        
                        HG.client_controller.WriteSynchronous( 'import_update', update_network_string, update_hash, mime )
                        
                    except Exception as e:
                        
                        with self._lock:
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'While downloading updates for the ' + self._name + ' repository, one failed to import! The error follows:'
                        
                        HydrusData.ShowText( message )
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    
                
                job_key.SetVariable( 'popup_text_1', 'finished' )
                job_key.DeleteVariable( 'popup_gauge_1' )
                
            finally:
                
                job_key.Finish()
                job_key.Delete( 5 )
                
            
        
    
    def _SyncProcessUpdates( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        with self._lock:
            
            if not self._CanSyncProcess():
                
                return
                
            
        
        if HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        work_done = False
        
        try:
            
            job_key = ClientThreading.JobKey( cancellable = True, maintenance_mode = maintenance_mode, stop_time = stop_time )
            
            title = '{} sync: processing updates'.format( self._name )
            
            job_key.SetStatusTitle( title )
            
            content_types_to_process = self._GetContentTypesWeAreProcessing()
            
            ( this_is_first_definitions_work, definition_hashes_and_content_types, this_is_first_content_work, content_hashes_and_content_types ) = HG.client_controller.Read( 'repository_update_hashes_to_process', self._service_key, content_types_to_process )
            
            if len( definition_hashes_and_content_types ) == 0 and len( content_hashes_and_content_types ) == 0:
                
                return # no work to do
                
            
            if len( content_hashes_and_content_types ) > 0:
                
                content_hashes_and_content_types = self._metadata.SortContentHashesAndContentTypes( content_hashes_and_content_types )
                
            
            HydrusData.Print( title )
            
            num_updates_done = 0
            num_updates_to_do = len( definition_hashes_and_content_types ) + len( content_hashes_and_content_types )
            
            HG.client_controller.pub( 'message', job_key )
            HG.client_controller.frame_splash_status.SetTitleText( title, print_to_log = False )
            
            total_definition_rows_completed = 0
            total_content_rows_completed = 0
            
            did_definition_analyze = False
            did_content_analyze = False
            
            definition_start_time = HydrusData.GetNowPrecise()
            
            try:
                
                for ( definition_hash, content_types ) in definition_hashes_and_content_types:
                    
                    progress_string = HydrusData.ConvertValueRangeToPrettyString( num_updates_done + 1, num_updates_to_do )
                    
                    splash_title = '{} sync: processing updates {}'.format( self._name, progress_string )
                    
                    HG.client_controller.frame_splash_status.SetTitleText( splash_title, clear_undertexts = False, print_to_log = False )
                    
                    status = 'processing {}'.format( progress_string )
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( num_updates_done, num_updates_to_do ) )
                    
                    try:
                        
                        update_path = HG.client_controller.client_files_manager.GetFilePath( definition_hash, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) was missing. Your repository should be paused, and all update files have been scheduled for a presence check. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    with open( update_path, 'rb' ) as f:
                        
                        update_network_bytes = f.read()
                        
                    
                    try:
                        
                        definition_update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
                        
                    except:
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) was invalid. Your repository should be paused, and all update files have been scheduled for an integrity check. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    if not isinstance( definition_update, HydrusNetwork.DefinitionsUpdate ):
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) has incorrect metadata. Your repository should be paused, and all update files have been scheduled for a metadata rescan. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    rows_in_this_update = definition_update.GetNumRows()
                    rows_done_in_this_update = 0
                    
                    iterator_dict = {}
                    
                    iterator_dict[ 'service_hash_ids_to_hashes' ] = iter( definition_update.GetHashIdsToHashes().items() )
                    iterator_dict[ 'service_tag_ids_to_tags' ] = iter( definition_update.GetTagIdsToTags().items() )
                    
                    while len( iterator_dict ) > 0:
                        
                        this_work_start_time = HydrusData.GetNowPrecise()
                        
                        if HG.client_controller.CurrentlyVeryIdle():
                            
                            work_time = 30
                            break_percentage = 0.03
                            
                        elif HG.client_controller.CurrentlyIdle():
                            
                            work_time = 10
                            break_percentage = 0.05
                            
                        else:
                            
                            work_time = 0.5
                            break_percentage = 0.1
                            
                        
                        start_time = HydrusData.GetNowPrecise()
                        
                        num_rows_done = HG.client_controller.WriteSynchronous( 'process_repository_definitions', self._service_key, definition_hash, iterator_dict, content_types, job_key, work_time )
                        
                        time_it_took = HydrusData.GetNowPrecise() - start_time
                        
                        rows_done_in_this_update += num_rows_done
                        total_definition_rows_completed += num_rows_done
                        
                        work_done = True
                        
                        if this_is_first_definitions_work and total_definition_rows_completed > 1000 and not did_definition_analyze:
                            
                            HG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
                            
                            did_definition_analyze = True
                            
                        
                        if HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_key.IsCancelled():
                            
                            return
                            
                        
                        time.sleep( break_percentage * time_it_took )
                        
                        self._ReportOngoingRowSpeed( job_key, rows_done_in_this_update, rows_in_this_update, this_work_start_time, num_rows_done, 'definitions' )
                        
                    
                    num_updates_done += 1
                    
                
                if this_is_first_definitions_work and not did_definition_analyze:
                    
                    HG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
                    
                    did_definition_analyze = True
                    
                
            finally:
                
                self._LogFinalRowSpeed( definition_start_time, total_definition_rows_completed, 'definitions' )
                
            
            if HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_key.IsCancelled():
                
                return
                
            
            content_start_time = HydrusData.GetNowPrecise()
            
            try:
                
                for ( content_hash, content_types ) in content_hashes_and_content_types:
                    
                    progress_string = HydrusData.ConvertValueRangeToPrettyString( num_updates_done + 1, num_updates_to_do )
                    
                    splash_title = '{} sync: processing updates {}'.format( self._name, progress_string )
                    
                    HG.client_controller.frame_splash_status.SetTitleText( splash_title, clear_undertexts = False, print_to_log = False )
                    
                    status = 'processing {}'.format( progress_string )
                    
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( num_updates_done, num_updates_to_do ) )
                    
                    try:
                        
                        update_path = HG.client_controller.client_files_manager.GetFilePath( content_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) was missing. Your repository should be paused, and all update files have been scheduled for a presence check. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    with open( update_path, 'rb' ) as f:
                        
                        update_network_bytes = f.read()
                        
                    
                    try:
                        
                        content_update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
                        
                    except:
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) was invalid. Your repository should be paused, and all update files have been scheduled for an integrity check. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    if not isinstance( content_update, HydrusNetwork.ContentUpdate ):
                        
                        HG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) has incorrect metadata. Your repository should be paused, and all update files have been scheduled for a metadata rescan. Please permit file maintenance under _database->file maintenance->review_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    rows_in_this_update = content_update.GetNumRows( content_types )
                    rows_done_in_this_update = 0
                    
                    iterator_dict = {}
                    
                    if HC.CONTENT_TYPE_FILES in content_types:
                        
                        iterator_dict[ 'new_files' ] = iter( content_update.GetNewFiles() )
                        iterator_dict[ 'deleted_files' ] = iter( content_update.GetDeletedFiles() )
                        
                    
                    if HC.CONTENT_TYPE_MAPPINGS in content_types:
                        
                        iterator_dict[ 'new_mappings' ] = HydrusData.SmoothOutMappingIterator( content_update.GetNewMappings(), 50 )
                        iterator_dict[ 'deleted_mappings' ] = HydrusData.SmoothOutMappingIterator( content_update.GetDeletedMappings(), 50 )
                        
                    
                    if HC.CONTENT_TYPE_TAG_PARENTS in content_types:
                        
                        iterator_dict[ 'new_parents' ] = iter( content_update.GetNewTagParents() )
                        iterator_dict[ 'deleted_parents' ] = iter( content_update.GetDeletedTagParents() )
                        
                    
                    if HC.CONTENT_TYPE_TAG_SIBLINGS in content_types:
                        
                        iterator_dict[ 'new_siblings' ] = iter( content_update.GetNewTagSiblings() )
                        iterator_dict[ 'deleted_siblings' ] = iter( content_update.GetDeletedTagSiblings() )
                        
                    
                    while len( iterator_dict ) > 0:
                        
                        this_work_start_time = HydrusData.GetNowPrecise()
                        
                        if HG.client_controller.CurrentlyVeryIdle():
                            
                            work_time = 30
                            break_percentage = 0.03
                            
                        elif HG.client_controller.CurrentlyIdle():
                            
                            work_time = 10
                            break_percentage = 0.05
                            
                        else:
                            
                            work_time = 0.5
                            break_percentage = 0.1
                            
                        
                        start_time = HydrusData.GetNowPrecise()
                        
                        num_rows_done = HG.client_controller.WriteSynchronous( 'process_repository_content', self._service_key, content_hash, iterator_dict, content_types, job_key, work_time )
                        
                        time_it_took = HydrusData.GetNowPrecise() - start_time
                        
                        rows_done_in_this_update += num_rows_done
                        total_content_rows_completed += num_rows_done
                        
                        work_done = True
                        
                        if this_is_first_content_work and total_content_rows_completed > 1000 and not did_content_analyze:
                            
                            HG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
                            
                            did_content_analyze = True
                            
                        
                        if HG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_key.IsCancelled():
                            
                            return
                            
                        
                        time.sleep( break_percentage * time_it_took )
                        
                        self._ReportOngoingRowSpeed( job_key, rows_done_in_this_update, rows_in_this_update, this_work_start_time, num_rows_done, 'content rows' )
                        
                    
                    num_updates_done += 1
                    
                
                if this_is_first_content_work and not did_content_analyze:
                    
                    HG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
                    
                    did_content_analyze = True
                    
                
            finally:
                
                self._LogFinalRowSpeed( content_start_time, total_content_rows_completed, 'content rows' )
                
            
        except HydrusExceptions.ShutdownException:
            
            return
            
        except Exception as e:
            
            message = 'Failed to process updates for the {} repository! The error follows:'.format( self._name )
            
            HydrusData.ShowText( message )
            
            HydrusData.ShowException( e )
            
            with self._lock:
                
                self._do_a_full_metadata_resync = True
                
                self._update_processing_paused = True
                
                self._SetDirty()
                
            
            HG.client_controller.pub( 'important_dirt_to_clean' )
            
            
        finally:
            
            if work_done:
                
                with self._lock:
                    
                    self._is_mostly_caught_up = None
                    
                    self._SetDirty()
                    
                
                HG.client_controller.pub( 'notify_new_force_refresh_tags_data' )
                HG.client_controller.pub( 'notify_new_tag_display_application' )
                
            
            job_key.DeleteVariable( 'popup_text_1' )
            job_key.DeleteVariable( 'popup_text_2' )
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            job_key.Finish()
            job_key.Delete( 3 )
            
        
    
    def CanDoIdleShutdownWork( self ):
        
        with self._lock:
            
            if not self._CanSyncProcess():
                
                return False
                
            
            service_key = self._service_key
            
        
        content_types_we_are_processing = self._GetContentTypesWeAreProcessing()
        
        ( num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates ) = HG.client_controller.Read( 'repository_progress', service_key )
        
        for ( content_type, num_processed_updates ) in content_types_to_num_processed_updates.items():
            
            if content_type not in content_types_we_are_processing:
                
                continue
                
            
            if num_processed_updates < content_types_to_num_updates[ content_type ]:
                
                return True
                
            
        
        return False
        
    
    def CanSyncDownload( self ):
        
        with self._lock:
            
            return self._CanSyncDownload()
            
        
    
    def CanSyncProcess( self ):
        
        with self._lock:
            
            return self._CanSyncProcess()
            
        
    
    def DoAFullMetadataResync( self ):
        
        with self._lock:
            
            self._next_account_sync = 1
            self._do_a_full_metadata_resync = True
            
            self._metadata.UpdateASAP()
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        HG.client_controller.pub( 'notify_new_permissions' )
        
    
    def GetMetadata( self ):
        
        with self._lock:
            
            return self._metadata
            
        
    
    def GetNextUpdateDueString( self ):
        
        with self._lock:
            
            return self._metadata.GetNextUpdateDueString( from_client = True )
            
        
    
    def GetNullificationPeriod( self ) -> int:
        
        with self._lock:
            
            if 'nullification_period' in self._service_options:
                
                nullification_period = self._service_options[ 'nullification_period' ]
                
                if not isinstance( nullification_period, int ):
                    
                    raise HydrusExceptions.DataMissing( 'This service has a bad anonymisation period! Try refreshing your account!' )
                    
                
                return nullification_period
                
            else:
                
                raise HydrusExceptions.DataMissing( 'This service does not seem to have an anonymisation period! Try refreshing your account!' )
                
            
        
    
    def GetUpdateHashes( self ):
        
        with self._lock:
            
            return self._metadata.GetUpdateHashes()
            
        
    
    def GetUpdatePeriod( self ) -> int:
        
        with self._lock:
            
            if 'update_period' in self._service_options:
                
                update_period = self._service_options[ 'update_period' ]
                
                if not isinstance( update_period, int ):
                    
                    raise HydrusExceptions.DataMissing( 'This service has a bad update period! Try refreshing your account!' )
                    
                
                return update_period
                
            else:
                
                raise HydrusExceptions.DataMissing( 'This service does not seem to have an update period! Try refreshing your account!' )
                
            
        
    
    def IsDueAFullMetadataResync( self ):
        
        with self._lock:
            
            return self._do_a_full_metadata_resync
            
        
    
    def IsMostlyCaughtUp( self ):
        
        # if a user is more than two weeks behind, let's assume they aren't 'caught up'
        CAUGHT_UP_BUFFER = 14 * 86400
        
        two_weeks_ago = HydrusData.GetNow() - CAUGHT_UP_BUFFER
        
        with self._lock:
            
            if self._is_mostly_caught_up is None:
                
                if not self._metadata.HasDoneInitialSync():
                    
                    self._is_mostly_caught_up = False
                    
                    return self._is_mostly_caught_up
                    
                else:
                    
                    next_begin = self._metadata.GetNextUpdateBegin()
                    
                    # haven't synced new metadata, so def not caught up
                    if next_begin < two_weeks_ago:
                        
                        self._is_mostly_caught_up = False
                        
                        return self._is_mostly_caught_up
                        
                    
                
            else:
                
                return self._is_mostly_caught_up
                
            
            service_key = self._service_key
            
        
        content_types_to_process = self._GetContentTypesWeAreProcessing()
        
        ( this_is_first_definitions_work, definition_hashes_and_content_types, this_is_first_content_work, content_hashes_and_content_types ) = HG.client_controller.Read( 'repository_update_hashes_to_process', self._service_key, content_types_to_process )
        
        missing_update_hashes = HG.client_controller.Read( 'missing_repository_update_hashes', service_key )
        
        unprocessed_update_hashes = set( ( hash for ( hash, content_types ) in definition_hashes_and_content_types ) ).union( ( hash for ( hash, content_types ) in content_hashes_and_content_types ) ).union( missing_update_hashes )
        
        with self._lock:
            
            if len( unprocessed_update_hashes ) == 0:
                
                self._is_mostly_caught_up = True # done them all, even if there aren't any yet to do
                
            else:
                
                earliest_unsorted_update_timestamp = self._metadata.GetEarliestTimestampForTheseHashes( unprocessed_update_hashes )
                
                self._is_mostly_caught_up = earliest_unsorted_update_timestamp > two_weeks_ago
                
            
            return self._is_mostly_caught_up
            
        
    
    def IsPausedUpdateDownloading( self ):
        
        with self._lock:
            
            return self._update_downloading_paused
            
        
    
    def IsPausedUpdateProcessing( self, content_type = None ):
        
        with self._lock:
            
            if content_type is None:
                
                return self._update_processing_paused
                
            else:
                
                return self._update_processing_content_types_paused[ content_type ]
                
            
        
    
    def PausePlayUpdateDownloading( self ):
        
        with self._lock:
            
            self._update_downloading_paused = not self._update_downloading_paused
            
            self._SetDirty()
            
            paused = self._update_downloading_paused
            
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            HG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def PausePlayUpdateProcessing( self, content_type = None ):
        
        with self._lock:
            
            if content_type is None:
                
                self._update_processing_paused = not self._update_processing_paused
                
            else:
                
                self._update_processing_content_types_paused[ content_type ] = not self._update_processing_content_types_paused[ content_type ]
                
            
            self._SetDirty()
            
            paused = self._update_processing_paused
            
            self._is_mostly_caught_up = None
            
        
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            HG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def Reset( self ):
        
        with self._lock:
            
            self._no_requests_reason = ''
            self._no_requests_until = 0
            
            self._account = HydrusNetwork.Account.GenerateUnknownAccount()
            
            self._next_account_sync = 0
            
            self._metadata = HydrusNetwork.Metadata()
            
            self._is_mostly_caught_up = None
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'notify_account_sync_due' )
        HG.client_controller.pub( 'important_dirt_to_clean' )
        
        HG.client_controller.Write( 'reset_repository', self )
        
    
    def SyncRemote( self, stop_time = None ):
        
        with self._sync_remote_lock:
            
            try:
                
                self._SyncDownloadMetadata()
                
                self._SyncDownloadUpdates( stop_time )
                
                if self._is_mostly_caught_up is not None and self._is_mostly_caught_up:
                    
                    self.SyncThumbnails( stop_time )
                    
                
            except HydrusExceptions.ShutdownException:
                
                pass
                
            except Exception as e:
                
                with self._lock:
                    
                    self._DelayFutureRequests( str( e ) )
                    
                
                HydrusData.ShowText( 'The service "{}" encountered an error while trying to sync! The error was "{}". It will not do any work for a little while. If the fix is not obvious, please elevate this to hydrus dev.'.format( self._name, str( e ) ) )
                
                HydrusData.ShowException( e )
                
            finally:
                
                if self.IsDirty():
                    
                    HG.client_controller.pub( 'important_dirt_to_clean' )
                    
                
            
        
    
    def SyncProcessUpdates( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        with self._sync_processing_lock:
            
            self._SyncProcessUpdates( maintenance_mode = maintenance_mode, stop_time = stop_time )
            
        
    
    def SyncThumbnails( self, stop_time ):
        
        with self._lock:
            
            if self._service_type != HC.FILE_REPOSITORY:
                
                return
                
            
            if not self._CanSyncDownload():
                
                return
                
            
            name = self._name
            service_key = self._service_key
            
        
        thumbnail_hashes = HG.client_controller.Read( 'missing_thumbnail_hashes', service_key )
        
        num_to_do = len( thumbnail_hashes )
        
        if num_to_do > 0:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_key.SetStatusTitle( name + ' sync: downloading thumbnails' )
                
                HG.client_controller.pub( 'message', job_key )
                
                for ( i, thumbnail_hash ) in enumerate( thumbnail_hashes ):
                    
                    status = 'thumbnail ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do )
                    
                    HG.client_controller.frame_splash_status.SetText( status, print_to_log = False )
                    job_key.SetVariable( 'popup_text_1', status )
                    job_key.SetVariable( 'popup_gauge_1', ( i + 1, num_to_do ) )
                    
                    with self._lock:
                        
                        if not self._CanSyncDownload():
                            
                            break
                            
                        
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', 3 * 60 )
                            
                        
                        return
                        
                    
                    try:
                        
                        thumbnail_bytes = self.Request( HC.GET, 'thumbnail', { 'hash' : thumbnail_hash } )
                        
                    except HydrusExceptions.CancelledException as e:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( str( e ) )
                            
                        
                        return
                        
                    except HydrusExceptions.NotFoundException:
                        
                        return
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        HydrusData.Print( 'Attempting to download a thumbnail for ' + name + ' resulted in a network error:' )
                        
                        HydrusData.Print( e )
                        
                        return
                        
                    
                    client_files_manager.AddThumbnailFromBytes( thumbnail_hash, thumbnail_bytes )
                    
                
                job_key.SetVariable( 'popup_text_1', 'finished' )
                job_key.DeleteVariable( 'popup_gauge_1' )
                
            finally:
                
                job_key.Finish()
                job_key.Delete( 5 )
                
            
        
    
class ServiceIPFS( ServiceRemote ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'multihash_prefix' ] = self._multihash_prefix
        dictionary[ 'use_nocopy' ] = self._use_nocopy
        dictionary[ 'nocopy_abs_path_translations' ] = self._nocopy_abs_path_translations
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRemote._LoadFromDictionary( self, dictionary )
        
        self._multihash_prefix = dictionary[ 'multihash_prefix' ]
        self._use_nocopy = dictionary[ 'use_nocopy' ]
        self._nocopy_abs_path_translations = dictionary[ 'nocopy_abs_path_translations' ]
        
    
    def _GetAPIBaseURL( self ):
        
        full_host = self._credentials.GetPortedAddress()
        
        api_base_url = 'http://{}/api/v0/'.format( full_host )
        
        return api_base_url
        
    
    def ConvertMultihashToURLTree( self, name, size, multihash, job_key: typing.Optional[ ClientThreading.JobKey ] = None ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        links_url = api_base_url + 'object/links/' + multihash
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( links_url )
        
        if job_key is not None:
            
            job_key.SetNetworkJob( network_job )
            
        
        try:
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        finally:
            
            if job_key is not None:
                
                job_key.DeleteNetworkJob()
                
                if job_key.IsCancelled():
                    
                    raise HydrusExceptions.CancelledException( 'Multihash parsing cancelled by user.' )
                    
                
            
        
        parsing_text = network_job.GetContentText()
        
        links_json = json.loads( parsing_text )
        
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
                
                children.append( self.ConvertMultihashToURLTree( subname, subsize, submultihash, job_key = job_key ) )
                
            
            if size is None:
                
                size = sum( ( subsize for ( type_gumpf, subname, subsize, submultihash ) in children ) )
                
            
            return ( 'directory', name, size, children )
            
        else:
            
            url = api_base_url + 'cat/' + multihash
            
            return ( 'file', name, size, url )
            
        
    
    def EnableNoCopy( self, value ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        arg_value = json.dumps( value ) # lower case true/false
        
        url = api_base_url + 'config?arg=Experimental.FilestoreEnabled&arg={}&bool=true'.format( arg_value )
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        parsing_text = network_job.GetContentText()
        
        j = json.loads( parsing_text )
        
        return j[ 'Value' ] == value
        
    
    def GetDaemonVersion( self ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'version'
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        parsing_text = network_job.GetContentText()
        
        j = json.loads( parsing_text )
        
        return j[ 'Version' ]
        
    
    def GetMultihashPrefix( self ):
        
        with self._lock:
            
            return self._multihash_prefix
            
        
    
    def GetNoCopyAvailable( self ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'config?arg=Experimental.FilestoreEnabled'
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.ServerException:
            
            # returns 500 and error if not yet set, wew
            
            parsing_text = network_job.GetContentText()
            
            if 'Experimental key has no attributes' in parsing_text:
                
                return False
                
            
        
        parsing_text = network_job.GetContentText()
        
        j = json.loads( parsing_text )
        
        return j[ 'Value' ]
        
    
    def ImportFile( self, multihash, silent = False ):
        
        def on_qt_select_tree( job_key, url_tree ):
            
            try:
                
                from hydrus.client.gui import ClientGUIDialogs
                
                tlw = HG.client_controller.GetMainTLW()
                
                with ClientGUIDialogs.DialogSelectFromURLTree( tlw, url_tree ) as dlg:
                    
                    urls_good = False
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        urls = dlg.GetURLs()
                        
                        if len( urls ) > 0:
                            
                            HG.client_controller.CallToThread( ClientImporting.THREADDownloadURLs, job_key, urls, multihash )
                            
                            urls_good = True
                            
                        
                    
                    if not urls_good:
                        
                        job_key.Delete()
                        
                    
                
            except:
                
                job_key.Delete()
                
                raise
                
            
        
        def off_qt():
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_text_1', 'Looking up multihash information' )
            
            if not silent:
                
                HG.client_controller.pub( 'message', job_key )
                
            
            try:
                
                try:
                    
                    url_tree = self.ConvertMultihashToURLTree( multihash, None, multihash, job_key = job_key )
                    
                except HydrusExceptions.NotFoundException:
                    
                    job_key.SetVariable( 'popup_text_1', 'Failed to find multihash information for "{}"!'.format( multihash ) )
                    
                    return
                    
                except HydrusExceptions.ServerException as e:
                    
                    job_key.SetVariable( 'popup_text_1', 'IPFS Error: "{}"!'.format( e ) )
                    
                    return
                    
                
                if url_tree[0] == 'file':
                    
                    url = url_tree[3]
                    
                    HG.client_controller.CallToThread( ClientImporting.THREADDownloadURL, job_key, url, multihash )
                    
                else:
                    
                    job_key.SetVariable( 'popup_text_1', 'Waiting for user selection' )
                    
                    QP.CallAfter( on_qt_select_tree, job_key, url_tree )
                    
                
            except:
                
                job_key.Delete()
                
                raise
                
            
        
        HG.client_controller.CallToThread( off_qt )
        
    
    def IsPinned( self, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        # check if it is pinned. if we try to unpin something not pinned, the daemon 500s
        
        url = api_base_url + 'pin/ls?arg={}'.format( multihash )
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
            parsing_text = network_job.GetContentText()
            
            j = json.loads( parsing_text )
            
            file_is_pinned = False
            
            if 'PinLsList' in j:
                
                file_is_pinned = 'Keys' in j[ 'PinLsList' ] and multihash in j[ 'PinLsList' ]['Keys']
                
            else:
                
                file_is_pinned = 'Keys' in j and multihash in j['Keys']
                
            
        except HydrusExceptions.ServerException:
            
            if 'not pinned' in network_job.GetContentText():
                
                return False
                
            
            raise
            
        
        return file_is_pinned
        
    
    def PinDirectory( self, hashes, note ):
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetStatusTitle( 'creating ipfs directory on ' + self._name )
        
        HG.client_controller.pub( 'message', job_key )
        
        try:
            
            file_info = []
            
            hashes = sorted( hashes )
            
            for ( i, hash ) in enumerate( hashes ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    job_key.SetVariable( 'popup_text_1', 'cancelled!' )
                    
                    return
                    
                
                job_key.SetVariable( 'popup_text_1', 'ensuring files are pinned: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( hashes ) ) )
                job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( hashes ) ) )
                
                media_result = HG.client_controller.Read( 'media_result', hash )
                
                mime = media_result.GetMime()
                
                result = HG.client_controller.Read( 'service_filenames', self._service_key, { hash } )
                
                if len( result ) == 0:
                    
                    try:
                        
                        multihash = self.PinFile( hash, mime )
                        
                    except HydrusExceptions.DataMissing:
                        
                        HydrusData.ShowText( 'File {} could not be pinned!'.format( hash.hex() ) )
                        
                        continue
                        
                    
                else:
                    
                    ( multihash, ) = result
                    
                
                file_info.append( ( hash, mime, multihash ) )
                
            
            with self._lock:
                
                api_base_url = self._GetAPIBaseURL()
                
            
            url = api_base_url + 'object/new?arg=unixfs-dir'
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            parsing_text = network_job.GetContentText()
            
            response_json = json.loads( parsing_text )
            
            for ( i, ( hash, mime, multihash ) ) in enumerate( file_info ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    job_key.SetVariable( 'popup_text_1', 'cancelled!' )
                    
                    return
                    
                
                job_key.SetVariable( 'popup_text_1', 'creating directory: ' + HydrusData.ConvertValueRangeToPrettyString( i + 1, len( file_info ) ) )
                job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( file_info ) ) )
                
                object_multihash = response_json[ 'Hash' ]
                
                filename = hash.hex() + HC.mime_ext_lookup[ mime ]
                
                url = api_base_url + 'object/patch/add-link?arg=' + object_multihash + '&arg=' + filename + '&arg=' + multihash
                
                network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                network_job.WaitUntilDone()
                
                parsing_text = network_job.GetContentText()
                
                response_json = json.loads( parsing_text )
                
            
            directory_multihash = response_json[ 'Hash' ]
            
            url = api_base_url + 'pin/add?arg=' + directory_multihash
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            content_update_row = ( hashes, directory_multihash, note )
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
            
            HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            
            with self._lock:
                
                text = self._multihash_prefix + directory_multihash
                
            
            job_key.SetVariable( 'popup_clipboard', ( 'copy multihash to clipboard', text ) )
            
            return directory_multihash
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            job_key.SetErrorException( e )
            
            job_key.Cancel()
            
        finally:
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            job_key.Finish()
            
        
    
    def PinFile( self, hash, mime ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        with open( path, 'rb' ) as f:
            
            if self._use_nocopy:
                
                url = api_base_url + 'add?nocopy=true'
                
                mime_string = 'application/octet-stream'
                
                ipfs_abspath = None
                
                for ( hydrus_portable_path, ipfs_translation ) in self._nocopy_abs_path_translations.items():
                    
                    hydrus_path = HydrusPaths.ConvertPortablePathToAbsPath( hydrus_portable_path )
                    
                    if path.startswith( hydrus_path ):
                        
                        if ipfs_translation == '':
                            
                            raise Exception( 'The path {} does not have an IPFS translation set! Please check your IPFS path mappings under manage services!'.format( hydrus_path ) )
                            
                        
                        ipfs_abspath = path.replace( hydrus_path, ipfs_translation )
                        
                        break
                        
                    
                
                if ipfs_abspath is None:
                    
                    raise Exception( 'Could not figure out an ipfs absolute path for {}! Have new paths been added due to a database migration? Please check your IPFS path mappings under manage services!'.format( path ) )
                    
                
                files = { 'path' : ( hash.hex(), f, mime_string, { 'Abspath' : ipfs_abspath } ) }
                
            else:
                
                url = api_base_url + 'add'
                
                mime_string = HC.mime_mimetype_string_lookup[ mime ]
                
                files = { 'path' : ( hash.hex(), f, mime_string ) }
                
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            network_job.SetFiles( files )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        
        parsing_text = network_job.GetContentText()
        
        j = json.loads( parsing_text )
        
        if 'Hash' not in j:
            
            message = 'IPFS was unable to pin--returned no hash!'
            
            HydrusData.Print( message )
            HydrusData.Print( parsing_text )
            
            raise HydrusExceptions.DataMissing( message )
            
        
        multihash = j[ 'Hash' ]
        
        EMPTY_IPFS_HASH = 'bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku'
        
        if multihash == EMPTY_IPFS_HASH:
            
            message = 'IPFS was unable to pin--returned empty multihash!'
            
            HydrusData.Print( message )
            HydrusData.Print( parsing_text )
            
            raise HydrusExceptions.DataMissing( message )
            
        
        media_result = HG.client_controller.Read( 'media_result', hash )
        
        file_info_manager = media_result.GetFileInfoManager()
        
        content_update_row = ( file_info_manager, multihash )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
        return multihash
        
    
    def UnpinDirectory( self, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        if self.IsPinned( multihash ):
            
            url = api_base_url + 'pin/rm/' + multihash
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_DELETE, multihash ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
    
    def UnpinFile( self, hash, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        if self.IsPinned( multihash ):
            
            url = api_base_url + 'pin/rm/' + multihash
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash } ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
        
    
class ServicesManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def _GetService( self, service_key: bytes ):
        
        try:
            
            return self._keys_to_services[ service_key ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'That service was not found!' )
            
        
    
    def _SetServices( self, services: typing.Collection[ Service ] ):
        
        self._keys_to_services = { service.GetServiceKey() : service for service in services }
        
        self._keys_to_services[ CC.TEST_SERVICE_KEY ] = GenerateService( CC.TEST_SERVICE_KEY, HC.TEST_SERVICE, 'test service' )
        
        key = lambda s: s.GetName()
        
        self._services_sorted = sorted( services, key = key )
        
    
    def Filter( self, service_keys: typing.Iterable[ bytes ], desired_types: typing.Iterable[ int ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services and self._keys_to_services[ service_key ].GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys: typing.Iterable[ bytes ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services ]
            
            return filtered_service_keys
            
        
    
    def GetDefaultLocationContext( self ) -> bytes:
        
        return ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
    
    def GetLocalMediaFileServices( self ):
        
        with self._lock:
            
            return [ service for service in self._services_sorted if service.GetServiceType() == HC.LOCAL_FILE_DOMAIN and service.GetServiceKey() != CC.LOCAL_UPDATE_SERVICE_KEY ]
            
        
    
    def GetName( self, service_key: bytes ):
        
        with self._lock:
            
            service = self._GetService( service_key )
            
            return service.GetName()
            
        
    
    def GetRemoteFileServiceKeys( self ):
        
        with self._lock:
            
            return { service_key for ( service_key, service ) in self._keys_to_services.items() if service.GetServiceType() in HC.REMOTE_FILE_SERVICES }
            
        
    
    def GetService( self, service_key: bytes ):
        
        with self._lock:
            
            return self._GetService( service_key )
            
        
    
    def GetServiceType( self, service_key: bytes ):
        
        with self._lock:
            
            return self._GetService( service_key ).GetServiceType()
            
        
    
    def GetServiceKeyFromName( self, allowed_types: typing.Collection[ int ], service_name: str ):
        
        with self._lock:
            
            for service in self._services_sorted:
                
                if service.GetServiceType() in allowed_types and service.GetName() == service_name:
                    
                    return service.GetServiceKey()
                    
                
            
            raise HydrusExceptions.DataMissing()
            
        
    
    def GetServiceKeys( self, desired_types: typing.Collection[ int ] = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for ( service_key, service ) in self._keys_to_services.items() if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types: typing.Collection[ int ] = HC.ALL_SERVICES, randomised: bool = False ):
        
        with self._lock:
            
            services = []
            
            for desired_type in desired_types:
                
                services.extend( [ service for service in self._services_sorted if service.GetServiceType() == desired_type ] )
                
            
            if randomised:
                
                random.shuffle( services )
                
            
            return services
            
        
    
    def RefreshServices( self ):
        
        with self._lock:
            
            services = self._controller.Read( 'services' )
            
            self._SetServices( services )
            
        
        self._controller.pub( 'notify_new_services' )
        
    
    def ServiceExists( self, service_key: bytes ):
        
        with self._lock:
            
            return service_key in self._keys_to_services
            
        
    
