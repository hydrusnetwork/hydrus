import collections.abc

from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

def FilterCurrentTagHashes( service_key: bytes, media_results: collections.abc.Collection[ ClientMediaResult.MediaResult ], tag: str ):
    
    hashes = { media_result.GetHash() for media_result in media_results if tag in media_result.GetTagsManager().GetCurrent( service_key, ClientTags.TAG_DISPLAY_STORAGE ) }
    
    return hashes
    

def FilterNotPreviouslyDeletedTags( service_key: bytes, media_result: ClientMediaResult.MediaResult, tags: collections.abc.Iterable[ str ] ):
    
    deleted_tags = set( media_result.GetTagsManager().GetDeleted( service_key, ClientTags.TAG_DISPLAY_STORAGE ) )
    
    tags = set( tags ).difference( deleted_tags )
    
    return tags
    

def FilterNotPreviouslyDeletedTagHashes( service_key: bytes, media_results: collections.abc.Collection[ ClientMediaResult.MediaResult ], tag: str ):
    
    hashes = { media_result.GetHash() for media_result in media_results if tag not in set( media_result.GetTagsManager().GetDeleted( service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) }
    
    return hashes
    

class CheckerOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CHECKER_OPTIONS
    SERIALISABLE_NAME = 'Checker Timing Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, intended_files_per_check: float = 8, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) ):
        
        super().__init__()
        
        self._intended_files_per_check = intended_files_per_check
        self._never_faster_than = never_faster_than
        self._never_slower_than = never_slower_than
        self._death_file_velocity = death_file_velocity
        
    
    def _GetCurrentFilesVelocity( self, file_seed_cache, last_check_time ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        since = last_check_time - death_time_delta
        
        current_files_found = file_seed_cache.GetNumNewFilesSince( since )
        
        # when a thread is only 30mins old (i.e. first file was posted 30 mins ago), we don't want to calculate based on a longer delete time delta
        # we want next check to be like 30mins from now, not 12 hours
        # so we'll say "5 files in 30 mins" rather than "5 files in 24 hours"
        
        earliest_source_time = file_seed_cache.GetEarliestSourceTime()
        
        if earliest_source_time is None:
            
            current_time_delta = death_time_delta
            
        else:
            
            early_time_delta = max( last_check_time - earliest_source_time, 30 )
            
            current_time_delta = min( early_time_delta, death_time_delta )
            
        
        return ( current_files_found, current_time_delta )
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity ) = serialisable_info
        
    
    def GetDeathFileVelocity( self ):
        
        return self._death_file_velocity
        
    
    def GetDeathFileVelocityPeriod( self ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        death_file_velocity_period = death_time_delta
        
        never_dies = death_files_found == 0
        static_check_timing = self._never_faster_than == self._never_slower_than
        
        if static_check_timing:
            
            death_file_velocity_period = min( death_file_velocity_period, self._never_faster_than * 5 )
            
        
        if never_dies or static_check_timing:
            
            six_months = 6 * 60 * 86400
            
            death_file_velocity_period = min( death_file_velocity_period, six_months )
            
        
        return death_file_velocity_period
        
    
    def GetNextCheckTime( self, file_seed_cache, last_check_time: int ) -> int:
        
        if len( file_seed_cache ) == 0:
            
            if last_check_time == 0:
                
                return 0 # haven't checked yet, so should check immediately
                
            else:
                
                return HydrusTime.GetNow() + self._never_slower_than
                
            
        
        
        if self._never_faster_than == self._never_slower_than:
            
            # fixed check period
            fixed_check_period = self._never_slower_than
            
            # I had a bunch of complicated logic to try and make sure a saturday check stayed on saturday, even if the check was delayed to sunday, and it just wasn't worth the trouble
            # KISS
            
            next_check_time = last_check_time + fixed_check_period
            
            while HydrusTime.TimeHasPassed( next_check_time + fixed_check_period ):
                
                next_check_time += fixed_check_period
                
            
        else:
            
            # dynamic check period
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            if current_files_found == 0:
                
                # this shouldn't typically matter, since a dead checker won't care about next check time
                # so let's just have a nice safe value in case this is ever asked legit
                check_period = self._never_slower_than
                
            else:
                
                approx_time_per_file = current_time_delta // current_files_found
                
                ideal_check_period = self._intended_files_per_check * approx_time_per_file
                
                latest_source_time = file_seed_cache.GetLatestSourceTime()
                
                # safety throttle, but it is legacy and I might remove it. perhaps more confusing than useful
                time_since_latest_file = max( last_check_time - latest_source_time, 30 )
                
                never_faster_than = max( self._never_faster_than, time_since_latest_file * 0.25 )
                
                check_period = int( min( max( never_faster_than, ideal_check_period ), self._never_slower_than ) )
                
            
            next_check_time = last_check_time + check_period
            
        
        return next_check_time
        
    
    def GetPrettyCurrentVelocity( self, file_seed_cache, last_check_time, no_prefix = False ):
        
        if len( file_seed_cache ) == 0:
            
            if last_check_time == 0:
                
                pretty_current_velocity = 'no files yet'
                
            else:
                
                pretty_current_velocity = 'no files, unable to determine velocity'
                
            
        else:
            
            if no_prefix:
                
                pretty_current_velocity = ''
                
            else:
                
                pretty_current_velocity = 'at last check, found '
                
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            pretty_current_velocity += HydrusNumbers.ToHumanInt( current_files_found ) + ' files in previous ' + HydrusTime.TimeDeltaToPrettyTimeDelta( current_time_delta )
            
        
        return pretty_current_velocity
        
    
    def GetRawCurrentVelocity( self, file_seed_cache, last_check_time ):
        
        return self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
        
    
    def GetSummary( self ):
        
        if self._never_faster_than == self._never_slower_than:
            
            timing_statement = 'Checking every ' + HydrusTime.TimeDeltaToPrettyTimeDelta( self._never_faster_than ) + '.'
            
        else:
            
            if self._intended_files_per_check == int( self._intended_files_per_check ):
                
                intended_files_per_check_str = HydrusNumbers.ToHumanInt( self._intended_files_per_check )
                
            else:
                
                # TODO: We should have a nice way of presenting a float to an arbitrary sig figs, with commas; ToHumanFloat
                intended_files_per_check_str = str( self._intended_files_per_check )
                
            
            timing_statement = f'Trying to get {intended_files_per_check_str} files per check, never faster than ' + HydrusTime.TimeDeltaToPrettyTimeDelta( self._never_faster_than ) + ' and never slower than ' + HydrusTime.TimeDeltaToPrettyTimeDelta( self._never_slower_than ) + '.'
            
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        if death_files_found == 0:
            
            death_statement = 'Never stopping.'
            
        else:
            
            death_statement = 'Stopping if file velocity falls below ' + HydrusNumbers.ToHumanInt( death_files_found ) + ' files per ' + HydrusTime.TimeDeltaToPrettyTimeDelta( death_time_delta ) + '.'
            
        
        return timing_statement + '\n' * 2 + death_statement
        
    
    def HasStaticCheckTime( self ):
        
        return self._never_faster_than == self._never_slower_than
        
    
    def NeverDies( self ):
        
        ( death_files_found, death_time_delta ) = self._death_file_velocity
        
        return death_files_found == 0
        
    
    def IsDead( self, file_seed_cache, last_check_time ):
        
        if len( file_seed_cache ) == 0 and last_check_time == 0:
            
            return False
            
        else:
            
            ( current_files_found, current_time_delta ) = self._GetCurrentFilesVelocity( file_seed_cache, last_check_time )
            
            ( death_files_found, deleted_time_delta ) = self._death_file_velocity
            
            current_file_velocity_float = current_files_found / current_time_delta
            death_file_velocity_float = death_files_found / deleted_time_delta
            
            return current_file_velocity_float < death_file_velocity_float
            
        
    
    def ToTuple( self ):
        
        return ( self._intended_files_per_check, self._never_faster_than, self._never_slower_than, self._death_file_velocity )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CHECKER_OPTIONS ] = CheckerOptions
