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
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        raise NotImplementedError()
        
    
    def _GenerateIndexName( self, table_name, columns ):
        
        return '{}_{}_index'.format( table_name, '_'.join( columns ) )
        
    
    def _STI( self, iterable_cursor ):
        
        # strip singleton tuples to an iterator
        
        return ( item for ( item, ) in iterable_cursor )
        
    
    def _STL( self, iterable_cursor ):
        
        # strip singleton tuples to a list
        
        return [ item for ( item, ) in iterable_cursor ]
        
    
    def _STS( self, iterable_cursor ):
        
        # strip singleton tuples to a set
        
        return { item for ( item, ) in iterable_cursor }
        
    
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
        
    
