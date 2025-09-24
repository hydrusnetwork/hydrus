import collections.abc
import hashlib
from io import BytesIO
import json
import random
import threading
import time
import traceback
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

SHORT_DELAY_PERIOD = 50000
ACCOUNT_SYNC_PERIOD = 250000

def ConvertNumericalRatingToPrettyString( lower, upper, rating, rounded_result = False, out_of = True ):
    
    rating_converted = ( rating * ( upper - lower ) ) + lower
    
    if rounded_result:
        
        rating_converted = round( rating_converted )
        
    
    s = '{:.2f}'.format( rating_converted )
    
    if out_of and lower in ( 0, 1 ):
        
        s += '/{:.2f}'.format( upper )
        
    
    return s
    

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
            
        
    
    if service_type == HC.CLIENT_API_SERVICE:
        
        dictionary[ 'port' ] = None
        dictionary[ 'upnp_port' ] = None
        dictionary[ 'bandwidth_tracker' ] = HydrusNetworking.BandwidthTracker()
        dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
        
        dictionary[ 'support_cors' ] = False
        dictionary[ 'log_requests' ] = False
        
        dictionary[ 'use_normie_eris' ] = False
        
        dictionary[ 'external_scheme_override' ] = None
        dictionary[ 'external_host_override' ] = None
        dictionary[ 'external_port_override' ] = None
        
        dictionary[ 'allow_non_local_connections' ] = False
        dictionary[ 'use_https' ] = False
        
    
    if service_type in HC.RATINGS_SERVICES:
        
        from hydrus.client.gui import ClientGUIRatings
        
        dictionary[ 'colours' ] = []
        dictionary[ 'show_in_thumbnail' ] = False
        dictionary[ 'show_in_thumbnail_even_when_null' ] = False
        
        if service_type in HC.STAR_RATINGS_SERVICES:
            
            dictionary[ 'shape' ] = ClientRatings.CIRCLE #change default to ClientRatings.HEART ?
            dictionary[ 'rating_svg' ] = None
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                dictionary[ 'colours' ] = list( ClientGUIRatings.default_like_colours.items() )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                dictionary[ 'colours' ] = list( ClientGUIRatings.default_numerical_colours.items() )
                dictionary[ 'num_stars' ] = 5
                dictionary[ 'allow_zero' ] = True
                dictionary[ 'custom_pad' ] = ClientGUIRatings.STAR_PAD.width()
                dictionary[ 'show_fraction_beside_stars' ] = ClientRatings.DRAW_NO
                
            
        
        if service_type == HC.LOCAL_RATING_INCDEC:
            
            dictionary[ 'colours' ] = list( ClientGUIRatings.default_incdec_colours.items() )
            
        
    
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
        
    elif service_type == HC.LOCAL_RATING_INCDEC:
        
        cl = ServiceLocalRatingIncDec
        
    elif service_type in HC.REPOSITORIES:
        
        cl = ServiceRepository
        
    elif service_type in HC.RESTRICTED_SERVICES:
        
        cl = ServiceRestricted
        
    elif service_type == HC.IPFS:
        
        cl = ServiceIPFS
        
    elif service_type in HC.REMOTE_SERVICES:
        
        cl = ServiceRemote
        
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
        
    
    def __hash__( self ):
        
        return self._service_key.__hash__()
        
    
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
        
        CG.client_controller.pub( 'service_updated', self )
        
    
    def CheckFunctional( self ):
        
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
            
        
    
    def GetStatusInfo( self ) -> tuple[ bool, str ]:
        
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
        dictionary[ 'use_normie_eris' ] = self._use_normie_eris
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
        self._use_normie_eris = dictionary[ 'use_normie_eris' ]
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
            
        
    
    def UseNormieEris( self ):
        
        with self._lock:
            
            return self._use_normie_eris
            
        
    

class ServiceClientAPI( ServiceLocalServerService ):
    
    pass
    

class ServiceLocalTag( Service ):
    
    pass
    

