import ClientData
import ClientDefaults
import ClientImageHandling
import ClientMedia
import ClientRatings
import ClientSearch
import ClientServices
import ClientThreading
import collections
import gc
import hashlib
import itertools
import json
import HydrusConstants as HC
import HydrusData
import HydrusDB
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals
import HydrusImageHandling
import HydrusNetwork
import HydrusPaths
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import ClientConstants as CC
import os
import psutil
import random
import re
import sqlite3
import time
import traceback
import wx

YAML_DUMP_ID_SINGLE = 0
YAML_DUMP_ID_REMOTE_BOORU = 1
YAML_DUMP_ID_FAVOURITE_CUSTOM_FILTER_ACTIONS = 2
YAML_DUMP_ID_GUI_SESSION = 3
YAML_DUMP_ID_IMAGEBOARD = 4
YAML_DUMP_ID_IMPORT_FOLDER = 5
YAML_DUMP_ID_EXPORT_FOLDER = 6
YAML_DUMP_ID_SUBSCRIPTION = 7
YAML_DUMP_ID_LOCAL_BOORU = 8

def ConvertWildcardToSQLiteLikeParameter( wildcard ):
    
    like_param = wildcard.replace( '*', '%' )
    
    return like_param
    
def GenerateCombinedFilesMappingsCacheTableName( service_id ):
    
    return 'external_caches.combined_files_ac_cache_' + str( service_id )
    
def GenerateMappingsTableNames( service_id ):
    
    suffix = str( service_id )
    
    current_mappings_table_name = 'external_mappings.current_mappings_' + suffix
    
    deleted_mappings_table_name = 'external_mappings.deleted_mappings_' + suffix
    
    pending_mappings_table_name = 'external_mappings.pending_mappings_' + suffix
    
    petitioned_mappings_table_name = 'external_mappings.petitioned_mappings_' + suffix
    
    return ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name )
    
def GenerateRepositoryMasterCacheTableNames( service_id ):
    
    suffix = str( service_id )
    
    hash_id_map_table_name = 'external_master.repository_hash_id_map_' + suffix
    tag_id_map_table_name = 'external_master.repository_tag_id_map_' + suffix
    
    return ( hash_id_map_table_name, tag_id_map_table_name )
    
def GenerateRepositoryRepositoryUpdatesTableName( service_id ):
    
    repository_updates_table_name = 'repository_updates_' + str( service_id )
    
    return repository_updates_table_name
    
def GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id ):
    
    suffix = str( file_service_id ) + '_' + str( tag_service_id )
    
    cache_files_table_name = 'external_caches.specific_files_cache_' + suffix
    
    cache_current_mappings_table_name = 'external_caches.specific_current_mappings_cache_' + suffix
    
    cache_pending_mappings_table_name = 'external_caches.specific_pending_mappings_cache_' + suffix
    
    ac_cache_table_name = 'external_caches.specific_ac_cache_' + suffix
    
    return ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name )
    
def report_content_speed_to_job_key( job_key, rows_done, total_rows, precise_timestamp, num_rows, row_name ):
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ConvertIntToPrettyString( num_rows / it_took )
    
    popup_message = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( rows_done, total_rows ) + ': processing ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HydrusGlobals.client_controller.pub( 'splash_set_status_text', popup_message, print_to_log = False )
    job_key.SetVariable( 'popup_text_2', popup_message )
    
def report_speed_to_job_key( job_key, precise_timestamp, num_rows, row_name ):
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ConvertIntToPrettyString( num_rows / it_took )
    
    popup_message = 'processing ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HydrusGlobals.client_controller.pub( 'splash_set_status_text', popup_message, print_to_log = False )
    job_key.SetVariable( 'popup_text_2', popup_message )
    
def report_speed_to_log( precise_timestamp, num_rows, row_name ):
    
    it_took = HydrusData.GetNowPrecise() - precise_timestamp
    
    rows_s = HydrusData.ConvertIntToPrettyString( num_rows / it_took )
    
    summary = 'processed ' + HydrusData.ConvertIntToPrettyString( num_rows ) + ' ' + row_name + ' at ' + rows_s + ' rows/s'
    
    HydrusData.Print( summary )
    
