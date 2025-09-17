import collections
import collections.abc
import itertools
import random
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSimilarFiles
from hydrus.client.db import ClientDBFilesDuplicatesAutoResolutionStorage
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext

class ClientDBFilesDuplicates( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles,
        modules_files_duplicates_auto_resolution_storage: ClientDBFilesDuplicatesAutoResolutionStorage.ClientDBFilesDuplicatesAutoResolutionStorage
        ):
        
        super().__init__( 'client file duplicates', cursor )
        
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_similar_files = modules_similar_files
        self.modules_files_duplicates_auto_resolution_storage = modules_files_duplicates_auto_resolution_storage
        
        self._location_contexts_to_potential_duplicate_id_pairs_and_distances_rows = {}
        
        self._service_ids_to_content_types_to_outstanding_local_processing = collections.defaultdict( dict )
        
    
    def _GetFileHashIdsByDuplicateType( self, db_location_context: ClientDBFilesStorage.DBLocationContext, hash_id: int, duplicate_type: int ) -> list[ int ]:
        
        dupe_hash_ids = set()
        
        if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    false_positive_alternates_group_ids = self.GetFalsePositiveAlternatesGroupIds( alternates_group_id )
                    
                    false_positive_alternates_group_ids.discard( alternates_group_id )
                    
                    false_positive_media_ids = set()
                    
                    for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                        
                        false_positive_media_ids.update( self.GetAlternateMediaIds( false_positive_alternates_group_id ) )
                        
                    
                    for false_positive_media_id in false_positive_media_ids:
                        
                        best_king_hash_id = self.GetBestKingId( false_positive_media_id, db_location_context )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_ALTERNATE:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    alternates_media_ids = self._STS( self._Execute( 'SELECT media_id FROM alternate_file_group_members WHERE alternates_group_id = ?;', ( alternates_group_id, ) ) )
                    
                    alternates_media_ids.discard( media_id )
                    
                    for alternates_media_id in alternates_media_ids:
                        
                        best_king_hash_id = self.GetBestKingId( alternates_media_id, db_location_context )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_MEMBER:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                media_hash_ids = self.GetDuplicateHashIds( media_id, db_location_context = db_location_context )
                
                dupe_hash_ids.update( media_hash_ids )
                
            
        elif duplicate_type == HC.DUPLICATE_KING:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                best_king_hash_id = self.GetBestKingId( media_id, db_location_context )
                
                if best_king_hash_id is not None:
                    
                    dupe_hash_ids.add( best_king_hash_id )
                    
                
            
        elif duplicate_type == HC.DUPLICATE_POTENTIAL:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                table_join = self.GetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
                
                for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT smaller_media_id, larger_media_id FROM {} WHERE smaller_media_id = ? OR larger_media_id = ?;'.format( table_join ), ( media_id, media_id ) ).fetchall():
                    
                    if smaller_media_id != media_id:
                        
                        potential_media_id = smaller_media_id
                        
                    else:
                        
                        potential_media_id = larger_media_id
                        
                    
                    best_king_hash_id = self.GetBestKingId( potential_media_id, db_location_context )
                    
                    if best_king_hash_id is not None:
                        
                        dupe_hash_ids.add( best_king_hash_id )
                        
                    
                
            
        
        dupe_hash_ids.discard( hash_id )
        
        dupe_hash_ids = list( dupe_hash_ids )
        
        dupe_hash_ids.insert( 0, hash_id )
        
        return dupe_hash_ids
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.duplicate_false_positives' ] = [
            ( [ 'larger_alternates_group_id', 'smaller_alternates_group_id' ], True, 469 )
        ]
        
        index_generation_dict[ 'main.potential_duplicate_pairs' ] = [
            ( [ 'larger_media_id', 'smaller_media_id' ], True, 469 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.alternate_file_groups' : ( 'CREATE TABLE IF NOT EXISTS {} ( alternates_group_id INTEGER PRIMARY KEY );', 469 ),
            'main.alternate_file_group_members' : ( 'CREATE TABLE IF NOT EXISTS {} ( alternates_group_id INTEGER, media_id INTEGER UNIQUE, PRIMARY KEY ( alternates_group_id, media_id ) );', 469 ),
            'main.confirmed_alternate_pairs' : ( 'CREATE TABLE IF NOT EXISTS {} ( smaller_media_id INTEGER, larger_media_id INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );', 469 ),
            'main.duplicate_files' : ( 'CREATE TABLE IF NOT EXISTS {} ( media_id INTEGER PRIMARY KEY, king_hash_id INTEGER UNIQUE );', 469 ),
            'main.duplicate_file_members' : ( 'CREATE TABLE IF NOT EXISTS {} ( media_id INTEGER, hash_id INTEGER UNIQUE, PRIMARY KEY ( media_id, hash_id ) );', 469 ),
            'main.duplicate_false_positives' : ( 'CREATE TABLE IF NOT EXISTS {} ( smaller_alternates_group_id INTEGER, larger_alternates_group_id INTEGER, PRIMARY KEY ( smaller_alternates_group_id, larger_alternates_group_id ) );', 469 ),
            'main.potential_duplicate_pairs' : ( 'CREATE TABLE IF NOT EXISTS {} ( smaller_media_id INTEGER, larger_media_id INTEGER, distance INTEGER, PRIMARY KEY ( smaller_media_id, larger_media_id ) );', 469 )
        }
        
    
    def _NotifyChangeToPotentialDuplicatePairs( self ):
        
        self._location_contexts_to_potential_duplicate_id_pairs_and_distances_rows = {}
        
    
    def AddPotentialDuplicates( self, media_id, potential_duplicate_media_ids_and_distances ):
        
        inserts = []
        
        for ( potential_duplicate_media_id, distance ) in potential_duplicate_media_ids_and_distances:
            
            if potential_duplicate_media_id == media_id: # already duplicates!
                
                continue
                
            
            if self.MediasAreFalsePositive( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            if self.MediasAreConfirmedAlternates( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            # if they are alternates with different alt label and index, do not add
            # however this _could_ be folded into areconfirmedalts on the setalt event--any other alt with diff label/index also gets added
            
            smaller_media_id = min( media_id, potential_duplicate_media_id )
            larger_media_id = max( media_id, potential_duplicate_media_id )
            
            inserts.append( ( smaller_media_id, larger_media_id, distance ) )
            
        
        if len( inserts ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO potential_duplicate_pairs ( smaller_media_id, larger_media_id, distance ) VALUES ( ?, ?, ? );', inserts )
            
            self._NotifyChangeToPotentialDuplicatePairs()
            
            self.modules_files_duplicates_auto_resolution_storage.NotifyNewPotentialDuplicatePairsAdded(
                [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id, distance ) in inserts ]
            )
            
        
    
    def AlternatesGroupsAreFalsePositive( self, alternates_group_id_a, alternates_group_id_b ):
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return False
            
        
        smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
        larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
        
        result = self._Execute( 'SELECT 1 FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', ( smaller_alternates_group_id, larger_alternates_group_id ) ).fetchone()
        
        false_positive_pair_found = result is not None
        
        return false_positive_pair_found
        
    
    def ClearInternalFalsePositivesHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        media_ids = { self.GetMediaId( hash_id, do_not_create = True ) for hash_id in hash_ids }
        
        media_ids.discard( None )
        
        if len( media_ids ) < 2:
            
            return 0
            
        
        alternates_group_ids = { self.GetAlternatesGroupId( media_id, do_not_create = True ) for media_id in media_ids }
        
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
        
        media_ids = { self.GetMediaId( hash_id, do_not_create = True ) for hash_id in hash_ids }
        
        media_ids.discard( None )
        
        if len( media_ids ) == 0:
            
            return 0
            
        
        alternates_group_ids = { self.GetAlternatesGroupId( media_id, do_not_create = True ) for media_id in media_ids }
        
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
        
        media_ids_a = self.GetAlternateMediaIds( alternates_group_id_a )
        media_ids_b = self.GetAlternateMediaIds( alternates_group_id_b )
        
        self.ClearPotentialsBetweenMedias( media_ids_a, media_ids_b )
        
    
    def DeleteAllPotentialDuplicatePairs( self ):
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs;' )
        
        self._NotifyChangeToPotentialDuplicatePairs()
        
        self.modules_files_duplicates_auto_resolution_storage.DeleteAllPotentialDuplicatePairs()
        
        self.modules_similar_files.ResetSearchForAll()
        
    
    def DeletePotentialDuplicates( self, pairs ):
        
        if len( pairs ) > 0:
            
            self._ExecuteMany( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', pairs )
            
            self._NotifyChangeToPotentialDuplicatePairs()
            
            self.modules_files_duplicates_auto_resolution_storage.NotifyExistingPotentialDuplicatePairsRemoved( pairs )
            
        
    
    def DeletePotentialDuplicatesForMediaId( self, media_id: int ):
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
        
        if self._GetRowCount() > 0:
            
            self._NotifyChangeToPotentialDuplicatePairs()
            
        
        self.modules_files_duplicates_auto_resolution_storage.NotifyMediaIdNoLongerPotential( media_id )
        
    
    def DissolveAlternatesGroupId( self, alternates_group_id ):
        
        media_ids = self.GetAlternateMediaIds( alternates_group_id )
        
        for media_id in media_ids:
            
            self.DissolveMediaId( media_id )
            
        
        self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id, ) )
        self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
        
    
    def DissolveAlternatesGroupIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.GetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    self.DissolveAlternatesGroupId( alternates_group_id )
                    
                
            
        
    
    def DissolveMediaId( self, media_id ):
        
        self.RemoveAlternateMember( media_id )
        
        self.DeletePotentialDuplicatesForMediaId( media_id )
        
        hash_ids = self.GetDuplicateHashIds( media_id )
        
        self._Execute( 'DELETE FROM duplicate_file_members WHERE media_id = ?;', ( media_id, ) )
        self._Execute( 'DELETE FROM duplicate_files WHERE media_id = ?;', ( media_id, ) )
        
        if len( hash_ids ) > 0:
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def DissolveMediaIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.DissolveMediaId( media_id )
                
            
        
    
    def FilterKingHashIds( self, allowed_hash_ids ):
        
        # can't just pull explicit king_hash_ids, since files that do not have a media_id are still kings
        # kings = hashes - explicitly not kings
        
        if not isinstance( allowed_hash_ids, set ):
            
            allowed_hash_ids = set( allowed_hash_ids )
            
        
        with self._MakeTemporaryIntegerTable( allowed_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            explicit_king_hash_ids = self._STS( self._Execute( 'SELECT king_hash_id FROM {} CROSS JOIN duplicate_files ON ( {}.hash_id = duplicate_files.king_hash_id );'.format( temp_hash_ids_table_name, temp_hash_ids_table_name ) ) )
            
            all_duplicate_member_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN duplicate_file_members USING ( hash_id );'.format( temp_hash_ids_table_name ) ) )
            
        
        all_non_king_hash_ids = all_duplicate_member_hash_ids.difference( explicit_king_hash_ids )
        
        return allowed_hash_ids.difference( all_non_king_hash_ids )
        
    
    def FilterMediaIdPairs( self, db_location_context: ClientDBFilesStorage.DBLocationContext, media_id_pairs ):
        
        if len( media_id_pairs ) == 0:
            
            return []
            
        
        # this is pretty wonked out due to me not wanting to force db_location_context to make a single table
        
        all_media_ids = { i for i in itertools.chain.from_iterable( media_id_pairs ) }
        
        with self._MakeTemporaryIntegerTable( all_media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            hash_ids_to_media_ids = dict( self._Execute( 'SELECT hash_id, media_id FROM {} CROSS JOIN {} USING ( media_id );'.format( temp_media_ids_table_name, 'duplicate_file_members' ) ) )
            
        
        all_hash_ids = set( hash_ids_to_media_ids.keys() )
        
        good_hash_ids = self.modules_files_storage.FilterHashIds( db_location_context.location_context, all_hash_ids )
        
        good_media_ids = { hash_ids_to_media_ids[ hash_id ] for hash_id in good_hash_ids }
        
        good_media_id_pairs = [ ( smaller_media_id, larger_media_id ) for ( smaller_media_id, larger_media_id ) in media_id_pairs if smaller_media_id in good_media_ids and larger_media_id in good_media_ids ]
        
        return good_media_id_pairs
        
    
    def FilterExistingPotentialDuplicatePairs( self, potential_pair_ids_table_name: str ):
        """
        Which of these actually exist in storage?
        """
        
        existing_pairs = set( self._Execute( f'SELECT smaller_media_id, larger_media_id FROM {potential_pair_ids_table_name} CROSS JOIN potential_duplicate_pairs ON ( {potential_pair_ids_table_name}.smaller_media_id = potential_duplicate_pairs.smaller_media_id AND {potential_pair_ids_table_name}.larger_media_id = potential_duplicate_pairs.larger_media_id );' ) )
        
        return existing_pairs
        
    
    def GetAlternatesGroupId( self, media_id, do_not_create = False ):
        
        result = self._Execute( 'SELECT alternates_group_id FROM alternate_file_group_members WHERE media_id = ?;', ( media_id, ) ).fetchone()
        
        if result is None:
            
            if do_not_create:
                
                return None
                
            
            self._Execute( 'INSERT INTO alternate_file_groups DEFAULT VALUES;' )
            
            alternates_group_id = self._GetLastRowId()
            
            self._Execute( 'INSERT INTO alternate_file_group_members ( alternates_group_id, media_id ) VALUES ( ?, ? );', ( alternates_group_id, media_id ) )
            
        else:
            
            ( alternates_group_id, ) = result
            
        
        return alternates_group_id
        
    
    def GetAlternateMediaIds( self, alternates_group_id ):
        
        media_ids = self._STS( self._Execute( 'SELECT media_id FROM alternate_file_group_members WHERE alternates_group_id = ?;', ( alternates_group_id, ) ) )
        
        return media_ids
        
    
    def GetBestKingId( self, media_id, db_location_context: ClientDBFilesStorage.DBLocationContext, allowed_hash_ids = None, preferred_hash_ids = None ):
        
        media_hash_ids = self.GetDuplicateHashIds( media_id, db_location_context = db_location_context )
        
        if allowed_hash_ids is not None:
            
            media_hash_ids.intersection_update( allowed_hash_ids )
            
        
        if len( media_hash_ids ) > 0:
            
            king_hash_id = self.GetKingHashId( media_id )
            
            if preferred_hash_ids is not None:
                
                preferred_hash_ids = media_hash_ids.intersection( preferred_hash_ids )
                
                if len( preferred_hash_ids ) > 0:
                    
                    if king_hash_id not in preferred_hash_ids:
                        
                        king_hash_id = random.choice( list( preferred_hash_ids ) )
                        
                    
                    return king_hash_id
                    
                
            
            if king_hash_id not in media_hash_ids:
                
                king_hash_id = random.choice( list( media_hash_ids ) )
                
            
            return king_hash_id
            
        
        return None
        
    
    def GetDuplicateHashIds( self, media_id, db_location_context: ClientDBFilesStorage.DBLocationContext = None ):
        
        table_join = 'duplicate_file_members'
        
        if db_location_context is not None:
            
            if not db_location_context.SingleTableIsFast():
                
                hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} WHERE media_id = ?;'.format( table_join ), ( media_id, ) ) )
                
                hash_ids = self.modules_files_storage.FilterHashIds( db_location_context.location_context, hash_ids )
                
                return hash_ids
                
            
            table_join = db_location_context.GetTableJoinLimitedByFileDomain( table_join )
            
        
        hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} WHERE media_id = ?;'.format( table_join ), ( media_id, ) ) )
        
        return hash_ids
        
    
    def GetDuplicatesHashIds( self, media_ids, db_location_context: ClientDBFilesStorage.DBLocationContext = None ):
        
        with self._MakeTemporaryIntegerTable( media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            table_join = '{} CROSS JOIN {} USING ( media_id )'.format( temp_media_ids_table_name, 'duplicate_file_members' )
            
            if db_location_context is not None:
                
                table_join = db_location_context.GetTableJoinLimitedByFileDomain( table_join )
                
            
            hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
            
        
        return hash_ids
        
    
    def GetFalsePositiveAlternatesGroupIds( self, alternates_group_id ):
        
        false_positive_alternates_group_ids = set()
        
        results = self._Execute( 'SELECT smaller_alternates_group_id, larger_alternates_group_id FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) ).fetchall()
        
        for ( smaller_alternates_group_id, larger_alternates_group_id ) in results:
            
            false_positive_alternates_group_ids.add( smaller_alternates_group_id )
            false_positive_alternates_group_ids.add( larger_alternates_group_id )
            
        
        return false_positive_alternates_group_ids
        
    
    def GetFileDuplicateInfo( self, location_context, hash ):
        
        result_dict = {}
        
        result_dict[ 'is_king' ] = True
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        counter = collections.Counter()
        
        media_id = self.GetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
            
            all_potential_pairs = self._Execute( 'SELECT DISTINCT smaller_media_id, larger_media_id FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id, ) ).fetchall()
            
            potential_pairs = self.FilterMediaIdPairs( db_location_context, all_potential_pairs )
            
            if len( potential_pairs ) > 0:
                
                counter[ HC.DUPLICATE_POTENTIAL ] = len( potential_pairs )
                
            
            king_hash_id = self.GetKingHashId( media_id )
            
            result_dict[ 'is_king' ] = king_hash_id == hash_id
            
            media_hash_ids = self.GetDuplicateHashIds( media_id, db_location_context = db_location_context )
            
            num_other_dupe_members = len( media_hash_ids ) - 1
            
            if num_other_dupe_members > 0:
                
                counter[ HC.DUPLICATE_MEMBER ] = num_other_dupe_members
                
            
            alternates_group_id = self.GetAlternatesGroupId( media_id, do_not_create = True )
            
            if alternates_group_id is not None:
                
                alt_media_ids = self.GetAlternateMediaIds( alternates_group_id )
                
                alt_media_ids.discard( media_id )
                
                for alt_media_id in alt_media_ids:
                    
                    alt_hash_ids = self.GetDuplicateHashIds( alt_media_id, db_location_context = db_location_context )
                    
                    if len( alt_hash_ids ) > 0:
                        
                        counter[ HC.DUPLICATE_ALTERNATE ] += 1
                        
                        smaller_media_id = min( media_id, alt_media_id )
                        larger_media_id = max( media_id, alt_media_id )
                        
                        result = self._Execute( 'SELECT 1 FROM confirmed_alternate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) ).fetchone()
                        
                        if result is not None:
                            
                            counter[ HC.DUPLICATE_CONFIRMED_ALTERNATE ] += 1
                            
                        
                    
                
                false_positive_alternates_group_ids = self.GetFalsePositiveAlternatesGroupIds( alternates_group_id )
                
                false_positive_alternates_group_ids.discard( alternates_group_id )
                
                for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                    
                    fp_media_ids = self.GetAlternateMediaIds( false_positive_alternates_group_id )
                    
                    for fp_media_id in fp_media_ids:
                        
                        fp_hash_ids = self.GetDuplicateHashIds( fp_media_id, db_location_context = db_location_context )
                        
                        if len( fp_hash_ids ) > 0:
                            
                            counter[ HC.DUPLICATE_FALSE_POSITIVE ] += 1
                            
                        
                    
                
            
        
        result_dict[ 'counts' ] = counter
        
        return result_dict
        
    
    def GetFileRelationshipsForAPI( self, location_context: ClientLocation.LocationContext, hashes: collections.abc.Collection[ bytes ] ):
        
        hashes_to_file_relationships = {}
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
        
        duplicate_types_to_fetch = (
            HC.DUPLICATE_POTENTIAL,
            HC.DUPLICATE_MEMBER,
            HC.DUPLICATE_FALSE_POSITIVE,
            HC.DUPLICATE_ALTERNATE
        )
        
        for hash in hashes:
            
            file_relationships_dict = {}
            
            hash_id = self.modules_hashes_local_cache.GetHashId( hash )
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is None:
                
                king_hash_id = hash_id
                
            else:
                
                king_hash_id = self.GetKingHashId( media_id )
                
            
            if king_hash_id == hash_id:
                
                file_relationships_dict[ 'is_king' ] = True
                file_relationships_dict[ 'king' ] = hash.hex()
                
            else:
                
                file_relationships_dict[ 'is_king' ] = False
                file_relationships_dict[ 'king' ] = self.modules_hashes_local_cache.GetHash( king_hash_id ).hex()
                
            
            filtered_hash_ids = self.modules_files_storage.FilterHashIds( db_location_context.location_context, { hash_id } )
            
            file_relationships_dict[ 'king_is_on_file_domain' ] = len( filtered_hash_ids ) > 0
            
            filtered_hash_ids = self.modules_files_storage.FilterHashIds( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ), { hash_id } )
            
            file_relationships_dict[ 'king_is_local' ] = len( filtered_hash_ids ) > 0
            
            if media_id is None:
                
                for duplicate_type in duplicate_types_to_fetch:
                    
                    file_relationships_dict[ str( duplicate_type ) ] = []
                    
                
            else:
                
                for duplicate_type in ( HC.DUPLICATE_POTENTIAL, HC.DUPLICATE_MEMBER, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                    
                    dupe_hash_ids = list( self._GetFileHashIdsByDuplicateType( db_location_context, hash_id, duplicate_type ) )
                    
                    dupe_hash_ids.sort()
                    
                    if hash_id in dupe_hash_ids:
                        
                        dupe_hash_ids.remove( hash_id )
                        
                    
                    file_relationships_dict[ str( duplicate_type ) ] = [ h.hex() for h in self.modules_hashes_local_cache.GetHashes( dupe_hash_ids ) ]
                    
                
            
            hashes_to_file_relationships[ hash.hex() ] = file_relationships_dict
            
        
        return hashes_to_file_relationships
        
    
    def GetFileHashesByDuplicateType( self, location_context: ClientLocation.LocationContext, hash: bytes, duplicate_type: int ) -> list[ bytes ]:
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
        
        dupe_hash_ids = self._GetFileHashIdsByDuplicateType( db_location_context, hash_id, duplicate_type )
        
        dupe_hashes = self.modules_hashes_local_cache.GetHashes( dupe_hash_ids )
        
        return dupe_hashes
        
    
    def GetHashIdsFromDuplicateCountPredicate( self, db_location_context: ClientDBFilesStorage.DBLocationContext, operator, num_relationships, dupe_type ):
        
        # doesn't work for '= 0' or '< 1'
        
        if operator == HC.UNICODE_APPROX_EQUAL:
            
            lower_bound = 0.8 * num_relationships
            upper_bound = 1.2 * num_relationships
            
            def filter_func( count ):
                
                return lower_bound < count < upper_bound
                
            
        elif operator == '<':
            
            def filter_func( count ):
                
                return count < num_relationships
                
            
        elif operator == '>':
            
            def filter_func( count ):
                
                return count > num_relationships
                
            
        elif operator == '=':
            
            def filter_func( count ):
                
                return count == num_relationships
                
            
        else:
            
            raise NotImplementedError( f'Unknown operator "{operator}"!' )
            
        
        hash_ids = set()
        
        if dupe_type == HC.DUPLICATE_FALSE_POSITIVE:
            
            alternates_group_ids_to_valid_for_file_domain = {}
            alternates_group_ids_to_false_positives = collections.defaultdict( list )
            
            query = 'SELECT smaller_alternates_group_id, larger_alternates_group_id FROM duplicate_false_positives;'
            
            for ( alternates_group_id_a, alternates_group_id_b ) in self._Execute( query ):
                
                alternates_group_ids_to_false_positives[ alternates_group_id_a ].append( alternates_group_id_b )
                alternates_group_ids_to_false_positives[ alternates_group_id_b ].append( alternates_group_id_a )
                
            
            for ( alternates_group_id, false_positive_alternates_group_ids ) in alternates_group_ids_to_false_positives.items():
                
                count = 0
                
                for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                    
                    if false_positive_alternates_group_id not in alternates_group_ids_to_valid_for_file_domain:
                        
                        valid = False
                        
                        fp_media_ids = self.GetAlternateMediaIds( false_positive_alternates_group_id )
                        
                        for fp_media_id in fp_media_ids:
                            
                            fp_hash_ids = self.GetDuplicateHashIds( fp_media_id, db_location_context = db_location_context )
                            
                            if len( fp_hash_ids ) > 0:
                                
                                valid = True
                                
                                break
                                
                            
                        
                        alternates_group_ids_to_valid_for_file_domain[ false_positive_alternates_group_id ] = valid
                        
                    
                    if alternates_group_ids_to_valid_for_file_domain[ false_positive_alternates_group_id ]:
                        
                        count += 1
                        
                    
                
                if filter_func( count ):
                    
                    media_ids = self.GetAlternateMediaIds( alternates_group_id )
                    
                    hash_ids.update( self.GetDuplicatesHashIds( media_ids, db_location_context = db_location_context ) )
                    
                
            
        elif dupe_type == HC.DUPLICATE_ALTERNATE:
            
            query = 'SELECT alternates_group_id, COUNT( * ) FROM alternate_file_group_members GROUP BY alternates_group_id;'
            
            results = self._Execute( query ).fetchall()
            
            for ( alternates_group_id, count ) in results:
                
                count -= 1 # num relationships is number group members - 1
                
                media_ids = self.GetAlternateMediaIds( alternates_group_id )
                
                alternates_group_id_hash_ids = []
                
                for media_id in media_ids:
                    
                    media_id_hash_ids = self.GetDuplicateHashIds( media_id, db_location_context = db_location_context )
                    
                    if len( media_id_hash_ids ) == 0:
                        
                        # this alternate relation does not count for our current file domain, so it should not contribute to the count
                        count -= 1
                        
                    else:
                        
                        alternates_group_id_hash_ids.extend( media_id_hash_ids )
                        
                    
                
                if filter_func( count ):
                    
                    hash_ids.update( alternates_group_id_hash_ids )
                    
                
            
        elif dupe_type == HC.DUPLICATE_MEMBER:
            
            table_join = db_location_context.GetTableJoinLimitedByFileDomain( 'duplicate_file_members' )
            
            query = 'SELECT media_id, COUNT( * ) FROM {} GROUP BY media_id;'.format( table_join )
            
            media_ids = []
            
            for ( media_id, count ) in self._Execute( query ):
                
                count -= 1
                
                if filter_func( count ):
                    
                    media_ids.append( media_id )
                    
                
            
            hash_ids = self.GetDuplicatesHashIds( media_ids, db_location_context = db_location_context )
            
        elif dupe_type == HC.DUPLICATE_POTENTIAL:
            
            table_join = self.GetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
            
            smaller_query = 'SELECT smaller_media_id, COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} ) GROUP BY smaller_media_id;'.format( table_join )
            larger_query = 'SELECT larger_media_id, COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} ) GROUP BY larger_media_id;'.format( table_join )
            
            media_ids_to_counts = collections.Counter()
            
            for ( media_id, count ) in self._Execute( smaller_query ):
                
                media_ids_to_counts[ media_id ] += count
                
            
            for ( media_id, count ) in self._Execute( larger_query ):
                
                media_ids_to_counts[ media_id ] += count
                
            
            media_ids = [ media_id for ( media_id, count ) in media_ids_to_counts.items() if filter_func( count ) ]
            
            hash_ids = self.GetDuplicatesHashIds( media_ids, db_location_context = db_location_context )
            
        
        return hash_ids
        
    
    def GetKingHashId( self, media_id ) -> int:
        
        ( king_hash_id, ) = self._Execute( 'SELECT king_hash_id FROM duplicate_files WHERE media_id = ?;', ( media_id, ) ).fetchone()
        
        return king_hash_id
        
    
    def GetKingHashIds( self, db_location_context: ClientDBFilesStorage.DBLocationContext, media_ids: set[ int ] ):
        """
        This guy won't filter to the db location context when it is complicated, but he will always return kings.
        """
        
        with self._MakeTemporaryIntegerTable( media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            if db_location_context.SingleTableIsFast():
                
                files_table_name = db_location_context.GetSingleFilesTableName()
                
                return self._STS( self._Execute( f'SELECT king_hash_id FROM {temp_media_ids_table_name} CROSS JOIN duplicate_files USING ( media_id ) CROSS JOIN {files_table_name} ON ( duplicate_files.king_hash_id = {files_table_name}.hash_id );' ) )
                
            
            return self._STS( self._Execute( f'SELECT king_hash_id FROM {temp_media_ids_table_name} CROSS JOIN duplicate_files USING ( media_id );' ) )
            
        
    
    def GetMediaId( self, hash_id, do_not_create = False ):
        
        result = self._Execute( 'SELECT media_id FROM duplicate_file_members WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            if do_not_create:
                
                return None
                
            
            # adding safety check to catch desynced database
            result = self._Execute( 'SELECT media_id FROM duplicate_files WHERE king_hash_id = ?;', ( hash_id, ) ).fetchone()
            
            if result is None:
                
                self._Execute( 'INSERT INTO duplicate_files ( king_hash_id ) VALUES ( ? );', ( hash_id, ) )
                
                media_id = self._GetLastRowId()
                
            else:
                
                ( media_id, ) = result
                
                HydrusData.Print( f'When looking for the media_id {media_id} of hash_id {hash_id}, it did not have a member row but did have a definiton row!' )
                
            
            self._Execute( 'INSERT INTO duplicate_file_members ( media_id, hash_id ) VALUES ( ?, ? );', ( media_id, hash_id ) )
            
        else:
            
            ( media_id, ) = result
            
        
        return media_id
        
    
    def GetPotentialDuplicateIdPairsAndDistances( self, location_context: ClientLocation.LocationContext ):
        
        if location_context not in self._location_contexts_to_potential_duplicate_id_pairs_and_distances_rows:
            
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
                    
                
            
            self._location_contexts_to_potential_duplicate_id_pairs_and_distances_rows[ location_context ] = rows
            
        
        return ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances( self._location_contexts_to_potential_duplicate_id_pairs_and_distances_rows[ location_context ] )
        
    
    def GetPotentialDuplicatePairsTableJoinGetInitialTablesAndPreds( self, pixel_dupes_preference: int, max_hamming_distance: int, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        # little note but the 'master_potential_duplicate_pairs_table_name' needs a distance column! not just the media pair
        
        tables = [
            master_potential_duplicate_pairs_table_name,
            'duplicate_files AS duplicate_files_smaller',
            'duplicate_files AS duplicate_files_larger'
        ]
        
        join_predicates = [ f'{master_potential_duplicate_pairs_table_name}.smaller_media_id = duplicate_files_smaller.media_id AND {master_potential_duplicate_pairs_table_name}.larger_media_id = duplicate_files_larger.media_id' ]
        
        if pixel_dupes_preference != ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
            
            join_predicates.append( 'distance <= {}'.format( max_hamming_distance ) )
            
        
        if pixel_dupes_preference in ( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            # OK we are adding the files_info gubbins here because my current pixel hash does not include dimension data!!!
            # thus a purely black image of 100x500 is matching another of 200x250
            # if and when we tuck the resolution into the start of the pixel hash and trigger a complete wipe and regen, we can remove the patch
            
            predicate_parts = [
                'duplicate_files_smaller.king_hash_id = pixel_hash_map_smaller.hash_id',
                'duplicate_files_larger.king_hash_id = pixel_hash_map_larger.hash_id',
                'pixel_hash_map_smaller.pixel_hash_id = pixel_hash_map_larger.pixel_hash_id',
                'duplicate_files_smaller.king_hash_id = pixel_files_info_smaller.hash_id',
                'duplicate_files_larger.king_hash_id = pixel_files_info_larger.hash_id',
                'pixel_files_info_smaller.width = pixel_files_info_larger.width'
            ]
            
            join_predicate_pixel_dupes = ' AND '.join( predicate_parts )
            
            if pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
                
                tables.extend( [
                    'pixel_hash_map AS pixel_hash_map_smaller',
                    'pixel_hash_map AS pixel_hash_map_larger',
                    'files_info AS pixel_files_info_smaller',
                    'files_info AS pixel_files_info_larger'
                ] )
                
                join_predicates.append( join_predicate_pixel_dupes )
                
            elif pixel_dupes_preference == ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED:
                
                # can't do "AND NOT {}", or the join will just give you the million rows where it isn't true. we want 'AND NEVER {}', and quick
                
                select_statement = 'SELECT 1 FROM pixel_hash_map AS pixel_hash_map_smaller, pixel_hash_map as pixel_hash_map_larger, files_info AS pixel_files_info_smaller, files_info AS pixel_files_info_larger ON ( {} )'.format( join_predicate_pixel_dupes )
                
                join_predicates.append( 'NOT EXISTS ( {} )'.format( select_statement ) )
                
            
        
        return ( tables, join_predicates )
        
    
    def GetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( self, db_location_context: ClientDBFilesStorage.DBLocationContext, pixel_dupes_preference: int, max_hamming_distance: int, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        ( tables, join_predicates ) = self.GetPotentialDuplicatePairsTableJoinGetInitialTablesAndPreds( pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = master_potential_duplicate_pairs_table_name )
        
        if not db_location_context.location_context.IsAllKnownFiles():
            
            files_table_name = db_location_context.GetSingleFilesTableName()
            
            tables.extend( [
                '{} AS current_files_smaller'.format( files_table_name ),
                '{} AS current_files_larger'.format( files_table_name )
            ] )
            
            join_predicates.append( 'duplicate_files_smaller.king_hash_id = current_files_smaller.hash_id AND duplicate_files_larger.king_hash_id = current_files_larger.hash_id' )
            
        
        table_join = '{} ON ( {} )'.format( ', '.join( tables ), ' AND '.join( join_predicates ) )
        
        return table_join
        
    
    def GetPotentialDuplicatePairsTableJoinOnFileService( self, db_location_context: ClientDBFilesStorage.DBLocationContext ):
        
        if db_location_context.location_context.IsAllKnownFiles():
            
            table_join = 'potential_duplicate_pairs'
            
        else:
            
            files_table_name = db_location_context.GetSingleFilesTableName()
            
            table_join = 'potential_duplicate_pairs, duplicate_files AS duplicate_files_smaller, {} AS current_files_smaller, duplicate_files AS duplicate_files_larger, {} AS current_files_larger ON ( smaller_media_id = duplicate_files_smaller.media_id AND duplicate_files_smaller.king_hash_id = current_files_smaller.hash_id AND larger_media_id = duplicate_files_larger.media_id AND duplicate_files_larger.king_hash_id = current_files_larger.hash_id )'.format( files_table_name, files_table_name )
            
        
        return table_join
        
    
    def GetPotentialDuplicatePairsTableJoinOnSearchResultsBothFiles( self, results_table_name: str, pixel_dupes_preference: int, max_hamming_distance: int, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        ( tables, join_predicates ) = self.GetPotentialDuplicatePairsTableJoinGetInitialTablesAndPreds( pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = master_potential_duplicate_pairs_table_name )
        
        tables.extend( [
            '{} AS results_smaller'.format( results_table_name ),
            '{} AS results_larger'.format( results_table_name )
        ] )
        
        join_predicates.append( 'duplicate_files_smaller.king_hash_id = results_smaller.hash_id AND duplicate_files_larger.king_hash_id = results_larger.hash_id' )
        
        table_join = '{} ON ( {} )'.format( ', '.join( tables ), ' AND '.join( join_predicates ) )
        
        return table_join
        
    
    def GetPotentialDuplicatePairsTableJoinOnSearchResults( self, db_location_context: ClientDBFilesStorage.DBLocationContext, results_table_name: str, pixel_dupes_preference: int, max_hamming_distance: int, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        # why yes this is a seven table join that involves a mix of duplicated tables, temporary tables, and duplicated temporary tables
        #
        # main thing is, give this guy a search from duplicate filter UI, it'll give you a fast table join that returns potential dupes that match that
        #
        # ████████████████████████████████████████████████████████████████████████
        # ████████████████████████████████████████████████████████████████████████
        # ██████████████████████████████████▓█████████████████████████████████████
        # ██████████████████████████████████▒▓████████████████████████████████████
        # █████████████████████████████▓▒▓▓▒░░▒░██████████████████████████████████
        # ███████████████████████████▓▒▒░░░░    ▒▓███████▓▓▓██████████████████████
        # █████████████████████▓▒▓▓▓█       ▒     ▓████▓▓▓▓▓██████████████████████
        # █████████████████▓▓▓▓▓░   ░      ░░     ░▓█▓▓▓██▓▓██████████████████████
        # █████████████████▓▓▓▒░▒▒▒        █▒  ░▓▓▓█████▓▓▓▓██████████████████████
        # █████████████████▓▓▒░░ ░▒      ░▒█▓░▒▓▓▓█████▒▒▒▒▒▓█████████████████████
        # ████████████████████▓▒░   ░   ░▒▒▓▓▓██▓▓█▓░ ░░▓▓▒▓▓▒▓▓██████████████████
        # ██████████████████████▒░░░░  ▒▓▓▓▓▒▓▓▓▓██▓▓░▓█▓▓▓▓▓▓▓▓▓▓████████████████
        # ████████████▓▒█▓███▓▓▒▓░▒░░▒▓▓▓▓▓▒▒░░ ░▒▓▓████▓ ▓▓░░▒▓▓  ░▒▒████████████
        # ████████████▒▒████▓░ ░▒▒▒▓██▓▓▒▒▒▒░░        ▒▓▓▒ ░▒░░▓▒    ▒████████████
        # ████████████▒▓▓▓█▓░▒▒░▒▓███▓▓▒░░░░ ░░   ░░░▒  ▒▓▒▒▒░▒▒      ▓███████████
        # █████████████▒▓▓▓▒▒▓▓▒▓███▓▓▓▒▒░░░░░     ░░▒▓▓  ▒▒░░░       ▓███████████
        # ██████████████▓▓▓▓███▓██▓▓▓▓▓▒▒░░░░ ░       ░▓░ ░░       ░▓█████████████
        # ███████████████▓▓██▒▓█▓▓▓▓▓▓▒▒░░░░ ░░        ▒▓░         ▓██████████████
        # █████████████████▓▒▓█▓▓▓▓▓▓▓▓▒▒▒▒░░▒▒▒      ░▒█▒       ▓████████████████
        # ████████████████▓░▒██▓▓▓▓▓▓▓▓▓▒▒▒░░▒▒▒▓▒▒  ░▒▓▓▒▒░░▒░▓██████████████████
        # ██████████████▓░▓████▓▓▓▓▓▓▓▓▒▒░░░▒░░░▒▒   ▒▓▓▓ ░▒▓▓▓ ▒█████████████████
        # ██████████████▓▓▓██████▓▓▓▓▓▓▒   ░▒▓▒░▓▓   ░ ░▒ ▒░▒▒▒▒▓▒ ▓██████████████
        # ██████████████▓▒░▒▒ ▓█▓▓▓▓▓▓▓▓▓▓▒░▒▒▒░▒▒░░░░    ▓▒░░   ░████▓███████████
        # █████████████████░  ▓█▓██████████▓░░ ░▒▓█████▓   ▒░░ ░▓▓▒▓██░░▓█████████
        # █████████████████▒  ▒█▓▓▓██████████▓▓█▓████████▓ ▒░▒▒░▒ ░███   ▓████████
        # ██████████████████▒ ▒█▓▓▓██████████▒ ███████████  ░▓▒ ▒████▒    ████████
        # █████████████████████▓▓▒▓██▓███████░ ▒▒████████▒░███▒ ░▓▓▓▓▒▒███████████
        # ███████████████████████▒▒███████▓▓▓▓▒  ░▓██████ ▒████▒▓▓▓▓▒▓████████████
        # █████████████████████▓▓▓▓▓▓▓▓▓▓▓▓█████    ▒▒▓▒▒  ▓██▓      ▒████████████
        # ██████████████████████▓▓▓▓▓▓▓█▓▓▓██████ ▒██▓░░░    ▒ ░▓█▓▒▒█████████████
        # ███████████████████████▓▓▓▓▓▓█▓▓▓██▓██▓ ░▓███▓▓▓░   ▓███████████████████
        # ████████████████████████▓███▓▓▓▓▓▓█▓█▓ ░ ░▓█  ▒░░▒  ▓███████████████████
        # █████████████████████████▓▓████▓▓▓▓▓     ▒█░    ▓█▓▓████████████████████
        # ████████████████████████▓█▓██▓▓▓▓▓▒▓     ▓▒   ▒█████████████████████████
        # ████████████████████████▓▓███▓▓▓▒▓▒▓░▒░  ▓░░  ██████████████████████████
        # ████████████████████████▓▓▓▓▓█▓▓▓▒░░░░░  ▒   ▒██████████████████████████
        # █████████████████████████▓▓▓▓▓▓▓█▓▓▓▓▒░  ░░ ▒███████████████████████████
        # ███████████████████████████▓▓▓▓▓▓▓▓▓▓▒     ▓████████████████████████████
        # ████████████████████████████▓▓▓▓▓▒▒  ▒░   ██████████████████████████████
        # ██████████████████████████████▓▓▓▒      ▒███████████████████████████████
        # ███████████████████████████████▓▓▒░    ▓████████████████████████████████
        # ████████████████████████████████████████████████████████████████████████
        # ████████████████████████████████████████████████████████████████████████
        #
        
        ( tables, join_predicates ) = self.GetPotentialDuplicatePairsTableJoinGetInitialTablesAndPreds( pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = master_potential_duplicate_pairs_table_name )
        
        if db_location_context.location_context.IsAllKnownFiles():
            
            tables.append( '{} AS results_table_for_this_query'.format( results_table_name ) )
            
            join_predicates.append( '( duplicate_files_smaller.king_hash_id = results_table_for_this_query.hash_id OR duplicate_files_larger.king_hash_id = results_table_for_this_query.hash_id )' )
            
        else:
            
            files_table_name = db_location_context.GetSingleFilesTableName()
            
            tables.extend( [
                '{} AS results_table_for_this_query'.format( results_table_name ),
                '{} AS current_files_for_this_query'.format( files_table_name )
            ] )
            
            join_predicate_smaller_matches = '( duplicate_files_smaller.king_hash_id = results_table_for_this_query.hash_id AND duplicate_files_larger.king_hash_id = current_files_for_this_query.hash_id )'
            
            join_predicate_larger_matches = '( duplicate_files_smaller.king_hash_id = current_files_for_this_query.hash_id AND duplicate_files_larger.king_hash_id = results_table_for_this_query.hash_id )'
            
            join_predicates.append( '( {} OR {} )'.format( join_predicate_smaller_matches, join_predicate_larger_matches ) )
            
        
        table_join = '{} ON ( {} )'.format( ', '.join( tables ), ' AND '.join( join_predicates ) )
        
        return table_join
        
    
    def GetPotentialDuplicatePairsTableJoinOnSeparateSearchResults( self, results_table_name_1: str, results_table_name_2: str, pixel_dupes_preference: int, max_hamming_distance: int, master_potential_duplicate_pairs_table_name = 'potential_duplicate_pairs' ):
        
        #
        # And taking the above to its logical conclusion with two results sets, one file in xor either
        #
        
        ( tables, join_predicates ) = self.GetPotentialDuplicatePairsTableJoinGetInitialTablesAndPreds( pixel_dupes_preference, max_hamming_distance, master_potential_duplicate_pairs_table_name = master_potential_duplicate_pairs_table_name )
        
        # we don't have to do any db_location_context jibber-jabber here as long as we stipulate that the two results sets have the same location context, which we'll enforce in UI
        # just like above when 'both files match', we know we are db_location_context cross-referenced since we are intersecting with file searches performed on that search domain
        # so, this is actually a bit simpler than the non-both-files-match one search case!!
        
        tables.extend( [
            '{} AS results_table_for_this_query_1'.format( results_table_name_1 ),
            '{} AS results_table_for_this_query_2'.format( results_table_name_2 )
        ] )
        
        one_two = '( duplicate_files_smaller.king_hash_id = results_table_for_this_query_1.hash_id AND duplicate_files_larger.king_hash_id = results_table_for_this_query_2.hash_id )'
        two_one = '( duplicate_files_smaller.king_hash_id = results_table_for_this_query_2.hash_id AND duplicate_files_larger.king_hash_id = results_table_for_this_query_1.hash_id )'
        
        join_predicates.append( '( {} OR {} )'.format( one_two, two_one ) )
        
        table_join = '{} ON ( {} )'.format( ', '.join( tables ), ' AND '.join( join_predicates ) )
        
        return table_join
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'duplicate_files', 'king_hash_id' ) )
            tables_and_columns.append( ( 'duplicate_file_members', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def MediasAreAlternates( self, media_id_a, media_id_b ):
        
        alternates_group_id_a = self.GetAlternatesGroupId( media_id_a, do_not_create = True )
        
        if alternates_group_id_a is None:
            
            return False
            
        
        alternates_group_id_b = self.GetAlternatesGroupId( media_id_b, do_not_create = True )
        
        if alternates_group_id_b is None:
            
            return False
            
        
        return alternates_group_id_a == alternates_group_id_b
        
    
    def MediasAreConfirmedAlternates( self, media_id_a, media_id_b ):
        
        smaller_media_id = min( media_id_a, media_id_b )
        larger_media_id = max( media_id_a, media_id_b )
        
        result = self._Execute( 'SELECT 1 FROM confirmed_alternate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) ).fetchone()
        
        return result is not None
        
    
    def MediasAreFalsePositive( self, media_id_a, media_id_b ):
        
        alternates_group_id_a = self.GetAlternatesGroupId( media_id_a, do_not_create = True )
        
        if alternates_group_id_a is None:
            
            return False
            
        
        alternates_group_id_b = self.GetAlternatesGroupId( media_id_b, do_not_create = True )
        
        if alternates_group_id_b is None:
            
            return False
            
        
        return self.AlternatesGroupsAreFalsePositive( alternates_group_id_a, alternates_group_id_b )
        
    
    def RemoveAlternateMember( self, media_id ):
        
        alternates_group_id = self.GetAlternatesGroupId( media_id, do_not_create = True )
        
        if alternates_group_id is not None:
            
            alternates_media_ids = self.GetAlternateMediaIds( alternates_group_id )
            
            self._Execute( 'DELETE FROM alternate_file_group_members WHERE media_id = ?;', ( media_id, ) )
            
            self._Execute( 'DELETE FROM confirmed_alternate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
            
            if len( alternates_media_ids ) == 1: # i.e. what we just removed was the last of the group
                
                self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id, ) )
                
                self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
                
            
            hash_ids = self.GetDuplicateHashIds( media_id )
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def RemoveAlternateMemberFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.GetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.RemoveAlternateMember( media_id )
                
            
        
    
    def RemoveMediaIdMember( self, hash_id ):
        
        media_id = self.GetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            king_hash_id = self.GetKingHashId( media_id )
            
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
        
        media_id = self.GetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            self.DeletePotentialDuplicatesForMediaId( media_id )
            
        
    
    def RemovePotentialPairsFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            self.RemovePotentialPairs( hash_id )
            
        
    
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
        
        alternates_group_id_a = self.GetAlternatesGroupId( superior_media_id )
        alternates_group_id_b = self.GetAlternatesGroupId( mergee_media_id )
        
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
            
        
        superior_alternates_group_id = self.GetAlternatesGroupId( superior_media_id )
        mergee_alternates_group_id = self.GetAlternatesGroupId( mergee_media_id, do_not_create = True )
        
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
        
        media_id = self.GetMediaId( hash_id )
        
        self.SetKing( hash_id, media_id )
        
    
