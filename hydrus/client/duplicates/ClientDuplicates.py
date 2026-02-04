import collections
import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

DUPE_PAIR_SORT_MAX_FILESIZE = 0
DUPE_PAIR_SORT_SIMILARITY = 1
DUPE_PAIR_SORT_MIN_FILESIZE = 2
DUPE_PAIR_SORT_RANDOM = 3

dupe_pair_sort_string_lookup = {
    DUPE_PAIR_SORT_MAX_FILESIZE : 'filesize of larger file',
    DUPE_PAIR_SORT_SIMILARITY : 'similarity (distance/filesize ratio)',
    DUPE_PAIR_SORT_MIN_FILESIZE : 'filesize of smaller file',
    DUPE_PAIR_SORT_RANDOM : 'random'
}

DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH = 0
DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH = 1
DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES = 2

SIMILAR_FILES_PIXEL_DUPES_REQUIRED = 0
SIMILAR_FILES_PIXEL_DUPES_ALLOWED = 1
SIMILAR_FILES_PIXEL_DUPES_EXCLUDED = 2

similar_files_pixel_dupes_string_lookup = {
    SIMILAR_FILES_PIXEL_DUPES_REQUIRED : 'must be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_ALLOWED : 'can be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_EXCLUDED : 'must not be pixel dupes'
}

SYNC_ARCHIVE_NONE = 0
SYNC_ARCHIVE_IF_ONE_DO_BOTH = 1
SYNC_ARCHIVE_DO_BOTH_REGARDLESS = 2

def get_updated_domain_modified_timestamp_datas( destination_media_result: ClientMediaResult.MediaResult, source_media_result: ClientMediaResult.MediaResult, urls: collections.abc.Collection[ str ] ):
    
    from hydrus.client.networking import ClientNetworkingFunctions
    
    domains = set()
    
    for url in urls:
        
        try:
            
            domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
            
            domains.add( domain )
            
        except Exception as e:
            
            continue # not an url in the strict sense, let's skip since this method really wants to be dealing with nice URLs
            
        
    
    timestamp_datas = []
    source_timestamp_manager = source_media_result.GetTimesManager()
    destination_timestamp_manager = destination_media_result.GetTimesManager()
    
    for domain in domains:
        
        source_timestamp_ms = source_timestamp_manager.GetDomainModifiedTimestampMS( domain )
        
        if source_timestamp_ms is not None:
            
            destination_timestamp_ms = destination_timestamp_manager.GetDomainModifiedTimestampMS( domain )
            
            if destination_timestamp_ms is None or ClientTime.ShouldUpdateModifiedTime( destination_timestamp_ms, source_timestamp_ms ):
                
                timestamp_data = ClientTime.TimestampData.STATICDomainModifiedTime( domain, source_timestamp_ms )
                
                timestamp_datas.append( timestamp_data )
                
            
        
    
    return timestamp_datas
    

def get_domain_modified_content_updates( destination_media_result: ClientMediaResult.MediaResult, source_media_result: ClientMediaResult.MediaResult, urls: collections.abc.Collection[ str ] ):
    
    timestamp_datas = get_updated_domain_modified_timestamp_datas( destination_media_result, source_media_result, urls )
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( destination_media_result.GetHash(), ), timestamp_data ) ) for timestamp_data in timestamp_datas ]
    
    return content_updates
    

class DuplicateContentMergeOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS
    SERIALISABLE_NAME = 'Duplicate Metadata Merge Options'
    SERIALISABLE_VERSION = 7
    
    def __init__( self ):
        
        super().__init__()
        
        # it is important that the default init of this guy syncs absolutely nothing!
        # we use empty dupe merge option guys to do some other processing, so empty must mean empty
        
        self._tag_service_actions = []
        self._rating_service_actions = []
        self._sync_notes_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_note_import_options = NoteImportOptions.NoteImportOptions()
        self._sync_archive_action = SYNC_ARCHIVE_NONE
        self._sync_urls_action = HC.CONTENT_MERGE_ACTION_NONE
        self._sync_file_modified_date_action = HC.CONTENT_MERGE_ACTION_NONE
        
    
    def _GetSerialisableInfo( self ):
        
        if CG.client_controller.IsBooted():
            
            services_manager = CG.client_controller.services_manager
            
            self._tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, action, tag_filter ) in self._tag_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in HC.REAL_TAG_SERVICES ]
            self._rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._rating_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in HC.RATINGS_SERVICES ]
            
        
        serialisable_tag_service_actions = [ ( service_key.hex(), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in self._tag_service_actions ]
        serialisable_rating_service_actions = [ ( service_key.hex(), action ) for ( service_key, action ) in self._rating_service_actions ]
        
        serialisable_sync_note_import_options = self._sync_note_import_options.GetSerialisableTuple()
        
        return (
            serialisable_tag_service_actions,
            serialisable_rating_service_actions,
            self._sync_notes_action,
            serialisable_sync_note_import_options,
            self._sync_archive_action,
            self._sync_urls_action,
            self._sync_file_modified_date_action
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_tag_service_actions,
            serialisable_rating_service_actions,
            self._sync_notes_action,
            serialisable_sync_note_import_options,
            self._sync_archive_action,
            self._sync_urls_action,
            self._sync_file_modified_date_action
        ) = serialisable_info
        
        self._tag_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter ) ) for ( serialisable_service_key, action, serialisable_tag_filter ) in serialisable_tag_service_actions ]
        self._rating_service_actions = [ ( bytes.fromhex( serialisable_service_key ), action ) for ( serialisable_service_key, action ) in serialisable_rating_service_actions ]
        self._sync_note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_sync_note_import_options )
        
    
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
            
        
        if version == 4:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive, sync_urls_action ) = old_serialisable_info
            
            if sync_archive:
                
                sync_archive_action = SYNC_ARCHIVE_IF_ONE_DO_BOTH
                
            else:
                
                sync_archive_action = SYNC_ARCHIVE_NONE
                
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive_action, sync_urls_action )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_archive_action, sync_urls_action ) = old_serialisable_info
            
            if sync_urls_action is None:
                
                sync_urls_action = HC.CONTENT_MERGE_ACTION_NONE
                
            
            sync_notes_action = HC.CONTENT_MERGE_ACTION_NONE
            sync_note_import_options = NoteImportOptions.NoteImportOptions()
            
            serialisable_sync_note_import_options = sync_note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, sync_notes_action, serialisable_sync_note_import_options, sync_archive_action, sync_urls_action )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            (
                serialisable_tag_service_actions,
                serialisable_rating_service_actions,
                sync_notes_action,
                serialisable_sync_note_import_options,
                sync_archive_action,
                sync_urls_action
            ) = old_serialisable_info
            
            sync_file_modified_date_action = HC.CONTENT_MERGE_ACTION_NONE
            
            new_serialisable_info = (
                serialisable_tag_service_actions,
                serialisable_rating_service_actions,
                sync_notes_action,
                serialisable_sync_note_import_options,
                sync_archive_action,
                sync_urls_action,
                sync_file_modified_date_action
            )
            
            return ( 7, new_serialisable_info )
            
        
    
    def GetMergeSummaryOnPair( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult, delete_a: bool, delete_b: bool, in_auto_resolution = False ):
        
        # do file delete; this guy only cares about the content merge
        content_update_packages = self.ProcessPairIntoContentUpdatePackages( media_result_a, media_result_b, delete_a = delete_a, delete_b = delete_b, in_auto_resolution = in_auto_resolution )
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        
        a_work = collections.defaultdict( list )
        b_work = collections.defaultdict( list )
        
        for content_update_package in content_update_packages:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    s = content_update.ToActionSummary()
                    
                    if hash_a in hashes:
                        
                        a_work[ service_key ].append( s )
                        
                    
                    if hash_b in hashes:
                        
                        b_work[ service_key ].append( s )
                        
                    
                
            
        
        work_strings = []
        
        for ( hash_name, work ) in [
            ( 'A', a_work ),
            ( 'B', b_work )
        ]:
            
            work_flat = sorted( [ ( CG.client_controller.services_manager.GetName( service_key ), sorted( summary_strings ) ) for ( service_key, summary_strings ) in work.items() ] )
            
            gubbins = '|'.join( [ name + ': ' + ', '.join( summary_strings ) for ( name, summary_strings ) in work_flat ] )
            
            if len( gubbins ) == 0:
                
                work_string = hash_name + ': no changes'
                
            else:
                
                work_string = hash_name + ': ' + gubbins
                
            
            work_strings.append( work_string )
            
        
        if len( work_strings ) > 0:
            
            return '\n'.join( work_strings )
            
        else:
            
            return 'no content updates'
            
        
    
    def GetRatingServiceActions( self ) -> collections.abc.Collection[ tuple ]:
        
        return self._rating_service_actions
        
    
    def GetTagServiceActions( self ) -> collections.abc.Collection[ tuple ]:
        
        return self._tag_service_actions
        
    
    def GetSyncArchiveAction( self ) -> int:
        
        return self._sync_archive_action
        
    
    def GetSyncFileModifiedDateAction( self ) -> int:
        
        return self._sync_file_modified_date_action
        
    
    def GetSyncNotesAction( self ) -> int:
        
        return self._sync_notes_action
        
    
    def GetSyncNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        return self._sync_note_import_options
        
    
    def GetSyncURLsAction( self ) -> int:
        
        return self._sync_urls_action
        
    
    def SetRatingServiceActions( self, rating_service_actions: collections.abc.Collection[ tuple ] ):
        
        self._rating_service_actions = rating_service_actions
        
    
    def SetTagServiceActions( self, tag_service_actions: collections.abc.Collection[ tuple ] ):
        
        self._tag_service_actions = tag_service_actions
        
    
    def SetSyncArchiveAction( self, sync_archive_action: int ):
        
        self._sync_archive_action = sync_archive_action
        
    
    def SetSyncFileModifiedDateAction( self, sync_file_modified_date_action: int ):
        
        self._sync_file_modified_date_action = sync_file_modified_date_action
        
    
    def SetSyncNotesAction( self, sync_notes_action: int ):
        
        self._sync_notes_action = sync_notes_action
        
    
    def SetSyncNoteImportOptions( self, sync_note_import_options: NoteImportOptions.NoteImportOptions ):
        
        self._sync_note_import_options = sync_note_import_options
        
    
    def SetSyncURLsAction( self, sync_urls_action: int ):
        
        self._sync_urls_action = sync_urls_action
        
    
    def ProcessPairIntoContentUpdatePackages(
        self,
        media_result_a: ClientMediaResult.MediaResult,
        media_result_b: ClientMediaResult.MediaResult,
        delete_a = False,
        delete_b = False,
        file_deletion_reason = None,
        do_not_do_deletes = False,
        in_auto_resolution = False
    ) -> list[ ClientContentUpdates.ContentUpdatePackage ]:
        
        if file_deletion_reason is None:
            
            file_deletion_reason = 'unknown reason'
            
        
        content_update_packages = []
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        hash_a_set = { hash_a }
        hash_b_set = { hash_b }
        
        #
        
        services_manager = CG.client_controller.services_manager
        
        for ( service_key, action, tag_filter ) in self._tag_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.TAG_REPOSITORY and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                action = HC.CONTENT_MERGE_ACTION_COPY
                
            
            if service_type == HC.LOCAL_TAG:
                
                add_content_action = HC.CONTENT_UPDATE_ADD
                
            elif service_type == HC.TAG_REPOSITORY:
                
                add_content_action = HC.CONTENT_UPDATE_PEND
                
            else:
                
                continue
                
            
            first_tags = media_result_a.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            second_tags = media_result_b.GetTagsManager().GetCurrentAndPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            first_tags = tag_filter.Filter( first_tags )
            second_tags = tag_filter.Filter( second_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_tags.difference( first_tags )
                second_needs = first_tags.difference( second_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_b_set ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_tags.difference( first_tags )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, hash_a_set ) ) for tag in first_needs ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, hash_b_set ) ) for tag in second_tags ) )
                
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
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
                
            
            first_current_value = media_result_a.GetRatingsManager().GetRating( service_key )
            second_current_value = media_result_b.GetRatingsManager().GetRating( service_key )
            
            service_type = service.GetServiceType()
            
            if service_type in HC.STAR_RATINGS_SERVICES:
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if worth_updating_rating( first_current_value, second_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, hash_b_set ) ) )
                        
                    elif worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if worth_updating_rating( second_current_value, first_current_value ):
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value is not None:
                        
                        if worth_updating_rating( second_current_value, first_current_value ):
                            
                            content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, hash_a_set ) ) )
                            
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, hash_b_set ) ) )
                        
                    
                
            elif service_type == HC.LOCAL_RATING_INCDEC:
                
                sum_value = first_current_value + second_current_value
                
                if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        
                    
                    if first_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_b_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_COPY:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        
                    
                elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                    
                    if second_current_value > 0:
                        
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( sum_value, hash_a_set ) ) )
                        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0, hash_b_set ) ) )
                        
                    
                
            else:
                
                continue
                
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        #
        
        if self._sync_notes_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_names_and_notes = list( media_result_a.GetNotesManager().GetNamesToNotes().items() )
            second_names_and_notes = list( media_result_b.GetNotesManager().GetNamesToNotes().items() )
            
            # TODO: rework this to UpdateeNamesToNotes
            
            if self._sync_notes_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                second_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_b, first_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                content_update_package.AddContentUpdatePackage( second_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
            elif self._sync_notes_action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_content_update_package = self._sync_note_import_options.GetContentUpdatePackage( media_result_a, second_names_and_notes )
                
                content_update_package.AddContentUpdatePackage( first_content_update_package )
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash_b, name ) ) for ( name, note ) in second_names_and_notes ]
                
                content_update_package.AddContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
                
            
        
        #
        
        content_update_archive_first = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hash_a_set )
        content_update_archive_second = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hash_b_set )
        
        # the "and not delete_a" gubbins here is to help out the delete lock lmao. don't want to archive and then try to delete
        
        action_to_actually_consult = self._sync_archive_action
        
        # don't archive both files if the user hasn't seen them in the duplicate filter bruh
        if in_auto_resolution and action_to_actually_consult == SYNC_ARCHIVE_DO_BOTH_REGARDLESS:
            
            action_to_actually_consult = SYNC_ARCHIVE_IF_ONE_DO_BOTH
            
        
        first_locations_manager = media_result_a.GetLocationsManager()
        second_locations_manager = media_result_b.GetLocationsManager()
        
        if action_to_actually_consult == SYNC_ARCHIVE_IF_ONE_DO_BOTH:
            
            if first_locations_manager.inbox and not second_locations_manager.inbox and not delete_a:
                
                content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update_archive_first )
                
            elif not first_locations_manager.inbox and second_locations_manager.inbox and not delete_b:
                
                content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update_archive_second )
                
            
        elif action_to_actually_consult == SYNC_ARCHIVE_DO_BOTH_REGARDLESS:
            
            if first_locations_manager.inbox and not delete_a:
                
                content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update_archive_first )
                
            
            if second_locations_manager.inbox and not delete_b:
                
                content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update_archive_second )
                
            
        
        #
        
        if self._sync_file_modified_date_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_timestamp_ms = media_result_a.GetTimesManager().GetFileModifiedTimestampMS()
            second_timestamp_ms = media_result_b.GetTimesManager().GetFileModifiedTimestampMS()
            
            if self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_a, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                elif ClientTime.ShouldUpdateModifiedTime( second_timestamp_ms, first_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_b, ), ClientTime.TimestampData.STATICFileModifiedTime( first_timestamp_ms ) ) ) )
                    
                
            elif self._sync_file_modified_date_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if ClientTime.ShouldUpdateModifiedTime( first_timestamp_ms, second_timestamp_ms ):
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, HC.CONTENT_UPDATE_SET, ( ( hash_a, ), ClientTime.TimestampData.STATICFileModifiedTime( second_timestamp_ms ) ) ) )
                    
                
            
        
        #
        
        if self._sync_urls_action != HC.CONTENT_MERGE_ACTION_NONE:
            
            first_urls = set( media_result_a.GetLocationsManager().GetURLs() )
            second_urls = set( media_result_b.GetLocationsManager().GetURLs() )
            
            # hey note here that they url action is x_needs, but the timestamp action works off of what they other guy _has_, totally, since we want to examine conflicts to get the earlier time
            
            if self._sync_urls_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_urls.difference( first_urls )
                second_needs = first_urls.difference( second_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, hash_a_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, get_domain_modified_content_updates( media_result_a, media_result_b, second_urls ) )
                    
                
                if len( second_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( second_needs, hash_b_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, get_domain_modified_content_updates( media_result_b, media_result_a, first_urls ) )
                    
                
            elif self._sync_urls_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_urls.difference( first_urls )
                
                if len( first_needs ) > 0:
                    
                    content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, hash_a_set ) ) )
                    
                    content_update_package.AddContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, get_domain_modified_content_updates( media_result_a, media_result_b, second_urls ) )
                    
                
            
        
        #
        
        if content_update_package.HasContent():
            
            content_update_packages.append( content_update_package )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
        
        #
        
        deletee_media_results = []
        
        if delete_a:
            
            deletee_media_results.append( media_result_a )
            
        
        if delete_b:
            
            deletee_media_results.append( media_result_b )
            
        
        for media_result in deletee_media_results:
            
            if do_not_do_deletes:
                
                continue
                
            
            if CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in media_result.GetLocationsManager().GetCurrent():
                
                delete_lock_applies = not media_result.GetLocationsManager().inbox and CG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
                
                if delete_lock_applies:
                    
                    undo_delete_lock_1 = not in_auto_resolution and CG.client_controller.new_options.GetBoolean( 'delete_lock_reinbox_deletees_after_duplicate_filter' )
                    undo_delete_lock_2 = in_auto_resolution and CG.client_controller.new_options.GetBoolean( 'delete_lock_reinbox_deletees_in_auto_resolution' )
                    
                    if ( undo_delete_lock_1 or undo_delete_lock_2 ):
                        
                        content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { media_result.GetHash() } ) )
                        
                        content_update_packages.append( content_update_package )
                        
                        content_update_package = ClientContentUpdates.ContentUpdatePackage()
                        
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { media_result.GetHash() }, reason = file_deletion_reason )
                
                content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, content_update )
                
            
        
        #
        
        if content_update_package.HasContent():
            
            content_update_packages.append( content_update_package )
            
        
        return content_update_packages
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS ] = DuplicateContentMergeOptions
