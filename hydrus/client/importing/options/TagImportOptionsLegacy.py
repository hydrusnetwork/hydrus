from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client.importing.options import TagFilteringImportOptions
from hydrus.client.importing.options import TagImportOptions

class TagImportOptionsLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS_LEGACY
    SERIALISABLE_NAME = 'Tag Import Options (Legacy)'
    SERIALISABLE_VERSION = 9
    
    def __init__(
        self,
        fetch_tags_even_if_url_recognised_and_file_already_in_db = False,
        fetch_tags_even_if_hash_recognised_and_file_already_in_db = False,
        tag_filtering_import_options = None,
        tag_import_options = None,
        is_default = False
    ):
        
        super().__init__()
        
        if tag_filtering_import_options is None:
            
            tag_filtering_import_options = TagFilteringImportOptions.TagFilteringImportOptions()
            
        
        if tag_import_options is None:
            
            tag_import_options = TagImportOptions.TagImportOptions()
            
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db
        
        self._tag_filtering_import_options = tag_filtering_import_options
        self._tag_import_options = tag_import_options
        
        self._is_default = is_default
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_tag_filtering_import_options = self._tag_filtering_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_filtering_import_options, serialisable_tag_import_options, self._is_default )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._fetch_tags_even_if_url_recognised_and_file_already_in_db, self._fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_filtering_import_options, serialisable_tag_import_options, self._is_default ) = serialisable_info
        
        self._tag_filtering_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filtering_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            safe_service_keys_to_namespaces = old_serialisable_info
            
            safe_service_keys_to_additional_tags = {}
            
            new_serialisable_info = ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            fetch_tags_even_if_url_recognised_and_file_already_in_db = False
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            tag_blacklist = HydrusTags.TagFilter()
            
            serialisable_tag_blacklist = tag_blacklist.GetSerialisableTuple()
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            serialisable_get_all_service_keys = []
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_get_all_service_keys, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_get_all_service_keys, safe_service_keys_to_namespaces, safe_service_keys_to_additional_tags ) = old_serialisable_info
            
            fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db
            
            get_all_service_keys = { bytes.fromhex( encoded_service_key ) for encoded_service_key in serialisable_get_all_service_keys }
            service_keys_to_namespaces = { bytes.fromhex( service_key ) : set( namespaces ) for ( service_key, namespaces ) in list(safe_service_keys_to_namespaces.items()) }
            service_keys_to_additional_tags = { bytes.fromhex( service_key ) : set( tags ) for ( service_key, tags ) in list(safe_service_keys_to_additional_tags.items()) }
            
            service_keys_to_service_tag_import_options = {}
            
            service_keys = set()
            
            service_keys.update( get_all_service_keys )
            service_keys.update( list(service_keys_to_namespaces.keys()) )
            service_keys.update( list(service_keys_to_additional_tags.keys()) )
            
            for service_key in service_keys:
                
                get_tags = False
                namespaces = []
                additional_tags = []
                
                if service_key in service_keys_to_namespaces:
                    
                    namespaces = service_keys_to_namespaces[ service_key ]
                    
                
                if service_key in get_all_service_keys or 'all namespaces' in namespaces:
                    
                    get_tags = True
                    
                
                if service_key in service_keys_to_additional_tags:
                    
                    additional_tags = service_keys_to_additional_tags[ service_key ]
                    
                
                ( to_new_files, to_already_in_inbox, to_already_in_archive, only_add_existing_tags ) = ( True, True, True, False )
                
                service_tag_import_options = TagImportOptions.ServiceTagImportOptions( get_tags = get_tags, additional_tags = additional_tags, to_new_files = to_new_files, to_already_in_inbox = to_already_in_inbox, to_already_in_archive = to_already_in_archive, only_add_existing_tags = only_add_existing_tags )
                
                service_keys_to_service_tag_import_options[ service_key ] = service_tag_import_options
                
            
            serialisable_service_keys_to_service_tag_import_options = [ ( service_key.hex(), service_tag_import_options.GetSerialisableTuple() ) for ( service_key, service_tag_import_options ) in list(service_keys_to_service_tag_import_options.items()) ]
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options ) = old_serialisable_info
            
            is_default = False
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, is_default )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, serialisable_service_keys_to_service_tag_import_options, is_default ) = old_serialisable_info
            
            tag_whitelist = []
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, tag_whitelist, serialisable_service_keys_to_service_tag_import_options, is_default )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_blacklist, tag_whitelist, serialisable_service_keys_to_service_tag_import_options, is_default ) = old_serialisable_info
            
            tag_blacklist = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_blacklist )
            
            service_keys_to_service_tag_import_options = { bytes.fromhex( encoded_service_key ) : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_service_tag_import_options ) for ( encoded_service_key, serialisable_service_tag_import_options ) in serialisable_service_keys_to_service_tag_import_options }
            
            tag_filtering_import_options = TagFilteringImportOptions.TagFilteringImportOptions( tag_blacklist = tag_blacklist, tag_whitelist = tag_whitelist )
            tag_import_options = TagImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
            
            serialisable_tag_filtering_import_options = tag_filtering_import_options.GetSerialisableTuple()
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db, serialisable_tag_filtering_import_options, serialisable_tag_import_options, is_default )
            
            return ( 9, new_serialisable_info )
            
        
    
    def GetTagFilteringImportOptions( self ) -> TagFilteringImportOptions.TagFilteringImportOptions:
        
        return self._tag_filtering_import_options
        
    
    def GetTagImportOptions( self ) -> TagImportOptions.TagImportOptions:
        
        return self._tag_import_options
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
        if self._is_default:
            
            return 'Using whatever the default tag import options is at at time of import.'
            
        
        statements = []
        
        #
        
        statements.append( self._tag_filtering_import_options.GetSummary( show_downloader_options) )
        
        #
        
        statements.append( self._tag_import_options.GetSummary( show_downloader_options ) )
        
        #
        
        summary = '\n'.join( statements )
        
        return summary
        
    
    def IsDefault( self ):
        
        return self._is_default
        
    
    def SetIsDefault( self, value: bool ):
        
        self._is_default = value
        
    
    def SetShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = value
        
    
    def SetShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self, value: bool ):
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = value
        
    
    def ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_hash_recognised_and_file_already_in_db
        
    
    def ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB( self ):
        
        return self._fetch_tags_even_if_url_recognised_and_file_already_in_db
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS_LEGACY ] = TagImportOptionsLegacy
