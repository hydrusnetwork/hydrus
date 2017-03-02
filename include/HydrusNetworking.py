import calendar
import collections
import datetime
import httplib
import HydrusConstants as HC
import HydrusData
import HydrusSerialisable
import socket
import ssl
import threading
import time

def ConvertBandwidthRuleToString( rule ):
    
    ( bandwidth_type, time_delta, max_allowed ) = rule
    
    if max_allowed == 0:
        
        return 'No requests currently permitted.'
        
    
    if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
        
        s = HydrusData.ConvertIntToBytes( max_allowed )
        
    elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
        
        s = HydrusData.ConvertIntToPrettyString( max_allowed )
        
    
    if time_delta is None:
        
        s += ' per month'
        
    else:
        
        s += ' per ' + HydrusData.ConvertTimeDeltaToPrettyString( time_delta )
        
    
    return s
    
def GetLocalConnection( port, https = False ):
    
    old_socket = httplib.socket.socket
    
    httplib.socket.socket = socket._socketobject
    
    try:
        
        if https:
            
            context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            
            connection = httplib.HTTPSConnection( '127.0.0.1', port, timeout = 8, context = context )
            
        else:
            
            connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 8 )
            
        
        connection.connect()
        
    finally:
        
        httplib.socket.socket = old_socket
        
    
    return connection
    
