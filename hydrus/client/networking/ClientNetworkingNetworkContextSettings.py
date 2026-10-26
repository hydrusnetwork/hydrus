import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client.networking import ClientNetworkingConstants as CNC
from hydrus.client.networking import ClientNetworkingContexts

class NetworkContextSettings( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_SETTINGS
    SERIALISABLE_NAME = 'Network Context Settings'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._settings = HydrusSerialisable.SerialisableDictionary()
        self._custom_headers = HydrusSerialisable.SerialisableDictionary()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_settings = self._settings.GetSerialisableTuple()
        serialisable_custom_headers = self._custom_headers.GetSerialisableTuple()
        
        return ( serialisable_settings, serialisable_custom_headers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, serialisable_type_whitelist: set[ int ] | None ):
        
        ( serialisable_settings, serialisable_custom_headers ) = serialisable_info
        
        self._settings = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_settings )
        self._custom_headers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_custom_headers )
        
    
    def ClearSetting( self, setting_type ):
        
        with self._lock:
            
            if setting_type in self._settings:
                
                del self._settings[ setting_type ]
                
            
        
    
    def GetSettingOrRaise( self, setting_type: int ):
        
        # we're going to try raise instead of return None because this guy deals with small types, not a serialisable options object, and an option like 'max number of x' could well be None sometime
        
        with self._lock:
            
            if setting_type in self._settings:
                
                return self._settings[ setting_type ]
                
            else:
                
                if setting_type in CNC.network_context_setting_enum_str_lookup:
                    
                    raise HydrusExceptions.DataMissing( f'This domain settings object does not have an entry for {CNC.network_context_setting_enum_str_lookup[setting_type]}' )
                    
                else:
                    
                    raise NotImplementedError( f'This domain settings object was asked about an invalid domain setting type, here: {setting_type}' )
                    
                
            
        
    
    def IsStub( self ):
        
        with self._lock:
            
            return len( self._settings ) == 0
            
        
    
    def SetSetting( self, setting_type: int, value: object ):
        
        with self._lock:
            
            self._settings[ setting_type ] = value
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_SETTINGS ] = NetworkContextSettings

class NetworkContextStatus( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_STATUS
    SERIALISABLE_NAME = 'Network Context Status'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._events_ms = HydrusSerialisable.SerialisableDictionary()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_events_ms = self._events_ms.GetSerialisableTuple()
        
        return serialisable_events_ms
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, serialisable_type_whitelist: set[ int ] | None ):
        
        serialisable_events_ms = serialisable_info
        
        self._events_ms = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_events_ms )
        
    
    def CleanseOldRecords( self, time_delta_s: float ):
        
        with self._lock:
            
            dead_time = HydrusTime.GetNowMS() - HydrusTime.MillisecondiseS( time_delta_s )
            
            for key in list( self._events_ms.keys() ):
                
                list_of_events_ms = self._events_ms[ key ]
                
                cleansed_list_of_events_ms = [ event_ms for event_ms in list_of_events_ms if event_ms > dead_time ]
                
                if len( cleansed_list_of_events_ms ) > 0:
                    
                    self._events_ms[ key ] = cleansed_list_of_events_ms
                    
                else:
                    
                    del self._events_ms[ key ]
                    
                
            
        
    
    def IsStub( self ):
        
        with self._lock:
            
            return len( self._events_ms ) == 0
            
        
    
    def NumberOfEvents( self, event_type: int, time_delta_s: float ):
        
        with self._lock:
            
            if event_type in self._events_ms:
                
                dead_time = HydrusTime.GetNowMS() - HydrusTime.MillisecondiseS( time_delta_s )
                
                return len( [ 1 for event_ms in self._events_ms[ event_type ] if event_ms > dead_time ] )
                
            else:
                
                return 0
                
            
        
    
    def RegisterDomainEvent( self, event_type: int ):
        
        with self._lock:
            
            if event_type not in self._events_ms:
                
                self._events_ms[ event_type ] = []
                
            
            self._events_ms[ event_type ].append( HydrusTime.GetNowMS() )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_STATUS ] = NetworkContextStatus

# ok this guy is going to eventually eat up all the network_context->headers/errors/proxy/whatever stuff we have and want to do
# primarily, we'll be talking 'domain' NCs here, but we'll stay flexible
class NetworkContextRecord( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_RECORD
    SERIALISABLE_NAME = 'Network Context Record'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self.network_context = ClientNetworkingContexts.NetworkContext.STATICGenerateForDomain( 'example.com' )
        self.status = NetworkContextStatus()
        self.settings = NetworkContextSettings()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_context = self.network_context.GetSerialisableTuple()
        serialisable_status = self.status.GetSerialisableTuple()
        serialisable_settings = self.settings.GetSerialisableTuple()
        
        return ( serialisable_network_context, serialisable_status, serialisable_settings )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, serialisable_type_whitelist: set[ int ] | None ):
        
        ( serialisable_network_context, serialisable_status, serialisable_settings ) = serialisable_info
        
        self.network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
        self.status = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_status )
        self.settings = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_settings )
        
    
    def IsStub( self ):
        
        return self.status.IsStub() and self.settings.IsStub()
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT_RECORD ] = NetworkContextRecord
