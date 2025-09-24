import collections.abc
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.networking import ClientNetworking
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingJobs

SUBSCRIPTION_BANDWIDTH_OK_WINDOW = 90

def GenerateQueryLogContainerName() -> str:
    
    return HydrusData.GenerateKey().hex()
    
class SubscriptionQueryLogContainer( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER
    SERIALISABLE_NAME = 'Subscription Query Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        super().__init__( name )
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        return ( serialisable_gallery_seed_log, serialisable_file_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_seed_log, serialisable_file_seed_cache ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def SetFileSeedCache( self, file_seed_cache: ClientImportFileSeeds.FileSeedCache ):
        
        self._file_seed_cache = file_seed_cache
        
    
    def SetGallerySeedLog( self, gallery_seed_log: ClientImportGallerySeeds.GallerySeedLog ):
        
        self._gallery_seed_log = gallery_seed_log
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER ] = SubscriptionQueryLogContainer

LOG_CONTAINER_SYNCED = 0
LOG_CONTAINER_UNSYNCED = 1
LOG_CONTAINER_MISSING = 2

class SubscriptionQueryHeader( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_HEADER
    SERIALISABLE_NAME = 'Subscription Query Summary'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        super().__init__()
        
        self._query_log_container_name = GenerateQueryLogContainerName()
        self._query_text = 'query'
        self._display_name = None
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._checker_status = ClientImporting.CHECKER_STATUS_OK
        self._query_log_container_status = LOG_CONTAINER_UNSYNCED
        self._file_seed_cache_status = ClientImportFileSeeds.FileSeedCacheStatus()
        self._file_seed_cache_compaction_number = 250
        self._gallery_seed_log_compaction_number = 100
        self._tag_import_options = TagImportOptions.TagImportOptions()
        self._raw_file_velocity = ( 0, 1 )
        self._pretty_file_velocity = 'unknown'
        self._example_file_seed = None
        self._example_gallery_seed = None
        
    
    def _DomainOK( self, domain_manager: ClientNetworkingDomain.NetworkDomainManager, example_url: typing.Optional[ str ] ):
        
        if example_url is None:
            
            domain_ok = True
            
        else:
            
            domain_ok = domain_manager.DomainOK( example_url )
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "{}" domain test. Domain ok: {}'.format( self._GetHumanName(), domain_ok ) )
            
        
        return domain_ok
        
    
    def _GenerateNetworkJobFactory( self, subscription_name: str ):
        
        subscription_key = self._GenerateNetworkJobSubscriptionKey( subscription_name )
        
        def network_job_factory( *args, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, *args, **kwargs )
            
            network_job.OverrideBandwidth( 30 )
            
            return network_job
            
        
        return network_job_factory
        
    
    def _GenerateNetworkJobSubscriptionKey( self, subscription_name: str ):
        
        return '{}: {}'.format( subscription_name, self._GetHumanName() )
        
    
    def _GetExampleFileURL( self ):
        
        if self._example_file_seed is None or self._example_file_seed.file_seed_type == ClientImportFileSeeds.FILE_SEED_TYPE_HDD:
            
            example_url = None
            
        else:
            
            example_url = self._example_file_seed.file_seed_data
            
        
        return example_url
        
    
    def _GetExampleGalleryURL( self ):
        
        if self._example_gallery_seed is None:
            
            example_url = None
            
        else:
            
            example_url = self._example_gallery_seed.url
            
        
        return example_url
        
    
    def _GetExampleNetworkContexts( self, example_url: typing.Optional[ str ], subscription_name: str ):
        
        subscription_key = self._GenerateNetworkJobSubscriptionKey( subscription_name )
        
        if example_url is None:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        try: # if the url is borked for some reason
            
            example_nj = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, 'GET', example_url )
            example_network_contexts = example_nj.GetNetworkContexts()
            
        except:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        return example_network_contexts
        
    
    def _GetHumanName( self ) -> str:
        
        if self._display_name is None:
            
            return self._query_text
            
        else:
            
            return self._display_name
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_seed_cache_status = self._file_seed_cache_status.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_example_file_seed = HydrusSerialisable.GetNoneableSerialisableTuple( self._example_file_seed )
        serialisable_example_gallery_seed = HydrusSerialisable.GetNoneableSerialisableTuple( self._example_gallery_seed )
        
        return (
            self._query_log_container_name,
            self._query_text,
            self._display_name,
            self._check_now,
            self._last_check_time,
            self._next_check_time,
            self._paused,
            self._checker_status,
            self._query_log_container_status,
            serialisable_file_seed_cache_status,
            self._file_seed_cache_compaction_number,
            self._gallery_seed_log_compaction_number,
            serialisable_tag_import_options,
            self._raw_file_velocity,
            self._pretty_file_velocity,
            serialisable_example_file_seed,
            serialisable_example_gallery_seed
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._query_log_container_name,
            self._query_text,
            self._display_name,
            self._check_now,
            self._last_check_time,
            self._next_check_time,
            self._paused,
            self._checker_status,
            self._query_log_container_status,
            serialisable_file_seed_cache_status,
            self._file_seed_cache_compaction_number,
            self._gallery_seed_log_compaction_number,
            serialisable_tag_import_options,
            self._raw_file_velocity,
            self._pretty_file_velocity,
            serialisable_example_file_seed,
            serialisable_example_gallery_seed
            ) = serialisable_info
        
        self._file_seed_cache_status = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache_status )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
        try:
            
            self._example_file_seed = HydrusSerialisable.CreateFromNoneableSerialisableTuple( serialisable_example_file_seed )
            
        except:
            
            self._example_file_seed = None
            
        
        try:
            
            self._example_gallery_seed = HydrusSerialisable.CreateFromNoneableSerialisableTuple( serialisable_example_gallery_seed )
            
        except:
            
            self._example_gallery_seed = None
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            (
                query_log_container_name,
                query_text,
                display_name,
                check_now,
                last_check_time,
                next_check_time,
                paused,
                checker_status,
                query_log_container_status,
                serialisable_file_seed_cache_status,
                serialisable_tag_import_options,
                raw_file_velocity,
                pretty_file_velocity,
                serialisable_example_file_seed,
                serialisable_example_gallery_seed
                ) = old_serialisable_info
            
            file_seed_cache_compaction_number = 250
            gallery_seed_log_compaction_number = 100
            
            new_serialisable_info = (
                query_log_container_name,
                query_text,
                display_name,
                check_now,
                last_check_time,
                next_check_time,
                paused,
                checker_status,
                query_log_container_status,
                serialisable_file_seed_cache_status,
                file_seed_cache_compaction_number,
                gallery_seed_log_compaction_number,
                serialisable_tag_import_options,
                raw_file_velocity,
                pretty_file_velocity,
                serialisable_example_file_seed,
                serialisable_example_gallery_seed
                )
            
            return ( 2, new_serialisable_info )
            
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanRetryFailed( self ):
        
        return self._file_seed_cache_status.GetFileSeedCount( CC.STATUS_ERROR ) > 0
        
    
    def CanRetryIgnored( self ):
        
        return self._file_seed_cache_status.GetFileSeedCount( CC.STATUS_VETOED ) > 0
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
        self._next_check_time = 0
        self._checker_status = ClientImporting.CHECKER_STATUS_OK
        
    
    def FileBandwidthOK( self, bandwidth_manager: ClientNetworkingBandwidth.NetworkBandwidthManager, subscription_name: str ):
        
        example_url = self._GetExampleFileURL()
        
        example_network_contexts = self._GetExampleNetworkContexts( example_url, subscription_name )
        
        bandwidth_ok = bandwidth_manager.CanDoWork( example_network_contexts, threshold = SUBSCRIPTION_BANDWIDTH_OK_WINDOW )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._GetHumanName() + '" bandwidth/domain test. Bandwidth ok: {}'.format( bandwidth_ok ) )
            
        
        return bandwidth_ok
        
    
    def FileDomainOK( self, domain_manager: ClientNetworkingDomain.NetworkDomainManager ):
        
        example_url = self._GetExampleFileURL()
        
        return self._DomainOK( domain_manager, example_url )
        
    
    def FileLoginOK( self, network_engine: ClientNetworking.NetworkEngine, subscription_name: str ) -> tuple[ bool, str ]:
        
        reason = 'login looks good!'
        
        if self._example_file_seed is None:
            
            result = True
            
        else:
            
            nj = self._example_file_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( subscription_name ) )
            
            nj.engine = network_engine
            
            if nj.CurrentlyNeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    reason = str( e )
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "{}" pre-work file login test. Login ok: {}. {}'.format( self._GetHumanName(), str( result ), reason ) )
            
        
        return ( result, reason )
        
    
    
    def GalleryDomainOK( self, domain_manager: ClientNetworkingDomain.NetworkDomainManager ):
        
        example_url = self._GetExampleGalleryURL()
        
        return self._DomainOK( domain_manager, example_url )
        
    
    def GalleryLoginOK( self, network_engine: ClientNetworking.NetworkEngine, subscription_name: str ) -> tuple[ bool, str ]:
        
        reason = 'login looks good!'
        
        if self._example_gallery_seed is None:
            
            result = True
            
        else:
            
            nj = self._example_gallery_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( subscription_name ) )
            
            nj.engine = network_engine
            
            if nj.CurrentlyNeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    reason = str( e )
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "{}" pre-work sync login test. Login ok: {}. {}'.format( self._GetHumanName(), str( result ), reason ) )
            
        
        return ( result, reason )
        
    
    def GenerateNetworkJobFactory( self, subscription_name: str ):
        
        return self._GenerateNetworkJobFactory( subscription_name )
        
    
    def GetBandwidthWaitingEstimate( self, bandwidth_manager: ClientNetworkingBandwidth.NetworkBandwidthManager, subscription_name: str ):
        
        example_url = self._GetExampleFileURL()
        
        example_network_contexts = self._GetExampleNetworkContexts( example_url, subscription_name )
        
        ( estimate, bandwidth_network_context ) = bandwidth_manager.GetWaitingEstimateAndContext( example_network_contexts )
        
        if estimate < SUBSCRIPTION_BANDWIDTH_OK_WINDOW:
            
            estimate = 0
            
        
        return estimate
        
    
    def GetCheckerStatus( self ):
        
        return self._checker_status
        
    
    def GetDisplayName( self ):
        
        return self._display_name
        
    
    def GetHumanName( self ):
        
        return self._GetHumanName()
        
    
    def GetFileSeedCacheCompactionNumber( self ) -> int:
        
        return self._file_seed_cache_compaction_number
        
    
    def GetFileSeedCacheStatus( self ):
        
        return self._file_seed_cache_status
        
    
    def GetFileVelocityInfo( self ):
        
        return ( self._raw_file_velocity, self._pretty_file_velocity )
        
    
    def GetLastCheckTime( self ) -> int:
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._file_seed_cache_status.GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._checker_status == ClientImporting.CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        elif self._query_log_container_status == LOG_CONTAINER_UNSYNCED:
            
            return 'will recalculate when next fully loaded'
            
        else:
            
            if HydrusTime.TimeHasPassed( self._next_check_time ):
                
                s = 'imminent'
                
            else:
                
                s = HydrusTime.TimestampToPrettyTimeDelta( self._next_check_time )
                
            
            if self._paused:
                
                s = 'paused, but would be ' + s
                
            
            return s
            
        
    
    def GetNextCheckTime( self ):
        
        return self._next_check_time
        
    
    def GetNextWorkTime( self, bandwidth_manager: ClientNetworkingBandwidth.NetworkBandwidthManager, subscription_name: str ):
        
        if not self.IsExpectingToWorkInFuture():
            
            return None
            
        
        work_times = set()
        
        if self._query_log_container_status == LOG_CONTAINER_UNSYNCED:
            
            work_times.add( 0 )
            
        
        work_times.add( self._next_check_time )
        
        if self.HasFileWorkToDo():
            
            try:
                
                file_bandwidth_estimate = self.GetBandwidthWaitingEstimate( bandwidth_manager, subscription_name )
                
            except:
                
                # this is tricky, but if there is a borked url in here causing trouble, we should let it run and error out immediately tbh
                
                file_bandwidth_estimate = 0
                
            
            if file_bandwidth_estimate == 0:
                
                work_times.add( 0 )
                
            else:
                
                file_work_time = HydrusTime.GetNow() + file_bandwidth_estimate
                
                work_times.add( file_work_time )
                
            
        
        if len( work_times ) == 0:
            
            return None
            
        
        return min( work_times )
        
    
    def GetQueryLogContainerName( self ):
        
        return self._query_log_container_name
        
    
    def GetQueryLogContainerStatus( self ):
        
        return self._query_log_container_status
        
    
    def GetQueryText( self ):
        
        return self._query_text
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasFileWorkToDo( self ):
        
        result = self._file_seed_cache_status.HasWorkToDo()
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "{}" HasFileWorkToDo test. Result is {}.'.format( self._query_text, result ) )
            
        
        return result
        
    
    def IsCheckingNow( self ):
        
        return self._check_now
        
    
    def IsDead( self ):
        
        return self._checker_status == ClientImporting.CHECKER_STATUS_DEAD
        
    
    def IsExpectingToWorkInFuture( self ):
        
        if self.IsPaused() or self.IsDead() or not self.IsLogContainerOK():
            
            return False
            
        
        return True
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsLogContainerOK( self ):
        
        return self._query_log_container_status != LOG_CONTAINER_MISSING
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def IsSyncDue( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query_text + '" IsSyncDue test. Paused/dead/container status is {}/{}/{}, check time due is {}, and check_now is {}.'.format( self._paused, self.IsDead(), self.IsLogContainerOK(), HydrusTime.TimeHasPassed( self._next_check_time ), self._check_now ) )
            
        
        if not self.IsExpectingToWorkInFuture():
            
            return False
            
        
        return HydrusTime.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self, checker_options: ClientImportOptions.CheckerOptions, query_log_container: SubscriptionQueryLogContainer ):
        
        self._last_check_time = HydrusTime.GetNow()
        
        self._check_now = False
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - death_period
        
        gallery_seed_log = query_log_container.GetGallerySeedLog()
        
        if gallery_seed_log.CanCompact( self._gallery_seed_log_compaction_number, compact_before_this_time ):
            
            gallery_seed_log.Compact( self._gallery_seed_log_compaction_number, compact_before_this_time )
            
        
        file_seed_cache = query_log_container.GetFileSeedCache()
        
        if file_seed_cache.CanCompact( self._file_seed_cache_compaction_number, compact_before_this_time ):
            
            file_seed_cache.Compact( self._file_seed_cache_compaction_number, compact_before_this_time )
            
        
        self.SyncToQueryLogContainer( checker_options, query_log_container )
        
    
    def Reset( self, query_log_container: SubscriptionQueryLogContainer ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._checker_status = ClientImporting.CHECKER_STATUS_OK
        self._paused = False
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        query_log_container.SetFileSeedCache( file_seed_cache )
        
        self.UpdateFileStatus( query_log_container )
        
    
    def SetCheckNow( self, check_now: bool ):
        
        self._check_now = check_now
        
    
    def SetCheckerStatus( self, checker_status: int ):
        
        self._checker_status = checker_status
        
    
    def SetDisplayName( self, display_name ):
        
        self._display_name = display_name
        
    
    def SetLastCheckTime( self, last_check_time: int ):
        
        self._last_check_time = last_check_time
        
    
    def SetFileSeedCacheCompactionNumber( self, file_seed_cache_compaction_number: int ):
        
        self._file_seed_cache_compaction_number = file_seed_cache_compaction_number
        
    
    def SetNextCheckTime( self, next_check_time: int ):
        
        self._next_check_time = next_check_time
        
    
    def SetPaused( self, paused: bool ):
        
        self._paused = paused
        
    
    def SetQueryLogContainerName( self, query_log_container_name: str ):
        
        self._query_log_container_name = query_log_container_name
        
        self.SetQueryLogContainerStatus( LOG_CONTAINER_UNSYNCED )
        
    
    def SetQueryLogContainerStatus( self, log_container_status: int, pretty_velocity_override = None ):
        
        self._query_log_container_status = log_container_status
        
        if self._query_log_container_status == LOG_CONTAINER_UNSYNCED:
            
            self._raw_file_velocity = ( 0, 1 )
            
            if pretty_velocity_override is None:
                
                pfv = 'unknown'
                
            else:
                
                pfv = pretty_velocity_override
                
            
            self._pretty_file_velocity = pfv
            
        
    
    def SetQueryText( self, query_text: str ):
        
        self._query_text = query_text
        
    
    def SetTagImportOptions( self, tag_import_options: TagImportOptions.TagImportOptions ):
        
        self._tag_import_options = tag_import_options
        
    
    def SyncToQueryLogContainer( self, checker_options: ClientImportOptions.CheckerOptions, query_log_container: SubscriptionQueryLogContainer ):
        
        gallery_seed_log = query_log_container.GetGallerySeedLog()
        
        self._example_gallery_seed = gallery_seed_log.GetExampleGallerySeed()
        
        self.UpdateFileStatus( query_log_container )
        
        file_seed_cache = query_log_container.GetFileSeedCache()
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._checker_status = ClientImporting.CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( file_seed_cache, self._last_check_time ):
                
                self._checker_status = ClientImporting.CHECKER_STATUS_DEAD
                
                if not self.HasFileWorkToDo():
                    
                    self._paused = True
                    
                
            
            self._next_check_time = checker_options.GetNextCheckTime( file_seed_cache, self._last_check_time )
            
        
        self._raw_file_velocity = checker_options.GetRawCurrentVelocity( file_seed_cache, self._last_check_time )
        self._pretty_file_velocity = checker_options.GetPrettyCurrentVelocity( file_seed_cache, self._last_check_time, no_prefix = True )
        
        self._query_log_container_status = LOG_CONTAINER_SYNCED
        
    
    def UpdateFileStatus( self, query_log_container: SubscriptionQueryLogContainer ):
        
        file_seed_cache = query_log_container.GetFileSeedCache()
        
        self._file_seed_cache_status = file_seed_cache.GetStatus()
        self._example_file_seed = file_seed_cache.GetExampleURLFileSeed()
        
    
    def WantsToResyncWithLogContainer( self ):
        
        return self._query_log_container_status == LOG_CONTAINER_UNSYNCED
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_HEADER ] = SubscriptionQueryHeader

def GenerateQueryHeadersStatus( query_headers: collections.abc.Iterable[ SubscriptionQueryHeader ] ):
    
    fscs = ClientImportFileSeeds.FileSeedCacheStatus()
    
    for query_header in query_headers:
        
        fscs.Merge( query_header.GetFileSeedCacheStatus() )
        
    
    return fscs
    
