import collections
import sqlite3

from hydrus.core import HydrusGlobals as HG

class TemporaryIntegerTableNameCache( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        TemporaryIntegerTableNameCache.my_instance = self
        
        self._column_names_to_table_names = collections.defaultdict( collections.deque )
        self._column_names_counter = collections.Counter()
        
    
    @staticmethod
    def instance() -> 'TemporaryIntegerTableNameCache':
        
        if TemporaryIntegerTableNameCache.my_instance is None:
            
            raise Exception( 'TemporaryIntegerTableNameCache is not yet initialised!' )
            
        else:
            
            return TemporaryIntegerTableNameCache.my_instance
            
        
    
    def Clear( self ):
        
        self._column_names_to_table_names = collections.defaultdict( collections.deque )
        self._column_names_counter = collections.Counter()
        
    
    def GetName( self, column_name ):
        
        table_names = self._column_names_to_table_names[ column_name ]
        
        initialised = True
        
        if len( table_names ) == 0:
            
            initialised = False
            
            i = self._column_names_counter[ column_name ]
            
            table_name = 'mem.temp_int_{}_{}'.format( column_name, i )
            
            table_names.append( table_name )
            
            self._column_names_counter[ column_name ] += 1
            
        
        table_name = table_names.pop()
        
        return ( initialised, table_name )
        
    
    def ReleaseName( self, column_name, table_name ):
        
        self._column_names_to_table_names[ column_name ].append( table_name )
        
    
class TemporaryIntegerTable( object ):
    
    def __init__( self, cursor: sqlite3.Cursor, integer_iterable, column_name ):
        
        if not isinstance( integer_iterable, set ):
            
            integer_iterable = set( integer_iterable )
            
        
        self._cursor = cursor
        self._integer_iterable = integer_iterable
        self._column_name = column_name
        
        ( self._initialised, self._table_name ) = TemporaryIntegerTableNameCache.instance().GetName( self._column_name )
        
    
    def __enter__( self ):
        
        if not self._initialised:
            
            self._cursor.execute( 'CREATE TABLE IF NOT EXISTS {} ( {} INTEGER PRIMARY KEY );'.format( self._table_name, self._column_name ) )
            
        
        self._cursor.executemany( 'INSERT INTO {} ( {} ) VALUES ( ? );'.format( self._table_name, self._column_name ), ( ( i, ) for i in self._integer_iterable ) )
        
        return self._table_name
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._cursor.execute( 'DELETE FROM {};'.format( self._table_name ) )
        
        TemporaryIntegerTableNameCache.instance().ReleaseName( self._column_name, self._table_name )
        
        return False
        
    
class DBBase( object ):
    
    def __init__( self ):
        
        self._c = None
        
    
    def _CloseCursor( self ):
        
        if self._c is not None:
            
            self._c.close()
            
            del self._c
            
            self._c = None
            
        
    
    def _CreateIndex( self, table_name, columns, unique = False ):
        
        if unique:
            
            create_phrase = 'CREATE UNIQUE INDEX IF NOT EXISTS'
            
        else:
            
            create_phrase = 'CREATE INDEX IF NOT EXISTS'
            
        
        index_name = self._GenerateIndexName( table_name, columns )
        
        if '.' in table_name:
            
            table_name_simple = table_name.split( '.' )[1]
            
        else:
            
            table_name_simple = table_name
            
        
        statement = '{} {} ON {} ({});'.format( create_phrase, index_name, table_name_simple, ', '.join( columns ) )
        
        self._Execute( statement )
        
    
    def _Execute( self, query, *args ) -> sqlite3.Cursor:
        
        if HG.query_planner_mode and query not in HG.queries_planned:
            
            plan_lines = self._c.execute( 'EXPLAIN QUERY PLAN {}'.format( query ), *args ).fetchall()
            
            HG.query_planner_query_count += 1
            
            HG.client_controller.PrintQueryPlan( query, plan_lines )
            
        
        return self._c.execute( query, *args )
        
    
    def _ExecuteMany( self, query, args_iterator ):
        
        if HG.query_planner_mode and query not in HG.queries_planned:
            
            args_iterator = list( args_iterator )
            
            if len( args_iterator ) > 0:
                
                plan_lines = self._c.execute( 'EXPLAIN QUERY PLAN {}'.format( query ), args_iterator[0] ).fetchall()
                
                HG.query_planner_query_count += 1
                
                HG.client_controller.PrintQueryPlan( query, plan_lines )
                
            
        
        self._c.executemany( query, args_iterator )
        
    
    def _GenerateIndexName( self, table_name, columns ):
        
        return '{}_{}_index'.format( table_name, '_'.join( columns ) )
        
    
    def _ExecuteManySelectSingleParam( self, query, single_param_iterator ):
        
        select_args_iterator = ( ( param, ) for param in single_param_iterator )
        
        return self._ExecuteManySelect( query, select_args_iterator )
        
    
    def _ExecuteManySelect( self, query, select_args_iterator ):
        
        # back in python 2, we did batches of 256 hash_ids/whatever at a time in big "hash_id IN (?,?,?,?,...)" predicates.
        # this was useful to get over some 100,000 x fetchall() call overhead, but it would sometimes throw the SQLite query planner off and do non-optimal queries
        # (basically, the "hash_id in (256)" would weight the hash_id index request x 256 vs another when comparing the sqlite_stat1 tables, which could lead to WEWLAD for some indices with low median very-high mean skewed distribution
        # python 3 is better about call overhead, so we'll go back to what is pure
        # cursor.executemany SELECT when
        
        for select_args in select_args_iterator:
            
            for result in self._Execute( query, select_args ):
                
                yield result
                
            
        
    
    def _GetLastRowId( self ) -> int:
        
        return self._c.lastrowid
        
    
    def _GetRowCount( self ):
        
        row_count = self._c.rowcount
        
        if row_count == -1:
            
            return 0
            
        else:
            
            return row_count
            
        
    
    def _MakeTemporaryIntegerTable( self, integer_iterable, column_name ):
        
        return TemporaryIntegerTable( self._c, integer_iterable, column_name )
        
    
    def _SetCursor( self, c: sqlite3.Cursor ):
        
        self._c = c
        
    
    def _STI( self, iterable_cursor ):
        
        # strip singleton tuples to an iterator
        
        return ( item for ( item, ) in iterable_cursor )
        
    
    def _STL( self, iterable_cursor ):
        
        # strip singleton tuples to a list
        
        return [ item for ( item, ) in iterable_cursor ]
        
    
    def _STS( self, iterable_cursor ):
        
        # strip singleton tuples to a set
        
        return { item for ( item, ) in iterable_cursor }
        
    