class BandwidthRules( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_RULES
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._rules = set()
        
    
    def _GetSerialisableInfo( self ):
        
        return list( self._rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        # tuples converted to lists via json
        
        self._rules = set( ( tuple( rule_list ) for rule_list in serialisable_info ) )
        
    
    def AddRule( self, bandwidth_type, time_delta, max_allowed ):
        
        with self._lock:
            
            rule = ( bandwidth_type, time_delta, max_allowed )
            
            self._rules.add( rule )
            
        
    
    def GetUsageStringsAndGaugeTuples( self, bandwidth_tracker, threshold = 3600 ):
        
        with self._lock:
            
            rows = []
            
            for ( bandwidth_type, time_delta, max_allowed ) in self._rules:
                
                time_is_less_than_threshold = time_delta is not None and time_delta < threshold
                
                if time_is_less_than_threshold or max_allowed == 0:
                    
                    continue
                    
                
                usage = bandwidth_tracker.GetUsage( bandwidth_type, time_delta )
                
                s = 'used '
                
                if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                    
                    s += HydrusData.ConvertValueRangeToBytes( usage, max_allowed )
                    
                elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                    
                    s += HydrusData.ConvertValueRangeToPrettyString( usage, max_allowed ) + ' requests'
                    
                
                if time_delta is None:
                    
                    s += ' this month'
                    
                else:
                    
                    s += ' in the past ' + HydrusData.ConvertTimeDeltaToPrettyString( time_delta )
                    
                
                rows.append( ( s, ( usage, max_allowed ) ) )
                
            
            return rows
        
    
    def GetRules( self ):
        
        with self._lock:
            
            return list( self._rules )
            
        
    
    def Ok( self, bandwidth_tracker ):
        
        with self._lock:
            
            for ( bandwidth_type, time_delta, max_allowed ) in self._rules:
                
                if max_allowed == 0:
                    
                    return False
                    
                
                if bandwidth_tracker.GetUsage( bandwidth_type, time_delta ) > max_allowed:
                    
                    return False
                    
                
            
            return True
            
        

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_RULES ] = BandwidthRules

class BandwidthTracker( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_TRACKER
    SERIALISABLE_VERSION = 1
    
    # I want to track and query using smaller periods even when the total time delta is larger than the next step up to increase granularity
    # for instance, querying minutes for 90 mins time delta is more smooth than watching a juddery sliding two hour window
    MAX_SECONDS_TIME_DELTA = 240
    MAX_MINUTES_TIME_DELTA = 180 * 60
    MAX_HOURS_TIME_DELTA = 72 * 3600
    MAX_DAYS_TIME_DELTA = 31 * 86400
    
    CACHE_MAINTENANCE_TIME_DELTA = 120
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._next_cache_maintenance_timestamp = HydrusData.GetNow() + self.CACHE_MAINTENANCE_TIME_DELTA
        
        self._months_bytes = collections.Counter()
        self._days_bytes = collections.Counter()
        self._hours_bytes = collections.Counter()
        self._minutes_bytes = collections.Counter()
        self._seconds_bytes = collections.Counter()
        
        self._months_requests = collections.Counter()
        self._days_requests = collections.Counter()
        self._hours_requests = collections.Counter()
        self._minutes_requests = collections.Counter()
        self._seconds_requests = collections.Counter()
        
    
    def _GetSerialisableInfo( self ):
        
        dicts_flat = []
        
        for d in ( self._months_bytes, self._days_bytes, self._hours_bytes, self._minutes_bytes, self._seconds_bytes, self._months_requests, self._days_requests, self._hours_requests, self._minutes_requests, self._seconds_requests ):
            
            dicts_flat.append( d.items() )
            
        
        return dicts_flat
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        counters = [ collections.Counter( dict( flat_dict ) ) for flat_dict in serialisable_info ]
        
        self._months_bytes = counters[ 0 ]
        self._days_bytes = counters[ 1 ]
        self._hours_bytes = counters[ 2 ]
        self._minutes_bytes = counters[ 3 ]
        self._seconds_bytes = counters[ 4 ]
        
        self._months_requests = counters[ 5 ]
        self._days_requests = counters[ 6 ]
        self._hours_requests = counters[ 7 ]
        self._minutes_requests = counters[ 8 ]
        self._seconds_requests = counters[ 9 ]
        
    
    def _GetMonthTime( self, dt ):
        
        ( year, month ) = ( dt.year, dt.month )
        
        month_dt = datetime.datetime( year, month, 1 )
        
        month_time = calendar.timegm( month_dt.timetuple() )
        
        return month_time
        
    
    def _GetTimes( self, dt ):
        
        # collapse each time portion to the latest timestamp it covers
        
        ( year, month, day, hour, minute ) = ( dt.year, dt.month, dt.day, dt.hour, dt.minute )
        
        month_dt = datetime.datetime( year, month, 1 )
        day_dt = datetime.datetime( year, month, day )
        hour_dt = datetime.datetime( year, month, day, hour )
        minute_dt = datetime.datetime( year, month, day, hour, minute )
        
        month_time = calendar.timegm( month_dt.timetuple() )
        day_time = calendar.timegm( day_dt.timetuple() )
        hour_time = calendar.timegm( hour_dt.timetuple() )
        minute_time = calendar.timegm( minute_dt.timetuple() )
        
        second_time = calendar.timegm( dt.timetuple() )
        
        return ( month_time, day_time, hour_time, minute_time, second_time )
        
    
    def _GetUsage( self, bandwidth_type, time_delta ):
        
        if time_delta is None:
            
            dt = datetime.datetime.utcnow()
            
            month_time = self._GetMonthTime( dt )
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                return self._months_bytes[ month_time ]
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                return self._months_requests[ month_time ]
                
            
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            if time_delta < self.MAX_SECONDS_TIME_DELTA:
                
                window = 1
                counter = self._seconds_bytes
                
            elif time_delta < self.MAX_MINUTES_TIME_DELTA:
                
                window = 60
                counter = self._minutes_bytes
                
            elif time_delta < self.MAX_HOURS_TIME_DELTA:
                
                window = 3600
                counter = self._hours_bytes
                
            else:
                
                window = 86400
                counter = self._days_bytes
                
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            if time_delta < self.MAX_SECONDS_TIME_DELTA:
                
                window = 1
                counter = self._seconds_requests
                
            elif time_delta < self.MAX_MINUTES_TIME_DELTA:
                
                window = 60
                counter = self._minutes_requests
                
            elif time_delta < self.MAX_HOURS_TIME_DELTA:
                
                window = 3600
                counter = self._hours_requests
                
            else:
                
                window = 86400
                counter = self._days_requests
                
            
        
        # we need the 'window' because this tracks backets from the first timestamp and we want to include if since lands anywhere in the bracket
        
        time_delta += window
        
        since = HydrusData.GetNow() - time_delta
        
        self._MaintainCache()
        
        return sum( ( value for ( key, value ) in counter.items() if key >= since ) )
        
    
    def _MaintainCache( self ):
        
        if HydrusData.TimeHasPassed( self._next_cache_maintenance_timestamp ):
            
            now = HydrusData.GetNow()
            
            oldest_second = now - self.MAX_SECONDS_TIME_DELTA
            oldest_minute = now - self.MAX_MINUTES_TIME_DELTA
            oldest_hour = now - self.MAX_HOURS_TIME_DELTA
            oldest_day = now - self.MAX_DAYS_TIME_DELTA
            
            def clear_counter( counter, timestamp ):
                
                bad_keys = [ key for key in counter.keys() if key < timestamp ]
                
                for bad_key in bad_keys:
                    
                    del counter[ bad_key ]
                    
                
            
            clear_counter( self._days_bytes, oldest_day )
            clear_counter( self._days_requests, oldest_day )
            clear_counter( self._hours_bytes, oldest_hour )
            clear_counter( self._hours_requests, oldest_hour )
            clear_counter( self._minutes_bytes, oldest_minute )
            clear_counter( self._minutes_requests, oldest_minute )
            clear_counter( self._seconds_bytes, oldest_second )
            clear_counter( self._seconds_requests, oldest_second )
            
            self._next_cache_maintenance_timestamp = HydrusData.GetNow() + self.CACHE_MAINTENANCE_TIME_DELTA
            
        
    
    def GetCurrentMonthSummary( self ):
        
        num_bytes = self._GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
        num_requests = self._GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None )
        
        return 'used ' + HydrusData.ConvertIntToBytes( num_bytes ) + ' in ' + HydrusData.ConvertIntToPrettyString( num_requests ) + ' requests this month'
        
    
    def GetUsage( self, bandwidth_type, time_delta ):
        
        with self._lock:
            
            return self._GetUsage( bandwidth_type, time_delta )
            
        
    
    def RequestMade( self, num_bytes ):
        
        with self._lock:
            
            dt = datetime.datetime.utcnow()
            
            ( month_time, day_time, hour_time, minute_time, second_time ) = self._GetTimes( dt )
            
            self._months_bytes[ month_time ] += num_bytes
            self._months_requests[ month_time ] += 1
            
            self._days_bytes[ day_time ] += num_bytes
            self._days_requests[ day_time ] += 1
            
            self._hours_bytes[ hour_time ] += num_bytes
            self._hours_requests[ hour_time ] += 1
            
            self._minutes_bytes[ minute_time ] += num_bytes
            self._minutes_requests[ minute_time ] += 1
            
            self._seconds_bytes[ second_time ] += num_bytes
            self._seconds_requests[ second_time ] += 1
            
            self._MaintainCache()
            
        

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_TRACKER ] = BandwidthTracker
