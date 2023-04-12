import datetime
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusSerialisable

try:
    
    from dateutil.relativedelta import relativedelta
    
    DATEUTIL_OK = True
    
except:
    
    DATEUTIL_OK = False
    

from hydrus.core import HydrusData

def CalendarToTimestamp( dt: datetime.datetime ) -> int:
    
    try:
        
        # mktime is local calendar time to timestamp, so this is client specific
        timestamp = int( time.mktime( dt.timetuple() ) )
        
    except:
        
        timestamp = HydrusData.GetNow()
        
    
    return timestamp
    

def CalendarDelta( dt: datetime.datetime, month_delta = 0, day_delta = 0 ) -> datetime.datetime:
    
    if DATEUTIL_OK:
        
        delta = relativedelta( months = month_delta, days = day_delta )
        
        return dt + delta
        
    else:
        
        total_days = ( 30 * month_delta ) + day_delta
        
        return dt + datetime.timedelta( days = total_days )
        
    

def GetDateTime( year: int, month: int, day: int, hour: int, minute: int ) -> datetime.datetime:
    
    return datetime.datetime( year, month, day, hour, minute )
    
def MergeModifiedTimes( existing_timestamp: typing.Optional[ int ], new_timestamp: typing.Optional[ int ] ) -> typing.Optional[ int ]:
    
    if not TimestampIsSensible( existing_timestamp ):
        
        existing_timestamp = None
        
    
    if not TimestampIsSensible( new_timestamp ):
        
        new_timestamp = None
        
    
    if ShouldUpdateModifiedTime( existing_timestamp, new_timestamp ):
        
        return new_timestamp
        
    else:
        
        return existing_timestamp
        
    

def ShouldUpdateModifiedTime( existing_timestamp: int, new_timestamp: typing.Optional[ int ] ) -> bool:
    
    if not TimestampIsSensible( new_timestamp ):
        
        return False
        
    
    if not TimestampIsSensible( existing_timestamp ):
        
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
