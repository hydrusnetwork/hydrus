import collections.abc
import itertools
import sqlite3
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client.db import ClientDBModule
from hydrus.client.search import ClientSearchFileSearchContext

class FileSearchContextLeaf( object ):
    
    def __init__( self, file_service_id: int, tag_service_id: int ):
        
        # special thing about a leaf is that it has a specific current domain in the caches
        # no all known files or deleted files here. leaf might not be file cross-referenced, but it does cover something we can search fast
        
        # it should get tag display type at some point, maybe current/pending too
        
        self.file_service_id = file_service_id
        self.tag_service_id = tag_service_id
        
    
class FileSearchContextBranch( object ):
    
    def __init__( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext, file_service_ids: collections.abc.Collection[ int ], tag_service_ids: collections.abc.Collection[ int ], file_location_is_cross_referenced: bool ):
        
        self.file_search_context = file_search_context
        
        self.file_service_ids = file_service_ids
        self.tag_service_ids = tag_service_ids
        self.file_location_is_cross_referenced = file_location_is_cross_referenced
        
    
    def FileLocationIsCrossReferenced( self ) -> bool:
        
        return self.file_location_is_cross_referenced
        
    
    def GetFileSearchContext( self ) -> ClientSearchFileSearchContext.FileSearchContext:
        
        return self.file_search_context
        
    
    def IterateLeaves( self ):
        
        for ( file_service_id, tag_service_id ) in itertools.product( self.file_service_ids, self.tag_service_ids ):
            
            yield FileSearchContextLeaf( file_service_id, tag_service_id )
            
        
    
    def IterateTableIdPairs( self ):
        
        for ( file_service_id, tag_service_id ) in itertools.product( self.file_service_ids, self.tag_service_ids ):
            
            yield ( file_service_id, tag_service_id )
            
        
    
class ClientDBMasterServices( ClientDBModule.ClientDBModule ):
    
    def __init__( self, cursor: sqlite3.Cursor ):
        
        super().__init__( 'client services master', cursor )
        
        self._service_ids_to_services = {}
        self._service_keys_to_service_ids = {}
        
        self.local_update_service_id = None
        self.trash_service_id = None
        self.combined_local_file_service_id = None
        self.combined_local_media_service_id = None
        self.combined_file_service_id = None
        self.combined_deleted_file_service_id = None
        self.combined_tag_service_id = None
        
        self._InitCaches()
        
    
    def _GetCriticalTableNames( self ) -> collections.abc.Collection[ str ]:
        
        return {
            'main.services'
        }
        
    
    def _GetInitialTableGenerationDict( self ) -> dict:
        
        return {
            'main.services' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER PRIMARY KEY AUTOINCREMENT, service_key BLOB_BYTES UNIQUE, service_type INTEGER, name TEXT, dictionary_string TEXT );', 400 ),
            'main.service_info' : ( 'CREATE TABLE IF NOT EXISTS {} ( service_id INTEGER, info_type INTEGER, info INTEGER, PRIMARY KEY ( service_id, info_type ) );', 400 )
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
                self.combined_local_media_service_id = self.GetServiceId( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
            except HydrusExceptions.DataMissing:
                
                # version 465/486 it might not be in yet
                
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
            
        elif service_key == CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY:
            
            self.combined_local_media_service_id = service_id
            
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
        
    
    def GetFileSearchContextBranch( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ) -> FileSearchContextBranch:
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        ( file_service_keys, file_location_is_cross_referenced ) = location_context.GetCoveringCurrentFileServiceKeys()
        
        search_file_service_ids = []
        
        for file_service_key in file_service_keys:
            
            try:
                
                search_file_service_id = self.GetServiceId( file_service_key )
                
            except HydrusExceptions.DataMissing:
                
                HydrusData.ShowText( 'A query was run for a file service that does not exist! If you just removed a service, you might want to try checking the search and/or restarting the client.' )
                
                continue
                
            
            search_file_service_ids.append( search_file_service_id )
            
        
        if tag_context.IsAllKnownTags():
            
            search_tag_service_ids = self.GetServiceIds( HC.REAL_TAG_SERVICES )
            
        else:
            
            try:
                
                search_tag_service_ids = ( self.GetServiceId( tag_context.service_key ), )
                
            except HydrusExceptions.DataMissing:
                
                HydrusData.ShowText( 'A query was run for a tag service that does not exist! If you just removed a service, you might want to try checking the search and/or restarting the client.' )
                
                search_tag_service_ids = []
                
            
        
        return FileSearchContextBranch( file_search_context, search_file_service_ids, search_tag_service_ids, file_location_is_cross_referenced )
        
    
    def GetNonDupeName( self, name ) -> str:
        
        existing_names = { service.GetName() for service in self._service_ids_to_services.values() }
        
        return HydrusData.GetNonDupeName( name, existing_names, do_casefold = True )
        
    
    def GetService( self, service_id ) -> typing.Any:
        
        if service_id in self._service_ids_to_services:
            
            return self._service_ids_to_services[ service_id ]
            
        
        raise HydrusExceptions.DataMissing( 'Service id error in database: id "{}" does not exist!'.format( service_id ) )
        
    
    def GetServices( self, limited_types = HC.ALL_SERVICES ):
        
        return [ service for service in self._service_ids_to_services.values() if service.GetServiceType() in limited_types ]
        
    
    def GetServiceId( self, service_key: bytes ) -> int:
        
        if service_key in self._service_keys_to_service_ids:
            
            return self._service_keys_to_service_ids[ service_key ]
            
        
        raise HydrusExceptions.DataMissing( 'Service id error in database: key "{}" does not exist!'.format( service_key.hex() ) )
        
    
    def GetServiceIds( self, service_types ) -> set[ int ]:
        
        return { service_id for ( service_id, service ) in self._service_ids_to_services.items() if service.GetServiceType() in service_types }
        
    
    def GetServiceIdsToServiceKeys( self ) -> dict[ int, bytes ]:
        
        return { service_id : service_key for ( service_key, service_id ) in self._service_keys_to_service_ids.items() }
        
    
    def GetServiceKey( self, service_id: int ) -> bytes:
        
        return self.GetService( service_id ).GetServiceKey()
        
    
    def GetServiceKeys( self ) -> set[ bytes ]:
        
        return set( self._service_keys_to_service_ids.keys() )
        
    
    def GetServiceType( self, service_id ) -> ClientServices.Service:
        
        if service_id in self._service_ids_to_services:
            
            return self._service_ids_to_services[ service_id ].GetServiceType()
            
        
        raise HydrusExceptions.DataMissing( 'Service id error in database: id "{}" does not exist!'.format( service_id ) )
        
    
    def GetTablesAndColumnsThatUseDefinitions( self, content_type: int ) -> list[ tuple[ str, str ] ]:
        
        return []
        
    
    def LocationContextIsCoveredByCombinedLocalFiles( self, location_context: ClientLocation.LocationContext ):
        
        if location_context.IncludesDeleted():
            
            return False
            
        
        service_ids = { self.GetServiceId( service_key ) for service_key in location_context.current_service_keys }
        
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
        