class ServiceLocalRating( Service ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = Service._GetSerialisableDictionary( self )
        
        dictionary[ 'colours' ] = list(self._colours.items())
        dictionary[ 'show_in_thumbnail' ] = self._show_in_thumbnail
        dictionary[ 'show_in_thumbnail_even_when_null' ] = self._show_in_thumbnail_even_when_null        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        Service._LoadFromDictionary( self, dictionary )
        
        self._colours = dict( dictionary[ 'colours' ] )
        self._show_in_thumbnail = dictionary[ 'show_in_thumbnail' ]
        self._show_in_thumbnail_even_when_null = dictionary[ 'show_in_thumbnail_even_when_null' ]
        
    
    def GetColour( self, rating_state ):
        
        with self._lock:
            
            return self._colours[ rating_state ]
            
        

    def GetShowInThumbnail( self ):
        
        with self._lock:
            
            return self._show_in_thumbnail
            
        
    
    def GetShowInThumbnailEvenWhenNull( self ):
        
        with self._lock:
            
            return self._show_in_thumbnail_even_when_null
            
        
    
    def ConvertNoneableRatingToString( self, rating: typing.Optional[ float ] ):
        
        raise NotImplementedError()
        
    

class ServiceLocalRatingIncDec( ServiceLocalRating ):
    
    def ConvertNoneableRatingToString( self, rating: typing.Optional[ int ] ):
        
        if rating is None:
            
            return 'not set'
            
        elif isinstance( rating, int ):
            
            return HydrusNumbers.ToHumanInt( rating )
            
        
        return 'unknown'
        
    
    def ConvertRatingStateAndRatingToString( self, rating_state: int, rating: float ):
        
        if rating_state == ClientRatings.SET:
            
            return HydrusNumbers.ToHumanInt( rating )
            
        elif rating_state == ClientRatings.MIXED:
            
            return 'mixed'
            
        elif rating_state == ClientRatings.NULL:
            
            return 'not set'
            
        else:
            
            return 'unknown'
            
        
    

class ServiceLocalRatingStars( ServiceLocalRating ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceLocalRating._GetSerialisableDictionary( self )
        
        dictionary[ 'shape' ] = self._shape
        dictionary[ 'rating_svg' ] = self._rating_svg
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceLocalRating._LoadFromDictionary( self, dictionary )
        
        self._shape = dictionary[ 'shape' ]
        self._rating_svg = dictionary[ 'rating_svg' ]
        
    
    def ConvertNoneableRatingToString( self, rating: typing.Optional[ float ] ):
        
        raise NotImplementedError()
        
    
    def GetStarType( self ) -> ClientRatings.StarType:
        
        with self._lock:
            
            return ClientRatings.StarType( self._shape, self._rating_svg )
            
        
    
class ServiceLocalRatingLike( ServiceLocalRatingStars ):
    
    def ConvertNoneableRatingToString( self, rating: typing.Optional[ float ] ):
        
        if rating is None:
            
            return 'not set'
            
        elif isinstance( rating, ( float, int ) ):
            
            if rating < 0.5:
                
                return 'dislike'
                
            elif rating >= 0.5:
                
                return 'like'
                
            
        
        return 'unknown'
        
    
    def ConvertRatingStateToString( self, rating_state: int ):
        
        if rating_state == ClientRatings.LIKE:
            
            return 'like'
            
        elif rating_state == ClientRatings.DISLIKE:
            
            return 'dislike'
            
        elif rating_state == ClientRatings.MIXED:
            
            return 'mixed'
            
        elif rating_state == ClientRatings.NULL:
            
            return 'not set'
            
        else:
            
            return 'unknown'
            
        
    
class ServiceLocalRatingNumerical( ServiceLocalRatingStars ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceLocalRatingStars._GetSerialisableDictionary( self )
        
        dictionary[ 'num_stars' ] = self._num_stars
        dictionary[ 'allow_zero' ] = self._allow_zero
        dictionary[ 'custom_pad' ] = self._custom_pad
        dictionary[ 'show_fraction_beside_stars' ] = self._show_fraction_beside_stars
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceLocalRatingStars._LoadFromDictionary( self, dictionary )
        
        self._num_stars = dictionary[ 'num_stars' ]
        self._allow_zero = dictionary[ 'allow_zero' ]
        self._custom_pad = dictionary[ 'custom_pad' ]
        self._show_fraction_beside_stars = dictionary[ 'show_fraction_beside_stars' ]
        
    
    def AllowZero( self ):
        
        with self._lock:
            
            return self._allow_zero
            
        
    
    def ConvertNoneableRatingToString( self, rating: typing.Optional[ float ] ):
        
        if rating is None:
            
            return 'not set'
            
        elif isinstance( rating, float ):
            
            rating_value = self.ConvertRatingToStars( rating )
            rating_range = self._num_stars
            
            return HydrusNumbers.ValueRangeToPrettyString( rating_value, rating_range )
            
        
        return 'unknown'
        
    
    def ConvertRatingStateAndRatingToString( self, rating_state: int, rating: float ):
        
        if rating_state == ClientRatings.SET:
            
            return self.ConvertNoneableRatingToString( rating )
            
        elif rating_state == ClientRatings.MIXED:
            
            return 'mixed'
            
        elif rating_state == ClientRatings.NULL:
            
            return 'not set'
            
        else:
            
            return 'unknown'
            
        
    
    def ConvertRatingToStars( self, rating: float ) -> int:
        
        return ClientRatings.ConvertRatingToStars( self._num_stars, self._allow_zero, rating )
        
    
    def ConvertStarsToRating( self, stars: int ):
        
        return ClientRatings.ConvertStarsToRating( self._num_stars, self._allow_zero, stars )
        
    
    def GetNumStars( self ):
        
        with self._lock:
            
            return self._num_stars
            
        
    
    def GetCustomPad( self ):
        
        with self._lock:
            
            return self._custom_pad
            
        
    def GetOneStarValue( self ):
        
        num_choices = self._num_stars
        
        if self._allow_zero:
            
            num_choices += 1
            
        
        one_star_value = 1.0 / ( num_choices - 1 )
        
        return one_star_value
        
    def GetShowFractionBesideStars( self ):
        
        with self._lock:
            
            return self._show_fraction_beside_stars
            
        
    
class ServiceRemote( Service ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        super().__init__( service_key, service_type, name, dictionary = dictionary )
        
        self.network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        
    
    def _DelayFutureRequests( self, reason, duration_s = None ):
        
        if reason == '':
            
            reason = 'unknown error'
            
        
        if duration_s is None:
            
            duration_s = self._GetErrorWaitPeriod()
            
        
        next_no_requests_until = HydrusTime.GetNow() + duration_s
        
        if next_no_requests_until > self._no_requests_until:
            
            self._no_requests_reason = reason
            self._no_requests_until = HydrusTime.GetNow() + duration_s
            
        
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
        
        if not HydrusTime.TimeHasPassed( self._no_requests_until ):
            
            raise HydrusExceptions.InsufficientCredentialsException( self._no_requests_reason + ' - next request ' + HydrusTime.TimestampToPrettyTimeDelta( self._no_requests_until ) )
            
        
        if including_bandwidth:
            
            example_nj = ClientNetworkingJobs.NetworkJobHydrus( self._service_key, 'GET', self._GetBaseURL() )
            
            can_start = CG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), threshold = 60 )
            
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
        
    
    def DelayFutureRequests( self, reason, duration_s = None ):
        
        with self._lock:
            
            self._DelayFutureRequests( reason, duration_s = None )
            
        
    
    def GetBandwidthCurrentMonthSummary( self ):
        
        with self._lock:
            
            return CG.client_controller.network_engine.bandwidth_manager.GetCurrentMonthSummary( self.network_context )
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self ):
        
        with self._lock:
            
            return CG.client_controller.network_engine.bandwidth_manager.GetBandwidthStringsAndGaugeTuples( self.network_context )
            
        
    
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
        
        CG.client_controller.pub( 'notify_account_sync_due' )
        
        self._next_account_sync = HydrusTime.GetNow()
        
        CG.client_controller.network_engine.session_manager.ClearSession( self.network_context )
        
        self._SetDirty()
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
    
    def _DealWithFundamentalNetworkError( self ):
        
        account_key = self._account.GetAccountKey()
        
        self._account = HydrusNetwork.Account.GenerateUnknownAccount( account_key )
        
        self._next_account_sync = HydrusTime.GetNow() + ACCOUNT_SYNC_PERIOD
        
        self._SetDirty()
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
    
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
        
        self._next_account_sync = HydrusTime.GetNow()
        
        self._SetDirty()
        
        CG.client_controller.pub( 'notify_account_sync_due' )
        
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( self._account )
        dictionary[ 'next_account_sync' ] = self._next_account_sync
        dictionary[ 'network_sync_paused' ] = self._network_sync_paused
        dictionary[ 'service_options' ] = HydrusSerialisable.SerialisableDictionary( self._service_options )
        
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
            
        
        self._service_options = HydrusSerialisable.SerialisableDictionary( dictionary[ 'service_options' ] )
        
    
    def _SetNewTagFilter( self, tag_filter: HydrusTags.TagFilter ):
        
        self._service_options[ 'tag_filter' ] = tag_filter
        
    
    def _UpdateServiceOptions( self, service_options ):
        
        self._service_options.update( service_options )
        
    
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
        
        if HydrusTime.TimeHasPassed( self._next_account_sync ):
            
            s = 'imminently'
            
        else:
            
            s = HydrusTime.TimestampToPrettyTimeDelta( self._next_account_sync )
            
        
        return 'next account sync ' + s
        
    
    def GetStatusInfo( self ) -> tuple[ bool, str ]:
        
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
            
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            CG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def Request( self, method, command, request_args = None, request_headers = None, report_hooks = None, temp_path = None, file_body_path = None ):
        
        if request_args is None: request_args = {}
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        try:
            
            query = ''
            body = ''
            
            if method == HC.GET:
                
                query = HydrusNetworkVariableHandling.DumpToGETQuery( request_args )
                
                body = ''
                
                content_type = None
                
            elif method == HC.POST:
                
                query = ''
                
                if command == 'file':
                    
                    content_type = HC.APPLICATION_OCTET_STREAM
                    
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
                
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( self._service_key, method, url, body = body, temp_path = temp_path, file_body_path = file_body_path )
            
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
                
            
            CG.client_controller.network_engine.AddJob( network_job )
            
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
                    
                    self._DelayFutureRequests( 'server was busy', duration_s = 5 * 60 )
                    
                elif isinstance( e, HydrusExceptions.SessionException ):
                    
                    CG.client_controller.network_engine.session_manager.ClearSession( self.network_context )
                    
                elif isinstance( e, ( HydrusExceptions.MissingCredentialsException, HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ConflictException ) ):
                    
                    self._DealWithAccountError()
                    
                elif isinstance( e, HydrusExceptions.NetworkVersionException ):
                    
                    self._DealWithFundamentalNetworkError()
                    
                elif isinstance( e, HydrusExceptions.BandwidthException ):
                    
                    self._DelayFutureRequests( 'service has exceeded bandwidth', duration_s = ACCOUNT_SYNC_PERIOD )
                    
                elif isinstance( e, HydrusExceptions.ServerException ):
                    
                    self._DelayFutureRequests( str( e ) )
                    
                
            
            raise
            
        
    
    def SetAccountRefreshDueNow( self ):
        
        with self._lock:
            
            self._next_account_sync = HydrusTime.GetNow() - 1
            
            self._SetDirty()
            
        
        CG.client_controller.pub( 'notify_account_sync_due' )
        
    
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
                    
                    self._next_account_sync = HydrusTime.GetNow() + SHORT_DELAY_PERIOD
                    
                    self._SetDirty()
                    
                else:
                    
                    do_it = HydrusTime.TimeHasPassed( self._next_account_sync )
                    
                
            
        
        if do_it:
            
            try:
                
                account_response = self.Request( HC.GET, 'account' )
                
                with self._lock:
                    
                    self._account = account_response[ 'account' ]
                    
                    ( message, message_created ) = self._account.GetMessageAndTimestamp()
                    
                    if message != '' and message_created != original_message_created and not HydrusTime.TimeHasPassed( message_created + ( 86400 * 5 ) ):
                        
                        m = 'New message for your account on {}:'.format( self._name )
                        m += '\n' * 2
                        m += message
                        
                        HydrusData.ShowText( m )
                        
                    
                    if force:
                        
                        self._no_requests_until = 0
                        
                    
                
                try:
                    
                    options_response = self.Request( HC.GET, 'options' )
                    
                    with self._lock:
                        
                        service_options = options_response[ 'service_options' ]
                        
                        self._UpdateServiceOptions( service_options )
                        
                    
                except HydrusExceptions.SerialisationException:
                    
                    pass
                    
                
                if self._service_type == HC.TAG_REPOSITORY:
                    
                    try:
                        
                        tag_filter_response = self.Request( HC.GET, 'tag_filter' )
                        
                        with self._lock:
                            
                            tag_filter = tag_filter_response[ 'tag_filter' ]
                            
                            if 'tag_filter' in self._service_options and CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                                
                                old_tag_filter = self._service_options[ 'tag_filter' ]
                                
                                if old_tag_filter != tag_filter:
                                    
                                    try:
                                        
                                        summary = tag_filter.GetChangesSummaryText( old_tag_filter )
                                        
                                        message = 'The tag filter for "{}" just changed! Changes are:{}{}'.format( self._name, '\n' * 2, summary )
                                        
                                        HydrusData.ShowText( message )
                                        
                                    except:
                                        
                                        pass
                                        
                                    
                                
                            
                            self._SetNewTagFilter( tag_filter )
                            
                        
                    except Exception: # any exception, screw it
                        
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
                    
                    self._next_account_sync = HydrusTime.GetNow() + ACCOUNT_SYNC_PERIOD
                    
                    self._SetDirty()
                    
                
                CG.client_controller.pub( 'notify_new_permissions' )
                CG.client_controller.pub( 'important_dirt_to_clean' )
                
            
        
    
class ServiceRepository( ServiceRestricted ):
    
    def __init__( self, service_key, service_type, name, dictionary = None ):
        
        super().__init__( service_key, service_type, name, dictionary = dictionary )
        
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
        
        return not ( self._update_processing_paused or CG.client_controller.new_options.GetBoolean( 'pause_repo_sync' ) )
        
    
    def _CheckFunctional( self, including_external_communication = True, including_bandwidth = True, including_account = True ):
        
        if CG.client_controller.new_options.GetBoolean( 'pause_repo_sync' ):
            
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
            
        
        it_took = HydrusTime.GetNowPrecise() - precise_timestamp
        
        rows_s = HydrusNumbers.ToHumanInt( int( total_rows / it_took ) )
        
        summary = '{} processed {} {} at {} rows/s'.format( self._name, HydrusNumbers.ToHumanInt( total_rows ), row_name, rows_s )
        
        HydrusData.Print( summary )
        
    
    def _ReportOngoingRowSpeed( self, job_status, rows_done, total_rows, precise_timestamp, rows_done_in_last_packet, row_name ):
        
        it_took = HydrusTime.GetNowPrecise() - precise_timestamp
        
        rows_s = HydrusNumbers.ToHumanInt( int( rows_done_in_last_packet / it_took ) )
        
        popup_message = '{} {}: processing at {} rows/s'.format( row_name, HydrusNumbers.ValueRangeToPrettyString( rows_done, total_rows ), rows_s )
        
        CG.client_controller.frame_splash_status.SetText( popup_message, print_to_log = False )
        job_status.SetStatusText( popup_message, 2 )
        
    
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
                
                CG.client_controller.WriteSynchronous( 'set_repository_update_hashes', service_key, metadata_slice )
                
            else:
                
                CG.client_controller.WriteSynchronous( 'associate_repository_update_hashes', service_key, metadata_slice )
                
            
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
            
        
        update_hashes = CG.client_controller.Read( 'missing_repository_update_hashes', service_key )
        
        if len( update_hashes ) > 0:
            
            job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_status.SetStatusTitle( name + ' sync: downloading updates' )
                
                CG.client_controller.pub( 'message', job_status )
                
                for ( i, update_hash ) in enumerate( update_hashes ):
                    
                    status = HydrusNumbers.ValueRangeToPrettyString( i, len( update_hashes ) )
                    
                    CG.client_controller.frame_splash_status.SetText( status, print_to_log = False )
                    job_status.SetStatusText( status )
                    job_status.SetGauge( i, len( update_hashes ) )
                    
                    with self._lock:
                        
                        if not self._CanSyncDownload():
                            
                            return
                            
                        
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', duration_s = 3 * 60 )
                            
                        
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
                        message += '\n' * 2
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
                        message += '\n' * 2
                        message += 'The repository has been paused for now. Please look into what could be wrong and report this to the hydrus dev.'
                        
                        HydrusData.ShowText( message )
                        
                        return
                        
                    
                    try:
                        
                        CG.client_controller.WriteSynchronous( 'import_update', update_network_string, update_hash, mime )
                        
                    except Exception as e:
                        
                        with self._lock:
                            
                            self._DealWithFundamentalNetworkError()
                            
                        
                        message = 'While downloading updates for the ' + self._name + ' repository, one failed to import! The error follows:'
                        
                        HydrusData.ShowText( message )
                        
                        HydrusData.ShowException( e )
                        
                        return
                        
                    
                
                job_status.SetStatusText( 'finished' )
                job_status.DeleteGauge()
                
            finally:
                
                job_status.FinishAndDismiss( 5 )
                
            
        
    
    def _SyncProcessUpdates( self, maintenance_mode = HC.MAINTENANCE_IDLE, stop_time = None ):
        
        with self._lock:
            
            if not self._CanSyncProcess():
                
                return
                
            
        
        if CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ):
            
            return
            
        
        work_done = False
        
        try:
            
            job_status = ClientThreading.JobStatus( cancellable = True, maintenance_mode = maintenance_mode, stop_time = stop_time )
            
            title = '{} sync: processing updates'.format( self._name )
            
            job_status.SetStatusTitle( title )
            
            content_types_to_process = self._GetContentTypesWeAreProcessing()
            
            ( this_is_first_definitions_work, definition_hashes_and_content_types, this_is_first_content_work, content_hashes_and_content_types ) = CG.client_controller.Read( 'repository_update_hashes_to_process', self._service_key, content_types_to_process )
            
            if len( definition_hashes_and_content_types ) == 0 and len( content_hashes_and_content_types ) == 0:
                
                return # no work to do
                
            
            if len( content_hashes_and_content_types ) > 0:
                
                content_hashes_and_content_types = self._metadata.SortContentHashesAndContentTypes( content_hashes_and_content_types )
                
            
            HydrusData.Print( title )
            
            num_updates_done = 0
            num_updates_to_do = len( definition_hashes_and_content_types ) + len( content_hashes_and_content_types )
            
            CG.client_controller.pub( 'message', job_status )
            CG.client_controller.frame_splash_status.SetTitleText( title, print_to_log = False )
            
            total_definition_rows_completed = 0
            total_content_rows_completed = 0
            
            did_definition_analyze = False
            did_content_analyze = False
            
            definition_start_time = HydrusTime.GetNowPrecise()
            
            try:
                
                for ( definition_hash, content_types ) in definition_hashes_and_content_types:
                    
                    progress_string = HydrusNumbers.ValueRangeToPrettyString( num_updates_done, num_updates_to_do )
                    
                    splash_title = '{} sync: processing updates: {}'.format( self._name, progress_string )
                    
                    CG.client_controller.frame_splash_status.SetTitleText( splash_title, clear_undertexts = False, print_to_log = False )
                    
                    status = 'processing: {}'.format( progress_string )
                    
                    job_status.SetStatusText( status )
                    job_status.SetGauge( num_updates_done, num_updates_to_do )
                    
                    try:
                        
                        update_path = CG.client_controller.client_files_manager.GetFilePath( definition_hash, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) was missing. Your repository should be paused, and all update files have been scheduled for a presence check. I recommend you run _database->maintenance->clear/fix orphan file records_ too. Please then permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    with open( update_path, 'rb' ) as f:
                        
                        update_network_bytes = f.read()
                        
                    
                    try:
                        
                        definition_update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
                        
                    except:
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) was invalid. Your repository should be paused, and all update files have been scheduled for an integrity check. Please permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    if not isinstance( definition_update, HydrusNetwork.DefinitionsUpdate ):
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a definition update file ({}) has incorrect metadata. Your repository should be paused, and all update files have been scheduled for a metadata rescan. Please permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( definition_hash.hex() ) )
                        
                    
                    rows_in_this_update = definition_update.GetNumRows()
                    rows_done_in_this_update = 0
                    
                    iterator_dict = {}
                    
                    iterator_dict[ 'service_hash_ids_to_hashes' ] = iter( definition_update.GetHashIdsToHashes().items() )
                    iterator_dict[ 'service_tag_ids_to_tags' ] = iter( definition_update.GetTagIdsToTags().items() )
                    
                    while len( iterator_dict ) > 0:
                        
                        this_work_start_time = HydrusTime.GetNowPrecise()
                        
                        if CG.client_controller.CurrentlyVeryIdle():
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_very_idle' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_very_idle' ) / 100
                            
                        elif CG.client_controller.CurrentlyIdle():
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_idle' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_idle' ) / 100
                            
                        else:
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_normal' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_normal' ) / 100
                            
                        
                        start_time = HydrusTime.GetNowPrecise()
                        
                        num_rows_done = CG.client_controller.WriteSynchronous( 'process_repository_definitions', self._service_key, definition_hash, iterator_dict, content_types, job_status, expected_work_period )
                        
                        actual_work_period = HydrusTime.GetNowPrecise() - start_time
                        
                        rows_done_in_this_update += num_rows_done
                        total_definition_rows_completed += num_rows_done
                        
                        work_done = True
                        
                        if ( this_is_first_definitions_work or total_definition_rows_completed > 10000 ) and not did_definition_analyze:
                            
                            CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode )
                            
                            did_definition_analyze = True
                            
                        
                        if CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_status.IsCancelled():
                            
                            return
                            
                        
                        reasonable_work_time = min( 5 * expected_work_period, actual_work_period )
                        
                        time.sleep( reasonable_work_time * rest_ratio )
                        
                        self._ReportOngoingRowSpeed( job_status, rows_done_in_this_update, rows_in_this_update, this_work_start_time, num_rows_done, 'definitions' )
                        
                    
                    num_updates_done += 1
                    
                
                if ( this_is_first_definitions_work or total_definition_rows_completed > 10000 ) and not did_definition_analyze:
                    
                    CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode )
                    
                    did_definition_analyze = True
                    
                
            finally:
                
                self._LogFinalRowSpeed( definition_start_time, total_definition_rows_completed, 'definitions' )
                
            
            if CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_status.IsCancelled():
                
                return
                
            
            content_start_time = HydrusTime.GetNowPrecise()
            
            try:
                
                for ( content_hash, content_types ) in content_hashes_and_content_types:
                    
                    progress_string = HydrusNumbers.ValueRangeToPrettyString( num_updates_done, num_updates_to_do )
                    
                    splash_title = '{} sync: processing updates: {}'.format( self._name, progress_string )
                    
                    CG.client_controller.frame_splash_status.SetTitleText( splash_title, clear_undertexts = False, print_to_log = False )
                    
                    status = 'processing: {}'.format( progress_string )
                    
                    job_status.SetStatusText( status )
                    job_status.SetGauge( num_updates_done, num_updates_to_do )
                    
                    try:
                        
                        update_path = CG.client_controller.client_files_manager.GetFilePath( content_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
                        
                    except HydrusExceptions.FileMissingException:
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_PRESENCE_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) was missing. Your repository should be paused, and all update files have been scheduled for a presence check. I recommend you run _database->maintenance->clear/fix orphan file records_ too. Please then permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    with open( update_path, 'rb' ) as f:
                        
                        update_network_bytes = f.read()
                        
                    
                    try:
                        
                        content_update = HydrusSerialisable.CreateFromNetworkBytes( update_network_bytes )
                        
                    except:
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_REMOVE_RECORD )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) was invalid. Your repository should be paused, and all update files have been scheduled for an integrity check. Please permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    if not isinstance( content_update, HydrusNetwork.ContentUpdate ):
                        
                        CG.client_controller.WriteSynchronous( 'schedule_repository_update_file_maintenance', self._service_key, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                        
                        raise Exception( 'An unusual error has occured during repository processing: a content update file ({}) has incorrect metadata. Your repository should be paused, and all update files have been scheduled for a metadata rescan. Please permit file maintenance under _database->file maintenance->manage scheduled jobs_ to finish its new work, which should fix this, before unpausing your repository.'.format( content_hash.hex() ) )
                        
                    
                    rows_in_this_update = content_update.GetNumRows( content_types )
                    rows_done_in_this_update = 0
                    
                    iterator_dict = {}
                    
                    if HC.CONTENT_TYPE_FILES in content_types:
                        
                        iterator_dict[ 'new_files' ] = iter( content_update.GetNewFiles() )
                        iterator_dict[ 'deleted_files' ] = iter( content_update.GetDeletedFiles() )
                        
                    
                    if HC.CONTENT_TYPE_MAPPINGS in content_types:
                        
                        iterator_dict[ 'new_mappings' ] = HydrusLists.SmoothOutMappingIterator( content_update.GetNewMappings(), 50 )
                        iterator_dict[ 'deleted_mappings' ] = HydrusLists.SmoothOutMappingIterator( content_update.GetDeletedMappings(), 50 )
                        
                    
                    if HC.CONTENT_TYPE_TAG_PARENTS in content_types:
                        
                        iterator_dict[ 'new_parents' ] = iter( content_update.GetNewTagParents() )
                        iterator_dict[ 'deleted_parents' ] = iter( content_update.GetDeletedTagParents() )
                        
                    
                    if HC.CONTENT_TYPE_TAG_SIBLINGS in content_types:
                        
                        iterator_dict[ 'new_siblings' ] = iter( content_update.GetNewTagSiblings() )
                        iterator_dict[ 'deleted_siblings' ] = iter( content_update.GetDeletedTagSiblings() )
                        
                    
                    while len( iterator_dict ) > 0:
                        
                        this_work_start_time = HydrusTime.GetNowPrecise()
                        
                        if CG.client_controller.CurrentlyVeryIdle():
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_very_idle' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_very_idle' ) / 100
                            
                        elif CG.client_controller.CurrentlyIdle():
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_idle' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_idle' ) / 100
                            
                        else:
                            
                            expected_work_period = HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'repository_processing_work_time_ms_normal' ) )
                            rest_ratio = CG.client_controller.new_options.GetInteger( 'repository_processing_rest_percentage_normal' ) / 100
                            
                        
                        start_time = HydrusTime.GetNowPrecise()
                        
                        num_rows_done = CG.client_controller.WriteSynchronous( 'process_repository_content', self._service_key, content_hash, iterator_dict, content_types, job_status, expected_work_period )
                        
                        actual_work_period = HydrusTime.GetNowPrecise() - start_time
                        
                        rows_done_in_this_update += num_rows_done
                        total_content_rows_completed += num_rows_done
                        
                        work_done = True
                        
                        if ( this_is_first_content_work or total_content_rows_completed > 10000 ) and not did_content_analyze:
                            
                            CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode )
                            
                            did_content_analyze = True
                            
                        
                        if CG.client_controller.ShouldStopThisWork( maintenance_mode, stop_time = stop_time ) or job_status.IsCancelled():
                            
                            return
                            
                        
                        reasonable_work_time = min( 5 * expected_work_period, actual_work_period )
                        
                        time.sleep( reasonable_work_time * rest_ratio )
                        
                        self._ReportOngoingRowSpeed( job_status, rows_done_in_this_update, rows_in_this_update, this_work_start_time, num_rows_done, 'content rows' )
                        
                    
                    num_updates_done += 1
                    
                
                if ( this_is_first_content_work or total_content_rows_completed > 10000 ) and not did_content_analyze:
                    
                    CG.client_controller.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode )
                    
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
                
            
            CG.client_controller.pub( 'important_dirt_to_clean' )
            
            
        finally:
            
            if work_done:
                
                with self._lock:
                    
                    self._is_mostly_caught_up = None
                    
                    self._SetDirty()
                    
                
                CG.client_controller.pub( 'notify_force_refresh_tags_data' )
                CG.client_controller.pub( 'notify_new_tag_display_application' )
                
            
            job_status.DeleteStatusText()
            job_status.DeleteStatusText( level = 2 )
            job_status.DeleteGauge()
            
            job_status.FinishAndDismiss( 3 )
            
        
    
    def _UpdateServiceOptions( self, service_options ):
        
        if 'update_period' in service_options and 'update_period' in self._service_options and service_options[ 'update_period' ] != self._service_options[ 'update_period' ]:
            
            update_period = service_options[ 'update_period' ]
            
            self._metadata.CalculateNewNextUpdateDue( update_period )
            
        
        ServiceRestricted._UpdateServiceOptions( self, service_options )
        
    
    def CanDoIdleShutdownWork( self ):
        
        with self._lock:
            
            if not self._CanSyncProcess():
                
                return False
                
            
            service_key = self._service_key
            
        
        content_types_we_are_processing = self._GetContentTypesWeAreProcessing()
        
        ( num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates ) = CG.client_controller.Read( 'repository_progress', service_key )
        
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
            
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        CG.client_controller.pub( 'notify_new_permissions' )
        
    
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
                
            
        
    
    def GetTagFilter( self ) -> HydrusTags.TagFilter:
        
        with self._lock:
            
            if self._service_type != HC.TAG_REPOSITORY:
                
                raise Exception( 'This is not a tag repository! It does not have a tag filter!' )
                
            
            if 'tag_filter' in self._service_options:
                
                tag_filter = self._service_options[ 'tag_filter' ]
                
                if not isinstance( tag_filter, HydrusTags.TagFilter ):
                    
                    raise HydrusExceptions.DataMissing( 'This service has a bad tag filter! Try refreshing your account!' )
                    
                
                return tag_filter
                
            else:
                
                raise HydrusExceptions.DataMissing( 'This service does not seem to have a tag filter! Try refreshing your account!' )
                
            
        
    
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
        
        two_weeks_ago = HydrusTime.GetNow() - CAUGHT_UP_BUFFER
        
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
        
        ( this_is_first_definitions_work, definition_hashes_and_content_types, this_is_first_content_work, content_hashes_and_content_types ) = CG.client_controller.Read( 'repository_update_hashes_to_process', self._service_key, content_types_to_process )
        
        missing_update_hashes = CG.client_controller.Read( 'missing_repository_update_hashes', service_key )
        
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
            
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            CG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def PausePlayUpdateProcessing( self, content_type = None ):
        
        with self._lock:
            
            if content_type is None:
                
                self._update_processing_paused = not self._update_processing_paused
                
            else:
                
                self._update_processing_content_types_paused[ content_type ] = not self._update_processing_content_types_paused[ content_type ]
                
            
            self._SetDirty()
            
            paused = self._update_processing_paused
            
            self._is_mostly_caught_up = None
            
        
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
        if not paused:
            
            CG.client_controller.pub( 'notify_new_permissions' )
            
        
    
    def Reset( self ):
        
        with self._lock:
            
            self._no_requests_reason = ''
            self._no_requests_until = 0
            
            self._account = HydrusNetwork.Account.GenerateUnknownAccount()
            
            self._next_account_sync = 0
            
            self._metadata = HydrusNetwork.Metadata()
            
            self._is_mostly_caught_up = None
            
            self._SetDirty()
            
        
        CG.client_controller.pub( 'notify_account_sync_due' )
        CG.client_controller.pub( 'important_dirt_to_clean' )
        
        CG.client_controller.Write( 'reset_repository', self )
        
    
    def SetTagFilter( self, tag_filter: HydrusTags.TagFilter ):
        
        with self._lock:
            
            if self._service_type != HC.TAG_REPOSITORY:
                
                raise Exception( 'This is not a tag repository! It does not have a tag filter!' )
                
            
            self._service_options[ 'tag_filter' ] = tag_filter
            
        
    
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
                    
                    CG.client_controller.pub( 'important_dirt_to_clean' )
                    
                
            
        
    
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
            
        
        thumbnail_hashes = CG.client_controller.Read( 'missing_thumbnail_hashes', service_key )
        
        num_to_do = len( thumbnail_hashes )
        
        if num_to_do > 0:
            
            client_files_manager = CG.client_controller.client_files_manager
            
            job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
            
            try:
                
                job_status.SetStatusTitle( name + ' sync: downloading thumbnails' )
                
                CG.client_controller.pub( 'message', job_status )
                
                for ( i, thumbnail_hash ) in enumerate( thumbnail_hashes ):
                    
                    status = HydrusNumbers.ValueRangeToPrettyString( i, num_to_do )
                    
                    CG.client_controller.frame_splash_status.SetText( status, print_to_log = False )
                    job_status.SetStatusText( status )
                    job_status.SetGauge( i, num_to_do )
                    
                    with self._lock:
                        
                        if not self._CanSyncDownload():
                            
                            break
                            
                        
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        with self._lock:
                            
                            self._DelayFutureRequests( 'download was recently cancelled', duration_s = 3 * 60 )
                            
                        
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
                    
                
                job_status.SetStatusText( 'finished' )
                job_status.DeleteGauge()
                
            finally:
                
                job_status.FinishAndDismiss( 5 )
                
            
        
    

