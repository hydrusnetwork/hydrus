import collections
import itertools
import random
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBFilesStorage
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBSimilarFiles

class ClientDBFilesDuplicates( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        modules_similar_files: ClientDBSimilarFiles.ClientDBSimilarFiles
        ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client file duplicates', cursor )
        
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        self.modules_similar_files = modules_similar_files
        
        self._service_ids_to_content_types_to_outstanding_local_processing = collections.defaultdict( dict )
        
    
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
        
    
    def DuplicatesAddPotentialDuplicates( self, media_id, potential_duplicate_media_ids_and_distances ):
        
        inserts = []
        
        for ( potential_duplicate_media_id, distance ) in potential_duplicate_media_ids_and_distances:
            
            if potential_duplicate_media_id == media_id: # already duplicates!
                
                continue
                
            
            if self.DuplicatesMediasAreFalsePositive( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            if self.DuplicatesMediasAreConfirmedAlternates( media_id, potential_duplicate_media_id ):
                
                continue
                
            
            # if they are alternates with different alt label and index, do not add
            # however this _could_ be folded into areconfirmedalts on the setalt event--any other alt with diff label/index also gets added
            
            smaller_media_id = min( media_id, potential_duplicate_media_id )
            larger_media_id = max( media_id, potential_duplicate_media_id )
            
            inserts.append( ( smaller_media_id, larger_media_id, distance ) )
            
        
        if len( inserts ) > 0:
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO potential_duplicate_pairs ( smaller_media_id, larger_media_id, distance ) VALUES ( ?, ?, ? );', inserts )
            
        
    
    def DuplicatesAlternatesGroupsAreFalsePositive( self, alternates_group_id_a, alternates_group_id_b ):
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return False
            
        
        smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
        larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
        
        result = self._Execute( 'SELECT 1 FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', ( smaller_alternates_group_id, larger_alternates_group_id ) ).fetchone()
        
        false_positive_pair_found = result is not None
        
        return false_positive_pair_found
        
    
    def DuplicatesClearAllFalsePositiveRelations( self, alternates_group_id ):
        
        self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
        
        media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
        
        hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids )
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
    
    def DuplicatesClearAllFalsePositiveRelationsFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    self.DuplicatesClearAllFalsePositiveRelations( alternates_group_id )
                    
                
            
        
    
    def DuplicatesClearFalsePositiveRelationsBetweenGroups( self, alternates_group_ids ):
        
        pairs = list( itertools.combinations( alternates_group_ids, 2 ) )
        
        for ( alternates_group_id_a, alternates_group_id_b ) in pairs:
            
            smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
            larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
            
            self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', ( smaller_alternates_group_id, larger_alternates_group_id ) )
            
        
        for alternates_group_id in alternates_group_ids:
            
            media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
            
            hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids )
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def DuplicatesClearFalsePositiveRelationsBetweenGroupsFromHashes( self, hashes ):
        
        alternates_group_ids = set()
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
            
            if alternates_group_id is not None:
                
                alternates_group_ids.add( alternates_group_id )
                
            
        
        if len( alternates_group_ids ) > 1:
            
            self.DuplicatesClearFalsePositiveRelationsBetweenGroups( alternates_group_ids )
            
        
    
    def DuplicatesClearPotentialsBetweenMedias( self, media_ids_a, media_ids_b ):
        
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
            
            self._ExecuteMany( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', deletees )
            
        
    
    def DuplicatesClearPotentialsBetweenAlternatesGroups( self, alternates_group_id_a, alternates_group_id_b ):
        
        # these groups are being set as false positive. therefore, any potential between them no longer applies
        
        media_ids_a = self.DuplicatesGetAlternateMediaIds( alternates_group_id_a )
        media_ids_b = self.DuplicatesGetAlternateMediaIds( alternates_group_id_b )
        
        self.DuplicatesClearPotentialsBetweenMedias( media_ids_a, media_ids_b )
        
    
    def DuplicatesDeleteAllPotentialDuplicatePairs( self ):
        
        media_ids = set()
        
        for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT smaller_media_id, larger_media_id FROM potential_duplicate_pairs;' ):
            
            media_ids.add( smaller_media_id )
            media_ids.add( larger_media_id )
            
        
        hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids )
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs;' )
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
    
    def DuplicatesDissolveAlternatesGroupId( self, alternates_group_id ):
        
        media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
        
        for media_id in media_ids:
            
            self.DuplicatesDissolveMediaId( media_id )
            
        
    
    def DuplicatesDissolveAlternatesGroupIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    self.DuplicatesDissolveAlternatesGroupId( alternates_group_id )
                    
                
            
        
    
    def DuplicatesDissolveMediaId( self, media_id ):
        
        self.DuplicatesRemoveAlternateMember( media_id )
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
        
        hash_ids = self.DuplicatesGetDuplicateHashIds( media_id )
        
        self._Execute( 'DELETE FROM duplicate_file_members WHERE media_id = ?;', ( media_id, ) )
        self._Execute( 'DELETE FROM duplicate_files WHERE media_id = ?;', ( media_id, ) )
        
        self.modules_similar_files.ResetSearch( hash_ids )
        
    
    def DuplicatesDissolveMediaIdFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.DuplicatesDissolveMediaId( media_id )
                
            
        
    
    def DuplicatesFilterKingHashIds( self, allowed_hash_ids ):
        
        # can't just pull explicit king_hash_ids, since files that do not have a media_id are still kings
        # kings = hashes - explicitly not kings
        
        if not isinstance( allowed_hash_ids, set ):
            
            allowed_hash_ids = set( allowed_hash_ids )
            
        
        with self._MakeTemporaryIntegerTable( allowed_hash_ids, 'hash_id' ) as temp_hash_ids_table_name:
            
            explicit_king_hash_ids = self._STS( self._Execute( 'SELECT king_hash_id FROM {} CROSS JOIN duplicate_files ON ( {}.hash_id = duplicate_files.king_hash_id );'.format( temp_hash_ids_table_name, temp_hash_ids_table_name ) ) )
            
            all_duplicate_member_hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} CROSS JOIN duplicate_file_members USING ( hash_id );'.format( temp_hash_ids_table_name ) ) )
            
        
        all_non_king_hash_ids = all_duplicate_member_hash_ids.difference( explicit_king_hash_ids )
        
        return allowed_hash_ids.difference( all_non_king_hash_ids )
        
    
    def DuplicatesGetAlternatesGroupId( self, media_id, do_not_create = False ):
        
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
        
    
    def DuplicatesGetAlternateMediaIds( self, alternates_group_id ):
        
        media_ids = self._STS( self._Execute( 'SELECT media_id FROM alternate_file_group_members WHERE alternates_group_id = ?;', ( alternates_group_id, ) ) )
        
        return media_ids
        
    
    def DuplicatesGetBestKingId( self, media_id, db_location_context: ClientDBFilesStorage.DBLocationContext, allowed_hash_ids = None, preferred_hash_ids = None ):
        
        media_hash_ids = self.DuplicatesGetDuplicateHashIds( media_id, db_location_context = db_location_context )
        
        if allowed_hash_ids is not None:
            
            media_hash_ids.intersection_update( allowed_hash_ids )
            
        
        if len( media_hash_ids ) > 0:
            
            king_hash_id = self.DuplicatesGetKingHashId( media_id )
            
            if preferred_hash_ids is not None:
                
                preferred_hash_ids = media_hash_ids.intersection( preferred_hash_ids )
                
                if len( preferred_hash_ids ) > 0:
                    
                    if king_hash_id not in preferred_hash_ids:
                        
                        king_hash_id = random.sample( preferred_hash_ids, 1 )[0]
                        
                    
                    return king_hash_id
                    
                
            
            if king_hash_id not in media_hash_ids:
                
                king_hash_id = random.sample( media_hash_ids, 1 )[0]
                
            
            return king_hash_id
            
        
        return None
        
    
    def DuplicatesGetDuplicateHashIds( self, media_id, db_location_context: ClientDBFilesStorage.DBLocationContext = None ):
        
        table_join = 'duplicate_file_members'
        
        if db_location_context is not None:
            
            table_join = db_location_context.GetTableJoinLimitedByFileDomain( table_join )
            
        
        hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {} WHERE media_id = ?;'.format( table_join ), ( media_id, ) ) )
        
        return hash_ids
        
    
    def DuplicatesGetDuplicatesHashIds( self, media_ids, db_location_context: ClientDBFilesStorage.DBLocationContext = None ):
        
        with self._MakeTemporaryIntegerTable( media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            table_join = '{} CROSS JOIN {} USING ( media_id )'.format( temp_media_ids_table_name, 'duplicate_file_members' )
            
            if db_location_context is not None:
            
                table_join = db_location_context.GetTableJoinLimitedByFileDomain( table_join )
                
            
            hash_ids = self._STS( self._Execute( 'SELECT hash_id FROM {};'.format( table_join ) ) )
            
        
        return hash_ids
        
    
    def DuplicatesGetFalsePositiveAlternatesGroupIds( self, alternates_group_id ):
        
        false_positive_alternates_group_ids = set()
        
        results = self._Execute( 'SELECT smaller_alternates_group_id, larger_alternates_group_id FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) ).fetchall()
        
        for ( smaller_alternates_group_id, larger_alternates_group_id ) in results:
            
            false_positive_alternates_group_ids.add( smaller_alternates_group_id )
            false_positive_alternates_group_ids.add( larger_alternates_group_id )
            
        
        return false_positive_alternates_group_ids
        
    
    def DuplicatesGetFileDuplicateInfo( self, location_context, hash ):
        
        result_dict = {}
        
        result_dict[ 'is_king' ] = True
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        counter = collections.Counter()
        
        media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
            
            table_join = self.DuplicatesGetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
            
            ( num_potentials, ) = self._Execute( 'SELECT COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} WHERE smaller_media_id = ? OR larger_media_id = ? );'.format( table_join ), ( media_id, media_id, ) ).fetchone()
            
            if num_potentials > 0:
                
                counter[ HC.DUPLICATE_POTENTIAL ] = num_potentials
                
            
            king_hash_id = self.DuplicatesGetKingHashId( media_id )
            
            result_dict[ 'is_king' ] = king_hash_id == hash_id
            
            media_hash_ids = self.DuplicatesGetDuplicateHashIds( media_id, db_location_context = db_location_context )
            
            num_other_dupe_members = len( media_hash_ids ) - 1
            
            if num_other_dupe_members > 0:
                
                counter[ HC.DUPLICATE_MEMBER ] = num_other_dupe_members
                
            
            alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
            
            if alternates_group_id is not None:
                
                alt_media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
                
                alt_media_ids.discard( media_id )
                
                for alt_media_id in alt_media_ids:
                    
                    alt_hash_ids = self.DuplicatesGetDuplicateHashIds( alt_media_id, db_location_context = db_location_context )
                    
                    if len( alt_hash_ids ) > 0:
                        
                        counter[ HC.DUPLICATE_ALTERNATE ] += 1
                        
                        smaller_media_id = min( media_id, alt_media_id )
                        larger_media_id = max( media_id, alt_media_id )
                        
                        result = self._Execute( 'SELECT 1 FROM confirmed_alternate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) ).fetchone()
                        
                        if result is not None:
                            
                            counter[ HC.DUPLICATE_CONFIRMED_ALTERNATE ] += 1
                            
                        
                    
                
                false_positive_alternates_group_ids = self.DuplicatesGetFalsePositiveAlternatesGroupIds( alternates_group_id )
                
                false_positive_alternates_group_ids.discard( alternates_group_id )
                
                for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                    
                    fp_media_ids = self.DuplicatesGetAlternateMediaIds( false_positive_alternates_group_id )
                    
                    for fp_media_id in fp_media_ids:
                        
                        fp_hash_ids = self.DuplicatesGetDuplicateHashIds( fp_media_id, db_location_context = db_location_context )
                        
                        if len( fp_hash_ids ) > 0:
                            
                            counter[ HC.DUPLICATE_FALSE_POSITIVE ] += 1
                            
                        
                    
                
            
        
        result_dict[ 'counts' ] = counter
        
        return result_dict
        
    
    def DuplicatesGetFileHashesByDuplicateType( self, location_context: ClientLocation.LocationContext, hash, duplicate_type, allowed_hash_ids = None, preferred_hash_ids = None ):
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        db_location_context = self.modules_files_storage.GetDBLocationContext( location_context )
        
        dupe_hash_ids = set()
        
        if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    false_positive_alternates_group_ids = self.DuplicatesGetFalsePositiveAlternatesGroupIds( alternates_group_id )
                    
                    false_positive_alternates_group_ids.discard( alternates_group_id )
                    
                    false_positive_media_ids = set()
                    
                    for false_positive_alternates_group_id in false_positive_alternates_group_ids:
                        
                        false_positive_media_ids.update( self.DuplicatesGetAlternateMediaIds( false_positive_alternates_group_id ) )
                        
                    
                    for false_positive_media_id in false_positive_media_ids:
                        
                        best_king_hash_id = self.DuplicatesGetBestKingId( false_positive_media_id, db_location_context, allowed_hash_ids = allowed_hash_ids, preferred_hash_ids = preferred_hash_ids )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_ALTERNATE:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
                
                if alternates_group_id is not None:
                    
                    alternates_media_ids = self._STS( self._Execute( 'SELECT media_id FROM alternate_file_group_members WHERE alternates_group_id = ?;', ( alternates_group_id, ) ) )
                    
                    alternates_media_ids.discard( media_id )
                    
                    for alternates_media_id in alternates_media_ids:
                        
                        best_king_hash_id = self.DuplicatesGetBestKingId( alternates_media_id, db_location_context, allowed_hash_ids = allowed_hash_ids, preferred_hash_ids = preferred_hash_ids )
                        
                        if best_king_hash_id is not None:
                            
                            dupe_hash_ids.add( best_king_hash_id )
                            
                        
                    
                
            
        elif duplicate_type == HC.DUPLICATE_MEMBER:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                media_hash_ids = self.DuplicatesGetDuplicateHashIds( media_id, db_location_context = db_location_context )
                
                if allowed_hash_ids is not None:
                    
                    media_hash_ids.intersection_update( allowed_hash_ids )
                    
                
                dupe_hash_ids.update( media_hash_ids )
                
            
        elif duplicate_type == HC.DUPLICATE_KING:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                best_king_hash_id = self.DuplicatesGetBestKingId( media_id, db_location_context, allowed_hash_ids = allowed_hash_ids, preferred_hash_ids = preferred_hash_ids )
                
                if best_king_hash_id is not None:
                    
                    dupe_hash_ids.add( best_king_hash_id )
                    
                
            
        elif duplicate_type == HC.DUPLICATE_POTENTIAL:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                table_join = self.DuplicatesGetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
                
                for ( smaller_media_id, larger_media_id ) in self._Execute( 'SELECT smaller_media_id, larger_media_id FROM {} WHERE smaller_media_id = ? OR larger_media_id = ?;'.format( table_join ), ( media_id, media_id ) ).fetchall():
                    
                    if smaller_media_id != media_id:
                        
                        potential_media_id = smaller_media_id
                        
                    else:
                        
                        potential_media_id = larger_media_id
                        
                    
                    best_king_hash_id = self.DuplicatesGetBestKingId( potential_media_id, db_location_context, allowed_hash_ids = allowed_hash_ids, preferred_hash_ids = preferred_hash_ids )
                    
                    if best_king_hash_id is not None:
                        
                        dupe_hash_ids.add( best_king_hash_id )
                        
                    
                
            
        
        dupe_hash_ids.discard( hash_id )
        
        dupe_hash_ids = list( dupe_hash_ids )
        
        dupe_hash_ids.insert( 0, hash_id )
        
        dupe_hashes = self.modules_hashes_local_cache.GetHashes( dupe_hash_ids )
        
        return dupe_hashes
        
    
    def DuplicatesGetHashIdsFromDuplicateCountPredicate( self, db_location_context: ClientDBFilesStorage.DBLocationContext, operator, num_relationships, dupe_type ):
        
        # doesn't work for '= 0' or '< 1'
        
        if operator == CC.UNICODE_ALMOST_EQUAL_TO:
            
            lower_bound = 0.8 * num_relationships
            upper_bound = 1.2 * num_relationships
            
            def filter_func( count ):
                
                return lower_bound < count and count < upper_bound
                
            
        elif operator == '<':
            
            def filter_func( count ):
                
                return count < num_relationships
                
            
        elif operator == '>':
            
            def filter_func( count ):
                
                return count > num_relationships
                
            
        elif operator == '=':
            
            def filter_func( count ):
                
                return count == num_relationships
                
            
        
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
                        
                        fp_media_ids = self.DuplicatesGetAlternateMediaIds( false_positive_alternates_group_id )
                        
                        for fp_media_id in fp_media_ids:
                            
                            fp_hash_ids = self.DuplicatesGetDuplicateHashIds( fp_media_id, db_location_context = db_location_context )
                            
                            if len( fp_hash_ids ) > 0:
                                
                                valid = True
                                
                                break
                                
                            
                        
                        alternates_group_ids_to_valid_for_file_domain[ false_positive_alternates_group_id ] = valid
                        
                    
                    if alternates_group_ids_to_valid_for_file_domain[ false_positive_alternates_group_id ]:
                        
                        count += 1
                        
                    
                
                if filter_func( count ):
                    
                    media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
                    
                    hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids, db_location_context = db_location_context )
                    
                
            
        elif dupe_type == HC.DUPLICATE_ALTERNATE:
            
            query = 'SELECT alternates_group_id, COUNT( * ) FROM alternate_file_group_members GROUP BY alternates_group_id;'
            
            results = self._Execute( query ).fetchall()
            
            for ( alternates_group_id, count ) in results:
                
                count -= 1 # num relationships is number group members - 1
                
                media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
                
                alternates_group_id_hash_ids = []
                
                for media_id in media_ids:
                    
                    media_id_hash_ids = self.DuplicatesGetDuplicateHashIds( media_id, db_location_context = db_location_context )
                    
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
                    
                
            
            hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids, db_location_context = db_location_context )
            
        elif dupe_type == HC.DUPLICATE_POTENTIAL:
            
            table_join = self.DuplicatesGetPotentialDuplicatePairsTableJoinOnFileService( db_location_context )
            
            smaller_query = 'SELECT smaller_media_id, COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} ) GROUP BY smaller_media_id;'.format( table_join )
            larger_query = 'SELECT larger_media_id, COUNT( * ) FROM ( SELECT DISTINCT smaller_media_id, larger_media_id FROM {} ) GROUP BY larger_media_id;'.format( table_join )
            
            media_ids_to_counts = collections.Counter()
            
            for ( media_id, count ) in self._Execute( smaller_query ):
                
                media_ids_to_counts[ media_id ] += count
                
            
            for ( media_id, count ) in self._Execute( larger_query ):
                
                media_ids_to_counts[ media_id ] += count
                
            
            media_ids = [ media_id for ( media_id, count ) in media_ids_to_counts.items() if filter_func( count ) ]
            
            hash_ids = self.DuplicatesGetDuplicatesHashIds( media_ids, db_location_context = db_location_context )
            
        
        return hash_ids
        
    
    def DuplicatesGetKingHashId( self, media_id ):
        
        ( king_hash_id, ) = self._Execute( 'SELECT king_hash_id FROM duplicate_files WHERE media_id = ?;', ( media_id, ) ).fetchone()
        
        return king_hash_id
        
    
    def DuplicatesGetMediaId( self, hash_id, do_not_create = False ):
        
        result = self._Execute( 'SELECT media_id FROM duplicate_file_members WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            if do_not_create:
                
                return None
                
            
            self._Execute( 'INSERT INTO duplicate_files ( king_hash_id ) VALUES ( ? );', ( hash_id, ) )
            
            media_id = self._GetLastRowId()
            
            self._Execute( 'INSERT INTO duplicate_file_members ( media_id, hash_id ) VALUES ( ?, ? );', ( media_id, hash_id ) )
            
        else:
            
            ( media_id, ) = result
            
        
        return media_id
        
    
    def DuplicatesGetPotentialDuplicatePairsTableJoinOnEverythingSearchResults( self, db_location_context: ClientDBFilesStorage.DBLocationContext, pixel_dupes_preference: int, max_hamming_distance: int ):
        
        tables = 'potential_duplicate_pairs, duplicate_file_members AS duplicate_file_members_smaller, duplicate_file_members AS duplicate_file_members_larger'
        join_predicate = 'smaller_media_id = duplicate_file_members_smaller.media_id AND larger_media_id = duplicate_file_members_larger.media_id AND distance <= {}'.format( max_hamming_distance )
        
        if not db_location_context.location_context.IsAllKnownFiles():
            
            files_table_name = db_location_context.files_table_name
            
            tables = '{}, {} AS current_files_smaller, {} AS current_files_larger'.format( tables, files_table_name, files_table_name )
            
            join_predicate = '{} AND duplicate_file_members_smaller.hash_id = current_files_smaller.hash_id AND duplicate_file_members_larger.hash_id = current_files_larger.hash_id'.format( join_predicate )
            
        
        if pixel_dupes_preference in ( CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, CC.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            join_predicate_pixel_dupes = 'duplicate_file_members_smaller.hash_id = pixel_hash_map_smaller.hash_id AND duplicate_file_members_larger.hash_id = pixel_hash_map_larger.hash_id AND pixel_hash_map_smaller.pixel_hash_id = pixel_hash_map_larger.pixel_hash_id'
            
            if pixel_dupes_preference == CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
                
                tables = '{}, pixel_hash_map AS pixel_hash_map_smaller, pixel_hash_map AS pixel_hash_map_larger'.format( tables )
                
                join_predicate = '{} AND {}'.format( join_predicate, join_predicate_pixel_dupes )
                
            elif pixel_dupes_preference == CC.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED:
                
                # can't do "AND NOT {}", or the join will just give you the million rows where it isn't true. we want 'AND NEVER {}', and quick
                
                select_statement = 'SELECT 1 FROM pixel_hash_map AS pixel_hash_map_smaller, pixel_hash_map as pixel_hash_map_larger ON ( {} )'.format( join_predicate_pixel_dupes )
                
                join_predicate = '{} AND NOT EXISTS ( {} )'.format( join_predicate, select_statement )
                
            
        
        table_join = '{} ON ( {} )'.format( tables, join_predicate )
        
        return table_join
        
    
    def DuplicatesGetPotentialDuplicatePairsTableJoinOnFileService( self, db_location_context: ClientDBFilesStorage.DBLocationContext ):
        
        if db_location_context.location_context.IsAllKnownFiles():
            
            table_join = 'potential_duplicate_pairs'
            
        else:
            
            files_table_name = db_location_context.files_table_name
            
            table_join = 'potential_duplicate_pairs, duplicate_file_members AS duplicate_file_members_smaller, {} AS current_files_smaller, duplicate_file_members AS duplicate_file_members_larger, {} AS current_files_larger ON ( smaller_media_id = duplicate_file_members_smaller.media_id AND duplicate_file_members_smaller.hash_id = current_files_smaller.hash_id AND larger_media_id = duplicate_file_members_larger.media_id AND duplicate_file_members_larger.hash_id = current_files_larger.hash_id )'.format( files_table_name, files_table_name )
            
        
        return table_join
        
    
    def DuplicatesGetPotentialDuplicatePairsTableJoinOnSearchResults( self, db_location_context: ClientDBFilesStorage.DBLocationContext, results_table_name: str, both_files_match: bool, pixel_dupes_preference: int, max_hamming_distance: int ):
        
        # why yes this is a seven table join that involves a mix of duplicated tables, temporary tables, and duplicated temporary tables
        #
        # main thing is, give this guy a search in duplicate filter UI, it'll give you a fast table join that returns potential dupes that match that
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
        
        base_tables = 'potential_duplicate_pairs, duplicate_file_members AS duplicate_file_members_smaller, duplicate_file_members AS duplicate_file_members_larger'
        
        join_predicate_media_to_hashes = 'smaller_media_id = duplicate_file_members_smaller.media_id AND larger_media_id = duplicate_file_members_larger.media_id AND distance <= {}'.format( max_hamming_distance )
        
        if both_files_match:
            
            tables = '{}, {} AS results_smaller, {} AS results_larger'.format( base_tables, results_table_name, results_table_name )
            
            join_predicate_hashes_to_allowed_results = 'duplicate_file_members_smaller.hash_id = results_smaller.hash_id AND duplicate_file_members_larger.hash_id = results_larger.hash_id'
            
        else:
            
            if db_location_context.location_context.IsAllKnownFiles():
                
                tables = '{}, {} AS results_table_for_this_query'.format( base_tables, results_table_name )
                
                join_predicate_hashes_to_allowed_results = '( duplicate_file_members_smaller.hash_id = results_table_for_this_query.hash_id OR duplicate_file_members_larger.hash_id = results_table_for_this_query.hash_id )'
                
            else:
                
                files_table_name = db_location_context.files_table_name
                
                tables = '{}, {} AS results_table_for_this_query, {} AS current_files_for_this_query'.format( base_tables, results_table_name, files_table_name )
                
                join_predicate_smaller_matches = '( duplicate_file_members_smaller.hash_id = results_table_for_this_query.hash_id AND duplicate_file_members_larger.hash_id = current_files_for_this_query.hash_id )'
                
                join_predicate_larger_matches = '( duplicate_file_members_smaller.hash_id = current_files_for_this_query.hash_id AND duplicate_file_members_larger.hash_id = results_table_for_this_query.hash_id )'
                
                join_predicate_hashes_to_allowed_results = '( {} OR {} )'.format( join_predicate_smaller_matches, join_predicate_larger_matches )
                
            
        
        if pixel_dupes_preference in ( CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, CC.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            join_predicate_pixel_dupes = 'duplicate_file_members_smaller.hash_id = pixel_hash_map_smaller.hash_id AND duplicate_file_members_larger.hash_id = pixel_hash_map_larger.hash_id AND pixel_hash_map_smaller.pixel_hash_id = pixel_hash_map_larger.pixel_hash_id'
            
            if pixel_dupes_preference == CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED:
                
                tables = '{}, pixel_hash_map AS pixel_hash_map_smaller, pixel_hash_map AS pixel_hash_map_larger'.format( tables )
                
                join_predicate_hashes_to_allowed_results = '{} AND {}'.format( join_predicate_hashes_to_allowed_results, join_predicate_pixel_dupes )
                
            elif pixel_dupes_preference == CC.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED:
                
                # can't do "AND NOT {}", or the join will just give you the million rows where it isn't true. we want 'AND NEVER {}', and quick
                
                select_statement = 'SELECT 1 FROM pixel_hash_map AS pixel_hash_map_smaller, pixel_hash_map as pixel_hash_map_larger ON ( {} )'.format( join_predicate_pixel_dupes )
                
                join_predicate_hashes_to_allowed_results = '{} AND NOT EXISTS ( {} )'.format( join_predicate_hashes_to_allowed_results, select_statement )
                
            
        
        join_predicate = '{} AND {}'.format( join_predicate_media_to_hashes, join_predicate_hashes_to_allowed_results )
        
        table_join = '{} ON ( {} )'.format( tables, join_predicate )
        
        return table_join
        
    
    def DuplicatesMediasAreAlternates( self, media_id_a, media_id_b ):
        
        alternates_group_id_a = self.DuplicatesGetAlternatesGroupId( media_id_a, do_not_create = True )
        
        if alternates_group_id_a is None:
            
            return False
            
        
        alternates_group_id_b = self.DuplicatesGetAlternatesGroupId( media_id_b, do_not_create = True )
        
        if alternates_group_id_b is None:
            
            return False
            
        
        return alternates_group_id_a == alternates_group_id_b
        
    
    def DuplicatesMediasAreConfirmedAlternates( self, media_id_a, media_id_b ):
        
        smaller_media_id = min( media_id_a, media_id_b )
        larger_media_id = max( media_id_a, media_id_b )
        
        result = self._Execute( 'SELECT 1 FROM confirmed_alternate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) ).fetchone()
        
        return result is not None
        
    
    def DuplicatesMediasAreFalsePositive( self, media_id_a, media_id_b ):
        
        alternates_group_id_a = self.DuplicatesGetAlternatesGroupId( media_id_a, do_not_create = True )
        
        if alternates_group_id_a is None:
            
            return False
            
        
        alternates_group_id_b = self.DuplicatesGetAlternatesGroupId( media_id_b, do_not_create = True )
        
        if alternates_group_id_b is None:
            
            return False
            
        
        return self.DuplicatesAlternatesGroupsAreFalsePositive( alternates_group_id_a, alternates_group_id_b )
        
    
    def DuplicatesMergeMedias( self, superior_media_id, mergee_media_id ):
        
        if superior_media_id == mergee_media_id:
            
            return
            
        
        self.DuplicatesClearPotentialsBetweenMedias( ( superior_media_id, ), ( mergee_media_id, ) )
        
        alternates_group_id = self.DuplicatesGetAlternatesGroupId( superior_media_id )
        mergee_alternates_group_id = self.DuplicatesGetAlternatesGroupId( mergee_media_id )
        
        if alternates_group_id != mergee_alternates_group_id:
            
            if self.DuplicatesAlternatesGroupsAreFalsePositive( alternates_group_id, mergee_alternates_group_id ):
                
                smaller_alternates_group_id = min( alternates_group_id, mergee_alternates_group_id )
                larger_alternates_group_id = max( alternates_group_id, mergee_alternates_group_id )
                
                self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', ( smaller_alternates_group_id, larger_alternates_group_id ) )
                
            
            self.DuplicatesSetAlternates( superior_media_id, mergee_media_id )
            
        
        self._Execute( 'UPDATE duplicate_file_members SET media_id = ? WHERE media_id = ?;', ( superior_media_id, mergee_media_id ) )
        
        smaller_media_id = min( superior_media_id, mergee_media_id )
        larger_media_id = max( superior_media_id, mergee_media_id )
        
        # ensure the potential merge pair is gone
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) )
        
        # now merge potentials from the old to the new--however this has complicated tests to stop confirmed alts and so on, so can't just update ids
        
        existing_potential_info_of_mergee_media_id = self._Execute( 'SELECT smaller_media_id, larger_media_id, distance FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( mergee_media_id, mergee_media_id ) ).fetchall()
        
        self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( mergee_media_id, mergee_media_id ) )
        
        for ( smaller_media_id, larger_media_id, distance ) in existing_potential_info_of_mergee_media_id:
            
            if smaller_media_id == mergee_media_id:
                
                media_id_a = superior_media_id
                media_id_b = larger_media_id
                
            else:
                
                media_id_a = smaller_media_id
                media_id_b = superior_media_id
                
            
            potential_duplicate_media_ids_and_distances = [ ( media_id_b, distance ) ]
            
            self.DuplicatesAddPotentialDuplicates( media_id_a, potential_duplicate_media_ids_and_distances )
            
        
        # ensure any previous confirmed alt pair is gone
        
        self._Execute( 'DELETE FROM confirmed_alternate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', ( smaller_media_id, larger_media_id ) )
        
        # now merge confirmed alts from the old to the new
        
        self._Execute( 'UPDATE OR IGNORE confirmed_alternate_pairs SET smaller_media_id = ? WHERE smaller_media_id = ?;', ( superior_media_id, mergee_media_id ) )
        self._Execute( 'UPDATE OR IGNORE confirmed_alternate_pairs SET larger_media_id = ? WHERE larger_media_id = ?;', ( superior_media_id, mergee_media_id ) )
        
        # and clear out potentials that are now invalid
        
        confirmed_alternate_pairs = self._Execute( 'SELECT smaller_media_id, larger_media_id FROM confirmed_alternate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( superior_media_id, superior_media_id ) ).fetchall()
        
        self._ExecuteMany( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? AND larger_media_id = ?;', confirmed_alternate_pairs )
        
        # clear out empty records
        
        self._Execute( 'DELETE FROM alternate_file_group_members WHERE media_id = ?;', ( mergee_media_id, ) )
        
        self._Execute( 'DELETE FROM duplicate_files WHERE media_id = ?;', ( mergee_media_id, ) )
        
    
    def DuplicatesRemoveAlternateMember( self, media_id ):
        
        alternates_group_id = self.DuplicatesGetAlternatesGroupId( media_id, do_not_create = True )
        
        if alternates_group_id is not None:
            
            alternates_media_ids = self.DuplicatesGetAlternateMediaIds( alternates_group_id )
            
            self._Execute( 'DELETE FROM alternate_file_group_members WHERE media_id = ?;', ( media_id, ) )
            
            self._Execute( 'DELETE FROM confirmed_alternate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
            
            if len( alternates_media_ids ) == 1: # i.e. what we just removed was the last of the group
                
                self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id, ) )
                
                self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id, alternates_group_id ) )
                
            
            hash_ids = self.DuplicatesGetDuplicateHashIds( media_id )
            
            self.modules_similar_files.ResetSearch( hash_ids )
            
        
    
    def DuplicatesRemoveAlternateMemberFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
            
            if media_id is not None:
                
                self.DuplicatesRemoveAlternateMember( media_id )
                
            
        
    
    def DuplicatesRemoveMediaIdMember( self, hash_id ):
        
        media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            king_hash_id = self.DuplicatesGetKingHashId( media_id )
            
            if hash_id == king_hash_id:
                
                self.DuplicatesDissolveMediaId( media_id )
                
            else:
                
                self._Execute( 'DELETE FROM duplicate_file_members WHERE hash_id = ?;', ( hash_id, ) )
                
                self.modules_similar_files.ResetSearch( ( hash_id, ) )
                
            
        
    
    def DuplicatesRemoveMediaIdMemberFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            self.DuplicatesRemoveMediaIdMember( hash_id )
            
        
    
    def DuplicatesRemovePotentialPairs( self, hash_id ):
        
        media_id = self.DuplicatesGetMediaId( hash_id, do_not_create = True )
        
        if media_id is not None:
            
            self._Execute( 'DELETE FROM potential_duplicate_pairs WHERE smaller_media_id = ? OR larger_media_id = ?;', ( media_id, media_id ) )
            
        
    
    def DuplicatesRemovePotentialPairsFromHashes( self, hashes ):
        
        hash_ids = self.modules_hashes_local_cache.GetHashIds( hashes )
        
        for hash_id in hash_ids:
            
            self.DuplicatesRemovePotentialPairs( hash_id )
            
        
    
    def DuplicatesSetAlternates( self, media_id_a, media_id_b ):
        
        # let's clear out any outstanding potentials. whether this is a valid or not connection, we don't want to see it again
        
        self.DuplicatesClearPotentialsBetweenMedias( ( media_id_a, ), ( media_id_b, ) )
        
        # now check if we should be making a new relationship
        
        alternates_group_id_a = self.DuplicatesGetAlternatesGroupId( media_id_a )
        alternates_group_id_b = self.DuplicatesGetAlternatesGroupId( media_id_b )
        
        if self.DuplicatesAlternatesGroupsAreFalsePositive( alternates_group_id_a, alternates_group_id_b ):
            
            return
            
        
        # write a confirmed result so this can't come up again due to subsequent re-searching etc...
        # in future, I can tune this to consider alternate labels and indices. alternates with different labels and indices are not appropriate for potentials, so we can add more rows here
        
        smaller_media_id = min( media_id_a, media_id_b )
        larger_media_id = max( media_id_a, media_id_b )
        
        self._Execute( 'INSERT OR IGNORE INTO confirmed_alternate_pairs ( smaller_media_id, larger_media_id ) VALUES ( ?, ? );', ( smaller_media_id, larger_media_id ) )
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return
            
        
        # ok, they are currently not alternates, so we need to merge B into A
        
        # first, for all false positive relationships that A already has, clear out potentials between B and those fps before it moves over
        
        false_positive_pairs = self._Execute( 'SELECT smaller_alternates_group_id, larger_alternates_group_id FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id_a, alternates_group_id_a ) )
        
        for ( smaller_false_positive_alternates_group_id, larger_false_positive_alternates_group_id ) in false_positive_pairs:
            
            if smaller_false_positive_alternates_group_id == alternates_group_id_a:
                
                self.DuplicatesClearPotentialsBetweenAlternatesGroups( alternates_group_id_b, larger_false_positive_alternates_group_id )
                
            else:
                
                self.DuplicatesClearPotentialsBetweenAlternatesGroups( smaller_false_positive_alternates_group_id, alternates_group_id_b )
                
            
        
        # first, update all B to A
        
        self._Execute( 'UPDATE alternate_file_group_members SET alternates_group_id = ? WHERE alternates_group_id = ?;', ( alternates_group_id_a, alternates_group_id_b ) )
        
        # move false positive records for B to A
        
        false_positive_pairs = self._Execute( 'SELECT smaller_alternates_group_id, larger_alternates_group_id FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id_b, alternates_group_id_b ) )
        
        self._Execute( 'DELETE FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? OR larger_alternates_group_id = ?;', ( alternates_group_id_b, alternates_group_id_b ) )
        
        for ( smaller_false_positive_alternates_group_id, larger_false_positive_alternates_group_id ) in false_positive_pairs:
            
            if smaller_false_positive_alternates_group_id == alternates_group_id_b:
                
                self.DuplicatesSetFalsePositive( alternates_group_id_a, larger_false_positive_alternates_group_id )
                
            else:
                
                self.DuplicatesSetFalsePositive( smaller_false_positive_alternates_group_id, alternates_group_id_a )
                
            
        
        # remove master record
        
        self._Execute( 'DELETE FROM alternate_file_groups WHERE alternates_group_id = ?;', ( alternates_group_id_b, ) )
        
        # pubsub to refresh alternates info for alternates_group_id_a and _b goes here
        
    
    def DuplicatesSetFalsePositive( self, alternates_group_id_a, alternates_group_id_b ):
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return
            
        
        self.DuplicatesClearPotentialsBetweenAlternatesGroups( alternates_group_id_a, alternates_group_id_b )
        
        smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
        larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
        
        self._Execute( 'INSERT OR IGNORE INTO duplicate_false_positives ( smaller_alternates_group_id, larger_alternates_group_id ) VALUES ( ?, ? );', ( smaller_alternates_group_id, larger_alternates_group_id ) )
        
    
    def DuplicatesSetKing( self, king_hash_id, media_id ):
        
        self._Execute( 'UPDATE duplicate_files SET king_hash_id = ? WHERE media_id = ?;', ( king_hash_id, media_id ) )
        
    
    def DuplicatesSetKingFromHash( self, hash ):
        
        hash_id = self.modules_hashes_local_cache.GetHashId( hash )
        
        media_id = self.DuplicatesGetMediaId( hash_id )
        
        self.DuplicatesSetKing( hash_id, media_id )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'file_maintenance_jobs', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
