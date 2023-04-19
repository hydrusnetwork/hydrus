import calendar
import datetime
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC

try:
    
    from dateutil.relativedelta import relativedelta
    
    DATEUTIL_OK = True
    
except:
    
    DATEUTIL_OK = False
    

from hydrus.core import HydrusData
from hydrus.core import HydrusTime

def CalendarDelta( dt: datetime.datetime, month_delta = 0, day_delta = 0 ) -> datetime.datetime:
    
    if DATEUTIL_OK:
        
        delta = relativedelta( months = month_delta, days = day_delta )
        
        return dt + delta
        
    else:
        
        total_days = ( 30 * month_delta ) + day_delta
        
        return dt + datetime.timedelta( days = total_days )
        
    

def MergeModifiedTimes( existing_timestamp: typing.Optional[ int ], new_timestamp: typing.Optional[ int ] ) -> typing.Optional[ int ]:
    
    if ShouldUpdateModifiedTime( existing_timestamp, new_timestamp ):
        
        return new_timestamp
        
    else:
        
        return existing_timestamp
        
    

def ShouldUpdateModifiedTime( existing_timestamp: int, new_timestamp: typing.Optional[ int ] ) -> bool:
    
    if new_timestamp is None:
        
        return False
        
    
    if existing_timestamp is None:
        
        return True
        
    
    # only go backwards, in general
    if new_timestamp >= existing_timestamp:
        
        return False
        
    
    return True
    

def TimestampIsSensible( timestamp: typing.Optional[ int ] ) -> bool:
    
    if timestamp is None:
        
        return False
        
    
    # assume anything too early is a meme and a timestamp parsing conversion error
    if timestamp <= 86400 * 7:
        
        return False
        
    
    return True
    

def TimestampToPrettyTimeDelta( timestamp, just_now_string = 'just now', just_now_threshold = 3, history_suffix = ' ago', show_seconds = True, no_prefix = False ):
    
    if HG.client_controller.new_options.GetBoolean( 'always_show_iso_time' ):
        
        return HydrusTime.TimestampToPrettyTime( timestamp )
        
    else:
        
        return HydrusTime.BaseTimestampToPrettyTimeDelta( timestamp, just_now_string = just_now_string, just_now_threshold = just_now_threshold, history_suffix = history_suffix, show_seconds = show_seconds, no_prefix = no_prefix )
        
    

HydrusTime.TimestampToPrettyTimeDelta = TimestampToPrettyTimeDelta

REAL_SIMPLE_TIMESTAMP_TYPES = {
    HC.TIMESTAMP_TYPE_ARCHIVED,
    HC.TIMESTAMP_TYPE_MODIFIED_FILE
}

SIMPLE_TIMESTAMP_TYPES = {
    HC.TIMESTAMP_TYPE_ARCHIVED,
    HC.TIMESTAMP_TYPE_MODIFIED_FILE,
    HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE
}

FILE_SERVICE_TIMESTAMP_TYPES = {
    HC.TIMESTAMP_TYPE_IMPORTED,
    HC.TIMESTAMP_TYPE_DELETED,
    HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED
}

class TimestampData( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TIMESTAMP_DATA
    SERIALISABLE_NAME = 'Timestamp Data'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, timestamp_type = None, location = None, timestamp = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.timestamp_type = timestamp_type
        self.location = location
        self.timestamp = timestamp
        
    
    def __eq__( self, other ):
        
        if isinstance( other, TimestampData ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.timestamp_type, self.location, self.timestamp ).__hash__()
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        if self.timestamp_type in FILE_SERVICE_TIMESTAMP_TYPES:
            
            serialisable_location = self.location.hex()
            
        else:
            
            serialisable_location = self.location # str, int, or None
            
        
        return ( self.timestamp_type, serialisable_location, self.timestamp )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.timestamp_type, serialisable_location, self.timestamp ) = serialisable_info
        
        if self.timestamp_type in FILE_SERVICE_TIMESTAMP_TYPES:
            
            self.location = bytes.fromhex( serialisable_location )
            
        else:
            
            self.location = serialisable_location
            
        
    
    def ToString( self ) -> str:
        
        if self.timestamp_type in SIMPLE_TIMESTAMP_TYPES:
            
            type_base = HC.timestamp_type_str_lookup[ self.timestamp_type ]
            
        else:
            
            if self.timestamp_type in FILE_SERVICE_TIMESTAMP_TYPES:
                
                try:
                    
                    service_string = HG.client_controller.services_manager.GetName( self.location )
                    
                except:
                    
                    service_string = 'unknown service'
                    
                
                type_base = '"{}" {}'.format( service_string, HC.timestamp_type_str_lookup[ self.timestamp_type ] )
                
            elif self.timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
                
                type_base = '{} {}'.format( CC.canvas_type_str_lookup[ self.location ], HC.timestamp_type_str_lookup[ self.timestamp_type ] )
                
            elif self.timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
                
                type_base = '"{}" {}'.format( self.location, HC.timestamp_type_str_lookup[ self.timestamp_type ] )
                
            else:
                
                type_base = 'unknown timestamp type'
                
            
        
        if self.timestamp is None:
            
            # we are a stub, type summary is appropriate
            return type_base
            
        else:
            
            return '{}: {}'.format( type_base, HydrusTime.TimestampToPrettyTime( self.timestamp ) )
            
        
    
    
    @staticmethod
    def STATICArchivedTime( timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_ARCHIVED, timestamp = timestamp )
        
    
    @staticmethod
    def STATICAggregateModifiedTime( timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE, timestamp = timestamp )
        
    
    @staticmethod
    def STATICDeletedTime( service_key: bytes, timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_DELETED, location = service_key, timestamp = timestamp )
        
    
    @staticmethod
    def STATICDomainModifiedTime( domain: str, timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = domain, timestamp = timestamp )
        
    
    @staticmethod
    def STATICFileModifiedTime( timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_FILE, timestamp = timestamp )
        
    
    @staticmethod
    def STATICImportedTime( service_key: bytes, timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_IMPORTED, location = service_key, timestamp = timestamp )
        
    
    @staticmethod
    def STATICLastViewedTime( canvas_type: int, timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_LAST_VIEWED, location = canvas_type, timestamp = timestamp )
        
    
    @staticmethod
    def STATICPreviouslyImportedTime( service_key: bytes, timestamp: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, location = service_key, timestamp = timestamp )
        
    
    @staticmethod
    def STATICSimpleStub( timestamp_type: int ) -> "TimestampData":
        
        return TimestampData( timestamp_type = timestamp_type )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TIMESTAMP_DATA ] = TimestampData
