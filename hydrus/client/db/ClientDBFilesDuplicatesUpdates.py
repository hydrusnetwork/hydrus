import collections.abc
import itertools
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBFilesDuplicatesAutoResolutionStorage
from hydrus.client.db import ClientDBFilesDuplicatesStorage
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext

class ClientDBFilesDuplicatesUpdates( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper,
        modules_services: ClientDBServices.ClientDBMasterServices,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_files_duplicates_storage: ClientDBFilesDuplicatesStorage.ClientDBFilesDuplicatesStorage,
        modules_files_duplicates_auto_resolution_storage: ClientDBFilesDuplicatesAutoResolutionStorage.ClientDBFilesDuplicatesAutoResolutionStorage,
        ):
        
        super().__init__( 'client file duplicates', cursor )
        
        self._cursor_transaction_wrapper = cursor_transaction_wrapper
        self.modules_services = modules_services
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_similar_files = modules_similar_files
        self.modules_files_duplicates_storage = modules_files_duplicates_storage
        self.modules_files_duplicates_auto_resolution_storage = modules_files_duplicates_auto_resolution_storage
        
        # TODO: Make this guy weakref the location contexts or something so things here can decay
        # Ok so when we moved to 'update this guy' instead of 'invalidate this guy', suddenly we were no longer deleting anything from here
        # it is important we don't delete anything because we rely on the store of location contexts to know which fragmentary searches are waiting on a filtered pubsub for
        # so we need some sort of weakref or object ref count or something so when a fragmentary search is deleted, we know we can clear out a bulky cache record here and stop doing update maths on it
        self._location_contexts_to_potential_duplicate_id_pairs_and_distances: dict[ ClientLocation.LocationContext, ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances ] = {}
        
    
    def _GetFileHashIdsByDuplicateType( self, db_location_context: ClientDBFilesStorage.DBLocationContext, hash_id: int, duplicate_type: int ) -> list[ int ]:
        
        dupe_hash_ids = set()
        
        if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    false_positive_alternates_group_ids = self.modules_files_duplicates_storage.GetFalsePositiveAlternatesGroupIds( alternates_group_id )
                    
                    false_positive_alternates_group_ids.discard( alternates_group_id )
                    
                    false_positive_media_ids = set()
                    
                    for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                        
                        false_positive_media_ids.update( self.modules_files_duplicates_storage.GetAlternateMediaIds( false_positive_alternates_group_id ) )
                        
                    
                    for false_positive_media_id in false_positive_media_ids:
                        
                        best_king_hash_id = self.modules_files_duplicates_storage.GetBestKingId( false_positive_media_id, db_location_context )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_ALTERNATE:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    alternates_media_ids = self._STS( self._Execute( 'SELECT media_id FROM alternate_file_group_members WHERE alternates_group_id = ?;', ( alternates_group_id, ) ) )
                    
                    alternates_media_ids.discard( media_id )
                    
                    for alternates_media_id in alternates_media_ids:
                        
                        best_king_hash_id = self.modules_files_duplicates_storage.GetBestKingId( alternates_media_id, db_location_context )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_MEMBER:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                media_hash_ids = self.modules_files_duplicates_storage.GetDuplicateHashIds( media_id, db_location_context = db_location_context )
                
                dupe_hash_ids.update( media_hash_ids )
                
            
        elif duplicate_type == HC.DUPLICATE_KING:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                best_king_hash_id = self.modules_files_duplicates_storage.GetBestKingId( media_id, db_location_context )
                
                if best_king_hash_id is not None:
                    
                    dupe_hash_ids.add( best_king_hash_id )
                    
                
            
        elif duplicate_type == HC.DUPLICATE_POTENTIAL:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                table_join = self.modules_files_duplicates_storage.GetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
                
                for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT smaller_media_id, larger_media_id FROM {} WHERE smaller_media_id = ? OR larger_media_id = ?;'.format( table_join ), ( media_id, media_id ) ).fetchall():
                    
                    if smaller_media_id != media_id:
                        
                        potential_media_id = smaller_media_id
                        
                    else:
                        
                        potential_media_id = larger_media_id
                        
                    
                    best_king_hash_id = self.modules_files_duplicates_storage.GetBestKingId( potential_media_id, db_location_context )
                    
                    if best_king_hash_id is not None:
                        
                        dupe_hash_ids.add( best_king_hash_id )
                        
                    
                
            
        
        dupe_hash_ids.discard( hash_id )
        
        dupe_hash_ids = list( dupe_hash_ids )
        
        dupe_hash_ids.insert( 0, hash_id )
        
        return dupe_hash_ids
        
    
    def _AddRowsToRowCacheAndAutoResolutionRules( self, rows: collections.abc.Collection[ tuple[ int, int, int ] ], only_for_this_file_service_key: bytes | None = None ):
        
        auto_resolution_location_contexts = set( self.modules_files_duplicates_auto_resolution_storage.GetAllRuleLocationContexts() )
        
        cache_location_contexts = set( self._location_contexts_to_potential_duplicate_id_pairs_and_distances.keys() )
        
        all_pertinent_location_contexts = auto_resolution_location_contexts.union( cache_location_contexts )
        
        if only_for_this_file_service_key is not None:
            
            all_pertinent_location_contexts = [ location_context for location_context in all_pertinent_location_contexts if only_for_this_file_service_key in location_context.current_service_keys ]
            
        
        if len( all_pertinent_location_contexts ) == 0:
            
            return
            
        
        pairs_to_distances = { ( smaller_media_id, larger_media_id ) : distance for ( smaller_media_id, larger_media_id, distance ) in rows }
        
        insert_pairs = set( pairs_to_distances.keys() )
        
        for location_context in all_pertinent_location_contexts:
            
            filtered_pairs = self.modules_files_duplicates_storage.FilterMediaIdPairs( location_context, insert_pairs )
            
            if len( filtered_pairs ) == 0:
                
                continue
                
            
            if location_context in self._location_contexts_to_potential_duplicate_id_pairs_and_distances:
                
                filtered_rows = [ ( smaller_media_id, larger_media_id, pairs_to_distances[ ( smaller_media_id, larger_media_id ) ] ) for ( smaller_media_id, larger_media_id ) in filtered_pairs ]
                
                potential_duplicate_id_pairs_and_distances = self._location_contexts_to_potential_duplicate_id_pairs_and_distances[ location_context ]
                
                potential_duplicate_id_pairs_and_distances.AddRows( filtered_rows )
                
                self._cursor_transaction_wrapper.pub_after_job( 'potential_duplicate_pairs_update', ClientPotentialDuplicatesSearchContext.PAIRS_UPDATE_ADD_ROWS, location_context, filtered_rows )
                
            
            if location_context in auto_resolution_location_contexts:
                
                self.modules_files_duplicates_auto_resolution_storage.NotifyNewPotentialDuplicatePairsAdded( location_context, filtered_pairs )
                
            
        
    
    def _DeletePairsFromRowCacheAndAutoResolutionRules( self, deletee_pairs: collections.abc.Collection[ tuple[ int, int ] ], only_for_this_file_service_key: bytes | None = None ):
        
        auto_resolution_location_contexts = set( self.modules_files_duplicates_auto_resolution_storage.GetAllRuleLocationContexts() )
        
        cache_location_contexts = set( self._location_contexts_to_potential_duplicate_id_pairs_and_distances.keys() )
        
        all_pertinent_location_contexts = auto_resolution_location_contexts.union( cache_location_contexts )
        
        if only_for_this_file_service_key is not None:
            
            all_pertinent_location_contexts = [ location_context for location_context in all_pertinent_location_contexts if only_for_this_file_service_key in location_context.current_service_keys ]
            
        
        if len( all_pertinent_location_contexts ) == 0:
            
            return
            
        
        deletee_pairs = set( deletee_pairs )
        
        for location_context in all_pertinent_location_contexts:
            
            if location_context.IsOneDomain():
                
                valid_pairs = deletee_pairs
                
            else:
                
                still_in_there_pairs = self.modules_files_duplicates_storage.FilterMediaIdPairs( location_context, deletee_pairs ) # some complicated multi-domain guy where files are still in some other domain
                
                valid_pairs = deletee_pairs.difference( still_in_there_pairs )
                
            
            if len( valid_pairs ) == 0:
                
                continue
                
            
            if location_context in self._location_contexts_to_potential_duplicate_id_pairs_and_distances:
                
                potential_duplicate_id_pairs_and_distances = self._location_contexts_to_potential_duplicate_id_pairs_and_distances[ location_context ]
                
                potential_duplicate_id_pairs_and_distances.DeletePairs( valid_pairs )
                
                self._cursor_transaction_wrapper.pub_after_job( 'potential_duplicate_pairs_update', ClientPotentialDuplicatesSearchContext.PAIRS_UPDATE_DELETE_PAIRS, location_context, valid_pairs )
                
            
            if location_context in auto_resolution_location_contexts:
                
                self.modules_files_duplicates_auto_resolution_storage.NotifyExistingPotentialDuplicatePairsRemoved( location_context, valid_pairs )
                
            
        
    
    def AddPotentialDuplicates( self, media_id, potential_duplicate_media_ids_and_distances ):
        
        inserts = []
        
        for ( potential_duplicate_media_id, distance ) in potential_duplicate_media_ids_and_distances:
            
            if potential_duplicate_media_id == media_id: # already duplicates!
                
                continue
                
            
            if self.modules_files_duplicates_storage.MediasAreFalsePositive( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            if self.modules_files_duplicates_storage.MediasAreConfirmedAlternates( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            # if they are alternates with different alt label and index, do not add
            # however this _could_ be folded into areconfirmedalts on the setalt event--any other alt with diff label/index also gets added
            
            smaller_media_id = min( media_id, potential_duplicate_media_id )
            larger_media_id = max( media_id, potential_duplicate_media_id )
            
            inserts.append( ( smaller_media_id, larger_media_id, distance ) )
            
        
        if len( inserts ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO potential_duplicate_pairs ( smaller_media_id, larger_media_id, distance ) VALUES ( ?, ?, ? );', inserts )
            
            self._AddRowsToRowCacheAndAutoResolutionRules( inserts )
            
        
    
    def ClearInternalFalsePositivesHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        media_ids = { self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True ) for hash_id in hash_ids }
        
        media_ids.discard( None )
        
        if len( media_ids ) < 2:
            
            return 0
            
        
        alternates_group_ids = { self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True ) for media_id in media_ids }
        
        alternates_group_ids.discard( None )
        
        if len( alternates_group_ids ) < 2:
            
            return 0
            
        
        # BIG BRAIN ALERT
        # if we pre-sort the list we give combinations, every pair in the output is sorted, a < b, which satisfies our need for smaller/larger pair
        all_pairs = list( itertools.combinations( sorted( alternates_group_ids ), 2 ) )
        
        self._ExecuteMany( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', all_pairs )
        
        num_cleared = self._GetRowCount()
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
        return num_cleared
        
    
    def ClearAllFalsePositivesHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        media_ids = { self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True ) for hash_id in hash_ids }
        
        media_ids.discard( None )
        
        if len( media_ids ) == 0:
            
            return 0
            
        
        alternates_group_ids = { self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True ) for media_id in media_ids }
        
        alternates_group_ids.discard( None )
        
        if len( alternates_group_ids ) == 0:
            
            return 0
            
        
        self._ExecuteMany( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( ( alternates_group_id, alternates_group_id ) for alternates_group_id in alternates_group_ids ) )
        
        num_cleared = self._GetRowCount()
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
        return num_cleared
        
    
    def ClearPotentialsBetweenMedias( self, media_ids_a, media_ids_b ):
        
        # these two groups of medias now have a false positive or alternates relationship set between them, or they are about to be merged
        # therefore, potentials between them are no longer needed
        # note that we are not eliminating intra-potentials within A or B, only inter-potentials between A and B
        
        all_media_ids = set()
        
        all_media_ids.update( media_ids_a )
        all_media_ids.update( media_ids_b )
        
        with self._MakeTemporaryIntegerTable( all_media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            # keep these separate--older sqlite can't do cross join to an OR ON
            
            # temp media ids to potential pairs
            potential_duplicate_pairs = set( self._Execute( 'SELECT smaller_media_id, larger_media_id FROM {} CROSS JOIN potential_duplicate_pairs ON ( smaller_media_id = media_id );'.format( temp_media_ids_table_name ) ).fetchall() )
            potential_duplicate_pairs.update( self._Execute( 'SELECT smaller_media_id, larger_media_id FROM {} CROSS JOIN potential_duplicate_pairs ON ( larger_media_id = media_id );'.format( temp_media_ids_table_name ) ).fetchall() )
            
        
        deletees = []
        
        for ( smaller_media_id, larger_media_id ) in potential_duplicate_pairs:
            
            if ( smaller_media_id in media_ids_a and larger_media_id in media_ids_b ) or ( smaller_media_id in media_ids_b and larger_media_id in media_ids_a ):
                
                deletees.append( ( smaller_media_id, larger_media_id ) )
                
            
        
        if len( deletees ) > 0:
            
            self.DeletePotentialDuplicates( deletees )
            
        
    
    def ClearPotentialsBetweenAlternatesGroups( self, alternates_group_id_a, alternates_group_id_b ):
        
        # these groups are being set as false positive. therefore, any potential between them no longer applies
        
        media_ids_a = self.modules_files_duplicates_storage.GetAlternateMediaIds( alternates_group_id_a )
        media_ids_b = self.modules_files_duplicates_storage.GetAlternateMediaIds( alternates_group_id_b )
        
        self.ClearPotentialsBetweenMedias( media_ids_a, media_ids_b )
        
    
    def DeleteAllPotentialDuplicatePairs( self ):
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs;' )
        
        for ( location_context, potential_duplicate_id_pairs_and_distances ) in self._location_contexts_to_potential_duplicate_id_pairs_and_distances.items():
            
            potential_duplicate_id_pairs_and_distances.ClearPairs()
            
        
        self._cursor_transaction_wrapper.pub_after_job( 'potential_duplicate_pairs_update', ClientPotentialDuplicatesSearchContext.PAIRS_UPDATE_CLEAR_ALL )
        
        self.modules_files_duplicates_auto_resolution_storage.DeleteAllPotentialDuplicatePairs()
        
        self.modules_similar_files.ResetSearchForAll()
        
    
    def DeletePotentialDuplicates( self, pairs ):
        
        if len( pairs ) > 0:
            
            self._ExecuteMany( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', pairs )
            
            self._DeletePairsFromRowCacheAndAutoResolutionRules( pairs )
            
        
    
    def DeletePotentialDuplicatesForMediaId( self, media_id: int ):
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
        
        # no location context here yet, unlike the add/delete calls
        self._cursor_transaction_wrapper.pub_after_job( 'potential_duplicate_pairs_update', ClientPotentialDuplicatesSearchContext.PAIRS_UPDATE_DELETE_PAIRS_BY_MEDIA_ID, media_id )
        
        if self._GetRowCount() > 0:
            
            for ( location_context, potential_duplicate_id_pairs_and_distances ) in self._location_contexts_to_potential_duplicate_id_pairs_and_distances.items():
                
                potential_duplicate_id_pairs_and_distances.DeletePairsByMediaId( media_id )
                
            
        
        self.modules_files_duplicates_auto_resolution_storage.NotifyMediaIdNoLongerPotential( media_id )
        
    
    def DissolveAlternatesGroupId( self, alternates_group_id ):
        
        media_ids = self.modules_files_duplicates_storage.GetAlternateMediaIds( alternates_group_id )
        
        for media_id in media_ids:
            
            self.DissolveMediaId( media_id )
            
        
        self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id, ) )
        self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
        
    
    def DissolveAlternatesGroupIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    self.DissolveAlternatesGroupId( alternates_group_id )
                    
                
            
        
    
    def DissolveMediaId( self, media_id ):
        
        self.RemoveAlternateMember( media_id )
        
        self.DeletePotentialDuplicatesForMediaId( media_id )
        
        hash_ids = self.modules_files_duplicates_storage.GetDuplicateHashIds( media_id )
        
        self._Execute( 'DELETE FROM duplicate_file_members WHERE media_id = ?;', ( media_id, ) )
        self._Execute( 'DELETE FROM duplicate_files WHERE media_id = ?;', ( media_id, ) )
        
        if len( hash_ids ) > 0:
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def DissolveMediaIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.DissolveMediaId( media_id )
                
            
        
    
    def GetPotentialDuplicateIdPairsAndDistances( self, location_context: ClientLocation.LocationContext ):
        
        if location_context not in self._location_contexts_to_potential_duplicate_id_pairs_and_distances:
            
            # ok lets filter our pairs down to what exists in the domain
            # a pair is good when both nodes' king hash ids exist in _any_ of the UNION of stuff
            # we are going to give the SQLite query planner latitude to figure out what it wants; we'll see how it goes
            
            if location_context.IsAllKnownFiles():
                
                rows = self._Execute( 'SELECT smaller_media_id, larger_media_id, distance FROM potential_duplicate_pairs;' ).fetchall()
                
            else:
                
                db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
                
                file_table_names = db_location_context.GetMultipleFilesTableNames()
                
                if len( file_table_names ) == 1:
                    
                    files_table_name = file_table_names[0]
                    
                    table_join = f'potential_duplicate_pairs, {files_table_name} AS files_smaller, {files_table_name} AS files_larger, duplicate_files AS duplicate_files_smaller, duplicate_files AS duplicate_files_larger ON ( potential_duplicate_pairs.smaller_media_id = duplicate_files_smaller.media_id AND duplicate_files_smaller.king_hash_id = files_smaller.hash_id AND potential_duplicate_pairs.larger_media_id = duplicate_files_larger.media_id AND duplicate_files_larger.king_hash_id = files_larger.hash_id )'
                    
                    query = f'SELECT smaller_media_id, larger_media_id, distance FROM {table_join};'
                    
                    rows = self._Execute( query ).fetchall()
                    
                else:
                    
                    # maybe this is better done with a tempinttable for media_id and we do iterative INSERT OR IGNORE, and then do a double table join using that
                    # I suspect the index-building of that makes it not much better, if at all, than just a quick and dirty python set
                    
                    queries = []
                    
                    for files_table_name in db_location_context.GetMultipleFilesTableNames():
                        
                        smaller_query = f'SELECT smaller_media_id FROM potential_duplicate_pairs, duplicate_files, {files_table_name} ON ( potential_duplicate_pairs.smaller_media_id = duplicate_files.media_id AND duplicate_files.king_hash_id = {files_table_name}.hash_id );'
                        larger_query = f'SELECT larger_media_id FROM potential_duplicate_pairs, duplicate_files, {files_table_name} ON ( potential_duplicate_pairs.larger_media_id = duplicate_files.media_id AND duplicate_files.king_hash_id = {files_table_name}.hash_id );'
                        
                        queries.append( smaller_query )
                        queries.append( larger_query )
                        
                    
                    good_media_ids = set()
                    
                    for query in queries:
                        
                        good_media_ids.update( self._STI( self._Execute( query ) ) )
                        
                    
                    all_potential_duplicate_id_pairs_and_distances = self.GetPotentialDuplicateIdPairsAndDistances( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ) )
                    
                    rows = [ ( smaller_media_id, larger_media_id, distance ) for ( smaller_media_id, larger_media_id, distance ) in all_potential_duplicate_id_pairs_and_distances.IterateRows() if smaller_media_id in good_media_ids and larger_media_id in good_media_ids ]
                    
                
            
            potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( rows )
            
            self._location_contexts_to_potential_duplicate_id_pairs_and_distances[ location_context ] = potential_duplicate_id_pairs_and_distances
            
        
        return self._location_contexts_to_potential_duplicate_id_pairs_and_distances[ location_context ].Duplicate()
        
    
    def NotifyFilesEnteringDomains( self, hash_ids, only_for_this_file_service_key = None ):
        
        rows = []
        
        for hash_id in hash_ids:
            
            if not self.modules_files_duplicates_storage.IsKing( hash_id ):
                
                continue
                
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is None:
                
                continue
                
            
            rows_for_this_file = self._Execute( 'SELECT smaller_media_id, larger_media_id, distance FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) ).fetchall()
            
            rows.extend( rows_for_this_file )
            
        
        if len( rows ) == 0:
            
            return
            
        
        self._AddRowsToRowCacheAndAutoResolutionRules( rows, only_for_this_file_service_key = only_for_this_file_service_key )
        
    
    def NotifyFilesEnteringCombinedLocalFileDomains( self, hash_ids ):
        
        if len( hash_ids ) == 0:
            
            return
            
        
        self.NotifyFilesEnteringDomains( hash_ids, only_for_this_file_service_key = CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
    
    def NotifyFilesEnteringLocalFileDomain( self, service_id, hash_ids ):
        
        if len( hash_ids ) == 0:
            
            return
            
        
        service_key = self.modules_services.GetServiceKey( service_id )
        
        self.NotifyFilesEnteringDomains( hash_ids, only_for_this_file_service_key = service_key )
        
    
    def NotifyFilesLeavingDomains( self, hash_ids, only_for_this_file_service_key = None ):
        
        pairs = []
        
        for hash_id in hash_ids:
            
            if not self.modules_files_duplicates_storage.IsKing( hash_id ):
                
                continue
                
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is None:
                
                continue
                
            
            pairs_for_this_file = self._Execute( 'SELECT smaller_media_id, larger_media_id FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) ).fetchall()
            
            pairs.extend( pairs_for_this_file )
            
        
        if len( pairs ) == 0:
            
            return
            
        
        self._DeletePairsFromRowCacheAndAutoResolutionRules( pairs, only_for_this_file_service_key = only_for_this_file_service_key )
        
    
    def NotifyFilesLeavingCombinedLocalFileDomains( self, hash_ids ):
        
        if len( hash_ids ) == 0:
            
            return
            
        
        self.NotifyFilesLeavingDomains( hash_ids, only_for_this_file_service_key = CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
    
    def NotifyFilesLeavingLocalFileDomain( self, service_id, hash_ids ):
        
        if len( hash_ids ) == 0:
            
            return
            
        
        service_key = self.modules_services.GetServiceKey( service_id )
        
        self.NotifyFilesLeavingDomains( hash_ids, only_for_this_file_service_key = service_key )
        
    
    def NotifyFileLeavingHydrusLocalFileStorage( self, hash_id ):
        
        if self.modules_files_duplicates_storage.IsKing( hash_id ):
            
            self.RemovePotentialPairs( hash_id )
            
        
        self.modules_similar_files.StopSearchingFile( hash_id )
        
    
    def RemoveAlternateMember( self, media_id ):
        
        alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( media_id, do_not_create = True )
        
        if alternates_group_id is not None:
            
            alternates_media_ids = self.modules_files_duplicates_storage.GetAlternateMediaIds( alternates_group_id )
            
            self._Execute( 'DELETE FROM alternate_file_group_members WHERE media_id = ?;', ( media_id, ) )
            
            self._Execute( 'DELETE FROM confirmed_alternate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
            
            if len( alternates_media_ids ) == 1: # i.e. what we just removed was the last of the group
                
                self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id, ) )
                
                self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
                
            
            hash_ids = self.modules_files_duplicates_storage.GetDuplicateHashIds( media_id )
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def RemoveAlternateMemberFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.RemoveAlternateMember( media_id )
                
            
        
    
    def RemoveMediaIdMember( self, hash_id ):
        
        media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            king_hash_id = self.modules_files_duplicates_storage.GetKingHashId( media_id )
            
            if hash_id == king_hash_id:
                
                self.DissolveMediaId( media_id )
                
            else:
                
                self._Execute( 'DELETE FROM duplicate_file_members WHERE hash_id = ?;', ( hash_id, ) )
                
                self.modules_similar_files.ResetSearch( ( hash_id, ) )
                
            
        
    
    def RemoveMediaIdMemberFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            self.RemoveMediaIdMember( hash_id )
            
        
    
    def RemovePotentialPairs( self, hash_id ):
        
        media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            self.DeletePotentialDuplicatesForMediaId( media_id )
            
        
    
    def RemovePotentialPairsFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            self.RemovePotentialPairs( hash_id )
            
        
    
    def ResyncPotentialPairsToHydrusLocalFileStorage( self ):
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        num_files_cleared_out = 0
        
        try:
            
            job_status.SetStatusTitle( 'resyncing potential pairs to hydrus local file storage' )
            
            CG.client_controller.pub( 'message', job_status )
            
            job_status.SetStatusText( 'gathering data' )
            
            all_ids_we_are_tracking = self._Execute( 'SELECT DISTINCT king_hash_id, media_id FROM potential_duplicate_pairs CROSS JOIN duplicate_files ON ( potential_duplicate_pairs.smaller_media_id = duplicate_files.media_id OR potential_duplicate_pairs.larger_media_id = duplicate_files.media_id );' ).fetchall()
            
            all_king_hash_ids_we_are_tracking = { king_hash_id for ( king_hash_id, media_id ) in all_ids_we_are_tracking }
            
            good_king_hash_ids = self.modules_files_storage.FilterAllLocalHashIds( all_king_hash_ids_we_are_tracking )
            
            bad_king_hash_ids = all_king_hash_ids_we_are_tracking.difference( good_king_hash_ids )
            
            num_bad_king_hash_ids = len( bad_king_hash_ids )
            
            if num_bad_king_hash_ids > 0:
                
                all_bad_ids = [ ( king_hash_id, media_id ) for ( king_hash_id, media_id ) in all_ids_we_are_tracking if king_hash_id in bad_king_hash_ids ]
                
                for ( num_done, num_to_do, batch_of_bad_ids ) in HydrusLists.SplitListIntoChunksRich( all_bad_ids, 16 ):
                    
                    if job_status.IsCancelled():
                        
                        break
                        
                    
                    message = f'Clearing orphans: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
                    
                    job_status.SetStatusText( message )
                    job_status.SetGauge( num_done, num_to_do )
                    
                    for ( king_hash_id, media_id ) in batch_of_bad_ids:
                        
                        if job_status.IsCancelled():
                            
                            break
                            
                        
                        self.DeletePotentialDuplicatesForMediaId( media_id )
                        
                        self.modules_similar_files.StopSearchingFile( king_hash_id )
                        
                        num_files_cleared_out += 1
                        
                    
                
            
        finally:
            
            if num_files_cleared_out > 0:
                
                HydrusData.Print( f'During potential duplicate pair local storage resync, I cleared out pairs for {HydrusNumbers.ToHumanInt(num_files_cleared_out)} files.' )
                
                job_status.SetStatusText( f'Done! Pairs for {HydrusNumbers.ToHumanInt(num_files_cleared_out)} out-of-domain files cleared out.' )
                
            else:
                
                if job_status.IsCancelled():
                    
                    job_status.SetStatusText( 'Cancelled!' )
                    
                else:
                    
                    job_status.SetStatusText( 'Done! No orphan pairs found!' )
                    
                
            
            job_status.DeleteGauge()
            
            job_status.Finish()
            
        
    
    def SetAlternates( self, superior_media_id, mergee_media_id ):
        """
        If mergee_media_id has a different alternates group id, this guy is going to merge, and the mergee alternates group disappears.
        """
        
        if superior_media_id == mergee_media_id:
            
            return
            
        
        # let's clear out any outstanding potentials. whether this is a valid connection or not, we don't want to see it again
        
        smaller_media_id = min( superior_media_id, mergee_media_id )
        larger_media_id = max( superior_media_id, mergee_media_id )
        
        self.DeletePotentialDuplicates( [ ( smaller_media_id, larger_media_id ) ] )
        
        # now check if we should be making a new relationship
        
        alternates_group_id_a = self.modules_files_duplicates_storage.GetAlternatesGroupId( superior_media_id )
        alternates_group_id_b = self.modules_files_duplicates_storage.GetAlternatesGroupId( mergee_media_id )
        
        if alternates_group_id_a != alternates_group_id_b:
            
            # ok, if A-alt-B, then A-alt-anything-alt-B, so we need to merge B into A
            
            # first, copy other false positive records from B to A
            
            false_positive_records = self._STS( self._Execute( 'SELECT smaller_alternates_group_id FROM duplicate_false_positives WHERE larger_alternates_group_id = ?;', ( alternates_group_id_b, ) ) )
            false_positive_records.update( self._STI( self._Execute( 'SELECT larger_alternates_group_id FROM duplicate_false_positives WHERE smaller_alternates_group_id = ?;', ( alternates_group_id_b, ) ) ) )
            
            for alternates_group_id_x in false_positive_records:
                
                if alternates_group_id_x in ( alternates_group_id_a, alternates_group_id_b ):
                    
                    continue
                    
                
                self.SetFalsePositive( alternates_group_id_a, alternates_group_id_x )
                
            
            # now move all B to A
            # all existing confirmed B/X pairs stay intact, no worries
            
            self._Execute( 'UPDATE alternate_file_group_members SET alternates_group_id = ? WHERE alternates_group_id = ?;', ( alternates_group_id_a, alternates_group_id_b ) )
            
            # remove empty B
            
            self.DissolveAlternatesGroupId( alternates_group_id_b )
            
        
        # in future, I can tune this to consider alternate labels and indices. alternates with different labels and indices are not appropriate for potentials, so we can add more rows here
        
        self._Execute( 'INSERT OR IGNORE INTO confirmed_alternate_pairs ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );', ( smaller_media_id, larger_media_id ) )
        
    
    def SetDuplicates( self, superior_media_id, mergee_media_id ):
        
        if superior_media_id == mergee_media_id:
            
            return
            
        
        superior_alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( superior_media_id )
        mergee_alternates_group_id = self.modules_files_duplicates_storage.GetAlternatesGroupId( mergee_media_id, do_not_create = True )
        
        if mergee_alternates_group_id is not None:
            
            # if they are not currently in the same alternates group, let's merge them!
            # any false positive relations the mergee_media_id may have had are also transitively moved over nicely
            
            if superior_alternates_group_id != mergee_alternates_group_id:
                
                self.SetAlternates( superior_media_id, mergee_media_id )
                
                # mergee_alternates_group_id no longer exists
                
            
        
        # copy other potentials from the mergee to the superior
        
        existing_potential_info = set( self._Execute( 'SELECT smaller_media_id, distance FROM potential_duplicate_pairs WHERE larger_media_id = ?;', ( mergee_media_id, ) ) )
        existing_potential_info.update( self._Execute( 'SELECT larger_media_id, distance FROM potential_duplicate_pairs WHERE smaller_media_id = ?;', ( mergee_media_id, ) ) )
        
        potential_duplicate_media_ids_and_distances = [ ( media_id_x, distance ) for ( media_id_x, distance ) in existing_potential_info if media_id_x not in ( mergee_media_id, superior_media_id ) ]
        
        if len( potential_duplicate_media_ids_and_distances ) > 0:
            
            self.AddPotentialDuplicates( superior_media_id, potential_duplicate_media_ids_and_distances )
            
        
        # copy any previous confirmed alt pair that B has to A
        
        mergee_confirmed_alternates = self._STS( self._Execute( 'SELECT smaller_media_id FROM confirmed_alternate_pairs WHERE larger_media_id = ?;', ( mergee_media_id, ) ) )
        mergee_confirmed_alternates.update( self._STI( self._Execute( 'SELECT larger_media_id FROM confirmed_alternate_pairs WHERE smaller_media_id = ?;', ( mergee_media_id, ) ) ) )
        
        for media_id_x in mergee_confirmed_alternates:
            
            if media_id_x in ( mergee_media_id, superior_media_id ):
                
                continue
                
            
            self.SetAlternates( superior_media_id, media_id_x )
            
        
        # actually move the members over
        
        self._Execute( 'UPDATE duplicate_file_members SET media_id = ? WHERE media_id = ?;', ( superior_media_id, mergee_media_id ) )
        
        # clear out empty duplicate group
        
        self.DissolveMediaId( mergee_media_id )
        
    
    def SetFalsePositive( self, alternates_group_id_a, alternates_group_id_b ):
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return
            
        
        self.ClearPotentialsBetweenAlternatesGroups( alternates_group_id_a, alternates_group_id_b )
        
        smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
        larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
        
        self._Execute( 'INSERT OR IGNORE INTO duplicate_false_positives ( smaller_alternates_group_id, larger_alternates_group_id ) VALUES ( ?, ? );', ( smaller_alternates_group_id, larger_alternates_group_id ) )
        
    
    def SetKing( self, king_hash_id, media_id ):
        
        self._Execute( 'UPDATE duplicate_files SET king_hash_id = ? WHERE media_id = ?;', ( king_hash_id, media_id ) )
        
    
    def SetKingFromHash( self, hash ):
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        media_id = self.modules_files_duplicates_storage.GetMediaId( hash_id )
        
        self.SetKing( hash_id, media_id )
        
    
