import threading
import typing
import weakref

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusThreading

from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags

class MediaResultCache( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._hash_ids_to_media_results = weakref.WeakValueDictionary()
        self._hashes_to_media_results = weakref.WeakValueDictionary()
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_data' )
        HG.client_controller.sub( self, 'ProcessServiceUpdates', 'service_updates_data' )
        HG.client_controller.sub( self, 'NewForceRefreshTags', 'notify_new_force_refresh_tags_data' )
        HG.client_controller.sub( self, 'NewTagDisplayRules', 'notify_new_tag_display_rules' )
        
    
    def AddMediaResults( self, media_results: typing.Iterable[ ClientMediaResult.MediaResult ] ):
        
        with self._lock:
            
            for media_result in media_results:
                
                hash_id = media_result.GetHashId()
                hash = media_result.GetHash()
                
                self._hash_ids_to_media_results[ hash_id ] = media_result
                self._hashes_to_media_results[ hash ] = media_result
                
            
        
    
    def DropMediaResult( self, hash_id: int, hash: bytes ):
        
        with self._lock:
            
            media_result = self._hash_ids_to_media_results.get( hash_id, None )
            
            if media_result is not None:
                
                del self._hash_ids_to_media_results[ hash_id ]
                
            
            media_result = self._hashes_to_media_results.get( hash, None )
            
            if media_result is not None:
                
                del self._hashes_to_media_results[ hash ]
                
            
        
    
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
                    
                
            
            return ( media_results, missing_hash_ids )
            
        
    
    def HasFile( self, hash_id: int ):
        
        with self._lock:
            
            return hash_id in self._hash_ids_to_media_results
            
        
    
    def NewForceRefreshTags( self ):
        
        # repo sync or tag migration occurred, so we need complete refresh
        
        def do_it( hash_ids ):
            
            for group_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 256 ):
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                hash_ids_to_tags_managers = HG.client_controller.Read( 'force_refresh_tags_managers', group_of_hash_ids )
                
                with self._lock:
                    
                    for ( hash_id, tags_manager ) in hash_ids_to_tags_managers.items():
                        
                        media_result = self._hash_ids_to_media_results.get( hash_id, None )
                        
                        if media_result is not None:
                            
                            media_result.SetTagsManager( tags_manager )
                            
                        
                    
                
            
            HG.client_controller.pub( 'refresh_all_tag_presentation_gui' )
            
        
        with self._lock:
            
            hash_ids = list( self._hash_ids_to_media_results.keys() )
            
        
        HG.client_controller.CallToThread( do_it, hash_ids )
        
    
    def NewTagDisplayRules( self ):
        
        with self._lock:
            
            for media_result in self._hash_ids_to_media_results.values():
                
                media_result.GetTagsManager().NewTagDisplayRules()
                
            
        
        HG.client_controller.pub( 'refresh_all_tag_presentation_gui' )
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        with self._lock:
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
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
                    
                
            
        
