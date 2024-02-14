import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.importing import ClientImportGallery
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing import ClientImportSimpleURLs
from hydrus.client.importing import ClientImportWatchers
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.search import ClientSearch

MANAGEMENT_TYPE_DUMPER = 0
MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY = 1
MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER = 2
MANAGEMENT_TYPE_IMPORT_HDD = 3
MANAGEMENT_TYPE_IMPORT_WATCHER = 4 # defunct
MANAGEMENT_TYPE_PETITIONS = 5
MANAGEMENT_TYPE_QUERY = 6
MANAGEMENT_TYPE_IMPORT_URLS = 7
MANAGEMENT_TYPE_DUPLICATE_FILTER = 8
MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER = 9
MANAGEMENT_TYPE_PAGE_OF_PAGES = 10

def CreateManagementController( page_name, management_type ):
    
    new_options = CG.client_controller.new_options
    
    management_controller = ManagementController( page_name )
    
    management_controller.SetType( management_type )
    management_controller.SetVariable( 'media_sort', new_options.GetDefaultSort() )
    management_controller.SetVariable( 'media_collect', new_options.GetDefaultCollect() )
    
    return management_controller
    

def CreateManagementControllerDuplicateFilter(
    location_context = None,
    initial_predicates = None,
    page_name = None
):
    
    if location_context is None:
        
        location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
    
    if initial_predicates is None:
        
        initial_predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
    
    if page_name is None:
        
        page_name = 'duplicates'
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_DUPLICATE_FILTER )
    
    file_search_context = ClientSearch.FileSearchContext( location_context = location_context, predicates = initial_predicates )
    
    synchronised = CG.client_controller.new_options.GetBoolean( 'default_search_synchronised' )
    
    management_controller.SetVariable( 'synchronised', synchronised )
    
    management_controller.SetVariable( 'file_search_context_1', file_search_context )
    management_controller.SetVariable( 'file_search_context_2', file_search_context.Duplicate() )
    management_controller.SetVariable( 'dupe_search_type', CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
    management_controller.SetVariable( 'pixel_dupes_preference', CC.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
    management_controller.SetVariable( 'max_hamming_distance', 4 )
    
    return management_controller
    

def CreateManagementControllerImportGallery( page_name = None ):
    
    if page_name is None:
        
        page_name = 'gallery'
        
    
    gug_key_and_name = CG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
    
    multiple_gallery_import = ClientImportGallery.MultipleGalleryImport( gug_key_and_name = gug_key_and_name )
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY )
    
    management_controller.SetVariable( 'multiple_gallery_import', multiple_gallery_import )
    
    return management_controller
    

def CreateManagementControllerImportSimpleDownloader():
    
    simple_downloader_import = ClientImportSimpleURLs.SimpleDownloaderImport()
    
    formula_name = CG.client_controller.new_options.GetString( 'favourite_simple_downloader_formula' )
    
    simple_downloader_import.SetFormulaName( formula_name )
    
    management_controller = CreateManagementController( 'simple downloader', MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER )
    
    management_controller.SetVariable( 'simple_downloader_import', simple_downloader_import )
    
    return management_controller
    

def CreateManagementControllerImportHDD( paths, file_import_options: FileImportOptions.FileImportOptions, metadata_routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ], paths_to_additional_service_keys_to_tags, delete_after_success ):
    
    management_controller = CreateManagementController( 'import', MANAGEMENT_TYPE_IMPORT_HDD )
    
    hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, metadata_routers = metadata_routers, paths_to_additional_service_keys_to_tags = paths_to_additional_service_keys_to_tags, delete_after_success = delete_after_success )
    
    management_controller.SetVariable( 'hdd_import', hdd_import )
    
    return management_controller
    

def CreateManagementControllerImportMultipleWatcher( page_name = None, url = None ):
    
    if page_name is None:
        
        page_name = 'watcher'
        
    
    multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport( url = url )
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER )
    
    management_controller.SetVariable( 'multiple_watcher_import', multiple_watcher_import )
    
    return management_controller
    

