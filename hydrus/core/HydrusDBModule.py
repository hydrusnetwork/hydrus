import sqlite3
import typing

from hydrus.core import HydrusDBBase

class HydrusDBModule( HydrusDBBase.DBBase ):
    
    def __init__( self, name, cursor: sqlite3.Cursor ):
        
        HydrusDBBase.DBBase.__init__( self )
        
        self.name = name
        
        self._SetCursor( cursor )
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        raise NotImplementedError()
        
    
    def CreateInitialIndices( self ):
        
        index_generation_tuples = self._GetInitialIndexGenerationTuples()
        
        for ( table_name, columns, unique ) in index_generation_tuples:
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def CreateInitialTables( self ):
        
        raise NotImplementedError()
        
    
    def GetExpectedIndexNames( self ) -> typing.Collection[ str ]:
        
        index_generation_tuples = self._GetInitialIndexGenerationTuples()
        
        expected_index_names = [ self._GenerateIndexName( table_name, columns ) for ( table_name, columns, unique ) in index_generation_tuples ]
        
        return expected_index_names
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        raise NotImplementedError()
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # could also do another one of these for orphan tables that have service id in the name.
        
        raise NotImplementedError()
        
    