def GetIPFSConfigValue( api_base_url, config_key ):
    
    url = f'{api_base_url}config?arg={config_key}'
    
    network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
    
    CG.client_controller.network_engine.AddJob( network_job )
    
    network_job.WaitUntilDone()
    
    parsing_text = network_job.GetContentText()
    
    j = json.loads( parsing_text )
    
    return j[ 'Value' ]
    

def SetIPFSConfigValueBool( api_base_url, config_key, value: bool ):
    
    value_json = 'true' if value else 'false'
    
    # bool=true helps it know the type
    url = f'{api_base_url}config?arg={config_key}&arg={value_json}&bool=true'
    
    network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
    
    CG.client_controller.network_engine.AddJob( network_job )
    
    network_job.WaitUntilDone()
    
    parsing_text = network_job.GetContentText()
    
    j = json.loads( parsing_text )
    
    if j[ 'Value' ] != value:
        
        raise Exception( f'Could not set {config_key} to {value}!\n\n{parsing_text}' )
        
    

def GetTSize( api_base_url, multihash ):
    
    url = f'{api_base_url}dag/stat?arg={multihash}&progress=false'
    
    network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
    
    CG.client_controller.network_engine.AddJob( network_job )
    
    network_job.WaitUntilDone()
    
    parsing_text = network_job.GetContentText()
    
    j = json.loads( parsing_text )
    
    return j[ 'TotalSize' ]
    