def CreateManagementControllerImportURLs( page_name = None ):
    
    if page_name is None:
        
        page_name = 'url import'
        
    
    urls_import = ClientImportSimpleURLs.URLsImport()
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_URLS )
    
    management_controller.SetVariable( 'urls_import', urls_import )
    
    return management_controller
    

def CreateManagementControllerPetitions( petition_service_key ):
    
    petition_service = CG.client_controller.services_manager.GetService( petition_service_key )
    
    page_name = petition_service.GetName() + ' petitions'
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_PETITIONS )
    
    management_controller.SetVariable( 'petition_service_key', petition_service_key )
    
    management_controller.SetVariable( 'petition_type_content_type', None )
    management_controller.SetVariable( 'petition_type_status', None )
    management_controller.SetVariable( 'num_petitions_to_fetch', 40 )
    management_controller.SetVariable( 'num_files_to_show', 256 )
    
    return management_controller
    

def CreateManagementControllerQuery( page_name, file_search_context: ClientSearch.FileSearchContext, search_enabled ):
    
    location_context = file_search_context.GetLocationContext()
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_QUERY )
    
    synchronised = CG.client_controller.new_options.GetBoolean( 'default_search_synchronised' )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'search_enabled', search_enabled )
    management_controller.SetVariable( 'synchronised', synchronised )
    
    return management_controller
    

