import datetime
import time
import typing

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
        
    
    if ShouldUpdateDomainModifiedTime( existing_timestamp, new_timestamp ):
        
        return new_timestamp
        
    else:
        
        return existing_timestamp
        
    

def ShouldUpdateDomainModifiedTime( existing_timestamp: int, new_timestamp: typing.Optional[ int ] ) -> bool:
    
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
    
