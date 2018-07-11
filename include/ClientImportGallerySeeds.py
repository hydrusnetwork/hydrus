import ClientConstants as CC
import ClientImporting
import ClientNetworkingDomain
import ClientParsing
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import itertools
import os
import threading
import time
import traceback
import urlparse

def GenerateGallerySeedLogStatus( statuses_to_counts ):
    
    num_successful = statuses_to_counts[ CC.STATUS_SUCCESSFUL_AND_NEW ]
    num_ignored = statuses_to_counts[ CC.STATUS_VETOED ]
    num_failed = statuses_to_counts[ CC.STATUS_ERROR ]
    num_skipped = statuses_to_counts[ CC.STATUS_SKIPPED ]
    num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
    
    # add some kind of '(512 files found (so far))', which may be asking too much here
    # might be this is complicated and needs to be (partly) done in the object, which will know if it is paused or whatever.
    
    status_strings = []
    
    if num_successful > 0:
        
        s = HydrusData.ToHumanInt( num_successful ) + ' successful'
        
        status_strings.append( s )
        
    
    if num_ignored > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_ignored ) + ' ignored' )
        
    
    if num_failed > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_failed ) + ' failed' )
        
    
    if num_skipped > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_skipped ) + ' skipped' )
        
    
    if num_unknown > 0:
        
        status_strings.append( HydrusData.ToHumanInt( num_unknown ) + ' pending' )
        
    
    status = ', '.join( status_strings )
    
    total = sum( statuses_to_counts.values() )
    
    total_processed = total - num_unknown
    
    return ( status, ( total_processed, total ) )
    
