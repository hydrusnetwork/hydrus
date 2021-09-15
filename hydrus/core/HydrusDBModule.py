import sqlite3
import typing

from hydrus.core import HydrusDBBase
from hydrus.core import HydrusExceptions

class HydrusDBModule( HydrusDBBase.DBBase ):
    
    def __init__( self, name, cursor: sqlite3.Cursor ):
        
        HydrusDBBase.DBBase.__init__( self )
        
        self.name = name
        
        self._SetCursor( cursor )
        
    
    def _FlattenIndexGenerationDict( self, index_generation_dict: dict ):
        
        tuples = []
        
        for ( table_name, index_rows ) in index_generation_dict.items():
            
            tuples.extend( ( ( table_name, columns, unique, version_added ) for ( columns, unique, version_added ) in index_rows ) )
            
        
        return tuples
        
    
    def _GetCriticalTableNames( self ) -> typing.Collection[ str ]:
        
        return set()
        
    
    def _GetServiceIndexGenerationDict( self, service_id ) -> dict:
        
        return {}
        
    
    def _GetServiceTableGenerationDict( self, service_id ) -> dict:
        
        return {}
        
    
    def _GetServicesIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        for service_id in self._GetServiceIdsWeGenerateDynamicTablesFor():
            
            index_generation_dict.update( self._GetServiceIndexGenerationDict( service_id ) )
            
        
        return index_generation_dict
        
    
    def _GetServicesTableGenerationDict( self ) -> dict:
        
        table_generation_dict = {}
        
        for service_id in self._GetServiceIdsWeGenerateDynamicTablesFor():
            
            table_generation_dict.update( self._GetServiceTableGenerationDict( service_id ) )
            
        
        return table_generation_dict
        
    
    def _GetServiceIdsWeGenerateDynamicTablesFor( self ):
        
        return []
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        return {}
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {}
        
    
    def _PresentMissingIndicesWarningToUser( self, index_names ):
        
        raise NotImplementedError()
        
    
    def _PresentMissingTablesWarningToUser( self, table_names ):
        
        raise NotImplementedError()
        
    
    def _RepairRepopulateTables( self, table_names, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        pass
        
    
    def CreateInitialIndices( self ):
        
        index_generation_dict = self._GetInitialIndexGenerationDict()
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            self._CreateIndex( table_name, columns, unique = unique )
            
        
    
    def CreateInitialTables( self ):
        
        table_generation_dict = self._GetInitialTableGenerationDict()
        
        for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items():
            
            self._Execute( create_query_without_name.format( table_name ) )
            
        
    
    def GetExpectedServiceIndexNames( self ) -> typing.Collection[ str ]:
        
        index_generation_dict = self._GetServicesIndexGenerationDict()
        
        expected_index_names = []
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            expected_index_names.append( self._GenerateIndexName( table_name, columns ) )
            
        
        return expected_index_names
        
    
    def GetExpectedInitialIndexNames( self ) -> typing.Collection[ str ]:
        
        index_generation_dict = self._GetInitialIndexGenerationDict()
        
        expected_index_names = []
        
        for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ):
            
            expected_index_names.append( self._GenerateIndexName( table_name, columns ) )
            
        
        return expected_index_names
        
    
    def GetExpectedServiceTableNames( self ) -> typing.Collection[ str ]:
        
        table_generation_dict = self._GetServicesTableGenerationDict()
        
        return list( table_generation_dict.keys() )
        
    
    def GetExpectedInitialTableNames( self ) -> typing.Collection[ str ]:
        
        table_generation_dict = self._GetInitialTableGenerationDict()
        
        return list( table_generation_dict.keys() )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        # could also do another one of these for orphan tables that have service id in the name.
        
        raise NotImplementedError()
        
    
    def Repair( self, current_db_version, cursor_transaction_wrapper: HydrusDBBase.DBCursorTransactionWrapper ):
        
        # core, initial tables first
        
        table_generation_dict = self._GetInitialTableGenerationDict()
        
        missing_table_rows = [ ( table_name, create_query_without_name ) for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items() if version_added <= current_db_version and not self._TableExists( table_name ) ]
        
        if len( missing_table_rows ) > 0:
            
            missing_table_names = sorted( [ missing_table_row[0] for missing_table_row in missing_table_rows ] )
            
            critical_table_names = self._GetCriticalTableNames()
            
            missing_critical_table_names = set( missing_table_names ).intersection( critical_table_names )
            
            if len( missing_critical_table_names ) > 0:
                
                message = 'Unfortunately, this database is missing one or more critical tables! This database is non functional and cannot be repaired. Please check out "install_dir/db/help my db is broke.txt" for the next steps.'
                
                raise HydrusExceptions.DBAccessException( message )
                
            
            self._PresentMissingTablesWarningToUser( missing_table_names )
            
            for ( table_name, create_query_without_name ) in missing_table_rows:
                
                self._Execute( create_query_without_name.format( table_name ) )
                
                cursor_transaction_wrapper.CommitAndBegin()
                
            
            self._RepairRepopulateTables( missing_table_names, cursor_transaction_wrapper )
            
            cursor_transaction_wrapper.CommitAndBegin()
            
        
        # now indices for those tables
        
        index_generation_dict = self._GetInitialIndexGenerationDict()
        
        missing_index_rows = [ ( self._GenerateIndexName( table_name, columns ), table_name, columns, unique ) for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ) if version_added <= current_db_version and not self._IndexExists( table_name, columns ) ]
        
        if len( missing_index_rows ):
            
            self._PresentMissingIndicesWarningToUser( sorted( [ index_name for ( index_name, table_name, columns, unique ) in missing_index_rows ] ) )
            
            for ( index_name, table_name, columns, unique ) in missing_index_rows:
                
                self._CreateIndex( table_name, columns, unique = unique )
                
                cursor_transaction_wrapper.CommitAndBegin()
                
            
        
        # now do service tables, same thing over again
        
        table_generation_dict = self._GetServicesTableGenerationDict()
        
        missing_table_rows = [ ( table_name, create_query_without_name ) for ( table_name, ( create_query_without_name, version_added ) ) in table_generation_dict.items() if version_added <= current_db_version and not self._TableExists( table_name ) ]
        
        if len( missing_table_rows ) > 0:
            
            missing_table_names = sorted( [ missing_table_row[0] for missing_table_row in missing_table_rows ] )
            
            self._PresentMissingTablesWarningToUser( missing_table_names )
            
            for ( table_name, create_query_without_name ) in missing_table_rows:
                
                self._Execute( create_query_without_name.format( table_name ) )
                
                cursor_transaction_wrapper.CommitAndBegin()
                
            
            self._RepairRepopulateTables( missing_table_names, cursor_transaction_wrapper )
            
            cursor_transaction_wrapper.CommitAndBegin()
            
        
        # now indices for those tables
        
        index_generation_dict = self._GetServicesIndexGenerationDict()
        
        missing_index_rows = [ ( self._GenerateIndexName( table_name, columns ), table_name, columns, unique ) for ( table_name, columns, unique, version_added ) in self._FlattenIndexGenerationDict( index_generation_dict ) if version_added <= current_db_version and not self._IndexExists( table_name, columns ) ]
        
        if len( missing_index_rows ):
            
            self._PresentMissingIndicesWarningToUser( sorted( [ index_name for ( index_name, table_name, columns, unique ) in missing_index_rows ] ) )
            
            for ( index_name, table_name, columns, unique ) in missing_index_rows:
                
                self._CreateIndex( table_name, columns, unique = unique )
                
                cursor_transaction_wrapper.CommitAndBegin()
                
            
        
