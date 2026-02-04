import calendar
import datetime
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers

def DateTimeToPrettyTime( dt: datetime.datetime, include_24h_time = True, include_milliseconds = False ):
    
    if include_24h_time:
        
        phrase = '%Y-%m-%d %H:%M:%S'
        
    else:
        
        phrase = '%Y-%m-%d'
        
    
    try:
        
        result = dt.strftime( phrase )
        
    except Exception as e:
        
        return f'unknown time {dt}'
        
    
    if include_milliseconds:
        
        result = f'{result}.{dt.microsecond // 1000:03}'
        
    
    return result
    

def DateTimeToTimestamp( dt: datetime.datetime ) -> int:
    
    try:
        
        timestamp = int( dt.timestamp() )
        
    except Exception as e:
        
        try:
            
            # ok bros, an important thing about time.mktime and datetime.timestamp is they can't always handle <1970!
            # so we'll do some mickey mouse stuff here and this does work
            
            dt_epoch = datetime.datetime( 1970, 1, 1, tzinfo = datetime.timezone.utc )
            
            # we would want to go dt_local = dt.astimezone(), but we can't do astimezone on a dt with pre-1970 date
            # but we can mess around it. and if an hour of DST is miscalculated fifty years ago, oh well!
            my_current_timezone = datetime.datetime.now().astimezone().tzinfo
            
            dt_local = datetime.datetime(
                year = dt.year,
                month = dt.month,
                day = dt.day,
                hour = dt.hour,
                minute = dt.minute,
                second = dt.second,
                microsecond = dt.microsecond,
                tzinfo = my_current_timezone
            )
            
            time_delta = dt_local - dt_epoch
            
            timestamp = int( time_delta.total_seconds() )
            
        except Exception as e:
            
            timestamp = GetNow()
            
        
    
    return timestamp
    