class GallerySeed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED
    SERIALISABLE_NAME = 'Gallery Log Entry'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, url = None, can_generate_more_pages = True ):
        
        if url is None:
            
            url = 'https://nostrils-central.cx/index.php?post=s&tag=hyper_nostrils&page=3'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.url = url
        self._can_generate_more_pages = can_generate_more_pages
        
        self.created = HydrusData.GetNow()
        self.modified = self.created
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._referral_url = None
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.url, self.created ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.url, self._can_generate_more_pages, self.created, self.modified, self.status, self.note, self._referral_url )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.url, self._can_generate_more_pages, self.created, self.modified, self.status, self.note, self._referral_url ) = serialisable_info
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusData.GetNow()
        
    
    def Normalise( self ):
        
        self.url = HG.client_controller.network_engine.domain_manager.NormaliseURL( self.url )
        
    
    def SetReferralURL( self, referral_url ):
        
        self._referral_url = referral_url
        
    
    def SetStatus( self, status, note = '', exception = None ):
        
        if exception is not None:
            
            first_line = HydrusData.ToUnicode( exception ).split( os.linesep )[0]
            
            note = first_line + u'\u2026 (Copy note to see full error)'
            note += os.linesep
            note += HydrusData.ToUnicode( traceback.format_exc() )
            
            HydrusData.Print( 'Error when processing ' + self.url + ' !' )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
    def WorksInNewSystem( self ):
        
        ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.url )
        
        if url_type == HC.URL_TYPE_GALLERY and can_parse:
            
            return True
            
        
        return False
        
    
    def WorkOnURL( self, gallery_seed_log, file_seed_cache, status_hook, title_hook, network_job_factory, network_job_presentation_context_factory, file_import_options, max_new_urls_allowed = None, gallery_urls_seen_before = None ):
        
        if gallery_urls_seen_before is None:
            
            gallery_urls_seen_before = set()
            
        
        # maybe something like 'append urls' vs 'reverse-prepend' for subs or something
        
        # should also take--and populate--a set of urls we have seen this 'run', so we can bomb out if next_gallery_url ends up in some loop
        
        num_urls_added = 0
        added_all_possible_urls = False
        result_404 = False
        
        try:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self.url )
            
            if url_type not in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                raise HydrusExceptions.VetoException( 'Did not recognise this as a gallery or watchable URL!' )
                
            
            if not can_parse:
                
                raise HydrusExceptions.VetoException( 'Did not have a parser for this URL!' )
                
            
            did_substantial_work = True
            
            ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( self.url )
            
            status_hook( 'downloading page' )
            
            if self._referral_url not in ( self.url, url_to_check ):
                
                referral_url = self._referral_url
                
            else:
                
                referral_url = None
                
            
            network_job = network_job_factory( 'GET', url_to_check, referral_url = referral_url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            with network_job_presentation_context_factory( network_job ) as njpc:
                
                network_job.WaitUntilDone()
                
            
            data = network_job.GetContent()
            
            parsing_context = {}
            
            parsing_context[ 'gallery_url' ] = self.url
            parsing_context[ 'url' ] = url_to_check
            
            all_parse_results = parser.Parse( parsing_context, data )
            
            if len( all_parse_results ) == 0:
                
                raise HydrusExceptions.VetoException( 'Could not parse any data!' )
                
            
            title = ClientParsing.GetTitleFromAllParseResults( all_parse_results )
            
            if title is not None:
                
                title_hook( title )
                
            
            ( num_urls_added, num_urls_already_in, added_all_possible_urls ) = ClientImporting.UpdateFileSeedCacheWithAllParseResults( file_seed_cache, all_parse_results, self.url, max_new_urls_allowed )
            
            # harvest file_seeds based on all_parse_results, append them to file_seed cache
            
            status = CC.STATUS_SUCCESSFUL_AND_NEW
            note = 'checked OK - ' + HydrusData.ToHumanInt( num_urls_added ) + ' new urls'
            
            if num_urls_already_in > 0:
                
                note += ' (' + HydrusData.ToHumanInt( num_urls_already_in ) + ' already in)'
                
            
            if self._can_generate_more_pages:
                
                flattened_results = list( itertools.chain( all_parse_results ) )
                
                next_page_urls = ClientParsing.GetURLsFromParseResults( flattened_results, ( HC.URL_TYPE_NEXT, ), only_get_top_priority = True )
                
                if len( next_page_urls ) > 0:
                    
                    next_page_urls = HydrusData.DedupeList( next_page_urls )
                    
                    new_next_page_urls = [ next_page_url for next_page_url in next_page_urls if next_page_url not in gallery_urls_seen_before ]
                    
                    if len( new_next_page_urls ) > 0:
                        
                        gallery_urls_seen_before.update( new_next_page_urls )
                        
                        next_gallery_seeds = [ GallerySeed( next_page_url ) for next_page_url in new_next_page_urls ]
                        
                        gallery_seed_log.AddGallerySeeds( next_gallery_seeds )
                        
                        num_total = len( next_page_urls )
                        num_new = len( new_next_page_urls )
                        
                        if num_new < num_total:
                            
                            num_dupes = num_total - num_new
                            
                            note += ' - ' + HydrusData.ToHumanInt( num_new ) + ' next gallery pages found, but ' + HydrusData.ToHumanInt( num_dupes ) + ' had already been visited this run and were not added'
                            
                        else:
                            
                            note += ' - ' + HydrusData.ToHumanInt( num_new ) + ' next gallery pages found'
                            
                        
                    else:
                        
                        note += ' - ' + HydrusData.ToHumanInt( num_new ) + ' next gallery pages found, but they had already been visited this run and were not added'
                        
                    
                
            
            self.SetStatus( status, note = note )
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = HydrusData.ToUnicode( e )
            
            self.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                status_hook( 'cancelled!' )
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_VETOED
            note = '404'
            
            self.SetStatus( status, note = note )
            
            status_hook( '404' )
            
            time.sleep( 2 )
            
            result_404 = True
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            self.SetStatus( status, exception = e )
            
            status_hook( 'error!' )
            
            time.sleep( 3 )
            
            if isinstance( e, HydrusExceptions.NetworkException ): # so the larger queue can set a delaywork or whatever
                
                raise
                
            
        
        gallery_seed_log.NotifyGallerySeedsUpdated( ( self, ) )
        
        return ( num_urls_added, added_all_possible_urls, result_404 )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED ] = GallerySeed

