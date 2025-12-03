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
from hydrus.client.duplicates import ClientDuplicates

class ClientDBFilesDuplicatesStorage( ClientDBModule.ClientDBModule ):
    
    def __init__(
        self,
        cursor: sqlite3.Cursor,
        modules_files_storage: ClientDBFilesStorage.ClientDBFilesStorage,
        modules_hashes_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalHashes,
        ):
        
        super().__init__( 'client file duplicates', cursor )
        
        self.modules_files_storage = modules_files_storage
        self.modules_hashes_local_cache = modules_hashes_local_cache
        
    
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
        
    
    def AlternatesGroupsAreFalsePositive( self, alternates_group_id_a, alternates_group_id_b ):
        
        if alternates_group_id_a == alternates_group_id_b:
            
            return False
            
        
        smaller_alternates_group_id = min( alternates_group_id_a, alternates_group_id_b )
        larger_alternates_group_id = max( alternates_group_id_a, alternates_group_id_b )
        
        result = self._Execute( 'SELECT 1 FROM duplicate_false_positives WHERE smaller_alternates_group_id = ? AND larger_alternates_group_id = ?;', ( smaller_alternates_group_id, larger_alternates_group_id ) ).fetchone()
        
        false_positive_pair_found = result is not None
        
        return false_positive_pair_found
        
    
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
        
    
    def FilterMediaIdPairs( self, location_context: ClientLocation.LocationContext, media_id_pairs ):
        
        if len( media_id_pairs ) == 0:
            
            return []
            
        
        # this is pretty wonked out due to me not wanting to force db_location_context to make a single table
        
        all_media_ids = { i for i in itertools.chain.from_iterable( media_id_pairs ) }
        
        with self._MakeTemporaryIntegerTable( all_media_ids, 'media_id' ) as temp_media_ids_table_name:
            
            hash_ids_to_media_ids = dict( self._Execute( 'SELECT hash_id, media_id FROM {} CROSS JOIN {} USING ( media_id );'.format( temp_media_ids_table_name, 'duplicate_file_members' ) ) )
            
        
        all_hash_ids = set( hash_ids_to_media_ids.keys() )
        
        good_hash_ids = self.modules_files_storage.FilterHashIds( location_context, all_hash_ids )
        
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
            
            potential_pairs = self.FilterMediaIdPairs( location_context, all_potential_pairs )
            
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
            
            filtered_hash_ids = self.modules_files_storage.FilterHashIds( ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ), { hash_id } )
            
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
        
    
    def IsKing( self, hash_id: int   ):
        
        result = self._Execute( 'SELECT king_hash_id FROM duplicate_file_members CROSS JOIN duplicate_files USING ( media_id ) WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            return True
            
        else:
            
            ( king_hash_id, ) = result
            
            return king_hash_id == hash_id
            
        
    
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
        
    