class ManagementController( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER
    SERIALISABLE_NAME = 'Client Page Management Controller'
    SERIALISABLE_VERSION = 13
    
    def __init__( self, page_name = 'page' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._page_name = page_name
        
        self._management_type = None
        
        self._last_serialisable_change_timestamp = 0
        
        self._variables = HydrusSerialisable.SerialisableDictionary()
        
    
    def __repr__( self ):
        
        return 'Management Controller: {} - {}'.format( self._management_type, self._page_name )
        
    
    def _GetSerialisableInfo( self ):
        
        # don't save these
        TRANSITORY_KEYS = { 'page' }
        
        serialisable_variables = self._variables.GetSerialisableTuple()
        
        return ( self._page_name, self._management_type, serialisable_variables )
        
    
    def _InitialiseDefaults( self ):
        
        self._variables[ 'media_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        self._variables[ 'media_collect' ] = ClientMedia.MediaCollect()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._page_name, self._management_type, serialisable_variables ) = serialisable_info
        
        self._InitialiseDefaults()
        
        self._variables.update( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_variables ) )
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                advanced_import_options = serialisable_simples[ 'advanced_import_options' ]
                paths_info = serialisable_simples[ 'paths_info' ]
                paths_to_tags = serialisable_simples[ 'paths_to_tags' ]
                delete_after_success = serialisable_simples[ 'delete_after_success' ]
                
                paths = [ path_info for ( path_type, path_info ) in paths_info if path_type != 'zip' ]
                
                exclude_deleted = advanced_import_options[ 'exclude_deleted' ]
                preimport_hash_check_type = FileImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE
                preimport_url_check_type = FileImportOptions.DO_CHECK
                preimport_url_check_looks_for_neighbours = True
                allow_decompression_bombs = False
                min_size = advanced_import_options[ 'min_size' ]
                max_size = None
                max_gif_size = None
                min_resolution = advanced_import_options[ 'min_resolution' ]
                max_resolution = None
                
                automatic_archive = advanced_import_options[ 'automatic_archive' ]
                associate_primary_urls = True
                associate_source_urls = True
                
                file_import_options = FileImportOptions.FileImportOptions()
                
                file_import_options.SetPreImportOptions( exclude_deleted, preimport_hash_check_type, preimport_url_check_type, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                file_import_options.SetPreImportURLCheckLooksForNeighbours( preimport_url_check_looks_for_neighbours )
                file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
                
                paths_to_tags = { path : { bytes.fromhex( service_key ) : tags for ( service_key, tags ) in additional_service_keys_to_tags } for ( path, additional_service_keys_to_tags ) in paths_to_tags.items() }
                
                hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_additional_service_keys_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                
                serialisable_serialisables[ 'hdd_import' ] = hdd_import.GetSerialisableTuple()
                
                del serialisable_serialisables[ 'advanced_import_options' ]
                del serialisable_serialisables[ 'paths_info' ]
                del serialisable_serialisables[ 'paths_to_tags' ]
                del serialisable_serialisables[ 'delete_after_success' ]
                
            
            new_serialisable_info = ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            page_name = 'page'
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'page_of_images_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'simple_downloader_import' ] = serialisable_serialisables[ 'page_of_images_import' ]
                
                del serialisable_serialisables[ 'page_of_images_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'thread_watcher_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'watcher_import' ] = serialisable_serialisables[ 'thread_watcher_import' ]
                
                del serialisable_serialisables[ 'thread_watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'gallery_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'multiple_gallery_import' ] = serialisable_serialisables[ 'gallery_import' ]
                
                del serialisable_serialisables[ 'gallery_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'watcher_import' in serialisable_serialisables:
                
                watcher = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_serialisables[ 'watcher_import' ] )
                
                management_type = MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
                
                multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport()
                
                multiple_watcher_import.AddWatcher( watcher )
                
                serialisable_multiple_watcher_import = multiple_watcher_import.GetSerialisableTuple()
                
                serialisable_serialisables[ 'multiple_watcher_import' ] = serialisable_multiple_watcher_import
                
                del serialisable_serialisables[ 'watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if page_name.startswith( '[USER]' ) and len( page_name ) > 6:
                
                page_name = page_name[6:]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
                
                if 'duplicate_filter_file_domain' in serialisable_keys:
                    
                    del serialisable_keys[ 'duplicate_filter_file_domain' ]
                    
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
                
                file_search_context = ClientSearch.FileSearchContext( location_context = location_context, predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
                
                serialisable_serialisables[ 'file_search_context' ] = file_search_context.GetSerialisableTuple()
                
                serialisable_simples[ 'both_files_match' ] = False
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'media_collect' in serialisable_simples:
                
                try:
                    
                    old_collect = serialisable_simples[ 'media_collect' ]
                    
                    if old_collect is None:
                        
                        old_collect = []
                        
                    
                    namespaces = [ n for ( t, n ) in old_collect if t == 'namespace' ]
                    rating_service_keys = [ bytes.fromhex( r ) for ( t, r ) in old_collect if t == 'rating' ]
                    
                except:
                    
                    namespaces = []
                    rating_service_keys = []
                    
                
                media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys )
                
                serialisable_serialisables[ 'media_collect' ] = media_collect.GetSerialisableTuple()
                
                del serialisable_simples[ 'media_collect' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 10, new_serialisable_info )
            
        
        if version == 10:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'file_service' in serialisable_keys:
                
                file_service_key_encoded = serialisable_keys[ 'file_service' ]
                
                try:
                    
                    file_service_key = bytes.fromhex( file_service_key_encoded )
                    
                except:
                    
                    file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                    
                
                del serialisable_keys[ 'file_service' ]
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
                
                serialisable_serialisables[ 'location_context' ] = location_context.GetSerialisableTuple()
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 11, new_serialisable_info )
            
        
        if version == 11:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            # notice I rename them to _key here!
            # we had 'page' and 'petition_service' before, so adding the key brings us in line with elsewhere
            keys = { name + '_key' : bytes.fromhex( key ) for ( name, key ) in serialisable_keys.items() }
            
            simples = dict( serialisable_simples )
            
            serialisables = { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in list(serialisable_serialisables.items()) }
            
            variables = HydrusSerialisable.SerialisableDictionary()
            
            variables.update( keys )
            variables.update( simples )
            variables.update( serialisables )
            
            if management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
                
                value = CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
                if 'both_files_match' in variables:
                    
                    if variables[ 'both_files_match' ]:
                        
                        value = CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
                        
                    
                    del variables[ 'both_files_match' ]
                    
                
                variables[ 'dupe_search_type' ] = value
                
                default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
                
                file_search_context = ClientSearch.FileSearchContext( location_context = default_location_context, predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
                
                variables[ 'file_search_context_1' ] = file_search_context
                variables[ 'file_search_context_2' ] = file_search_context.Duplicate()
                
                if 'file_search_context' in variables:
                    
                    variables[ 'file_search_context_1' ] = variables[ 'file_search_context' ]
                    
                    del variables[ 'file_search_context' ]
                    
                
            
            serialisable_variables = variables.GetSerialisableTuple()
            
            new_serialisable_info = ( page_name, management_type, serialisable_variables )
            
            return ( 12, new_serialisable_info )
            
        
        if version == 12:
            
            ( page_name, management_type, serialisable_variables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_PETITIONS:
                
                variables = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_variables )
                
                variables[ 'petition_type_content_type' ] = None
                variables[ 'petition_type_status' ] = None
                variables[ 'num_petitions_to_fetch' ] = 40
                variables[ 'num_files_to_show' ] = 256
                
                serialisable_variables = variables.GetSerialisableTuple()
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_variables )
            
            return ( 13, new_serialisable_info )
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
            
            hdd_import = self._variables[ 'hdd_import' ]
            
            d[ 'hdd_import' ] = hdd_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
            
            simple_downloader_import = self._variables[ 'simple_downloader_import' ]
            
            d[ 'simple_downloader_import' ] = simple_downloader_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
            
            multiple_gallery_import = self._variables[ 'multiple_gallery_import' ]
            
            d[ 'multiple_gallery_import' ] = multiple_gallery_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
            
            multiple_watcher_import = self._variables[ 'multiple_watcher_import' ]
            
            d[ 'multiple_watcher_import' ] = multiple_watcher_import.GetAPIInfoDict( simple )
            
        elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
            
            urls_import = self._variables[ 'urls_import' ]
            
            d[ 'urls_import' ] = urls_import.GetAPIInfoDict( simple )
            
        
        return d
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        # this is hacky, but it has a decent backstop and it is easier than keeping the management controller updated with this oft-changing thing all the time when we nearly always have it duped somewhere else anyway
        
        source_names = [
            'file_search_context',
            'file_search_context_1',
            'multiple_gallery_import',
            'multiple_watcher_import',
            'hdd_import',
            'simple_downloader_import',
            'urls_import'
        ]
        
        for source_name in source_names:
            
            if source_name in self._variables:
                
                source = self._variables[ source_name ]
                
                if hasattr( source, 'GetFileImportOptions' ):
                    
                    file_import_options = source.GetFileImportOptions()
                    
                    location_context = FileImportOptions.GetRealFileImportOptions( file_import_options, FileImportOptions.IMPORT_TYPE_LOUD ).GetDestinationLocationContext()
                    
                    return location_context
                    
                elif hasattr( source, 'GetLocationContext' ):
                    
                    location_context = source.GetLocationContext()
                    
                    return location_context
                    
                
            
        
        if 'petition_service_key' in self._variables:
            
            petition_service_key = self._variables[ 'petition_service_key' ]
            
            try:
                
                petition_service = CG.client_controller.services_manager.GetService( petition_service_key )
                
                petition_service_type = petition_service.GetServiceType()
                
                if petition_service_type in HC.LOCAL_FILE_SERVICES or petition_service_type == HC.FILE_REPOSITORY:
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( petition_service_key )
                    
                else:
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
                    
                
                return location_context
                
            except HydrusExceptions.DataMissing:
                
                pass
                
        
        if 'location_context' in self._variables:
            
            return self._variables[ 'location_context' ]
            
        
        return ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
    
    def GetNumSeeds( self ):
        
        try:
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                hdd_import = self._variables[ 'hdd_import' ]
                
                return hdd_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                simple_downloader_import = self._variables[ 'simple_downloader_import' ]
                
                return simple_downloader_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                multiple_gallery_import = self._variables[ 'multiple_gallery_import' ]
                
                return multiple_gallery_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                multiple_watcher_import = self._variables[ 'multiple_watcher_import' ]
                
                return multiple_watcher_import.GetNumSeeds()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                urls_import = self._variables[ 'urls_import' ]
                
                return urls_import.GetNumSeeds()
                
            
        except KeyError:
            
            return 0
            
        
        return 0
        
    
    def GetPageName( self ):
        
        return self._page_name
        
    
    def GetType( self ):
        
        return self._management_type
        
    
    def GetValueRange( self ):
        
        if self.IsImporter():
            
            try:
                
                if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                    
                    importer = self._variables[ 'hdd_import' ]
                    
                elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                    
                    importer = self._variables[ 'simple_downloader_import' ]
                    
                elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                    
                    importer = self._variables[ 'multiple_gallery_import' ]
                    
                elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                    
                    importer = self._variables[ 'multiple_watcher_import' ]
                    
                elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                    
                    importer = self._variables[ 'urls_import' ]
                    
                else:
                    
                    raise KeyError()
                    
                
                return importer.GetValueRange()
                
            except KeyError:
                
                return ( 0, 0 )
                
            
        else:
            
            return ( 0, 0 )
            
        
    
    def GetVariable( self, name ):
        
        return self._variables[ name ]
        
    
    def HasSerialisableChangesSince( self, since_timestamp ):
        
        if self.IsImporter():
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                importer = self._variables[ 'hdd_import' ]
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                importer = self._variables[ 'simple_downloader_import' ]
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                importer = self._variables[ 'multiple_gallery_import' ]
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                importer = self._variables[ 'multiple_watcher_import' ]
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                importer = self._variables[ 'urls_import' ]
                
            
            if importer.HasSerialisableChangesSince( since_timestamp ):
                
                return True
                
            
        
        return self._last_serialisable_change_timestamp > since_timestamp
        
    
    def HasVariable( self, name ):
        
        return name in self._variables
        
    
    def IsImporter( self ):
        
        return self._management_type in ( MANAGEMENT_TYPE_IMPORT_HDD, MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER, MANAGEMENT_TYPE_IMPORT_URLS )
        
    
    def NotifyLoadingWithHashes( self ):
        
        if self.HasVariable( 'file_search_context' ):
            
            file_search_context = self.GetVariable( 'file_search_context' )
            
            file_search_context.SetComplete()
            
        
    
    def SetDirty( self ):
        
        self._SerialisableChangeMade()
        
    
    def SetPageName( self, name ):
        
        if name != self._page_name:
            
            self._page_name = name
            
            self._SerialisableChangeMade()
            
        
    
    def SetType( self, management_type ):
        
        self._management_type = management_type
        
        self._InitialiseDefaults()
        
        self._SerialisableChangeMade()
        
    
    def SetVariable( self, name, value ):
        
        if name in self._variables:
            
            existing_value = self._variables[ name ]
            
            if isinstance( value, type( existing_value ) ):
                
                if isinstance( value, HydrusSerialisable.SerialisableBase ):
                    
                    if value is existing_value:
                        
                        # assume that it was changed and we can't detect that
                        self._SerialisableChangeMade()
                        
                        return
                        
                    
                    if value.GetSerialisableTuple() == existing_value.GetSerialisableTuple():
                        
                        return
                        
                    
                elif value == self._variables[ name ]:
                    
                    return
                    
                
            
        
        self._variables[ name ] = value
        
        self._SerialisableChangeMade()
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER ] = ManagementController
