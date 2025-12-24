import collections.abc
import sqlite3

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientThreading
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.search import ClientNumberTest

class ClientDBNotesMap( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_texts: ClientDBMaster.ClientDBMasterTexts ):
        
        self.modules_texts = modules_texts
        
        super().__init__( 'client notes mapping', cursor )
        
    
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
        
    
    def GetHashIdsFromNoteName( self, name: str, hash_ids_table_name: str, job_status: ClientThreading.JobStatus | None = None ):
        
        label_id = self.modules_texts.GetLabelId( name )
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        # as note name is rare, we force this to run opposite to typical: notes to temp hashes
        return self._STS( self._ExecuteCancellable( 'SELECT hash_id FROM file_notes CROSS JOIN {} USING ( hash_id ) WHERE name_id = ?;'.format( hash_ids_table_name ), ( label_id, ), cancelled_hook ) )
        
    
    def GetHashIdsFromNumNotes( self, number_tests: list[ ClientNumberTest.NumberTest ], hash_ids: collections.abc.Collection[ int ], hash_ids_table_name: str, job_status: ClientThreading.JobStatus | None = None ):
        
        result_hash_ids = set( hash_ids )
        
        specific_number_tests = [ number_test for number_test in number_tests if not ( number_test.IsZero() or number_test.IsAnythingButZero() ) ]
        
        megalambda = ClientNumberTest.NumberTest.STATICCreateMegaLambda( specific_number_tests )
        
        is_zero = True in ( number_test.IsZero() for number_test in number_tests )
        is_anything_but_zero = True in ( number_test.IsAnythingButZero() for number_test in number_tests )
        wants_zero = True in ( number_test.WantsZero() for number_test in number_tests )
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        nonzero_hash_ids = set()
        
        if is_zero or is_anything_but_zero or wants_zero:
            
            nonzero_hash_ids = self.GetHashIdsThatHaveNotes( hash_ids_table_name, job_status = job_status )
            
            if is_zero:
                
                result_hash_ids.difference_update( nonzero_hash_ids )
                
            
            if is_anything_but_zero:
                
                result_hash_ids.intersection_update( nonzero_hash_ids )
                
            
        
        if len( specific_number_tests ) > 0:
            
            # temp hashes to notes
            query = 'SELECT hash_id, COUNT( * ) FROM {} CROSS JOIN file_notes USING ( hash_id ) GROUP BY hash_id;'.format( hash_ids_table_name )
            
            good_url_count_hash_ids = { hash_id for ( hash_id, count ) in self._ExecuteCancellable( query, (), cancelled_hook ) if megalambda( count ) }
            
            if wants_zero:
                
                zero_hash_ids = result_hash_ids.difference( nonzero_hash_ids )
                
                good_url_count_hash_ids.update( zero_hash_ids )
                
            
            result_hash_ids.intersection_update( good_url_count_hash_ids )
            
        
        return result_hash_ids
        
    
    def GetHashIdsThatDoNotHaveNotes( self, hash_ids_table_name: str, job_status: ClientThreading.JobStatus | None = None ):
        
        cancelled_hook = None
        
        if job_status is not None:
            
            cancelled_hook = job_status.IsCancelled
            
        
        query = 'SELECT hash_id FROM {} WHERE NOT EXISTS ( SELECT 1 FROM file_notes WHERE file_notes.hash_id = {}.hash_id );'.format( hash_ids_table_name, hash_ids_table_name )
        
        hash_ids = self._STS( self._ExecuteCancellable( query, (), cancelled_hook ) )
        
        return hash_ids
        
    
    def GetHashIdsThatHaveNotes( self, hash_ids_table_name: str, job_status: ClientThreading.JobStatus | None = None ):
        
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
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        # if content type is a domain, then give urls? bleh
        
        tables_and_columns = []
        
        if content_type == HC.CONTENT_TYPE_HASH:
            
            tables_and_columns.append( ( 'main.file_notes', 'hash_id' ) )
            
        
        return tables_and_columns
        
    
    def SetNote( self, hash_id: int, name: str, note: str ):
        
        name_id = self.modules_texts.GetLabelId( name )
        
        self._Execute( 'DELETE FROM file_notes WHERE hash_id = ? AND name_id = ?;', ( hash_id, name_id ) )
        
        if len( note ) > 0:
            
            note_id = self.modules_texts.GetNoteId( note )
            
            self._Execute( 'INSERT OR IGNORE INTO file_notes ( hash_id, name_id, note_id ) VALUES ( ?, ?, ? );', ( hash_id, name_id, note_id ) )
            
        
    
