from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

class LocationImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_LOCATION_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Location Import Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._automatically_archives = False
        self._associate_primary_urls = True
        self._associate_source_urls = True
        self._do_automatic_archive_on_already_in_db_files = True
        self._do_import_destinations_on_already_in_db_files = False
        
        try:
            
            fallback = CG.client_controller.services_manager.GetLocalMediaFileServices()[0].GetServiceKey()
            
        except Exception as e:
            
            fallback = CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY
            
        
        self._import_destination_location_context = ClientLocation.LocationContext.STATICCreateSimple( fallback )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_destination_location_context = self._import_destination_location_context.GetSerialisableTuple()
        
        return (
            serialisable_import_destination_location_context,
            self._automatically_archives,
            self._associate_primary_urls,
            self._associate_source_urls,
            self._do_automatic_archive_on_already_in_db_files,
            self._do_import_destinations_on_already_in_db_files
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_import_destination_location_context,
            self._automatically_archives,
            self._associate_primary_urls,
            self._associate_source_urls,
            self._do_automatic_archive_on_already_in_db_files,
            self._do_import_destinations_on_already_in_db_files
        ) = serialisable_info
        
        self._import_destination_location_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_destination_location_context )
        
    
    def AutomaticallyArchives( self ) -> bool:
        
        return self._automatically_archives
        
    
    def CheckReadyToImport( self ) -> None:
        
        if self._import_destination_location_context.IsEmpty():
            
            raise HydrusExceptions.FileImportBlockException( 'There is no import destination set in the Location Import Options!' )
            
        
    
    def DoAutomaticArchiveOnAlreadyInDBFiles( self ) -> bool:
        
        return self._do_automatic_archive_on_already_in_db_files
        
    
    def DoImportDestinationsOnAlreadyInDBFiles( self ) -> bool:
        
        return self._do_import_destinations_on_already_in_db_files
        
    
    def GetAlreadyInDBPostImportContentUpdatePackage( self, media_result: ClientMediaResult.MediaResult ):
        
        # this guy is actually called by two guys, both the file seed and the import job, so expect it to do a bit of redundant work in a normal import
        # this is because we need to run it in both an isolated file import job from the client api (file import job, no file seed) and a 'url checked, already in db' (file seed, no file import job)
        # but when we have 'novel url, file already in db', we'll be running it in the file import job and in the file seed post-import writecontentupdates. no worries, even if the media result isn't updated yet this is idempotent
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        if self._do_import_destinations_on_already_in_db_files:
            
            desired_file_service_keys = self._import_destination_location_context.current_service_keys
            current_file_service_keys = media_result.GetLocationsManager().GetCurrent()
            
            file_service_keys_to_add_to = set( desired_file_service_keys ).difference( current_file_service_keys )
            
            if len( file_service_keys_to_add_to ) > 0:
                
                file_info_manager = media_result.GetFileInfoManager()
                now_ms = HydrusTime.GetNowMS()
                
                for service_key in file_service_keys_to_add_to:
                    
                    content_update_package.AddContentUpdate( service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( file_info_manager, now_ms ) ) )
                    
                
            
        
        #
        
        if self._do_automatic_archive_on_already_in_db_files:
            
            if self._automatically_archives:
                
                hashes = { media_result.GetHash() }
                
                content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) )
                
            
        
        return content_update_package
        
    
    def GetDestinationLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._import_destination_location_context
        
    
    def GetSummary( self ):
        
        statements = []
        
        #
        
        if self._automatically_archives:
            
            statements.append( 'automatically archiving' )
            
        
        #
        
        summary = '\n'.join( statements )
        
        return summary
        
    
    def SetAutomaticallyArchives( self, value: bool ):
        
        self._automatically_archives = value
        
    
    def SetDestinationLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._import_destination_location_context = location_context.Duplicate()
        
    
    def SetDoAutomaticArchiveOnAlreadyInDBFiles( self, value: bool ):
        
        self._do_automatic_archive_on_already_in_db_files = value
        
    
    def SetDoImportDestinationsOnAlreadyInDBFiles( self, value: bool ):
        
        self._do_import_destinations_on_already_in_db_files = value
        
    
    def SetShouldAssociatePrimaryURLs( self, value: bool ):
        
        self._associate_primary_urls = value
        
    
    def SetShouldAssociateSourceURLs( self, value: bool ):
        
        self._associate_source_urls = value
        
    
    def ShouldAssociatePrimaryURLs( self ) -> bool:
        
        return self._associate_primary_urls
        
    
    def ShouldAssociateSourceURLs( self ) -> bool:
        
        return self._associate_source_urls
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_LOCATION_IMPORT_OPTIONS ] = LocationImportOptions