def DateTimeToTimestampMS( dt: datetime.datetime ) -> float:
    
    return MillisecondiseS( DateTimeToTimestamp( dt ) ) + ( dt.microsecond // 1000 )
    

def GetDateTime( year: int, month: int, day: int, hour: int, minute: int ) -> datetime.datetime:
    
    return datetime.datetime( year, month, day, hour, minute )
    

def GetNow():
    
    return int( time.time() )
    

def GetNowFloat():
    
    return time.time()
    

def GetNowMS():
    
    return int( time.time() * 1000 )
    

def GetNowPrecise():
    
    return time.perf_counter()
    

def GetTimeDeltaSinceTime( timestamp ):
    
    time_since = timestamp - GetNow()
    
    result = min( time_since, 0 )
    
    return - result
    

def GetTimeDeltaUntilTime( timestamp ):
    
    time_remaining = timestamp - GetNow()
    
    return max( time_remaining, 0 )
    

def GetTimeDeltaUntilTimeFloat( timestamp ):
    
    time_remaining = timestamp - GetNowFloat()
    
    return max( time_remaining, 0.0 )
    

def GetTimeDeltaUntilTimePrecise( t ):
    
    time_remaining = t - GetNowPrecise()
    
    return max( time_remaining, 0.0 )
    

def MillisecondiseS( time_delta_s: int | float | None ) -> int | None:
    
    return None if time_delta_s is None else int( time_delta_s * 1000 )
    

def SecondiseMS( time_delta_ms: int | float | None ) -> int | None:
    
    return None if time_delta_ms is None else int( time_delta_ms // 1000 )
    

def SecondiseMSFloat( time_delta_ms: int | float | None ) -> float | None:
    
    return None if time_delta_ms is None else time_delta_ms / 1000.0
    

def TimeHasPassed( timestamp ):
    
    if timestamp is None:
        
        return False
        
    
    return GetNow() > timestamp
    

def TimeHasPassedFloat( timestamp ):
    
    return GetNowFloat() > timestamp
    

def TimeHasPassedMS( timestamp_ms ):
    
    if timestamp_ms is None:
        
        return False
        
    
    return GetNowMS() > timestamp_ms
    

def TimeHasPassedPrecise( precise_timestamp ):
    
    return GetNowPrecise() > precise_timestamp
    

def TimeUntil( timestamp ):
    
    return timestamp - GetNow()
    

def CalendarDeltaToDateTime( years : int, months : int, days : int, hours : int ) -> datetime.datetime:
    
    now = datetime.datetime.now()
    
    day_and_hour_delta = datetime.timedelta( days = days, hours = hours )
    
    result = now - day_and_hour_delta
    
    new_year = result.year - years
    new_month = result.month - months
    
    while new_month < 1:
        
        new_year -= 1
        new_month += 12
        
    
    while new_month > 12:
        
        new_year += 1
        new_month -= 12
        
    
    try:
        
        dayrange = calendar.monthrange( new_year, new_month )
        
    except Exception as e:
        
        dayrange = ( 0, 30 )
        
    
    new_day = min( dayrange[1], result.day )
    
    result = datetime.datetime(
        year = new_year,
        month = new_month,
        day = new_day,
        hour = result.hour,
        minute = result.minute,
        second = result.second
    )
    
    return result
    

def CalendarDeltaToRoughDateTimeTimeDelta( years : int, months : int, days : int, hours : int ) -> datetime.timedelta:
    
    return datetime.timedelta( days = days + ( months * ( 365.25 / 12 ) ) + ( years * 365.25 ), hours = hours )
    

def TimeDeltaToPrettyTimeDelta( seconds: float, show_seconds = True, no_bigger_than_days = False ):
    
    if seconds is None:
        
        return 'per month'
        
    
    if seconds == 0:
        
        return '0 seconds'
        
    
    if seconds < 0:
        
        negative = True
        seconds = abs( seconds )
        
    else:
        
        negative = False
        
    
    if seconds >= 60:
        
        seconds = int( seconds )
        
        MINUTE = 60
        HOUR = 60 * MINUTE
        DAY = 24 * HOUR
        YEAR = 365.25 * DAY
        MONTH = YEAR / 12
        
        lines = []
        
        if not no_bigger_than_days:
            
            lines.append( ( 'year', YEAR ) )
            lines.append( ( 'month', MONTH ) )
            
        
        lines.append( ( 'day', DAY ) )
        lines.append( ( 'hour', HOUR ) )
        lines.append( ( 'minute', MINUTE ) )
        
        if show_seconds:
            
            lines.append( ( 'second', 1 ) )
            
        
        result_components = []
        
        for ( time_string, time_delta_s ) in lines:
            
            time_quantity = seconds // time_delta_s
            
            seconds %= time_delta_s
            
            # little rounding thing if you get 364th day with 30 day months
            if time_string == 'month' and time_quantity > 11:
                
                time_quantity = 11
                
            
            if time_quantity > 0:
                
                s = HydrusNumbers.ToHumanInt( time_quantity ) + ' ' + time_string
                
                if time_quantity > 1:
                    
                    s += 's'
                    
                
                result_components.append( s )
                
                if len( result_components ) == 2: # we now have 1 month 2 days
                    
                    break
                    
                
            else:
                
                if len( result_components ) > 0: # something like '1 year' -- in which case we do not care about the days and hours
                    
                    break
                    
                
            
        
        result = ' '.join( result_components )
        
    elif seconds > 1:
        
        if int( seconds ) == seconds:
            
            result = HydrusNumbers.ToHumanInt( seconds ) + ' seconds'
            
        else:
            
            result = '{:.1f} seconds'.format( seconds )
            
        
    elif seconds == 1:
        
        result = '1 second'
        
    else:
        
        ms = seconds * 1000
        
        if ms > 100 or ms % 1 == 0:
            
            result = f'{int( ms )} milliseconds'
            
        elif ms > 10:
            
            result = f'{ms:.1f} milliseconds'
            
        elif ms >= 1:
            
            result = f'{ms:.2f} milliseconds'
            
        else:
            
            result = f'{int( ms * 1000 )} microseconds'
            
        
    
    if negative:
        
        result = '-' + result
        
    
    return result
    

def TimestampMSToDateTime( timestamp_ms, timezone = None ) -> datetime.datetime:
    
    if timezone is None:
        
        timezone = HC.TIMEZONE_LOCAL
        
    
    # ok we run into the <1970 problems again here. time.gmtime may just fail for -12345678
    # therefore we'll meme it up by adding our timestamp as a delta, which works
    # ALSO NOTE YOU CAN MESS UP IN TWENTY WAYS HERE. if you try to do dt.astimezone() on a certain date, you'll either get standard or daylight timezone lmao!
    dt_epoch = datetime.datetime( 1970, 1, 1 )
    
    dt = dt_epoch + datetime.timedelta( milliseconds = timestamp_ms )
    
    if timezone == HC.TIMEZONE_LOCAL:
        
        my_current_timezone = datetime.datetime.now().astimezone().tzinfo
        
        my_offset_timedelta = my_current_timezone.utcoffset( None )
        
        dt += my_offset_timedelta
        
    
    return dt
    

def TimestampToDateTime( timestamp, timezone = None ) -> datetime.datetime:
    
    if timezone is None:
        
        timezone = HC.TIMEZONE_LOCAL
        
    
    # ok we run into the <1970 problems again here. time.gmtime may just fail for -12345678
    # therefore we'll meme it up by adding our timestamp as a delta, which works
    # ALSO NOTE YOU CAN MESS UP IN TWENTY WAYS HERE. if you try to do dt.astimezone() on a certain date, you'll either get standard or daylight timezone lmao!
    dt_epoch = datetime.datetime( 1970, 1, 1 )
    
    dt = dt_epoch + datetime.timedelta( seconds = timestamp )
    
    if timezone == HC.TIMEZONE_LOCAL:
        
        my_current_timezone = datetime.datetime.now().astimezone().tzinfo
        
        my_offset_timedelta = my_current_timezone.utcoffset( None )
        
        dt += my_offset_timedelta
        
    
    return dt
    

def TimestampToPrettyExpires( timestamp ):
    
    if timestamp is None:
        
        return 'does not expire'
        
    
    if timestamp == 0:
        
        return 'unknown expiration'
        
    
    try:
        
        time_delta_string = TimestampToPrettyTimeDelta( timestamp )
        
        if TimeHasPassed( timestamp ):
            
            return 'expired ' + time_delta_string
            
        else:
            return 'expires ' + time_delta_string
            
        
    except Exception as e:
        
        return 'unparseable time {}'.format( timestamp )
        
    

def MillisecondsDurationToPrettyTime( duration_ms: int | None, force_numbers = False ) -> str:
    
    # should this function just be merged into timedeltatoprettytimedelta or something?
    
    if ( duration_ms is None or duration_ms == 0 ) and not force_numbers:
        
        return 'no duration'
        
    
    hours = duration_ms // 3600000
    
    duration_ms = duration_ms % 3600000
    
    minutes = duration_ms // 60000
    
    duration_ms = duration_ms % 60000
    
    seconds = duration_ms // 1000
    
    duration_ms = duration_ms % 1000
    
    if minutes == 1:
        
        minutes_result = '1 minute'
        
    else:
        
        minutes_result = str( minutes ) + ' minutes'
        
    
    if hours > 0:
        
        if hours == 1:
            
            hours_result = '1 hour'
            
        else:
            
            hours_result = str( hours ) + ' hours'
            
        
        return hours_result + ' ' + minutes_result
        
    
    if minutes > 0:
        
        if seconds == 1:
            
            seconds_result = '1 second'
            
        else:
            
            seconds_result = str( seconds ) + ' seconds'
            
        
        return minutes_result + ' ' + seconds_result
        
    
    if seconds > 0:
        
        detailed_seconds = seconds + SecondiseMSFloat( duration_ms )
        
        if int( detailed_seconds ) == detailed_seconds:
            
            detailed_seconds_result = f'{HydrusNumbers.ToHumanInt( detailed_seconds )} seconds'
            
        else:
            
            detailed_seconds_result = '{:.1f} seconds'.format( detailed_seconds )
            
        
        return detailed_seconds_result
        
    
    duration_ms = int( duration_ms )
    
    if duration_ms == 1:
        
        milliseconds_result = '1 millisecond'
        
    else:
        
        milliseconds_result = '{} milliseconds'.format( duration_ms )
        
    
    return milliseconds_result
    

def TimestampMSToPrettyTime( timestamp_ms: int | None, in_utc = False, include_24h_time = True, include_milliseconds = True ) -> str:
    
    if timestamp_ms is None:
        
        return 'unknown time'
        
    
    if in_utc:
        
        timezone = HC.TIMEZONE_UTC
        
    else:
        
        timezone = HC.TIMEZONE_LOCAL
        
    
    # ok this timezone fails when the date of the timestamp we are actually talking about is in summer time and we are in standard time, or _vice versa_
    # might be able to predict timezone better by recreating the dt using our year, month, day tuple and then pulling _that_ TZ, which I am pretty sure is corrected
    # OR just don't convert back and forth so much when handling this garbage, which was the original fix to a system:date predicate shifting by an hour through two conversions
    
    try:
        
        dt = TimestampMSToDateTime( timestamp_ms, timezone = timezone )
        
    except Exception as e:
        
        return 'unparseable ms time {}'.format( timestamp_ms )
        
    
    return DateTimeToPrettyTime( dt, include_24h_time = include_24h_time, include_milliseconds = include_milliseconds )
    

def TimestampToPrettyTime( timestamp: float | None, in_utc = False, include_24h_time = True ) -> str:
    
    if timestamp is None:
        
        return 'unknown time'
        
    
    if in_utc:
        
        timezone = HC.TIMEZONE_UTC
        
    else:
        
        timezone = HC.TIMEZONE_LOCAL
        
    
    # ok this timezone fails when the date of the timestamp we are actually talking about is in summer time and we are in standard time, or _vice versa_
    # might be able to predict timezone better by recreating the dt using our year, month, day tuple and then pulling _that_ TZ, which I am pretty sure is corrected
    # OR just don't convert back and forth so much when handling this garbage, which was the original fix to a system:date predicate shifting by an hour through two conversions
    
    try:
        
        dt = TimestampToDateTime( timestamp, timezone = timezone )
        
    except Exception as e:
        
        return 'unparseable time {}'.format( timestamp )
        
    
    return DateTimeToPrettyTime( dt, include_24h_time = include_24h_time )
    

ALWAYS_SHOW_ISO_TIME_ON_DELTA_CALL = False

def TimestampToPrettyTimeDelta( timestamp, just_now_string = 'now', just_now_threshold = 3, history_suffix = ' ago', show_seconds = True, no_prefix = False, reverse_iso_delta_setting = False, force_no_iso = False ) -> str:
    
    if not force_no_iso and ( ALWAYS_SHOW_ISO_TIME_ON_DELTA_CALL ^ reverse_iso_delta_setting ):
        
        return TimestampToPrettyTime( timestamp )
        
    
    if timestamp is None:
        
        return 'at an unknown time'
        
    
    if not show_seconds:
        
        just_now_threshold = max( just_now_threshold, 60 )
        
    
    try:
        
        time_delta = abs( timestamp - GetNow() )
        
        if time_delta <= just_now_threshold:
            
            return just_now_string
            
        
        time_delta_string = TimeDeltaToPrettyTimeDelta( time_delta, show_seconds = show_seconds )
        
        if TimeHasPassed( timestamp ):
            
            return '{}{}'.format( time_delta_string, history_suffix )
            
        else:
            
            if no_prefix:
                
                return time_delta_string
                
            else:
                
                return 'in ' + time_delta_string
                
            
        
    except Exception as e:
        
        return 'unparseable time {}'.format( timestamp )
        
    

def ValueRangeToScanbarTimestampsMS( value_ms, range_ms ):
    
    value_ms = int( round( value_ms ) )
    
    range_hours = range_ms // 3600000
    value_hours = value_ms // 3600000
    range_minutes = ( range_ms % 3600000 ) // 60000
    value_minutes = ( value_ms % 3600000 ) // 60000
    range_seconds = ( range_ms % 60000 ) // 1000
    value_seconds = ( value_ms % 60000 ) // 1000
    range_ms = range_ms % 1000
    value_ms = value_ms % 1000
    
    if range_hours > 0:
        
        # 0:01:23.033/1:12:57.067
        
        time_phrase = '{}:{:0>2}:{:0>2}.{:0>3}'
        
        args = ( value_hours, value_minutes, value_seconds, value_ms, range_hours, range_minutes, range_seconds, range_ms )
        
    elif range_minutes > 0:
        
        # 01:23.033/12:57.067 or 0:23.033/1:57.067
        
        if range_minutes > 9:
            
            time_phrase = '{:0>2}:{:0>2}.{:0>3}'
            
        else:
            
            time_phrase = '{:0>1}:{:0>2}.{:0>3}'
            
        
        args = ( value_minutes, value_seconds, value_ms, range_minutes, range_seconds, range_ms )
        
    else:
        
        # 23.033/57.067 or 3.033/7.067 or 0.033/0.067
        
        if range_seconds > 9:
            
            time_phrase = '{:0>2}.{:0>3}'
            
        else:
            
            time_phrase = '{:0>1}.{:0>3}'
            
        
        args = ( value_seconds, value_ms, range_seconds, range_ms )
        
    
    full_phrase = '{}/{}'.format( time_phrase, time_phrase )
    
    result = full_phrase.format( *args )
    
    return result