class ServiceIPFS( ServiceRemote ):
    
    def _GetSerialisableDictionary( self ):
        
        dictionary = ServiceRemote._GetSerialisableDictionary( self )
        
        dictionary[ 'multihash_prefix' ] = self._multihash_prefix
        
        return dictionary
        
    
    def _LoadFromDictionary( self, dictionary ):
        
        ServiceRemote._LoadFromDictionary( self, dictionary )
        
        self._multihash_prefix = dictionary[ 'multihash_prefix' ]
        
    
    def _GetAPIBaseURL( self ):
        
        full_host = self._credentials.GetPortedAddress()
        
        api_base_url = 'http://{}/api/v0/'.format( full_host )
        
        return api_base_url
        
    
    def GetDaemonVersion( self ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        url = api_base_url + 'version'
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        CG.client_controller.network_engine.AddJob( network_job )
        
        network_job.WaitUntilDone()
        
        parsing_text = network_job.GetContentText()
        
        j = json.loads( parsing_text )
        
        return j[ 'Version' ]
        
    
    def GetMultihashPrefix( self ):
        
        with self._lock:
            
            return self._multihash_prefix
            
        
    
    def IsPinned( self, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        # check if it is pinned. if we try to unpin something not pinned, the daemon 500s
        
        url = api_base_url + 'pin/ls?arg={}'.format( multihash )
        
        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
        
        CG.client_controller.network_engine.AddJob( network_job )
        
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
        
        job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
        
        job_status.SetStatusTitle( 'creating ipfs directory on ' + self._name )
        
        CG.client_controller.pub( 'message', job_status )
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        try:
            
            hashes = sorted( hashes )
            
            dag_object = {
                'Data' : { '/' : { 'bytes' : 'CAE=' } }, # ok this is an empty UnixFS dir in base64, but the 'bytes' part lets DAG-JSON know it should be in bytes. nothing could be simpler or more obvious
                'Links' : []
            }
            
            for ( i, hash ) in enumerate( hashes ):
                
                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                
                if should_quit:
                    
                    job_status.SetStatusText( 'cancelled!' )
                    
                    return
                    
                
                job_status.SetStatusText( 'ensuring files are pinned: ' + HydrusNumbers.ValueRangeToPrettyString( i, len( hashes ) ) )
                job_status.SetGauge( i, len( hashes ) )
                
                media_result = CG.client_controller.Read( 'media_result', hash )
                
                mime = media_result.GetMime()
                
                multihash = media_result.GetLocationsManager().GetServiceFilename( self._service_key )
                
                if multihash is None:
                    
                    try:
                        
                        multihash = self.PinFile( hash, mime )
                        
                    except Exception as e:
                        
                        raise Exception( f'File {hash.hex()} could not be pinned!\n\n{e}' )
                        
                    
                
                try:
                    
                    tsize = GetTSize( api_base_url, multihash )
                    
                except Exception as e:
                    
                    raise Exception( f'Could not get multihash total size info for {hash.hex()}/{multihash}!\n\n{e}' )
                    
                
                filename = hash.hex() + HC.mime_ext_lookup[ mime ]
                
                dag_object[ 'Links' ].append(
                    {
                        'Name' : filename,
                        'Hash' : {
                            '/' : multihash
                        },
                        'Tsize' : tsize
                    }
                )
                
            
            job_status.SetStatusText( 'creating directory' )
            job_status.DeleteGauge()
            
            dag_json_encoded = json.dumps( dag_object )
            
            url = api_base_url + 'dag/put?input-codec=dag-json&store-codec=dag-pb&pin=true'
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            f = BytesIO( dag_json_encoded.encode( 'utf-8' ) )
            
            files = { 'file' : ( 'dag.json', f, 'application/json' ) }
            
            network_job.SetFiles( files )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            parsing_text = network_job.GetContentText()
            
            response_json = json.loads( parsing_text )
            
            directory_multihash = response_json[ 'Cid' ][ '/' ]
            
            content_update_row = ( hashes, directory_multihash, note )
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
            
            CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates ) )
            
            job_status.SetStatusText( 'done!' )
            
            with self._lock:
                
                text = self._multihash_prefix + directory_multihash
                
            
            job_status.SetVariable( 'popup_clipboard', ( 'copy multihash to clipboard', text ) )
            
            return directory_multihash
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            job_status.SetErrorException( e )
            
            job_status.Cancel()
            
        finally:
            
            job_status.DeleteGauge()
            
            job_status.Finish()
            
        
    
    def PinFile( self, hash, mime ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        client_files_manager = CG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        with open( path, 'rb' ) as f:
            
            url = api_base_url + 'add'
            
            mime_string = HC.mime_mimetype_string_lookup[ mime ]
            
            files = { 'path' : ( hash.hex(), f, mime_string ) }
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            network_job.SetFiles( files )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
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
            
        
        media_result = CG.client_controller.Read( 'media_result', hash )
        
        file_info_manager = media_result.GetFileInfoManager()
        
        content_update_row = ( file_info_manager, multihash )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates ) )
        
        return multihash
        
    
    def UnpinDirectory( self, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        if self.IsPinned( multihash ):
            
            url = f'{api_base_url}pin/rm?arg={multihash}'
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_DELETE, multihash ) ]
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates ) )
        
    
    def UnpinFile( self, hash, multihash ):
        
        with self._lock:
            
            api_base_url = self._GetAPIBaseURL()
            
        
        if self.IsPinned( multihash ):
            
            url = f'{api_base_url}pin/rm?arg={multihash}'
            
            network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash } ) ]
        
        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates ) )
        
    

