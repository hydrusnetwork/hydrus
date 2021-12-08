import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client import ClientServices
from hydrus.client.db import ClientDBModule

class ClientDBMasterServices( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        ClientDBModule.ClientDBModule.__init__( self, 'client services master', cursor )
        
        self._service_ids_to_services = {}
        self._service_keys_to_service_ids = {}
        
        self.local_update_service_id = None
        self.trash_service_id = None
        self.combined_local_file_service_id = None
        self.combined_file_service_id = None
        self.combined_deleted_file_service_id = None
        self.combined_tag_service_id = None
        
        self._InitCaches()
        
    
    def _GetCriticalTableNames( self ) -> typing.Collection[ str ]:
        
        return {
            'main.services'
        }
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.services' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER PRIMARY KEY AUTOINCREMENT, service_key BLOB_BYTES UNIQUE, service_type INTEGER, name TEXT, dictionary_string TEXT );', 400 )
        }
        
    
    def _InitCaches( self ):
        
        if self._Execute( 'SELECT 1 FROM sqlite_master WHERE name = ?;', ( 'services', ) ).fetchone() is not None:
            
            all_data = self._Execute( 'SELECT service_id, service_key, service_type, name, dictionary_string FROM services;' ).fetchall()
            
            for ( service_id, service_key, service_type, name, dictionary_string ) in all_data:
                
                dictionary = HydrusSerialisable.CreateFromString( dictionary_string )
                
                service = ClientServices.GenerateService( service_key, service_type, name, dictionary )
                
                self._service_ids_to_services[ service_id ] = service
                
                self._service_keys_to_service_ids[ service_key ] = service_id
                
            
            self.local_update_service_id = self.GetServiceId( CC.LOCAL_UPDATE_SERVICE_KEY )
            self.trash_service_id = self.GetServiceId( CC.TRASH_SERVICE_KEY )
            self.combined_local_file_service_id = self.GetServiceId( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            self.combined_file_service_id = self.GetServiceId( CC.COMBINED_FILE_SERVICE_KEY )
            
            try:
                
                self.combined_deleted_file_service_id = self.GetServiceId( CC.COMBINED_DELETED_FILE_SERVICE_KEY )
                
            except HydrusExceptions.DataMissing:
                
                # version 465 it might not be in yet
                
                pass
                
            
            self.combined_tag_service_id = self.GetServiceId( CC.COMBINED_TAG_SERVICE_KEY )
            
        
    
    def AddService( self, service_key, service_type, name, dictionary: HydrusSerialisable.SerialisableBase ) -> int:
        
        dictionary_string = dictionary.DumpToString()
        
        self._Execute( 'INSERT INTO services ( service_key, service_type, name, dictionary_string ) VALUES ( ?, ?, ?, ? );', ( sqlite3.Binary( service_key ), service_type, name, dictionary_string ) )
        
        service_id = self._GetLastRowId()
        
        service = ClientServices.GenerateService( service_key, service_type, name, dictionary )
        
        self._service_ids_to_services[ service_id ] = service
        self._service_keys_to_service_ids[ service_key ] = service_id
        
        if service_key == CC.LOCAL_UPDATE_SERVICE_KEY:
            
            self.local_update_service_id = service_id
            
        elif service_key == CC.TRASH_SERVICE_KEY:
            
            self.trash_service_id = service_id
            
        elif service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
            
            self.combined_local_file_service_id = service_id
            
        elif service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            self.combined_file_service_id = service_id
            
        elif service_key == CC.COMBINED_DELETED_FILE_SERVICE_KEY:
            
            self.combined_deleted_file_service_id = service_id
            
        elif service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            self.combined_tag_service_id = service_id
            
        
        return service_id
        
    
    def DeleteService( self, service_id ):
        
        if service_id in self._service_ids_to_services:
            
            service_key = self._service_ids_to_services[ service_id ].GetServiceKey()
            
            del self._service_ids_to_services[ service_id ]
            
            if service_key in self._service_keys_to_service_ids:
                
                del self._service_keys_to_service_ids[ service_key ]
                
            
        
        self._Execute( 'DELETE FROM services WHERE service_id = ?;', ( service_id, ) )
        
    
    def FileServiceIsCoveredByAllLocalFiles( self, service_id ) -> bool:
        
        service_type = self.GetService( service_id ).GetServiceType()
        
        return service_type in HC.FILE_SERVICES_COVERED_BY_COMBINED_LOCAL_FILE
        
    
    def GetNonDupeName( self, name ) -> str:
        
        existing_names = { service.GetName() for service in self._service_ids_to_services.values() }
        
        return HydrusData.GetNonDupeName( name, existing_names )
        
    
    def GetService( self, service_id ) -> ClientServices.Service:
        
        if service_id in self._service_ids_to_services:
            
            return self._service_ids_to_services[ service_id ]
            
        
        raise HydrusExceptions.DataMissing( 'Service id error in database: id "{}" does not exist!'.format( service_id ) )
        
    
    def GetServices( self, limited_types = HC.ALL_SERVICES ):
        
        return [ service for service in self._service_ids_to_services.values() if service.GetServiceType() in limited_types ]
        
    
    def GetServiceId( self, service_key: bytes ) -> int:
        
        if service_key in self._service_keys_to_service_ids:
            
            return self._service_keys_to_service_ids[ service_key ]
            
        
        raise HydrusExceptions.DataMissing( 'Service id error in database: key "{}" does not exist!'.format( service_key.hex() ) )
        
    
    def GetServiceIds( self, service_types ) -> typing.Set[ int ]:
        
        return { service_id for ( service_id, service ) in self._service_ids_to_services.items() if service.GetServiceType() in service_types }
        
    
    def GetServiceIdsToServiceKeys( self ) -> typing.Dict[ int, bytes ]:
        
        return { service_id : service_key for ( service_key, service_id ) in self._service_keys_to_service_ids.items() }
        
    
    def GetServiceKeys( self ) -> typing.Set[ bytes ]:
        
        return set( self._service_keys_to_service_ids.keys() )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> typing.List[ typing.Tuple[ str, str ] ]:
        
        return []
        
    
    def LocationSearchContextIsCoveredByCombinedLocalFiles( self, location_search_context: ClientSearch.LocationSearchContext ):
        
        if location_search_context.SearchesDeleted():
            
            return False
            
        
        service_ids = { self.GetServiceId( service_key ) for service_key in location_search_context.current_service_keys }
        
        for service_id in service_ids:
            
            if not self.FileServiceIsCoveredByAllLocalFiles( service_id ):
                
                return False
                
            
        
        return True
        
    
    def UpdateService( self, service: ClientServices.Service ):
        
        ( service_key, service_type, name, dictionary ) = service.ToTuple()
        
        service_id = self.GetServiceId( service_key )
        
        dictionary_string = dictionary.DumpToString()
        
        self._Execute( 'UPDATE services SET name = ?, dictionary_string = ? WHERE service_id = ?;', ( name, dictionary_string, service_id ) )
        
        self._service_ids_to_services[ service_id ] = service
        
        service.SetClean()
        
