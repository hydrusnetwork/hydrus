import sqlite3
import typing

class HydrusDBModule( object ):
    
    def __init__( self, name, cursor: sqlite3.Cursor ):
        
        self.name = name
        self._c = cursor
        
    
    def _CreateIndex( self, table_name, columns, unique = False ):
        
        if '.' in table_name:
            
            table_name_simple = table_name.split( '.' )[1]
            
        else:
            
            table_name_simple = table_name
            
        
        index_name = self._GenerateIndexName( table_name, columns )
        
        if unique:
            
            create_phrase = 'CREATE UNIQUE INDEX IF NOT EXISTS '
            
        else:
            
            create_phrase = 'CREATE INDEX IF NOT EXISTS '
            
        
        on_phrase = ' ON ' + table_name_simple + ' (' + ', '.join( columns ) + ');'
        
        statement = create_phrase + index_name + on_phrase
        
        self._c.execute( statement )
        
    
    def _GetIndexGenerationTuples( self ):
        
        raise NotImplementedError()
        
    
    def _GenerateIndexName( self, table_name, columns ):
        
        return '{}_{}_index'.format( table_name, '_'.join( columns ) )
        
    
    def CreateIndices( self ):
        
        index_generation_tuples = self._GetIndexGenerationTuples()
        
        for ( table_name, columns, unique ) in index_generation_tuples:
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def CreateTables( self ):
        
        raise NotImplementedError()
        
    
    def GetExpectedIndexNames( self ) -> typing.Collection[ str ]:
        
        index_generation_tuples = self._GetIndexGenerationTuples()
        
        expected_index_names = [ self._GenerateIndexName( table_name, columns ) for ( table_name, columns, unique ) in index_generation_tuples ]
        
        return expected_index_names
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        raise NotImplementedError()
        
    