class ServicesManager( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        self._keys_to_services: dict[ bytes, Service ] = {}
        self._services_sorted = []
        
        self.RefreshServices()
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_data' )
        
    
    def _GetService( self, service_key: bytes ) -> Service:
        
        try:
            
            return self._keys_to_services[ service_key ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'That service was not found!' )
            
        
    
    def _SetServices( self, services: collections.abc.Collection[ Service ] ):
        
        self._keys_to_services = { service.GetServiceKey() : service for service in services }
        
        self._keys_to_services[ CC.TEST_SERVICE_KEY ] = GenerateService( CC.TEST_SERVICE_KEY, HC.TEST_SERVICE, 'test service' )
        
        key = lambda s: s.GetName().lower()
        
        self._services_sorted = sorted( services, key = key )
        
    
    def Filter( self, service_keys: collections.abc.Iterable[ bytes ], desired_types: collections.abc.Iterable[ int ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services and self._keys_to_services[ service_key ].GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def FilterValidServiceKeys( self, service_keys: collections.abc.Iterable[ bytes ] ):
        
        with self._lock:
            
            filtered_service_keys = [ service_key for service_key in service_keys if service_key in self._keys_to_services ]
            
            return filtered_service_keys
            
        
    
    def GetDefaultLocalTagService( self ) -> Service:
        
        # I can replace this with 'default_local_location_context' kind of thing at some point, but for now we'll merge in here
        
        return self.GetServices( ( HC.LOCAL_TAG, ) )[0]
        
    
    def GetLocalMediaFileServices( self ):
        
        with self._lock:
            
            return [ service for service in self._services_sorted if service.GetServiceType() == HC.LOCAL_FILE_DOMAIN ]
            
        
    
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
            
        
    
    def GetServiceKeysToNames( self ):
        
        with self._lock:
            
            return { service_key : service.GetName() for ( service_key, service ) in self._keys_to_services.items() }
            
        
    
    def GetServiceName( self, service_key: bytes ) -> str:
        
        with self._lock:
            
            return self._GetService( service_key ).GetName()
            
        
    
    def GetServiceType( self, service_key: bytes ) -> int:
        
        with self._lock:
            
            return self._GetService( service_key ).GetServiceType()
            
        
    
    def GetServiceKeyFromName( self, allowed_types: collections.abc.Collection[ int ], service_name: str ):
        
        with self._lock:
            
            for service in self._services_sorted:
                
                if service.GetServiceType() in allowed_types and service.GetName() == service_name:
                    
                    return service.GetServiceKey()
                    
                
            
            for service in self._services_sorted:
                
                if service.GetServiceType() in allowed_types and service.GetName().lower() == service_name.lower():
                    
                    return service.GetServiceKey()
                    
                
            
            raise HydrusExceptions.DataMissing()
            
        
    
    def GetServiceKeys( self, desired_types: collections.abc.Collection[ int ] = HC.ALL_SERVICES ):
        
        with self._lock:
            
            filtered_service_keys = [ service.GetServiceKey() for service in self._services_sorted if service.GetServiceType() in desired_types ]
            
            return filtered_service_keys
            
        
    
    def GetServices( self, desired_types: collections.abc.Collection[ int ] = HC.ALL_SERVICES, randomised: bool = False ) -> list[ Service ]:
        
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
            
        
    

class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ):
        
        return ( self._action, self._row )
        
    
