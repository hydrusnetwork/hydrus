import collections
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDBBase

from hydrus.client import ClientConstants as CC
from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaintenance
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling

def GenerateTagSiblingsLookupCacheTableName( display_type: int, service_id: int ):
    
    ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
    
    if display_type == ClientTags.TAG_DISPLAY_DISPLAY_IDEAL:
        
        return cache_ideal_tag_siblings_lookup_table_name
        
    elif display_type == ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL:
        
        return cache_actual_tag_siblings_lookup_table_name
        
    

TAG_SIBLINGS_IDEAL_PREFIX = 'ideal_tag_siblings_lookup_cache_'
TAG_SIBLINGS_ACTUAL_PREFIX = 'actual_tag_siblings_lookup_cache_'

def GenerateTagSiblingsLookupCacheTableNames( service_id ):
    
    suffix = service_id
    
    cache_ideal_tag_siblings_lookup_table_name = f'external_caches.{TAG_SIBLINGS_IDEAL_PREFIX}{suffix}'
    cache_actual_tag_siblings_lookup_table_name = f'external_caches.{TAG_SIBLINGS_ACTUAL_PREFIX}{suffix}'
    
    return ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name )
    

TAG_SIBLINGS_CURRENT_STORAGE_PREFIX = 'current_tag_siblings_'
TAG_SIBLINGS_DELETED_STORAGE_PREFIX = 'deleted_tag_siblings_'
TAG_SIBLINGS_PENDING_STORAGE_PREFIX = 'pending_tag_siblings_'
TAG_SIBLINGS_PETITIONED_STORAGE_PREFIX = 'petitioned_tag_siblings_'

def GenerateTagSiblingsStorageTableNames( service_id ):
    
    suffix = service_id
    
    return {
        HC.CONTENT_STATUS_CURRENT : f'{TAG_SIBLINGS_CURRENT_STORAGE_PREFIX}{suffix}',
        HC.CONTENT_STATUS_DELETED : f'{TAG_SIBLINGS_DELETED_STORAGE_PREFIX}{suffix}',
        HC.CONTENT_STATUS_PENDING : f'{TAG_SIBLINGS_PENDING_STORAGE_PREFIX}{suffix}',
        HC.CONTENT_STATUS_PETITIONED : f'{TAG_SIBLINGS_PETITIONED_STORAGE_PREFIX}{suffix}'
    }
    

