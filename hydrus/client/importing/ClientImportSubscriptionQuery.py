from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.client import ClientConstants as CC
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing import ClientImportOptions
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

class SubscriptionQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY
    SERIALISABLE_NAME = 'Subscription Query'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, query = 'query text' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._query = query
        self._display_name = None
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._tag_import_options = ClientImportOptions.TagImportOptions()
        
    
    def _GetExampleNetworkContexts( self, subscription_name ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        subscription_key = self.GetNetworkJobSubscriptionKey( subscription_name )
        
        if file_seed is None:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        url = file_seed.file_seed_data
        
        try: # if the url is borked for some reason
            
            example_nj = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, 'GET', url )
            example_network_contexts = example_nj.GetNetworkContexts()
            
        except:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        return example_network_contexts
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = old_serialisable_info
            
            display_name = None
            tag_import_options = ClientImportOptions.TagImportOptions()
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( query, display_name, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
            
            return ( 3, new_serialisable_info )
            
        
    
    def BandwidthOK( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        threshold = 90
        
        bandwidth_ok = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_network_contexts, threshold = threshold )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self.GetHumanName() + '" bandwidth/domain test. Bandwidth ok: {}'.format( bandwidth_ok ) )
            
        
        return bandwidth_ok
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanRetryFailed( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
        
    
    def CanRetryIgnored( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED ) > 0
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        
    
    def DomainOK( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return True
            
        
        url = file_seed.file_seed_data
        
        domain_ok = HG.client_controller.network_engine.domain_manager.DomainOK( url )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self.GetHumanName() + '" domain test. Domain ok: {}'.format( domain_ok ) )
            
        
        return domain_ok
        
    
    def GetBandwidthWaitingEstimate( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        ( estimate, bandwidth_network_context ) = HG.client_controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( example_network_contexts )
        
        return estimate
        
    
    def GetDisplayName( self ):
        
        return self._display_name
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetHumanName( self ):
        
        if self._display_name is None:
            
            return self._query
            
        else:
            
            return self._display_name
            
        
    
    def GetLastChecked( self ):
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._file_seed_cache.GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._status == ClientImporting.CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        else:
            
            if HydrusData.TimeHasPassed( self._next_check_time ):
                
                s = 'imminent'
                
            else:
                
                s = HydrusData.TimestampToPrettyTimeDelta( self._next_check_time )
                
            
            if self._paused:
                
                s = 'paused, but would be ' + s
                
            
            return s
            
        
    
    def GetNextWorkTime( self, subscription_name ):
        
        if self.IsPaused():
            
            return None
            
        
        work_times = set()
        
        if self.HasFileWorkToDo():
            
            try:
                
                file_bandwidth_estimate = self.GetBandwidthWaitingEstimate( subscription_name )
                
            except:
                
                # this is tricky, but if there is a borked url in here causing trouble, we should let it run and error out immediately tbh
                
                file_bandwidth_estimate = 0
                
            
            if file_bandwidth_estimate == 0:
                
                work_times.add( 0 )
                
            else:
                
                file_work_time = HydrusData.GetNow() + file_bandwidth_estimate
                
                work_times.add( file_work_time )
                
            
        
        if not self.IsDead():
            
            work_times.add( self._next_check_time )
            
        
        if len( work_times ) == 0:
            
            return None
            
        
        return min( work_times )
        
    
    def GetNumURLsAndFailed( self ):
        
        return ( self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN ), len( self._file_seed_cache ), self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) )
        
    
    def GetNetworkJobSubscriptionKey( self, subscription_name ):
        
        return subscription_name + ': ' + self.GetHumanName()
        
    
    def GetQueryText( self ):
        
        return self._query
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasFileWorkToDo( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" HasFileWorkToDo test. Next import is ' + repr( file_seed ) + '.' )
            
        
        return file_seed is not None
        
    
    def IsDead( self ):
        
        return self._status == ClientImporting.CHECKER_STATUS_DEAD
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def IsSyncDue( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" IsSyncDue test. Paused/dead status is {}/{}, check time due is {}, and check_now is {}.'.format( self._paused, self.IsDead(), HydrusData.TimeHasPassed( self._next_check_time ), self._check_now ) )
            
        
        if self._paused or self.IsDead():
            
            return False
            
        
        return HydrusData.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self, checker_options: ClientImportOptions.CheckerOptions ):
        
        self._last_check_time = HydrusData.GetNow()
        
        self._check_now = False
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - death_period
        
        if self._gallery_seed_log.CanCompact( compact_before_this_time ):
            
            self._gallery_seed_log.Compact( compact_before_this_time )
            
        
        if self._file_seed_cache.CanCompact( compact_before_this_time ):
            
            self._file_seed_cache.Compact( compact_before_this_time )
            
        
    
    def Reset( self ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._paused = False
        
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def RetryFailures( self ):
        
        self._file_seed_cache.RetryFailures()    
        
    
    def RetryIgnored( self ):
        
        self._file_seed_cache.RetryIgnored()    
        
    
    def SetCheckNow( self, check_now ):
        
        self._check_now = check_now
        
    
    def SetDisplayName( self, display_name ):
        
        self._display_name = display_name
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
    
    def SetQueryAndSeeds( self, query, file_seed_cache, gallery_seed_log ):
        
        self._query = query
        self._file_seed_cache = file_seed_cache
        self._gallery_seed_log = gallery_seed_log
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options
        
    
    def UpdateNextCheckTime( self, checker_options: ClientImportOptions.CheckerOptions ):
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._status = ClientImporting.CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                
                self._status = ClientImporting.CHECKER_STATUS_DEAD
                
                if not self.HasFileWorkToDo():
                    
                    self._paused = True
                    
                
            
            last_next_check_time = self._next_check_time
            
            self._next_check_time = checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time, last_next_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery
