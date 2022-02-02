import collections
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase

from hydrus.client import ClientConstants as CC
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling

def GenerateTagSiblingsLookupCacheTableName( display_type: int, service_id: int ):
    
    ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
    
    if display_type == ClientTags.TAG_DISPLAY_IDEAL:
        
        return cache_ideal_tag_siblings_lookup_table_name
        
    elif display_type == ClientTags.TAG_DISPLAY_ACTUAL:
        
        return cache_actual_tag_siblings_lookup_table_name
        
    
def GenerateTagSiblingsLookupCacheTableNames( service_id ):
    
    cache_ideal_tag_siblings_lookup_table_name = 'external_caches.ideal_tag_siblings_lookup_cache_{}'.format( service_id )
    cache_actual_tag_siblings_lookup_table_name = 'external_caches.actual_tag_siblings_lookup_cache_{}'.format( service_id )
    
    return ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name )
    
class ClientDBTagSiblings( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices, modules_tags: ClientDBMaster.ClientDBMasterTags, modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags ):
        
        self.modules_services = modules_services
        self.modules_tags_local_cache = modules_tags_local_cache
        self.modules_tags = modules_tags
        
        self._service_ids_to_display_application_status = {}
        
        self._service_ids_to_applicable_service_ids = None
        self._service_ids_to_interested_service_ids = None
        
        ClientDBModule.ClientDBModule.__init__( self, 'client tag siblings', cursor )
        
    
    def _GenerateApplicationDicts( self ):
        
        unsorted_dict = HydrusData.BuildKeyToListDict( ( master_service_id, ( index, application_service_id ) ) for ( master_service_id, index, application_service_id ) in self._Execute( 'SELECT master_service_id, service_index, application_service_id FROM tag_sibling_application;' ) )
        
        self._service_ids_to_applicable_service_ids = collections.defaultdict( list )
        
        self._service_ids_to_applicable_service_ids.update( { master_service_id : [ application_service_id for ( index, application_service_id ) in sorted( index_and_applicable_service_ids ) ] for ( master_service_id, index_and_applicable_service_ids ) in unsorted_dict.items() } )
        
        self._service_ids_to_interested_service_ids = collections.defaultdict( set )
        
        for ( master_service_id, application_service_ids ) in self._service_ids_to_applicable_service_ids.items():
            
            for application_service_id in application_service_ids:
                
                self._service_ids_to_interested_service_ids[ application_service_id ].add( master_service_id )
                
            
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'tag_siblings' ] = [
            ( [ 'service_id', 'good_tag_id' ], False, 420 )
        ]
        
        index_generation_dict[ 'tag_sibling_petitions' ] = [
            ( [ 'service_id', 'good_tag_id' ], False, 420 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.tag_siblings' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );', 414 ),
            'main.tag_sibling_petitions' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );', 414 ),
            'main.tag_sibling_application' : ( 'CREATE TABLE IF NOT EXISTS {} ( master_service_id INTEGER, service_index INTEGER, application_service_id INTEGER, PRIMARY KEY ( master_service_id, service_index ) );', 414 )
        }
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
        
        index_generation_dict = {}
        
        index_generation_dict[ cache_actual_tag_siblings_lookup_table_name ] = [
            ( [ 'ideal_tag_id' ], False, 414 )
        ]
        
        index_generation_dict[ cache_ideal_tag_siblings_lookup_table_name ] = [
            ( [ 'ideal_tag_id' ], False, 414 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
        
        return {
            cache_actual_tag_siblings_lookup_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER PRIMARY KEY, ideal_tag_id INTEGER );', 414 ),
            cache_ideal_tag_siblings_lookup_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER PRIMARY KEY, ideal_tag_id INTEGER );', 414 )
        }
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
        
    
    def _RepairRepopulateTables( self, repopulate_table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        for service_id in self._GetServiceIdsWeGenerateDynamicTablesFor():
            
            table_generation_dict = self._GetServiceTableGenerationDict( service_id )
            
            this_service_table_names = set( table_generation_dict.keys() )
            
            this_service_needs_repopulation = len( this_service_table_names.intersection( repopulate_table_names ) ) > 0
            
            if this_service_needs_repopulation:
                
                self._service_ids_to_applicable_service_ids = None
                self._service_ids_to_interested_service_ids = None
                
                self.Regen( ( service_id, ) )
                
                cursor_transaction_wrapper.CommitAndBegin()
                
            
        
    
    def AddTagSiblings( self, service_id, pairs ):
        
        self._ExecuteMany( 'DELETE FROM tag_siblings WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ?;', ( ( service_id, bad_tag_id, good_tag_id ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_PENDING ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO tag_siblings ( service_id, bad_tag_id, good_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_CURRENT ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def ClearActual( self, service_id ):
        
        cache_actual_tag_sibling_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_ACTUAL, service_id )
        
        self._Execute( 'DELETE FROM {};'.format( cache_actual_tag_sibling_lookup_table_name ) )
        
        if service_id in self._service_ids_to_display_application_status:
            
            del self._service_ids_to_display_application_status[ service_id ]
            
        
    
    def DeleteTagSiblings( self, service_id, pairs ):
        
        self._ExecuteMany( 'DELETE FROM tag_siblings WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ?;', ( ( service_id, bad_tag_id, good_tag_id ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_PETITIONED ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO tag_siblings ( service_id, bad_tag_id, good_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_DELETED ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def Drop( self, tag_service_id ):
        
        self._Execute( 'DELETE FROM tag_siblings WHERE service_id = ?;', ( tag_service_id, ) )
        self._Execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ?;', ( tag_service_id, ) )
        
        ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( tag_service_id )
        
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( cache_actual_tag_siblings_lookup_table_name ) )
        self._Execute( 'DROP TABLE IF EXISTS {};'.format( cache_ideal_tag_siblings_lookup_table_name ) )
        
        self._Execute( 'DELETE FROM tag_sibling_application WHERE master_service_id = ? OR application_service_id = ?;', ( tag_service_id, tag_service_id ) )
        
        self._service_ids_to_applicable_service_ids = None
        self._service_ids_to_interested_service_ids = None
        
    
    def FilterChained( self, display_type, tag_service_id, tag_ids ):
        
        if len( tag_ids ) == 0:
            
            return set()
            
        elif len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            if self.IsChained( display_type, tag_service_id, tag_id ):
                
                return { tag_id }
                
            else:
                
                return set()
                
            
        
        # get the tag_ids that are part of a sibling chain
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_table_name:
            
            # keep these separate--older sqlite can't do cross join to an OR ON
            
            # temp tags to lookup
            chain_tag_ids = self._STS( self._Execute( 'SELECT tag_id FROM {} CROSS JOIN {} ON ( bad_tag_id = tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ) )
            chain_tag_ids.update( self._STI( self._Execute( 'SELECT tag_id FROM {} CROSS JOIN {} ON ( ideal_tag_id = tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ) ) )
            
        
        return chain_tag_ids
        
    
    def FilterChainedIdealsIntoTable( self, display_type, tag_service_id, tag_ids_table_name, results_table_name ):
        
        # get the tag_ids that are part of a sibling chain
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        # keep these separate--older sqlite can't do cross join to an OR ON
        
        # temp tags to lookup
        self._Execute( 'INSERT OR IGNORE INTO {} SELECT ideal_tag_id FROM {} CROSS JOIN {} ON ( bad_tag_id = tag_id );'.format( results_table_name, tag_ids_table_name, cache_tag_siblings_lookup_table_name ) )
        self._STI( self._Execute( 'INSERT OR IGNORE INTO {} SELECT ideal_tag_id FROM {} CROSS JOIN {} ON ( ideal_tag_id = tag_id );'.format( results_table_name, tag_ids_table_name, cache_tag_siblings_lookup_table_name ) ) )
        
    
    def FilterChainedIntoTable( self, display_type, tag_service_id, tag_ids_table_name, results_table_name ):
        
        # get the tag_ids that are part of a sibling chain
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        # keep these separate--older sqlite can't do cross join to an OR ON
        
        # temp tags to lookup
        self._Execute( 'INSERT OR IGNORE INTO {} SELECT tag_id FROM {} CROSS JOIN {} ON ( bad_tag_id = tag_id );'.format( results_table_name, tag_ids_table_name, cache_tag_siblings_lookup_table_name ) )
        self._STI( self._Execute( 'INSERT OR IGNORE INTO {} SELECT tag_id FROM {} CROSS JOIN {} ON ( ideal_tag_id = tag_id );'.format( results_table_name, tag_ids_table_name, cache_tag_siblings_lookup_table_name ) ) )
        
    
    def Generate( self, tag_service_id ):
        
        table_generation_dict = self._GetServiceTableGenerationDict( tag_service_id )
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
        index_generation_dict = self._GetServiceIndexGenerationDict( tag_service_id )
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
        self._Execute( 'INSERT OR IGNORE INTO tag_sibling_application ( master_service_id, service_index, application_service_id ) VALUES ( ?, ?, ? );', ( tag_service_id, 0, tag_service_id ) )
        
        self._service_ids_to_applicable_service_ids = None
        self._service_ids_to_interested_service_ids = None
        
        self.Regen( ( tag_service_id, ) )
        
    
    def GetAllTagIds( self, display_type, tag_service_id ):
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        tag_ids = set()
        
        tag_ids.update( self._STI( self._Execute( 'SELECT DISTINCT bad_tag_id FROM {};'.format( cache_tag_siblings_lookup_table_name ) ) ) )
        tag_ids.update( self._STI( self._Execute( 'SELECT ideal_tag_id FROM {};'.format( cache_tag_siblings_lookup_table_name ) ) ) )
        
        return tag_ids
        
    
    def GetApplicableServiceIds( self, tag_service_id ):
        
        if self._service_ids_to_applicable_service_ids is None:
            
            self._GenerateApplicationDicts()
            
        
        return self._service_ids_to_applicable_service_ids[ tag_service_id ]
        
    
    def GetApplication( self ):
        
        if self._service_ids_to_applicable_service_ids is None:
            
            self._GenerateApplicationDicts()
            
        
        service_ids_to_service_keys = {}
        
        service_keys_to_applicable_service_keys = {}
        
        for ( master_service_id, applicable_service_ids ) in self._service_ids_to_applicable_service_ids.items():
            
            all_service_ids = [ master_service_id ] + list( applicable_service_ids )
            
            for service_id in all_service_ids:
                
                if service_id not in service_ids_to_service_keys:
                    
                    service_ids_to_service_keys[ service_id ] = self.modules_services.GetService( service_id ).GetServiceKey()
                    
                
            
            service_keys_to_applicable_service_keys[ service_ids_to_service_keys[ master_service_id ] ] = [ service_ids_to_service_keys[ service_id ] for service_id in applicable_service_ids ]
            
        
        return service_keys_to_applicable_service_keys
        
    
    def GetApplicationStatus( self, service_id ):
        
        if service_id not in self._service_ids_to_display_application_status:
            
            ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
            
            actual_sibling_rows = set( self._Execute( 'SELECT bad_tag_id, ideal_tag_id FROM {};'.format( cache_actual_tag_siblings_lookup_table_name ) ) )
            ideal_sibling_rows = set( self._Execute( 'SELECT bad_tag_id, ideal_tag_id FROM {};'.format( cache_ideal_tag_siblings_lookup_table_name ) ) )
            
            sibling_rows_to_remove = actual_sibling_rows.difference( ideal_sibling_rows )
            sibling_rows_to_add = ideal_sibling_rows.difference( actual_sibling_rows )
            
            num_actual_rows = len( actual_sibling_rows )
            num_ideal_rows = len( ideal_sibling_rows )
            
            self._service_ids_to_display_application_status[ service_id ] = ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows )
            
        
        ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows ) = self._service_ids_to_display_application_status[ service_id ]
        
        return ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows )
        
    
    def GetChainMembersFromIdeal( self, display_type, tag_service_id, ideal_tag_id ) -> typing.Set[ int ]:
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        sibling_tag_ids = self._STS( self._Execute( 'SELECT bad_tag_id FROM {} WHERE ideal_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( ideal_tag_id, ) ) )
        
        sibling_tag_ids.add( ideal_tag_id )
        
        return sibling_tag_ids
        
    
    def GetChainsMembersFromIdeals( self, display_type, tag_service_id, ideal_tag_ids ) -> typing.Set[ int ]:
        
        if len( ideal_tag_ids ) == 0:
            
            return set()
            
        elif len( ideal_tag_ids ) == 1:
            
            ( ideal_tag_id, ) = ideal_tag_ids
            
            return self.GetChainMembersFromIdeal( display_type, tag_service_id, ideal_tag_id )
            
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        with self._MakeTemporaryIntegerTable( ideal_tag_ids, 'ideal_tag_id' ) as temp_table_name:
            
            # temp tags to lookup
            sibling_tag_ids = self._STS( self._Execute( 'SELECT bad_tag_id FROM {} CROSS JOIN {} USING ( ideal_tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ) )
            
        
        sibling_tag_ids.update( ideal_tag_ids )
        
        return sibling_tag_ids
        
    
    def GetChainsMembersFromIdealsTables( self, display_type, tag_service_id, ideal_tag_ids_table_name, results_table_name ) -> typing.Set[ int ]:
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id ) SELECT ideal_tag_id FROM {};'.format( results_table_name, ideal_tag_ids_table_name ) )
        
        # tags to lookup
        self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id ) SELECT bad_tag_id FROM {} CROSS JOIN {} USING ( ideal_tag_id );'.format( results_table_name, ideal_tag_ids_table_name, cache_tag_siblings_lookup_table_name ) )
        
    
    def GetIdeal( self, display_type, tag_service_id, tag_id ) -> int:
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        result = self._Execute( 'SELECT ideal_tag_id FROM {} WHERE bad_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( tag_id, ) ).fetchone()
        
        if result is None:
            
            return tag_id
            
        else:
            
            ( ideal_tag_id, ) = result
            
            return ideal_tag_id
            
        
    
    def GetIdeals( self, display_type, tag_service_id, tag_ids ) -> typing.Set[ int ]:
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        if len( tag_ids ) == 0:
            
            return set()
            
        elif len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            return { self.GetIdeal( display_type, tag_service_id, tag_id ) }
            
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_tag_ids_table_name:
            
            magic_case = 'CASE WHEN ideal_tag_id NOT NULL THEN ideal_tag_id ELSE tag_id END'
            
            cursor = self._Execute(
                'SELECT {} FROM {} LEFT OUTER JOIN {} ON ( tag_id = bad_tag_id );'.format(
                    magic_case,
                    temp_tag_ids_table_name,
                    cache_tag_siblings_lookup_table_name
                )
            )
            
            return self._STS( cursor )
            
        
        '''
        no_ideal_found_tag_ids = set( tag_ids )
        ideal_tag_ids = set()
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_table_name:
            
            # temp tags to lookup
            for ( tag_id, ideal_tag_id ) in self._Execute( 'SELECT tag_id, ideal_tag_id FROM {} CROSS JOIN {} ON ( bad_tag_id = tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ):
                
                no_ideal_found_tag_ids.discard( tag_id )
                ideal_tag_ids.add( ideal_tag_id )
                
            
            ideal_tag_ids.update( no_ideal_found_tag_ids )
            
        
        return ideal_tag_ids
        '''
        
    
    def GetIdealsIntoTable( self, display_type, tag_service_id, tag_ids_table_name, results_table_name ):
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        magic_case = 'CASE WHEN ideal_tag_id NOT NULL THEN ideal_tag_id ELSE tag_id END'
        
        cursor = self._Execute(
            'INSERT OR IGNORE INTO {} ( ideal_tag_id ) SELECT {} FROM {} LEFT OUTER JOIN {} ON ( tag_id = bad_tag_id );'.format(
                results_table_name,
                magic_case,
                tag_ids_table_name,
                cache_tag_siblings_lookup_table_name
            )
        )
        
        return self._STS( cursor )
        
    
    def GetIdealsToChains( self, display_type, tag_service_id, ideal_tag_ids ):
        
        # this only takes ideal_tag_ids
        
        if len( ideal_tag_ids ) == 0:
            
            return {}
            
        elif len( ideal_tag_ids ) == 1:
            
            ( ideal_tag_id, ) = ideal_tag_ids
            
            chain_tag_ids = self.GetChainMembersFromIdeal( display_type, tag_service_id, ideal_tag_id )
            
            return { ideal_tag_id : chain_tag_ids }
            
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        with self._MakeTemporaryIntegerTable( ideal_tag_ids, 'ideal_tag_id' ) as temp_table_name:
            
            # temp tags to lookup
            ideal_tag_ids_to_chain_members = HydrusData.BuildKeyToSetDict( self._Execute( 'SELECT ideal_tag_id, bad_tag_id FROM {} CROSS JOIN {} USING ( ideal_tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ) )
            
        
        # this returns ideal in the chain, and chains of size 1
        
        for ideal_tag_id in ideal_tag_ids:
            
            ideal_tag_ids_to_chain_members[ ideal_tag_id ].add( ideal_tag_id )
            
        
        return ideal_tag_ids_to_chain_members
        
    
    def GetInterestedServiceIds( self, tag_service_id ):
        
        if self._service_ids_to_interested_service_ids is None:
            
            self._GenerateApplicationDicts()
            
        
        return self._service_ids_to_interested_service_ids[ tag_service_id ]
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            return [
                ( 'tag_siblings', 'bad_tag_id' ),
                ( 'tag_siblings', 'good_tag_id' ),
                ( 'tag_sibling_petitions', 'bad_tag_id' ),
                ( 'tag_sibling_petitions', 'good_tag_id' )
            ]
            
        
        return []
        
    
    def GetTagSiblingsForTags( self, service_key, tags ):
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = ( self.modules_services.GetServiceId( service_key ), )
            
        
        existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
        
        existing_tag_ids = set( self.modules_tags_local_cache.GetTagIdsToTags( tags = existing_tags ).keys() )
        
        tag_ids_to_chain_tag_ids = collections.defaultdict( set )
        
        for tag_service_id in tag_service_ids:
            
            tag_ids_to_ideal_tag_ids = self.GetTagsToIdeals( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, existing_tag_ids )
            
            ideal_tag_ids = set( tag_ids_to_ideal_tag_ids.values() )
            
            ideal_tag_ids_to_chain_tag_ids = self.GetIdealsToChains( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id, ideal_tag_ids )
            
            for tag_id in existing_tag_ids:
                
                chain_tag_ids = ideal_tag_ids_to_chain_tag_ids[ tag_ids_to_ideal_tag_ids[ tag_id ] ]
                
                tag_ids_to_chain_tag_ids[ tag_id ].update( chain_tag_ids )
                
            
        
        all_tag_ids = set( tag_ids_to_chain_tag_ids.keys() )
        all_tag_ids.update( itertools.chain.from_iterable( tag_ids_to_chain_tag_ids.values() ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
        
        tags_to_siblings = { tag_ids_to_tags[ tag_id ] : { tag_ids_to_tags[ chain_tag_id ] for chain_tag_id in chain_tag_ids } for ( tag_id, chain_tag_ids ) in tag_ids_to_chain_tag_ids.items() }
        
        for tag in tags:
            
            if tag not in existing_tags:
                
                tags_to_siblings[ tag ] = { tag }
                
            
        
        return tags_to_siblings
        
    
    def GetTagSiblingsIdeals( self, service_key ):
        
        tag_service_id = self.modules_services.GetServiceId( service_key )
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_ACTUAL, tag_service_id )
        
        pair_ids = self._Execute( 'SELECT bad_tag_id, ideal_tag_id FROM {};'.format( cache_tag_siblings_lookup_table_name ) ).fetchall()
        
        all_tag_ids = set( itertools.chain.from_iterable( pair_ids ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
        
        tags_to_ideals = { tag_ids_to_tags[ bad_tag_id ] : tag_ids_to_tags[ good_tag_id ] for ( bad_tag_id, good_tag_id ) in pair_ids }
        
        return tags_to_ideals
        
    
    def GetTagsToIdeals( self, display_type, tag_service_id, tag_ids ):
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        if len( tag_ids ) == 0:
            
            return {}
            
        elif len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            return { tag_id : self.GetIdeal( display_type, tag_service_id, tag_id ) }
            
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        no_ideal_found_tag_ids = set( tag_ids )
        tag_ids_to_ideal_tag_ids = {}
        
        with self._MakeTemporaryIntegerTable( tag_ids, 'tag_id' ) as temp_table_name:
            
            # temp tags to lookup
            for ( tag_id, ideal_tag_id ) in self._Execute( 'SELECT tag_id, ideal_tag_id FROM {} CROSS JOIN {} ON ( bad_tag_id = tag_id );'.format( temp_table_name, cache_tag_siblings_lookup_table_name ) ):
                
                no_ideal_found_tag_ids.discard( tag_id )
                tag_ids_to_ideal_tag_ids[ tag_id ] = ideal_tag_id
                
            
            tag_ids_to_ideal_tag_ids.update( { tag_id : tag_id for tag_id in no_ideal_found_tag_ids } )
            
        
        return tag_ids_to_ideal_tag_ids
        
    
    def GetTagSiblings( self, service_key ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        statuses_to_pair_ids = self.GetTagSiblingsIds( service_id )
        
        all_tag_ids = set()
        
        for pair_ids in statuses_to_pair_ids.values():
            
            for ( bad_tag_id, good_tag_id ) in pair_ids:
                
                all_tag_ids.add( bad_tag_id )
                all_tag_ids.add( good_tag_id )
                
            
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
        
        statuses_to_pairs = collections.defaultdict( set )
        
        statuses_to_pairs.update( { status : { ( tag_ids_to_tags[ bad_tag_id ], tag_ids_to_tags[ good_tag_id ] ) for ( bad_tag_id, good_tag_id ) in pair_ids } for ( status, pair_ids ) in statuses_to_pair_ids.items() } )
        
        return statuses_to_pairs
        
    
    def GetTagSiblingsIds( self, service_id ):
        
        statuses_and_pair_ids = self._Execute( 'SELECT status, bad_tag_id, good_tag_id FROM tag_siblings WHERE service_id = ? UNION SELECT status, bad_tag_id, good_tag_id FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, service_id ) ).fetchall()
        
        unsorted_statuses_to_pair_ids = HydrusData.BuildKeyToListDict( ( status, ( bad_tag_id, good_tag_id ) ) for ( status, bad_tag_id, good_tag_id ) in statuses_and_pair_ids )
        
        statuses_to_pair_ids = collections.defaultdict( list )
        
        statuses_to_pair_ids.update( { status : sorted( pair_ids ) for ( status, pair_ids ) in unsorted_statuses_to_pair_ids.items() } )
        
        return statuses_to_pair_ids
        
    
    def GetTagSiblingsIdsChains( self, service_id, tag_ids ):
        
        done_tag_ids = set()
        next_tag_ids = set( tag_ids )
        result_rows = set()
        
        while len( next_tag_ids ) > 0:
            
            with self._MakeTemporaryIntegerTable( next_tag_ids, 'tag_id' ) as temp_next_tag_ids_table_name:
                
                done_tag_ids.update( next_tag_ids )
                
                next_tag_ids = set()
                
                # keep these separate--older sqlite can't do cross join to an OR ON
                
                # temp tag_ids to siblings
                queries = [
                    'SELECT status, bad_tag_id, good_tag_id FROM {} CROSS JOIN tag_siblings ON ( bad_tag_id = tag_id ) WHERE service_id = ?'.format( temp_next_tag_ids_table_name ),
                    'SELECT status, bad_tag_id, good_tag_id FROM {} CROSS JOIN tag_siblings ON ( good_tag_id = tag_id ) WHERE service_id = ?'.format( temp_next_tag_ids_table_name ),
                    'SELECT status, bad_tag_id, good_tag_id FROM {} CROSS JOIN tag_sibling_petitions ON ( bad_tag_id = tag_id ) WHERE service_id = ?'.format( temp_next_tag_ids_table_name ),
                    'SELECT status, bad_tag_id, good_tag_id FROM {} CROSS JOIN tag_sibling_petitions ON ( good_tag_id = tag_id ) WHERE service_id = ?'.format( temp_next_tag_ids_table_name )
                ]
                
                query = ' UNION '.join( queries )
                
                for row in self._Execute( query, ( service_id, service_id, service_id, service_id ) ):
                    
                    result_rows.add( row )
                    
                    ( status, bad_tag_id, good_tag_id ) = row
                    
                    for tag_id in ( bad_tag_id, good_tag_id ):
                        
                        if tag_id not in done_tag_ids:
                            
                            next_tag_ids.add( tag_id )
                            
                        
                    
                
            
        
        unsorted_statuses_to_pair_ids = HydrusData.BuildKeyToListDict( ( status, ( bad_tag_id, good_tag_id ) ) for ( status, bad_tag_id, good_tag_id ) in result_rows )
        
        statuses_to_pair_ids = collections.defaultdict( list )
        
        statuses_to_pair_ids.update( { status : sorted( pair_ids ) for ( status, pair_ids ) in unsorted_statuses_to_pair_ids.items() } )
        
        return statuses_to_pair_ids
        
    
    def IsChained( self, display_type, tag_service_id, tag_id ):
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        return self._Execute( 'SELECT 1 FROM {} WHERE bad_tag_id = ? OR ideal_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( tag_id, tag_id ) ).fetchone() is not None
        
    
    def NotifySiblingAddRowSynced( self, tag_service_id, row ):
        
        if tag_service_id in self._service_ids_to_display_application_status:
            
            ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows ) = self._service_ids_to_display_application_status[ tag_service_id ]
            
            sibling_rows_to_add.discard( row )
            
            num_actual_rows += 1
            
            self._service_ids_to_display_application_status[ tag_service_id ] = ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows )
            
        
    
    def NotifySiblingDeleteRowSynced( self, tag_service_id, row ):
        
        if tag_service_id in self._service_ids_to_display_application_status:
            
            ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows ) = self._service_ids_to_display_application_status[ tag_service_id ]
            
            sibling_rows_to_remove.discard( row )
            
            num_actual_rows -= 1
            
            self._service_ids_to_display_application_status[ tag_service_id ] = ( sibling_rows_to_add, sibling_rows_to_remove, num_actual_rows, num_ideal_rows )
            
        
    
    def PendTagSiblings( self, service_id, triples ):
        
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ?;', ( ( service_id, bad_tag_id, good_tag_id ) for ( bad_tag_id, good_tag_id, reason_id ) in triples ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO tag_sibling_petitions ( service_id, bad_tag_id, good_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, reason_id, HC.CONTENT_STATUS_PENDING ) for ( bad_tag_id, good_tag_id, reason_id ) in triples ) )
        
    
    def PetitionTagSiblings( self, service_id, triples ):
        
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ?;', ( ( service_id, bad_tag_id, good_tag_id ) for ( bad_tag_id, good_tag_id, reason_id ) in triples ) )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO tag_sibling_petitions ( service_id, bad_tag_id, good_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, reason_id, HC.CONTENT_STATUS_PETITIONED ) for ( bad_tag_id, good_tag_id, reason_id ) in triples ) )
        
    
    def RescindPendingTagSiblings( self, service_id, pairs ):
        
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_PENDING ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def RescindPetitionedTagSiblings( self, service_id, pairs ):
        
        self._ExecuteMany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND good_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_PETITIONED ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def Regen( self, tag_service_ids ):
        
        for tag_service_id in tag_service_ids:
            
            cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_IDEAL, tag_service_id )
            
            self._Execute( 'DELETE FROM {};'.format( cache_tag_siblings_lookup_table_name ) )
            
            applicable_service_ids = self.GetApplicableServiceIds( tag_service_id )
            
            tss = ClientTagsHandling.TagSiblingsStructure()
            
            for applicable_service_id in applicable_service_ids:
                
                statuses_to_pair_ids = self.GetTagSiblingsIds( service_id = applicable_service_id )
                
                petitioned_fast_lookup = set( statuses_to_pair_ids[ HC.CONTENT_STATUS_PETITIONED ] )
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if ( bad_tag_id, good_tag_id ) in petitioned_fast_lookup:
                        
                        continue
                        
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_PENDING ]:
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( bad_tag_id, ideal_tag_id ) VALUES ( ?, ? );'.format( cache_tag_siblings_lookup_table_name ), tss.GetBadTagsToIdealTags().items() )
            
            if tag_service_id in self._service_ids_to_display_application_status:
                
                del self._service_ids_to_display_application_status[ tag_service_id ]
                
            
        
    
    def RegenChains( self, tag_service_ids, tag_ids ):
        
        # as this guy can change ideals, the related parent chains need to be regenned afterwards too
        
        if len( tag_ids ) == 0:
            
            return
            
        
        for tag_service_id in tag_service_ids:
            
            cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_IDEAL, tag_service_id )
            
            tag_ids_to_clear_and_regen = set( tag_ids )
            
            ideal_tag_ids = self.GetIdeals( ClientTags.TAG_DISPLAY_IDEAL, tag_service_id, tag_ids )
            
            tag_ids_to_clear_and_regen.update( self.GetChainsMembersFromIdeals( ClientTags.TAG_DISPLAY_IDEAL, tag_service_id, ideal_tag_ids ) )
            
            self._ExecuteMany( 'DELETE FROM {} WHERE bad_tag_id = ? OR ideal_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( ( tag_id, tag_id ) for tag_id in tag_ids_to_clear_and_regen ) )
            
            applicable_tag_service_ids = self.GetApplicableServiceIds( tag_service_id )
            
            tss = ClientTagsHandling.TagSiblingsStructure()
            
            for applicable_tag_service_id in applicable_tag_service_ids:
                
                service_key = self.modules_services.GetService( applicable_tag_service_id ).GetServiceKey()
                
                statuses_to_pair_ids = self.GetTagSiblingsIdsChains( applicable_tag_service_id, tag_ids_to_clear_and_regen )
                
                petitioned_fast_lookup = set( statuses_to_pair_ids[ HC.CONTENT_STATUS_PETITIONED ] )
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if ( bad_tag_id, good_tag_id ) in petitioned_fast_lookup:
                        
                        continue
                        
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_PENDING ]:
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( bad_tag_id, ideal_tag_id ) VALUES ( ?, ? );'.format( cache_tag_siblings_lookup_table_name ), tss.GetBadTagsToIdealTags().items() )
            
            if tag_service_id in self._service_ids_to_display_application_status:
                
                del self._service_ids_to_display_application_status[ tag_service_id ]
                
            
        
    
    def SetApplication( self, service_keys_to_applicable_service_keys ):
        
        if self._service_ids_to_applicable_service_ids is None:
            
            self._GenerateApplicationDicts()
            
        
        new_service_ids_to_applicable_service_ids = collections.defaultdict( list )
        
        for ( master_service_key, applicable_service_keys ) in service_keys_to_applicable_service_keys.items():
            
            master_service_id = self.modules_services.GetServiceId( master_service_key )
            applicable_service_ids = [ self.modules_services.GetServiceId( service_key ) for service_key in applicable_service_keys ]
            
            new_service_ids_to_applicable_service_ids[ master_service_id ] = applicable_service_ids
            
        
        old_and_new_master_service_ids = set( self._service_ids_to_applicable_service_ids.keys() )
        old_and_new_master_service_ids.update( new_service_ids_to_applicable_service_ids.keys() )
        
        inserts = []
        
        service_ids_to_sync = set()
        
        for master_service_id in old_and_new_master_service_ids:
            
            if master_service_id in new_service_ids_to_applicable_service_ids:
                
                applicable_service_ids = new_service_ids_to_applicable_service_ids[ master_service_id ]
                
                inserts.extend( ( ( master_service_id, i, applicable_service_id ) for ( i, applicable_service_id ) in enumerate( applicable_service_ids ) ) )
                
                if applicable_service_ids != self._service_ids_to_applicable_service_ids[ master_service_id ]:
                    
                    service_ids_to_sync.add( master_service_id )
                    
                
            else:
                
                service_ids_to_sync.add( master_service_id )
                
            
        
        self._Execute( 'DELETE FROM tag_sibling_application;' )
        
        self._ExecuteMany( 'INSERT OR IGNORE INTO tag_sibling_application ( master_service_id, service_index, application_service_id ) VALUES ( ?, ?, ? );', inserts )
        
        self._service_ids_to_applicable_service_ids = None
        self._service_ids_to_interested_service_ids = None
        
        return service_ids_to_sync
        
    
