import sqlite3
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusDB
from hydrus.core import HydrusDBModule
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client.db import ClientDBServices

def GenerateMappingsTableNames( service_id: int ) -> typing.Tuple[ str, str, str, str ]:
    
    suffix = str( service_id )
    
    current_mappings_table_name = 'external_mappings.current_mappings_{}'.format( suffix )
    
    deleted_mappings_table_name = 'external_mappings.deleted_mappings_{}'.format( suffix )
    
    pending_mappings_table_name = 'external_mappings.pending_mappings_{}'.format( suffix )
    
    petitioned_mappings_table_name = 'external_mappings.petitioned_mappings_{}'.format( suffix )
    
    return ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name )
    
class ClientDBMappingsStorage( HydrusDBModule.HydrusDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices ):
        
        self.modules_services = modules_services
        
        HydrusDBModule.HydrusDBModule.__init__( self, 'client mappings storage', cursor )
        
    
    def _GetInitialIndexGenerationTuples( self ):
        
        index_generation_tuples = []
        
        return index_generation_tuples
        
    
    def CreateInitialTables( self ):
        
        pass
        
    
    def GetExpectedTableNames( self ) -> typing.Collection[ str ]:
        
        expected_table_names = []
        
        return expected_table_names
        
    
    def DropMappingsTables( self, service_id: int ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( current_mappings_table_name ) )
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( deleted_mappings_table_name ) )
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( pending_mappings_table_name ) )
        self._c.execute( 'DROP TABLE IF EXISTS {};'.format( petitioned_mappings_table_name ) )
        
    
    def GenerateMappingsTables( self, service_id: int ):
        
        ( current_mappings_table_name, deleted_mappings_table_name, pending_mappings_table_name, petitioned_mappings_table_name ) = GenerateMappingsTableNames( service_id )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;'.format( current_mappings_table_name ) )
        self._CreateIndex( current_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;'.format( deleted_mappings_table_name ) )
        self._CreateIndex( deleted_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;'.format( pending_mappings_table_name ) )
        self._CreateIndex( pending_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
        
        self._c.execute( 'CREATE TABLE IF NOT EXISTS {} ( tag_id INTEGER, hash_id INTEGER, reason_id INTEGER, PRIMARY KEY ( tag_id, hash_id ) ) WITHOUT ROWID;'.format( petitioned_mappings_table_name ) )
        self._CreateIndex( petitioned_mappings_table_name, [ 'hash_id', 'tag_id' ], unique = True )
        
    