class ClientDBTagSiblings( ClientDBModule.ClientDBModule ):
    
    CAN_REPOPULATE_ALL_MISSING_DATA = True
    
    def __init__( self, cursor: sqlite3.Cursor, modules_db_maintenance: ClientDBMaintenance.ClientDBMaintenance, modules_services: ClientDBServices.ClientDBMasterServices, modules_tags: ClientDBMaster.ClientDBMasterTags, modules_tags_local_cache: ClientDBDefinitionsCache.ClientDBCacheLocalTags ):
        
        self.modules_db_maintenance = modules_db_maintenance
        self.modules_services = modules_services
        self.modules_tags_local_cache = modules_tags_local_cache
        self.modules_tags = modules_tags
        
        self._service_ids_to_display_application_status = {}
        
        self._service_ids_to_applicable_service_ids = None
        self._service_ids_to_interested_service_ids = None
        
        super().__init__( 'client tag siblings', cursor )
        
    
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
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
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
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        index_generation_dict[ statuses_to_storage_table_names[ HC.CONTENT_STATUS_CURRENT ] ] = [
            ( [ 'good_tag_id' ], False, 586 )
        ]
        
        index_generation_dict[ statuses_to_storage_table_names[ HC.CONTENT_STATUS_DELETED ] ] = [
            ( [ 'good_tag_id' ], False, 586 )
        ]
        
        index_generation_dict[ statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ] ] = [
            ( [ 'good_tag_id' ], False, 586 )
        ]
        
        index_generation_dict[ statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ] ] = [
            ( [ 'good_tag_id' ], False, 586 )
        ]
        
        return index_generation_dict
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( service_id )
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        return {
            cache_actual_tag_siblings_lookup_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER PRIMARY KEY, ideal_tag_id INTEGER );', 414 ),
            cache_ideal_tag_siblings_lookup_table_name : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER PRIMARY KEY, ideal_tag_id INTEGER );', 414 ),
            statuses_to_storage_table_names[ HC.CONTENT_STATUS_CURRENT ] : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER, good_tag_id INTEGER, PRIMARY KEY ( bad_tag_id, good_tag_id ) );', 586 ),
            statuses_to_storage_table_names[ HC.CONTENT_STATUS_DELETED ] : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER, good_tag_id INTEGER, PRIMARY KEY ( bad_tag_id, good_tag_id ) );', 586 ),
            statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ] : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER, good_tag_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_tag_id, good_tag_id ) );', 586 ),
            statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ] : ( 'CREATE TABLE IF NOT EXISTS {} ( bad_tag_id INTEGER, good_tag_id INTEGER, reason_id INTEGER, PRIMARY KEY ( bad_tag_id, good_tag_id ) );', 586 )
        }
        
    
    def _GetServiceTablePrefixes( self ):
        
        return {
            TAG_SIBLINGS_IDEAL_PREFIX,
            TAG_SIBLINGS_ACTUAL_PREFIX,
            TAG_SIBLINGS_CURRENT_STORAGE_PREFIX,
            TAG_SIBLINGS_DELETED_STORAGE_PREFIX,
            TAG_SIBLINGS_PENDING_STORAGE_PREFIX,
            TAG_SIBLINGS_PETITIONED_STORAGE_PREFIX
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
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[HC.CONTENT_STATUS_DELETED]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[HC.CONTENT_STATUS_PENDING]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        
        self._ExecuteMany( f'INSERT OR IGNORE INTO {statuses_to_storage_table_names[HC.CONTENT_STATUS_CURRENT]} ( bad_tag_id, good_tag_id ) VALUES ( ?, ? );', pairs )
        
    
    def ClearActual( self, service_id, tag_ids = None ):
        
        cache_actual_tag_sibling_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, service_id )
        
        if tag_ids is None:
            
            self._Execute( f'DELETE FROM {cache_actual_tag_sibling_lookup_table_name};' )
            
        else:
            
            self._ExecuteMany( f'DELETE FROM {cache_actual_tag_sibling_lookup_table_name} WHERE bad_tag_id = ? OR ideal_tag_id = ?;', ( ( tag_id, tag_id ) for tag_id in tag_ids ) )
            
        
        if service_id in self._service_ids_to_display_application_status:
            
            del self._service_ids_to_display_application_status[ service_id ]
            
        
    
    def DeletePending( self, service_id ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._Execute( f'DELETE FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ]};' )
        self._Execute( f'DELETE FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ]};' )
        
    
    def DeleteTagSiblings( self, service_id, pairs ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[HC.CONTENT_STATUS_CURRENT]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[HC.CONTENT_STATUS_PETITIONED]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        
        self._ExecuteMany( f'INSERT OR IGNORE INTO {statuses_to_storage_table_names[HC.CONTENT_STATUS_DELETED]} ( bad_tag_id, good_tag_id ) VALUES ( ?, ? );', pairs )
        
    
    def Drop( self, tag_service_id ):
        
        for table_name in GenerateTagSiblingsStorageTableNames( tag_service_id ).values():
            
            self.modules_db_maintenance.DeferredDropTable( table_name )
            
        
        ( cache_ideal_tag_siblings_lookup_table_name, cache_actual_tag_siblings_lookup_table_name ) = GenerateTagSiblingsLookupCacheTableNames( tag_service_id )
        
        self.modules_db_maintenance.DeferredDropTable( cache_actual_tag_siblings_lookup_table_name )
        self.modules_db_maintenance.DeferredDropTable( cache_ideal_tag_siblings_lookup_table_name )
        
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
            
            self._CreateTable( create_query_without_name, table_name )
            
        
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
            
            self._service_ids_to_display_application_status[ service_id ] = ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove )
            
        
        ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove ) = self._service_ids_to_display_application_status[ service_id ]
        
        return ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove )
        
    
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
        
    
    def GetChainsMembersFromIdealsTables( self, display_type, tag_service_id, ideal_tag_ids_table_name, results_table_name ):
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id ) SELECT ideal_tag_id FROM {};'.format( results_table_name, ideal_tag_ids_table_name ) )
        
        # tags to lookup
        self._Execute( 'INSERT OR IGNORE INTO {} ( tag_id ) SELECT bad_tag_id FROM {} CROSS JOIN {} USING ( ideal_tag_id );'.format( results_table_name, ideal_tag_ids_table_name, cache_tag_siblings_lookup_table_name ) )
        
    
    def GetIdeals( self, tag_display_type, service_key, tags ) -> typing.Set[ str ]:
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = ( self.modules_services.GetServiceId( service_key ), )
            
        
        existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
        
        existing_tag_ids = set( self.modules_tags_local_cache.GetTagIdsToTags( tags = existing_tags ).keys() )
        
        result_ideal_tag_ids = set()
        
        for tag_service_id in tag_service_ids:
            
            ideal_tag_ids = self.GetIdealTagIds( tag_display_type, tag_service_id, existing_tag_ids )
            
            result_ideal_tag_ids.update( ideal_tag_ids )
            
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = result_ideal_tag_ids )
        
        ideal_tags = set( tag_ids_to_tags.values() )
        
        for tag in tags:
            
            if tag not in existing_tags:
                
                ideal_tags.add( tag )
                
            
        
        return ideal_tags
        
    
    def GetIdealTagId( self, display_type, tag_service_id, tag_id ) -> int:
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        result = self._Execute( 'SELECT ideal_tag_id FROM {} WHERE bad_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( tag_id, ) ).fetchone()
        
        if result is None:
            
            return tag_id
            
        else:
            
            ( ideal_tag_id, ) = result
            
            return ideal_tag_id
            
        
    
    def GetIdealTagIds( self, display_type, tag_service_id, tag_ids ) -> typing.Set[ int ]:
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        if len( tag_ids ) == 0:
            
            return set()
            
        elif len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            return { self.GetIdealTagId( display_type, tag_service_id, tag_id ) }
            
        
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
        
    
    def GetIdealTagIdsIntoTable( self, display_type, tag_service_id, tag_ids_table_name, results_table_name ):
        
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
        
    
    def GetIdealTagIdsToChains( self, display_type, tag_service_id, ideal_tag_ids ):
        
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
        
    
    def GetPendingSiblingsCount( self, service_id: int ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        ( info, ) = self._Execute( f'SELECT COUNT( * ) FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ]};' ).fetchone()
        
        return info
        
    
    def GetPetitionedSiblingsCount( self, service_id: int ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        ( info, ) = self._Execute( f'SELECT COUNT( * ) FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ]};' ).fetchone()
        
        return info
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_TAG:
            
            for service_id in self._GetServiceIdsWeGenerateDynamicTablesFor():
                
                for table_name in GenerateTagSiblingsStorageTableNames( service_id ).values():
                    
                    tables_and_columns.append( ( table_name, 'bad_tag_id' ) )
                    tables_and_columns.append( ( table_name, 'good_tag_id' ) )
                    
                
                for table_name in GenerateTagSiblingsLookupCacheTableNames( service_id ):
                    
                    tables_and_columns.append( ( table_name, 'bad_tag_id' ) )
                    tables_and_columns.append( ( table_name, 'ideal_tag_id' ) )
                    
                
            
        
        return tables_and_columns
        
    
    def GetTagIdsToIdealTagIds( self, display_type, tag_service_id, tag_ids ):
        
        if not isinstance( tag_ids, set ):
            
            tag_ids = set( tag_ids )
            
        
        if len( tag_ids ) == 0:
            
            return {}
            
        elif len( tag_ids ) == 1:
            
            ( tag_id, ) = tag_ids
            
            return { tag_id : self.GetIdealTagId( display_type, tag_service_id, tag_id ) }
            
        
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
        
    
    def GetTagSiblingsForTags( self, service_key, tags ) -> typing.Dict[ str, typing.Set[ str ] ]:
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            tag_service_ids = self.modules_services.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            tag_service_ids = ( self.modules_services.GetServiceId( service_key ), )
            
        
        existing_tags = { tag for tag in tags if self.modules_tags.TagExists( tag ) }
        
        existing_tag_ids = set( self.modules_tags_local_cache.GetTagIdsToTags( tags = existing_tags ).keys() )
        
        tag_ids_to_chain_tag_ids = collections.defaultdict( set )
        
        for tag_service_id in tag_service_ids:
            
            tag_ids_to_ideal_tag_ids = self.GetTagIdsToIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, existing_tag_ids )
            
            ideal_tag_ids = set( tag_ids_to_ideal_tag_ids.values() )
            
            ideal_tag_ids_to_chain_tag_ids = self.GetIdealTagIdsToChains( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id, ideal_tag_ids )
            
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
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tag_service_id )
        
        pair_ids = self._Execute( 'SELECT bad_tag_id, ideal_tag_id FROM {};'.format( cache_tag_siblings_lookup_table_name ) ).fetchall()
        
        all_tag_ids = set( itertools.chain.from_iterable( pair_ids ) )
        
        tag_ids_to_tags = self.modules_tags_local_cache.GetTagIdsToTags( tag_ids = all_tag_ids )
        
        tags_to_ideals = { tag_ids_to_tags[ bad_tag_id ] : tag_ids_to_tags[ good_tag_id ] for ( bad_tag_id, good_tag_id ) in pair_ids }
        
        return tags_to_ideals
        
    
    def GetTagSiblings( self, service_key, tags = None, where_chain_includes_pending_or_petitioned = False ):
        
        service_id = self.modules_services.GetServiceId( service_key )
        
        if tags is None and not where_chain_includes_pending_or_petitioned:
            
            statuses_to_pair_ids = self.GetTagSiblingsIds( service_id )
            
        else:
            
            if where_chain_includes_pending_or_petitioned:
                
                tag_ids = set()
                
                statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
                
                queries = [
                    f'SELECT bad_tag_id, good_tag_id FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ]};',
                    f'SELECT bad_tag_id, good_tag_id FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ]};'
                ]
                
                for query in queries:
                    
                    for pair in self._Execute( query ):
                        
                        tag_ids.update( pair )
                        
                    
                
            else:
                
                tag_ids = set( self.modules_tags_local_cache.GetTagIdsToTags( tags = tags ).keys() )
                
            
            statuses_to_pair_ids = self.GetTagSiblingsIdsChains( service_id, tag_ids )
            
        
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
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        statuses_to_pair_ids = collections.defaultdict( list )
        
        for ( status, table_name ) in statuses_to_storage_table_names.items():
            
            statuses_to_pair_ids[ status ] = sorted( self._Execute( f'SELECT bad_tag_id, good_tag_id FROM {table_name};' ).fetchall() )
            
        
        return statuses_to_pair_ids
        
    
    def GetTagSiblingsIdsChains( self, service_id, tag_ids ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        searched_tag_ids = set()
        next_tag_ids = set( tag_ids )
        
        unsorted_statuses_to_pair_ids = collections.defaultdict( set )
        
        while len( next_tag_ids ) > 0:
            
            loop_tag_ids = set( next_tag_ids )
            next_tag_ids = set()
            
            with self._MakeTemporaryIntegerTable( loop_tag_ids, 'tag_id' ) as temp_next_tag_ids_table_name:
                
                # keep these separate--older sqlite can't do cross join to an OR ON
                # ALSO ditching UNION, which perhaps was not helping!
                
                # just a note, this thing is inefficient--it fetches the same rows twice, looking from either direction
                # there's probably a way to more carefully shape the iterations of search, remembering which direction we got things from or something, but it wouldn't be trivial I think!
                
                for ( status, table_name ) in statuses_to_storage_table_names.items():
                    
                    queries = [
                        f'SELECT bad_tag_id, good_tag_id FROM {temp_next_tag_ids_table_name} CROSS JOIN {table_name} ON ( bad_tag_id = tag_id );',
                        f'SELECT bad_tag_id, good_tag_id FROM {temp_next_tag_ids_table_name} CROSS JOIN {table_name} ON ( good_tag_id = tag_id );'
                    ]
                    
                    for query in queries:
                        
                        for pair in self._Execute( query ):
                            
                            unsorted_statuses_to_pair_ids[ status ].add( pair )
                            
                            next_tag_ids.update( pair )
                            
                        
                    
                
            
            searched_tag_ids.update( loop_tag_ids )
            
            next_tag_ids.difference_update( searched_tag_ids )
            
        
        statuses_to_pair_ids = collections.defaultdict( list )
        
        statuses_to_pair_ids.update( { status : sorted( pair_ids ) for ( status, pair_ids ) in unsorted_statuses_to_pair_ids.items() } )
        
        return statuses_to_pair_ids
        
    
    def IsChained( self, display_type, tag_service_id, tag_id ):
        
        cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( display_type, tag_service_id )
        
        return self._Execute( 'SELECT 1 FROM {} WHERE bad_tag_id = ? OR ideal_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( tag_id, tag_id ) ).fetchone() is not None
        
    
    def NotifySiblingAddRowSynced( self, tag_service_id, row ):
        
        if tag_service_id in self._service_ids_to_display_application_status:
            
            ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove ) = self._service_ids_to_display_application_status[ tag_service_id ]
            
            actual_sibling_rows.add( row )
            sibling_rows_to_add.discard( row )
            
            self._service_ids_to_display_application_status[ tag_service_id ] = ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove )
            
        
    
    def NotifySiblingDeleteRowSynced( self, tag_service_id, row ):
        
        if tag_service_id in self._service_ids_to_display_application_status:
            
            ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove ) = self._service_ids_to_display_application_status[ tag_service_id ]
            
            actual_sibling_rows.discard( row )
            sibling_rows_to_remove.discard( row )
            
            self._service_ids_to_display_application_status[ tag_service_id ] = ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove )
            
        
    
    def PendTagSiblings( self, service_id, triples ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'REPLACE INTO {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ]} ( bad_tag_id, good_tag_id, reason_id ) VALUES ( ?, ?, ? );', triples )
        
    
    def PetitionTagSiblings( self, service_id, triples ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'REPLACE INTO {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ]} ( bad_tag_id, good_tag_id, reason_id ) VALUES ( ?, ?, ? );', triples )
        
    
    def RescindPendingTagSiblings( self, service_id, pairs ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PENDING ]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        
    
    def RescindPetitionedTagSiblings( self, service_id, pairs ):
        
        statuses_to_storage_table_names = GenerateTagSiblingsStorageTableNames( service_id )
        
        self._ExecuteMany( f'DELETE FROM {statuses_to_storage_table_names[ HC.CONTENT_STATUS_PETITIONED ]} WHERE bad_tag_id = ? AND good_tag_id = ?;', pairs )
        
    
    def Regen( self, tag_service_ids ):
        
        for tag_service_id in tag_service_ids:
            
            cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_DISPLAY_IDEAL, tag_service_id )
            
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
        
        if self._service_ids_to_applicable_service_ids is None:
            
            self._GenerateApplicationDicts()
            
        
        # as this guy can change ideals, the related parent chains need to be regenned afterwards too
        
        if len( tag_ids ) == 0:
            
            return
            
        
        for tag_service_id in tag_service_ids:
            
            cache_tag_siblings_lookup_table_name = GenerateTagSiblingsLookupCacheTableName( ClientTags.TAG_DISPLAY_DISPLAY_IDEAL, tag_service_id )
            
            tag_ids_to_clear_and_regen = set( tag_ids )
            
            ideal_tag_ids = self.GetIdealTagIds( ClientTags.TAG_DISPLAY_DISPLAY_IDEAL, tag_service_id, tag_ids )
            
            tag_ids_to_clear_and_regen.update( self.GetChainsMembersFromIdeals( ClientTags.TAG_DISPLAY_DISPLAY_IDEAL, tag_service_id, ideal_tag_ids ) )
            
            if tag_service_id in self._service_ids_to_applicable_service_ids:
                
                with self._MakeTemporaryIntegerTable( tag_ids_to_clear_and_regen, 'tag_id' ) as temp_tag_ids_table_name:
                    
                    stuff_deleted = set( self._Execute( f'SELECT bad_tag_id, ideal_tag_id FROM {temp_tag_ids_table_name} CROSS JOIN {cache_tag_siblings_lookup_table_name} ON ( bad_tag_id = tag_id );' ) )
                    stuff_deleted.update( self._Execute( f'SELECT bad_tag_id, ideal_tag_id FROM {temp_tag_ids_table_name} CROSS JOIN {cache_tag_siblings_lookup_table_name} ON ( ideal_tag_id = tag_id );' ) )
                    
                
            else:
                
                stuff_deleted = set()
                
            
            self._ExecuteMany( 'DELETE FROM {} WHERE bad_tag_id = ? OR ideal_tag_id = ?;'.format( cache_tag_siblings_lookup_table_name ), ( ( tag_id, tag_id ) for tag_id in tag_ids_to_clear_and_regen ) )
            
            applicable_tag_service_ids = self.GetApplicableServiceIds( tag_service_id )
            
            tss = ClientTagsHandling.TagSiblingsStructure()
            
            for applicable_tag_service_id in applicable_tag_service_ids:
                
                statuses_to_pair_ids = self.GetTagSiblingsIdsChains( applicable_tag_service_id, tag_ids_to_clear_and_regen )
                
                petitioned_fast_lookup = set( statuses_to_pair_ids[ HC.CONTENT_STATUS_PETITIONED ] )
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if ( bad_tag_id, good_tag_id ) in petitioned_fast_lookup:
                        
                        continue
                        
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
                for ( bad_tag_id, good_tag_id ) in statuses_to_pair_ids[ HC.CONTENT_STATUS_PENDING ]:
                    
                    tss.AddPair( bad_tag_id, good_tag_id )
                    
                
            
            stuff_added = set( tss.GetBadTagsToIdealTags().items() )
            
            self._ExecuteMany( 'INSERT OR IGNORE INTO {} ( bad_tag_id, ideal_tag_id ) VALUES ( ?, ? );'.format( cache_tag_siblings_lookup_table_name ), stuff_added )
            
            if tag_service_id in self._service_ids_to_display_application_status:
                
                stuff_no_changes = stuff_deleted.intersection( stuff_added )
                stuff_deleted.difference_update( stuff_no_changes )
                stuff_added.difference_update( stuff_no_changes )
                
                ( actual_sibling_rows, ideal_sibling_rows, sibling_rows_to_add, sibling_rows_to_remove ) = self._service_ids_to_display_application_status[ tag_service_id ]
                
                ideal_sibling_rows.difference_update( stuff_deleted )
                sibling_rows_to_add.difference_update( stuff_deleted )
                sibling_rows_to_remove.update( actual_sibling_rows.intersection( stuff_deleted ) )
                
                ideal_sibling_rows.update( stuff_added )
                sibling_rows_to_add.update( stuff_added.difference( actual_sibling_rows ) )
                sibling_rows_to_remove.difference_update( stuff_added )
                
            
        
    
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
        
    