class GallerySeedLog( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED_LOG
    SERIALISABLE_NAME = 'Gallery Log'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._gallery_seeds = HydrusSerialisable.SerialisableList()
        
        self._gallery_seeds_to_indices = {}
        
        self._gallery_seed_log_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        self._status_cache_generation_time = 0
        
        self._status_dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._gallery_seeds )
        
    
    def _GenerateStatus( self ):
        
        statuses_to_counts = self._GetStatusesToCounts()
        
        self._status_cache = GenerateGallerySeedLogStatus( statuses_to_counts )
        self._status_cache_generation_time = HydrusData.GetNow()
        
        self._status_dirty = False
        
    
    def _GetStatusesToCounts( self ):
        
        statuses_to_counts = collections.Counter()
        
        for gallery_seed in self._gallery_seeds:
            
            statuses_to_counts[ gallery_seed.status ] += 1
            
        
        return statuses_to_counts
        
    
    def _GetGallerySeeds( self, status = None ):
        
        if status is None:
            
            return list( self._gallery_seeds )
            
        else:
            
            return [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status == status ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            return self._gallery_seeds.GetSerialisableTuple()
            
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._gallery_seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
        
    
    def _SetStatusDirty( self ):
        
        self._status_dirty = True
        
    
    def AddGallerySeeds( self, gallery_seeds ):
        
        if len( gallery_seeds ) == 0:
            
            return 0
            
        
        new_gallery_seeds = []
        
        with self._lock:
            
            for gallery_seed in gallery_seeds:
                
                gallery_seed.Normalise()
                
                if gallery_seed in self._gallery_seeds_to_indices:
                    
                    continue
                    
                
                new_gallery_seeds.append( gallery_seed )
                
                self._gallery_seeds.append( gallery_seed )
                
                self._gallery_seeds_to_indices[ gallery_seed ] = len( self._gallery_seeds ) - 1
                
            
            self._SetStatusDirty()
            
        
        self.NotifyGallerySeedsUpdated( new_gallery_seeds )
        
        return len( new_gallery_seeds )
        
    
    def AdvanceGallerySeed( self, gallery_seed ):
        
        with self._lock:
            
            if gallery_seed in self._gallery_seeds_to_indices:
                
                index = self._gallery_seeds_to_indices[ gallery_seed ]
                
                if index > 0:
                    
                    self._gallery_seeds.remove( gallery_seed )
                    
                    self._gallery_seeds.insert( index - 1, gallery_seed )
                    
                
                self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
                
            
        
        self.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
        
    
    def DelayGallerySeed( self, gallery_seed ):
        
        with self._lock:
            
            if gallery_seed in self._gallery_seeds_to_indices:
                
                index = self._gallery_seeds_to_indices[ gallery_seed ]
                
                if index < len( self._gallery_seeds ) - 1:
                    
                    self._gallery_seeds.remove( gallery_seed )
                    
                    self._gallery_seeds.insert( index + 1, gallery_seed )
                    
                
                self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
                
            
        
        self.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
        
    
    def GetNextGallerySeed( self, status ):
        
        with self._lock:
            
            for gallery_seed in self._gallery_seeds:
                
                if gallery_seed.status == status:
                    
                    return gallery_seed
                    
                
            
        
        return None
        
    
    def GetGallerySeedLogKey( self ):
        
        return self._gallery_seed_log_key
        
    
    def GetGallerySeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._gallery_seeds )
                
            else:
                
                for gallery_seed in self._gallery_seeds:
                    
                    if gallery_seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetGallerySeeds( self, status = None ):
        
        with self._lock:
            
            return self._GetGallerySeeds( status )
            
        
    
    def GetGallerySeedIndex( self, gallery_seed ):
        
        with self._lock:
            
            return self._gallery_seeds_to_indices[ gallery_seed ]
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetStatusGenerationTime( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                return HydrusData.GetNow()
                
            
            return self._status_cache_generation_time
            
        
    
    def GetStatusesToCounts( self ):
        
        with self._lock:
            
            return self._GetStatusesToCounts()
            
        
    
    def HasGallerySeed( self, gallery_seed ):
        
        with self._lock:
            
            return gallery_seed in self._gallery_seeds_to_indices
            
        
    
    def HasGalleryURL( self, url ):
        
        search_gallery_seed = GallerySeed( url )
        
        search_gallery_seed.Normalise()
        
        search_url = search_gallery_seed.url
        
        return search_url in ( gallery_seed.url for gallery_seed in self._gallery_seeds )
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seeds ):
        
        with self._lock:
            
            self._SetStatusDirty()
            
        
        HG.client_controller.pub( 'gallery_seed_log_gallery_seeds_updated', self._gallery_seed_log_key, gallery_seeds )
        
    
    def RemoveGallerySeeds( self, gallery_seeds ):
        
        with self._lock:
            
            gallery_seeds_to_delete = set( gallery_seeds )
            
            self._gallery_seeds = HydrusSerialisable.SerialisableList( [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed not in gallery_seeds_to_delete ] )
            
            self._gallery_seeds_to_indices = { gallery_seed : index for ( index, gallery_seed ) in enumerate( self._gallery_seeds ) }
            
            self._SetStatusDirty()
            
        
        self.NotifyGallerySeedsUpdated( gallery_seeds_to_delete )
        
    
    def RemoveGallerySeedsByStatus( self, statuses_to_remove ):
        
        with self._lock:
            
            gallery_seeds_to_delete = [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status in statuses_to_remove ]
            
        
        self.RemoveGallerySeeds( gallery_seeds_to_delete )
        
    
    def RemoveAllButUnknownGallerySeeds( self ):
        
        with self._lock:
            
            gallery_seeds_to_delete = [ gallery_seed for gallery_seed in self._gallery_seeds if gallery_seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveGallerySeeds( gallery_seeds_to_delete )
        
    
    def RetryFailures( self ):
        
        with self._lock:
            
            failed_gallery_seeds = self._GetGallerySeeds( CC.STATUS_ERROR )
            
            for gallery_seed in failed_gallery_seeds:
                
                gallery_seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifyGallerySeedsUpdated( failed_gallery_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._GenerateStatus()
                
            
            ( status, simple_status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_SEED_LOG ] = GallerySeedLog
