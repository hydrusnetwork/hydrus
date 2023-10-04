import collections
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client.db import ClientDBDefinitionsCache
from hydrus.client.db import ClientDBMaster
from hydrus.client.db import ClientDBModule
from hydrus.client.db import ClientDBServices

class ClientDBRatings( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor, modules_services: ClientDBServices.ClientDBMasterServices ):
        
        self.modules_services = modules_services
        
        ClientDBModule.ClientDBModule.__init__( self, 'client ratings', cursor )
        
    
    def _GetInitialIndexGenerationDict( self ) -> dict:
        
        index_generation_dict = {}
        
        index_generation_dict[ 'main.local_ratings' ] = [
            ( [ 'hash_id' ], False, 400 ),
            ( [ 'rating' ], False, 400 )
        ]
        
        index_generation_dict[ 'main.local_incdec_ratings' ] = [
            ( [ 'hash_id' ], False, 400 ),
            ( [ 'rating' ], False, 400 )
        ]
        
        return index_generation_dict
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.local_ratings' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, hash_id INTEGER, rating REAL, PRIMARY KEY ( service_id, hash_id ) );', 400 ),
            'main.local_incdec_ratings' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, hash_id INTEGER, rating INTEGER, PRIMARY KEY ( service_id, hash_id ) );', 400 )
        }
        
    
    def Drop( self, service_id: int ):
        
        self._Execute( 'DELETE FROM local_ratings WHERE service_id = ?;', ( service_id, ) )
        self._Execute( 'DELETE FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) )
        
    
    def GetHashIdsToRatings( self, hash_ids_table_name ):
        
        hash_ids_to_local_star_ratings = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in self._Execute( 'SELECT service_id, hash_id, rating FROM {} CROSS JOIN local_ratings USING ( hash_id );'.format( hash_ids_table_name ) ) ) )
        hash_ids_to_local_incdec_ratings = HydrusData.BuildKeyToListDict( ( ( hash_id, ( service_id, rating ) ) for ( service_id, hash_id, rating ) in self._Execute( 'SELECT service_id, hash_id, rating FROM {} CROSS JOIN local_incdec_ratings USING ( hash_id );'.format( hash_ids_table_name ) ) ) )
        
        hash_ids_to_local_ratings = collections.defaultdict( list )
        
        for ( hash_id, info_list ) in hash_ids_to_local_star_ratings.items():
            
            hash_ids_to_local_ratings[ hash_id ].extend( info_list )
            
        
        for ( hash_id, info_list ) in hash_ids_to_local_incdec_ratings.items():
            
            hash_ids_to_local_ratings[ hash_id ].extend( info_list )
            
        
        return hash_ids_to_local_ratings
        
    
    def GetIncDecServiceCount( self, service_id: int ):
        
        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM local_incdec_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return info
        
    
    def GetStarredServiceCount( self, service_id: int ):
        
        ( info, ) = self._Execute( 'SELECT COUNT( * ) FROM local_ratings WHERE service_id = ?;', ( service_id, ) ).fetchone()
        
        return info
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        tables_and_columns = []
        
        return tables_and_columns
        
    
    def SetRating( self, service_id, hash_ids, rating ):
        
        service_type = self.modules_services.GetServiceType( service_id )
        
        if service_type in HC.STAR_RATINGS_SERVICES:
            
            ratings_added = 0
            
            self._ExecuteMany( 'DELETE FROM local_ratings WHERE service_id = ? AND hash_id = ?;', ( ( service_id, hash_id ) for hash_id in hash_ids ) )
            
            ratings_added -= self._GetRowCount()
            
            if rating is not None:
                
                self._ExecuteMany( 'INSERT INTO local_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                
                ratings_added += self._GetRowCount()
                
            
            self._Execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
            
        elif service_type == HC.LOCAL_RATING_INCDEC:
            
            ratings_added = 0
            
            self._ExecuteMany( 'DELETE FROM local_incdec_ratings WHERE service_id = ? AND hash_id = ?;', ( ( service_id, hash_id ) for hash_id in hash_ids ) )
            
            ratings_added -= self._GetRowCount()
            
            if rating != 0:
                
                self._ExecuteMany( 'INSERT INTO local_incdec_ratings ( service_id, hash_id, rating ) VALUES ( ?, ?, ? );', [ ( service_id, hash_id, rating ) for hash_id in hash_ids ] )
                
                ratings_added += self._GetRowCount()
                
            
            self._Execute( 'UPDATE service_info SET info = info + ? WHERE service_id = ? AND info_type = ?;', ( ratings_added, service_id, HC.SERVICE_INFO_NUM_FILE_HASHES ) )
            
        
    
