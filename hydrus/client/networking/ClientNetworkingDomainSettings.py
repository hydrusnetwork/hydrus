import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

DOMAIN_SETTING_MAX_CONNECTION_ATTEMPTS_PER_REQUEST = 0
DOMAIN_SETTING_MAX_RETRIES_PER_REQUEST = 1
DOMAIN_SETTING_CONNECTION_ERROR_TIMEOUT = 2
DOMAIN_SETTING_CONNECTION_ERROR_RETRY_WAIT = 3
DOMAIN_SETTING_CONNECTION_INACTIVITY_TIMEOUT = 4
DOMAIN_SETTING_SERVERSIDE_BANDIWIDTH_RETRY_WAIT = 5
DOMAIN_SETTING_NETWORK_INFRASTRUCTURE_PROBLEMS_HALT_VELOCITY = 6
DOMAIN_SETTING_MAX_ACTIVE_NETWORK_JOBS = 7
DOMAIN_SETTING_VERIFY_HTTPS_TRAFFIC = 8
# TODO: proxy stuff
# TODO: what to do with 400, 403, 404, 501, 503, including back-out-and-retry-later tech levers

domain_setting_enum_str_lookup = {
    DOMAIN_SETTING_MAX_CONNECTION_ATTEMPTS_PER_REQUEST : 'max connection attempts per request',
    DOMAIN_SETTING_MAX_RETRIES_PER_REQUEST : 'max retries per request',
    DOMAIN_SETTING_CONNECTION_ERROR_TIMEOUT : 'connection error timeout',
    DOMAIN_SETTING_CONNECTION_ERROR_RETRY_WAIT : 'connection error/inactivity retry wait',
    DOMAIN_SETTING_CONNECTION_INACTIVITY_TIMEOUT : 'inactivity timeout',
    DOMAIN_SETTING_SERVERSIDE_BANDIWIDTH_RETRY_WAIT : 'serverside bandwidth retry wait',
    DOMAIN_SETTING_NETWORK_INFRASTRUCTURE_PROBLEMS_HALT_VELOCITY : 'network infrastructure error halt velocity',
    DOMAIN_SETTING_MAX_ACTIVE_NETWORK_JOBS : 'max number of simultaneous active network jobs',
    DOMAIN_SETTING_VERIFY_HTTPS_TRAFFIC : 'verify https traffic',
}

class DomainSettings( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_SETTINGS
    SERIALISABLE_NAME = 'Domain Settings'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._domain_settings = HydrusSerialisable.SerialisableDictionary()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, DomainSettings ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return tuple( sorted( self._domain_settings.items() ) ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = self._domain_settings.GetSerialisableTuple()
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_domain_settings = serialisable_info
        
        self._domain_settings = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_domain_settings )
        
    
    def ClearSetting( self, domain_setting_type ):
        
        with self._lock:
            
            if domain_setting_type in self._domain_settings:
                
                del self._domain_settings[ domain_setting_type ]
                
            
        
    
    def GetSettingOrRaise( self, domain_setting_type: int ):
        
        # we're going to try raise instead of return None because this guy deals with small types, not a serialisable options object, and an option like 'max number of x' could well be None sometime
        
        with self._lock:
            
            if domain_setting_type in self._domain_settings:
                
                return self._domain_settings[ domain_setting_type ]
                
            else:
                
                if domain_setting_type in domain_setting_enum_str_lookup:
                    
                    raise HydrusExceptions.DataMissing( f'This domain settings object does not have an entry for {domain_setting_enum_str_lookup[domain_setting_type]}' )
                    
                else:
                    
                    raise NotImplementedError( f'This domain settings object was asked about an invalid domain setting type, here: {domain_setting_type}' )
                    
                
            
        
    
    def SetSetting( self, domain_setting_type: int, value: object ):
        
        with self._lock:
            
            self._domain_settings[ domain_setting_type ] = value
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_SETTINGS ] = DomainSettings

DOMAIN_EVENT_NETWORK_INFRASTRUCTURE = 0
DOMAIN_EVENT_SERVERSIDE_BANDWIDTH = 1
# TODO: 503 stuff if we want, captcha gateways, whatever (but these are currently network infrastructure so we'd prob want to granularise it all to connectionerror, unknown server exception, etc...)

class DomainStatus( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_STATUS
    SERIALISABLE_NAME = 'Domain Status'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._domain_events_ms = HydrusSerialisable.SerialisableDictionary()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, DomainSettings ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return tuple( sorted( self._domain_events_ms.items() ) ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_info = self._domain_events_ms.GetSerialisableTuple()
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_domain_events_ms = serialisable_info
        
        self._domain_events_ms = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_domain_events_ms )
        
    
    def CleanseOldRecords( self, time_delta_s: float ):
        
        with self._lock:
            
            dead_time = HydrusTime.GetNowMS() - HydrusTime.MillisecondiseS( time_delta_s )
            
            for key in list( self._domain_events_ms.keys() ):
                
                list_of_events_ms = self._domain_events_ms[ key ]
                
                cleansed_list_of_events_ms = [ event_ms for event_ms in list_of_events_ms if event_ms > dead_time ]
                
                if len( cleansed_list_of_events_ms ) > 0:
                    
                    self._domain_events_ms[ key ] = cleansed_list_of_events_ms
                    
                else:
                    
                    del self._domain_events_ms[ key ]
                    
                
            
        
    
    def IsStub( self ):
        
        with self._lock:
            
            return len( self._domain_events_ms ) == 0
            
        
    
    def NumberOfEvents( self, event_type: int, time_delta_s: float ):
        
        with self._lock:
            
            if event_type in self._domain_events_ms:
                
                dead_time = HydrusTime.GetNowMS() - HydrusTime.MillisecondiseS( time_delta_s )
                
                return len( [ 1 for event_ms in self._domain_events_ms[ event_type ] if event_ms > dead_time ] )
                
            else:
                
                return 0
                
            
        
    
    def RegisterDomainEvent( self, event_type: int ):
        
        with self._lock:
            
            if event_type not in self._domain_events_ms:
                
                self._domain_events_ms[ event_type ] = []
                
            
            self._domain_events_ms[ event_type ].append( HydrusTime.GetNowMS() )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_STATUS ] = DomainStatus

