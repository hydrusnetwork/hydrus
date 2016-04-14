import ClientData
import ClientDefaults
import ClientFiles
import ClientImporting
import ClientMedia
import ClientRatings
import ClientThreading
import collections
import hashlib
import httplib
import itertools
import json
import HydrusConstants as HC
import HydrusDB
import ClientDownloading
import ClientImageHandling
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusNATPunch
import HydrusPaths
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import lz4
import os
import Queue
import random
import shutil
import sqlite3
import stat
import sys
import threading
import time
import traceback
import wx
import yaml
import HydrusData
import ClientSearch
import HydrusGlobals

class SpecificServicesDB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 0
    
    def _AddFiles( self, hash_ids ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO current_files ( hash_id ) VALUES ( ? );', ( ( hash_id, ) for hash_id in hash_ids ) )
        
    
    def _AddMappings( self, mappings_ids ):
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._FilterFiles( hash_ids )
            
            if len( hash_ids ) > 0:
                
                # direct copy of rescind pending, so we don't filter twice
                self._c.execute( 'DELETE FROM pending_mappings WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND namespace_id = ? AND tag_id = ?;', ( namespace_id, tag_id ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._c.execute( 'UPDATE ac_cache SET pending_count = pending_count - ? WHERE namespace_id = ? AND tag_id = ?;', ( num_deleted, namespace_id, tag_id ) )
                    
                    self._c.execute( 'DELETE FROM ac_cache WHERE namespace_id = ? AND tag_id = ? AND current_count = ? AND pending_count = ?;', ( namespace_id, tag_id, 0, 0 ) )
                    
                
                #
                
                self._c.executemany( 'INSERT OR IGNORE INTO current_mappings ( hash_id, namespace_id, tag_id ) VALUES ( ?, ?, ? );', ( ( hash_id, namespace_id, tag_id ) for hash_id in hash_ids ) )
                
                num_new = self._GetRowCount()
                
                if num_new > 0:
                    
                    self._c.execute( 'INSERT OR IGNORE INTO ac_cache ( namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ? );', ( namespace_id, tag_id, 0, 0 ) )
                    
                    self._c.execute( 'UPDATE ac_cache SET current_count = current_count + ? WHERE namespace_id = ? AND tag_id = ?;', ( num_new, namespace_id, tag_id ) )
                    
                
            
        
    
    def _Analyze( self, stale_time_delta, stop_time ):
        
        all_names = [ name for ( name, ) in self._c.execute( 'SELECT name FROM sqlite_master;' ) ]
        
        existing_names_to_timestamps = dict( self._c.execute( 'SELECT name, timestamp FROM analyze_timestamps;' ).fetchall() )
        
        names_to_analyze = [ name for name in all_names if name not in existing_names_to_timestamps or HydrusData.TimeHasPassed( existing_names_to_timestamps[ name ] + stale_time_delta ) ]
        
        random.shuffle( names_to_analyze )
        
        while len( names_to_analyze ) > 0:
            
            name = names_to_analyze.pop()
            
            started = HydrusData.GetNowPrecise()
            
            self._c.execute( 'ANALYZE ' + name + ';' )
            
            self._c.execute( 'REPLACE INTO analyze_timestamps ( name, timestamp ) VALUES ( ?, ? );', ( name, HydrusData.GetNow() ) )
            
            time_took = HydrusData.GetNowPrecise() - started
            
            if HydrusData.TimeHasPassed( stop_time ) or not self._controller.CurrentlyIdle():
                
                break
                
            
        
        self._c.execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
        
        still_more_to_do = len( names_to_analyze ) > 0
        
        return still_more_to_do
        
    
    def _CreateDB( self ):
        
        HydrusDB.SetupDBCreatePragma( self._c, no_wal = self._no_wal )
        
        try: self._c.execute( 'BEGIN IMMEDIATE' )
        except Exception as e:
            
            raise HydrusExceptions.DBAccessException( HydrusData.ToUnicode( e ) )
            
        
        self._c.execute( 'CREATE TABLE current_files ( hash_id INTEGER PRIMARY KEY );' )
        
        self._c.execute( 'CREATE TABLE current_mappings ( hash_id INTEGER, namespace_id INTEGER, tag_id INTEGER, PRIMARY KEY( hash_id, namespace_id, tag_id ) );' )
        self._c.execute( 'CREATE TABLE pending_mappings ( hash_id INTEGER, namespace_id INTEGER, tag_id INTEGER, PRIMARY KEY( hash_id, namespace_id, tag_id ) );' )
        
        self._c.execute( 'CREATE TABLE ac_cache ( namespace_id INTEGER, tag_id INTEGER, current_count INTEGER, pending_count INTEGER, PRIMARY KEY( namespace_id, tag_id ) );' )
        
        self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, timestamp INTEGER );' )
        self._c.execute( 'CREATE TABLE maintenance_timestamps ( name TEXT, timestamp INTEGER );' )
        self._c.execute( 'CREATE TABLE version ( version INTEGER );' )
        
        self._c.execute( 'INSERT INTO version ( version ) VALUES ( ? );', ( HC.SOFTWARE_VERSION, ) )
        
        self._c.execute( 'COMMIT' )
        
    
    def _DeleteFiles( self, hash_ids ):
        
        for hash_id in hash_ids:
            
            hash_id_set = { hash_id }
            
            pending_mappings_ids = [ ( namespace_id, tag_id, hash_id_set ) for ( namespace_id, tag_id ) in self._c.execute( 'SELECT namespace_id, tag_id FROM pending_mappings WHERE hash_id = ?;', ( hash_id, ) ) ]
            
            self._RescindPendingMappings( pending_mappings_ids )
            
            current_mappings_ids = [ ( namespace_id, tag_id, hash_id_set ) for ( namespace_id, tag_id ) in self._c.execute( 'SELECT namespace_id, tag_id FROM current_mappings WHERE hash_id = ?;', ( hash_id, ) ) ]
            
            self._DeleteMappings( current_mappings_ids )
            
        
        self._c.execute( 'DELETE FROM current_files WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' )
        
    
    def _DeleteMappings( self, mappings_ids ):
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._FilterFiles( hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.execute( 'DELETE FROM current_mappings WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND namespace_id = ? AND tag_id = ?;', ( namespace_id, tag_id ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._c.execute( 'UPDATE ac_cache SET current_count = current_count - ? WHERE namespace_id = ? AND tag_id = ?;', ( num_deleted, namespace_id, tag_id ) )
                    
                    self._c.execute( 'DELETE FROM ac_cache WHERE namespace_id = ? AND tag_id = ? AND current_count = ? AND pending_count = ?;', ( namespace_id, tag_id, 0, 0 ) )
                    
                
            
        
    
    def _GetAutocompleteCounts( self, namespace_ids_to_tag_ids ):
        
        results = []
        
        for ( namespace_id, tag_ids ) in namespace_ids_to_tag_ids.items():
            
            results.extend( ( ( namespace_id, tag_id, current_count, pending_count ) for ( tag_id, current_count, pending_count ) in self._c.execute( 'SELECT tag_id, current_count, pending_count FROM ac_cache WHERE namespace_id = ? AND tag_id IN ' + HydrusData.SplayListForDB( tag_ids ) + ';', ( namespace_id, ) ) ) )
            
        
        return results
        
    
    def _FilterFiles( self, hash_ids ):
        
        return [ hash_id for ( hash_id, ) in self._c.execute( 'SELECT hash_id FROM current_files WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ';' ) ]
        
    
    def _HasFile( self, hash_id ):
        
        result = self._c.execute( 'SELECT 1 FROM current_files WHERE hash_id = ?;', ( hash_id, ) ).fetchone()
        
        if result is None:
            
            return False
            
        else:
            
            return True
            
        
    
    def _ManageDBError( self, job, e ):
        
        ( exception_type, value, tb ) = sys.exc_info()
        
        new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
        
        job.PutResult( new_e )
        
    
    def _PendMappings( self, mappings_ids ):
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._FilterFiles( hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.executemany( 'INSERT OR IGNORE INTO pending_mappings ( hash_id, namespace_id, tag_id ) VALUES ( ?, ?, ? );', ( ( hash_id, namespace_id, tag_id ) for hash_id in hash_ids ) )
                
                num_new = self._GetRowCount()
                
                if num_new > 0:
                    
                    self._c.execute( 'INSERT OR IGNORE INTO ac_cache ( namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ? );', ( namespace_id, tag_id, 0, 0 ) )
                    
                    self._c.execute( 'UPDATE ac_cache SET pending_count = pending_count + ? WHERE namespace_id = ? AND tag_id = ?;', ( num_new, namespace_id, tag_id ) )
                    
                
            
        
    
    def _RescindPendingMappings( self, mappings_ids ):
        
        for ( namespace_id, tag_id, hash_ids ) in mappings_ids:
            
            hash_ids = self._FilterFiles( hash_ids )
            
            if len( hash_ids ) > 0:
                
                self._c.execute( 'DELETE FROM pending_mappings WHERE hash_id IN ' + HydrusData.SplayListForDB( hash_ids ) + ' AND namespace_id = ? AND tag_id = ?;', ( namespace_id, tag_id ) )
                
                num_deleted = self._GetRowCount()
                
                if num_deleted > 0:
                    
                    self._c.execute( 'UPDATE ac_cache SET pending_count = pending_count - ? WHERE namespace_id = ? AND tag_id = ?;', ( num_deleted, namespace_id, tag_id ) )
                    
                    self._c.execute( 'DELETE FROM ac_cache WHERE namespace_id = ? AND tag_id = ? AND current_count = ? AND pending_count = ?;', ( namespace_id, tag_id, 0, 0 ) )
                    
                
            
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'ac_counts': result = self._GetAutocompleteCounts( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _UpdateDB( self, version ):
        
        self._c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action == 'add_files': result = self._AddFiles( *args, **kwargs )
        elif action == 'add_mappings': result = self._AddMappings( *args, **kwargs )
        elif action == 'analyze': result = self._Analyze( *args, **kwargs )
        elif action == 'delete_files': result = self._DeleteFiles( *args, **kwargs )
        elif action == 'delete_mappings': result = self._DeleteMappings( *args, **kwargs )
        elif action == 'pend_mappings': result = self._PendMappings( *args, **kwargs )
        elif action == 'rescind_pending_mappings': result = self._RescindPendingMappings( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    

class CombinedFilesDB( HydrusDB.HydrusDB ):
    
    READ_WRITE_ACTIONS = []
    UPDATE_WAIT = 0
    
    def _Analyze( self, stale_time_delta, stop_time ):
        
        all_names = [ name for ( name, ) in self._c.execute( 'SELECT name FROM sqlite_master;' ) ]
        
        existing_names_to_timestamps = dict( self._c.execute( 'SELECT name, timestamp FROM analyze_timestamps;' ).fetchall() )
        
        names_to_analyze = [ name for name in all_names if name not in existing_names_to_timestamps or HydrusData.TimeHasPassed( existing_names_to_timestamps[ name ] + stale_time_delta ) ]
        
        random.shuffle( names_to_analyze )
        
        while len( names_to_analyze ) > 0:
            
            name = names_to_analyze.pop()
            
            started = HydrusData.GetNowPrecise()
            
            self._c.execute( 'ANALYZE ' + name + ';' )
            
            self._c.execute( 'REPLACE INTO analyze_timestamps ( name, timestamp ) VALUES ( ?, ? );', ( name, HydrusData.GetNow() ) )
            
            time_took = HydrusData.GetNowPrecise() - started
            
            if HydrusData.TimeHasPassed( stop_time ) or not self._controller.CurrentlyIdle():
                
                break
                
            
        
        self._c.execute( 'ANALYZE sqlite_master;' ) # this reloads the current stats into the query planner
        
        still_more_to_do = len( names_to_analyze ) > 0
        
        return still_more_to_do
        
    
    def _CreateDB( self ):
        
        HydrusDB.SetupDBCreatePragma( self._c, no_wal = self._no_wal )
        
        try: self._c.execute( 'BEGIN IMMEDIATE' )
        except Exception as e:
            
            raise HydrusExceptions.DBAccessException( HydrusData.ToUnicode( e ) )
            
        
        self._c.execute( 'CREATE TABLE ac_cache ( namespace_id INTEGER, tag_id INTEGER, current_count INTEGER, pending_count INTEGER, PRIMARY KEY( namespace_id, tag_id ) );' )
        
        self._c.execute( 'CREATE TABLE analyze_timestamps ( name TEXT, timestamp INTEGER );' )
        self._c.execute( 'CREATE TABLE maintenance_timestamps ( name TEXT, timestamp INTEGER );' )
        self._c.execute( 'CREATE TABLE version ( version INTEGER );' )
        
        self._c.execute( 'INSERT INTO version ( version ) VALUES ( ? );', ( HC.SOFTWARE_VERSION, ) )
        
        self._c.execute( 'COMMIT' )
        
    
    def _GetAutocompleteCounts( self, namespace_ids_to_tag_ids ):
        
        results = []
        
        for ( namespace_id, tag_ids ) in namespace_ids_to_tag_ids.items():
            
            results.extend( ( ( namespace_id, tag_id, current_count, pending_count ) for ( tag_id, current_count, pending_count ) in self._c.execute( 'SELECT tag_id, current_count, pending_count FROM ac_cache WHERE namespace_id = ? AND tag_id IN ' + HydrusData.SplayListForDB( tag_ids ) + ';', ( namespace_id, ) ) ) )
            
        
        return results
        
    
    def _ManageDBError( self, job, e ):
        
        ( exception_type, value, tb ) = sys.exc_info()
        
        new_e = type( e )( os.linesep.join( traceback.format_exception( exception_type, value, tb ) ) )
        
        job.PutResult( new_e )
        
    
    def _UpdateCounts( self, count_ids ):
        
        self._c.executemany( 'INSERT OR IGNORE INTO ac_cache ( namespace_id, tag_id, current_count, pending_count ) VALUES ( ?, ?, ?, ? );', ( ( namespace_id, tag_id, 0, 0 ) for ( namespace_id, tag_id, current_delta, pending_delta ) in count_ids ) )
        
        self._c.executemany( 'UPDATE ac_cache SET current_count = current_count + ?, pending_count = pending_count + ? WHERE namespace_id = ? AND tag_id = ?;', ( ( current_delta, pending_delta, namespace_id, tag_id ) for ( namespace_id, tag_id, current_delta, pending_delta ) in count_ids ) )
        
        self._c.executemany( 'DELETE FROM ac_cache WHERE namespace_id = ? AND tag_id = ? AND current_count = ? AND pending_count = ?;', ( ( namespace_id, tag_id, 0, 0 ) for ( namespace_id, tag_id, current_delta, pending_delta ) in count_ids ) )
        
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'ac_counts': result = self._GetAutocompleteCounts( *args, **kwargs )
        else: raise Exception( 'db received an unknown read command: ' + action )
        
        return result
        
    
    def _UpdateDB( self, version ):
        
        self._c.execute( 'UPDATE version SET version = ?;', ( version + 1, ) )
        
    
    def _Write( self, action, *args, **kwargs ):
        
        if action == 'update_counts': result = self._UpdateCounts( *args, **kwargs )
        elif action == 'analyze': result = self._Analyze( *args, **kwargs )
        else: raise Exception( 'db received an unknown write command: ' + action )
        
        return result
        
    