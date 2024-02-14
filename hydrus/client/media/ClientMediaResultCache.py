import threading
import typing
import weakref

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusThreading

from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.caches import ClientCachesBase

class MediaResultCacheContainer( ClientCachesBase.CacheableObject ):
    
    def __init__( self, media_result ):
        
        self._media_result = media_result
        
    
    def GetEstimatedMemoryFootprint( self ) -> int:
        
        return 1
        
    

class MediaResultCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._hash_ids_to_media_results = weakref.WeakValueDictionary()
        self._hashes_to_media_results = weakref.WeakValueDictionary()
        
        # ok this is a bit of an experiment, it may be a failure and just add overhead for no great reason. it force-keeps the most recent fetched media results for two minutes
        # this means that if a user refreshes a search and the existing media result handles briefly go to zero...
        # or if the client api makes repeated requests on the same media results...
        # then that won't be a chance for the weakvaluedict to step in. we'll keep this scratchpad of stuff
        self._fifo_timeout_cache = ClientCachesBase.DataCache( CG.client_controller, 'media result cache', 2048, 120 )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_data' )
        CG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        CG.client_controller.sub( self, 'NewForceRefreshTags', 'notify_new_force_refresh_tags_data' )
        CG.client_controller.sub( self, 'NewTagDisplayRules', 'notify_new_tag_display_rules' )
        
    
    def AddMediaResults( self, media_results: typing.Iterable[ ClientMediaResult.MediaResult ] ):
        
        with self._lock:
            
            for media_result in media_results:
                
                hash_id = media_result.GetHashId()
                hash = media_result.GetHash()
                
                self._hash_ids_to_media_results[ hash_id ] = media_result
                self._hashes_to_media_results[ hash ] = media_result
                
                self._fifo_timeout_cache.AddData( hash_id, MediaResultCacheContainer( media_result ) )
                
            
        
    
    def DropMediaResult( self, hash_id: int, hash: bytes ):
        
        with self._lock:
            
            media_result = self._hash_ids_to_media_results.get( hash_id, None )
            
            if media_result is not None:
                
                del self._hash_ids_to_media_results[ hash_id ]
                
            
            media_result = self._hashes_to_media_results.get( hash, None )
            
            if media_result is not None:
                
                del self._hashes_to_media_results[ hash ]
                
            
            self._fifo_timeout_cache.DeleteData( hash_id )
            
        
    
    def FilterFiles( self, hash_ids: typing.Collection[ int ] ):
        
        with self._lock:
            
            return { hash_id for hash_id in hash_ids if hash_id in self._hash_ids_to_media_results }
            
        
    
    def FilterFilesWithTags( self, tags: typing.Collection[ str ] ):
        
        with self._lock:
            
            return { hash_id for ( hash_id, media_result ) in self._hash_ids_to_media_results.items() if media_result.GetTagsManager().HasAnyOfTheseTags( tags, ClientTags.TAG_DISPLAY_STORAGE ) }
            
        
    
    def GetMediaResultsAndMissing( self, hash_ids: typing.Iterable[ int ] ):
        
        with self._lock:
            
            media_results = []
            missing_hash_ids = []
            
            for hash_id in hash_ids:
                
                media_result = self._hash_ids_to_media_results.get( hash_id, None )
                
                if media_result is None:
                    
                    missing_hash_ids.append( hash_id )
                    
                else:
                    
                    media_results.append( media_result )
                    
                    self._fifo_timeout_cache.TouchKey( hash_id )
                    
                
            
            return ( media_results, missing_hash_ids )
            
        
    
    def HasFile( self, hash_id: int ):
        
        with self._lock:
            
            return hash_id in self._hash_ids_to_media_results
            
        
    
    def NewForceRefreshTags( self ):
        
        # repo sync or tag migration occurred, so we need complete refresh
        
        def do_it( hash_ids ):
            
            for group_of_hash_ids in HydrusLists.SplitListIntoChunks( hash_ids, 256 ):
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                hash_ids_to_tags_managers = CG.client_controller.Read( 'force_refresh_tags_managers', group_of_hash_ids )
                
                with self._lock:
                    
                    for ( hash_id, tags_manager ) in hash_ids_to_tags_managers.items():
                        
                        media_result = self._hash_ids_to_media_results.get( hash_id, None )
                        
                        if media_result is not None:
                            
                            media_result.SetTagsManager( tags_manager )
                            
                        
                    
                
            
            CG.client_controller.pub( 'refresh_all_tag_presentation_gui' )
            
        
        with self._lock:
            
            hash_ids = list( self._hash_ids_to_media_results.keys() )
            
        
        CG.client_controller.CallToThread( do_it, hash_ids )
        
    
    def NewTagDisplayRules( self ):
        
        with self._lock:
            
            for media_result in self._hash_ids_to_media_results.values():
                
                media_result.GetTagsManager().NewTagDisplayRules()
                
            
        
        CG.client_controller.pub( 'refresh_all_tag_presentation_gui' )
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        with self._lock:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    for hash in hashes:
                        
                        media_result = self._hashes_to_media_results.get( hash, None )
                        
                        if media_result is not None:
                            
                            media_result.ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        with self._lock:
            
            for ( service_key, service_updates ) in service_keys_to_service_updates.items():
                
                for service_update in service_updates:
                    
                    ( action, row ) = service_update.ToTuple()
                    
                    if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                        
                        for media_result in self._hash_ids_to_media_results.values():
                            
                            if action == HC.SERVICE_UPDATE_DELETE_PENDING:
                                
                                media_result.DeletePending( service_key )
                                
                            elif action == HC.SERVICE_UPDATE_RESET:
                                
                                media_result.ResetService( service_key )
                                
                            
                        
                    
                
            
        
    
    def SilentlyTakeNewTagsManagers( self, hash_ids_to_tags_managers ):
        
        with self._lock:
            
            for ( hash_id, tags_manager ) in hash_ids_to_tags_managers.items():
                
                media_result = self._hash_ids_to_media_results.get( hash_id, None )
                
                if media_result is not None:
                    
                    media_result.SetTagsManager( tags_manager )
                    
                
            
        
