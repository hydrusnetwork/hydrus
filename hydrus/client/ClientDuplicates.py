import collections
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientThreading
from hydrus.client.metadata import ClientTags

class DuplicatesManager( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        DuplicatesManager.my_instance = self
        
        self._similar_files_maintenance_status = None
        self._currently_refreshing_maintenance_numbers = False
        self._refresh_maintenance_numbers = True
        
        self._currently_doing_potentials_search = False
        
        self._lock = threading.Lock()
        
    
    @staticmethod
    def instance() -> 'DuplicatesManager':
        
        if DuplicatesManager.my_instance is None:
            
            DuplicatesManager()
            
        
        return DuplicatesManager.my_instance
        
    
    def GetMaintenanceNumbers( self ):
        
        with self._lock:
            
            if self._refresh_maintenance_numbers and not self._currently_refreshing_maintenance_numbers:
                
                self._refresh_maintenance_numbers = False
                self._currently_refreshing_maintenance_numbers = True
                
                HG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
                
                HG.client_controller.CallToThread( self.THREADRefreshMaintenanceNumbers )
                
            
            return ( self._similar_files_maintenance_status, self._currently_refreshing_maintenance_numbers, self._currently_doing_potentials_search )
            
        
    
    def RefreshMaintenanceNumbers( self ):
        
        with self._lock:
            
            self._refresh_maintenance_numbers = True
            
            HG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
        
    
    def NotifyNewPotentialsSearchNumbers( self ):
        
        HG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
        
    
    def StartPotentialsSearch( self ):
        
        with self._lock:
            
            if self._currently_doing_potentials_search or self._similar_files_maintenance_status is None:
                
                return
                
            
            self._currently_doing_potentials_search = True
            
            HG.client_controller.CallToThreadLongRunning( self.THREADSearchPotentials )
            
        
    
    def THREADRefreshMaintenanceNumbers( self ):
        
        try:
            
            similar_files_maintenance_status = HG.client_controller.Read( 'similar_files_maintenance_status' )
            
            with self._lock:
                
                self._similar_files_maintenance_status = similar_files_maintenance_status
                
                if self._refresh_maintenance_numbers:
                    
                    self._refresh_maintenance_numbers = False
                    
                    HG.client_controller.CallToThread( self.THREADRefreshMaintenanceNumbers )
                    
                else:
                    
                    self._currently_refreshing_maintenance_numbers = False
                    self._refresh_maintenance_numbers = False
                    
                
                HG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
                
            
        except:
            
            self._currently_refreshing_maintenance_numbers = False
            HG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
            raise
            
        
    
    def THREADSearchPotentials( self ):
        
        try:
            
            search_distance = HG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            with self._lock:
                
                if self._similar_files_maintenance_status is None:
                    
                    return
                    
                
                searched_distances_to_count = self._similar_files_maintenance_status
                
                total_num_files = sum( searched_distances_to_count.values() )
                
                num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
                
                all_files_searched = num_searched >= total_num_files
                
                if all_files_searched:
                    
                    return # no work to do
                    
                
            
            num_searched_estimate = num_searched
            
            HG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            job_key.SetStatusTitle( 'searching for potential duplicates' )
            
            HG.client_controller.pub( 'message', job_key )
            
            still_work_to_do = True
            
            while still_work_to_do:
                
                search_distance = HG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
                
                start_time = HydrusData.GetNowPrecise()
                
                ( still_work_to_do, num_done ) = HG.client_controller.WriteSynchronous( 'maintain_similar_files_search_for_potential_duplicates', search_distance, maintenance_mode = HC.MAINTENANCE_FORCED, job_key = job_key, work_time_float = 0.5 )
                
                time_it_took = HydrusData.GetNowPrecise() - start_time
                
                num_searched_estimate += num_done
                
                if num_searched_estimate > total_num_files:
                    
                    similar_files_maintenance_status = HG.client_controller.Read( 'similar_files_maintenance_status' )
                    
                    if similar_files_maintenance_status is None:
                        
                        break
                        
                    
                    with self._lock:
                        
                        self._similar_files_maintenance_status = similar_files_maintenance_status
                        
                        searched_distances_to_count = self._similar_files_maintenance_status
                        
                        total_num_files = max( num_searched_estimate, sum( searched_distances_to_count.values() ) )
                        
                    
                
                text = 'searching: {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_searched_estimate, total_num_files ) )
                job_key.SetVariable( 'popup_text_1', text )
                job_key.SetVariable( 'popup_gauge_1', ( num_searched_estimate, total_num_files ) )
                
                if job_key.IsCancelled() or HG.model_shutdown:
                    
                    break
                    
                
                time.sleep( min( 5, time_it_took ) ) # ideally 0.5s, but potentially longer
                
            
            job_key.Delete()
            
        finally:
            
            with self._lock:
                
                self._currently_doing_potentials_search = False
                
            
            self.RefreshMaintenanceNumbers()
            self.NotifyNewPotentialsSearchNumbers()
            
        
    
class DuplicateActionOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS
    SERIALISABLE_NAME = 'Duplicate Action Options'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, tag_service_actions = None, rating_service_actions = None, sync_archive = False, sync_urls_action = None ):
        
        if tag_service_actions is None:
            
            tag_service_actions = []
            
        
        if rating_service_actions is None:
            
            rating_service_actions = []
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._sync_archive = sync_archive
        self._sync_urls_action = sync_urls_action
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            self._tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, action, tag_filter ) in self._tag_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in HC.REAL_TAG_SERVICES ]
            self._rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._rating_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
        
        serialisable_tag_service_actions = [ ( service_key.hex(), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in self._tag_service_actions ]
        serialisable_rating_service_actions = [ ( service_key.hex(), action ) for ( service_key, action ) in self._rating_service_actions ]
        
        return ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._sync_archive, self._sync_urls_action )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._sync_archive, self._sync_urls_action ) = serialisable_info
        
        self._tag_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter ) ) for ( serialisable_service_key, action, serialisable_tag_filter ) in serialisable_tag_service_actions ]
        self._rating_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action ) for ( serialisable_service_key, action ) in serialisable_rating_service_actions ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_service_actions, delete_second_file ) = old_serialisable_info
            
            tag_service_actions = []
            rating_service_actions = []
            
            # As the client isn't booted when this is loaded in options, there isn't a good way to figure out tag from rating
            # So, let's just dupe and purge later on, in serialisation
            for ( service_key_encoded, action ) in serialisable_service_actions:
                
                service_key = bytes.fromhex( service_key_encoded )
                
                tag_filter = HydrusTags.TagFilter()
                
                tag_service_actions.append( ( service_key, action, tag_filter ) )
                
                rating_service_actions.append( ( service_key, action ) )
                
            
            serialisable_tag_service_actions = [ ( service_key.hex(), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in tag_service_actions ]
            serialisable_rating_service_actions = [ ( service_key.hex(), action ) for ( service_key, action ) in rating_service_actions ]
            
            sync_archive = delete_second_file
            delete_both_files = False
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files ) = old_serialisable_info
            
            sync_urls_action = None
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive, sync_urls_action )
            
            return ( 4, new_serialisable_info )
            
        
    
    def SetTuple( self, tag_service_actions, rating_service_actions, sync_archive, sync_urls_action ):
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._sync_archive = sync_archive
        self._sync_urls_action = sync_urls_action
        
    
    def ToTuple( self ):
        
        return ( self._tag_service_actions, self._rating_service_actions, self._sync_archive, self._sync_urls_action )
        
    
    def ProcessPairIntoContentUpdates( self, first_media, second_media, delete_first = False, delete_second = False, delete_both = False, file_deletion_reason = None ):
        
        if file_deletion_reason is None:
            
            file_deletion_reason = 'unknown reason'
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        first_hashes = first_media.GetHashes()
        second_hashes = second_media.GetHashes()
        
        #
        
        services_manager = HG.client_controller.services_manager
        
        for ( service_key, action, tag_filter ) in self._tag_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_TAG:
                
                add_content_action = HC.CONTENT_UPDATE_ADD
                
            elif service_type == HC.TAG_REPOSITORY:
                
                add_content_action = HC.CONTENT_UPDATE_PEND
                
            
            first_tags = first_media.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            second_tags = second_media.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            first_tags = tag_filter.Filter( first_tags )
            second_tags = tag_filter.Filter( second_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_tags.difference( first_tags )
                second_needs = first_tags.difference( second_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, second_hashes ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, second_hashes ) ) for tag in second_tags ) )
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        def worth_updating_rating( source_rating, dest_rating ):
            
            if source_rating is not None:
                
                if dest_rating is None or source_rating > dest_rating:
                    
                    return True
                    
                
            
            return False
            
        
        for ( service_key, action ) in self._rating_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            first_current_value = first_media.GetRatingsManager().GetRating( service_key )
            second_current_value = second_media.GetRatingsManager().GetRating( service_key )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if worth_updating_rating( first_current_value, second_current_value ):
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, second_hashes ) ) )
                    
                elif worth_updating_rating( second_current_value, first_current_value ):
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if worth_updating_rating( second_current_value, first_current_value ):
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                if second_current_value is not None:
                    
                    if worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, second_hashes ) ) )
                    
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        #
        
        if self._sync_archive:
            
            if first_media.HasInbox() and second_media.HasArchive():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, first_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
                
            elif first_media.HasArchive() and second_media.HasInbox():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, second_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
                
            
        
        #
        
        if self._sync_urls_action is not None:
            
            first_urls = set( first_media.GetLocationsManager().GetURLs() )
            second_urls = set( second_media.GetLocationsManager().GetURLs() )
            
            content_updates = []
            
            if self._sync_urls_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_urls.difference( first_urls )
                second_needs = first_urls.difference( second_urls )
                
                if len( first_needs ) > 0:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                    
                
                if len( second_needs ) > 0:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( second_needs, second_hashes ) ) )
                    
                
            elif self._sync_urls_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_urls.difference( first_urls )
                
                if len( first_needs ) > 0:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                    
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].extend( content_updates )
                
            
        
        #
        
        deletee_media = []
        
        if delete_first or delete_second or delete_both:
            
            if delete_first or delete_both:
                
                deletee_media.append( first_media )
                
            
            if delete_second or delete_both:
                
                deletee_media.append( second_media )
                
            
        
        delete_lock_for_archived_files = HG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
        
        for media in deletee_media:
            
            if delete_lock_for_archived_files and not media.HasInbox():
                
                continue
                
            
            if media.GetLocationsManager().IsTrashed():
                
                deletee_service_keys = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, )
                
            else:
                
                local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                
                deletee_service_keys = media.GetLocationsManager().GetCurrent().intersection( local_file_service_keys )
                
            
            for deletee_service_key in deletee_service_keys:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, media.GetHashes(), reason = file_deletion_reason )
                
                service_keys_to_content_updates[ deletee_service_key ].append( content_update )
                
            
        
        #
        
        return service_keys_to_content_updates
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS ] = DuplicateActionOptions
