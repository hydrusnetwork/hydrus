import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusDB

from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule

class ClientDBNotesMap( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_texts: ClientDBMaster.ClientDBMasterTexts ):
        
        self.modules_texts = modules_texts
        
        ClientDBModule.ClientDBModule.__init__( self, 'client notes mapping', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.file_notes' ] = [
            ( [ 'note_id' ], False, 400 ),
            ( [ 'name_id' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.file_notes' : ( 'CREATE TABLE IF NOT EXISTS {} ( hash_id INTEGER, name_id INTEGER, note_id INTEGER, PRIMARY KEY ( hash_id, name_id ) );', 400 )
        }
        
    
    def DeleteNote( self, hash_id: int, name: str ):
        
        name_id = self.modules_texts.GetLabelId( name )
        
        self._Execute( 'DELETE FROM file_notes WHERE hash_id = ? AND name_id = ?;', ( hash_id, name_id ) )
        
    
    def GetHashIdsFromNoteName( self, name: str, hash_ids_table_name: str, job_status: typing.Optional[ ClientThreading.JobStatus ] = None ):
        
        label_id = self.modules_texts.GetLabelId( name )
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        # as note name is rare, we force this to run opposite to typical: notes to temp hashes
        return self._STS( self._ExecuteCancellable( 'SELECT hash_id FROM file_notes CROSS JOIN {} USING ( hash_id ) WHERE name_id = ?;'.format( hash_ids_table_name ), ( label_id, ), cancelled_hook ) )
        
    
    def GetHashIdsFromNumNotes( self, min_num_notes: typing.Optional[ int ], max_num_notes: typing.Optional[ int ], hash_ids_table_name: str, job_status: typing.Optional[ ClientThreading.JobStatus ] = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        has_notes = max_num_notes is None and min_num_notes == 1
        not_has_notes = ( min_num_notes is None or min_num_notes == 0 ) and max_num_notes is not None and max_num_notes == 0
        
        if has_notes:
            
            hash_ids = self.GetHashIdsThatHaveNotes( hash_ids_table_name, job_status = job_status )
            
        elif not_has_notes:
            
            hash_ids = self.GetHashIdsThatDoNotHaveNotes( hash_ids_table_name, job_status = job_status )
            
        else:
            
            include_zero_count_hash_ids = False
            
            if min_num_notes is None:
                
                filt = lambda c: c <= max_num_notes
                
                include_zero_count_hash_ids = True
                
            elif max_num_notes is None:
                
                filt = lambda c: min_num_notes <= c
                
            else:
                
                filt = lambda c: min_num_notes <= c <= max_num_notes
                
            
            # temp hashes to notes
            query = 'SELECT hash_id, COUNT( * ) FROM {} CROSS JOIN file_notes USING ( hash_id ) GROUP BY hash_id;'.format( hash_ids_table_name )
            
            hash_ids = { hash_id for ( hash_id, count ) in self._ExecuteCancellable( query, (), cancelled_hook ) if filt( count ) }
            
            if include_zero_count_hash_ids:
                
                zero_hash_ids = self.GetHashIdsThatDoNotHaveNotes( hash_ids_table_name, job_status = job_status )
                
                hash_ids.update( zero_hash_ids )
                
            
        
        return hash_ids
        
    
    def GetHashIdsThatDoNotHaveNotes( self, hash_ids_table_name: str, job_status: typing.Optional[ ClientThreading.JobStatus ] = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        query = 'SELECT hash_id FROM {} WHERE NOT EXISTS ( SELECT 1 FROM file_notes WHERE file_notes.hash_id = {}.hash_id );'.format( hash_ids_table_name, hash_ids_table_name )
        
        hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
        
        return hash_ids
        
    
    def GetHashIdsThatHaveNotes( self, hash_ids_table_name: str, job_status: typing.Optional[ ClientThreading.JobStatus ] = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        query = 'SELECT hash_id FROM {} WHERE EXISTS ( SELECT 1 FROM file_notes WHERE file_notes.hash_id = {}.hash_id );'.format( hash_ids_table_name, hash_ids_table_name )
        
        hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
        
        return hash_ids
        
    
    def GetHashIdsToNamesAndNotes( self, hash_ids_table_name: str ):
        
        query = 'SELECT file_notes.hash_id, label, note FROM {} CROSS JOIN file_notes USING ( hash_id ), labels, notes ON ( file_notes.name_id = labels.label_id AND file_notes.note_id = notes.note_id );'.format( hash_ids_table_name )
        
        hash_ids_to_names_and_notes = HydrusData.BuildKeyToListDict( ( ( hash_id, ( name, note ) ) for ( hash_id, name, note ) in self._Execute( query ) ) )
        
        return hash_ids_to_names_and_notes
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_FILES:
            
            tables_and_columns.append( ( 'main.file_notes', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def SetNote( self, hash_id: int, name: str, note: str ):
        
        name_id = self.modules_texts.GetLabelId( name )
        
        self._Execute( 'DELETE FROM file_notes WHERE hash_id = ? AND name_id = ?;', ( hash_id, name_id ) )
        
        if len( note ) > 0:
            
            note_id = self.modules_texts.GetNoteId( note )
            
            self._Execute( 'INSERT OR IGNORE INTO file_notes ( hash_id, name_id, note_id ) VALUES ( ?, ?, ? );', ( hash_id, name_id, note_id ) )
            
        
    