class DB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = [ 'service_info', 'system_predicates', 'missing_thumbnail_hashes' ]
    
    def __init__( self, controller, db_dir, db_name, no_wal = False ):
        
        self._initial_messages = []
        
        HydrusDB.HydrusDB.__init__( self, controller, db_dir, db_name, no_wal = no_wal )
        
    
    def _AddFilesInfo( self, rows, overwrite = False ):
        
        if overwrite:
            
            insert_phrase = 'REPLACE INTO'
            
        else:
            
            insert_phrase = 'INSERT OR IGNORE INTO'
            
        
        # hash_id, size, mime, width, height, duration, num_frames, num_words
        self._c.executemany( insert_phrase + ' files_info VALUES ( ?, ?, ?, ?, ?, ?, ?, ? );', rows )
        
    
    def _AddFiles( self, service_id, rows ):
        
        hash_ids = { row[0] for row in rows }
        
        existing_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) }
        
        valid_hash_ids = hash_ids.difference( existing_hash_ids )
        
        if len( valid_hash_ids ) > 0:
            
            valid_rows = [ ( hash_id, timestamp ) for ( hash_id, timestamp ) in rows if hash_id in valid_hash_ids ]
            
            splayed_valid_hash_ids = HydrusData.SplayListForDB( valid_hash_ids )
            
            # insert the files
            
            self._c.executemany( 'INSERT OR IGNORE INTO current_files VALUES ( ?, ?, ? );', ( ( service_id, hash_id, timestamp ) for ( hash_id, timestamp ) in valid_rows ) )
            
            self._c.execute( 'DELETE FROM file_transfers WHERE service_id = ? AND hash_id IN ' + splayed_valid_hash_ids + ';', ( service_id, ) )
            
            info = self._c.execute( 'SELECT hash_id, size, mime FROM files_info WHERE hash_id IN ' + splayed_valid_hash_ids + ';' ).fetchall()
            
            num_files = len( valid_hash_ids )
            delta_size = sum( ( size for ( hash_id, size, mime ) in info ) )
            num_inbox = len( valid_hash_ids.intersection( self._inbox_hash_ids ) )
            
            service_info_updates = []
            
            service_info_updates.append( ( delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            select_statement = 'SELECT COUNT( * ) FROM files_info WHERE mime IN ' + HydrusData.SplayListForDB( HC.SEARCHABLE_MIMES ) + ' AND hash_id IN %s;'
            
            num_viewable_files = sum( self._STL( self._SelectFromList( select_statement, valid_hash_ids ) ) )
            
            service_info_updates.append( ( num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            
            # now do special stuff
            
            service = self._GetService( service_id )
            
            service_type = service.GetServiceType()
            
            # remove any records of previous deletion
            
            if service_id == self._combined_local_file_service_id or service_type == HC.FILE_REPOSITORY:
                
                self._c.execute( 'DELETE FROM deleted_files WHERE service_id = ? AND hash_id IN ' + splayed_valid_hash_ids + ';', ( service_id, ) )
                
                num_deleted = self._GetRowCount()
                
                service_info_updates.append( ( -num_deleted, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
            
            # if we are adding to a local file domain, remove any from the trash and add to combined local file service if needed
            
            if service_type == HC.LOCAL_FILE_DOMAIN:
                
                self._DeleteFiles( self._trash_service_id, valid_hash_ids )
                
                self._AddFiles( self._combined_local_file_service_id, valid_rows )
                
            
            # if we track tags for this service, update the a/c cache
            
            if service_type in HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES:
                
                tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
                
                for tag_service_id in tag_service_ids:
                    
                    self._CacheSpecificMappingsAddFiles( service_id, tag_service_id, valid_hash_ids )
                    
                
            
            # push the service updates, done
            
            self._c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
        
    
    def _AddHydrusSession( self, service_key, session_key, expires ):
        
        service_id = self._GetServiceId( service_key )
        
        self._c.execute( 'REPLACE INTO hydrus_sessions ( service_id, session_key, expiry ) VALUES ( ?, ?, ? );', ( service_id, sqlite3.Binary( session_key ), expires ) )
        
    
    def _AddService( self, service_key, service_type, name, dictionary ):
        
        result = self._c.execute( 'SELECT 1 FROM services WHERE name = ?;', ( name, ) ).fetchone()
        
        while result is not None:
            
            name += str( random.randint( 0, 9 ) )
            
            result = self._c.execute( 'SELECT 1 FROM services WHERE name = ?;', ( name, ) ).fetchone()
            
        
        dictionary_string = dictionary.DumpToString()
        
        self._c.execute( 'INSERT INTO services ( service_key, service_type, name, dictionary_string ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, name, dictionary_string ) )
        
        service_id = self._c.lastrowid
        
        if service_type in HC.REPOSITORIES:
            
            repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
            
            self._c.execute( 'CREATE TABLE ' + repository_updates_table_name + ' ( update_index INTEGER, hash_id INTEGER, processed INTEGER_BOOLEAN, PRIMARY KEY ( update_index, hash_id ) );' )
            self._CreateIndex( repository_updates_table_name, [ 'hash_id' ] )
            
            ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
            
            self._c.execute( 'CREATE TABLE ' + hash_id_map_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, hash_id INTEGER );' )
            self._c.execute( 'CREATE TABLE ' + tag_id_map_table_name + ' ( service_tag_id INTEGER PRIMARY KEY, tag_id INTEGER );' )
            
        
        if service_type in HC.TAG_SERVICES:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS ' + current_mappings_table_name + ' ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
            self._CreateIndex( current_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS ' + deleted_mappings_table_name + ' ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
            self._CreateIndex( deleted_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS ' + pending_mappings_table_name + ' ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
            self._CreateIndex( pending_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS ' + petitioned_mappings_table_name + ' ( tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
            self._CreateIndex( petitioned_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
            
            #
            
            self._CacheCombinedFilesMappingsGenerate( service_id )
            
            file_service_ids = self._GetServiceIds( HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES )
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsGenerate( file_service_id, service_id )
                
            
        
        if service_type in HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES:
            
            tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self._CacheSpecificMappingsGenerate( service_id, tag_service_id )
                
            
        
    
    def _AddTagParents( self, service_id, pairs, make_content_updates = False ):
        
        self._c.executemany( 'DELETE FROM tag_parents WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ?;', ( ( service_id, child_tag_id, parent_tag_id ) for ( child_tag_id, parent_tag_id ) in pairs ) )
        self._c.executemany( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ? AND status = ?;', ( ( service_id, child_tag_id, parent_tag_id, HC.CONTENT_STATUS_PENDING ) for ( child_tag_id, parent_tag_id ) in pairs )  )
        
        self._c.executemany( 'INSERT OR IGNORE INTO tag_parents ( service_id, child_tag_id, parent_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, child_tag_id, parent_tag_id, HC.CONTENT_STATUS_CURRENT ) for ( child_tag_id, parent_tag_id ) in pairs ) )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        mappings_ids = []
        special_content_updates = []
        
        for ( child_tag_id, parent_tag_id ) in pairs:
            
            child_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( child_tag_id, ) ) }
            parent_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( parent_tag_id, ) ) }
            
            needed_hash_ids = child_hash_ids.difference( parent_hash_ids )
            
            mappings_ids.append( ( parent_tag_id, needed_hash_ids ) )
            
            if make_content_updates:
                
                parent_tag = self._GetTag( parent_tag_id )
                
                needed_hashes = self._GetHashes( needed_hash_ids )
                
                special_content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( parent_tag, needed_hashes ) )
                
                special_content_updates.append( special_content_update )
                
            
        
        self._UpdateMappings( service_id, mappings_ids = mappings_ids )
        
        return special_content_updates
        
    
    def _AddTagSiblings( self, service_id, pairs ):
        
        self._c.executemany( 'DELETE FROM tag_siblings WHERE service_id = ? AND bad_tag_id = ?;', ( ( service_id, bad_tag_id ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        self._c.executemany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, HC.CONTENT_STATUS_PENDING ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
        self._c.executemany( 'INSERT OR IGNORE INTO tag_siblings ( service_id, bad_tag_id, good_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_CURRENT ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def _AddWebSession( self, name, cookies, expires ):
        
        self._c.execute( 'REPLACE INTO web_sessions ( name, cookies, expiry ) VALUES ( ?, ?, ? );', ( name, cookies, expires ) )
        
    
    def _AnalyzeStaleBigTables( self, stop_time = None, only_when_idle = False, force_reanalyze = False ):
        
        names_to_analyze = self._GetBigTableNamesToAnalyze( force_reanalyze = force_reanalyze )
        
        if len( names_to_analyze ) > 0:
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_title', 'database maintenance - analyzing' )
            
            self._controller.pub( 'message', job_key )
            
            random.shuffle( names_to_analyze )
            
            for name in names_to_analyze:
                
                self._controller.pub( 'splash_set_status_text', 'analyzing ' + name )
                job_key.SetVariable( 'popup_text_1', 'analyzing ' + name )
                
                started = HydrusData.GetNowPrecise()
                
                self._AnalyzeTable( name )
                
                time_took = HydrusData.GetNowPrecise() - started
                
                if time_took > 1:
                    
                    HydrusData.Print( 'Analyzed ' + name + ' in ' + HydrusData.ConvertTimeDeltaToPrettyString( time_took ) )
                    
                
                p1 = stop_time is not None and HydrusData.TimeHasPassed( stop_time )
                p2 = only_when_idle and not self._controller.CurrentlyIdle()
                
                if p1 or p2:
                    
                    break
                    
                
            
            self._c.execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            
            HydrusData.Print( job_key.ToString() )
            
            job_key.Delete( 30 )
            
        
    
    def _AnalyzeTable( self, name ):
        
        self._c.execute( 'ANALYZE ' + name + ';' )
        
        ( num_rows, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + name + ';' ).fetchone()
        
        self._c.execute( 'DELETE FROM analyze_timestamps WHERE name = ?;', ( name, ) )
        
        self._c.execute( 'INSERT OR IGNORE INTO analyze_timestamps ( name, num_rows, timestamp ) VALUES ( ?, ?, ? );', ( name, num_rows, HydrusData.GetNow() ) )
        
    
    def _ArchiveFiles( self, hash_ids ):
        
        valid_hash_ids = [ hash_id for hash_id in hash_ids if hash_id in self._inbox_hash_ids ]
        
        if len( valid_hash_ids ) > 0:
            
            splayed_hash_ids = HydrusData.SplayListForDB( valid_hash_ids )
            
            self._c.execute( 'DELETE FROM file_inbox WHERE hash_id IN ' + splayed_hash_ids + ';' )
            
            updates = self._c.execute( 'SELECT service_id, COUNT( * ) FROM current_files WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            self._c.executemany( 'UPDATE service_info SET info = info - ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
            self._inbox_hash_ids.difference_update( valid_hash_ids )
            
        
    
    def _AssociateRepositoryUpdateHashes( self, service_key, metadata_slice ):
        
        service_id = self._GetServiceId( service_key )
        
        processed = False
        
        inserts = []
        
        for ( update_index, update_hashes ) in metadata_slice.IterateUpdateIndicesAndHashes():
            
            for update_hash in update_hashes:
                
                hash_id = self._GetHashId( update_hash )
                
                inserts.append( ( update_index, hash_id, processed ) )
                
            
        
        repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + repository_updates_table_name + ' ( update_index, hash_id, processed ) VALUES ( ?, ?, ? );', inserts )
        
    
    def _Backup( self, path ):
        
        client_files_locations = self._GetClientFilesLocations()
        
        client_files_default = os.path.join( self._db_dir, 'client_files' )
        
        for location in client_files_locations.values():
            
            if not location.startswith( client_files_default ):
                
                HydrusData.ShowText( 'Some of your files are stored outside of ' + client_files_default + '. These files will not be backed up--please do this manually, yourself.' )
                
                break
                
            
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'backing up db' )
        
        self._controller.pub( 'message', job_key )
        
        job_key.SetVariable( 'popup_text_1', 'closing db' )
        
        self._Commit()
        
        self._CloseDBCursor()
        
        try:
            
            HydrusPaths.MakeSureDirectoryExists( path )
            
            for filename in self._db_filenames.values():
                
                job_key.SetVariable( 'popup_text_1', 'copying ' + filename )
                
                source = os.path.join( self._db_dir, filename )
                dest = os.path.join( path, filename )
                
                HydrusPaths.MirrorFile( source, dest )
                
            
            job_key.SetVariable( 'popup_text_1', 'copying files directory' )
            
            if os.path.exists( client_files_default ):
                
                HydrusPaths.MirrorTree( client_files_default, os.path.join( path, 'client_files' ) )
                
            
        finally:
            
            self._InitDBCursor()
            
            self._BeginImmediate()
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        
        job_key.Finish()
        
    
    def _CacheCombinedFilesMappingsDrop( self, service_id ):
        
        ac_cache_table_name = GenerateCombinedFilesMappingsCacheTableName( service_id )
        
        self._c.execute( 'DROP TABLE IF EXISTS ' + ac_cache_table_name + ';' )
        
    
    def _CacheCombinedFilesMappingsGenerate( self, service_id ):
        
        ac_cache_table_name = GenerateCombinedFilesMappingsCacheTableName( service_id )
        
        self._c.execute( 'CREATE TABLE ' + ac_cache_table_name + ' ( tag_id INTEGER PRIMARY KEY, current_count INTEGER, pending_count INTEGER );' )
        
        #
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        current_mappings_exist = self._c.execute( 'SELECT 1 FROM ' + current_mappings_table_name + ' LIMIT 1;' ).fetchone() is not None
        pending_mappings_exist = self._c.execute( 'SELECT 1 FROM ' + pending_mappings_table_name + ' LIMIT 1;' ).fetchone() is not None
        
        if current_mappings_exist or pending_mappings_exist:
            
            all_known_ids = [ tag_id for ( tag_id, ) in self._c.execute( 'SELECT tag_id FROM tags;' ) ]
            
            for group_of_ids in HydrusData.SplitListIntoChunks( all_known_ids, 10000 ):
                
                current_counter = collections.Counter()
                
                if current_mappings_exist:
                    
                    select_statement = 'SELECT tag_id, COUNT( * ) FROM ' + current_mappings_table_name + ' WHERE tag_id IN %s GROUP BY tag_id;'
                    
                    for ( tag_id, count ) in self._SelectFromList( select_statement, group_of_ids ):
                        
                        if count > 0:
                            
                            current_counter[ tag_id ] = count
                            
                        
                    
                
                #
                
                pending_counter = collections.Counter()
                
                if pending_mappings_exist:
                    
                    select_statement = 'SELECT tag_id, COUNT( * ) FROM ' + pending_mappings_table_name + ' WHERE tag_id IN %s GROUP BY tag_id;'
                    
                    for ( tag_id, count ) in self._SelectFromList( select_statement, group_of_ids ):
                        
                        if count > 0:
                            
                            pending_counter[ tag_id ] = count
                            
                        
                    
                
                all_ids_seen = set( current_counter.keys() )
                all_ids_seen.update( pending_counter.keys() )
                
                count_ids = [ ( tag_id, current_counter[ tag_id ], pending_counter[ tag_id ] ) for tag_id in all_ids_seen ]
                
                if len( count_ids ) > 0:
                    
                    self._CacheCombinedFilesMappingsUpdate( service_id, count_ids )
                    
                
            
        
    
    def _CacheCombinedFilesMappingsGetAutocompleteCounts( self, service_id, tag_ids ):
        
        ac_cache_table_name = GenerateCombinedFilesMappingsCacheTableName( service_id )
        
        select_statement = 'SELECT tag_id, current_count, pending_count FROM ' + ac_cache_table_name + ' WHERE tag_id IN %s;'
        
        return self._SelectFromListFetchAll( select_statement, tag_ids )
        
    
    def _CacheCombinedFilesMappingsUpdate( self, service_id, count_ids ):
        
        ac_cache_table_name = GenerateCombinedFilesMappingsCacheTableName( service_id )
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + ac_cache_table_name + ' ( tag_id, current_count, pending_count ) VALUES ( ?, ?, ? );', ( ( tag_id, 0, 0 ) for ( tag_id, current_delta, pending_delta ) in count_ids ) )
        
        self._c.executemany( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count + ?, pending_count = pending_count + ? WHERE tag_id = ?;', ( ( current_delta, pending_delta, tag_id ) for ( tag_id, current_delta, pending_delta ) in count_ids ) )
        
        self._c.executemany( 'DELETE FROM ' + ac_cache_table_name + ' WHERE tag_id = ? AND current_count = ? AND pending_count = ?;', ( ( tag_id, 0, 0 ) for ( tag_id, current_delta, pending_delta ) in count_ids ) )
        
    
    def _CacheRepositoryAddHashes( self, service_id, service_hash_ids_to_hashes ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        inserts = []
        
        for ( service_hash_id, hash ) in service_hash_ids_to_hashes.items():
            
            hash_id = self._GetHashId( hash )
            
            inserts.append( ( service_hash_id, hash_id ) )
            
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + hash_id_map_table_name + ' ( service_hash_id, hash_id ) VALUES ( ?, ? );', inserts )
        
    
    def _CacheRepositoryAddTags( self, service_id, service_tag_ids_to_tags ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        inserts = []
        
        for ( service_tag_id, tag ) in service_tag_ids_to_tags.items():
            
            tag_id = self._GetTagId( tag )
            
            inserts.append( ( service_tag_id, tag_id ) )
            
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + tag_id_map_table_name + ' ( service_tag_id, tag_id ) VALUES ( ?, ? );', inserts )
        
    
    def _CacheRepositoryNormaliseServiceHashId( self, service_id, service_hash_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        result = self._c.execute( 'SELECT hash_id FROM ' + hash_id_map_table_name + ' WHERE service_hash_id = ?;', ( service_hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service file hash map error in database' )
            
        
        ( hash_id, ) = result
        
        return hash_id
        
    
    def _CacheRepositoryNormaliseServiceHashIds( self, service_id, service_hash_ids ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        select_statement = 'SELECT hash_id FROM ' + hash_id_map_table_name + ' WHERE service_hash_id IN %s;'
        
        hash_ids = [ hash_id for ( hash_id, ) in self._SelectFromList( select_statement, service_hash_ids ) ]
        
        if len( hash_ids ) != len( service_hash_ids ):
            
            raise HydrusExceptions.DataMissing( 'Service file hash map error in database' )
            
        
        return hash_ids
        
    
    def _CacheRepositoryNormaliseServiceTagId( self, service_id, service_tag_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        result = self._c.execute( 'SELECT tag_id FROM ' + tag_id_map_table_name + ' WHERE service_tag_id = ?;', ( service_tag_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service tag map error in database' )
            
        
        ( tag_id, ) = result
        
        return tag_id
        
    
    def _CacheRepositoryDrop( self, service_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        self._c.execute( 'DROP ' + hash_id_map_table_name )
        self._c.execute( 'DROP ' + tag_id_map_table_name )
        
    
    def _CacheRepositoryGenerate( self, service_id ):
        
        ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE ' + hash_id_map_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, hash_id INTEGER );' )
        self._c.execute( 'CREATE TABLE ' + tag_id_map_table_name + ' ( service_tag_id INTEGER PRIMARY KEY, tag_id INTEGER );' )
        
    
    def _CacheSimilarFilesAddLeaf( self, phash_id, phash ):
        
        result = self._c.execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
        
        if result is None:
            
            parent_id = None
            
        else:
            
            ( root_node_phash_id, ) = result
            
            ancestors_we_are_inside = []
            ancestors_we_are_outside = []
            
            an_ancestor_is_unbalanced = False
            
            next_ancestor_id = root_node_phash_id
            
            while next_ancestor_id is not None:
                
                ancestor_id = next_ancestor_id
                
                ( ancestor_phash, ancestor_radius, ancestor_inner_id, ancestor_inner_population, ancestor_outer_id, ancestor_outer_population ) = self._c.execute( 'SELECT phash, radius, inner_id, inner_population, outer_id, outer_population FROM shape_perceptual_hashes NATURAL JOIN shape_vptree WHERE phash_id = ?;', ( ancestor_id, ) ).fetchone()
                
                distance_to_ancestor = HydrusData.Get64BitHammingDistance( phash, ancestor_phash )
                
                if ancestor_radius is None or distance_to_ancestor <= ancestor_radius:
                    
                    ancestors_we_are_inside.append( ancestor_id )
                    ancestor_inner_population += 1
                    next_ancestor_id = ancestor_inner_id
                    
                    if ancestor_inner_id is None:
                        
                        self._c.execute( 'UPDATE shape_vptree SET inner_id = ?, radius = ? WHERE phash_id = ?;', ( phash_id, distance_to_ancestor, ancestor_id ) )
                        
                        parent_id = ancestor_id
                        
                    
                else:
                    
                    ancestors_we_are_outside.append( ancestor_id )
                    ancestor_outer_population += 1
                    next_ancestor_id = ancestor_outer_id
                    
                    if ancestor_outer_id is None:
                        
                        self._c.execute( 'UPDATE shape_vptree SET outer_id = ? WHERE phash_id = ?;', ( phash_id, ancestor_id ) )
                        
                        parent_id = ancestor_id
                        
                    
                
                if not an_ancestor_is_unbalanced and ancestor_inner_population + ancestor_outer_population > 16:
                    
                    larger = float( max( ancestor_inner_population, ancestor_outer_population ) )
                    smaller = float( min( ancestor_inner_population, ancestor_outer_population ) )
                    
                    if smaller / larger < 0.5:
                        
                        self._c.execute( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ancestor_id, ) )
                        
                        # we only do this for the eldest ancestor, as the eventual rebalancing will affect all children
                        
                        an_ancestor_is_unbalanced = True
                        
                    
                
            
            self._c.executemany( 'UPDATE shape_vptree SET inner_population = inner_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_inside ) )
            self._c.executemany( 'UPDATE shape_vptree SET outer_population = outer_population + 1 WHERE phash_id = ?;', ( ( ancestor_id, ) for ancestor_id in ancestors_we_are_outside ) )
            
        
        radius = None
        inner_id = None
        inner_population = 0
        outer_id = None
        outer_population = 0
        
        self._c.execute( 'INSERT INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
        
    
    def _CacheSimilarFilesAssociatePHashes( self, hash_id, phashes ):
        
        phash_ids = set()
        
        for phash in phashes:
            
            phash_id = self._CacheSimilarFilesGetPHashId( phash )
            
            phash_ids.add( phash_id )
            
        
        self._c.executemany( 'INSERT OR IGNORE INTO shape_perceptual_hash_map ( phash_id, hash_id ) VALUES ( ?, ? );', ( ( phash_id, hash_id ) for phash_id in phash_ids ) )
        
        if self._GetRowCount() > 0:
            
            self._c.execute( 'REPLACE INTO shape_search_cache ( hash_id, searched_distance ) VALUES ( ?, ? );', ( hash_id, None ) )
            
        
        return phash_ids
        
    
    def _CacheSimilarFilesDeleteFile( self, hash_id ):
        
        phash_ids = { phash_id for ( phash_id, ) in self._c.execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) }
        
        self._CacheSimilarFilesDisassociatePHashes( hash_id, phash_ids )
        
        self._c.execute( 'DELETE FROM shape_search_cache WHERE hash_id = ?;', ( hash_id, ) )
        self._c.execute( 'DELETE FROM duplicate_pairs WHERE smaller_hash_id = ? or larger_hash_id = ?;', ( hash_id, hash_id ) )
        self._c.execute( 'DELETE FROM shape_maintenance_phash_regen WHERE hash_id = ?;', ( hash_id, ) )
        
    
    def _CacheSimilarFilesDeleteUnknownDuplicatePairs( self ):
        
        hash_ids = set()
        
        for ( smaller_hash_id, larger_hash_id ) in self._c.execute( 'SELECT smaller_hash_id, larger_hash_id FROM duplicate_pairs WHERE duplicate_type = ?;', ( HC.DUPLICATE_UNKNOWN, ) ):
            
            hash_ids.add( smaller_hash_id )
            hash_ids.add( larger_hash_id )
            
        
        self._c.execute( 'DELETE FROM duplicate_pairs WHERE duplicate_type = ?;', ( HC.DUPLICATE_UNKNOWN, ) )
        
        self._c.executemany( 'UPDATE shape_search_cache SET searched_distance = NULL WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def _CacheSimilarFilesDisassociatePHashes( self, hash_id, phash_ids ):
        
        self._c.executemany( 'DELETE FROM shape_perceptual_hash_map WHERE phash_id = ? AND hash_id = ?;', ( ( phash_id, hash_id ) for phash_id in phash_ids ) )
        
        useful_phash_ids = { phash for ( phash, ) in self._c.execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE phash_id IN ' + HydrusData.SplayListForDB( phash_ids ) + ';' ) }
        
        useless_phash_ids = phash_ids.difference( useful_phash_ids )
        
        self._c.executemany( 'INSERT OR IGNORE INTO shape_maintenance_branch_regen ( phash_id ) VALUES ( ? );', ( ( phash_id, ) for phash_id in useless_phash_ids ) )
        
    
    def _CacheSimilarFilesGenerateBranch( self, job_key, parent_id, phash_id, phash, children ):
        
        process_queue = [ ( parent_id, phash_id, phash, children ) ]
        
        insert_rows = []
        
        num_done = 0
        num_to_do = len( children ) + 1
        
        while len( process_queue ) > 0:
            
            job_key.SetVariable( 'popup_text_2', 'generating new branch -- ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
            
            ( parent_id, phash_id, phash, children ) = process_queue.pop( 0 )
            
            if len( children ) == 0:
                
                inner_id = None
                inner_population = 0
                
                outer_id = None
                outer_population = 0
                
                radius = None
                
            else:
                
                children = [ ( HydrusData.Get64BitHammingDistance( phash, child_phash ), child_id, child_phash ) for ( child_id, child_phash ) in children ]
                
                children.sort()
                
                median_index = len( children ) / 2
                
                median_radius = children[ median_index ][0]
                
                inner_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance < median_radius ]
                radius_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance == median_radius ]
                outer_children = [ ( child_id, child_phash ) for ( distance, child_id, child_phash ) in children if distance > median_radius ]
                
                if len( inner_children ) <= len( outer_children ):
                    
                    radius = median_radius
                    
                    inner_children.extend( radius_children )
                    
                else:
                    
                    radius = median_radius - 1
                    
                    outer_children.extend( radius_children )
                    
                
                inner_population = len( inner_children )
                outer_population = len( outer_children )
                
                ( inner_id, inner_phash ) = self._CacheSimilarFilesPopBestRootNode( inner_children ) #HydrusData.MedianPop( inner_children )
                
                if len( outer_children ) == 0:
                    
                    outer_id = None
                    
                else:
                    
                    ( outer_id, outer_phash ) = self._CacheSimilarFilesPopBestRootNode( outer_children ) #HydrusData.MedianPop( outer_children )
                    
                
            
            insert_rows.append( ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) )
            
            if inner_id is not None:
                
                process_queue.append( ( phash_id, inner_id, inner_phash, inner_children ) )
                
            
            if outer_id is not None:
                
                process_queue.append( ( phash_id, outer_id, outer_phash, outer_children ) )
                
            
            num_done += 1
            
        
        job_key.SetVariable( 'popup_text_2', 'branch constructed, now committing' )
        
        self._c.executemany( 'INSERT INTO shape_vptree ( phash_id, parent_id, radius, inner_id, inner_population, outer_id, outer_population ) VALUES ( ?, ?, ?, ?, ?, ?, ? );', insert_rows )
        
    
    def _CacheSimilarFilesGetDuplicatePair( self, service_key, duplicate_type ):
        
        ( table_join, predicate_string ) = self._CacheSimilarFilesGetDuplicatePairsTableJoinInfo( service_key )
        
        result = self._c.execute( 'SELECT smaller_hash_id, larger_hash_id FROM ' + table_join + ' WHERE ' + predicate_string + ' AND duplicate_type = ? ORDER BY RANDOM() LIMIT 1;', ( HC.DUPLICATE_UNKNOWN, ) ).fetchone()
        
        if result is None:
            
            return None
            
        else:
            
            ( smaller_hash_id, larger_hash_id ) = result
            
            media_results = self._GetMediaResults( ( smaller_hash_id, larger_hash_id ) )
            
            return media_results
            
        
    
    def _CacheSimilarFilesGetDuplicatePairsTableJoinInfo( self, file_service_key ):
        
        service_id = self._GetServiceId( file_service_key )
        
        table_join = 'duplicate_pairs, current_files AS current_files_smaller, current_files AS current_files_larger ON ( smaller_hash_id = current_files_smaller.hash_id AND larger_hash_id = current_files_larger.hash_id )'
        predicate_string = 'current_files_smaller.service_id = ' + str( service_id ) + ' AND current_files_larger.service_id = ' + str( service_id )
        
        return ( table_join, predicate_string )
        
    
    def _CacheSimilarFilesGetPHashId( self, phash ):
        
        result = self._c.execute( 'SELECT phash_id FROM shape_perceptual_hashes WHERE phash = ?;', ( sqlite3.Binary( phash ), ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO shape_perceptual_hashes ( phash ) VALUES ( ? );', ( sqlite3.Binary( phash ), ) )
            
            phash_id = self._c.lastrowid
            
            self._CacheSimilarFilesAddLeaf( phash_id, phash )
            
        else:
            
            ( phash_id, ) = result
            
        
        return phash_id
        
    
    def _CacheSimilarFilesGetMaintenanceStatus( self, file_service_key ):
        
        ( num_phashes_to_regen, ) = self._c.execute( 'SELECT COUNT( * ) FROM shape_maintenance_phash_regen;' ).fetchone()
        ( num_branches_to_regen, ) = self._c.execute( 'SELECT COUNT( * ) FROM shape_maintenance_branch_regen;' ).fetchone()
        
        searched_distances_to_count = collections.Counter( dict( self._c.execute( 'SELECT searched_distance, COUNT( * ) FROM shape_search_cache GROUP BY searched_distance;' ) ) )
        
        ( table_join, predicate_string ) = self._CacheSimilarFilesGetDuplicatePairsTableJoinInfo( file_service_key )
        
        duplicate_types_to_count = collections.Counter( dict( self._c.execute( 'SELECT duplicate_type, COUNT( * ) FROM ' + table_join + ' WHERE ' + predicate_string + ' GROUP BY duplicate_type;' ) ) )
        
        return ( num_phashes_to_regen, num_branches_to_regen, searched_distances_to_count, duplicate_types_to_count )
        
    
    def _CacheSimilarFilesGetSomeDupes( self, file_service_key ):
        
        ( table_join, predicate_string ) = self._CacheSimilarFilesGetDuplicatePairsTableJoinInfo( file_service_key )
        
        result = self._c.execute( 'SELECT smaller_hash_id, larger_hash_id FROM ' + table_join + ' WHERE ' + predicate_string + ' AND duplicate_type = ? ORDER BY RANDOM() LIMIT 1;', ( HC.DUPLICATE_UNKNOWN, ) ).fetchone()
        
        if result is None:
            
            return set()
            
        
        ( random_hash_id, ) = random.sample( result, 1 ) # either the smaller or larger
        
        dupe_hash_ids = set()
        
        for ( smaller_hash_id, larger_hash_id ) in self._c.execute( 'SELECT smaller_hash_id, larger_hash_id FROM ' + table_join + ' WHERE ' + predicate_string + ' AND duplicate_type = ? AND ( smaller_hash_id = ? OR larger_hash_id = ? );', ( HC.DUPLICATE_UNKNOWN, random_hash_id, random_hash_id ) ):
            
            dupe_hash_ids.add( smaller_hash_id )
            dupe_hash_ids.add( larger_hash_id )
            
        
        dupe_hashes = self._GetHashes( dupe_hash_ids )
        
        return dupe_hashes
        
    
    def _CacheSimilarFilesMaintainDuplicatePairs( self, search_distance, job_key = None, stop_time = None, abandon_if_other_work_to_do = False ):
        
        if abandon_if_other_work_to_do:
            
            result = self._c.execute( 'SELECT 1 FROM shape_maintenance_phash_regen;' ).fetchone()
            
            if result is not None:
                
                return
                
            
            result = self._c.execute( 'SELECT 1 FROM shape_maintenance_branch_regen;' ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        pub_job_key = False
        job_key_pubbed = False
        
        if job_key is None:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            pub_job_key = True
            
        
        try:
            
            ( total_num_hash_ids_in_cache, ) = self._c.execute( 'SELECT COUNT( * ) FROM shape_search_cache;' ).fetchone()
            
            hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ?;', ( search_distance, ) ) ]
            
            pairs_found = 0
            
            total_done_previously = total_num_hash_ids_in_cache - len( hash_ids )
            
            for ( i, hash_id ) in enumerate( hash_ids ):
                
                job_key.SetVariable( 'popup_title', 'similar files duplicate pair discovery' )
                
                if pub_job_key and not job_key_pubbed:
                    
                    self._controller.pub( 'message', job_key )
                    
                    job_key_pubbed = True
                    
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                should_stop = stop_time is not None and HydrusData.TimeHasPassed( stop_time )
                
                if should_quit or should_stop:
                    
                    return
                    
                
                text = 'searched ' + HydrusData.ConvertValueRangeToPrettyString( total_done_previously + i, total_num_hash_ids_in_cache ) + ' files, found ' + HydrusData.ConvertIntToPrettyString( pairs_found ) + ' potential duplicate pairs'
                
                job_key.SetVariable( 'popup_text_1', text )
                job_key.SetVariable( 'popup_gauge_1', ( total_done_previously + i, total_num_hash_ids_in_cache ) )
                
                if i % 100 == 0:
                    
                    HydrusGlobals.client_controller.pub( 'splash_set_status_text', text )
                    
                
                duplicate_hash_ids = [ duplicate_hash_id for duplicate_hash_id in self._CacheSimilarFilesSearch( hash_id, search_distance ) if duplicate_hash_id != hash_id ]
                
                # double-check the files exist in shape_search_cache, as I think stale branches are producing deleted file pairs here
                
                self._c.executemany( 'INSERT OR IGNORE INTO duplicate_pairs ( smaller_hash_id, larger_hash_id, duplicate_type ) VALUES ( ?, ?, ? );', ( ( min( hash_id, duplicate_hash_id ), max( hash_id, duplicate_hash_id ), HC.DUPLICATE_UNKNOWN ) for duplicate_hash_id in duplicate_hash_ids ) )
                
                pairs_found += self._GetRowCount()
                
                self._c.execute( 'UPDATE shape_search_cache SET searched_distance = ? WHERE hash_id = ?;', ( search_distance, hash_id ) )
                
            
        finally:
            
            job_key.SetVariable( 'popup_text_1', 'done!' )
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            job_key.Finish()
            job_key.Delete( 30 )
            
        
    
    def _CacheSimilarFilesMaintainFiles( self, job_key = None, stop_time = None ):
        
        pub_job_key = False
        job_key_pubbed = False
        
        if job_key is None:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            pub_job_key = True
            
        
        ( total_num_hash_ids_in_cache, ) = self._c.execute( 'SELECT COUNT( * ) FROM shape_search_cache;' ).fetchone()
        
        hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM shape_maintenance_phash_regen;' ) ]
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        total_done_previously = total_num_hash_ids_in_cache - len( hash_ids )
        
        for ( i, hash_id ) in enumerate( hash_ids ):
            
            job_key.SetVariable( 'popup_title', 'similar files metadata maintenance' )
            
            if pub_job_key and not job_key_pubbed:
                
                self._controller.pub( 'message', job_key )
                
                job_key_pubbed = True
                
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            should_stop = stop_time is not None and HydrusData.TimeHasPassed( stop_time )
            
            if should_quit or should_stop:
                
                return
                
            
            if i % 50 == 0:
                
                gc.collect()
                
            
            text = 'regenerating similar file metadata - ' + HydrusData.ConvertValueRangeToPrettyString( total_done_previously + i, total_num_hash_ids_in_cache )
            
            HydrusGlobals.client_controller.pub( 'splash_set_status_text', text )
            job_key.SetVariable( 'popup_text_1', text )
            job_key.SetVariable( 'popup_gauge_1', ( total_done_previously + i, total_num_hash_ids_in_cache ) )
            
            try:
                
                hash = self._GetHash( hash_id )
                mime = self._GetMime( hash_id )
                
                if mime in HC.MIMES_WE_CAN_PHASH:
                    
                    path = client_files_manager.GetFilePath( hash, mime )
                    
                    if mime in ( HC.IMAGE_JPEG, HC.IMAGE_PNG ):
                        
                        try:
                            
                            phashes = ClientImageHandling.GenerateShapePerceptualHashes( path )
                            
                        except Exception as e:
                            
                            HydrusData.Print( 'Could not generate phashes for ' + path )
                            
                            HydrusData.PrintException( e )
                            
                            phashes = []
                            
                        
                    
                else:
                    
                    phashes = []
                    
                
            except HydrusExceptions.FileMissingException:
                
                phashes = []
                
            
            existing_phash_ids = { phash_id for ( phash_id, ) in self._c.execute( 'SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) }
            
            correct_phash_ids = self._CacheSimilarFilesAssociatePHashes( hash_id, phashes )
            
            incorrect_phash_ids = existing_phash_ids.difference( correct_phash_ids )
            
            if len( incorrect_phash_ids ) > 0:
                
                self._CacheSimilarFilesDisassociatePHashes( hash_id, incorrect_phash_ids )
                
            
            self._c.execute( 'DELETE FROM shape_maintenance_phash_regen WHERE hash_id = ?;', ( hash_id, ) )
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        job_key.DeleteVariable( 'popup_gauge_1' )
        
        job_key.Finish()
        job_key.Delete( 30 )
        
    
    def _CacheSimilarFilesMaintainTree( self, job_key = None, stop_time = None, abandon_if_other_work_to_do = False ):
        
        if abandon_if_other_work_to_do:
            
            result = self._c.execute( 'SELECT 1 FROM shape_maintenance_phash_regen;' ).fetchone()
            
            if result is not None:
                
                return
                
            
        
        pub_job_key = False
        job_key_pubbed = False
        
        if job_key is None:
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            pub_job_key = True
            
        
        job_key.SetVariable( 'popup_title', 'similar files metadata maintenance' )
        
        rebalance_phash_ids = [ phash_id for ( phash_id, ) in self._c.execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) ]
        
        num_to_do = len( rebalance_phash_ids )
        
        while len( rebalance_phash_ids ) > 0:
            
            if pub_job_key and not job_key_pubbed:
                
                self._controller.pub( 'message', job_key )
                
                job_key_pubbed = True
                
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            should_stop = stop_time is not None and HydrusData.TimeHasPassed( stop_time )
            
            if should_quit or should_stop:
                
                return
                
            
            num_done = num_to_do - len( rebalance_phash_ids )
            
            text = 'rebalancing similar file metadata - ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do )
            
            HydrusGlobals.client_controller.pub( 'splash_set_status_text', text )
            job_key.SetVariable( 'popup_text_1', text )
            job_key.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
            
            with HydrusDB.TemporaryIntegerTable( self._c, rebalance_phash_ids, 'phash_id' ) as temp_table_name:
                
                ( biggest_phash_id, ) = self._c.execute( 'SELECT phash_id FROM shape_vptree NATURAL JOIN ' + temp_table_name + ' ORDER BY inner_population + outer_population DESC;' ).fetchone()
                
            
            self._CacheSimilarFilesRegenerateBranch( job_key, biggest_phash_id )
            
            rebalance_phash_ids = [ phash_id for ( phash_id, ) in self._c.execute( 'SELECT phash_id FROM shape_maintenance_branch_regen;' ) ]
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.DeleteVariable( 'popup_text_2' ) # used in the regenbranch call
        
        job_key.Finish()
        job_key.Delete( 30 )
        
    
    def _CacheSimilarFilesMaintenanceDue( self ):
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        if new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ):
            
            result = self._c.execute( 'SELECT 1 FROM shape_maintenance_phash_regen;' ).fetchone()
            
            if result is not None:
                
                return True
                
            
            result = self._c.execute( 'SELECT 1 FROM shape_maintenance_branch_regen;' ).fetchone()
            
            if result is not None:
                
                return True
                
            
            search_distance = HydrusGlobals.client_controller.GetNewOptions().GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            result = self._c.execute( 'SELECT 1 FROM shape_search_cache WHERE searched_distance IS NULL or searched_distance < ?;', ( search_distance, ) ).fetchone()
            
            if result is not None:
                
                return True
                
            
        
        return False
        
    
    def _CacheSimilarFilesPopBestRootNode( self, node_rows ):
        
        if len( node_rows ) == 1:
            
            root_row = node_rows.pop(0)
            
            return root_row
            
        
        MAX_VIEWPOINTS = 256
        MAX_SAMPLE = 64
        
        if len( node_rows ) > MAX_VIEWPOINTS:
            
            viewpoints = random.sample( node_rows, MAX_VIEWPOINTS )
            
        else:
            
            viewpoints = node_rows
            
        
        if len( node_rows ) > MAX_SAMPLE:
            
            sample = random.sample( node_rows, MAX_SAMPLE )
            
        else:
            
            sample = node_rows
            
        
        final_scores = []
        
        for ( v_id, v_phash ) in viewpoints:
            
            views = [ HydrusData.Get64BitHammingDistance( v_phash, s_phash ) for ( s_id, s_phash ) in sample if v_id != s_id ]
            
            views.sort()
            
            # let's figure out the ratio of left_children to right_children, preferring 1:1, and convert it to a discrete integer score
            
            median_index = len( views ) / 2
            
            radius = views[ median_index ]
            
            num_left = float( len( [ 1 for view in views if view < radius ] ) )
            num_radius = float( len( [ 1 for view in views if view == radius ] ) )
            num_right = float( len( [ 1 for view in views if view > radius ] ) )
            
            if num_left <= num_right:
                
                num_left += num_radius
                
            else:
                
                num_right += num_radius
                
            
            smaller = min( num_left, num_right )
            larger = max( num_left, num_right )
            
            ratio = smaller / larger
            
            ratio_score = int( ratio * MAX_SAMPLE / 2 )
            
            # now let's calc the standard deviation--larger sd tends to mean less sphere overlap when searching
            
            mean_view = sum( views ) / float( len( views ) )
            squared_diffs = [ ( view - mean_view  ) ** 2 for view in views ]
            sd = ( sum( squared_diffs ) / len( squared_diffs ) ) ** 0.5
            
            final_scores.append( ( ratio_score, sd, v_id ) )
            
        
        final_scores.sort()
        
        # we now have a list like [ ( 11, 4.0, [id] ), ( 15, 3.7, [id] ), ( 15, 4.3, [id] ) ]
        
        ( ratio_gumpf, sd_gumpf, root_id ) = final_scores.pop()
        
        for ( i, ( v_id, v_phash ) ) in enumerate( node_rows ):
            
            if v_id == root_id:
                
                root_row = node_rows.pop( i )
                
                return root_row
                
            
        
    
    def _CacheSimilarFilesRegenerateBranch( self, job_key, phash_id ):
        
        job_key.SetVariable( 'popup_text_2', 'reviewing existing branch' )
        
        # grab everything in the branch
        
        ( parent_id, ) = self._c.execute( 'SELECT parent_id FROM shape_vptree WHERE phash_id = ?;', ( phash_id, ) ).fetchone()
        
        cte_table_name = 'branch ( branch_phash_id )'
        initial_select = 'SELECT ?'
        recursive_select = 'SELECT phash_id FROM shape_vptree, branch ON parent_id = branch_phash_id'
        
        with_clause = 'WITH RECURSIVE ' + cte_table_name + ' AS ( ' + initial_select + ' UNION ALL ' +  recursive_select +  ')'
        
        unbalanced_nodes = self._c.execute( with_clause + ' SELECT branch_phash_id, phash FROM branch, shape_perceptual_hashes ON phash_id = branch_phash_id;', ( phash_id, ) ).fetchall()
        
        # removal of old branch, maintenance schedule, and orphan phashes
        
        job_key.SetVariable( 'popup_text_2', HydrusData.ConvertIntToPrettyString( len( unbalanced_nodes ) ) + ' leaves found--now clearing out old branch' )
        
        unbalanced_phash_ids = { p_id for ( p_id, p_h ) in unbalanced_nodes }
        
        self._c.executemany( 'DELETE FROM shape_vptree WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_phash_ids ) )
        
        self._c.executemany( 'DELETE FROM shape_maintenance_branch_regen WHERE phash_id = ?;', ( ( p_id, ) for p_id in unbalanced_phash_ids ) )
        
        select_statement = 'SELECT phash_id FROM shape_perceptual_hash_map WHERE phash_id IN %s;'
        
        useful_phash_ids = { p_id for ( p_id, ) in self._SelectFromList( select_statement, unbalanced_phash_ids ) }
        
        orphan_phash_ids = unbalanced_phash_ids.difference( useful_phash_ids )
        
        self._c.executemany( 'DELETE FROM shape_perceptual_hashes WHERE phash_id = ?;', ( ( p_id, ) for p_id in orphan_phash_ids ) )
        
        useful_nodes = [ row for row in unbalanced_nodes if row[0] in useful_phash_ids ]
        
        useful_population = len( useful_nodes )
        
        # now create the new branch, starting by choosing a new root and updating the parent's left/right reference to that
        
        if useful_population > 0:
            
            ( new_phash_id, new_phash ) = self._CacheSimilarFilesPopBestRootNode( useful_nodes ) #HydrusData.RandomPop( useful_nodes )
            
        else:
            
            new_phash_id = None
            
        
        if parent_id is not None:
            
            ( parent_inner_id, ) = self._c.execute( 'SELECT inner_id FROM shape_vptree WHERE phash_id = ?;', ( parent_id, ) ).fetchone()
            
            if parent_inner_id == phash_id:
                
                query = 'UPDATE shape_vptree SET inner_id = ?, inner_population = ? WHERE phash_id = ?;'
                
            else:
                
                query = 'UPDATE shape_vptree SET outer_id = ?, outer_population = ? WHERE phash_id = ?;'
                
            
            self._c.execute( query, ( new_phash_id, useful_population, parent_id ) )
            
        
        if useful_population > 0:
            
            self._CacheSimilarFilesGenerateBranch( job_key, parent_id, new_phash_id, new_phash, useful_nodes )
            
        
    
    def _CacheSimilarFilesRegenerateTree( self ):
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', 'regenerating similar file search data' )
        
        self._controller.pub( 'message', job_key )
        
        job_key.SetVariable( 'popup_text_1', 'gathering all leaves' )
        
        self._c.execute( 'DELETE FROM shape_vptree;' )
        
        all_nodes = self._c.execute( 'SELECT phash_id, phash FROM shape_perceptual_hashes;' ).fetchall()
        
        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertIntToPrettyString( len( all_nodes ) ) + ' leaves found, now regenerating' )
        
        ( root_id, root_phash ) = self._CacheSimilarFilesPopBestRootNode( all_nodes ) #HydrusData.RandomPop( all_nodes )
        
        self._CacheSimilarFilesGenerateBranch( job_key, None, root_id, root_phash, all_nodes )
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        job_key.DeleteVariable( 'popup_text_2' )
        
    
    def _CacheSimilarFilesSchedulePHashRegeneration( self, hash_ids = None ):
        
        if hash_ids is None:
            
            hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM files_info NATURAL JOIN current_files WHERE service_id = ? AND mime IN ' + HydrusData.SplayListForDB( HC.MIMES_WE_CAN_PHASH ) + ';', ( self._combined_local_file_service_id, ) ) ]
            
        
        self._c.executemany( 'INSERT OR IGNORE INTO shape_maintenance_phash_regen ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def _CacheSimilarFilesSearch( self, hash_id, max_hamming_distance ):
        
        if max_hamming_distance == 0:
            
            similar_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM shape_perceptual_hash_map WHERE phash_id IN ( SELECT phash_id FROM shape_perceptual_hash_map WHERE hash_id = ? );', ( hash_id, ) ) ]
            
        else:
            
            search_radius = max_hamming_distance
            
            result = self._c.execute( 'SELECT phash_id FROM shape_vptree WHERE parent_id IS NULL;' ).fetchone()
            
            if result is None:
                
                return []
                
            
            ( root_node_phash_id, ) = result
            
            search_phashes = [ phash for ( phash, ) in self._c.execute( 'SELECT phash FROM shape_perceptual_hashes NATURAL JOIN shape_perceptual_hash_map WHERE hash_id = ?;', ( hash_id, ) ) ]
            
            if len( search_phashes ) == 0:
                
                return []
                
            
            next_potentials = { root_node_phash_id : tuple( search_phashes ) }
            similar_phash_ids = set()
            
            num_cycles = 0
            
            while len( next_potentials ) > 0:
                
                current_potentials = next_potentials
                next_potentials = {}
                
                num_cycles += 1
                
                select_statement = 'SELECT phash_id, phash, radius, inner_id, outer_id FROM shape_perceptual_hashes NATURAL JOIN shape_vptree WHERE phash_id IN %s;'
                
                for ( node_phash_id, node_phash, node_radius, inner_phash_id, outer_phash_id ) in self._SelectFromList( select_statement, current_potentials.keys() ):
                    
                    search_phashes = current_potentials[ node_phash_id ]
                    
                    inner_search_phashes = []
                    outer_search_phashes = []
                    
                    for search_phash in search_phashes:
                        
                        # first check the node--is it similar?
                        
                        node_hamming_distance = HydrusData.Get64BitHammingDistance( search_phash, node_phash )
                        
                        if node_hamming_distance <= search_radius:
                            
                            similar_phash_ids.add( node_phash_id )
                            
                        
                        # now how about its children?
                        
                        if node_radius is not None:
                            
                            # we have two spheres--node and search--their centers separated by node_hamming_distance
                            # we want to search inside/outside the node_sphere if the search_sphere intersects with those spaces
                            # there are four possibles:
                            # (----N----)-(--S--)    intersects with outer only - distance between N and S > their radii
                            # (----N---(-)-S--)      intersects with both
                            # (----N-(--S-)-)        intersects with both
                            # (---(-N-S--)-)         intersects with inner only - distance between N and S + radius_S does not exceed radius_N
                            
                            spheres_disjoint = node_hamming_distance > ( node_radius + search_radius )
                            search_sphere_subset_of_node_sphere = ( node_hamming_distance + search_radius ) <= node_radius
                            
                            if not spheres_disjoint: # i.e. they intersect at some point
                                
                                inner_search_phashes.append( search_phash )
                                
                            
                            if not search_sphere_subset_of_node_sphere: # i.e. search sphere intersects with non-node sphere space at some point
                                
                                outer_search_phashes.append( search_phash )
                                
                            
                        
                    
                    if inner_phash_id is not None and len( inner_search_phashes ) > 0:
                        
                        next_potentials[ inner_phash_id ] = tuple( inner_search_phashes )
                        
                    
                    if outer_phash_id is not None and len( outer_search_phashes ) > 0:
                        
                        next_potentials[ outer_phash_id ] = tuple( outer_search_phashes )
                        
                    
                
            
            if HydrusGlobals.db_report_mode:
                
                HydrusData.ShowText( 'Similar file search completed in ' + HydrusData.ConvertIntToPrettyString( num_cycles ) + ' cycles.' )
                
            
            select_statement = 'SELECT hash_id FROM shape_perceptual_hash_map WHERE phash_id IN %s;'
            
            similar_hash_ids = [ hash_id for ( hash_id, ) in self._SelectFromList( select_statement, similar_phash_ids ) ]
            
        
        return similar_hash_ids
        
    
    def _CacheSpecificMappingsAddFiles( self, file_service_id, tag_service_id, hash_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._c.executemany( 'INSERT OR IGNORE INTO ' + cache_files_table_name + ' VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids ) )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( tag_service_id )
        
        ac_cache_changes = []
        
        for group_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 100 ):
            
            splayed_group_of_hash_ids = HydrusData.SplayListForDB( group_of_hash_ids )
            
            current_mapping_ids_raw = self._c.execute( 'SELECT tag_id, hash_id FROM ' + current_mappings_table_name + ' WHERE hash_id IN ' + splayed_group_of_hash_ids + ';' ).fetchall()
            
            current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( current_mapping_ids_raw )
            
            pending_mapping_ids_raw = self._c.execute( 'SELECT tag_id, hash_id FROM ' + pending_mappings_table_name + ' WHERE hash_id IN ' + splayed_group_of_hash_ids + ';' ).fetchall()
            
            pending_mapping_ids_dict = HydrusData.BuildKeyToSetDict( pending_mapping_ids_raw )
            
            all_ids_seen = set( current_mapping_ids_dict.keys() )
            all_ids_seen.update( pending_mapping_ids_dict.keys() )
            
            for tag_id in all_ids_seen:
                
                current_hash_ids = current_mapping_ids_dict[ tag_id ]
                
                num_current = len( current_hash_ids )
                
                if num_current > 0:
                    
                    self._c.executemany( 'INSERT OR IGNORE INTO ' + cache_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in current_hash_ids ) )
                    
                
                pending_hash_ids = pending_mapping_ids_dict[ tag_id ]
                
                num_pending = len( pending_hash_ids )
                
                if num_pending > 0:
                    
                    self._c.executemany( 'INSERT OR IGNORE INTO ' + cache_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in pending_hash_ids ) )
                    
                
                if num_current > 0 or num_pending > 0:
                    
                    ac_cache_changes.append( ( tag_id, num_current, num_pending ) )
                    
                
            
        
        if len( ac_cache_changes ) > 0:
            
            self._c.executemany( 'INSERT OR IGNORE INTO ' + ac_cache_table_name + ' ( tag_id, current_count, pending_count ) VALUES ( ?, ?, ? );', ( ( tag_id, 0, 0 ) for ( tag_id, num_current, num_pending ) in ac_cache_changes ) )
            
            self._c.executemany( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count + ?, pending_count = pending_count + ? WHERE tag_id = ?;', ( ( num_current, num_pending, tag_id ) for ( tag_id, num_current, num_pending ) in ac_cache_changes ) )
            
        
    
    def _CacheSpecificMappingsAddMappings( self, file_service_id, tag_service_id, mappings_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        for ( tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._CacheSpecificMappingsFilterHashIds( file_service_id, tag_service_id, hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.executemany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                
                num_pending_rescinded = self._GetRowCount()
                
                #
                
                self._c.executemany( 'INSERT OR IGNORE INTO ' + cache_current_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                
                num_added = self._GetRowCount()
                
                if num_pending_rescinded > 0:
                    
                    self._c.execute( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count + ?, pending_count = pending_count - ? WHERE tag_id = ?;', ( num_added, num_pending_rescinded, tag_id ) )
                    
                elif num_added > 0:
                    
                    self._c.execute( 'INSERT OR IGNORE INTO ' + ac_cache_table_name + ' ( tag_id, current_count, pending_count ) VALUES ( ?, ?, ? );', ( tag_id, 0, 0 ) )
                    
                    self._c.execute( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count + ? WHERE tag_id = ?;', ( num_added, tag_id ) )
                    
                
            
        
    
    def _CacheSpecificMappingsDrop( self, file_service_id, tag_service_id ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._c.execute( 'DROP TABLE IF EXISTS ' + cache_files_table_name + ';' )
        
        self._c.execute( 'DROP TABLE IF EXISTS ' + cache_current_mappings_table_name + ';' )
        
        self._c.execute( 'DROP TABLE IF EXISTS ' + cache_pending_mappings_table_name + ';' )
        
        self._c.execute( 'DROP TABLE IF EXISTS ' + ac_cache_table_name + ';' )
        
    
    def _CacheSpecificMappingsDeleteFiles( self, file_service_id, tag_service_id, hash_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._c.executemany( 'DELETE FROM ' + cache_files_table_name + ' WHERE hash_id = ?;', ( ( hash_id, ) for hash_id in hash_ids ) )
        
        ac_cache_changes = []
        
        for group_of_hash_ids in HydrusData.SplitListIntoChunks( hash_ids, 100 ):
            
            splayed_group_of_hash_ids = HydrusData.SplayListForDB( group_of_hash_ids )
            
            current_mapping_ids_raw = self._c.execute( 'SELECT tag_id, hash_id FROM ' + cache_current_mappings_table_name + ' WHERE hash_id IN ' + splayed_group_of_hash_ids + ';' ).fetchall()
            
            current_mapping_ids_dict = HydrusData.BuildKeyToSetDict( current_mapping_ids_raw )
            
            pending_mapping_ids_raw = self._c.execute( 'SELECT tag_id, hash_id FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id IN ' + splayed_group_of_hash_ids + ';' ).fetchall()
            
            pending_mapping_ids_dict = HydrusData.BuildKeyToSetDict( pending_mapping_ids_raw )
            
            all_ids_seen = set( current_mapping_ids_dict.keys() )
            all_ids_seen.update( pending_mapping_ids_dict.keys() )
            
            for tag_id in all_ids_seen:
                
                current_hash_ids = current_mapping_ids_dict[ tag_id ]
                
                num_current = len( current_hash_ids )
                
                if num_current > 0:
                    
                    self._c.executemany( 'DELETE FROM ' + cache_current_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in current_hash_ids ) )
                    
                
                pending_hash_ids = pending_mapping_ids_dict[ tag_id ]
                
                num_pending = len( pending_hash_ids )
                
                if num_pending > 0:
                    
                    self._c.executemany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in pending_hash_ids ) )
                    
                
                ac_cache_changes.append( ( tag_id, num_current, num_pending ) )
                
            
        
        if len( ac_cache_changes ) > 0:
            
            self._c.executemany( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count - ?, pending_count = pending_count - ? WHERE tag_id = ?;', ( ( num_current, num_pending, tag_id ) for ( tag_id, num_current, num_pending ) in ac_cache_changes ) )
            
            self._c.executemany( 'DELETE FROM ' + ac_cache_table_name + ' WHERE tag_id = ? AND current_count = ? AND pending_count = ?;', ( ( tag_id, 0, 0 ) for ( tag_id, num_current, num_pending ) in ac_cache_changes ) )
            
        
    
    def _CacheSpecificMappingsDeleteMappings( self, file_service_id, tag_service_id, mappings_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        for ( tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._CacheSpecificMappingsFilterHashIds( file_service_id, tag_service_id, hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.executemany( 'DELETE FROM ' + cache_current_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._c.execute( 'UPDATE ' + ac_cache_table_name + ' SET current_count = current_count - ? WHERE tag_id = ?;', ( num_deleted, tag_id ) )
                    
                    self._c.execute( 'DELETE FROM ' + ac_cache_table_name + ' WHERE tag_id = ? AND current_count = ? AND pending_count = ?;', ( tag_id, 0, 0 ) )
                    
                
            
        
    
    def _CacheSpecificMappingsFilterHashIds( self, file_service_id, tag_service_id, hash_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        select_statement = 'SELECT hash_id FROM ' + cache_files_table_name + ' WHERE hash_id IN %s;'
        
        return [ hash_id for ( hash_id, ) in self._SelectFromList( select_statement, hash_ids ) ]
        
    
    def _CacheSpecificMappingsGenerate( self, file_service_id, tag_service_id ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        self._c.execute( 'CREATE TABLE ' + cache_files_table_name + ' ( hash_id INTEGER PRIMARY KEY );' )
        
        self._c.execute( 'CREATE TABLE ' + cache_current_mappings_table_name + ' ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;' )
        
        self._c.execute( 'CREATE TABLE ' + cache_pending_mappings_table_name + ' ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;' )
        
        self._c.execute( 'CREATE TABLE ' + ac_cache_table_name + ' ( tag_id INTEGER PRIMARY KEY, current_count INTEGER, pending_count INTEGER );' )
        
        #
        
        hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?;', ( file_service_id, ) ) ]
        
        if len( hash_ids ) > 0:
            
            self._CacheSpecificMappingsAddFiles( file_service_id, tag_service_id, hash_ids )
            
        
    
    def _CacheSpecificMappingsGetAutocompleteCounts( self, file_service_id, tag_service_id, tag_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        select_statement = 'SELECT tag_id, current_count, pending_count FROM ' + ac_cache_table_name + ' WHERE tag_id IN %s;'
        
        return self._SelectFromListFetchAll( select_statement, tag_ids )
        
    
    def _CacheSpecificMappingsPendMappings( self, file_service_id, tag_service_id, mappings_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        for ( tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._CacheSpecificMappingsFilterHashIds( file_service_id, tag_service_id, hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.executemany( 'INSERT OR IGNORE INTO ' + cache_pending_mappings_table_name + ' ( hash_id, tag_id ) VALUES ( ?, ? );', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                
                num_added = self._GetRowCount()
                
                if num_added > 0:
                    
                    self._c.execute( 'INSERT OR IGNORE INTO ' + ac_cache_table_name + ' ( tag_id, current_count, pending_count ) VALUES ( ?, ?, ? );', ( tag_id, 0, 0 ) )
                    
                    self._c.execute( 'UPDATE ' + ac_cache_table_name + ' SET pending_count = pending_count + ? WHERE tag_id = ?;', ( num_added, tag_id ) )
                    
                
                
            
        
    
    def _CacheSpecificMappingsRescindPendingMappings( self, file_service_id, tag_service_id, mappings_ids ):
        
        ( cache_files_table_name, cache_current_mappings_table_name, cache_pending_mappings_table_name, ac_cache_table_name ) = GenerateSpecificMappingsCacheTableNames( file_service_id, tag_service_id )
        
        for ( tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._CacheSpecificMappingsFilterHashIds( file_service_id, tag_service_id, hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.executemany( 'DELETE FROM ' + cache_pending_mappings_table_name + ' WHERE hash_id = ? AND tag_id = ?;', ( ( hash_id, tag_id ) for hash_id in hash_ids ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._c.execute( 'UPDATE ' + ac_cache_table_name + ' SET pending_count = pending_count - ? WHERE tag_id = ?;', ( num_deleted, tag_id ) )
                    
                    self._c.execute( 'DELETE FROM ' + ac_cache_table_name + ' WHERE tag_id = ? AND current_count = ? AND pending_count = ?;', ( tag_id, 0, 0 ) )
                    
                
            
        
    
    def _CheckDBIntegrity( self ):
        
        prefix_string = 'checking db integrity: '
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', prefix_string + 'preparing' )
        
        self._controller.pub( 'message', job_key )
        
        num_errors = 0
        
        job_key.SetVariable( 'popup_title', prefix_string + 'running' )
        job_key.SetVariable( 'popup_text_1', 'errors found so far: ' + HydrusData.ConvertIntToPrettyString( num_errors ) )
        
        db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        for db_name in db_names:
            
            for ( text, ) in self._c.execute( 'PRAGMA ' + db_name + '.integrity_check;' ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    job_key.SetVariable( 'popup_title', prefix_string + 'cancelled' )
                    job_key.SetVariable( 'popup_text_1', 'errors found: ' + HydrusData.ConvertIntToPrettyString( num_errors ) )
                    
                    return
                    
                
                if text != 'ok':
                    
                    if num_errors == 0:
                        
                        HydrusData.Print( 'During a db integrity check, these errors were discovered:' )
                        
                    
                    HydrusData.Print( text )
                    
                    num_errors += 1
                    
                
                job_key.SetVariable( 'popup_text_1', 'errors found so far: ' + HydrusData.ConvertIntToPrettyString( num_errors ) )
                
            
        
        job_key.SetVariable( 'popup_title', prefix_string + 'completed' )
        job_key.SetVariable( 'popup_text_1', 'errors found: ' + HydrusData.ConvertIntToPrettyString( num_errors ) )
        
        HydrusData.Print( job_key.ToString() )
        
        job_key.Finish()
        
    
    def _CheckFileIntegrity( self, mode, move_location = None ):
        
        prefix_string = 'checking file integrity: '
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_text_1', prefix_string + 'preparing' )
        
        self._controller.pub( 'message', job_key )
        
        info = self._c.execute( 'SELECT hash_id, mime FROM current_files NATURAL JOIN files_info WHERE service_id = ?;', ( self._combined_local_file_service_id, ) ).fetchall()
        
        missing_count = 0
        deletee_hash_ids = []
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        for ( i, ( hash_id, mime ) ) in enumerate( info ):
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            if should_quit:
                
                return
                
            
            job_key.SetVariable( 'popup_text_1', prefix_string + HydrusData.ConvertValueRangeToPrettyString( i, len( info ) ) )
            job_key.SetVariable( 'popup_gauge_1', ( i, len( info ) ) )
            
            hash = self._GetHash( hash_id )
            
            try:
                
                # lockless because this db call is made by the locked client files manager
                path = client_files_manager.LocklessGetFilePath( hash, mime )
                
            except HydrusExceptions.FileMissingException:
                
                HydrusData.Print( 'Could not find the file for ' + hash.encode( 'hex' ) + '!' )
                
                deletee_hash_ids.append( hash_id )
                
                missing_count += 1
                
                continue
                
            
            if mode == 'thorough':
                
                actual_hash = HydrusFileHandling.GetHashFromPath( path )
                
                if actual_hash != hash:
                    
                    deletee_hash_ids.append( hash_id )
                    
                    if move_location is not None:
                        
                        move_filename = 'believed ' + hash.encode( 'hex' ) + ' actually ' + actual_hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ]
                        
                        move_path = os.path.join( move_location, move_filename )
                        
                        HydrusPaths.MergeFile( path, move_path )
                        
                    
                
            
        
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.SetVariable( 'popup_text_1', prefix_string + 'deleting the incorrect records' )
        
        self._DeleteFiles( self._local_file_service_id, deletee_hash_ids )
        self._DeleteFiles( self._trash_service_id, deletee_hash_ids )
        self._DeleteFiles( self._combined_local_file_service_id, deletee_hash_ids )
        
        final_text = 'done! '
        
        if len( deletee_hash_ids ) == 0:
            
            final_text += 'all files ok!'
            
        else:
            
            final_text += HydrusData.ConvertIntToPrettyString( missing_count ) + ' files were missing!'
            
            if mode == 'thorough':
                
                final_text += ' ' + HydrusData.ConvertIntToPrettyString( len( deletee_hash_ids ) - missing_count ) + ' files were incorrect and thus '
                
                if move_location is None:
                    
                    final_text += 'deleted!'
                    
                else:
                    
                    final_text += 'moved!'
                    
                
            
        
        job_key.SetVariable( 'popup_text_1', prefix_string + final_text )
        
        HydrusData.Print( job_key.ToString() )
        
        job_key.Finish()
        
    
    def _CleanUpCaches( self ):
        
        self._subscriptions_cache = {}
        self._service_cache = {}
        
    
    def _CreateDB( self ):
        
        client_files_default = os.path.join( self._db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( client_files_default )
        
        HydrusDB.SetupDBCreatePragma( self._c, no_wal = self._no_wal )
        
        try:
            
            self._BeginImmediate()
            
        except Exception as e:
            
            raise HydrusExceptions.DBAccessException( HydrusData.ToUnicode( e ) )
            
        
        self._c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY AUTOINCREMENT, service_key BLOB_BYTES UNIQUE, service_type INTEGER, name TEXT, dictionary_string TEXT );' )
        
        # main
        
        self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, num_rows INTEGER, timestamp INTEGER );' )
        
        self._c.execute( 'CREATE TABLE client_files_locations ( prefix TEXT, location TEXT );' )
        
        self._c.execute( 'CREATE TABLE current_files ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'current_files', [ 'timestamp' ] )
        
        self._c.execute( 'CREATE TABLE deleted_files ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY ( service_id, hash_id ) );' )
        
        self._c.execute( 'CREATE TABLE file_inbox ( hash_id INTEGER PRIMARY KEY );' )
        
        self._c.execute( 'CREATE TABLE files_info ( hash_id INTEGER PRIMARY KEY, size INTEGER, mime INTEGER, width INTEGER, height INTEGER, duration INTEGER, num_frames INTEGER, num_words INTEGER );' )
        self._CreateIndex( 'files_info', [ 'size' ] )
        self._CreateIndex( 'files_info', [ 'mime' ] )
        self._CreateIndex( 'files_info', [ 'width' ] )
        self._CreateIndex( 'files_info', [ 'height' ] )
        self._CreateIndex( 'files_info', [ 'duration' ] )
        self._CreateIndex( 'files_info', [ 'num_frames' ] )
        
        self._c.execute( 'CREATE TABLE file_transfers ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'file_transfers', [ 'hash_id' ] )
        
        self._c.execute( 'CREATE TABLE file_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, hash_id, reason_id ) );' )
        self._CreateIndex( 'file_petitions', [ 'hash_id' ] )
        
        self._c.execute( 'CREATE TABLE hydrus_sessions ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, session_key BLOB_BYTES, expiry INTEGER );' )
        
        self._c.execute( 'CREATE TABLE json_dict ( name TEXT PRIMARY KEY, dump BLOB_BYTES );' )
        self._c.execute( 'CREATE TABLE json_dumps ( dump_type INTEGER PRIMARY KEY, version INTEGER, dump BLOB_BYTES );' )
        self._c.execute( 'CREATE TABLE json_dumps_named ( dump_type INTEGER, dump_name TEXT, version INTEGER, dump BLOB_BYTES, PRIMARY KEY ( dump_type, dump_name ) );' )
        
        self._c.execute( 'CREATE TABLE local_hashes ( hash_id INTEGER PRIMARY KEY, md5 BLOB_BYTES, sha1 BLOB_BYTES, sha512 BLOB_BYTES );' )
        self._CreateIndex( 'local_hashes', [ 'md5' ] )
        self._CreateIndex( 'local_hashes', [ 'sha1' ] )
        self._CreateIndex( 'local_hashes', [ 'sha512' ] )
        
        self._c.execute( 'CREATE TABLE local_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, rating REAL, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'local_ratings', [ 'hash_id' ] )
        self._CreateIndex( 'local_ratings', [ 'rating' ] )
        
        self._c.execute( 'CREATE TABLE options ( options TEXT_YAML );', )
        
        self._c.execute( 'CREATE TABLE recent_tags ( service_id INTEGER REFERENCES services ON DELETE CASCADE, tag_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id ) );' )
        
        self._c.execute( 'CREATE TABLE remote_ratings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, count INTEGER, rating REAL, score REAL, PRIMARY KEY ( service_id, hash_id ) );' )
        self._CreateIndex( 'remote_ratings', [ 'hash_id' ] )
        self._CreateIndex( 'remote_ratings', [ 'rating' ] )
        self._CreateIndex( 'remote_ratings', [ 'score' ] )
        
        self._c.execute( 'CREATE TABLE remote_thumbnails ( service_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
        
        self._c.execute( 'CREATE TABLE service_filenames ( service_id INTEGER REFERENCES services ON DELETE CASCADE, hash_id INTEGER, filename TEXT, PRIMARY KEY ( service_id, hash_id ) );' )
        self._c.execute( 'CREATE TABLE service_directories ( service_id INTEGER REFERENCES services ON DELETE CASCADE, directory_id INTEGER, num_files INTEGER, total_size INTEGER, note TEXT, PRIMARY KEY ( service_id, directory_id ) );' )
        self._c.execute( 'CREATE TABLE service_directory_file_map ( service_id INTEGER REFERENCES services ON DELETE CASCADE, directory_id INTEGER, hash_id INTEGER, PRIMARY KEY ( service_id, directory_id, hash_id ) );' )
        
        self._c.execute( 'CREATE TABLE service_info ( service_id INTEGER REFERENCES services ON DELETE CASCADE, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );' )
        
        self._c.execute( 'CREATE TABLE statuses ( status_id INTEGER PRIMARY KEY, status TEXT UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE tag_censorship ( service_id INTEGER PRIMARY KEY REFERENCES services ON DELETE CASCADE, blacklist INTEGER_BOOLEAN, tags TEXT_YAML );' )
        
        self._c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_tag_id INTEGER, parent_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, child_tag_id, parent_tag_id, status ) );' )
        
        self._c.execute( 'CREATE TABLE tag_parent_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_tag_id INTEGER, parent_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, child_tag_id, parent_tag_id, status ) );' )
        
        self._c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );' )
        
        self._c.execute( 'CREATE TABLE tag_sibling_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );' )
        
        self._c.execute( 'CREATE TABLE urls ( url TEXT PRIMARY KEY, hash_id INTEGER );' )
        self._CreateIndex( 'urls', [ 'hash_id' ] )
        
        self._c.execute( 'CREATE TABLE vacuum_timestamps ( name TEXT, timestamp INTEGER );' )
        
        self._c.execute( 'CREATE TABLE version ( version INTEGER );' )
        
        self._c.execute( 'CREATE TABLE web_sessions ( name TEXT PRIMARY KEY, cookies TEXT_YAML, expiry INTEGER );' )
        
        self._c.execute( 'CREATE TABLE yaml_dumps ( dump_type INTEGER, dump_name TEXT, dump TEXT_YAML, PRIMARY KEY ( dump_type, dump_name ) );' )
        
        # cache
        
        self._c.execute( 'CREATE TABLE external_caches.shape_perceptual_hashes ( phash_id INTEGER PRIMARY KEY, phash BLOB_BYTES UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE external_caches.shape_perceptual_hash_map ( phash_id INTEGER, hash_id INTEGER, PRIMARY KEY ( phash_id, hash_id ) );' )
        self._CreateIndex( 'external_caches.shape_perceptual_hash_map', [ 'hash_id' ] )
        
        self._c.execute( 'CREATE TABLE external_caches.shape_vptree ( phash_id INTEGER PRIMARY KEY, parent_id INTEGER, radius INTEGER, inner_id INTEGER, inner_population INTEGER, outer_id INTEGER, outer_population INTEGER );' )
        self._CreateIndex( 'external_caches.shape_vptree', [ 'parent_id' ] )
        
        self._c.execute( 'CREATE TABLE external_caches.shape_maintenance_phash_regen ( hash_id INTEGER PRIMARY KEY );' )
        self._c.execute( 'CREATE TABLE external_caches.shape_maintenance_branch_regen ( phash_id INTEGER PRIMARY KEY );' )
        
        self._c.execute( 'CREATE TABLE external_caches.shape_search_cache ( hash_id INTEGER PRIMARY KEY, searched_distance INTEGER );' )
        
        self._c.execute( 'CREATE TABLE external_caches.duplicate_pairs ( smaller_hash_id INTEGER, larger_hash_id INTEGER, duplicate_type INTEGER, PRIMARY KEY ( smaller_hash_id, larger_hash_id ) );' )
        self._CreateIndex( 'external_caches.duplicate_pairs', [ 'larger_hash_id', 'smaller_hash_id' ], unique = True )
        
        # master
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.namespaces ( namespace_id INTEGER PRIMARY KEY, namespace TEXT UNIQUE );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.subtags ( subtag_id INTEGER PRIMARY KEY, subtag TEXT UNIQUE );' )
        
        self._c.execute( 'CREATE VIRTUAL TABLE IF NOT EXISTS external_master.subtags_fts4 USING fts4( subtag );' )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( tag_id INTEGER PRIMARY KEY, namespace_id INTEGER, subtag_id INTEGER );' )
        self._CreateIndex( 'external_master.tags', [ 'subtag_id', 'namespace_id' ] )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.texts ( text_id INTEGER PRIMARY KEY, text TEXT UNIQUE );' )
        
        # inserts
        
        location = HydrusPaths.ConvertAbsPathToPortablePath( client_files_default )
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            self._c.execute( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 'f' + prefix, location ) )
            self._c.execute( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 't' + prefix, location ) )
            self._c.execute( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', ( 'r' + prefix, location ) )
            
        
        init_service_info = []
        
        init_service_info.append( ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        init_service_info.append( ( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'my files' ) )
        init_service_info.append( ( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, CC.TRASH_SERVICE_KEY ) )
        init_service_info.append( ( CC.LOCAL_UPDATE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'repository updates' ) )
        init_service_info.append( ( CC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, CC.LOCAL_TAG_SERVICE_KEY ) )
        init_service_info.append( ( CC.COMBINED_FILE_SERVICE_KEY, HC.COMBINED_FILE, CC.COMBINED_FILE_SERVICE_KEY ) )
        init_service_info.append( ( CC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, CC.COMBINED_TAG_SERVICE_KEY ) )
        init_service_info.append( ( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, CC.LOCAL_BOORU_SERVICE_KEY ) )
        
        self._combined_files_ac_caches = {}
        
        for ( service_key, service_type, name ) in init_service_info:
            
            dictionary = ClientServices.GenerateDefaultServiceDictionary( service_type )
            
            self._AddService( service_key, service_type, name, dictionary )
            
        
        self._c.executemany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', ( ( YAML_DUMP_ID_REMOTE_BOORU, name, booru ) for ( name, booru ) in ClientDefaults.GetDefaultBoorus().items() ) )
        
        self._c.executemany( 'INSERT INTO yaml_dumps VALUES ( ?, ?, ? );', ( ( YAML_DUMP_ID_IMAGEBOARD, name, imageboards ) for ( name, imageboards ) in ClientDefaults.GetDefaultImageboards() ) )
        
        new_options = ClientData.ClientOptions( self._db_dir )
        
        self._SetJSONDump( new_options )
        
        self._c.execute( 'INSERT INTO namespaces ( namespace_id, namespace ) VALUES ( ?, ? );', ( 1, '' ) )
        
        self._c.execute( 'INSERT INTO version ( version ) VALUES ( ? );', ( HC.SOFTWARE_VERSION, ) )
        
        self._c.executemany( 'INSERT INTO json_dumps_named VALUES ( ?, ?, ?, ? );', ClientDefaults.GetDefaultScriptRows() )
        
        self._Commit()
        
    
    def _DeleteFiles( self, service_id, hash_ids ):
        
        splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
        
        valid_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) ) }
        
        if len( valid_hash_ids ) > 0:
            
            splayed_valid_hash_ids = HydrusData.SplayListForDB( valid_hash_ids )
            
            # remove them from the service
            
            self._c.execute( 'DELETE FROM current_files WHERE service_id = ? AND hash_id IN ' + splayed_valid_hash_ids + ';', ( service_id, ) )
            
            self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + splayed_valid_hash_ids + ';', ( service_id, ) )
            
            info = self._c.execute( 'SELECT size, mime FROM files_info WHERE hash_id IN ' + splayed_valid_hash_ids + ';' ).fetchall()
            
            num_files = len( valid_hash_ids )
            delta_size = sum( ( size for ( size, mime ) in info ) )
            num_inbox = len( valid_hash_ids.intersection( self._inbox_hash_ids ) )
            
            service_info_updates = []
            
            service_info_updates.append( ( -delta_size, service_id, HC.SERVICE_INFO_TOTAL_SIZE ) )
            service_info_updates.append( ( -num_files, service_id, HC.SERVICE_INFO_NUM_FILES ) )
            service_info_updates.append( ( -num_inbox, service_id, HC.SERVICE_INFO_NUM_INBOX ) )
            
            select_statement = 'SELECT COUNT( * ) FROM files_info WHERE mime IN ' + HydrusData.SplayListForDB( HC.SEARCHABLE_MIMES ) + ' AND hash_id IN %s;'
            
            num_viewable_files = sum( self._STL( self._SelectFromList( select_statement, valid_hash_ids ) ) )
            
            service_info_updates.append( ( -num_viewable_files, service_id, HC.SERVICE_INFO_NUM_VIEWABLE_FILES ) )
            
            # now do special stuff
            
            service = self._GetService( service_id )
            
            service_type = service.GetServiceType()
            
            # record the deleted row if appropriate
            
            if service_id == self._combined_local_file_service_id or service_type == HC.FILE_REPOSITORY:
                
                service_info_updates.append( ( num_files, service_id, HC.SERVICE_INFO_NUM_DELETED_FILES ) )
                
                self._c.executemany( 'INSERT OR IGNORE INTO deleted_files ( service_id, hash_id ) VALUES ( ?, ? );', [ ( service_id, hash_id ) for hash_id in valid_hash_ids ] )
                
            
            # if we maintain tag counts for this service, update
            
            if service_type in HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES:
                
                tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
                
                for tag_service_id in tag_service_ids:
                    
                    self._CacheSpecificMappingsDeleteFiles( service_id, tag_service_id, valid_hash_ids )
                    
                
            
            # if the files are no longer in any local file services, send them to the trash
            
            local_file_service_ids = self._GetServiceIds( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            if service_id in local_file_service_ids:
                
                splayed_local_file_service_ids = HydrusData.SplayListForDB( local_file_service_ids )
                
                non_orphan_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE hash_id IN ' + splayed_valid_hash_ids + ' AND service_id IN ' + splayed_local_file_service_ids + ';' ) }
                
                orphan_hash_ids = valid_hash_ids.difference( non_orphan_hash_ids )
                
                if len( orphan_hash_ids ) > 0:
                    
                    now = HydrusData.GetNow()
                    
                    delete_rows = [ ( hash_id, now ) for hash_id in orphan_hash_ids ]
                    
                    self._AddFiles( self._trash_service_id, delete_rows )
                    
                
            
            # if the files are being fully deleted, then physically delete them
            
            if service_id == self._combined_local_file_service_id:
                
                self._DeletePhysicalFiles( valid_hash_ids )
                
            
            # push the info updates, notify
            
            self._c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
            
            self.pub_after_commit( 'notify_new_pending' )
            
        
        return valid_hash_ids
        
    
    def _DeleteHydrusSessionKey( self, service_key ):
        
        try:
            
            service_id = self._GetServiceId( service_key )
            
        except HydrusExceptions.DataMissing: # usually a test service resetting itself--np
            
            return
            
        
        self._c.execute( 'DELETE FROM hydrus_sessions WHERE service_id = ?;', ( service_id, ) )
        
    
    def _DeleteJSONDump( self, dump_type ):
        
        self._c.execute( 'DELETE FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) )
        
    
    def _DeleteJSONDumpNamed( self, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) )
            
        else:
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
        
    
    def _DeletePending( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service = self._GetService( service_id )
        
        if service.GetServiceType() == HC.TAG_REPOSITORY:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
            
            pending_rescinded_mappings_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag_id, hash_id FROM ' + pending_mappings_table_name + ';' ) ).items()
            
            petitioned_rescinded_mappings_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag_id, hash_id FROM ' + petitioned_mappings_table_name + ';' ) ).items()
            
            self._UpdateMappings( service_id, pending_rescinded_mappings_ids = pending_rescinded_mappings_ids, petitioned_rescinded_mappings_ids = petitioned_rescinded_mappings_ids )
            
            self._c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, ) )
            self._c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ?;', ( service_id, ) )
            
        elif service.GetServiceType() in ( HC.FILE_REPOSITORY, HC.IPFS ):
            
            self._c.execute( 'DELETE FROM file_transfers WHERE service_id = ?;', ( service_id, ) )
            self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ?;', ( service_id, ) )
            
        
        self.pub_after_commit( 'notify_new_pending' )
        self.pub_after_commit( 'notify_new_siblings_data' )
        self.pub_after_commit( 'notify_new_siblings_gui' )
        self.pub_after_commit( 'notify_new_parents' )
        
        self.pub_service_updates_after_commit( { service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_DELETE_PENDING ) ] } )
        
    
    def _DeletePhysicalFiles( self, hash_ids ):
        
        self._ArchiveFiles( hash_ids )
        
        hash_ids = set( hash_ids )
        
        potentially_pending_upload_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_transfers;', ) }
        
        deletable_file_hash_ids = hash_ids.difference( potentially_pending_upload_hash_ids )
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        if len( deletable_file_hash_ids ) > 0:
            
            file_hashes = self._GetHashes( deletable_file_hash_ids )
            
            time_to_delete = HydrusData.GetNow() + 2
            
            self._controller.CallToThread( client_files_manager.DelayedDeleteFiles, file_hashes, time_to_delete )
            
        
        useful_thumbnail_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) }
        
        deletable_thumbnail_hash_ids = hash_ids.difference( useful_thumbnail_hash_ids )
        
        if len( deletable_thumbnail_hash_ids ) > 0:
            
            thumbnail_hashes = self._GetHashes( deletable_thumbnail_hash_ids )
            
            time_to_delete = HydrusData.GetNow() + 2
            
            self._controller.CallToThread( client_files_manager.DelayedDeleteThumbnails, thumbnail_hashes, time_to_delete )
            
        
        for hash_id in hash_ids:
            
            self._CacheSimilarFilesDeleteFile( hash_id )
            
        
    
    def _DeleteService( self, service_id ):
        
        service = self._GetService( service_id )
        
        service_key = service.GetServiceKey()
        service_type = service.GetServiceType()
        
        self._c.execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
        
        self._c.execute( 'DELETE FROM remote_thumbnails WHERE service_id = ?;', ( service_id, ) )
        
        if service_type in HC.TAG_SERVICES:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
            
            self._c.execute( 'DROP TABLE ' + current_mappings_table_name + ';' )
            self._c.execute( 'DROP TABLE ' + deleted_mappings_table_name + ';' )
            self._c.execute( 'DROP TABLE ' + pending_mappings_table_name + ';' )
            self._c.execute( 'DROP TABLE ' + petitioned_mappings_table_name + ';' )
            
            #
            
            self._CacheCombinedFilesMappingsDrop( service_id )
            
            file_service_ids = self._GetServiceIds( HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES )
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsDrop( file_service_id, service_id )
                
            
        
        if service_type in HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES:
            
            tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                self._CacheSpecificMappingsDrop( service_id, tag_service_id )
                
            
        
        if service_id in self._service_cache:
            
            del self._service_cache[ service_id ]
            
        
        service_update = HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_RESET )
        
        service_keys_to_service_updates = { service_key : [ service_update ] }
        
        self.pub_service_updates_after_commit( service_keys_to_service_updates )
        
    
    def _DeleteServiceDirectory( self, service_id, dirname ):
        
        directory_id = self._GetTextId( dirname )
        
        self._c.execute( 'DELETE FROM service_directories WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        self._c.execute( 'DELETE FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        
    
    def _DeleteServiceInfo( self ):
        
        self._c.execute( 'DELETE FROM service_info;' )
        
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _DeleteTagParents( self, service_id, pairs ):
        
        self._c.executemany( 'DELETE FROM tag_parents WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ?;', ( ( service_id, child_tag_id, parent_tag_id ) for ( child_tag_id, parent_tag_id ) in pairs ) )
        self._c.executemany( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ? AND status = ?;', ( ( service_id, child_tag_id, parent_tag_id, HC.CONTENT_STATUS_PETITIONED ) for ( child_tag_id, parent_tag_id ) in pairs )  )
        
        self._c.executemany( 'INSERT OR IGNORE INTO tag_parents ( service_id, child_tag_id, parent_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, child_tag_id, parent_tag_id, HC.CONTENT_STATUS_DELETED ) for ( child_tag_id, parent_tag_id ) in pairs ) )
        
    
    def _DeleteTagSiblings( self, service_id, pairs ):
        
        self._c.executemany( 'DELETE FROM tag_siblings WHERE service_id = ? AND bad_tag_id = ?;', ( ( service_id, bad_tag_id ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        self._c.executemany( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND status = ?;', ( ( service_id, bad_tag_id, HC.CONTENT_STATUS_PETITIONED ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
        self._c.executemany( 'INSERT OR IGNORE INTO tag_siblings ( service_id, bad_tag_id, good_tag_id, status ) VALUES ( ?, ?, ?, ? );', ( ( service_id, bad_tag_id, good_tag_id, HC.CONTENT_STATUS_DELETED ) for ( bad_tag_id, good_tag_id ) in pairs ) )
        
    
    def _DeleteYAMLDump( self, dump_type, dump_name = None ):
        
        if dump_name is None: self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) )
        else:
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION and dump_name in self._subscriptions_cache: del self._subscriptions_cache[ dump_name ]
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
            
            self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self._GetServiceId( CC.LOCAL_BOORU_SERVICE_KEY )
            
            self._c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            self._controller.pub( 'refresh_local_booru_shares' )
            
        
    
    def _ExportToTagArchive( self, path, service_key, hash_type, hashes = None ):
        
        # This could nicely take a whitelist or a blacklist for namespace filtering
        
        prefix_string = 'exporting to tag archive: '
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_text_1', prefix_string + 'preparing' )
        
        self._controller.pub( 'message', job_key )
        
        service_id = self._GetServiceId( service_key )
        
        hta_exists = os.path.exists( path )
        
        hta = HydrusTagArchive.HydrusTagArchive( path )
        
        if hta_exists and hta.HasHashTypeSet() and hta.GetHashType() != hash_type:
            
            raise Exception( 'This tag archive does not use the expected hash type, so it cannot be exported to!' )
            
        
        if hashes is None:
            
            include_current = True
            include_pending = False
            
            hash_ids = self._GetHashIdsThatHaveTags( service_key, include_current, include_pending )
            
        else:
            
            hash_ids = self._GetHashIds( hashes )
            
        
        service_ids_to_export_from = []
        
        if service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            service_ids_to_export_from = self._GetServiceIds( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
            
        else:
            
            service_ids_to_export_from = [ service_id ]
            
        
        hta.BeginBigJob()
        
        for service_id in service_ids_to_export_from:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
            
            for ( i, hash_id ) in enumerate( hash_ids ):
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    return
                    
                
                if i % 100 == 0:
                    
                    job_key.SetVariable( 'popup_text_1', prefix_string + HydrusData.ConvertValueRangeToPrettyString( i, len( hash_ids ) ) )
                    job_key.SetVariable( 'popup_gauge_1', ( i, len( hash_ids ) ) )
                    
                
                if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                    
                    archive_hash = self._GetHash( hash_id )
                    
                else:
                    
                    if hash_type == HydrusTagArchive.HASH_TYPE_MD5: h = 'md5'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: h = 'sha1'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: h = 'sha512'
                    
                    result = self._c.execute( 'SELECT ' + h + ' FROM local_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                    
                    if result is None:
                        
                        continue
                        
                    
                    ( archive_hash, ) = result
                    
                
                tag_ids = self._STL( self._c.execute( 'SELECT tag_id FROM ' + current_mappings_table_name + ' WHERE hash_id = ?;', ( hash_id, ) ) )
                
                tags = self._GetTags( tag_ids )
                
                hta.AddMappings( archive_hash, tags )
                
            
        
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.SetVariable( 'popup_text_1', prefix_string + 'committing the change and vacuuming the archive' )
        
        hta.CommitBigJob()
        
        job_key.SetVariable( 'popup_text_1', prefix_string + 'done!' )
        
        HydrusData.Print( job_key.ToString() )
        
        job_key.Finish()
        
    
    def _FilterHashes( self, hashes, file_service_key ):
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            return hashes
            
        
        service_id = self._GetServiceId( file_service_key )
        
        hashes_result = []
        
        for hash in hashes:
            
            if not self._HashExists( hash ):
                
                continue
                
            
            hash_id = self._GetHashId( hash )
            
            result = self._c.execute( 'SELECT 1 FROM current_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            if result is not None:
                
                hashes_result.append( hash )
                
            
        
        return hashes_result
        
    
    def _GetAutocompleteCounts( self, tag_service_id, file_service_id, tag_ids, include_current, include_pending ):
        
        if tag_service_id == self._combined_tag_service_id:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ tag_service_id ]
            
        
        if file_service_id == self._combined_file_service_id:
            
            cache_results = self._CacheCombinedFilesMappingsGetAutocompleteCounts( tag_service_id, tag_ids )
            
        else:
            
            cache_results = []
            
            for search_tag_service_id in search_tag_service_ids:
                
                cache_results.extend( self._CacheSpecificMappingsGetAutocompleteCounts( file_service_id, search_tag_service_id, tag_ids ) )
                
            
        
        #
        
        ids_to_count = {}
        
        for ( tag_id, current_count, pending_count ) in cache_results:
            
            if not include_current:
                
                current_count = 0
                
            
            if not include_pending:
                
                pending_count = 0
                
            
            if tag_id in ids_to_count:
                
                ( current_min, current_max, pending_min, pending_max ) = ids_to_count[ tag_id ]
                
                ( current_min, current_max ) = ClientData.MergeCounts( current_min, current_max, current_count, None )
                ( pending_min, pending_max ) = ClientData.MergeCounts( pending_min, pending_max, pending_count, None )
                
            else:
                
                ( current_min, current_max, pending_min, pending_max ) = ( current_count, None, pending_count, None )
                
            
            ids_to_count[ tag_id ] = ( current_min, current_max, pending_min, pending_max )
            
        
        
        return ids_to_count
        
    
    def _GetAutocompleteTagIds( self, service_key, search_text, exact_match ):
        
        if exact_match:
            
            tag = search_text
            
            if not self._TagExists( tag ):
                
                return set()
                
            
            ( tag_id ) = self._GetTagId( tag )
            
            predicates_phrase = 'tag_id = ' + str( tag_id )
            
        else:
            
            def GetPossibleSubtagIds( half_complete_subtag ):
                
                # complicated queries are passed to LIKE, because MATCH only supports appended wildcards 'gun*', and not complex stuff like '*gun*'
                
                if ClientSearch.IsComplexWildcard( half_complete_subtag ):
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( half_complete_subtag )
                    
                    return self._STL( self._c.execute( 'SELECT subtag_id FROM subtags WHERE subtag LIKE ?;', ( like_param, ) ) )
                    
                else:
                    
                    subtags_fts4_param = '"' + half_complete_subtag + '"'
                    
                    return self._STL( self._c.execute( 'SELECT docid FROM subtags_fts4 WHERE subtag MATCH ?;', ( subtags_fts4_param, ) ) )
                    
                
            
            ( namespace, half_complete_subtag ) = HydrusTags.SplitTag( search_text )
            
            if namespace != '':
                
                predicates = []
                
                if '*' in namespace:
                    
                    like_param = ConvertWildcardToSQLiteLikeParameter( namespace )
                    
                    possible_namespace_ids = self._STL( self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace LIKE ?;', ( like_param, ) ) )
                    
                    predicates.append( 'namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) )
                    
                else:
                    
                    result = self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
                    
                    if result is None:
                        
                        return set()
                        
                    else:
                        
                        ( namespace_id, ) = result
                        
                        predicates.append( 'namespace_id = ' + str( namespace_id ) )
                        
                    
                
                if half_complete_subtag not in ( '*', '' ):
                    
                    possible_subtag_ids = GetPossibleSubtagIds( half_complete_subtag )
                    
                    predicates.append( 'subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) )
                    
                
                predicates_phrase = ' AND '.join( predicates )
                
            else:
                
                if ClientSearch.ConvertTagToSearchable( half_complete_subtag ) in ( '', '*' ):
                    
                    return set()
                    
                
                like_param = ConvertWildcardToSQLiteLikeParameter( half_complete_subtag )
                
                possible_namespace_ids = self._STL( self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace LIKE ?;', ( like_param, ) ) )
                
                possible_subtag_ids = GetPossibleSubtagIds( half_complete_subtag )
                
                predicates_phrase = 'namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) + ' OR subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids )
                
            
        
        tag_ids = self._STS( self._c.execute( 'SELECT tag_id FROM tags WHERE ' + predicates_phrase + ';' ) )
        
        # now fetch siblings, add to set
        
        siblings_manager = self._controller.GetManager( 'tag_siblings' )
        
        all_associated_sibling_tags = siblings_manager.GetAutocompleteSiblings( service_key, search_text, exact_match )
        
        for sibling_tag in all_associated_sibling_tags:
            
            tag_id = self._GetTagId( sibling_tag )
            
            tag_ids.add( tag_id )
            
        
        return tag_ids
        
    
    def _GetAutocompletePredicates( self, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, file_service_key = CC.COMBINED_FILE_SERVICE_KEY, search_text = '', exact_match = False, inclusive = True, include_current = True, include_pending = True, add_namespaceless = False, collapse_siblings = False ):
        
        tag_ids = self._GetAutocompleteTagIds( tag_service_key, search_text, exact_match )
        
        tag_service_id = self._GetServiceId( tag_service_key )
        file_service_id = self._GetServiceId( file_service_key )
        
        if tag_service_id == self._combined_tag_service_id:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ tag_service_id ]
            
        
        all_predicates = []
        
        tag_censorship_manager = self._controller.GetManager( 'tag_censorship' )
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        for search_tag_service_id in search_tag_service_ids:
            
            search_tag_service_key = self._GetService( search_tag_service_id ).GetServiceKey()
            
            ids_to_count = self._GetAutocompleteCounts( search_tag_service_id, file_service_id, tag_ids, include_current, include_pending )
            
            #
            
            tag_ids_to_tags = self._GetTagIdsToTags( ids_to_count.keys() )
            
            tags_and_counts_generator = ( ( tag_ids_to_tags[ id ], ids_to_count[ id ] ) for id in ids_to_count.keys() )
            
            predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive, min_current_count = min_current_count, min_pending_count = min_pending_count, max_current_count = max_current_count, max_pending_count = max_pending_count ) for ( tag, ( min_current_count, max_current_count, min_pending_count, max_pending_count ) ) in tags_and_counts_generator ]
            
            if collapse_siblings:
                
                predicates = siblings_manager.CollapsePredicates( search_tag_service_key, predicates )
                
            
            predicates = tag_censorship_manager.FilterPredicates( search_tag_service_key, predicates )
            
            all_predicates.extend( predicates )
            
        
        predicates = ClientData.MergePredicates( all_predicates, add_namespaceless = add_namespaceless )
        
        return predicates
        
    
    def _GetBigTableNamesToAnalyze( self, force_reanalyze = False ):
        
        db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        all_names = set()
        
        for db_name in db_names:
            
            all_names.update( ( name for ( name, ) in self._c.execute( 'SELECT name FROM ' + db_name + '.sqlite_master WHERE type = ?;', ( 'table', ) ) ) )
            
        
        all_names.discard( 'sqlite_stat1' )
        
        if force_reanalyze:
            
            names_to_analyze = list( all_names )
            
        else:
            
            # The idea here is that some tables get huge faster than the normal maintenance cycle (usually after syncing to big repo)
            # They then search real slow for like 14 days. And then after that they don't need new analyzes tbh
            # Analyze on a small table takes ~1ms, so let's instead frequently do smaller tables and then catch them and throttle down as they grow
            
            big_table_minimum = 10000
            huge_table_minimum = 1000000
            
            small_table_stale_time_delta = 86400
            big_table_stale_time_delta = 30 * 86400
            huge_table_stale_time_delta = 30 * 86400 * 6
            
            existing_names_to_info = { name : ( num_rows, timestamp ) for ( name, num_rows, timestamp ) in self._c.execute( 'SELECT name, num_rows, timestamp FROM analyze_timestamps;' ) }
            
            names_to_analyze = []
            
            for name in all_names:
                
                if name in existing_names_to_info:
                    
                    ( num_rows, timestamp ) = existing_names_to_info[ name ]
                    
                    if num_rows > big_table_minimum:
                        
                        if num_rows > huge_table_minimum:
                            
                            due_time = timestamp + huge_table_stale_time_delta
                            
                        else:
                            
                            due_time = timestamp + big_table_stale_time_delta
                            
                        
                        if HydrusData.TimeHasPassed( due_time ):
                            
                            names_to_analyze.append( name )
                            
                        
                    else:
                        
                        # these usually take a couple of milliseconds, so just sneak them in here. no need to bother the user with a prompt
                        if HydrusData.TimeHasPassed( timestamp + small_table_stale_time_delta ):
                            
                            self._AnalyzeTable( name )
                            
                        
                    
                else:
                    
                    names_to_analyze.append( name )
                    
                
            
        
        return names_to_analyze
        
    
    def _GetClientFilesLocations( self ):
        
        result = { prefix : HydrusPaths.ConvertPortablePathToAbsPath( location ) for ( prefix, location ) in self._c.execute( 'SELECT prefix, location FROM client_files_locations;' ) }
        
        return result
        
    
    def _GetDownloads( self ):
        
        return { hash for ( hash, ) in self._c.execute( 'SELECT hash FROM file_transfers NATURAL JOIN hashes WHERE service_id = ?;', ( self._combined_local_file_service_id, ) ) }
        
    
    def _GetFileHashes( self, given_hashes, given_hash_type, desired_hash_type ):
        
        if given_hash_type == 'sha256':
            
            hash_ids = self._GetHashIds( given_hashes )
            
        else:
            
            hash_ids = []
            
            for given_hash in given_hashes:
                
                if given_hash is None:
                    
                    continue
                    
                
                result = self._c.execute( 'SELECT hash_id FROM local_hashes WHERE ' + given_hash_type + ' = ?;', ( sqlite3.Binary( given_hash ), ) ).fetchone()
                
                if result is not None:
                    
                    ( hash_id, ) = result
                    
                    hash_ids.append( hash_id )
                    
                
            
        
        if desired_hash_type == 'sha256':
            
            desired_hashes = self._GetHashes( hash_ids )
            
        else:
            
            desired_hashes = [ desired_hash for ( desired_hash, ) in self._c.execute( 'SELECT ' + desired_hash_type + ' FROM local_hashes WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) ]
            
        
        return desired_hashes
        
    
    def _GetFileSystemPredicates( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service = self._GetService( service_id )
        
        service_type = service.GetServiceType()
        
        predicates = []
        
        if service_type in ( HC.COMBINED_FILE, HC.COMBINED_TAG ):
            
            predicates.extend( [ ClientSearch.Predicate( predicate_type, None ) for predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, HC.PREDICATE_TYPE_SYSTEM_UNTAGGED, HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_HASH ] ] )
            
        elif service_type in HC.TAG_SERVICES:
            
            service_info = self._GetServiceInfoSpecific( service_id, service_type, { HC.SERVICE_INFO_NUM_FILES } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = num_everything ) )
            
            predicates.extend( [ ClientSearch.Predicate( predicate_type, None ) for predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_UNTAGGED, HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_HASH ] ] )
            
        elif service_type in HC.FILE_SERVICES:
            
            service_info = self._GetServiceInfoSpecific( service_id, service_type, { HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_NUM_INBOX } )
            
            num_everything = service_info[ HC.SERVICE_INFO_NUM_VIEWABLE_FILES ]
            num_inbox = service_info[ HC.SERVICE_INFO_NUM_INBOX ]
            num_archive = num_everything - num_inbox
            
            if service_type == HC.FILE_REPOSITORY:
                
                ( num_local, ) = self._c.execute( 'SELECT COUNT( * ) FROM current_files AS remote_current_files, current_files ON ( remote_current_files.hash_id = current_files.hash_id ) WHERE remote_current_files.service_id = ? AND current_files.service_id = ?;', ( service_id, self._combined_local_file_service_id ) ).fetchone()
                
                num_not_local = num_everything - num_local
                
                num_archive = num_local - num_inbox
                
            
            predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = num_everything ) )
            
            show_inbox_and_archive = True
            
            new_options = self._controller.GetNewOptions()
            
            if new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ) and ( num_inbox == 0 or num_archive == 0 ):
                
                show_inbox_and_archive = False
                
            
            if show_inbox_and_archive:
                
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX, min_current_count = num_inbox ) )
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, min_current_count = num_archive ) )
                
            
            if service_type == HC.FILE_REPOSITORY:
                
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LOCAL, min_current_count = num_local ) )
                predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, min_current_count = num_not_local ) )
                
            
            predicates.extend( [ ClientSearch.Predicate( predicate_type ) for predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_UNTAGGED, HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_SIZE, HC.PREDICATE_TYPE_SYSTEM_AGE, HC.PREDICATE_TYPE_SYSTEM_HASH, HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS, HC.PREDICATE_TYPE_SYSTEM_DURATION, HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, HC.PREDICATE_TYPE_SYSTEM_MIME ] ] )
            
            ratings_service_ids = self._GetServiceIds( HC.RATINGS_SERVICES )
            
            if len( ratings_service_ids ) > 0: predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_RATING ) )
            
            predicates.extend( [ ClientSearch.Predicate( predicate_type ) for predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE ] ] )
            
        
        return predicates
        
    
    def _GetHash( self, hash_id ):
        
        result = self._c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'File hash error in database' )
            
        
        ( hash, ) = result
        
        return hash
        
    
    def _GetHashes( self, hash_ids ): return [ hash for ( hash, ) in self._c.execute( 'SELECT hash FROM hashes WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) ]
    
    def _GetHashId( self, hash ):
        
        result = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( sqlite3.Binary( hash ), ) )
            
            hash_id = self._c.lastrowid
            
        else: ( hash_id, ) = result
        
        return hash_id
        
    
    def _GetHashIds( self, hashes ):
        
        hash_ids = set()
        hashes_not_in_db = set()
        
        for hash in hashes:
            
            if hash is None:
                
                continue
                
            
            result = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
            
            if result is None:
                
                hashes_not_in_db.add( hash )
                
            else:
                
                ( hash_id, ) = result
                
                hash_ids.add( hash_id )
                
            
        
        if len( hashes_not_in_db ) > 0:
            
            self._c.executemany( 'INSERT INTO hashes ( hash ) VALUES ( ? );', ( ( sqlite3.Binary( hash ), ) for hash in hashes_not_in_db ) )
            
            for hash in hashes_not_in_db:
                
                ( hash_id, ) = self._c.execute( 'SELECT hash_id FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
                
                hash_ids.add( hash_id )
                
            
        
        return hash_ids
        
    
    def _GetHashIdsFromNamespace( self, file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ):
        
        if not self._NamespaceExists( namespace ):
            
            return set()
            
        
        file_service_id = self._GetServiceId( file_service_key )
        tag_service_id = self._GetServiceId( tag_service_key )
        namespace_id = self._GetNamespaceId( namespace )
        
        current_selects = []
        pending_selects = []
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ tag_service_id ]
            
        
        for search_tag_service_id in search_tag_service_ids:
            
            ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
            
            if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                
                current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id = ' + str( namespace_id ) + ';' )
                pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id = ' + str( namespace_id ) + ';' )
                
            else:
                
                current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE service_id = ' + str( file_service_id ) + ' AND namespace_id = ' + str( namespace_id ) + ';' )
                pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE service_id = ' + str( file_service_id ) + ' AND namespace_id = ' + str( namespace_id ) + ';' )
                
            
        
        hash_ids = set()
        
        if include_current_tags:
            
            for current_select in current_selects:
                
                hash_ids.update( ( id for ( id, ) in self._c.execute( current_select ) ) )
                
            
        
        if include_pending_tags:
            
            for pending_select in pending_selects:
                
                hash_ids.update( ( id for ( id, ) in self._c.execute( pending_select ) ) )
                
            
        
        return hash_ids
        
    
    def _GetHashIdsFromQuery( self, search_context ):
        
        self._controller.ResetIdleTimer()
        
        system_predicates = search_context.GetSystemPredicates()
        
        file_service_key = search_context.GetFileServiceKey()
        tag_service_key = search_context.GetTagServiceKey()
        
        file_service_id = self._GetServiceId( file_service_key )
        tag_service_id = self._GetServiceId( tag_service_key )
        
        file_service = self._GetService( file_service_id )
        tag_service = self._GetService( tag_service_id )
        
        file_service_type = file_service.GetServiceType()
        
        tags_to_include = search_context.GetTagsToInclude()
        tags_to_exclude = search_context.GetTagsToExclude()
        
        namespaces_to_include = search_context.GetNamespacesToInclude()
        namespaces_to_exclude = search_context.GetNamespacesToExclude()
        
        wildcards_to_include = search_context.GetWildcardsToInclude()
        wildcards_to_exclude = search_context.GetWildcardsToExclude()
        
        include_current_tags = search_context.IncludeCurrentTags()
        include_pending_tags = search_context.IncludePendingTags()
        
        #
        
        files_info_predicates = []
        
        simple_preds = system_predicates.GetSimpleInfo()
        
        # This now overrides any other predicates, including file domain
        
        if 'hash' in simple_preds:
            
            query_hash_ids = set()
            
            ( search_hash, search_hash_type ) = simple_preds[ 'hash' ]
            
            if search_hash_type != 'sha256':
                
                result = self._GetFileHashes( [ search_hash ], search_hash_type, 'sha256' )
                
                if len( result ) > 0:
                    
                    ( search_hash, ) = result
                    
                    hash_id = self._GetHashId( search_hash )
                    
                    query_hash_ids = { hash_id }
                    
                
            else:
                
                if self._HashExists( search_hash ):
                    
                    hash_id = self._GetHashId( search_hash )
                    
                    query_hash_ids = { hash_id }
                    
                
            
            return query_hash_ids
            
        
        if 'min_size' in simple_preds: files_info_predicates.append( 'size > ' + str( simple_preds[ 'min_size' ] ) )
        if 'size' in simple_preds: files_info_predicates.append( 'size = ' + str( simple_preds[ 'size' ] ) )
        if 'max_size' in simple_preds: files_info_predicates.append( 'size < ' + str( simple_preds[ 'max_size' ] ) )
        
        if 'mimes' in simple_preds:
            
            mimes = simple_preds[ 'mimes' ]
            
            if len( mimes ) == 1:
                
                ( mime, ) = mimes
                
                files_info_predicates.append( 'mime = ' + str( mime ) )
                
            else:
                
                files_info_predicates.append( 'mime IN ' + HydrusData.SplayListForDB( mimes ) )
                
            
        
        if file_service_key != CC.COMBINED_FILE_SERVICE_KEY:
            
            if 'min_timestamp' in simple_preds: files_info_predicates.append( 'timestamp >= ' + str( simple_preds[ 'min_timestamp' ] ) )
            if 'max_timestamp' in simple_preds: files_info_predicates.append( 'timestamp <= ' + str( simple_preds[ 'max_timestamp' ] ) )
            
        
        if 'min_width' in simple_preds: files_info_predicates.append( 'width > ' + str( simple_preds[ 'min_width' ] ) )
        if 'width' in simple_preds: files_info_predicates.append( 'width = ' + str( simple_preds[ 'width' ] ) )
        if 'max_width' in simple_preds: files_info_predicates.append( 'width < ' + str( simple_preds[ 'max_width' ] ) )
        
        if 'min_height' in simple_preds: files_info_predicates.append( 'height > ' + str( simple_preds[ 'min_height' ] ) )
        if 'height' in simple_preds: files_info_predicates.append( 'height = ' + str( simple_preds[ 'height' ] ) )
        if 'max_height' in simple_preds: files_info_predicates.append( 'height < ' + str( simple_preds[ 'max_height' ] ) )
        
        if 'min_num_pixels' in simple_preds: files_info_predicates.append( 'width * height > ' + str( simple_preds[ 'min_num_pixels' ] ) )
        if 'num_pixels' in simple_preds: files_info_predicates.append( 'width * height = ' + str( simple_preds[ 'num_pixels' ] ) )
        if 'max_num_pixels' in simple_preds: files_info_predicates.append( 'width * height < ' + str( simple_preds[ 'max_num_pixels' ] ) )
        
        if 'min_ratio' in simple_preds:
            
            ( ratio_width, ratio_height ) = simple_preds[ 'min_ratio' ]
            
            files_info_predicates.append( '( width * 1.0 ) / height > ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
            
        if 'ratio' in simple_preds:
            
            ( ratio_width, ratio_height ) = simple_preds[ 'ratio' ]
            
            files_info_predicates.append( '( width * 1.0 ) / height = ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
            
        if 'max_ratio' in simple_preds:
            
            ( ratio_width, ratio_height ) = simple_preds[ 'max_ratio' ]
            
            files_info_predicates.append( '( width * 1.0 ) / height < ' + str( float( ratio_width ) ) + ' / ' + str( ratio_height ) )
            
        
        if 'min_num_words' in simple_preds: files_info_predicates.append( 'num_words > ' + str( simple_preds[ 'min_num_words' ] ) )
        if 'num_words' in simple_preds:
            
            num_words = simple_preds[ 'num_words' ]
            
            if num_words == 0: files_info_predicates.append( '( num_words IS NULL OR num_words = 0 )' )
            else: files_info_predicates.append( 'num_words = ' + str( num_words ) )
            
        if 'max_num_words' in simple_preds:
            
            max_num_words = simple_preds[ 'max_num_words' ]
            
            if max_num_words == 0: files_info_predicates.append( 'num_words < ' + str( max_num_words ) )
            else: files_info_predicates.append( '( num_words < ' + str( max_num_words ) + ' OR num_words IS NULL )' )
            
        
        if 'min_duration' in simple_preds: files_info_predicates.append( 'duration > ' + str( simple_preds[ 'min_duration' ] ) )
        if 'duration' in simple_preds:
            
            duration = simple_preds[ 'duration' ]
            
            if duration == 0: files_info_predicates.append( '( duration IS NULL OR duration = 0 )' )
            else: files_info_predicates.append( 'duration = ' + str( duration ) )
            
        if 'max_duration' in simple_preds:
            
            max_duration = simple_preds[ 'max_duration' ]
            
            if max_duration == 0: files_info_predicates.append( 'duration < ' + str( max_duration ) )
            else: files_info_predicates.append( '( duration < ' + str( max_duration ) + ' OR duration IS NULL )' )
            
        
        if len( tags_to_include ) > 0 or len( namespaces_to_include ) > 0 or len( wildcards_to_include ) > 0:
            
            query_hash_ids = None
            
            if len( tags_to_include ) > 0:
                
                query_hash_ids = HydrusData.IntelligentMassIntersect( ( self._GetHashIdsFromTag( file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ) for tag in tags_to_include ) )
                
            
            if len( namespaces_to_include ) > 0:
                
                namespace_query_hash_ids = HydrusData.IntelligentMassIntersect( ( self._GetHashIdsFromNamespace( file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ) for namespace in namespaces_to_include ) )
                
                if query_hash_ids is None: query_hash_ids = namespace_query_hash_ids
                else: query_hash_ids.intersection_update( namespace_query_hash_ids )
                
            
            if len( wildcards_to_include ) > 0:
                
                wildcard_query_hash_ids = HydrusData.IntelligentMassIntersect( ( self._GetHashIdsFromWildcard( file_service_key, tag_service_key, wildcard, include_current_tags, include_pending_tags ) for wildcard in wildcards_to_include ) )
                
                if query_hash_ids is None: query_hash_ids = wildcard_query_hash_ids
                else: query_hash_ids.intersection_update( wildcard_query_hash_ids )
                
            
            if len( files_info_predicates ) > 0:
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    query_hash_ids.intersection_update( self._STI( self._c.execute( 'SELECT hash_id FROM files_info WHERE ' + ' AND '.join( files_info_predicates ) + ';' ) ) )
                    
                else:
                    
                    files_info_predicates.insert( 0, 'service_id = ' + str( file_service_id ) )
                    
                    query_hash_ids.intersection_update( self._STI( self._c.execute( 'SELECT hash_id FROM current_files NATURAL JOIN files_info WHERE ' + ' AND '.join( files_info_predicates ) + ';' ) ) )
                    
                
            
        else:
            
            if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                
                query_hash_ids = self._GetHashIdsThatHaveTags( tag_service_key, include_current_tags, include_pending_tags )
                
            else:
                
                files_info_predicates.insert( 0, 'service_id = ' + str( file_service_id ) )
                
                query_hash_ids = self._STS( self._c.execute( 'SELECT hash_id FROM current_files NATURAL JOIN files_info WHERE ' + ' AND '.join( files_info_predicates ) + ';' ) )
                
            
        
        if file_service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
            
            repo_update_hash_ids = self._STS( self._c.execute( 'SELECT hash_id FROM current_files NATURAL JOIN files_info WHERE service_id = ?;', ( self._local_update_service_id, ) ) )
            
            query_hash_ids.difference_update( repo_update_hash_ids )
            
        
        #
        
        if system_predicates.HasSimilarTo():
            
            ( similar_to_hash, max_hamming ) = system_predicates.GetSimilarTo()
            
            hash_id = self._GetHashId( similar_to_hash )
            
            similar_hash_ids = self._CacheSimilarFilesSearch( hash_id, max_hamming )
            
            query_hash_ids.intersection_update( similar_hash_ids )
            
        
        #
        
        exclude_query_hash_ids = set()
        
        for tag in tags_to_exclude: exclude_query_hash_ids.update( self._GetHashIdsFromTag( file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ) )
        
        for namespace in namespaces_to_exclude: exclude_query_hash_ids.update( self._GetHashIdsFromNamespace( file_service_key, tag_service_key, namespace, include_current_tags, include_pending_tags ) )
        
        for wildcard in wildcards_to_exclude: exclude_query_hash_ids.update( self._GetHashIdsFromWildcard( file_service_key, tag_service_key, wildcard, include_current_tags, include_pending_tags ) )
        
        query_hash_ids.difference_update( exclude_query_hash_ids )
        
        #
        
        ( file_services_to_include_current, file_services_to_include_pending, file_services_to_exclude_current, file_services_to_exclude_pending ) = system_predicates.GetFileServiceInfo()
        
        for service_key in file_services_to_include_current:
            
            service_id = self._GetServiceId( service_key )
            
            query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_include_pending:
            
            service_id = self._GetServiceId( service_key )
            
            query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_exclude_current:
            
            service_id = self._GetServiceId( service_key )
            
            query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for service_key in file_services_to_exclude_pending:
            
            service_id = self._GetServiceId( service_key )
            
            query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ) ] )
            
        
        for ( operator, value, service_key ) in system_predicates.GetRatingsPredicates():
            
            service_id = self._GetServiceId( service_key )
            
            if value == 'rated': query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            elif value == 'not rated': query_hash_ids.difference_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ?;', ( service_id, ) ) ] )
            else:
                
                # floats are a pain!
                
                if operator == u'\u2248':
                    
                    predicate = str( value * 0.8 ) + ' < rating AND rating < ' + str( value * 1.2 )
                    
                elif operator == '<':
                    
                    predicate = 'rating < ' + str( value * 0.995 )
                    
                elif operator == '>':
                    
                    predicate = 'rating > ' + str( value * 1.005 )
                    
                elif operator == '=':
                    
                    predicate = str( value * 0.995 ) + ' < rating AND rating < ' + str( value * 1.005 )
                    
                
                query_hash_ids.intersection_update( [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM local_ratings WHERE service_id = ? AND ' + predicate + ';', ( service_id, ) ) ] )
                
            
        
        #
        
        must_be_local = system_predicates.MustBeLocal() or system_predicates.MustBeArchive()
        must_not_be_local = system_predicates.MustNotBeLocal()
        must_be_inbox = system_predicates.MustBeInbox()
        must_be_archive = system_predicates.MustBeArchive()
        
        if file_service_type in HC.LOCAL_FILE_SERVICES:
            
            if must_not_be_local:
                
                query_hash_ids = set()
                
            
        elif must_be_local or must_not_be_local:
            
            local_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?;', ( self._combined_local_file_service_id, ) ) )
            
            if must_be_local:
                
                query_hash_ids.intersection_update( local_hash_ids )
                
            elif must_not_be_local:
                
                query_hash_ids.difference_update( local_hash_ids )
                
            
        
        if must_be_inbox:
            
            query_hash_ids.intersection_update( self._inbox_hash_ids )
            
        elif must_be_archive:
            
            query_hash_ids.difference_update( self._inbox_hash_ids )
            
        
        #
        
        num_tags_zero = False
        num_tags_nonzero = False
        
        tag_predicates = []
        
        if 'min_num_tags' in simple_preds:
            
            min_num_tags = simple_preds[ 'min_num_tags' ]
            
            if min_num_tags == 0:
                
                num_tags_nonzero = True
                
            else:
                
                tag_predicates.append( lambda x: x > min_num_tags )
                
            
        
        if 'num_tags' in simple_preds:
            
            num_tags = simple_preds[ 'num_tags' ]
            
            if num_tags == 0:
                
                num_tags_zero = True
                
            else:
                
                tag_predicates.append( lambda x: x == num_tags )
                
            
        
        if 'max_num_tags' in simple_preds:
            
            max_num_tags = simple_preds[ 'max_num_tags' ]
            
            if max_num_tags == 1:
                
                num_tags_zero = True
                
            else:
                
                tag_predicates.append( lambda x: x < max_num_tags )
                
            
        
        tag_predicates_care_about_zero_counts = len( tag_predicates ) > 0 and False not in ( pred( 0 ) for pred in tag_predicates )
        
        if num_tags_zero or num_tags_nonzero or tag_predicates_care_about_zero_counts:
            
            nonzero_tag_query_hash_ids = self._GetHashIdsThatHaveTags( tag_service_key, include_current_tags, include_pending_tags, query_hash_ids )
            
            if num_tags_zero:
                
                query_hash_ids.difference_update( nonzero_tag_query_hash_ids )
                
            elif num_tags_nonzero:
                
                query_hash_ids.intersection_update( nonzero_tag_query_hash_ids )
                
            
        
        if len( tag_predicates ) > 0:
            
            hash_id_tag_counts = self._GetHashIdsTagCounts( tag_service_key, include_current_tags, include_pending_tags, query_hash_ids )
            
            good_tag_count_hash_ids = { id for ( id, count ) in hash_id_tag_counts if False not in ( pred( count ) for pred in tag_predicates ) }
            
            if tag_predicates_care_about_zero_counts:
                
                zero_hash_ids = query_hash_ids.difference( nonzero_tag_query_hash_ids )
                
                good_tag_count_hash_ids.update( zero_hash_ids )
                
            
            query_hash_ids.intersection_update( good_tag_count_hash_ids )
            
        
        #
        
        limit = system_predicates.GetLimit()
        
        if limit is not None and limit <= len( query_hash_ids ):
            
            query_hash_ids = random.sample( query_hash_ids, limit )
            
        else:
            
            query_hash_ids = list( query_hash_ids )
            
        
        return query_hash_ids
        
    
    def _GetHashIdsFromTag( self, file_service_key, tag_service_key, tag, include_current_tags, include_pending_tags ):
        
        siblings_manager = self._controller.GetManager( 'tag_siblings' )
        
        tags = siblings_manager.GetAllSiblings( tag_service_key, tag )
        
        file_service_id = self._GetServiceId( file_service_key )
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ self._GetServiceId( tag_service_key ) ]
            
        
        hash_ids = set()
        
        for tag in tags:
            
            current_selects = []
            pending_selects = []
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace != '':
                
                if not self._TagExists( tag ):
                    
                    continue
                    
                
                namespace_id = self._GetNamespaceId( namespace )
                subtag_id = self._GetSubtagId( subtag )
                
                for search_tag_service_id in search_tag_service_ids:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                    
                    if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                        
                        current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id = ' + str( namespace_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id = ' + str( namespace_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        
                    else:
                        
                        current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND namespace_id = ' + str( namespace_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND namespace_id = ' + str( namespace_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        
                    
                
            else:
                
                if not self._SubtagExists( subtag ):
                    
                    continue
                    
                
                subtag_id = self._GetSubtagId( subtag )
                
                for search_tag_service_id in search_tag_service_ids:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                    
                    if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                        
                        current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN tags WHERE subtag_id = ' + str( subtag_id ) + ';' )
                        pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN tags WHERE subtag_id = ' + str( subtag_id ) + ';' )
                        
                    else:
                        
                        current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND subtag_id = ' + str( subtag_id ) + ';' )
                        
                    
                
            
            if include_current_tags:
                
                for current_select in current_selects:
                    
                    hash_ids.update( ( id for ( id, ) in self._c.execute( current_select ) ) )
                    
                
            
            if include_pending_tags:
                
                for pending_select in pending_selects:
                    
                    hash_ids.update( ( id for ( id, ) in self._c.execute( pending_select ) ) )
                    
                
            
        
        return hash_ids
        
    
    def _GetHashIdsFromWildcard( self, file_service_key, tag_service_key, wildcard, include_current_tags, include_pending_tags ):
        
        def GetNamespaceIdsFromWildcard( w ):
            
            if '*' in w:
                
                like_param = ConvertWildcardToSQLiteLikeParameter( w )
                
                return [ namespace_id for ( namespace_id, ) in self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace LIKE ?;', ( like_param, ) ) ]
                
            else:
                
                if self._NamespaceExists( w ):
                    
                    namespace_id = self._GetNamespaceId( w )
                    
                    return [ namespace_id ]
                    
                else:
                    
                    return []
                    
                
            
        
        def GetSubtagIdsFromWildcard( w ):
            
            if '*' in w:
                
                like_param = ConvertWildcardToSQLiteLikeParameter( w )
                
                return [ subtag_id for ( subtag_id, ) in self._c.execute( 'SELECT subtag_id FROM subtags WHERE subtag LIKE ?;', ( like_param, ) ) ]
                
            else:
                
                if self._SubtagExists( w ):
                    
                    subtag_id = self._GetSubtagId( w )
                    
                    return [ subtag_id ]
                    
                else:
                    
                    return []
                    
                
            
        
        file_service_id = self._GetServiceId( file_service_key )
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ self._GetServiceId( tag_service_key ) ]
            
        
        current_selects = []
        pending_selects = []
        
        ( namespace_wildcard, subtag_wildcard ) = HydrusTags.SplitTag( wildcard )
        
        if namespace_wildcard != '':
            
            possible_namespace_ids = GetNamespaceIdsFromWildcard( namespace_wildcard )
            possible_subtag_ids = GetSubtagIdsFromWildcard( subtag_wildcard )
            
            for search_tag_service_id in search_tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) + ' AND subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN tags WHERE namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) + ' AND subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    
                else:
                    
                    current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) + ' AND subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND namespace_id IN ' + HydrusData.SplayListForDB( possible_namespace_ids ) + ' AND subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    
                
            
        else:
            
            possible_subtag_ids = GetSubtagIdsFromWildcard( subtag_wildcard )
            
            for search_tag_service_id in search_tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN tags WHERE subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN tags WHERE subtag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    
                else:
                    
                    current_selects.append( 'SELECT hash_id FROM ' + current_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND tag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    pending_selects.append( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN current_files NATURAL JOIN tags WHERE current_files.service_id = ' + str( file_service_id ) + ' AND tag_id IN ' + HydrusData.SplayListForDB( possible_subtag_ids ) + ';' )
                    
                
            
        
        hash_ids = set()
        
        if include_current_tags:
            
            for current_select in current_selects:
                
                hash_ids.update( ( id for ( id, ) in self._c.execute( current_select ) ) )
                
            
        
        if include_pending_tags:
            
            for pending_select in pending_selects:
                
                hash_ids.update( ( id for ( id, ) in self._c.execute( pending_select ) ) )
                
            
        
        return hash_ids
        
    
    def _GetHashIdsTagCounts( self, tag_service_key, include_current, include_pending, hash_ids = None ):
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ self._GetServiceId( tag_service_key ) ]
            
        
        tags_counter = collections.Counter()
        
        if hash_ids is None:
            
            for search_tag_service_id in search_tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                
                if include_current:
                    
                    for ( hash_id, count ) in self._c.execute( 'SELECT hash_id, COUNT( DISTINCT tag_id ) FROM ' + current_mappings_table_name + ' GROUP BY hash_id;' ):
                        
                        tags_counter[ hash_id ] += count
                        
                    
                
                if include_pending:
                    
                    for ( hash_id, count ) in self._c.execute( 'SELECT hash_id, COUNT( DISTINCT tag_id ) FROM ' + pending_mappings_table_name + ' GROUP BY hash_id;' ):
                        
                        tags_counter[ hash_id ] += count
                        
                    
                
            
        else:
            
            with HydrusDB.TemporaryIntegerTable( self._c, hash_ids, 'hash_id' ) as temp_table_name:
                
                for search_tag_service_id in search_tag_service_ids:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                    
                    if include_current:
                        
                        for ( hash_id, count ) in self._c.execute( 'SELECT hash_id, COUNT( DISTINCT tag_id ) FROM ' + temp_table_name + ' NATURAL JOIN ' + current_mappings_table_name + ' GROUP BY hash_id;' ):
                            
                            tags_counter[ hash_id ] += count
                            
                        
                    
                    if include_pending:
                        
                        for ( hash_id, count ) in self._c.execute( 'SELECT hash_id, COUNT( DISTINCT tag_id ) FROM ' + temp_table_name + ' NATURAL JOIN ' + pending_mappings_table_name + ' GROUP BY hash_id;' ):
                            
                            tags_counter[ hash_id ] += count
                            
                        
                    
                
            
        
        return tags_counter.items()
        
    
    def _GetHashIdsThatHaveTags( self, tag_service_key, include_current, include_pending, hash_ids = None ):
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            search_tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
        else:
            
            search_tag_service_ids = [ self._GetServiceId( tag_service_key ) ]
            
        
        nonzero_tag_hash_ids = set()
        
        if hash_ids is None:
            
            for search_tag_service_id in search_tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                
                if include_current:
                    
                    nonzero_tag_hash_ids.update( self._STI( self._c.execute( 'SELECT DISTINCT hash_id FROM ' + current_mappings_table_name + ';' ) ) )
                    
                
                if include_pending:
                    
                    nonzero_tag_hash_ids.update( self._STI( self._c.execute( 'SELECT DISTINCT hash_id FROM ' + pending_mappings_table_name + ';' ) ) )
                    
                
            
        else:
            
            with HydrusDB.TemporaryIntegerTable( self._c, hash_ids, 'hash_id' ) as temp_table_name:
                
                for search_tag_service_id in search_tag_service_ids:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( search_tag_service_id )
                    
                    if include_current and include_pending:
                        
                        nonzero_tag_hash_ids.update( self._STI( self._c.execute( 'SELECT hash_id as h FROM ' + temp_table_name + ' WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE hash_id = h ) OR EXISTS ( SELECT 1 FROM ' + pending_mappings_table_name + ' WHERE hash_id = h );' ) ) )
                        
                    elif include_current:
                        
                        nonzero_tag_hash_ids.update( self._STI( self._c.execute( 'SELECT hash_id as h FROM ' + temp_table_name + ' WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE hash_id = h );' ) ) )
                        
                    elif include_pending:
                        
                        nonzero_tag_hash_ids.update( self._STI( self._c.execute( 'SELECT hash_id as h FROM ' + temp_table_name + ' WHERE EXISTS ( SELECT 1 FROM ' + pending_mappings_table_name + ' WHERE hash_id = h );' ) ) )
                        
                    
                
            
        
        return nonzero_tag_hash_ids
        
    
    def _GetHashIdsToHashes( self, hash_ids ):
        
        # this is actually a bit faster than saying "hash_id IN ( bigass_list )"
        
        results = {}
        
        for hash_id in hash_ids:
            
            ( hash, ) = self._c.execute( 'SELECT hash FROM hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
            
            results[ hash_id ] = hash
            
        
        return results
        
    
    def _GetHashIdStatus( self, hash_id ):
    
        result = self._c.execute( 'SELECT 1 FROM deleted_files WHERE service_id = ? AND hash_id = ?;', ( self._combined_local_file_service_id, hash_id ) ).fetchone()
        
        if result is not None:
            
            return ( CC.STATUS_DELETED, None )
            
        
        result = self._c.execute( 'SELECT 1 FROM current_files WHERE service_id = ? AND hash_id = ?;', ( self._trash_service_id, hash_id ) ).fetchone()
        
        if result is not None:
            
            return ( CC.STATUS_DELETED, None )
            
        
        result = self._c.execute( 'SELECT 1 FROM current_files WHERE service_id = ? AND hash_id = ?;', ( self._combined_local_file_service_id, hash_id ) ).fetchone()
        
        if result is not None:
            
            hash = self._GetHash( hash_id )
            
            return ( CC.STATUS_REDUNDANT, hash )
            
        
        return ( CC.STATUS_NEW, None )
        
    
    def _GetHydrusSessions( self ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM hydrus_sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        results = self._c.execute( 'SELECT service_id, session_key, expiry FROM hydrus_sessions;' ).fetchall()
        
        for ( service_id, session_key, expires ) in results:
            
            service = self._GetService( service_id )
            
            service_key = service.GetServiceKey()
            
            sessions.append( ( service_key, session_key, expires ) )
            
        
        return sessions
        
    
    def _GetJSONDump( self, dump_type ):
        
        ( version, dump ) = self._c.execute( 'SELECT version, dump FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) ).fetchone()
        
        serialisable_info = json.loads( dump )
        
        return HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, version, serialisable_info ) )
        
    
    
    def _GetJSONDumpNamed( self, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            results = self._c.execute( 'SELECT dump_name, version, dump FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) ).fetchall()
            
            objs = []
            
            for ( dump_name, version, dump ) in results:
                
                serialisable_info = json.loads( dump )
                
                objs.append( HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, dump_name, version, serialisable_info ) ) )
                
            
            return objs
            
        else:
            
            ( version, dump ) = self._c.execute( 'SELECT version, dump FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) ).fetchone()
            
            serialisable_info = json.loads( dump )
            
            return HydrusSerialisable.CreateFromSerialisableTuple( ( dump_type, dump_name, version, serialisable_info ) )
            
        
    
    def _GetJSONDumpNames( self, dump_type ):
        
        names = [ name for ( name, ) in self._c.execute( 'SELECT dump_name FROM json_dumps_named WHERE dump_type = ?;', ( dump_type, ) ) ]
        
        return names
        
    
    def _GetJSONSimple( self, name ):
        
        result = self._c.execute( 'SELECT dump FROM json_dict WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            return None
            
        
        ( json_dump, ) = result
        
        value = json.loads( json_dump )
        
        return value
        
    
    def _GetKnownURLs( self, hash ):
        
        hash_id = self._GetHashId( hash )
        
        urls = [ url for ( url, ) in self._c.execute( 'SELECT url FROM urls WHERE hash_id = ?;', ( hash_id, ) ) ]
        
        return urls
        
    
    def _GetMD5Status( self, md5 ):
        
        result = self._c.execute( 'SELECT hash_id FROM local_hashes WHERE md5 = ?;', ( sqlite3.Binary( md5 ), ) ).fetchone()
        
        if result is None:
            
            return ( CC.STATUS_NEW, None )
            
        else:
            
            ( hash_id, ) = result
            
            return self._GetHashIdStatus( hash_id )
            
        
    
    def _GetMediaResults( self, hash_ids ):
        
        # get first detailed results
        
        with HydrusDB.TemporaryIntegerTable( self._c, hash_ids, 'hash_id' ) as temp_table_name:
            
            hash_ids_to_info = { hash_id : ( size, mime, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, width, height, duration, num_frames, num_words ) in self._c.execute( 'SELECT * FROM files_info NATURAL JOIN ' + temp_table_name + ';' ) }
            
            hash_ids_to_hashes = self._GetHashIdsToHashes( hash_ids )
            
            hash_ids_to_current_file_service_ids_and_timestamps = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, timestamp ) ) for ( hash_id, service_id, timestamp ) in self._c.execute( 'SELECT hash_id, service_id, timestamp FROM current_files NATURAL JOIN ' + temp_table_name + ';' ) ) )
            
            hash_ids_to_deleted_file_service_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT hash_id, service_id FROM deleted_files NATURAL JOIN ' + temp_table_name + ';' ) )
            
            hash_ids_to_pending_file_service_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT hash_id, service_id FROM file_transfers NATURAL JOIN ' + temp_table_name + ';' ) )
            
            hash_ids_to_petitioned_file_service_ids = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT hash_id, service_id FROM file_petitions NATURAL JOIN ' + temp_table_name + ';' ) )
            
            hash_ids_to_urls = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT hash_id, url FROM urls NATURAL JOIN ' + temp_table_name + ';' ) )
            
            hash_ids_to_service_ids_and_filenames = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, filename ) ) for ( hash_id, service_id, filename ) in self._c.execute( 'SELECT hash_id, service_id, filename FROM service_filenames NATURAL JOIN ' + temp_table_name + ';' ) ) )
            
            hash_ids_to_local_ratings = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in self._c.execute( 'SELECT service_id, hash_id, rating FROM local_ratings NATURAL JOIN ' + temp_table_name + ';' ) ) )
            
            tag_data = []
            
            tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
            
            for tag_service_id in tag_service_ids:
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( tag_service_id )
                
                tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_CURRENT, tag_id ) ) for ( hash_id, tag_id ) in self._c.execute( 'SELECT hash_id, tag_id FROM ' + current_mappings_table_name + ' NATURAL JOIN ' + temp_table_name + ';' ) )
                tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_DELETED, tag_id ) ) for ( hash_id, tag_id ) in self._c.execute( 'SELECT hash_id, tag_id FROM ' + deleted_mappings_table_name + ' NATURAL JOIN ' + temp_table_name + ';' ) )
                tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_PENDING, tag_id ) ) for ( hash_id, tag_id ) in self._c.execute( 'SELECT hash_id, tag_id FROM ' + pending_mappings_table_name + ' NATURAL JOIN ' + temp_table_name + ';' ) )
                tag_data.extend( ( hash_id, ( tag_service_id, HC.CONTENT_STATUS_PETITIONED, tag_id ) ) for ( hash_id, tag_id ) in self._c.execute( 'SELECT hash_id, tag_id FROM ' + petitioned_mappings_table_name + ' NATURAL JOIN ' + temp_table_name + ';' ) )
                
            
            seen_tag_ids = { tag_id for ( hash_id, ( tag_service_id, status, tag_id ) ) in tag_data }
            
            hash_ids_to_raw_tag_data = HydrusData.BuildKeyToListDict( tag_data )
            
            tag_ids_to_tags = self._GetTagIdsToTags( seen_tag_ids )
            
        
        # build it
        
        service_ids_to_service_keys = { service_id : service_key for ( service_id, service_key ) in self._c.execute( 'SELECT service_id, service_key FROM services;' ) }
        
        media_results = []
        
        tag_censorship_manager = self._controller.GetManager( 'tag_censorship' )
        
        for hash_id in hash_ids:
            
            hash = hash_ids_to_hashes[ hash_id ]
            
            #
            
            inbox = hash_id in self._inbox_hash_ids
            
            #
            
            # service_id, status, tag_id
            raw_tag_data = hash_ids_to_raw_tag_data[ hash_id ]
            
            # service_id -> ( status, tag )
            service_ids_to_tag_data = HydrusData.BuildKeyToListDict( ( ( tag_service_id, ( status, tag_ids_to_tags[ tag_id ] ) ) for ( tag_service_id, status, tag_id ) in raw_tag_data ) )
            
            service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
            
            service_keys_to_statuses_to_tags.update( { service_ids_to_service_keys[ service_id ] : HydrusData.BuildKeyToSetDict( tag_data ) for ( service_id, tag_data ) in service_ids_to_tag_data.items() } )
            
            service_keys_to_statuses_to_tags = tag_censorship_manager.FilterServiceKeysToStatusesToTags( service_keys_to_statuses_to_tags )
            
            tags_manager = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
            
            #
            
            current_file_service_keys = { service_ids_to_service_keys[ service_id ] for ( service_id, timestamp ) in hash_ids_to_current_file_service_ids_and_timestamps[ hash_id ] }
            
            deleted_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_deleted_file_service_ids[ hash_id ] }
            
            pending_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_pending_file_service_ids[ hash_id ] }
            
            petitioned_file_service_keys = { service_ids_to_service_keys[ service_id ] for service_id in hash_ids_to_petitioned_file_service_ids[ hash_id ] }
            
            urls = hash_ids_to_urls[ hash_id ]
            
            service_ids_to_filenames = HydrusData.BuildKeyToListDict( hash_ids_to_service_ids_and_filenames[ hash_id ] )
            
            service_keys_to_filenames = { service_ids_to_service_keys[ service_id ] : filenames for ( service_id, filenames ) in service_ids_to_filenames.items() }
            
            current_file_service_keys_to_timestamps = { service_ids_to_service_keys[ service_id ] : timestamp for ( service_id, timestamp ) in hash_ids_to_current_file_service_ids_and_timestamps[ hash_id ] }
            
            locations_manager = ClientMedia.LocationsManager( current_file_service_keys, deleted_file_service_keys, pending_file_service_keys, petitioned_file_service_keys, urls = urls, service_keys_to_filenames = service_keys_to_filenames, current_to_timestamps = current_file_service_keys_to_timestamps )
            
            #
            
            local_ratings = { service_ids_to_service_keys[ service_id ] : rating for ( service_id, rating ) in hash_ids_to_local_ratings[ hash_id ] }
            
            ratings_manager = ClientRatings.RatingsManager( local_ratings )
            
            #
            
            if hash_id in hash_ids_to_info:
                
                ( size, mime, width, height, duration, num_frames, num_words ) = hash_ids_to_info[ hash_id ]
                
            else:
                
                ( size, mime, width, height, duration, num_frames, num_words ) = ( None, HC.APPLICATION_UNKNOWN, None, None, None, None, None )
                
            
            media_results.append( ClientMedia.MediaResult( ( hash, inbox, size, mime, width, height, duration, num_frames, num_words, tags_manager, locations_manager, ratings_manager ) ) )
            
        
        return media_results
        
    
    def _GetMediaResultsFromHashes( self, hashes ):
        
        query_hash_ids = set( self._GetHashIds( hashes ) )
        
        return self._GetMediaResults( query_hash_ids )
        
    
    def _GetMime( self, hash_id ):
        
        result = self._c.execute( 'SELECT mime FROM files_info WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.FileMissingException( 'Did not have mime information for that file!' )
            
        
        ( mime, ) = result
        
        return mime
        
    
    def _GetNamespaceId( self, namespace ):
        
        if namespace == '':
            
            return self._null_namespace_id
            
        
        result = self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO namespaces ( namespace ) VALUES ( ? );', ( namespace, ) )
            
            namespace_id = self._c.lastrowid
            
        else:
            
            ( namespace_id, ) = result
            
        
        return namespace_id
        
    
    def _GetNumsPending( self ):
        
        services = self._GetServices( ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.IPFS ) )
        
        pendings = {}
        
        for service in services:
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            
            service_id = self._GetServiceId( service_key )
            
            if service_type in ( HC.FILE_REPOSITORY, HC.IPFS ): info_types = { HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES }
            elif service_type == HC.TAG_REPOSITORY: info_types = { HC.SERVICE_INFO_NUM_PENDING_MAPPINGS, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS }
            
            pendings[ service_key ] = self._GetServiceInfoSpecific( service_id, service_type, info_types )
            
        
        return pendings
        
    
    def _GetOptions( self ):
        
        result = self._c.execute( 'SELECT options FROM options;' ).fetchone()
        
        if result is None:
            
            options = ClientDefaults.GetClientDefaultOptions()
            
            self._c.execute( 'INSERT INTO options ( options ) VALUES ( ? );', ( options, ) )
            
        else:
            
            ( options, ) = result
            
            default_options = ClientDefaults.GetClientDefaultOptions()
            
            for key in default_options:
                
                if key not in options: options[ key ] = default_options[ key ]
                
            
        
        return options
        
    
    def _GetPending( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service = self._GetService( service_id )
        
        service_type = service.GetServiceType()
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        if service_type in HC.REPOSITORIES:
            
            if service_type == HC.TAG_REPOSITORY:
                
                # mappings
                
                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                
                pending_dict = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT tag_id, hash_id FROM ' + pending_mappings_table_name + ' ORDER BY tag_id LIMIT 100;' ) )
                
                for ( tag_id, hash_ids ) in pending_dict.items():
                    
                    tag = self._GetTag( tag_id )
                    hashes = self._GetHashes( hash_ids )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, hashes ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content )
                    
                
                petitioned_dict = HydrusData.BuildKeyToListDict( [ ( ( tag_id, reason_id ), hash_id ) for ( tag_id, hash_id, reason_id ) in self._c.execute( 'SELECT tag_id, hash_id, reason_id FROM ' + petitioned_mappings_table_name + ' ORDER BY reason_id LIMIT 100;' ) ] )
                
                for ( ( tag_id, reason_id ), hash_ids ) in petitioned_dict.items():
                    
                    tag = self._GetTag( tag_id )
                    hashes = self._GetHashes( hash_ids )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, hashes ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                    
                
                # tag parents
                
                pending = self._c.execute( 'SELECT child_tag_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT 1;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchall()
                
                for ( child_tag_id, parent_tag_id, reason_id ) in pending:
                    
                    child_tag = self._GetTag( child_tag_id )
                    parent_tag = self._GetTag( parent_tag_id )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason )
                    
                
                petitioned = self._c.execute( 'SELECT child_tag_id, parent_tag_id, reason_id FROM tag_parent_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT 100;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchall()
                
                for ( child_tag_id, parent_tag_id, reason_id ) in petitioned:
                    
                    child_tag = self._GetTag( child_tag_id )
                    parent_tag = self._GetTag( parent_tag_id )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_PARENTS, ( child_tag, parent_tag ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                    
                
                # tag siblings
                
                pending = self._c.execute( 'SELECT bad_tag_id, good_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT 100;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchall()
                
                for ( bad_tag_id, good_tag_id, reason_id ) in pending:
                    
                    bad_tag = self._GetTag( bad_tag_id )
                    good_tag = self._GetTag( good_tag_id )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, content, reason )
                    
                
                petitioned = self._c.execute( 'SELECT bad_tag_id, good_tag_id, reason_id FROM tag_sibling_petitions WHERE service_id = ? AND status = ? ORDER BY reason_id LIMIT 100;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchall()
                
                for ( bad_tag_id, good_tag_id, reason_id ) in petitioned:
                    
                    bad_tag = self._GetTag( bad_tag_id )
                    good_tag = self._GetTag( good_tag_id )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_TAG_SIBLINGS, ( bad_tag, good_tag ) )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                    
                
            elif service_type == HC.FILE_REPOSITORY:
                
                result = self._c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ).fetchone()
                
                if result is not None:
                    
                    ( hash_id, ) = result
                    
                    media_result = self._GetMediaResults( ( hash_id, ) )[ 0 ]
                    
                    return media_result
                    
                
                petitioned = HydrusData.BuildKeyToListDict( self._c.execute( 'SELECT reason_id, hash_id FROM file_petitions WHERE service_id = ? ORDER BY reason_id LIMIT 100;', ( service_id, ) ) ).items()
                
                for ( reason_id, hash_ids ) in petitioned:
                    
                    hashes = self._GetHashes( hash_ids )
                    
                    reason = self._GetText( reason_id )
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, hashes )
                    
                    client_to_server_update.AddContent( HC.CONTENT_UPDATE_PETITION, content, reason )
                    
                
            
            if client_to_server_update.HasContent():
                
                return client_to_server_update
                
            
        elif service_type == HC.IPFS:
            
            result = self._c.execute( 'SELECT hash_id FROM file_transfers WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            if result is not None:
                
                ( hash_id, ) = result
                
                media_result = self._GetMediaResults( ( hash_id, ) )[ 0 ]
                
                return media_result
                
            
            result = self._c.execute( 'SELECT hash_id FROM file_petitions WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            if result is not None:
                
                ( hash_id, ) = result
                
                hash = self._GetHash( hash_id )
                
                multihash = self._GetServiceFilename( service_id, hash_id )
                
                return ( hash, multihash )
                
            
        
        return None
        
    
    def _GetRecentTags( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        # we could be clever and do LIMIT and ORDER BY in the delete, but not all compilations of SQLite have that turned on, so let's KISS
        
        tag_ids_to_timestamp = { tag_id : timestamp for ( tag_id, timestamp ) in self._c.execute( 'SELECT tag_id, timestamp FROM recent_tags WHERE service_id = ?;', ( service_id, ) ) }
        
        def sort_key( key ):
            
            return tag_ids_to_timestamp[ key ]
            
        
        newest_first = tag_ids_to_timestamp.keys()
        
        newest_first.sort( key = sort_key, reverse = True )
        
        num_we_want = HydrusGlobals.client_controller.GetNewOptions().GetNoneableInteger( 'num_recent_tags' )
        
        if num_we_want == None:
            
            num_we_want = 20
            
        
        decayed = newest_first[ num_we_want : ]
        
        if len( decayed ) > 0:
            
            self._c.executemany( 'DELETE FROM recent_tags WHERE service_id = ? AND tag_id = ?;', ( ( service_id, tag_id ) for tag_id in decayed ) )
            
        
        sorted_recent_tag_ids = newest_first[ : num_we_want ]
        
        tag_ids_to_tags = self._GetTagIdsToTags( sorted_recent_tag_ids )
        
        sorted_recent_tags = [ tag_ids_to_tags[ tag_id ] for tag_id in sorted_recent_tag_ids ]
        
        return sorted_recent_tags
        
    
    def _GetRelatedTags( self, service_key, skip_hash, search_tags, max_results, max_time_to_take ):
        
        siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
        
        stop_time_for_finding_files = HydrusData.GetNowPrecise() + ( max_time_to_take / 2 )
        stop_time_for_finding_tags = HydrusData.GetNowPrecise() + ( max_time_to_take / 2 )
        
        search_tags = siblings_manager.CollapseTags( service_key, search_tags )
        
        service_id = self._GetServiceId( service_key )
        
        skip_hash_id = self._GetHashId( skip_hash )
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        tag_ids = [ self._GetTagId( tag ) for tag in search_tags ]
        
        random.shuffle( tag_ids )
        
        hash_ids_counter = collections.Counter()
        
        query = self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id IN ' + HydrusData.SplayListForDB( tag_ids ) + ';' )
        
        results = query.fetchmany( 100 )
        
        while len( results ) > 0:
            
            for ( hash_id, ) in results:
                
                hash_ids_counter[ hash_id ] += 1
                
            
            if HydrusData.TimeHasPassedPrecise( stop_time_for_finding_files ):
                
                break
                
            
            results = query.fetchmany( 100 )
            
        
        if skip_hash_id in hash_ids_counter:
            
            del hash_ids_counter[ skip_hash_id ]
            
        
        #
        
        if len( hash_ids_counter ) == 0:
            
            return []
            
        
        # this stuff is often 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.....
        # the 1 stuff often produces large quantities of the same very popular tag, so your search for [ 'eva', 'female' ] will produce 'touhou' because so many 2hu images have 'female'
        # so we want to do a 'soft' intersect, only picking the files that have the greatest number of shared search_tags
        # this filters to only the '2' results, which gives us eva females and their hair colour and a few choice other popular tags for that particular domain
        
        [ ( gumpf, largest_count ) ] = hash_ids_counter.most_common( 1 )
        
        hash_ids = [ hash_id for ( hash_id, count ) in hash_ids_counter.items() if count > largest_count * 0.8 ]
        
        counter = collections.Counter()
        
        random.shuffle( hash_ids )
        
        for hash_id in hash_ids:
            
            for ( tag_id, ) in self._c.execute( 'SELECT tag_id FROM ' + current_mappings_table_name + ' WHERE hash_id = ?;', ( hash_id, ) ):
                
                counter[ tag_id ] += 1
                
            
            if HydrusData.TimeHasPassedPrecise( stop_time_for_finding_tags ):
                
                break
                
            
        
        #
        
        for tag_id in tag_ids:
            
            if tag_id in counter:
                
                del counter[ tag_id ]
                
            
        
        results = counter.most_common( max_results )
        
        tags_to_counts = { self._GetTag( tag_id ) : count for ( tag_id, count ) in results }
        
        tags_to_counts = siblings_manager.CollapseTagsToCount( service_key, tags_to_counts )
        
        tags_to_do = tags_to_counts.keys()
        
        tags_to_do = { tag for tag in tags_to_counts if tag not in search_tags }
        
        tag_censorship_manager = self._controller.GetManager( 'tag_censorship' )
        
        filtered_tags = tag_censorship_manager.FilterTags( service_key, tags_to_do )
        
        inclusive = True
        pending_count = 0
        
        predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive, tags_to_counts[ tag ], pending_count ) for tag in filtered_tags ]
        
        return predicates
        
    
    def _GetRepositoryProgress( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
        
        ( num_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + repository_updates_table_name + ';' ).fetchone()
        
        ( num_processed_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM ' + repository_updates_table_name + ' WHERE processed = ?;', ( True, ) ).fetchone()
        
        ( num_local_updates, ) = self._c.execute( 'SELECT COUNT( * ) FROM current_files NATURAL JOIN ' + repository_updates_table_name + ' WHERE service_id = ?;', ( self._local_update_service_id, ) ).fetchone()
        
        return ( num_local_updates, num_processed_updates, num_updates )
        
    
    def _GetRepositoryThumbnailHashesIDoNotHave( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        needed_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files NATURAL JOIN files_info WHERE mime IN ' + HydrusData.SplayListForDB( HC.MIMES_WITH_THUMBNAILS ) + ' and service_id = ? EXCEPT SELECT hash_id FROM remote_thumbnails WHERE service_id = ?;', ( service_id, service_id ) ) ]
        
        needed_hashes = []
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        for hash_id in needed_hash_ids:
            
            hash = self._GetHash( hash_id )
            
            if client_files_manager.LocklessHasFullSizeThumbnail( hash ):
                
                self._c.execute( 'INSERT OR IGNORE INTO remote_thumbnails ( service_id, hash_id ) VALUES ( ?, ? );', ( service_id, hash_id ) )
                
            else:
                
                needed_hashes.append( hash )
                
                if len( needed_hashes ) == 100:
                    
                    return needed_hashes
                    
                
            
        
        return needed_hashes
        
    
    def _GetRepositoryUpdateHashesIDoNotHave( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
        
        desired_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + repository_updates_table_name + ' ORDER BY update_index ASC;' ) ]
        
        existing_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?;', ( self._local_update_service_id, ) ) }
        
        needed_hash_ids = [ hash_id for hash_id in desired_hash_ids if hash_id not in existing_hash_ids ]
        
        needed_hashes = self._GetHashes( needed_hash_ids )
        
        return needed_hashes
        
    
    def _GetService( self, service_id ):
        
        if service_id in self._service_cache:
            
            service = self._service_cache[ service_id ]
            
        else:
            
            ( service_key, service_type, name, dictionary_string ) = self._c.execute( 'SELECT service_key, service_type, name, dictionary_string FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
            
            service = ClientServices.GenerateService( service_key, service_type, name, dictionary )
            
            self._service_cache[ service_id ] = service
            
        
        return service
        
    
    def _GetServiceDirectoryHashes( self, service_key, dirname ):
        
        service_id = self._GetServiceId( service_key )
        directory_id = self._GetTextId( dirname )
        
        hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) ) ]
        
        hashes = self._GetHashes( hash_ids )
        
        return hashes
        
    
    def _GetServiceDirectoriesInfo( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        incomplete_info = self._c.execute( 'SELECT directory_id, num_files, total_size, note FROM service_directories WHERE service_id = ?;', ( service_id, ) ).fetchall()
        
        info = [ ( self._GetText( directory_id ), num_files, total_size, note ) for ( directory_id, num_files, total_size, note ) in incomplete_info ]
        
        return info
        
    
    def _GetServiceFilename( self, service_id, hash_id ):
        
        result = self._c.execute( 'SELECT filename FROM service_filenames WHERE service_id = ? AND hash_id = ?;', ( service_id, hash_id ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service filename not found!' )
            
        
        ( filename, ) = result
        
        return filename
        
    
    def _GetServiceFilenames( self, service_key, hashes ):
        
        service_id = self._GetServiceId( service_key )
        hash_ids = self._GetHashIds( hashes )
        
        result = [ filename for ( filename, ) in self._c.execute( 'SELECT filename FROM service_filenames WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) ) ]
        
        result.sort()
        
        return result
        
    
    def _GetServices( self, limited_types = HC.ALL_SERVICES ):
        
        service_ids = [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ' + HydrusData.SplayListForDB( limited_types ) + ';' ) ]
        
        services = [ self._GetService( service_id ) for service_id in service_ids ]
        
        return services
        
    
    def _GetServiceId( self, service_key ):
        
        result = self._c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( service_key ), ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Service id error in database' )
            
        
        ( service_id, ) = result
        
        return service_id
        
    
    def _GetServiceIds( self, service_types ):
        
        return [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ' + HydrusData.SplayListForDB( service_types ) + ';' ) ]
        
    
    def _GetServiceInfo( self, service_key ):
        
        service_id = self._GetServiceId( service_key )
        
        service = self._GetService( service_id )
        
        service_type = service.GetServiceType()
        
        if service_type == HC.COMBINED_LOCAL_FILE:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES }
            
        elif service_type in ( HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN ):
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE }
            
        elif service_type == HC.FILE_REPOSITORY:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE, HC.SERVICE_INFO_NUM_DELETED_FILES }
            
        elif service_type == HC.IPFS:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_VIEWABLE_FILES, HC.SERVICE_INFO_TOTAL_SIZE }
            
        elif service_type == HC.LOCAL_TAG:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS }
            
        elif service_type == HC.TAG_REPOSITORY:
            
            info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_TAGS, HC.SERVICE_INFO_NUM_MAPPINGS, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS }
            
        elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
            
            info_types = { HC.SERVICE_INFO_NUM_FILES }
            
        elif service_type == HC.LOCAL_BOORU:
            
            info_types = { HC.SERVICE_INFO_NUM_SHARES }
            
        else:
            
            info_types = set()
            
        
        service_info = self._GetServiceInfoSpecific( service_id, service_type, info_types )
        
        return service_info
        
    
    def _GetServiceInfoSpecific( self, service_id, service_type, info_types ):
        
        results = { info_type : info for ( info_type, info ) in self._c.execute( 'SELECT info_type, info FROM service_info WHERE service_id = ? AND info_type IN ' + HydrusData.SplayListForDB( info_types ) + ';', ( service_id, ) ) }
        
        if len( results ) != len( info_types ):
            
            info_types_hit = results.keys()
            
            info_types_missed = info_types.difference( info_types_hit )
            
            if service_type in HC.TAG_SERVICES:
                
                common_tag_info_types = { HC.SERVICE_INFO_NUM_FILES, HC.SERVICE_INFO_NUM_TAGS }
                
                if common_tag_info_types <= info_types_missed:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                    
                    ( num_files, num_tags ) = self._c.execute( 'SELECT COUNT( DISTINCT hash_id ), COUNT( DISTINCT tag_id ) FROM ' + current_mappings_table_name + ';' ).fetchone()
                    
                    results[ HC.SERVICE_INFO_NUM_FILES ] = num_files
                    results[ HC.SERVICE_INFO_NUM_TAGS ] = num_tags
                    
                    self._c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_FILES, num_files ) )
                    self._c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, HC.SERVICE_INFO_NUM_TAGS, num_tags ) )
                    
                    info_types_missed.difference_update( common_tag_info_types )
                    
                
            
            for info_type in info_types_missed:
                
                save_it = True
                
                if service_type in HC.FILE_SERVICES:
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_FILES, HC.SERVICE_INFO_NUM_PETITIONED_FILES ):
                        
                        save_it = False
                        
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM current_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_VIEWABLE_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM current_files NATURAL JOIN files_info WHERE service_id = ? AND mime IN ' + HydrusData.SplayListForDB( HC.SEARCHABLE_MIMES ) + ';', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_TOTAL_SIZE: result = self._c.execute( 'SELECT SUM( size ) FROM current_files NATURAL JOIN files_info WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM deleted_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM file_transfers WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM file_petitions where service_id = ?;', ( service_id, ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_INBOX: result = self._c.execute( 'SELECT COUNT( * ) FROM file_inbox NATURAL JOIN current_files WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type in HC.TAG_SERVICES:
                    
                    ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                    
                    if info_type in ( HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS, HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS, HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ):
                        
                        save_it = False
                        
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = self._c.execute( 'SELECT COUNT( DISTINCT hash_id ) FROM ' + current_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_TAGS: result = self._c.execute( 'SELECT COUNT( DISTINCT tag_id ) FROM ' + current_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_MAPPINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM ' + current_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_DELETED_MAPPINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM ' + deleted_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_MAPPINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM ' + pending_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM ' + petitioned_mappings_table_name + ';' ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS: result = self._c.execute( 'SELECT COUNT( * ) FROM tag_sibling_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS: result = self._c.execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PENDING ) ).fetchone()
                    elif info_type == HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS: result = self._c.execute( 'SELECT COUNT( * ) FROM tag_parent_petitions WHERE service_id = ? AND status = ?;', ( service_id, HC.CONTENT_STATUS_PETITIONED ) ).fetchone()
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    if info_type == HC.SERVICE_INFO_NUM_FILES: result = self._c.execute( 'SELECT COUNT( * ) FROM local_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    if info_type == HC.SERVICE_INFO_NUM_SHARES: result = self._c.execute( 'SELECT COUNT( * ) FROM yaml_dumps WHERE dump_type = ?;', ( YAML_DUMP_ID_LOCAL_BOORU, ) ).fetchone()
                    
                
                if result is None: info = 0
                else: ( info, ) = result
                
                if info is None: info = 0
                
                if save_it:
                    
                    self._c.execute( 'INSERT INTO service_info ( service_id, info_type, info ) VALUES ( ?, ?, ? );', ( service_id, info_type, info ) )
                    
                
                results[ info_type ] = info
                
            
        
        return results
        
    
    def _GetSiteId( self, name ):
        
        result = self._c.execute( 'SELECT site_id FROM imageboard_sites WHERE name = ?;', ( name, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO imageboard_sites ( name ) VALUES ( ? );', ( name, ) )
            
            site_id = self._c.lastrowid
            
        else: ( site_id, ) = result
        
        return site_id
        
    
    def _GetSubtagId( self, subtag ):
        
        result = self._c.execute( 'SELECT subtag_id FROM subtags WHERE subtag = ?;', ( subtag, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO subtags ( subtag ) VALUES ( ? );', ( subtag, ) )
            
            subtag_id = self._c.lastrowid
            
            self._c.execute( 'REPLACE INTO subtags_fts4 ( docid, subtag ) VALUES ( ?, ? );', ( subtag_id, subtag ) )
            
        else:
            
            ( subtag_id, ) = result
            
        
        return subtag_id
        
    
    def _GetTag( self, tag_id ):
        
        result = self._c.execute( 'SELECT namespace, subtag FROM tags NATURAL JOIN namespaces NATURAL JOIN subtags WHERE tag_id = ?;', ( tag_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Tag error in database' )
            
        
        ( namespace, subtag ) = result
        
        tag = HydrusTags.CombineTag( namespace, subtag )
        
        return tag
        
    
    def _GetTags( self, tag_ids ):
        
        select_statement = 'SELECT namespace, subtag FROM tags NATURAL JOIN namespaces NATURAL JOIN subtags WHERE tag_id IN %s;'
        
        results = self._SelectFromListFetchAll( select_statement, tag_ids )
        
        if len( results ) != len( tag_ids ):
            
            raise HydrusExceptions.DataMissing( 'Tag error in database' )
            
        
        tags = [ HydrusTags.CombineTag( namespace, subtag ) for ( namespace, subtag ) in results ]
        
        return tags
        
    
    def _GetTagCensorship( self, service_key = None ):
        
        if service_key is None:
            
            result = []
            
            for ( service_id, blacklist, tags ) in self._c.execute( 'SELECT service_id, blacklist, tags FROM tag_censorship;' ).fetchall():
                
                service = self._GetService( service_id )
                
                service_key = service.GetServiceKey()
                
                result.append( ( service_key, blacklist, tags ) )
                
            
        else:
            
            service_id = self._GetServiceId( service_key )
            
            result = self._c.execute( 'SELECT blacklist, tags FROM tag_censorship WHERE service_id = ?;', ( service_id, ) ).fetchone()
            
            if result is None: result = ( True, [] )
            
        
        return result
        
    
    def _GetTagId( self, tag ):
        
        tag = HydrusTags.CleanTag( tag )
        
        HydrusTags.CheckTagNotEmpty( tag )
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        namespace_id = self._GetNamespaceId( namespace )
        subtag_id = self._GetSubtagId( subtag )
        
        result = self._c.execute( 'SELECT tag_id FROM tags WHERE namespace_id = ? AND subtag_id = ?;', ( namespace_id, subtag_id ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO tags ( namespace_id, subtag_id ) VALUES ( ?, ? );', ( namespace_id, subtag_id ) )
            
            tag_id = self._c.lastrowid
            
        else:
            
            ( tag_id, ) = result
            
        
        return tag_id
        
    
    def _GetTagIdsToTags( self, tag_ids ):
        
        select_statement = 'SELECT tag_id, namespace, subtag FROM tags NATURAL JOIN namespaces NATURAL JOIN subtags WHERE tag_id IN %s;'
        
        return { tag_id : HydrusTags.CombineTag( namespace, subtag ) for ( tag_id, namespace, subtag ) in self._SelectFromList( select_statement, tag_ids ) }
        
    
    def _GetTagParents( self, service_key = None ):
        
        tag_censorship_manager = self._controller.GetManager( 'tag_censorship' )
        
        if service_key is None:
            
            service_ids_to_statuses_and_pair_ids = HydrusData.BuildKeyToListDict( ( ( service_id, ( status, child_tag_id, parent_tag_id ) ) for ( service_id, child_tag_id, parent_tag_id, status ) in self._c.execute( 'SELECT service_id, child_tag_id, parent_tag_id, status FROM tag_parents UNION SELECT service_id, child_tag_id, parent_tag_id, status FROM tag_parent_petitions;' ) ) )
            
            service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
            
            for ( service_id, statuses_and_pair_ids ) in service_ids_to_statuses_and_pair_ids.items():
                
                service = self._GetService( service_id )
                
                service_key = service.GetServiceKey()
                
                statuses_to_pairs = HydrusData.BuildKeyToSetDict( ( ( status, ( self._GetTag( child_tag_id ), self._GetTag( parent_tag_id ) ) ) for ( status, child_tag_id, parent_tag_id ) in statuses_and_pair_ids ) )
                
                statuses_to_pairs = tag_censorship_manager.FilterStatusesToPairs( service_key, statuses_to_pairs )
                
                service_keys_to_statuses_to_pairs[ service_key ] = statuses_to_pairs
                
            
            return service_keys_to_statuses_to_pairs
            
        else:
            
            service_id = self._GetServiceId( service_key )
            
            statuses_and_pair_ids = self._c.execute( 'SELECT child_tag_id, parent_tag_id, status FROM tag_parents WHERE service_id = ? UNION SELECT child_tag_id, parent_tag_id, status FROM tag_parent_petitions WHERE service_id = ?;', ( service_id, service_id ) ).fetchall()
            
            statuses_to_pairs = HydrusData.BuildKeyToSetDict( ( ( status, ( self._GetTag( child_tag_id ), self._GetTag( parent_tag_id ) ) ) for ( child_tag_id, parent_tag_id, status ) in statuses_and_pair_ids ) )
            
            statuses_to_pairs = tag_censorship_manager.FilterStatusesToPairs( service_key, statuses_to_pairs )
            
            return statuses_to_pairs
            
        
    
    def _GetTagSiblings( self, service_key = None ):
        
        tag_censorship_manager = self._controller.GetManager( 'tag_censorship' )
        
        if service_key is None:
            
            service_ids_to_statuses_and_pair_ids = HydrusData.BuildKeyToListDict( ( ( service_id, ( status, bad_tag_id, good_tag_id ) ) for ( service_id, bad_tag_id, good_tag_id, status ) in self._c.execute( 'SELECT service_id, bad_tag_id, good_tag_id, status FROM tag_siblings UNION SELECT service_id, bad_tag_id, good_tag_id, status FROM tag_sibling_petitions;' ) ) )
            
            service_keys_to_statuses_to_pairs = collections.defaultdict( HydrusData.default_dict_set )
            
            for ( service_id, statuses_and_pair_ids ) in service_ids_to_statuses_and_pair_ids.items():
                
                service = self._GetService( service_id )
                
                service_key = service.GetServiceKey()
                
                statuses_to_pairs = HydrusData.BuildKeyToSetDict( ( ( status, ( self._GetTag( bad_tag_id ), self._GetTag( good_tag_id ) ) ) for ( status, bad_tag_id, good_tag_id ) in statuses_and_pair_ids ) )
                
                statuses_to_pairs = tag_censorship_manager.FilterStatusesToPairs( service_key, statuses_to_pairs )
                
                service_keys_to_statuses_to_pairs[ service_key ] = statuses_to_pairs
                
            
            return service_keys_to_statuses_to_pairs
            
        else:
            
            service_id = self._GetServiceId( service_key )
            
            statuses_and_pair_ids = self._c.execute( 'SELECT bad_tag_id, good_tag_id, status FROM tag_siblings WHERE service_id = ? UNION SELECT bad_tag_id, good_tag_id, status FROM tag_sibling_petitions WHERE service_id = ?;', ( service_id, service_id ) ).fetchall()
            
            statuses_to_pairs = HydrusData.BuildKeyToSetDict( ( ( status, ( self._GetTag( bad_tag_id ), self._GetTag( good_tag_id ) ) ) for ( bad_tag_id, good_tag_id, status ) in statuses_and_pair_ids ) )
            
            statuses_to_pairs = tag_censorship_manager.FilterStatusesToPairs( service_key, statuses_to_pairs )
            
            return statuses_to_pairs
            
        
    
    def _GetText( self, text_id ):
        
        result = self._c.execute( 'SELECT text FROM texts WHERE text_id = ?;', ( text_id, ) ).fetchone()
        
        if result is None:
            
            raise HydrusExceptions.DataMissing( 'Text lookup error in database' )
            
        
        ( text, ) = result
        
        return text
        
    
    def _GetTextId( self, text ):
        
        result = self._c.execute( 'SELECT text_id FROM texts WHERE text = ?;', ( text, ) ).fetchone()
        
        if result is None:
            
            self._c.execute( 'INSERT INTO texts ( text ) VALUES ( ? );', ( text, ) )
            
            text_id = self._c.lastrowid
            
        else:
            
            ( text_id, ) = result
            
        
        return text_id
        
    
    def _GetTrashHashes( self, limit = None, minimum_age = None ):
        
        if limit is None:
            
            limit_phrase = ''
            
        else:
            
            limit_phrase = ' LIMIT ' + str( limit )
            
        
        if minimum_age is None:
            
            age_phrase = ''
            
        else:
            
            timestamp_cutoff = HydrusData.GetNow() - minimum_age
            
            age_phrase = ' AND timestamp < ' + str( timestamp_cutoff ) + ' ORDER BY timestamp ASC'
            
        
        hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE service_id = ?' + age_phrase + limit_phrase + ';', ( self._trash_service_id, ) ) }
        
        if HydrusGlobals.db_report_mode:
            
            message = 'When asked for '
            
            if limit is None:
                
                message += 'all the'
                
            else:
                
                message += 'at most ' + HydrusData.ConvertIntToPrettyString( limit )
                
            
            message += ' trash files,'
            
            if minimum_age is not None:
                
                message += ' with minimum age ' + HydrusData.ConvertTimestampToPrettyAge( timestamp_cutoff ) + ','
                
            
            message += ' I found ' + HydrusData.ConvertIntToPrettyString( len( hash_ids ) ) + '.'
            
            HydrusData.ShowText( message )
            
        
        return self._GetHashes( hash_ids )
        
    
    def _GetURLStatus( self, url ):
        
        result = self._c.execute( 'SELECT hash_id FROM urls WHERE url = ?;', ( url, ) ).fetchone()
        
        if result is None:
            
            return ( CC.STATUS_NEW, None )
            
        else:
            
            ( hash_id, ) = result
            
            return self._GetHashIdStatus( hash_id )
            
        
    
    def _GetWebSessions( self ):
        
        now = HydrusData.GetNow()
        
        self._c.execute( 'DELETE FROM web_sessions WHERE ? > expiry;', ( now, ) )
        
        sessions = []
        
        sessions = self._c.execute( 'SELECT name, cookies, expiry FROM web_sessions;' ).fetchall()
        
        return sessions
        
    
    def _GetYAMLDump( self, dump_type, dump_name = None ):
        
        if dump_name is None:
            
            result = { dump_name : data for ( dump_name, data ) in self._c.execute( 'SELECT dump_name, dump FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) }
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
                
                result = { dump_name.decode( 'hex' ) : data for ( dump_name, data ) in result.items() }
                
            
        else:
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION and dump_name in self._subscriptions_cache: return self._subscriptions_cache[ dump_name ]
            
            if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
            
            result = self._c.execute( 'SELECT dump FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) ).fetchone()
            
            if result is None:
                
                if result is None:
                    
                    raise HydrusExceptions.DataMissing( dump_name + ' was not found!' )
                    
                
            else: ( result, ) = result
            
            if dump_type == YAML_DUMP_ID_SUBSCRIPTION: self._subscriptions_cache[ dump_name ] = result
            
        
        return result
        
    
    def _GetYAMLDumpNames( self, dump_type ):
        
        names = [ name for ( name, ) in self._c.execute( 'SELECT dump_name FROM yaml_dumps WHERE dump_type = ?;', ( dump_type, ) ) ]
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            names = [ name.decode( 'hex' ) for name in names ]
            
        
        return names
        
    
    def _HashExists( self, hash ):
        
        result = self._c.execute( 'SELECT 1 FROM hashes WHERE hash = ?;', ( sqlite3.Binary( hash ), ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _ImportFile( self, temp_path, import_file_options = None, override_deleted = False, url = None ):
        
        if import_file_options is None:
            
            import_file_options = ClientDefaults.GetDefaultImportFileOptions()
            
        
        ( archive, exclude_deleted_files, min_size, min_resolution ) = import_file_options.ToTuple()
        
        HydrusImageHandling.ConvertToPngIfBmp( temp_path )
        
        hash = HydrusFileHandling.GetHashFromPath( temp_path )
        
        hash_id = self._GetHashId( hash )
        
        if url is not None:
            
            self._c.execute( 'INSERT OR IGNORE INTO urls ( url, hash_id ) VALUES ( ?, ? );', ( url, hash_id ) )
            
        
        ( status, status_hash ) = self._GetHashIdStatus( hash_id )
        
        if status == CC.STATUS_DELETED:
            
            if override_deleted or not exclude_deleted_files:
                
                status = CC.STATUS_NEW
                
            
        
        if status == CC.STATUS_REDUNDANT:
            
            if archive:
                
                self._ArchiveFiles( ( hash_id, ) )
                
                self.pub_content_updates_after_commit( { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, set( ( hash, ) ) ) ] } )
                
            
        elif status == CC.STATUS_NEW:
            
            ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( temp_path )
            
            if width is not None and height is not None:
                
                if min_resolution is not None:
                    
                    ( min_x, min_y ) = min_resolution
                    
                    if width < min_x or height < min_y:
                        
                        raise Exception( 'Resolution too small' )
                        
                    
                
            
            if min_size is not None:
                
                if size < min_size:
                    
                    raise Exception( 'File too small' )
                    
                
            
            timestamp = HydrusData.GetNow()
            
            client_files_manager = self._controller.GetClientFilesManager()
            
            if mime in HC.MIMES_WITH_THUMBNAILS:
                
                thumbnail = HydrusFileHandling.GenerateThumbnail( temp_path )
                
                # lockless because this db call is made by the locked client files manager
                client_files_manager.LocklessAddFullSizeThumbnail( hash, thumbnail )
                
            
            if mime in HC.MIMES_WE_CAN_PHASH:
                
                phashes = ClientImageHandling.GenerateShapePerceptualHashes( temp_path )
                
                self._CacheSimilarFilesAssociatePHashes( hash_id, phashes )
                
            
            # lockless because this db call is made by the locked client files manager
            client_files_manager.LocklessAddFile( hash, mime, temp_path )
            
            self._AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, num_words ) ], overwrite = True )
            
            self._AddFiles( self._local_file_service_id, [ ( hash_id, timestamp ) ] )
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) )
            
            self.pub_content_updates_after_commit( { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
            
            ( md5, sha1, sha512 ) = HydrusFileHandling.GetExtraHashesFromPath( temp_path )
            
            self._c.execute( 'INSERT OR IGNORE INTO local_hashes ( hash_id, md5, sha1, sha512 ) VALUES ( ?, ?, ?, ? );', ( hash_id, sqlite3.Binary( md5 ), sqlite3.Binary( sha1 ), sqlite3.Binary( sha512 ) ) )
            
            if archive:
                
                self._ArchiveFiles( ( hash_id, ) )
                
            else:
                
                self._InboxFiles( ( hash_id, ) )
                
            
            status = CC.STATUS_SUCCESSFUL
            
        
        tag_services = self._GetServices( HC.TAG_SERVICES )
        
        for service in tag_services:
            
            service_key = service.GetServiceKey()
            
            tag_archive_sync = service.GetTagArchiveSync()
            
            for ( portable_hta_path, namespaces ) in tag_archive_sync.items():
                
                hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
                
                adding = True
                
                try:
                    
                    self._SyncHashesToTagArchive( [ hash ], hta_path, service_key, adding, namespaces )
                    
                except:
                    
                    pass
                    
                
            
        
        return ( status, hash )
        
    
    def _ImportUpdate( self, update_network_string, update_hash, mime ):
        
        try:
            
            update = HydrusSerialisable.CreateFromNetworkString( update_network_string )
            
        except:
            
            HydrusData.ShowText( 'Was unable to parse an incoming update!' )
            
            raise
            
        
        hash_id = self._GetHashId( update_hash )
        
        size = len( update_network_string )
        
        width = None
        height = None
        duration = None
        num_frames = None
        num_words = None
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        # lockless because this db call is made by the locked client files manager
        client_files_manager.LocklessAddFileFromString( update_hash, mime, update_network_string )
        
        self._AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, num_words ) ], overwrite = True )
        
        now = HydrusData.GetNow()
        
        self._AddFiles( self._local_update_service_id, [ ( hash_id, now ) ] )
        
    
    def _InboxFiles( self, hash_ids ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO file_inbox VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids ) )
        
        num_added = self._GetRowCount()
        
        if num_added > 0:
            
            splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
            
            updates = self._c.execute( 'SELECT service_id, COUNT( * ) FROM current_files WHERE hash_id IN ' + splayed_hash_ids + ' GROUP BY service_id;' ).fetchall()
            
            self._c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', [ ( count, service_id, HC.SERVICE_INFO_NUM_INBOX ) for ( service_id, count ) in updates ] )
            
            self._inbox_hash_ids.update( hash_ids )
            
        
    
    def _InitCaches( self ):
        
        HydrusGlobals.client_controller.pub( 'splash_set_status_text', 'preparing db caches' )
        
        self._local_file_service_id = self._GetServiceId( CC.LOCAL_FILE_SERVICE_KEY )
        self._trash_service_id = self._GetServiceId( CC.TRASH_SERVICE_KEY )
        self._local_update_service_id = self._GetServiceId( CC.LOCAL_UPDATE_SERVICE_KEY )
        self._combined_local_file_service_id = self._GetServiceId( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        self._local_tag_service_id = self._GetServiceId( CC.LOCAL_TAG_SERVICE_KEY )
        self._combined_file_service_id = self._GetServiceId( CC.COMBINED_FILE_SERVICE_KEY )
        self._combined_tag_service_id = self._GetServiceId( CC.COMBINED_TAG_SERVICE_KEY )
        
        self._subscriptions_cache = {}
        self._service_cache = {}
        
        ( self._null_namespace_id, ) = self._c.execute( 'SELECT namespace_id FROM namespaces WHERE namespace = ?;', ( '', ) ).fetchone()
        
        self._inbox_hash_ids = { id for ( id, ) in self._c.execute( 'SELECT hash_id FROM file_inbox;' ) }
        
    
    def _InitDiskCache( self ):
        
        new_options = self._GetJSONDump( HydrusSerialisable.SERIALISABLE_TYPE_CLIENT_OPTIONS )
        
        disk_cache_init_period = new_options.GetNoneableInteger( 'disk_cache_init_period' )
        
        if disk_cache_init_period is not None:
            
            HydrusGlobals.client_controller.pub( 'splash_set_status_text', 'preparing disk cache' )
            
            stop_time = HydrusData.GetNow() + disk_cache_init_period
            
            self._LoadIntoDiskCache( stop_time = stop_time )
            
        
    
    def _InitExternalDatabases( self ):
        
        self._db_filenames[ 'external_caches' ] = 'client.caches.db'
        self._db_filenames[ 'external_mappings' ] = 'client.mappings.db'
        self._db_filenames[ 'external_master' ] = 'client.master.db'
        
    
    def _IsAnOrphan( self, test_type, possible_hash ):
        
        if self._HashExists( possible_hash ):
            
            hash = possible_hash
            
            if test_type == 'file':
                
                hash_id = self._GetHashId( hash )
                
                result = self._c.execute( 'SELECT 1 FROM current_files WHERE service_id = ? AND hash_id = ?;', ( self._combined_local_file_service_id, hash_id ) ).fetchone()
                
                if result is None:
                    
                    return True
                    
                else:
                    
                    return False
                    
                
            elif test_type == 'thumbnail':
                
                hash_id = self._GetHashId( hash )
                
                result = self._c.execute( 'SELECT 1 FROM current_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                
                if result is None:
                    
                    return True
                    
                else:
                    
                    return False
                    
                
            
        else:
            
            return True
            
        
    
    def _LoadIntoDiskCache( self, stop_time = None, caller_limit = None ):
        
        self._CloseDBCursor()
        
        try:
            
            approx_disk_cache_size = psutil.virtual_memory().available * 4 / 5
            
            disk_cache_limit = approx_disk_cache_size * 2 / 3
            
        except psutil.Error:
            
            disk_cache_limit = 512 * 1024 * 1024
            
        
        so_far_read = 0
        
        try:
            
            paths = [ os.path.join( self._db_dir, filename ) for filename in self._db_filenames.values() ]
            
            paths.sort( key = os.path.getsize )
            
            for path in paths:
                
                with open( path, 'rb' ) as f:
                    
                    while f.read( HC.READ_BLOCK_SIZE ) != '':
                        
                        if stop_time is not None and HydrusData.TimeHasPassed( stop_time ):
                            
                            return False
                            
                        
                        so_far_read += HC.READ_BLOCK_SIZE
                        
                        if so_far_read > disk_cache_limit:
                            
                            return True
                            
                        
                        if caller_limit is not None and so_far_read > caller_limit:
                            
                            return False
                            
                        
                    
                
            
        finally:
            
            self._InitDBCursor()
            
        
        return True
        
    
    def _MaintenanceDue( self, stop_time ):
        
        # vacuum
        
        new_options = self._controller.GetNewOptions()
        
        maintenance_vacuum_period_days = new_options.GetNoneableInteger( 'maintenance_vacuum_period_days' )
        
        if maintenance_vacuum_period_days is not None:
            
            stale_time_delta = maintenance_vacuum_period_days * 86400
            
            existing_names_to_timestamps = dict( self._c.execute( 'SELECT name, timestamp FROM vacuum_timestamps;' ).fetchall() )
            
            db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
            
            due_names = { name for name in db_names if name not in existing_names_to_timestamps or HydrusData.TimeHasPassed( existing_names_to_timestamps[ name ] + stale_time_delta ) }
            
            possible_due_names = set()
            
            if len( due_names ) > 0:
                
                self._CloseDBCursor()
                
                try:
                    
                    for name in due_names:
                        
                        db_path = os.path.join( self._db_dir, self._db_filenames[ name ] )
                        
                        if HydrusDB.CanVacuum( db_path, stop_time = stop_time ):
                            
                            possible_due_names.add( name )
                            
                        
                    
                    if len( possible_due_names ) > 0:
                        
                        return True
                        
                    
                finally:
                    
                    self._InitDBCursor()
                    
                
            
        
        # analyze
        
        names_to_analyze = self._GetBigTableNamesToAnalyze()
        
        if len( names_to_analyze ) > 0:
            
            return True
            
        
        return self._CacheSimilarFilesMaintenanceDue()
        
    
    def _ManageDBError( self, job, e ):
        
        if isinstance( e, MemoryError ):
            
            HydrusData.ShowText( 'The client is running out of memory! Restart it ASAP!' )
            
        
        if job.IsSynchronous():
            
            db_traceback = 'Database ' + traceback.format_exc()
            
            first_line = HydrusData.ToUnicode( type( e ).__name__ ) + ': ' + HydrusData.ToUnicode( e )
            
            new_e = HydrusExceptions.DBException( first_line, db_traceback )
            
            job.PutResult( new_e )
            
        else:
            
            HydrusData.ShowException( e )
            
        
    
    def _NamespaceExists( self, namespace ):
        
        if namespace == '':
            
            return True
            
        
        result = self._c.execute( 'SELECT 1 FROM namespaces WHERE namespace = ?;', ( namespace, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _OverwriteJSONDumps( self, dump_types, objs ):
        
        for dump_type in dump_types:
            
            self._DeleteJSONDumpNamed( dump_type )
            
        
        for obj in objs:
            
            self._SetJSONDump( obj )
            
        
    
    def _ProcessRepositoryContentUpdate( self, job_key, service_id, content_update ):
        
        FILES_CHUNK_SIZE = 20
        MAPPINGS_CHUNK_SIZE = 10000
        NEW_TAG_PARENTS_CHUNK_SIZE = 5
        
        total_rows = content_update.GetNumRows()
        
        rows_processed = 0
        
        for chunk in HydrusData.SplitListIntoChunks( content_update.GetNewFiles(), FILES_CHUNK_SIZE ):
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            files_info_rows = []
            files_rows = []
            hash_ids = []
            
            for ( service_hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in chunk:
                
                hash_id = self._CacheRepositoryNormaliseServiceHashId( service_id, service_hash_id )
                
                files_info_rows.append( ( hash_id, size, mime, width, height, duration, num_frames, num_words ) )
                
                files_rows.append( ( hash_id, timestamp ) )
                
                hash_ids.append( hash_id )
                
            
            self._AddFilesInfo( files_info_rows )
            
            self._AddFiles( service_id, files_rows )
            
            num_rows = len( files_rows )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'new files' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        for chunk in HydrusData.SplitListIntoChunks( content_update.GetDeletedFiles(), FILES_CHUNK_SIZE ):
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            service_hash_ids = chunk
            
            hash_ids = self._CacheRepositoryNormaliseServiceHashIds( service_id, service_hash_ids )
            
            self._DeleteFiles( service_id, hash_ids )
            
            num_rows = len( hash_ids )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'deleted files' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        for chunk in HydrusData.SplitMappingListIntoChunks( content_update.GetNewMappings(), MAPPINGS_CHUNK_SIZE ):
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            mappings_ids = []
            
            num_rows = 0
            
            for ( service_tag_id, service_hash_ids ) in chunk:
                
                tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_tag_id )
                hash_ids = self._CacheRepositoryNormaliseServiceHashIds( service_id, service_hash_ids )
                
                mappings_ids.append( ( tag_id, hash_ids ) )
                
                num_rows += len( service_hash_ids )
                
            
            self._UpdateMappings( service_id, mappings_ids = mappings_ids )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'new mappings' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        for chunk in HydrusData.SplitMappingListIntoChunks( content_update.GetDeletedMappings(), MAPPINGS_CHUNK_SIZE ):
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            deleted_mappings_ids = []
            
            num_rows = 0
            
            for ( service_tag_id, service_hash_ids ) in chunk:
                
                tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_tag_id )
                hash_ids = self._CacheRepositoryNormaliseServiceHashIds( service_id, service_hash_ids )
                
                deleted_mappings_ids.append( ( tag_id, hash_ids ) )
                
                num_rows += len( service_hash_ids )
                
            
            self._UpdateMappings( service_id, deleted_mappings_ids = deleted_mappings_ids )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'deleted mappings' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        for chunk in HydrusData.SplitListIntoChunks( content_update.GetNewTagParents(), NEW_TAG_PARENTS_CHUNK_SIZE ):
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            parent_ids = []
            
            for ( service_child_tag_id, service_parent_tag_id ) in chunk:
                
                child_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_child_tag_id )
                parent_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_parent_tag_id )
                
                parent_ids.append( ( child_tag_id, parent_tag_id ) )
                
            
            self._AddTagParents( service_id, parent_ids )
            
            num_rows = len( chunk )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'new tag parents' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        deleted_parents = content_update.GetDeletedTagParents()
        
        if len( deleted_parents ) > 0:
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            parent_ids = []
            
            for ( service_child_tag_id, service_parent_tag_id ) in deleted_parents:
                
                child_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_child_tag_id )
                parent_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_parent_tag_id )
                
                parent_ids.append( ( child_tag_id, parent_tag_id ) )
                
            
            self._DeleteTagParents( service_id, parent_ids )
            
            num_rows = len( deleted_parents )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'deleted tag parents' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        new_siblings = content_update.GetNewTagSiblings()
        
        if len( new_siblings ) > 0:
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            sibling_ids = []
            
            for ( service_bad_tag_id, service_good_tag_id ) in new_siblings:
                
                bad_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_bad_tag_id )
                good_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_good_tag_id )
                
                sibling_ids.append( ( bad_tag_id, good_tag_id ) )
                
            
            self._AddTagSiblings( service_id, sibling_ids )
            
            num_rows = len( new_siblings )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'new tag siblings' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
        #
        
        deleted_siblings = content_update.GetDeletedTagSiblings()
        
        if len( deleted_siblings ) > 0:
            
            precise_timestamp = HydrusData.GetNowPrecise()
            
            sibling_ids = []
            
            for ( service_bad_tag_id, service_good_tag_id ) in deleted_siblings:
                
                bad_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_bad_tag_id )
                good_tag_id = self._CacheRepositoryNormaliseServiceTagId( service_id, service_good_tag_id )
                
                sibling_ids.append( ( bad_tag_id, good_tag_id ) )
                
            
            self._DeleteTagSiblings( service_id, sibling_ids )
            
            num_rows = len( deleted_siblings )
            
            rows_processed += num_rows
            
            report_content_speed_to_job_key( job_key, rows_processed, total_rows, precise_timestamp, num_rows, 'deleted tag siblings' )
            job_key.SetVariable( 'popup_gauge_2', ( rows_processed, total_rows ) )
            
        
    
    def _ProcessRepositoryDefinitionUpdate( self, service_id, definition_update ):
        
        service_hash_ids_to_hashes = definition_update.GetHashIdsToHashes()
        
        num_rows = len( service_hash_ids_to_hashes )
        
        if num_rows > 0:
            
            self._CacheRepositoryAddHashes( service_id, service_hash_ids_to_hashes )
            
        
        service_tag_ids_to_tags = definition_update.GetTagIdsToTags()
        
        num_rows = len( service_tag_ids_to_tags )
        
        if num_rows > 0:
            
            self._CacheRepositoryAddTags( service_id, service_tag_ids_to_tags )
            
        
    
    def _ProcessContentUpdatePackage( self, service_key, content_update_package, job_key ):
        
        ( previous_journal_mode, ) = self._c.execute( 'PRAGMA journal_mode;' ).fetchone()
        
        if previous_journal_mode == 'wal' and not self._fast_big_transaction_wal:
            
            self._Commit()
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
            self._BeginImmediate()
            
        
        c_u_p_num_rows = content_update_package.GetNumRows()
        c_u_p_total_weight_processed = 0
        
        update_speed_string = u'writing\u2026'
        
        content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
        
        quit_early = False
        
        package_precise_timestamp = HydrusData.GetNowPrecise()
        
        for ( content_updates, weight ) in content_update_package.IterateContentUpdateChunks():
            
            options = self._controller.GetOptions()
            
            if options[ 'pause_repo_sync' ]:
                
                quit_early = True
                
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            if should_quit:
                
                quit_early = True
                
            
            if quit_early:
                
                package_took = HydrusData.GetNowPrecise() - package_precise_timestamp
                
                rows_s = c_u_p_total_weight_processed / package_took
                
                committing_string = 'wrote ' + HydrusData.ConvertIntToPrettyString( c_u_p_num_rows ) + ' rows at ' + HydrusData.ConvertIntToPrettyString( rows_s ) + ' rows/s - now committing to disk'
                
                job_key.SetVariable( 'popup_text_2', committing_string )
                
                HydrusData.Print( job_key.ToString() )
                
                if previous_journal_mode == 'wal' and not self._fast_big_transaction_wal:
                    
                    self._Commit()
                    
                    self._c.execute( 'PRAGMA journal_mode = WAL;' )
                    
                    self._BeginImmediate()
                    
                
                return ( False, c_u_p_total_weight_processed )
                
            
            content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
            
            self._controller.pub( 'splash_set_status_text', content_update_index_string + update_speed_string, print_to_log = False )
            job_key.SetVariable( 'popup_text_2', content_update_index_string + update_speed_string )
            
            job_key.SetVariable( 'popup_gauge_2', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
            
            chunk_precise_timestamp = HydrusData.GetNowPrecise()
            
            self._ProcessContentUpdates( { service_key : content_updates }, do_pubsubs = False )
            
            chunk_took = HydrusData.GetNowPrecise() - chunk_precise_timestamp
            
            rows_s = weight / chunk_took
            
            update_speed_string = 'writing at ' + HydrusData.ConvertIntToPrettyString( rows_s ) + ' rows/s'
            
            c_u_p_total_weight_processed += weight
            
        
        package_took = HydrusData.GetNowPrecise() - package_precise_timestamp
        
        rows_s = c_u_p_total_weight_processed / package_took
        
        committing_string = 'wrote ' + HydrusData.ConvertIntToPrettyString( c_u_p_num_rows ) + ' rows at ' + HydrusData.ConvertIntToPrettyString( rows_s ) + ' rows/s - now committing to disk'
        
        self._controller.pub( 'splash_set_status_text', committing_string )
        job_key.SetVariable( 'popup_text_2', committing_string )
        
        job_key.SetVariable( 'popup_gauge_2', ( c_u_p_num_rows, c_u_p_num_rows ) )
        
        HydrusData.Print( job_key.ToString() )
        
        if previous_journal_mode == 'wal' and not self._fast_big_transaction_wal:
            
            self._Commit()
            
            self._c.execute( 'PRAGMA journal_mode = WAL;' )
            
            self._BeginImmediate()
            
        
        return ( True, c_u_p_total_weight_processed )
        
    
    def _ProcessContentUpdates( self, service_keys_to_content_updates, do_pubsubs = True ):
        
        notify_new_downloads = False
        notify_new_pending = False
        notify_new_parents = False
        notify_new_siblings = False
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            try:
                
                service_id = self._GetServiceId( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service = self._GetService( service_id )
            
            service_type = service.GetServiceType()
            
            ultimate_mappings_ids = []
            ultimate_deleted_mappings_ids = []
            
            ultimate_pending_mappings_ids = []
            ultimate_pending_rescinded_mappings_ids = []
            
            ultimate_petitioned_mappings_ids = []
            ultimate_petitioned_rescinded_mappings_ids = []
            
            for content_update in content_updates:
                
                ( data_type, action, row ) = content_update.ToTuple()
                
                if service_type in HC.FILE_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_FILES:
                        
                        if action == HC.CONTENT_UPDATE_ADVANCED:
                            
                            ( sub_action, sub_row ) = row
                            
                            if sub_action == 'delete_deleted':
                                
                                self._c.execute( 'DELETE FROM deleted_files WHERE service_id = ?;', ( service_id, ) )
                                
                            
                            self._c.execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
                            
                        elif action == HC.CONTENT_UPDATE_ADD:
                            
                            if service_type in HC.LOCAL_FILE_SERVICES or service_type == HC.FILE_REPOSITORY:
                                
                                ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) = row
                                
                                hash_id = self._GetHashId( hash )
                                
                                self._AddFilesInfo( [ ( hash_id, size, mime, width, height, duration, num_frames, num_words ) ] )
                                
                            elif service_type == HC.IPFS:
                                
                                ( hash, multihash ) = row
                                
                                hash_id = self._GetHashId( hash )
                                
                                self._SetServiceFilename( service_id, hash_id, multihash )
                                
                                timestamp = HydrusData.GetNow()
                                
                            
                            self._AddFiles( service_id, [ ( hash_id, timestamp ) ] )
                            
                        elif action == HC.CONTENT_UPDATE_PEND:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            self._c.executemany( 'INSERT OR IGNORE INTO file_transfers ( service_id, hash_id ) VALUES ( ?, ? );', [ ( service_id, hash_id ) for hash_id in hash_ids ] )
                            
                            if service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY: notify_new_downloads = True
                            else: notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_PETITION:
                            
                            ( hashes, reason ) = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            reason_id = self._GetTextId( reason )
                            
                            self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            self._c.executemany( 'INSERT OR IGNORE INTO file_petitions ( service_id, hash_id, reason_id ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, reason_id ) for hash_id in hash_ids ] )
                            
                            notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            self._c.execute( 'DELETE FROM file_transfers WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            notify_new_pending = True
                            
                        elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            self._c.execute( 'DELETE FROM file_petitions WHERE service_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( service_id, ) )
                            
                            notify_new_pending = True
                            
                        else:
                            
                            hashes = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            if action == HC.CONTENT_UPDATE_ARCHIVE: self._ArchiveFiles( hash_ids )
                            elif action == HC.CONTENT_UPDATE_INBOX: self._InboxFiles( hash_ids )
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                deleted_hash_ids = self._DeleteFiles( service_id, hash_ids )
                                
                                if service_id == self._trash_service_id:
                                    
                                    self._DeleteFiles( self._combined_local_file_service_id, deleted_hash_ids )
                                    
                                
                            elif action == HC.CONTENT_UPDATE_UNDELETE:
                                
                                splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
                                
                                rows = self._c.execute( 'SELECT hash_id, timestamp FROM current_files WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( self._combined_local_file_service_id, ) ).fetchall()
                                
                                self._AddFiles( self._local_file_service_id, rows )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_DIRECTORIES:
                        
                        if action == HC.CONTENT_UPDATE_ADD:
                            
                            ( hashes, dirname, note ) = row
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            self._SetServiceDirectory( service_id, hash_ids, dirname, note )
                            
                        elif action == HC.CONTENT_UPDATE_DELETE:
                            
                            dirname = row
                            
                            self._DeleteServiceDirectory( service_id, dirname )
                            
                        
                    
                elif service_type in HC.TAG_SERVICES:
                    
                    if data_type == HC.CONTENT_TYPE_MAPPINGS:
                        
                        if action == HC.CONTENT_UPDATE_ADVANCED:
                            
                            ( sub_action, sub_row ) = row
                            
                            if sub_action in ( 'copy', 'delete', 'delete_deleted' ):
                                
                                self._c.execute( 'CREATE TEMPORARY TABLE temp_operation ( job_id INTEGER PRIMARY KEY AUTOINCREMENT, tag_id INTEGER, hash_id INTEGER );' )
                                
                                ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
                                
                                if sub_action == 'copy':
                                    
                                    ( tag, hashes, service_key_target ) = sub_row
                                    
                                    source_table_name = current_mappings_table_name
                                    
                                elif sub_action == 'delete':
                                    
                                    ( tag, hashes ) = sub_row
                                    
                                    source_table_name = current_mappings_table_name
                                    
                                elif sub_action == 'delete_deleted':
                                    
                                    ( tag, hashes ) = sub_row
                                    
                                    source_table_name = deleted_mappings_table_name
                                    
                                
                                predicates = []
                                
                                do_tags_join = False
                                
                                if tag is not None:
                                    
                                    ( tag_type, tag ) = tag
                                    
                                    if tag_type == 'tag':
                                        
                                        tag_id = self._GetTagId( tag )
                                        
                                        predicates.append( 'tag_id = ' + str( tag_id ) )
                                        
                                    elif tag_type == 'namespace':
                                        
                                        do_tags_join = True
                                        
                                        namespace = tag
                                        
                                        namespace_id = self._GetNamespaceId( namespace )
                                        
                                        predicates.append( 'namespace_id = ' + str( namespace_id ) )
                                        
                                    elif tag_type == 'namespaced':
                                        
                                        do_tags_join = True
                                        
                                        predicates.append( 'namespace_id != ' + str( self._null_namespace_id ) )
                                        
                                    elif tag_type == 'unnamespaced':
                                        
                                        do_tags_join = True
                                        
                                        predicates.append( 'namespace_id = ' + str( self._null_namespace_id ) )
                                        
                                    
                                
                                if do_tags_join:
                                    
                                    source_table_name = source_table_name + ' NATURAL JOIN tags'
                                    
                                
                                if hashes is not None:
                                    
                                    hash_ids = self._GetHashIds( hashes )
                                    
                                    predicates.append( 'hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) )
                                    
                                
                                if len( predicates ) == 0:
                                    
                                    self._c.execute( 'INSERT INTO temp_operation ( tag_id, hash_id ) SELECT tag_id, hash_id FROM ' + source_table_name + ';' )
                                    
                                else:
                                    
                                    self._c.execute( 'INSERT INTO temp_operation ( tag_id, hash_id ) SELECT tag_id, hash_id FROM ' + source_table_name + ' WHERE ' + ' AND '.join( predicates ) + ';' )
                                    
                                
                                num_to_do = self._GetRowCount()
                                
                                i = 0
                                
                                block_size = 1000
                                
                                while i < num_to_do:
                                    
                                    advanced_mappings_ids_flat = self._c.execute( 'SELECT tag_id, hash_id FROM temp_operation WHERE job_id BETWEEN ? AND ?;', ( i, i + block_size - 1 ) )
                                    
                                    advanced_mappings_ids = HydrusData.BuildKeyToListDict( advanced_mappings_ids_flat ).items()
                                    
                                    if sub_action == 'copy':
                                        
                                        service_id_target = self._GetServiceId( service_key_target )
                                        
                                        service_target = self._GetService( service_id_target )
                                        
                                        if service_target.GetServiceType() == HC.LOCAL_TAG:
                                            
                                            kwarg = 'mappings_ids'
                                            
                                        else:
                                            
                                            kwarg = 'pending_mappings_ids'
                                            
                                        
                                        kwargs = { kwarg : advanced_mappings_ids }
                                        
                                        self._UpdateMappings( service_id_target, **kwargs )
                                        
                                    elif sub_action == 'delete':
                                        
                                        self._UpdateMappings( service_id, deleted_mappings_ids = advanced_mappings_ids )
                                        
                                    elif sub_action == 'delete_deleted':
                                        
                                        for ( tag_id, hash_ids ) in advanced_mappings_ids:
                                            
                                            self._c.execute( 'DELETE FROM ' + deleted_mappings_table_name + ' WHERE tag_id = ? AND hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';', ( tag_id, ) )
                                            
                                        
                                        self._c.execute( 'DELETE FROM service_info WHERE service_id = ?;', ( service_id, ) )
                                        
                                    
                                    i += block_size
                                    
                                
                                self._c.execute( 'DROP TABLE temp_operation;' )
                                
                                self.pub_after_commit( 'notify_new_pending' )
                                
                            
                        else:
                            
                            if action == HC.CONTENT_UPDATE_PETITION:
                                
                                ( tag, hashes, reason ) = row
                                
                            else:
                                
                                ( tag, hashes ) = row
                                
                            
                            try:
                                
                                tag_id = self._GetTagId( tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            hash_ids = self._GetHashIds( hashes )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                ultimate_mappings_ids.append( ( tag_id, hash_ids ) )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                ultimate_deleted_mappings_ids.append( ( tag_id, hash_ids ) )
                                
                            elif action == HC.CONTENT_UPDATE_PEND:
                                
                                ultimate_pending_mappings_ids.append( ( tag_id, hash_ids ) )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                ultimate_pending_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                reason_id = self._GetTextId( reason )
                                
                                ultimate_petitioned_mappings_ids.append( ( tag_id, hash_ids, reason_id ) )
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                ultimate_petitioned_rescinded_mappings_ids.append( ( tag_id, hash_ids ) )
                                
                            
                        
                    elif data_type == HC.CONTENT_TYPE_TAG_PARENTS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self._GetTagId( child_tag )
                                
                                parent_tag_id = self._GetTagId( parent_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            pairs = ( ( child_tag_id, parent_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                special_content_updates = self._AddTagParents( service_id, pairs, make_content_updates = True )
                                
                                self.pub_content_updates_after_commit( { service_key : special_content_updates } )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self._DeleteTagParents( service_id, pairs )
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                new_status = HC.CONTENT_STATUS_PENDING
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                new_status = HC.CONTENT_STATUS_PETITIONED
                                
                            
                            ( ( child_tag, parent_tag ), reason ) = row
                            
                            try:
                                
                                child_tag_id = self._GetTagId( child_tag )
                                
                                parent_tag_id = self._GetTagId( parent_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            reason_id = self._GetTextId( reason )
                            
                            self._c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ?;', ( service_id, child_tag_id, parent_tag_id ) )
                            
                            self._c.execute( 'INSERT OR IGNORE INTO tag_parent_petitions ( service_id, child_tag_id, parent_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, child_tag_id, parent_tag_id, reason_id, new_status ) )
                            
                            notify_new_pending = True
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                deletee_status = HC.CONTENT_STATUS_PENDING
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                deletee_status = HC.CONTENT_STATUS_PETITIONED
                                
                            
                            ( child_tag, parent_tag ) = row
                            
                            try:
                                
                                child_tag_id = self._GetTagId( child_tag )
                                
                                parent_tag_id = self._GetTagId( parent_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            self._c.execute( 'DELETE FROM tag_parent_petitions WHERE service_id = ? AND child_tag_id = ? AND parent_tag_id = ? AND status = ?;', ( service_id, child_tag_id, parent_tag_id, deletee_status ) )
                            
                            notify_new_pending = True
                            
                        
                        notify_new_parents = True
                        
                    
                    elif data_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                        
                        if action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self._GetTagId( bad_tag )
                                
                                good_tag_id = self._GetTagId( good_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            pairs = ( ( bad_tag_id, good_tag_id ), )
                            
                            if action == HC.CONTENT_UPDATE_ADD:
                                
                                self._AddTagSiblings( service_id, pairs )
                                
                            elif action == HC.CONTENT_UPDATE_DELETE:
                                
                                self._DeleteTagSiblings( service_id, pairs )
                                
                            
                        elif action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_PEND:
                                
                                new_status = HC.CONTENT_STATUS_PENDING
                                
                            elif action == HC.CONTENT_UPDATE_PETITION:
                                
                                new_status = HC.CONTENT_STATUS_PETITIONED
                                
                            
                            ( ( bad_tag, good_tag ), reason ) = row
                            
                            try:
                                
                                bad_tag_id = self._GetTagId( bad_tag )
                                
                                good_tag_id = self._GetTagId( good_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            reason_id = self._GetTextId( reason )
                            
                            self._c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ?;', ( service_id, bad_tag_id ) )
                            
                            self._c.execute( 'INSERT OR IGNORE INTO tag_sibling_petitions ( service_id, bad_tag_id, good_tag_id, reason_id, status ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, bad_tag_id, good_tag_id, reason_id, new_status ) )
                            
                            notify_new_pending = True
                            
                        elif action in ( HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                            
                            if action == HC.CONTENT_UPDATE_RESCIND_PEND:
                                
                                deletee_status = HC.CONTENT_STATUS_PENDING
                                
                            elif action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                                
                                deletee_status = HC.CONTENT_STATUS_PETITIONED
                                
                            
                            ( bad_tag, good_tag ) = row
                            
                            try:
                                
                                bad_tag_id = self._GetTagId( bad_tag )
                                
                            except HydrusExceptions.SizeException:
                                
                                continue
                                
                            
                            self._c.execute( 'DELETE FROM tag_sibling_petitions WHERE service_id = ? AND bad_tag_id = ? AND status = ?;', ( service_id, bad_tag_id, deletee_status ) )
                            
                            notify_new_pending = True
                            
                        
                        notify_new_siblings = True
                        
                elif service_type in HC.RATINGS_SERVICES:
                    
                    if action == HC.CONTENT_UPDATE_ADD:
                        
                        ( rating, hashes ) = row
                        
                        hash_ids = self._GetHashIds( hashes )
                        
                        splayed_hash_ids = HydrusData.SplayListForDB( hash_ids )
                        
                        if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                            
                            ratings_added = 0
                            
                            self._c.execute( 'DELETE FROM local_ratings WHERE service_id = ? AND hash_id IN ' + splayed_hash_ids + ';', ( service_id, ) )
                            
                            ratings_added -= self._GetRowCount()
                            
                            if rating is not None:
                                
                                self._c.executemany( 'INSERT INTO local_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                                
                                ratings_added += self._GetRowCount()
                                
                            
                            self._c.execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILES ) )
                            
                            # and then do a thing here where it looks up remote services links and then pends/rescinds pends appropriately
                            
                        
                    
                
            
            if len( ultimate_mappings_ids ) + len( ultimate_deleted_mappings_ids ) + len( ultimate_pending_mappings_ids ) + len( ultimate_pending_rescinded_mappings_ids ) + len( ultimate_petitioned_mappings_ids ) + len( ultimate_petitioned_rescinded_mappings_ids ) > 0:
                
                self._UpdateMappings( service_id, mappings_ids = ultimate_mappings_ids, deleted_mappings_ids = ultimate_deleted_mappings_ids, pending_mappings_ids = ultimate_pending_mappings_ids, pending_rescinded_mappings_ids = ultimate_pending_rescinded_mappings_ids, petitioned_mappings_ids = ultimate_petitioned_mappings_ids, petitioned_rescinded_mappings_ids = ultimate_petitioned_rescinded_mappings_ids )
                
                notify_new_pending = True
                
            
        
        if do_pubsubs:
            
            if notify_new_downloads:
                
                self.pub_after_commit( 'notify_new_downloads' )
                
            if notify_new_pending:
                
                self.pub_after_commit( 'notify_new_pending' )
                
            if notify_new_siblings:
                
                self.pub_after_commit( 'notify_new_siblings_data' )
                self.pub_after_commit( 'notify_new_siblings_gui' )
                self.pub_after_commit( 'notify_new_parents' )
                
            elif notify_new_parents:
                
                self.pub_after_commit( 'notify_new_parents' )
                
            
            self.pub_content_updates_after_commit( service_keys_to_content_updates )
            
        
    
    def _ProcessRepositoryUpdates( self, service_key, only_when_idle = False, stop_time = None ):
        
        service_id = self._GetServiceId( service_key )
        
        ( name, ) = self._c.execute( 'SELECT name FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
        
        update_indices_to_unprocessed_hash_ids = HydrusData.BuildKeyToSetDict( self._c.execute( 'SELECT update_index, hash_id FROM ' + repository_updates_table_name + ' WHERE processed = ?;', ( False, ) ) )
        
        hash_ids_i_can_process = set()
        
        update_indices = update_indices_to_unprocessed_hash_ids.keys()
        
        update_indices.sort()
        
        for update_index in update_indices:
            
            unprocessed_hash_ids = update_indices_to_unprocessed_hash_ids[ update_index ]
            
            select_statement = 'SELECT hash_id FROM current_files WHERE service_id = ' + str( self._local_update_service_id ) + ' and hash_id IN %s;'
            
            local_hash_ids = { hash_id for ( hash_id, ) in self._SelectFromList( select_statement, unprocessed_hash_ids ) }
            
            if unprocessed_hash_ids == local_hash_ids:
                
                hash_ids_i_can_process.update( unprocessed_hash_ids )
                
            else:
                
                break
                
            
        
        num_updates_to_do = len( hash_ids_i_can_process )
        
        if num_updates_to_do > 0:
            
            job_key = ClientThreading.JobKey( cancellable = True, only_when_idle = only_when_idle, stop_time = stop_time )
            
            try:
                
                title = name + ' sync: processing updates'
                
                job_key.SetVariable( 'popup_title', title )
                
                HydrusData.Print( title )
                
                HydrusGlobals.client_controller.pub( 'message', job_key )
                
                status = 'loading pre-processing disk cache'
                
                self._controller.pub( 'splash_set_status_text', status, print_to_log = False )
                job_key.SetVariable( 'popup_text_1', status )
                
                stop_time = HydrusData.GetNow() + min( 5 + num_updates_to_do, 30 )
                
                self._Commit()
                
                self._LoadIntoDiskCache( stop_time = stop_time )
                
                self._BeginImmediate()
                
                num_updates_done = 0
                
                client_files_manager = self._controller.GetClientFilesManager()
                
                select_statement = 'SELECT hash_id FROM files_info WHERE mime = ' + str( HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ) + ' AND hash_id IN %s;'
                
                definition_hash_ids = [ hash_id for ( hash_id, ) in self._SelectFromList( select_statement, hash_ids_i_can_process ) ]
                
                if len( definition_hash_ids ) > 0:
                    
                    larger_precise_timestamp = HydrusData.GetNowPrecise()
                    
                    total_definitions_rows = 0
                    
                    try:
                        
                        for hash_id in definition_hash_ids:
                            
                            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                            
                            if should_quit:
                                
                                return ( True, False )
                                
                            
                            status = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( num_updates_done + 1, num_updates_to_do )
                            
                            job_key.SetVariable( 'popup_text_1', status )
                            job_key.SetVariable( 'popup_gauge_1', ( num_updates_done, num_updates_to_do ) )
                            
                            update_hash = self._GetHash( hash_id )
                            
                            update_path = client_files_manager.LocklessGetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
                            
                            with open( update_path, 'rb' ) as f:
                                
                                update_network_string = f.read()
                                
                            
                            definition_update = HydrusSerialisable.CreateFromNetworkString( update_network_string )
                            
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                            self._ProcessRepositoryDefinitionUpdate( service_id, definition_update )
                            
                            self._c.execute( 'UPDATE ' + repository_updates_table_name + ' SET processed = ? WHERE hash_id = ?;', ( True, hash_id ) )
                            
                            num_updates_done += 1
                            
                            num_rows = definition_update.GetNumRows()
                            
                            report_speed_to_job_key( job_key, precise_timestamp, num_rows, 'definitions' )
                            
                            total_definitions_rows += num_rows
                            
                        
                    finally:
                        
                        report_speed_to_log( larger_precise_timestamp, total_definitions_rows, 'definitions' )
                        
                    
                
                select_statement = 'SELECT hash_id FROM files_info WHERE mime = ' + str( HC.APPLICATION_HYDRUS_UPDATE_CONTENT ) + ' AND hash_id IN %s;'
                
                content_hash_ids = [ hash_id for ( hash_id, ) in self._SelectFromList( select_statement, hash_ids_i_can_process ) ]
                
                if len( content_hash_ids ) > 0:
                    
                    precise_timestamp = HydrusData.GetNowPrecise()
                    
                    total_content_rows = 0
                    
                    try:
                        
                        for hash_id in content_hash_ids:
                            
                            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                            
                            if should_quit:
                                
                                return ( True, False )
                                
                            
                            status = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( num_updates_done + 1, num_updates_to_do )
                            
                            job_key.SetVariable( 'popup_text_1', status )
                            job_key.SetVariable( 'popup_gauge_1', ( num_updates_done, num_updates_to_do ) )
                            
                            update_hash = self._GetHash( hash_id )
                            
                            update_path = client_files_manager.LocklessGetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
                            
                            with open( update_path, 'rb' ) as f:
                                
                                update_network_string = f.read()
                                
                            
                            content_update = HydrusSerialisable.CreateFromNetworkString( update_network_string )
                            
                            self._ProcessRepositoryContentUpdate( job_key, service_id, content_update )
                            
                            self._c.execute( 'UPDATE ' + repository_updates_table_name + ' SET processed = ? WHERE hash_id = ?;', ( True, hash_id ) )
                            
                            num_updates_done += 1
                            
                            num_rows = content_update.GetNumRows()
                            
                            total_content_rows += num_rows
                            
                        
                    finally:
                        
                        report_speed_to_log( precise_timestamp, total_content_rows, 'content rows' )
                        
                    
                
            finally:
                
                job_key.SetVariable( 'popup_text_1', 'finished' )
                job_key.DeleteVariable( 'popup_gauge_1' )
                job_key.DeleteVariable( 'popup_text_2' )
                job_key.DeleteVariable( 'popup_gauge_2' )
                
                job_key.Finish()
                job_key.Delete( 5 )
                
            
            return ( True, True )
            
        else:
            
            return ( False, True )
            
        
    
    def _PushRecentTags( self, service_key, tags ):
        
        service_id = self._GetServiceId( service_key )
        
        if tags is None:
            
            self._c.execute( 'DELETE FROM recent_tags WHERE service_id = ?;', ( service_id, ) )
            
        else:
            
            now = HydrusData.GetNow()
            
            tag_ids = [ self._GetTagId( tag ) for tag in tags ]
            
            self._c.executemany( 'REPLACE INTO recent_tags ( service_id, tag_id, timestamp ) VALUES ( ?, ?, ? );', ( ( service_id, tag_id, now ) for tag_id in tag_ids ) )
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'autocomplete_predicates': result = self._GetAutocompletePredicates( *args, **kwargs )
        elif action == 'client_files_locations': result = self._GetClientFilesLocations( *args, **kwargs )
        elif action == 'downloads': result = self._GetDownloads( *args, **kwargs )
        elif action == 'duplicate_pair': result = self._CacheSimilarFilesGetDuplicatePair( *args, **kwargs )
        elif action == 'file_hashes': result = self._GetFileHashes( *args, **kwargs )
        elif action == 'file_query_ids': result = self._GetHashIdsFromQuery( *args, **kwargs )
        elif action == 'file_system_predicates': result = self._GetFileSystemPredicates( *args, **kwargs )
        elif action == 'filter_hashes': result = self._FilterHashes( *args, **kwargs )
        elif action == 'hydrus_sessions': result = self._GetHydrusSessions( *args, **kwargs )
        elif action == 'imageboards': result = self._GetYAMLDump( YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
        elif action == 'is_an_orphan': result = self._IsAnOrphan( *args, **kwargs )
        elif action == 'known_urls': result = self._GetKnownURLs( *args, **kwargs )
        elif action == 'load_into_disk_cache': result = self._LoadIntoDiskCache( *args, **kwargs )
        elif action == 'local_booru_share_keys': result = self._GetYAMLDumpNames( YAML_DUMP_ID_LOCAL_BOORU )
        elif action == 'local_booru_share': result = self._GetYAMLDump( YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'local_booru_shares': result = self._GetYAMLDump( YAML_DUMP_ID_LOCAL_BOORU )
        elif action == 'maintenance_due': result = self._MaintenanceDue( *args, **kwargs )
        elif action == 'md5_status': result = self._GetMD5Status( *args, **kwargs )
        elif action == 'media_results': result = self._GetMediaResultsFromHashes( *args, **kwargs )
        elif action == 'media_results_from_ids': result = self._GetMediaResults( *args, **kwargs )
        elif action == 'missing_repository_update_hashes': result = self._GetRepositoryUpdateHashesIDoNotHave( *args, **kwargs )
        elif action == 'missing_thumbnail_hashes': result = self._GetRepositoryThumbnailHashesIDoNotHave( *args, **kwargs )
        elif action == 'nums_pending': result = self._GetNumsPending( *args, **kwargs )
        elif action == 'trash_hashes': result = self._GetTrashHashes( *args, **kwargs )
        elif action == 'options': result = self._GetOptions( *args, **kwargs )
        elif action == 'pending': result = self._GetPending( *args, **kwargs )
        elif action == 'recent_tags': result = self._GetRecentTags( *args, **kwargs )
        elif action == 'remote_booru': result = self._GetYAMLDump( YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
        elif action == 'remote_boorus': result = self._GetYAMLDump( YAML_DUMP_ID_REMOTE_BOORU )
        elif action == 'repository_progress': result = self._GetRepositoryProgress( *args, **kwargs )
        elif action == 'serialisable': result = self._GetJSONDump( *args, **kwargs )
        elif action == 'serialisable_simple': result = self._GetJSONSimple( *args, **kwargs )
        elif action == 'serialisable_named': result = self._GetJSONDumpNamed( *args, **kwargs )
        elif action == 'serialisable_names': result = self._GetJSONDumpNames( *args, **kwargs )
        elif action == 'service_directory': result = self._GetServiceDirectoryHashes( *args, **kwargs )
        elif action == 'service_directories': result = self._GetServiceDirectoriesInfo( *args, **kwargs )
        elif action == 'service_filenames': result = self._GetServiceFilenames( *args, **kwargs )
        elif action == 'service_info': result = self._GetServiceInfo( *args, **kwargs )
        elif action == 'services': result = self._GetServices( *args, **kwargs )
        elif action == 'similar_files_maintenance_status': result = self._CacheSimilarFilesGetMaintenanceStatus( *args, **kwargs )
        elif action == 'some_dupes': result = self._CacheSimilarFilesGetSomeDupes( *args, **kwargs )
        elif action == 'related_tags': result = self._GetRelatedTags( *args, **kwargs )
        elif action == 'tag_censorship': result = self._GetTagCensorship( *args, **kwargs )
        elif action == 'tag_parents': result = self._GetTagParents( *args, **kwargs )
        elif action == 'tag_siblings': result = self._GetTagSiblings( *args, **kwargs )
        elif action == 'url_status': result = self._GetURLStatus( *args, **kwargs )
        elif action == 'web_sessions': result = self._GetWebSessions( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _RelocateClientFiles( self, prefix, source, dest ):
        
        full_source = os.path.join( source, prefix )
        full_dest = os.path.join( dest, prefix )
        
        if os.path.exists( full_source ):
            
            HydrusPaths.MergeTree( full_source, full_dest )
            
        elif not os.path.exists( full_dest ):
            
            HydrusPaths.MakeSureDirectoryExists( full_dest )
            
        
        portable_dest = HydrusPaths.ConvertAbsPathToPortablePath( dest )
        
        self._c.execute( 'UPDATE client_files_locations SET location = ? WHERE prefix = ?;', ( portable_dest, prefix ) )
        
        if os.path.exists( full_source ):
            
            try: HydrusPaths.RecyclePath( full_source )
            except: pass
            
        
    
    def _RegenerateACCache( self ):
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', 'regenerating autocomplete cache' )
        
        self._controller.pub( 'message', job_key )
        
        tag_service_ids = self._GetServiceIds( HC.TAG_SERVICES )
        file_service_ids = self._GetServiceIds( HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES )
        
        for ( file_service_id, tag_service_id ) in itertools.product( file_service_ids, tag_service_ids ):
            
            job_key.SetVariable( 'popup_text_1', 'generating specific ac_cache ' + str( file_service_id ) + '_' + str( tag_service_id ) )
            
            self._CacheSpecificMappingsDrop( file_service_id, tag_service_id )
            
            self._CacheSpecificMappingsGenerate( file_service_id, tag_service_id )
            
        
        for tag_service_id in tag_service_ids:
            
            job_key.SetVariable( 'popup_text_1', 'generating combined files ac_cache ' + str( tag_service_id ) )
            
            self._CacheCombinedFilesMappingsDrop( tag_service_id )
            
            self._CacheCombinedFilesMappingsGenerate( tag_service_id )
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        
    
    def _ResetRepository( self, service ):
        
        self._Commit()
        
        if not self._fast_big_transaction_wal:
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
        
        self._c.execute( 'PRAGMA foreign_keys = ON;' )
        
        self._BeginImmediate()
        
        ( service_key, service_type, name, dictionary ) = service.ToTuple()
        
        service_id = self._GetServiceId( service_key )
        
        prefix = 'resetting ' + name
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', prefix + ': deleting service' )
        
        self._controller.pub( 'message', job_key )
        
        self._DeleteService( service_id )
        
        job_key.SetVariable( 'popup_text_1', prefix + ': recreating service' )
        
        self._AddService( service_key, service_type, name, dictionary )
        
        self.pub_after_commit( 'notify_unknown_accounts' )
        self.pub_after_commit( 'notify_new_pending' )
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        
        job_key.SetVariable( 'popup_text_1', prefix + ': done!' )
        
        self._Commit()
        
        self._InitDBCursor()
        
        self._BeginImmediate()
        
        job_key.Finish()
        
    
    def _SaveDirtyServices( self, dirty_services ):
        
        # if allowed to save objects
        
        self._SaveServices( dirty_services )
        
    
    def _SaveServices( self, services ):
        
        for service in services:
            
            ( service_key, service_type, name, dictionary ) = service.ToTuple()
            
            dictionary_string = dictionary.DumpToString()
            
            self._c.execute( 'UPDATE services SET dictionary_string = ? WHERE service_key = ?;', ( dictionary_string, sqlite3.Binary( service_key ) ) )
            
            service.SetClean()
            
        
    
    def _SaveOptions( self, options ):
        
        ( old_options, ) = self._c.execute( 'SELECT options FROM options;' ).fetchone()
        
        ( old_width, old_height ) = old_options[ 'thumbnail_dimensions' ]
        
        ( new_width, new_height ) = options[ 'thumbnail_dimensions' ]
        
        self._c.execute( 'UPDATE options SET options = ?;', ( options, ) )
        
        resize_thumbs = new_width != old_width or new_height != old_height
        
        if resize_thumbs:
            
            self.pub_after_commit( 'thumbnail_resize' )
            
        
        self.pub_after_commit( 'notify_new_options' )
        
    
    def _SetJSONDump( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableBaseNamed ):
            
            ( dump_type, dump_name, version, serialisable_info ) = obj.GetSerialisableTuple()
            
            try:
                
                dump = json.dumps( serialisable_info )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                HydrusData.Print( obj )
                HydrusData.Print( serialisable_info )
                
                raise Exception( 'Trying to json dump the object ' + HydrusData.ToUnicode( obj ) + ' with name ' + dump_name + ' caused an error. Its serialisable info has been dumped to the log.' )
                
            
            self._c.execute( 'DELETE FROM json_dumps_named WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
            
            self._c.execute( 'INSERT INTO json_dumps_named ( dump_type, dump_name, version, dump ) VALUES ( ?, ?, ?, ? );', ( dump_type, dump_name, version, sqlite3.Binary( dump ) ) )
            
        else:
            
            ( dump_type, version, serialisable_info ) = obj.GetSerialisableTuple()
            
            try:
                
                dump = json.dumps( serialisable_info )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                HydrusData.Print( obj )
                HydrusData.Print( serialisable_info )
                
                raise Exception( 'Trying to json dump the object ' + HydrusData.ToUnicode( obj ) + ' caused an error. Its serialisable info has been dumped to the log.' )
                
            
            self._c.execute( 'DELETE FROM json_dumps WHERE dump_type = ?;', ( dump_type, ) )
            
            self._c.execute( 'INSERT INTO json_dumps ( dump_type, version, dump ) VALUES ( ?, ?, ? );', ( dump_type, version, sqlite3.Binary( dump ) ) )
            
        
    
    def _SetJSONSimple( self, name, value ):
        
        if value is None:
            
            self._c.execute( 'DELET FROM json_dict WHERE name = ?;', ( name, ) )
            
        else:
            
            json_dump = json.dumps( value )
            
            self._c.execute( 'REPLACE INTO json_dict ( name, dump ) VALUES ( ?, ? );', ( name, sqlite3.Binary( json_dump ) ) )
            
        
    
    def _SetPassword( self, password ):
        
        if password is not None:
            
            # to convert from unusual unicode types
            password_bytes = HydrusData.ToByteString( password )
            
            password = hashlib.sha256( password_bytes ).digest()
            
        
        options = self._controller.GetOptions()
        
        options[ 'password' ] = password
        
        self._SaveOptions( options )
        
    
    def _SetServiceFilename( self, service_id, hash_id, filename ):
        
        self._c.execute( 'REPLACE INTO service_filenames ( service_id, hash_id, filename ) VALUES ( ?, ?, ? );', ( service_id, hash_id, filename ) )
        
    
    def _SetServiceDirectory( self, service_id, hash_ids, dirname, note ):
        
        directory_id = self._GetTextId( dirname )
        
        self._c.execute( 'DELETE FROM service_directories WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        self._c.execute( 'DELETE FROM service_directory_file_map WHERE service_id = ? AND directory_id = ?;', ( service_id, directory_id ) )
        
        num_files = len( hash_ids )
        
        result = self._c.execute( 'SELECT SUM( size ) FROM files_info WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ).fetchone()
        
        if result is None:
            
            total_size = 0
            
        else:
            
            ( total_size, ) = result
            
        
        self._c.execute( 'INSERT INTO service_directories ( service_id, directory_id, num_files, total_size, note ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, directory_id, num_files, total_size, note ) )
        self._c.executemany( 'INSERT INTO service_directory_file_map ( service_id, directory_id, hash_id ) VALUES ( ?, ?, ? );', ( ( service_id, directory_id, hash_id ) for hash_id in hash_ids ) )
        
    
    def _SetTagCensorship( self, info ):
        
        self._c.execute( 'DELETE FROM tag_censorship;' )
        
        for ( service_key, blacklist, tags ) in info:
            
            service_id = self._GetServiceId( service_key )
            
            tags = list( tags )
            
            self._c.execute( 'INSERT OR IGNORE INTO tag_censorship ( service_id, blacklist, tags ) VALUES ( ?, ?, ? );', ( service_id, blacklist, tags ) )
            
        
        self.pub_after_commit( 'notify_new_tag_censorship' )
        
    
    def _SetYAMLDump( self, dump_type, dump_name, data ):
        
        if dump_type == YAML_DUMP_ID_SUBSCRIPTION: self._subscriptions_cache[ dump_name ] = data
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU: dump_name = dump_name.encode( 'hex' )
        
        self._c.execute( 'DELETE FROM yaml_dumps WHERE dump_type = ? AND dump_name = ?;', ( dump_type, dump_name ) )
        
        try: self._c.execute( 'INSERT INTO yaml_dumps ( dump_type, dump_name, dump ) VALUES ( ?, ?, ? );', ( dump_type, dump_name, data ) )
        except:
            
            HydrusData.Print( ( dump_type, dump_name, data ) )
            
            raise
            
        
        if dump_type == YAML_DUMP_ID_LOCAL_BOORU:
            
            service_id = self._GetServiceId( CC.LOCAL_BOORU_SERVICE_KEY )
            
            self._c.execute( 'DELETE FROM service_info WHERE service_id = ? AND info_type = ?;', ( service_id, HC.SERVICE_INFO_NUM_SHARES ) )
            
            self._controller.pub( 'refresh_local_booru_shares' )
            
        
    
    def _SubtagExists( self, subtag ):
        
        try:
            
            HydrusTags.CheckTagNotEmpty( subtag )
            
        except HydrusExceptions.SizeException:
            
            return False
            
        
        result = self._c.execute( 'SELECT 1 FROM subtags WHERE subtag = ?;', ( subtag, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _SyncHashesToTagArchive( self, hashes, hta_path, tag_service_key, adding, namespaces ):
        
        hta = HydrusTagArchive.HydrusTagArchive( hta_path )
        
        hash_type = hta.GetHashType()
        
        content_updates = []
        
        for hash in hashes:
            
            if hash_type == HydrusTagArchive.HASH_TYPE_SHA256: archive_hash = hash
            else:
                
                hash_id = self._GetHashId( hash )
                
                if hash_type == HydrusTagArchive.HASH_TYPE_MD5: h = 'md5'
                elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: h = 'sha1'
                elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: h = 'sha512'
                
                try: ( archive_hash, ) = self._c.execute( 'SELECT ' + h + ' FROM local_hashes WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
                except: return
                
            
            tags = HydrusTags.CleanTags( hta.GetTags( archive_hash ) )
            
            desired_tags = HydrusTags.FilterNamespaces( tags, namespaces )
            
            if len( desired_tags ) > 0:
                
                if tag_service_key != CC.LOCAL_TAG_SERVICE_KEY and not adding:
                    
                    action = HC.CONTENT_UPDATE_PETITION
                    
                    rows = [ ( tag, ( hash, ), 'admin: tag archive desync' ) for tag in desired_tags ]
                    
                else:
                    
                    if adding:
                        
                        if tag_service_key == CC.LOCAL_TAG_SERVICE_KEY: action = HC.CONTENT_UPDATE_ADD
                        else: action = HC.CONTENT_UPDATE_PEND
                        
                    else: action = HC.CONTENT_UPDATE_DELETE
                    
                    rows = [ ( tag, ( hash, )  ) for tag in desired_tags ]
                    
                
                content_updates.extend( [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, action, row ) for row in rows ] )
                
            
        
        if len( content_updates ) > 0:
        
            service_keys_to_content_updates = { tag_service_key : content_updates }
            
            self._ProcessContentUpdates( service_keys_to_content_updates )
            
        
    
    def _TagExists( self, tag ):
        
        tag = HydrusTags.CleanTag( tag )
        
        try:
            
            HydrusTags.CheckTagNotEmpty( tag )
            
        except HydrusExceptions.SizeException:
            
            return False
            
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if self._NamespaceExists( namespace ):
            
            namespace_id = self._GetNamespaceId( namespace )
            
        else:
            
            return False
            
        
        if self._SubtagExists( subtag ):
            
            subtag_id = self._GetSubtagId( subtag )
            
            result = self._c.execute( 'SELECT 1 FROM tags WHERE namespace_id = ? AND subtag_id = ?;', ( namespace_id, subtag_id ) ).fetchone()
            
            if result is None:
                
                return False
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
    
    def _UpdateDB( self, version ):
        
        self._controller.pub( 'splash_set_title_text', 'updating db to v' + str( version + 1 ) )
        
        if version == 239:
            
            self._c.execute( 'DROP TABLE analyze_timestamps;' )
            
            self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, num_rows INTEGER, timestamp INTEGER );' )
            
            #
            
            self._controller.pub( 'splash_set_status_text', 'setting up next step of similar files stuff' )
            
            self._c.execute( 'CREATE TABLE external_caches.shape_search_cache ( hash_id INTEGER PRIMARY KEY, searched_distance INTEGER );' )
            
            self._c.execute( 'CREATE TABLE external_caches.duplicate_pairs ( smaller_hash_id INTEGER, larger_hash_id INTEGER, duplicate_type INTEGER, PRIMARY KEY ( smaller_hash_id, larger_hash_id ) );' )
            self._c.execute( 'CREATE UNIQUE INDEX external_caches.duplicate_pairs_reversed_hash_ids ON duplicate_pairs ( larger_hash_id, smaller_hash_id );' )
            
            combined_local_file_service_id = self._GetServiceId( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            self._c.execute( 'INSERT OR IGNORE INTO shape_search_cache SELECT hash_id, NULL FROM current_files NATURAL JOIN files_info  WHERE service_id = ? and mime IN ( ?, ? );', ( combined_local_file_service_id, HC.IMAGE_JPEG, HC.IMAGE_PNG ) )
            
        
        if version == 240:
            
            combined_local_file_service_id = self._GetServiceId( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
            self._c.execute( 'INSERT OR IGNORE INTO shape_maintenance_phash_regen SELECT hash_id FROM current_files NATURAL JOIN files_info WHERE service_id = ? AND mime IN ( ?, ? );', ( combined_local_file_service_id, HC.IMAGE_JPEG, HC.IMAGE_PNG ) )
            
            #
            
            self._c.execute( 'DELETE FROM web_sessions WHERE name = ?;', ( 'pixiv', ) )
            
        
        if version == 241:
            
            try:
                
                subscriptions = self._GetJSONDumpNamed( HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
                
                for subscription in subscriptions:
                    
                    g_i = subscription._gallery_identifier
                    
                    if g_i.GetSiteType() == HC.SITE_TYPE_BOORU:
                        
                        if 'sankaku' in g_i.GetAdditionalInfo():
                            
                            subscription._paused = True
                            
                            self._SetJSONDump( subscription )
                            
                        
                    
                
            except Exception as e:
                
                HydrusData.Print( 'While attempting to pause all sankaku subs, I had this problem:' )
                HydrusData.PrintException( e )
                
            
        
        if version == 243:
            
            mappings_path = os.path.join( self._db_dir, 'client.mappings.db' )
            
            mappings_size = os.path.getsize( mappings_path )
            
            needed_space = int( mappings_size * 1.2 )
            
            ( has_space, reason ) = HydrusPaths.HasSpaceForDBTransaction( self._db_dir, needed_space )
            
            if not has_space:
                
                message = 'The update to v244 temporarily requires a bit of free space, and I am not sure you have enough. Here is the reason my test gave:'
                message += os.linesep * 2
                message += reason
                message += os.linesep * 2
                message += 'Please free up some space and then hit ok. If you cannot free up any more space, you can either risk it (a failure is safe, it will just waste time) or kill the hydrus process now.'
                
                HydrusGlobals.client_controller.CallBlockingToWx( wx.MessageBox, message )
                
            
            # we are collapsing ( namespace_id, tag_id ) to just tag_id
            
            # first, convert existing tag_id to subtag_id
            
            self._controller.pub( 'splash_set_status_text', 'converting existing tags to subtags' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.subtags ( subtag_id INTEGER PRIMARY KEY, subtag TEXT UNIQUE );' )
            
            self._c.execute( 'INSERT INTO subtags SELECT tag_id, tag FROM tags;' )
            
            self._c.execute( 'CREATE VIRTUAL TABLE IF NOT EXISTS external_master.subtags_fts4 USING fts4( subtag );' )
            
            self._c.execute( 'INSERT INTO subtags_fts4 ( docid, subtag ) SELECT * FROM subtags;' )
            
            self._c.execute( 'DROP TABLE tags;' )
            self._c.execute( 'DROP TABLE tags_fts4;' )
            
            # now create the new tags table
            
            self._controller.pub( 'splash_set_status_text', 'creating the new tags table' )
            
            self._c.execute( 'CREATE TABLE IF NOT EXISTS external_master.tags ( tag_id INTEGER PRIMARY KEY, namespace_id INTEGER, subtag_id INTEGER );' )
            
            self._c.execute( 'INSERT INTO tags ( namespace_id, subtag_id ) SELECT namespace_id, tag_id FROM existing_tags;' )
            
            self._c.execute( 'DROP TABLE existing_tags;' )
            
            self._c.execute( 'CREATE UNIQUE INDEX external_master.tags_subtag_id_namespace_id_index ON tags ( subtag_id, namespace_id );' )
            
            # convert everything over
            
            # these tables are complicated but small, so it is worth doing ugly but simple 'just read it all into memory' solutions
            
            def get_tag_id( namespace_id, subtag_id ):
                
                result = self._c.execute( 'SELECT tag_id FROM tags WHERE namespace_id = ? AND subtag_id = ?;', ( namespace_id, subtag_id ) ).fetchone()
                
                if result is None:
                    
                    self._c.execute( 'INSERT INTO tags ( namespace_id, subtag_id ) VALUES ( ?, ? );', ( namespace_id, subtag_id, ) )
                    
                    tag_id = self._c.lastrowid
                    
                else:
                    
                    ( tag_id, ) = result
                    
                
                return tag_id
                
            
            self._controller.pub( 'splash_set_status_text', 'compacting smaller tables' )
            
            #
            
            old_data = self._c.execute( 'SELECT service_id, namespace_id, tag_id, timestamp FROM recent_tags;' ).fetchall()
            
            self._c.execute( 'DROP TABLE recent_tags;' )
            
            self._c.execute( 'CREATE TABLE recent_tags ( service_id INTEGER REFERENCES services ON DELETE CASCADE, tag_id INTEGER, timestamp INTEGER, PRIMARY KEY ( service_id, tag_id ) );' )
            
            new_inserts = []
            
            for ( service_id, namespace_id, subtag_id, timestamp ) in old_data:
                
                tag_id = get_tag_id( namespace_id, subtag_id )
                
                new_inserts.append( ( service_id, tag_id, timestamp ) )
                
            
            self._c.executemany( 'INSERT INTO recent_tags ( service_id, tag_id, timestamp ) VALUES ( ?, ?, ? );', new_inserts )
            
            #
            
            old_data = self._c.execute( 'SELECT service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status FROM tag_parents;' ).fetchall()
            
            self._c.execute( 'DROP TABLE tag_parents;' )
            
            self._c.execute( 'CREATE TABLE tag_parents ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_tag_id INTEGER, parent_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, child_tag_id, parent_tag_id, status ) );' )
            
            new_inserts = []
            
            for ( service_id, child_namespace_id, child_subtag_id, parent_namespace_id, parent_subtag_id, status ) in old_data:
                
                child_tag_id = get_tag_id( child_namespace_id, child_subtag_id )
                parent_tag_id = get_tag_id( parent_namespace_id, parent_subtag_id )
                
                new_inserts.append( ( service_id, child_tag_id, parent_tag_id, status ) )
                
            
            self._c.executemany( 'INSERT OR IGNORE INTO tag_parents ( service_id, child_tag_id, parent_tag_id, status ) VALUES ( ?, ?, ?, ? );', new_inserts )
            
            #
            
            old_data = self._c.execute( 'SELECT service_id, child_namespace_id, child_tag_id, parent_namespace_id, parent_tag_id, status, reason_id FROM tag_parent_petitions;' ).fetchall()
            
            self._c.execute( 'DROP TABLE tag_parent_petitions;' )
            
            self._c.execute( 'CREATE TABLE tag_parent_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, child_tag_id INTEGER, parent_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, child_tag_id, parent_tag_id, status ) );' )
            
            new_inserts = []
            
            for ( service_id, child_namespace_id, child_subtag_id, parent_namespace_id, parent_subtag_id, status, reason_id ) in old_data:
                
                child_tag_id = get_tag_id( child_namespace_id, child_subtag_id )
                parent_tag_id = get_tag_id( parent_namespace_id, parent_subtag_id )
                
                new_inserts.append( ( service_id, child_tag_id, parent_tag_id, status, reason_id ) )
                
            
            self._c.executemany( 'INSERT OR IGNORE INTO tag_parent_petitions ( service_id, child_tag_id, parent_tag_id, status, reason_id ) VALUES ( ?, ?, ?, ?, ? );', new_inserts )
            
            #
            
            old_data = self._c.execute( 'SELECT service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status FROM tag_siblings;' ).fetchall()
            
            self._c.execute( 'DROP TABLE tag_siblings;' )
            
            self._c.execute( 'CREATE TABLE tag_siblings ( service_id INTEGER REFERENCES services ON DELETE CASCADE, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );' )
            
            new_inserts = []
            
            for ( service_id, old_namespace_id, old_subtag_id, new_namespace_id, new_subtag_id, status ) in old_data:
                
                bad_tag_id = get_tag_id( old_namespace_id, old_subtag_id )
                good_tag_id = get_tag_id( new_namespace_id, new_subtag_id )
                
                new_inserts.append( ( service_id, bad_tag_id, good_tag_id, status ) )
                
            
            self._c.executemany( 'INSERT OR IGNORE INTO tag_siblings ( service_id, bad_tag_id, good_tag_id, status ) VALUES ( ?, ?, ?, ? );', new_inserts )
            
            #
            
            old_data = self._c.execute( 'SELECT service_id, old_namespace_id, old_tag_id, new_namespace_id, new_tag_id, status, reason_id FROM tag_sibling_petitions;' ).fetchall()
            
            self._c.execute( 'DROP TABLE tag_sibling_petitions;' )
            
            self._c.execute( 'CREATE TABLE tag_sibling_petitions ( service_id INTEGER REFERENCES services ON DELETE CASCADE, bad_tag_id INTEGER, good_tag_id INTEGER, status INTEGER, reason_id INTEGER, PRIMARY KEY ( service_id, bad_tag_id, status ) );' )
            
            new_inserts = []
            
            for ( service_id, old_namespace_id, old_subtag_id, new_namespace_id, new_subtag_id, status, reason_id ) in old_data:
                
                bad_tag_id = get_tag_id( old_namespace_id, old_subtag_id )
                good_tag_id = get_tag_id( new_namespace_id, new_subtag_id )
                
                new_inserts.append( ( service_id, bad_tag_id, good_tag_id, status, reason_id ) )
                
            
            self._c.executemany( 'INSERT OR IGNORE INTO tag_sibling_petitions ( service_id, bad_tag_id, good_tag_id, status, reason_id ) VALUES ( ?, ?, ?, ?, ? );', new_inserts )
            
            #
            
            the_table_join = 'tags, old_table ON old_table.namespace_id = tags.namespace_id AND old_table.tag_id = tags.subtag_id'
            
            #
            
            # there's a 'namespace_id' check in the sql here because users who update from v238 or so get new caches in the update code for the new all known files :/
            cache_table_names = [ name for ( name, sql ) in self._c.execute( 'SELECT name, sql FROM external_caches.sqlite_master WHERE type = ?', ( 'table', ) ) if 'namespace_id' in sql ]
            
            for cache_table_name in cache_table_names:
                
                self._controller.pub( 'splash_set_status_text', 'compacting ' + cache_table_name )
                
                if cache_table_name.startswith( 'combined_files_ac_cache_' ) or cache_table_name.startswith( 'specific_ac_cache_' ):
                    
                    self._c.execute( 'ALTER TABLE ' + cache_table_name + ' RENAME TO old_table;' )
                    
                    self._c.execute( 'CREATE TABLE external_caches.' + cache_table_name + ' ( tag_id INTEGER PRIMARY KEY, current_count INTEGER, pending_count INTEGER );' )
                    
                    self._c.execute( 'INSERT INTO ' + cache_table_name + ' ( tag_id, current_count, pending_count ) SELECT tags.tag_id, current_count, pending_count FROM ' + the_table_join + ';' )
                    
                    self._c.execute( 'DROP TABLE old_table;' )
                    
                elif cache_table_name.startswith( 'specific_current_mappings_cache_' ) or cache_table_name.startswith( 'specific_pending_mappings_cache_' ):
                    
                    self._c.execute( 'ALTER TABLE ' + cache_table_name + ' RENAME TO old_table;' )
                    
                    self._c.execute( 'CREATE TABLE external_caches.' + cache_table_name + ' ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) ) WITHOUT ROWID;' )
                    
                    self._c.execute( 'INSERT INTO ' + cache_table_name + ' ( hash_id, tag_id ) SELECT hash_id, tags.tag_id FROM ' + the_table_join + ';' )
                    
                    self._c.execute( 'DROP TABLE old_table;' )
                    
                
            
            #
            
            mapping_table_names = [ name for ( name, ) in self._c.execute( 'SELECT name FROM external_mappings.sqlite_master WHERE type = ?', ( 'table', ) ) ]
            
            for mapping_table_name in mapping_table_names:
                
                self._controller.pub( 'splash_set_status_text', 'compacting ' + mapping_table_name )
                
                if mapping_table_name.startswith( 'current_mappings_' ) or mapping_table_name.startswith( 'deleted_mappings_' ) or mapping_table_name.startswith( 'pending_mappings_' ):
                    
                    self._c.execute( 'ALTER TABLE ' + mapping_table_name + ' RENAME TO old_table;' )
                    
                    self._c.execute( 'CREATE TABLE external_mappings.' + mapping_table_name + ' ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
                    
                    self._c.execute( 'INSERT INTO ' + mapping_table_name + ' ( tag_id, hash_id ) SELECT tags.tag_id, hash_id FROM ' + the_table_join + ';' )
                    
                    self._c.execute( 'DROP TABLE old_table;' )
                    
                    self._controller.pub( 'splash_set_status_text', 'indexing ' + mapping_table_name )
                    
                    self._c.execute( 'CREATE UNIQUE INDEX external_mappings.' + mapping_table_name + '_hash_id_tag_id_index ON ' + mapping_table_name + ' ( hash_id, tag_id );' )
                    
                elif mapping_table_name.startswith( 'petitioned_mappings_' ):
                    
                    self._c.execute( 'ALTER TABLE ' + mapping_table_name + ' RENAME TO old_table;' )
                    
                    self._c.execute( 'CREATE TABLE external_mappings.' + mapping_table_name + ' ( tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;' )
                    
                    self._c.execute( 'INSERT INTO ' + mapping_table_name + ' ( tag_id, hash_id, reason_id ) SELECT tags.tag_id, hash_id, reason_id FROM ' + the_table_join + ';' )
                    
                    self._c.execute( 'DROP TABLE old_table;' )
                    
                    self._controller.pub( 'splash_set_status_text', 'indexing ' + mapping_table_name )
                    
                    self._c.execute( 'CREATE UNIQUE INDEX external_mappings.' + mapping_table_name + '_hash_id_tag_id_index ON ' + mapping_table_name + ' ( hash_id, tag_id );' )
                    
                
            
            self._controller.pub( 'splash_set_status_text', 'committing to disk' )
            
            self._Commit()
            
            self._CloseDBCursor()
            
            try:
                
                for filename in [ 'client.mappings.db', 'client.master.db', 'client.caches.db', 'client.db' ]:
                    
                    self._controller.pub( 'splash_set_status_text', 'vacuuming ' + filename )
                    
                    db_path = os.path.join( self._db_dir, filename )
                    
                    try:
                        
                        if HydrusDB.CanVacuum( db_path ):
                            
                            HydrusDB.VacuumDB( db_path )
                            
                        
                    except Exception as e:
                        
                        HydrusData.Print( 'Vacuum failed!' )
                        HydrusData.PrintException( e )
                        
                    
                
            finally:
                
                self._InitDBCursor()
                
                self._BeginImmediate()
                
            
            for schema in [ 'main', 'external_caches', 'external_master', 'external_mappings' ]:
                
                self._controller.pub( 'splash_set_status_text', 'analyzing ' + schema )
                
                try:
                    
                    self._c.execute( 'ANALYZE ' + schema + ';' )
                    
                except:
                    
                    HydrusData.Print( 'While updating to v244, ANALYZE ' + schema + ' failed!' )
                    
                
            
        
        if version == 244:
            
            ( foreign_keys_on, ) = self._c.execute( 'PRAGMA foreign_keys;' ).fetchone()
            
            if foreign_keys_on:
                
                self._Commit()
                
                self._c.execute( 'PRAGMA foreign_keys = ?;', ( False, ) )
                
                self._BeginImmediate()
                
            
            self._controller.pub( 'splash_set_status_text', 'updating services' )
            
            old_service_info = self._c.execute( 'SELECT * FROM services;' ).fetchall()
            
            self._c.execute( 'DROP TABLE services;' )
            
            self._c.execute( 'CREATE TABLE services ( service_id INTEGER PRIMARY KEY AUTOINCREMENT, service_key BLOB_BYTES UNIQUE, service_type INTEGER, name TEXT, dictionary_string TEXT );' )
            
            for ( service_id, service_key, service_type, name, info ) in old_service_info:
                
                dictionary = ClientServices.GenerateDefaultServiceDictionary( service_type )
                
                if service_type in HC.RATINGS_SERVICES:
                    
                    dictionary[ 'shape' ] = info[ 'shape' ]
                    dictionary[ 'colours' ] = info[ 'colours' ].items()
                    
                    if service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        dictionary[ 'num_stars' ] = info[ 'num_stars' ]
                        dictionary[ 'allow_zero' ] = info[ 'allow_zero' ]
                        
                    
                
                if service_type in HC.REMOTE_SERVICES:
                    
                    if service_type in HC.REPOSITORIES:
                        
                        dictionary[ 'bandwidth_rules' ].AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 50 * 1024 * 1024 )
                        
                    
                    host = info[ 'host' ]
                    port = info[ 'port' ]
                    
                    credentials = HydrusNetwork.Credentials( host, port )
                    
                    if 'access_key' in info:
                        
                        access_key = info[ 'access_key' ]
                        
                        credentials.SetAccessKey( access_key )
                        
                    
                    dictionary[ 'credentials' ] = credentials
                    
                    if service_type in HC.REPOSITORIES:
                        
                        dictionary[ 'paused' ] = info[ 'paused' ]
                        
                    
                    if service_type in HC.TAG_SERVICES:
                        
                        if 'tag_archive_sync' in info and info[ 'tag_archive_sync' ] is not None:
                            
                            dictionary[ 'tag_archive_sync' ] = [ ( portable_path, list( namespaces ) ) for ( portable_path, namespaces ) in info[ 'tag_archive_sync' ].items() ]
                            
                        
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    dictionary[ 'port' ] = info[ 'port' ]
                    
                
                dictionary_string = dictionary.DumpToString()
                
                self._c.execute( 'INSERT INTO services ( service_id, service_key, service_type, name, dictionary_string ) VALUES ( ?, ?, ?, ?, ? );', ( service_id, sqlite3.Binary( service_key ), service_type, name, dictionary_string ) )
                
            
            #
            
            self._c.execute( 'CREATE TABLE remote_thumbnails ( service_id INTEGER, hash_id INTEGER, PRIMARY KEY( service_id, hash_id ) );' )
            
            #
            
            dictionary = ClientServices.GenerateDefaultServiceDictionary( HC.LOCAL_FILE_DOMAIN )
            
            self._AddService( CC.LOCAL_UPDATE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'repository updates', dictionary )
            
            #
            
            service_ids = [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ( ?, ? );', ( HC.TAG_REPOSITORY, HC.FILE_REPOSITORY ) ) ]
            
            for service_id in service_ids:
                
                repository_updates_table_name = GenerateRepositoryRepositoryUpdatesTableName( service_id )
                
                self._c.execute( 'CREATE TABLE ' + repository_updates_table_name + ' ( update_index INTEGER, hash_id INTEGER, processed INTEGER_BOOLEAN, PRIMARY KEY ( update_index, hash_id ) );' )
                self._CreateIndex( repository_updates_table_name, [ 'hash_id' ] )
                
                ( hash_id_map_table_name, tag_id_map_table_name ) = GenerateRepositoryMasterCacheTableNames( service_id )
                
                self._c.execute( 'CREATE TABLE ' + hash_id_map_table_name + ' ( service_hash_id INTEGER PRIMARY KEY, hash_id INTEGER );' )
                self._c.execute( 'CREATE TABLE ' + tag_id_map_table_name + ' ( service_tag_id INTEGER PRIMARY KEY, tag_id INTEGER );' )
                
            
            #
            
            self._controller.pub( 'splash_set_status_text', 'deleting misc old cruft' )
            
            self._c.execute( 'DROP TABLE news;' )
            self._c.execute( 'DROP TABLE contacts;' )
            self._c.execute( 'DROP TABLE conversation_subjects;' )
            self._c.execute( 'DROP TABLE message_attachments;' )
            self._c.execute( 'DROP TABLE message_depots;' )
            self._c.execute( 'DROP TABLE message_destination_map;' )
            self._c.execute( 'DROP TABLE message_downloads;' )
            self._c.execute( 'DROP TABLE message_drafts;' )
            self._c.execute( 'DROP TABLE message_inbox;' )
            self._c.execute( 'DROP TABLE message_keys;' )
            self._c.execute( 'DROP TABLE message_bodies;' )
            self._c.execute( 'DROP TABLE incoming_message_statuses;' )
            self._c.execute( 'DROP TABLE messages;' )
            
            self._controller.pub( 'splash_set_status_text', 'deleting old updates dir' )
            
            updates_dir = os.path.join( self._db_dir, 'client_updates' )
            
            HydrusPaths.DeletePath( updates_dir )
            
        
        # cleantag definition has changed, so let's collapse all 'series: blah' stuff to 'series:blah'
        # server did it last week, so we can nuke non-local tags as they'll be replaced in the normal resync that's going on atm
        # this is for v245->v246, v247->v248 updates both
        
        def current_clean_tag( tag ):
            
            try:
                
                def strip_gumpf_out( t ):
                    
                    t.replace( '\r', '' )
                    t.replace( '\n', '' )
                    
                    t = re.sub( '[\\s]+', ' ', t, flags = re.UNICODE ) # turns multiple spaces into single spaces
                    
                    t = re.sub( '\\s\\Z', '', t, flags = re.UNICODE ) # removes space at the end
                    
                    while re.match( '\\s|-|system:', t, flags = re.UNICODE ) is not None:
                        
                        t = re.sub( '\\A(\\s|-|system:)', '', t, flags = re.UNICODE ) # removes spaces or garbage at the beginning
                        
                    
                    return t
                    
                
                tag = tag[:1024]
                
                tag = tag.lower()
                
                tag = HydrusData.ToUnicode( tag )
                
                if tag.startswith( ':' ):
                    
                    tag = re.sub( '^:(?!:)', '::', tag, flags = re.UNICODE ) # Convert anything starting with one colon to start with two i.e. :D -> ::D
                    
                    tag = strip_gumpf_out( tag )
                    
                elif ':' in tag:
                    
                    ( namespace, subtag ) = current_split_tag( tag )
                    
                    namespace = strip_gumpf_out( namespace )
                    subtag = strip_gumpf_out( subtag )
                    
                    tag = current_combine_tag( namespace, subtag )
                    
                else:
                    
                    tag = strip_gumpf_out( tag )
                    
                
            except Exception as e:
                
                text = 'Was unable to parse the tag: ' + HydrusData.ToUnicode( tag )
                text += os.linesep * 2
                text += HydrusData.ToUnicode( e )
                
                raise Exception( text )
                
            
            return tag
            
        
        def current_combine_tag( namespace, subtag ):
            
            if namespace == '':
                
                if subtag.startswith( ':' ):
                    
                    return ':' + subtag
                    
                else:
                    
                    return subtag
                    
                
            else:
                
                return namespace + ':' + subtag
                
            
        
        def current_split_tag( tag ):
            
            if ':' in tag:
                
                return tag.split( ':', 1 )
                
            else:
                
                return ( '', tag )
                
            
        
        if version == 245:
            
            self._InitCaches()
            
            # due to a previous update, some clients have two entries per prefix with ..\db\client_files vs client_files type superfluous stuff.
            # let's clean it up nicely, catching any other weirdness along the way
            
            all_client_files_info = self._c.execute( 'SELECT prefix, location FROM client_files_locations;' ).fetchall()
            
            if len( all_client_files_info ) > 768:
                
                self._c.execute( 'DELETE FROM client_files_locations;' )
                
                inserts = []
                
                prefixes_to_current_locations = HydrusData.BuildKeyToListDict( all_client_files_info )
                
                for ( prefix, portable_locations ) in prefixes_to_current_locations.items():
                    
                    correct_portable_location = portable_locations[0] # default to just put bad data back in
                    
                    correct_abs_locations = set()
                    
                    for portable_location in portable_locations:
                        
                        possibly_correct_abs_location = HydrusPaths.ConvertPortablePathToAbsPath( portable_location )
                        
                        if os.path.exists( possibly_correct_abs_location ):
                            
                            correct_abs_locations.add( possibly_correct_abs_location )
                            
                        
                    
                    if len( correct_abs_locations ) > 0:
                        
                        correct_abs_location = list( correct_abs_locations )[0] # if this somehow produces two different abs locations, let's collapse
                        
                        correct_portable_location = HydrusPaths.ConvertAbsPathToPortablePath( correct_abs_location )
                        
                    
                    inserts.append( ( prefix, correct_portable_location ) )
                    
                
                self._c.executemany( 'INSERT INTO client_files_locations ( prefix, location ) VALUES ( ?, ? );', inserts )
                
            
            #
            
            self._controller.pub( 'splash_set_status_text', 'cleaning tags' )
            
            dirty_namespace_info = []
            dirty_subtag_info = []
            invalid_subtag_ids = []
            
            for ( namespace_id, namespace ) in self._c.execute( 'SELECT namespace_id, namespace FROM namespaces;' ):
                
                pretend_subtag = 'subtag'
                
                tag = current_combine_tag( namespace, pretend_subtag )
                
                clean_tag = current_clean_tag( tag )
                
                if clean_tag != tag:
                    
                    ( clean_namespace, clean_subtag ) = current_split_tag( clean_tag )
                    
                    dirty_namespace_info.append( ( namespace_id, namespace, clean_namespace ) )
                    
                
            
            for ( subtag_id, subtag ) in self._c.execute( 'SELECT subtag_id, subtag FROM subtags;' ):
                
                pretend_namespace = 'series'
                
                tag = current_combine_tag( pretend_namespace, subtag )
                
                clean_tag = current_clean_tag( tag )
                
                try:
                    
                    HydrusTags.CheckTagNotEmpty( clean_tag )
                    
                except HydrusExceptions.SizeException:
                    
                    invalid_subtag_ids.append( subtag_id )
                    
                    continue
                    
                
                if clean_tag != tag:
                    
                    ( clean_namespace, clean_subtag ) = current_split_tag( clean_tag )
                    
                    dirty_subtag_info.append( ( subtag_id, subtag, clean_subtag ) )
                    
                
            
            self._controller.pub( 'splash_set_status_text', HydrusData.ConvertIntToPrettyString( len( dirty_namespace_info ) + len( dirty_subtag_info ) ) + ' dirty tag parts found, now cleaning' )
            
            dirty_and_clean_tag_ids = []
            
            for ( dirty_namespace_id, dirty_namespace, clean_namespace ) in dirty_namespace_info:
                
                if self._NamespaceExists( clean_namespace ):
                    
                    for ( dirty_tag_id, subtag ) in self._c.execute( 'SELECT tag_id, subtag FROM tags NATURAL JOIN subtags WHERE namespace_id = ?;', ( namespace_id, ) ).fetchall():
                        
                        clean_tag = current_combine_tag( clean_namespace, subtag )
                        
                        clean_tag_id = self._GetTagId( clean_tag )
                        
                        dirty_and_clean_tag_ids.append( ( dirty_tag_id, clean_tag_id ) )
                        
                    
                    clean_namespace = 'invalid namespace "' + dirty_namespace + '"'
                    
                
                self._c.execute( 'UPDATE namespaces SET namespace = ? WHERE namespace_id = ?;', ( clean_namespace, dirty_namespace_id ) )
                
            
            for ( dirty_subtag_id, dirty_subtag, clean_subtag ) in dirty_subtag_info:
                
                if self._SubtagExists( clean_subtag ):
                    
                    for ( dirty_tag_id, namespace ) in self._c.execute( 'SELECT tag_id, namespace FROM tags NATURAL JOIN namespaces WHERE subtag_id = ?;', ( subtag_id, ) ).fetchall():
                        
                        clean_tag = current_combine_tag( namespace, clean_subtag )
                        
                        clean_tag_id = self._GetTagId( clean_tag )
                        
                        dirty_and_clean_tag_ids.append( ( dirty_tag_id, clean_tag_id ) )
                        
                    
                    clean_subtag = 'invalid subtag "' + dirty_subtag + '"'
                    
                
                try:
                    
                    self._c.execute( 'UPDATE subtags SET subtag = ? WHERE subtag_id = ?;', ( clean_subtag, dirty_subtag_id ) )
                    
                except sqlite3.IntegrityError:
                    
                    # I'm not sure how this happened--it was on an unusual '-:' -> ':' pair, so it is probably so rare we can skip it for now
                    invalid_subtag_ids.append( dirty_subtag_id )
                    
                
            
            ( local_tag_service_id, ) = self._c.execute( 'SELECT service_id FROM services WHERE service_key = ?;', ( sqlite3.Binary( CC.LOCAL_TAG_SERVICE_KEY ), ) ).fetchone()
            
            repo_tag_service_ids = [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type = ?;', ( HC.TAG_REPOSITORY, ) ) ]
            
            for ( dirty_tag_id, clean_tag_id ) in dirty_and_clean_tag_ids:
                
                current_mappings_table_name = 'external_mappings.current_mappings_' + str( local_tag_service_id )
                
                dirty_local_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( dirty_tag_id, ) ) ]
                
                mappings_ids = [ ( clean_tag_id, dirty_local_hash_ids ) ]
                deleted_mappings_ids = [ ( dirty_tag_id, dirty_local_hash_ids ) ]
                
                self._UpdateMappings( local_tag_service_id, mappings_ids = mappings_ids, deleted_mappings_ids = deleted_mappings_ids )
                
                for repo_tag_service_id in repo_tag_service_ids:
                    
                    current_mappings_table_name = 'external_mappings.current_mappings_' + str( repo_tag_service_id )
                    
                    dirty_local_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( dirty_tag_id, ) ) ]
                    
                    deleted_mappings_ids = [ ( dirty_tag_id, dirty_local_hash_ids ) ]
                    
                    pending_mappings_table_name = 'external_mappings.pending_mappings_' + str( repo_tag_service_id )
                    
                    dirty_pending_local_hash_ids = [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM ' + pending_mappings_table_name + ' WHERE tag_id = ?;', ( dirty_tag_id, ) ) ]
                    
                    pending_rescinded_mappings_ids = [ ( dirty_tag_id, dirty_pending_local_hash_ids ) ]
                    
                    self._UpdateMappings( repo_tag_service_id, deleted_mappings_ids = deleted_mappings_ids, pending_rescinded_mappings_ids = pending_rescinded_mappings_ids )
                    
                
            
            self._controller.pub( 'splash_set_status_text', HydrusData.ConvertIntToPrettyString( len( invalid_subtag_ids ) ) + ' invalid tag parts found, now replacing' )
            
            for ( i, invalid_subtag_id ) in enumerate( invalid_subtag_ids ):
                
                clean_subtag = 'invalid empty subtag ' + str( i )
                
                while self._SubtagExists( clean_subtag ): # there actually was a collision here for one user!
                    
                    i += 1
                    
                    clean_subtag = 'invalid empty subtag ' + str( i )
                    
                
                self._c.execute( 'UPDATE subtags SET subtag = ? WHERE subtag_id = ?;', ( clean_subtag, invalid_subtag_id ) )
                
            
            #
            
            message = 'I have fixed a bug in the \'all known files\' autocomplete cache. Please go database->regenerate->autocomplete cache when it is convenient.'
            
            self.pub_initial_message( message )
            
        
        if version == 247:
            
            self._InitCaches()
            
            self._controller.pub( 'splash_set_status_text', 'cleaning tags again' )
            
            tag_service_ids = [ service_id for ( service_id, ) in self._c.execute( 'SELECT service_id FROM services WHERE service_type IN ( ?, ? );', ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ) ) ]
            
            # I've messed this up with several lots of bad logic, so let's give it another go
            
            ugly_namespace_info = self._c.execute( 'SELECT namespace_id, namespace FROM namespaces WHERE namespace LIKE "invalid namespace%";' ).fetchall()
            
            for ( ugly_namespace_id, ugly_namespace ) in ugly_namespace_info:
                
                if len( ugly_namespace ) > 21 and ugly_namespace.startswith( 'invalid namespace "' ) and ugly_namespace.endswith( '"' ):
                    
                    # 'invalid namespace "blah"'
                    
                    invalid_namespace = ugly_namespace[19:-1]
                    
                    example_tag = current_combine_tag( invalid_namespace, 'test' )
                    
                    clean_example_tag = current_clean_tag( example_tag )
                    
                    ( pretty_namespace, gumpf ) = current_split_tag( clean_example_tag )
                    
                    if len( pretty_namespace ) > 0:
                        
                        for ( ugly_tag_id, subtag ) in self._c.execute( 'SELECT tag_id, subtag FROM tags NATURAL JOIN subtags WHERE namespace_id = ?;', ( ugly_namespace_id, ) ).fetchall():
                            
                            pretty_tag = current_combine_tag( pretty_namespace, subtag )
                            
                            pretty_tag_id = self._GetTagId( pretty_tag )
                            
                            for tag_service_id in tag_service_ids:
                                
                                current_mappings_table_name = 'external_mappings.current_mappings_' + str( tag_service_id )
                                
                                ugly_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( ugly_tag_id, ) ) )
                                
                                if len( ugly_hash_ids ) > 0:
                                    
                                    mappings_ids = [ ( pretty_tag_id, ugly_hash_ids ) ]
                                    deleted_mappings_ids = [ ( ugly_tag_id, ugly_hash_ids ) ]
                                    
                                    self._UpdateMappings( tag_service_id, mappings_ids = mappings_ids, deleted_mappings_ids = deleted_mappings_ids )
                                    
                                
                            
                        
                    
                
            
            #
            
            ugly_subtag_info = self._c.execute( 'SELECT subtag_id, subtag FROM subtags WHERE subtag LIKE "invalid subtag%";' ).fetchall()
            
            for ( ugly_subtag_id, ugly_subtag ) in ugly_subtag_info:
                
                if len( ugly_subtag ) > 18 and ugly_subtag.startswith( 'invalid subtag "' ) and ugly_subtag.endswith( '"' ):
                    
                    # 'invalid subtag "blah"'
                    
                    invalid_subtag = ugly_subtag[16:-1]
                    
                    example_tag = current_combine_tag( 'series', invalid_subtag )
                    
                    clean_example_tag = current_clean_tag( example_tag )
                    
                    ( gumpf, pretty_subtag ) = current_split_tag( clean_example_tag )
                    
                    if len( pretty_subtag ) > 0:
                        
                        for ( ugly_tag_id, namespace ) in self._c.execute( 'SELECT tag_id, namespace FROM tags NATURAL JOIN namespaces WHERE subtag_id = ?;', ( ugly_subtag_id, ) ).fetchall():
                            
                            pretty_tag = current_combine_tag( namespace, pretty_subtag )
                            
                            pretty_tag_id = self._GetTagId( pretty_tag )
                            
                            for tag_service_id in tag_service_ids:
                                
                                current_mappings_table_name = 'external_mappings.current_mappings_' + str( tag_service_id )
                                
                                ugly_hash_ids = self._STL( self._c.execute( 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ?;', ( ugly_tag_id, ) ) )
                                
                                if len( ugly_hash_ids ) > 0:
                                    
                                    mappings_ids = [ ( pretty_tag_id, ugly_hash_ids ) ]
                                    deleted_mappings_ids = [ ( ugly_tag_id, ugly_hash_ids ) ]
                                    
                                    self._UpdateMappings( tag_service_id, mappings_ids = mappings_ids, deleted_mappings_ids = deleted_mappings_ids )
                                    
                                
                            
                        
                    
                
            
        
        self._controller.pub( 'splash_set_title_text', 'updated db to v' + str( version + 1 ) )
        
        self._c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _UpdateMappings( self, tag_service_id, mappings_ids = None, deleted_mappings_ids = None, pending_mappings_ids = None, pending_rescinded_mappings_ids = None, petitioned_mappings_ids = None, petitioned_rescinded_mappings_ids = None ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( tag_service_id )
        
        if mappings_ids is None: mappings_ids = []
        if deleted_mappings_ids is None: deleted_mappings_ids = []
        if pending_mappings_ids is None: pending_mappings_ids = []
        if pending_rescinded_mappings_ids is None: pending_rescinded_mappings_ids = []
        if petitioned_mappings_ids is None: petitioned_mappings_ids = []
        if petitioned_rescinded_mappings_ids is None: petitioned_rescinded_mappings_ids = []
        
        file_service_ids = self._GetServiceIds( HC.AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES )
        
        # this method grew into a monster that merged deleted, pending and current according to a hierarchy of services
        # this cost a lot of CPU time and was extremely difficult to maintain
        # now it attempts a simpler union, not letting delete overwrite a current or pending
        
        change_in_num_mappings = 0
        change_in_num_deleted_mappings = 0
        change_in_num_pending_mappings = 0
        change_in_num_petitioned_mappings = 0
        change_in_num_tags = 0
        change_in_num_files = 0
        
        all_adds = mappings_ids + pending_mappings_ids
        
        tag_ids_being_added = { tag_id for ( tag_id, hash_ids ) in all_adds }
        
        hash_ids_lists = [ hash_ids for ( tag_id, hash_ids ) in all_adds ]
        hash_ids_being_added = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        all_removes = deleted_mappings_ids + pending_rescinded_mappings_ids
        
        tag_ids_being_removed = { tag_id for ( tag_id, hash_ids ) in all_removes }
        
        hash_ids_lists = [ hash_ids for ( tag_id, hash_ids ) in all_removes ]
        hash_ids_being_removed = { hash_id for hash_id in itertools.chain.from_iterable( hash_ids_lists ) }
        
        tag_ids_to_search_for = tag_ids_being_added.union( tag_ids_being_removed )
        hash_ids_to_search_for = hash_ids_being_added.union( hash_ids_being_removed )
        
        self._c.execute( 'CREATE TABLE mem.temp_tag_ids ( tag_id INTEGER );' )
        self._c.execute( 'CREATE TABLE mem.temp_hash_ids ( hash_id INTEGER );' )
        
        self._c.executemany( 'INSERT INTO temp_tag_ids ( tag_id ) VALUES ( ? );', ( ( tag_id, ) for tag_id in tag_ids_to_search_for ) )
        self._c.executemany( 'INSERT INTO temp_hash_ids ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids_to_search_for ) )
        
        pre_existing_tag_ids = { tag_id for ( tag_id, ) in self._c.execute( 'SELECT tag_id as t FROM temp_tag_ids WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE tag_id = t );' ) }
        pre_existing_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id as h FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE hash_id = h );' ) }
        
        num_tags_added = len( tag_ids_being_added.difference( pre_existing_tag_ids ) )
        num_files_added = len( hash_ids_being_added.difference( pre_existing_hash_ids ) )
        
        change_in_num_tags += num_tags_added
        change_in_num_files += num_files_added
        
        combined_files_current_counter = collections.Counter()
        combined_files_pending_counter = collections.Counter()
        
        if len( mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in mappings_ids:
                
                self._c.executemany( 'DELETE FROM ' + deleted_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_deleted = self._GetRowCount()
                
                self._c.executemany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                self._c.executemany( 'INSERT OR IGNORE INTO ' + current_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_inserted = self._GetRowCount()
                
                change_in_num_deleted_mappings -= num_deleted_deleted
                change_in_num_pending_mappings -= num_pending_deleted
                change_in_num_mappings += num_current_inserted
                
                combined_files_pending_counter[ tag_id ] -= num_pending_deleted
                combined_files_current_counter[ tag_id ] += num_current_inserted
                
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsAddMappings( file_service_id, tag_service_id, mappings_ids )
                
            
        
        if len( deleted_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in deleted_mappings_ids:
                
                self._c.executemany( 'DELETE FROM ' + current_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_current_deleted = self._GetRowCount()
                
                self._c.executemany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_petitions_deleted = self._GetRowCount()
                
                self._c.executemany( 'INSERT OR IGNORE INTO ' + deleted_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_deleted_inserted = self._GetRowCount()
                
                change_in_num_mappings -= num_current_deleted
                change_in_num_petitioned_mappings -= num_petitions_deleted
                change_in_num_deleted_mappings += num_deleted_inserted
                
                combined_files_current_counter[ tag_id ] -= num_current_deleted
                
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsDeleteMappings( file_service_id, tag_service_id, deleted_mappings_ids )
                
            
        
        if len( pending_mappings_ids ) > 0:
            
            culled_pending_mappings_ids = []
            
            for ( tag_id, hash_ids ) in pending_mappings_ids:
                
                select_statement = 'SELECT hash_id FROM ' + current_mappings_table_name + ' WHERE tag_id = ' + str( tag_id ) + ' AND hash_id IN %s;'
                
                existing_current_hash_ids = { hash_id for ( hash_id, ) in self._SelectFromList( select_statement, hash_ids ) }
                
                valid_hash_ids = set( hash_ids ).difference( existing_current_hash_ids )
                
                culled_pending_mappings_ids.append( ( tag_id, valid_hash_ids ) )
                
            
            pending_mappings_ids = culled_pending_mappings_ids
            
            for ( tag_id, hash_ids ) in pending_mappings_ids:
                
                self._c.executemany( 'INSERT OR IGNORE INTO ' + pending_mappings_table_name + ' VALUES ( ?, ? );', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_inserted = self._GetRowCount()
                
                change_in_num_pending_mappings += num_pending_inserted
                
                combined_files_pending_counter[ tag_id ] += num_pending_inserted
                
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsPendMappings( file_service_id, tag_service_id, pending_mappings_ids )
                
            
        
        if len( pending_rescinded_mappings_ids ) > 0:
            
            for ( tag_id, hash_ids ) in pending_rescinded_mappings_ids:
                
                self._c.executemany( 'DELETE FROM ' + pending_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
                
                num_pending_deleted = self._GetRowCount()
                
                change_in_num_pending_mappings -= num_pending_deleted
                
                combined_files_pending_counter[ tag_id ] -= num_pending_deleted
                
            
            for file_service_id in file_service_ids:
                
                self._CacheSpecificMappingsRescindPendingMappings( file_service_id, tag_service_id, pending_rescinded_mappings_ids )
                
            
        
        combined_files_seen_ids = set( ( key for ( key, value ) in combined_files_current_counter.items() if value != 0 ) )
        combined_files_seen_ids.update( ( key for ( key, value ) in combined_files_pending_counter.items() if value != 0 ) )
        
        combined_files_counts = [ ( tag_id, combined_files_current_counter[ tag_id ], combined_files_pending_counter[ tag_id ] ) for tag_id in combined_files_seen_ids ]
        
        self._CacheCombinedFilesMappingsUpdate( tag_service_id, combined_files_counts )
        
        # 
        
        post_existing_tag_ids = { tag_id for ( tag_id, ) in self._c.execute( 'SELECT tag_id as t FROM temp_tag_ids WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE tag_id = t );' ) }
        post_existing_hash_ids = { hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id as h FROM temp_hash_ids WHERE EXISTS ( SELECT 1 FROM ' + current_mappings_table_name + ' WHERE hash_id = h );' ) }
        
        self._c.execute( 'DROP TABLE temp_tag_ids;' )
        self._c.execute( 'DROP TABLE temp_hash_ids;' )
        
        num_tags_removed = len( pre_existing_tag_ids.intersection( tag_ids_being_removed ).difference( post_existing_tag_ids ) )
        num_files_removed = len( pre_existing_hash_ids.intersection( hash_ids_being_removed ).difference( post_existing_hash_ids ) )
        
        change_in_num_tags -= num_tags_removed
        change_in_num_files -= num_files_removed
        
        for ( tag_id, hash_ids, reason_id ) in petitioned_mappings_ids:
            
            self._c.executemany( 'INSERT OR IGNORE INTO ' + petitioned_mappings_table_name + ' VALUES ( ?, ?, ? );', [ ( tag_id, hash_id, reason_id ) for hash_id in hash_ids ] )
            
            num_petitions_inserted = self._GetRowCount()
            
            change_in_num_petitioned_mappings += num_petitions_inserted
            
        
        for ( tag_id, hash_ids ) in petitioned_rescinded_mappings_ids:
            
            self._c.executemany( 'DELETE FROM ' + petitioned_mappings_table_name + ' WHERE tag_id = ? AND hash_id = ?;', ( ( tag_id, hash_id ) for hash_id in hash_ids ) )
            
            num_petitions_deleted = self._GetRowCount()
            
            change_in_num_petitioned_mappings -= num_petitions_deleted
            
        
        service_info_updates = []
        
        if change_in_num_mappings != 0: service_info_updates.append( ( change_in_num_mappings, tag_service_id, HC.SERVICE_INFO_NUM_MAPPINGS ) )
        if change_in_num_deleted_mappings != 0: service_info_updates.append( ( change_in_num_deleted_mappings, tag_service_id, HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ) )
        if change_in_num_pending_mappings != 0: service_info_updates.append( ( change_in_num_pending_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ) )
        if change_in_num_petitioned_mappings != 0: service_info_updates.append( ( change_in_num_petitioned_mappings, tag_service_id, HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ) )
        if change_in_num_tags != 0: service_info_updates.append( ( change_in_num_tags, tag_service_id, HC.SERVICE_INFO_NUM_TAGS ) )
        if change_in_num_files != 0: service_info_updates.append( ( change_in_num_files, tag_service_id, HC.SERVICE_INFO_NUM_FILES ) )
        
        if len( service_info_updates ) > 0: self._c.executemany( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', service_info_updates )
        
    
    def _UpdateServerServices( self, admin_service_key, serverside_services, service_keys_to_access_keys, deletee_service_keys ):
        
        admin_service_id = self._GetServiceId( admin_service_key )
        
        admin_service = self._GetService( admin_service_id )
        
        admin_credentials = admin_service.GetCredentials()
        
        ( host, admin_port ) = admin_credentials.GetAddress()
        
        #
        
        current_service_keys = { service_key for ( service_key, ) in self._c.execute( 'SELECT service_key FROM services;' ) }
        
        for serverside_service in serverside_services:
            
            service_key = serverside_service.GetServiceKey()
            
            if service_key in current_service_keys:
                
                service_id = self._GetServiceId( service_key )
                
                service = self._GetService( service_id )
                
                credentials = service.GetCredentials()
                
                upnp_port = serverside_service.GetUPnPPort()
                
                if upnp_port is None:
                    
                    port = serverside_service.GetPort()
                    
                    credentials.SetAddress( host, port )
                    
                else:
                    
                    credentials.SetAddress( host, upnp_port )
                    
                
                service.SetCredentials( credentials )
                
                self._UpdateService( service )
                
            else:
                
                if service_key in service_keys_to_access_keys:
                    
                    service_type = serverside_service.GetServiceType()
                    name = serverside_service.GetName()
                    
                    service = ClientServices.GenerateService( service_key, service_type, name )
                    
                    access_key = service_keys_to_access_keys[ service_key ]
                    
                    credentials = service.GetCredentials()
                    
                    upnp_port = serverside_service.GetUPnPPort()
                    
                    if upnp_port is None:
                        
                        port = serverside_service.GetPort()
                        
                        credentials.SetAddress( host, port )
                        
                    else:
                        
                        credentials.SetAddress( host, upnp_port )
                        
                    
                    credentials.SetAccessKey( access_key )
                    
                    service.SetCredentials( credentials )
                    
                    ( service_key, service_type, name, dictionary ) = service.ToTuple()
                    
                    self._AddService( service_key, service_type, name, dictionary )
                    
                
            
        
        for service_key in deletee_service_keys:
            
            try:
                
                self._GetServiceId( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            self._DeleteService( service_id )
            
        
        self.pub_after_commit( 'notify_unknown_accounts' )
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        self.pub_after_commit( 'notify_new_pending' )
        
    
    def _UpdateService( self, service ):
        
        ( service_key, service_type, name, dictionary ) = service.ToTuple()
        
        service_id = self._GetServiceId( service_key )
        
        ( old_dictionary_string, ) = self._c.execute( 'SELECT dictionary_string FROM services WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        old_dictionary = HydrusSerialisable.CreateFromString( old_dictionary_string )
        
        if service_type in HC.TAG_SERVICES:
            
            old_tag_archive_sync = dict( old_dictionary[ 'tag_archive_sync' ] )
            new_tag_archive_sync = dict( dictionary[ 'tag_archive_sync' ] )
            
            for portable_hta_path in new_tag_archive_sync.keys():
                
                namespaces = set( new_tag_archive_sync[ portable_hta_path ] )
                
                if portable_hta_path in old_tag_archive_sync:
                    
                    old_namespaces = old_tag_archive_sync[ portable_hta_path ]
                    
                    namespaces.difference_update( old_namespaces )
                    
                    if len( namespaces ) == 0:
                        
                        continue
                        
                    
                
                hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
                adding = True
                
                self._controller.pub( 'sync_to_tag_archive', hta_path, service_key, file_service_key, adding, namespaces )
                
            
        
        if service_type == HC.LOCAL_BOORU:
            
            old_port = old_dictionary[ 'port' ]
            new_port = dictionary[ 'port' ]
            
            if old_port != new_port:
                
                self.pub_after_commit( 'restart_booru' )
                self.pub_after_commit( 'notify_new_upnp_mappings' )
                
            else:
                
                old_upnp = old_dictionary[ 'upnp_port' ]
                new_upnp = dictionary[ 'upnp_port' ]
                
                if old_upnp != new_upnp:
                    
                    self.pub_after_commit( 'notify_new_upnp_mappings' )
                    
                
            
            
        
        dictionary_string = dictionary.DumpToString()
        
        self._c.execute( 'UPDATE services SET name = ?, dictionary_string = ? WHERE service_id = ?;', ( name, dictionary_string, service_id ) )
        
        if service_id in self._service_cache:
            
            del self._service_cache[ service_id ]
            
        
    
    def _UpdateServices( self, services ):
        
        self._Commit()
        
        if not self._fast_big_transaction_wal:
            
            self._c.execute( 'PRAGMA journal_mode = TRUNCATE;' )
            
        
        self._c.execute( 'PRAGMA foreign_keys = ON;' )
        
        self._BeginImmediate()
        
        current_service_keys = { service_key for ( service_key, ) in self._c.execute( 'SELECT service_key FROM services;' ) }
        
        future_service_keys = { service.GetServiceKey() for service in services }
        
        for service_key in current_service_keys:
            
            if service_key not in future_service_keys:
                
                service_id = self._GetServiceId( service_key )
                
                self._DeleteService( service_id )
                
            
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            if service_key in current_service_keys:
                
                self._UpdateService( service )
                
            else:
                
                ( service_key, service_type, name, dictionary ) = service.ToTuple()
                
                self._AddService( service_key, service_type, name, dictionary )
                
            
        
        self.pub_after_commit( 'notify_unknown_accounts' )
        self.pub_after_commit( 'notify_new_services_data' )
        self.pub_after_commit( 'notify_new_services_gui' )
        self.pub_after_commit( 'notify_new_pending' )
        
        self._Commit()
        
        self._InitDBCursor()
        
        self._BeginImmediate()
        
    
    def _Vacuum( self, stop_time = None, force_vacuum = False ):
        
        new_options = self._controller.GetNewOptions()
        
        maintenance_vacuum_period_days = new_options.GetNoneableInteger( 'maintenance_vacuum_period_days' )
        
        if maintenance_vacuum_period_days is None:
            
            return
            
        
        stale_time_delta = maintenance_vacuum_period_days * 86400
        
        existing_names_to_timestamps = dict( self._c.execute( 'SELECT name, timestamp FROM vacuum_timestamps;' ).fetchall() )
        
        db_names = [ name for ( index, name, path ) in self._c.execute( 'PRAGMA database_list;' ) if name not in ( 'mem', 'temp' ) ]
        
        if force_vacuum:
            
            due_names = db_names
            
        else:
            
            due_names = [ name for name in db_names if name not in existing_names_to_timestamps or HydrusData.TimeHasPassed( existing_names_to_timestamps[ name ] + stale_time_delta ) ]
            
        
        if len( due_names ) > 0:
            
            self._Commit()
            
            job_key_pubbed = False
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_title', 'database maintenance - vacuum' )
            
            self._CloseDBCursor()
            
            try:
                
                time.sleep( 1 )
                
                names_done = []
                
                for name in due_names:
                    
                    try:
                        
                        db_path = os.path.join( self._db_dir, self._db_filenames[ name ] )
                        
                        if HydrusDB.CanVacuum( db_path, stop_time = stop_time ):
                            
                            if not job_key_pubbed:
                                
                                self._controller.pub( 'message', job_key )
                                
                                job_key_pubbed = True
                                
                            
                            self._controller.pub( 'splash_set_status_text', 'vacuuming ' + name )
                            job_key.SetVariable( 'popup_text_1', 'vacuuming ' + name )
                            
                            started = HydrusData.GetNowPrecise()
                            
                            HydrusDB.VacuumDB( db_path )
                            
                            time_took = HydrusData.GetNowPrecise() - started
                            
                            HydrusData.Print( 'Vacuumed ' + db_path + ' in ' + HydrusData.ConvertTimeDeltaToPrettyString( time_took ) )
                            
                            names_done.append( name )
                            
                        
                    except Exception as e:
                        
                        HydrusData.Print( 'vacuum failed:' )
                        
                        HydrusData.ShowException( e )
                        
                        size = os.path.getsize( db_path )
                        
                        text = 'An attempt to vacuum the database failed.'
                        text += os.linesep * 2
                        text += 'For now, automatic vacuuming has been disabled. If the error is not obvious, please contact the hydrus developer.'
                        
                        HydrusData.ShowText( text )
                        
                        self._InitDBCursor()
                        
                        self._BeginImmediate()
                        
                        new_options.SetNoneableInteger( 'maintenance_vacuum_period_days', None )
                        
                        self._SaveOptions( HC.options )
                        
                        return
                        
                    
                
                job_key.SetVariable( 'popup_text_1', 'cleaning up' )
                
            finally:
                
                self._InitDBCursor()
                
                self._BeginImmediate()
                
                self._c.executemany( 'DELETE FROM vacuum_timestamps WHERE name = ?;', ( ( name, ) for name in names_done ) )
                
                self._c.executemany( 'INSERT OR IGNORE INTO vacuum_timestamps ( name, timestamp ) VALUES ( ?, ? );', ( ( name, HydrusData.GetNow() ) for name in names_done ) )
                
                job_key.SetVariable( 'popup_text_1', 'done!' )
                
                job_key.Delete( 30 )
                
            
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action == 'analyze': result = self._AnalyzeStaleBigTables( *args, **kwargs )
        elif action == 'associate_repository_update_hashes': result = self._AssociateRepositoryUpdateHashes( *args, **kwargs )
        elif action == 'backup': result = self._Backup( *args, **kwargs )
        elif action == 'content_update_package':result = self._ProcessContentUpdatePackage( *args, **kwargs )
        elif action == 'content_updates':result = self._ProcessContentUpdates( *args, **kwargs )
        elif action == 'db_integrity': result = self._CheckDBIntegrity( *args, **kwargs )
        elif action == 'delete_hydrus_session_key': result = self._DeleteHydrusSessionKey( *args, **kwargs )
        elif action == 'delete_imageboard': result = self._DeleteYAMLDump( YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
        elif action == 'delete_local_booru_share': result = self._DeleteYAMLDump( YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'delete_pending': result = self._DeletePending( *args, **kwargs )
        elif action == 'delete_remote_booru': result = self._DeleteYAMLDump( YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
        elif action == 'delete_serialisable_named': result = self._DeleteJSONDumpNamed( *args, **kwargs )
        elif action == 'delete_service_info': result = self._DeleteServiceInfo( *args, **kwargs )
        elif action == 'delete_unknown_duplicate_pairs': result = self._CacheSimilarFilesDeleteUnknownDuplicatePairs( *args, **kwargs )
        elif action == 'dirty_services': result = self._SaveDirtyServices( *args, **kwargs )
        elif action == 'export_mappings': result = self._ExportToTagArchive( *args, **kwargs )
        elif action == 'file_integrity': result = self._CheckFileIntegrity( *args, **kwargs )
        elif action == 'hydrus_session': result = self._AddHydrusSession( *args, **kwargs )
        elif action == 'imageboard': result = self._SetYAMLDump( YAML_DUMP_ID_IMAGEBOARD, *args, **kwargs )
        elif action == 'import_file': result = self._ImportFile( *args, **kwargs )
        elif action == 'import_update': result = self._ImportUpdate( *args, **kwargs )
        elif action == 'local_booru_share': result = self._SetYAMLDump( YAML_DUMP_ID_LOCAL_BOORU, *args, **kwargs )
        elif action == 'maintain_similar_files_duplicate_pairs': result = self._CacheSimilarFilesMaintainDuplicatePairs( *args, **kwargs )
        elif action == 'maintain_similar_files_phashes': result = self._CacheSimilarFilesMaintainFiles( *args, **kwargs )
        elif action == 'maintain_similar_files_tree': result = self._CacheSimilarFilesMaintainTree( *args, **kwargs )
        elif action == 'process_repository': result = self._ProcessRepositoryUpdates( *args, **kwargs )
        elif action == 'push_recent_tags': result = self._PushRecentTags( *args, **kwargs )
        elif action == 'regenerate_ac_cache': result = self._RegenerateACCache( *args, **kwargs )
        elif action == 'regenerate_similar_files': result = self._CacheSimilarFilesRegenerateTree( *args, **kwargs )
        elif action == 'relocate_client_files': result = self._RelocateClientFiles( *args, **kwargs )
        elif action == 'remote_booru': result = self._SetYAMLDump( YAML_DUMP_ID_REMOTE_BOORU, *args, **kwargs )
        elif action == 'reset_repository': result = self._ResetRepository( *args, **kwargs )
        elif action == 'save_options': result = self._SaveOptions( *args, **kwargs )
        elif action == 'serialisable_simple': result = self._SetJSONSimple( *args, **kwargs )
        elif action == 'serialisable': result = self._SetJSONDump( *args, **kwargs )
        elif action == 'serialisables_overwrite': result = self._OverwriteJSONDumps( *args, **kwargs )
        elif action == 'set_password': result = self._SetPassword( *args, **kwargs )
        elif action == 'sync_hashes_to_tag_archive': result = self._SyncHashesToTagArchive( *args, **kwargs )
        elif action == 'tag_censorship': result = self._SetTagCensorship( *args, **kwargs )
        elif action == 'update_server_services': result = self._UpdateServerServices( *args, **kwargs )
        elif action == 'update_services': result = self._UpdateServices( *args, **kwargs )
        elif action == 'vacuum': result = self._Vacuum( *args, **kwargs )
        elif action == 'web_session': result = self._AddWebSession( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    
    def pub_content_updates_after_commit( self, service_keys_to_content_updates ):
        
        self.pub_after_commit( 'content_updates_data', service_keys_to_content_updates )
        self.pub_after_commit( 'content_updates_gui', service_keys_to_content_updates )
        
    
    def pub_initial_message( self, message ):
        
        self._initial_messages.append( message )
        
    
    def pub_service_updates_after_commit( self, service_keys_to_service_updates ):
        
        self.pub_after_commit( 'service_updates_data', service_keys_to_service_updates )
        self.pub_after_commit( 'service_updates_gui', service_keys_to_service_updates )
        
    
    def GetInitialMessages( self ):
        
        return self._initial_messages
        
    
    def RestoreBackup( self, path ):
        
        for filename in self._db_filenames.values():
            
            source = os.path.join( path, filename )
            dest = os.path.join( self._db_dir, filename )
            
            if os.path.exists( source ):
                
                HydrusPaths.MirrorFile( source, dest )
                
            else:
                
                # if someone backs up with an older version that does not have as many db files as this version, we get conflict
                # don't want to delete just in case, but we will move it out the way
                
                HydrusPaths.MergeFile( dest, dest + '.old' )
                
            
        
        client_files_source = os.path.join( path, 'client_files' )
        client_files_default = os.path.join( self._db_dir, 'client_files' )
        
        if os.path.exists( client_files_source ):
            
            HydrusPaths.MirrorTree( client_files_source, client_files_default )
            
        
    
