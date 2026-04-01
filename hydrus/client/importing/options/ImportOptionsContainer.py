import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.importing.options.FileFilteringImportOptions import FileFilteringImportOptions
from hydrus.client.importing.options.LocationImportOptions import LocationImportOptions
from hydrus.client.importing.options.NoteImportOptions import NoteImportOptions
from hydrus.client.importing.options.PrefetchImportOptions import PrefetchImportOptions
from hydrus.client.importing.options.PresentationImportOptions import PresentationImportOptions
from hydrus.client.importing.options.TagFilteringImportOptions import TagFilteringImportOptions
from hydrus.client.importing.options.TagImportOptions import TagImportOptions

IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT = 0
IMPORT_OPTIONS_CALLER_TYPE_POST_URLS = 1
IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION = 2
IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS = 3
IMPORT_OPTIONS_CALLER_TYPE_GLOBAL = 4
IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS = 7
IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER = 8
IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER = 9
IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API = 10
IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES = 11

import_options_caller_type_str_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'local hard drive import',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'gallery/post urls',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'subscription',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'watchable urls',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'global',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'url class',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'specific importer',
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : 'import folder',
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : 'client api',
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : 'favourites template',
}

import_options_caller_type_desc_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'This covers all imports from a local hard drive, via a local import page or an "import folder". This is the place to filter, route, or present files differently to downloads.',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'This covers any gallery search or "post" URL, be that in a gallery downloader, urls downloader, or subscription. A general catch-all for all normal URLs. This is a good place to set up metadata filtering.',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'This covers all subscriptions. A good place to set up quieter presentation options than a normal download page (e.g. to make your subscription popups less spammy).',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'This covers all thread watcher work. A good place to set metadata filtering that differs from your gallery/post URL settings.',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'This is the base that all importers will default to if nothing else is set. This is the place to manage your general preferences.',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'This covers all URLs of a particular class. It overrides most other defaults. This is the place to set up blacklists particular to a certain site. The logic of passing from one URL to another can get tricky depending on the question, so if the site is complicated, spam these settings to all the URLs that might be involved (gallery, post, any file...) so you are covering every step of parsing and processing. Generally, though, the final "Post URL" encountered is the one that matters.',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'These import options are attached to this specific importer alone. If you set something here, it will only apply here, and it will definitely apply, overriding any other default.',
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : 'This covers all import folders, if you want different behaviour to a regular local import. A good place to set up quieter presentation options.',
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : 'This covers all files directly imported via the Client API, i.e. when an external program posts a raw file or a file path to be imported, with no downloader page involved. Only appropriate for file filtering and routing.',
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : 'This is a template you can load and paste wherever you need it.',
}

NON_DOWNLOADER_IMPORT_OPTION_CALLER_TYPES = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER,
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API
}

IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL,
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER,
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION,
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS,
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER,
]

IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER = [ ioct for ioct in IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER if ioct not in ( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS, IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER ) ]

IMPORT_OPTIONS_TYPE_PREFETCH = 0
IMPORT_OPTIONS_TYPE_FILE_FILTERING = 1
IMPORT_OPTIONS_TYPE_TAG_FILTERING = 2
IMPORT_OPTIONS_TYPE_LOCATIONS = 3
IMPORT_OPTIONS_TYPE_TAGS = 4
IMPORT_OPTIONS_TYPE_NOTES = 5
IMPORT_OPTIONS_TYPE_PRESENTATION = 6

import_options_type_str_lookup = {    
    IMPORT_OPTIONS_TYPE_PREFETCH : 'prefetch logic',
    IMPORT_OPTIONS_TYPE_FILE_FILTERING : 'file filtering',
    IMPORT_OPTIONS_TYPE_TAG_FILTERING : 'tag filtering',
    IMPORT_OPTIONS_TYPE_LOCATIONS : 'locations',
    IMPORT_OPTIONS_TYPE_TAGS : 'tags',
    IMPORT_OPTIONS_TYPE_NOTES : 'notes',
    IMPORT_OPTIONS_TYPE_PRESENTATION : 'presentation',
}

import_options_type_desc_lookup = {
    IMPORT_OPTIONS_TYPE_PREFETCH : 'Hydrus tries to save bandwidth. In most cases, it will not redownload a file page (HTML/JSON) or the file itself if it can correctly identify that it already has the file, or, in conjunction with file filtering options, wishes to exclude previously deleted files. Adjusting these settings can and will waste bandwidth and are only appropriate for one-off jobs where some forced recheck is needed.',
    IMPORT_OPTIONS_TYPE_FILE_FILTERING : 'Before a file is imported, it can be checked against these rules. If it fails one of these rules, it will get an "ignored" status.',
    IMPORT_OPTIONS_TYPE_TAG_FILTERING : 'Before a file is imported, its tags can be checked against a tag blacklist and/or whitelist. If a tag hits the blacklist, or no tag hits the whitelist, the import will get an "ignored" status. Only the tags that are parsed as part of the download are used in these tests.',
    IMPORT_OPTIONS_TYPE_LOCATIONS : 'If you have multiple local file services, you can choose to place incoming files in a different location than your default (probably "my files"). You can also send them to multiple locations.',
    IMPORT_OPTIONS_TYPE_TAGS : 'A file may pick up tags through the downloading and parsing process. Here you choose where to send any parsed tags.',
    IMPORT_OPTIONS_TYPE_NOTES : 'A file may pick up notes through the downloading and parsing process. Here you choose what to do with these notes. Default options are usually fine unless you have particular needs.',
    IMPORT_OPTIONS_TYPE_PRESENTATION : 'When files are imported, the associated downloader or subscription will want to show them, whether than is adding thumbnails to a page or publishing items to a popup button. You can shape which files are actually "presented". Selecting "only new" or "only inbox" are often useful to remove clutter.',
}

IMPORT_OPTIONS_TYPES_DOWNLOADER_ONLY = {
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_TAGS,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_NOTES,
}

IMPORT_OPTIONS_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_FILE_FILTERING,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_LOCATIONS,
    IMPORT_OPTIONS_TYPE_TAGS,
    IMPORT_OPTIONS_TYPE_NOTES,
    IMPORT_OPTIONS_TYPE_PRESENTATION,
]

IMPORT_OPTIONS_TYPES_SIMPLE_MODE_LOOKUP = {
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER : [ IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : [ IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES, IMPORT_OPTIONS_TYPE_PRESENTATION ],
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : [ IMPORT_OPTIONS_TYPE_PREFETCH, IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_TAG_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS, IMPORT_OPTIONS_TYPE_TAGS, IMPORT_OPTIONS_TYPE_NOTES ],
    IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API : [ IMPORT_OPTIONS_TYPE_FILE_FILTERING, IMPORT_OPTIONS_TYPE_LOCATIONS ],
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
    IMPORT_OPTIONS_CALLER_TYPE_FAVOURITES : IMPORT_OPTIONS_TYPES_CANONICAL_ORDER,
}

def GetImportOptionsCallerTypesPreferenceOrderFull( import_options_caller_type: int, url_class_key: bytes | None = None ):
    """
    The types of caller we should examine, from most to least specific, to layer our swiss cheese model.
    """
    
    preference_stack = [ IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ]
    
    if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
        
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
        preference_stack.append( import_options_caller_type )
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
        
    elif import_options_caller_type in ( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS, IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS ):
        
        preference_stack.append( import_options_caller_type )
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
        
        we_are_confident_in_what_it_is = False
        it_is_watchable = False
        
        if url_class_key is not None:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                
                if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                    
                    it_is_watchable = True
                    
                
                we_are_confident_in_what_it_is = True
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        if we_are_confident_in_what_it_is:
            
            if it_is_watchable:
                
                preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS )
                preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
                
            else:
                
                preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
                preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        else:
            
            
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER:
        
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT )
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER )
        
    else:
        
        preference_stack.append( import_options_caller_type )
        
    
    if import_options_caller_type != IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API:
        
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
        
    
    preference_stack.reverse()
    
    return preference_stack
    

def GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type: int, url_class_key: bytes | None = None ) -> str:
    """
    Given this type of caller in the options UI, what are we showing to the user to say about what is consulted?
    """
    
    if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
        
        return 'global'
        
    
    preference_stack = [ import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ] ]
    
    if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
        
        preference_stack.append( import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_POST_URLS ] )
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'specific import options for the particular subscription' )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_POST_URLS:
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'maybe "subscription"' )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'specific import options for the particular downloader page or subscription' )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS:
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        preference_stack.append( 'specific import options for the particular watcher page' )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
        
        we_are_confident_in_what_it_is = False
        it_is_watchable = False
        url_class_name = 'any matching URL Class'
        
        if url_class_key is not None:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                
                if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                    
                    it_is_watchable = True
                    
                
                url_class_name = f'urls of class "{url_class.GetName()}"'
                
                we_are_confident_in_what_it_is = True
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        if we_are_confident_in_what_it_is:
            
            if it_is_watchable:
                
                preference_stack.append( import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS ] )
                preference_stack.append( url_class_name )
                preference_stack.append( 'specific import options for the particular watcher page' )
                
            else:
                
                preference_stack.append( import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_POST_URLS ] )
                preference_stack.append( 'maybe "subscription"' )
                preference_stack.append( url_class_name )
                preference_stack.append( 'specific import options for the particular downloader page or subscription' )
                
            
        else:
            
            preference_stack.append( 'a gallery/post or watcher url' )
            preference_stack.append( 'maybe "subscription", if it is a gallery/post url class' )
            preference_stack.append( url_class_name )
            preference_stack.append( 'specific import options for the particular watcher page, downloader page, or subscription' )
            
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT_FOLDER:
        
        preference_stack.append( import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT ] )
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'specific import options for the particular import folder' )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_CLIENT_API:
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT:
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'specific import options for the particular local import page' )
        
    
    preference_stack.reverse()
    
    return '\n'.join( preference_stack )
    

class ImportOptionsManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER
    SERIALISABLE_NAME = 'Import Options Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        
        self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
    
    def _GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( self, import_options_caller_type: int, url_class_key: bytes | None = None, specific_import_options_container: "ImportOptionsContainer | None" = None ) -> "list[ ImportOptionsContainer ]":
        
        preference_stack = GetImportOptionsCallerTypesPreferenceOrderFull( import_options_caller_type, url_class_key = url_class_key )
        
        import_options_container_slices_in_preference_order_with_source_labels = []
        
        for preference_import_options_caller_type in preference_stack:
            
            if preference_import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER:
                
                if specific_import_options_container is not None:
                    
                    import_options_container_slices_in_preference_order_with_source_labels.append( ( specific_import_options_container, import_options_caller_type_str_lookup[ preference_import_options_caller_type ] ) )
                    
                
            elif preference_import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
                
                if url_class_key is not None and url_class_key in self._url_class_keys_to_default_import_options_containers:
                    
                    try:
                        
                        url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                        
                        source_label = f'url class: "{url_class.GetName()}"'
                        
                    except HydrusExceptions.DataMissing:
                        
                        source_label = f'url class: unknown/missing'
                        
                    
                    import_options_container_slices_in_preference_order_with_source_labels.append( ( self._url_class_keys_to_default_import_options_containers[ url_class_key ], source_label ) )
                    
                
            else:
                
                import_options_container_slices_in_preference_order_with_source_labels.append(
                    (
                        self._import_options_caller_types_to_default_import_options_containers[ preference_import_options_caller_type ],
                        import_options_caller_type_str_lookup[ preference_import_options_caller_type ]
                    )
                )
                
            
        
        return import_options_container_slices_in_preference_order_with_source_labels
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options_caller_types_to_default_import_options_containers = self._import_options_caller_types_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_import_options_containers = self._url_class_keys_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_names_to_favourite_import_options_containers = self._names_to_favourite_import_options_containers.GetSerialisableTuple()
        
        return (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_names_to_favourite_import_options_containers
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_names_to_favourite_import_options_containers,
        ) = serialisable_info
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options_caller_types_to_default_import_options_containers )
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_default_import_options_containers )
        self._names_to_favourite_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_names_to_favourite_import_options_containers )
        
    
    def _AddFavourite( self, name: str, import_options_container: "ImportOptionsContainer" ):
        
        name = HydrusData.GetNonDupeName( name, set( self._names_to_favourite_import_options_containers.keys() ) )
        
        self._names_to_favourite_import_options_containers[ name ] = import_options_container
        
    
    def _DeleteFavourite( self, name: str ):
        
        if name in self._names_to_favourite_import_options_containers:
            
            del self._names_to_favourite_import_options_containers[ name ]
            
        
    
    def AddFavourite( self, name: str, import_options_container: "ImportOptionsContainer" ):
        
        with self._lock:
            
            self._AddFavourite( name, import_options_container )
            
        
    
    def DeleteFavourite( self, name: str ):
        
        with self._lock:
            
            self._DeleteFavourite( name )
            
        
    
    def EditFavourite( self, original_name: str, name: str, import_options_container: "ImportOptionsContainer" ):
        
        with self._lock:
            
            self._DeleteFavourite( original_name )
            
            self._AddFavourite( name, import_options_container )
            
        
    
    def GenerateFullImportOptionsContainer( self, caller_import_options_container_slice: "ImportOptionsContainer", import_options_caller_type: int, url_class_key: bytes | None = None ) -> "ImportOptionsContainer":
        
        with self._lock:
            
            import_options_container_slices_in_preference_order_with_source_labels = self._GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( import_options_caller_type, url_class_key = url_class_key, specific_import_options_container = caller_import_options_container_slice )
            
            import_options_container_result = ImportOptionsContainer()
            
            # we have a bunch of slices, now we fill in all the holes
            for ( import_options_container_slice, source_label ) in import_options_container_slices_in_preference_order_with_source_labels:
                
                import_options_container_result.FillInWithThisSlice( import_options_container_slice, source_label = source_label )
                
            
            import_options_container_result.SetAndCheckFull()
            
            # this guy is now ready to answer any import question the caller has
            return import_options_container_result
            
        
    
    def GetDefaultImportOptionsContainerForCallerType( self, import_options_caller_type: int ) -> "ImportOptionsContainer":
        
        with self._lock:
            
            return self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ]
            
        
    
    def GetDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes ) -> "ImportOptionsContainer | None":
        
        with self._lock:
            
            return self._url_class_keys_to_default_import_options_containers.get( url_class_key, None )
            
        
    
    def GetFavouriteImportOptionContainers( self ) -> "dict[ str, ImportOptionsContainer ]":
        
        with self._lock:
            
            return dict( self._names_to_favourite_import_options_containers )
            
        
    
    def GetImportOptionsCallerTypesToDefaultImportOptionsContainers( self ) -> "dict[ int, ImportOptionsContainer ]":
        
        with self._lock:
            
            return dict( self._import_options_caller_types_to_default_import_options_containers )
            
        
    
    def GetURLClassKeysToDefaultImportOptionsContainers( self ) -> "dict[ bytes, ImportOptionsContainer ]":
        
        with self._lock:
            
            return dict( self._url_class_keys_to_default_import_options_containers )
            
        
    
    def SetFavouriteImportOptionContainers( self, names_to_favourite_import_options_containers: "dict[ str, ImportOptionsContainer ]" ):
        
        with self._lock:
            
            self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary( names_to_favourite_import_options_containers )
            
        
    
    def SetDefaultImportOptionsContainerForCallerType( self, import_options_caller_type: int, import_options_container: "ImportOptionsContainer" ):
        
        if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
            
            import_options_container.SetAndCheckFull()
            
        
        with self._lock:
            
            self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ] = import_options_container
            
        
    
    def SetDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes, import_options_container: "ImportOptionsContainer" ):
        
        with self._lock:
            
            if import_options_container.IsEmpty():
                
                if url_class_key in self._url_class_keys_to_default_import_options_containers:
                    
                    del self._url_class_keys_to_default_import_options_containers[ url_class_key ]
                    
                
            else:
                
                self._url_class_keys_to_default_import_options_containers[ url_class_key ] = import_options_container
                
            
        
    
    @staticmethod
    def GetDefaultInitialisedManager() -> "ImportOptionsManager":
            
            import_options_manager = ImportOptionsManager.STATICGetEmptyButValidManager()
            
            ImportOptionsManager.STATICPopulateManagerWithDefaultFavourites( import_options_manager )
            
            # loud settings for global
            # quiet filters for the three others
            # post/watchable tag parsing
            
            return import_options_manager
            
        
    
    @staticmethod
    def STATICGetEmptyButValidManager() -> "ImportOptionsManager":
            
            manager = ImportOptionsManager()
            
            for import_options_caller_type in IMPORT_OPTIONS_CALLER_TYPES_EDITABLE_CANONICAL_ORDER:
                
                import_options_container = ImportOptionsContainer()
                
                if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
                    
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_FILE_FILTERING, FileFilteringImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_LOCATIONS, LocationImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_NOTES, NoteImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_PREFETCH, PrefetchImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_PRESENTATION, PresentationImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_TAG_FILTERING, TagFilteringImportOptions() )
                    import_options_container.SetImportOptions( IMPORT_OPTIONS_TYPE_TAGS, TagImportOptions() )
                    
                
                manager.SetDefaultImportOptionsContainerForCallerType( import_options_caller_type, import_options_container )
                
            
            return manager
            
        
    
    @staticmethod
    def STATICPopulateManagerWithDefaultFavourites( import_options_manager: "ImportOptionsManager" ):
        
        import_options_manager.AddFavourite(
            'no tags',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 4], [2, [151, 1, []]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'show new files',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 6], [2, [108, 2, [[103, 1, [["616c6c206c6f63616c206d65646961"], []]], 1, 0]]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'show all files',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 6], [2, [108, 2, [[103, 1, [["616c6c206c6f63616c206d65646961"], []]], 0, 0]]]]]]]'
            )
        )
        
        import_options_manager.AddFavourite(
            'example blacklist',
            HydrusSerialisable.CreateFromString(
                '[143, 1, [21, 2, [[[0, 2], [2, [150, 1, [[44, 1, [["goblin", 1], ["orc", 1]]], []]]]]]]]'
            )
        )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER ] = ImportOptionsManager

ImportOptionsMetatype = PrefetchImportOptions | FileFilteringImportOptions | TagFilteringImportOptions | LocationImportOptions | TagImportOptions | NoteImportOptions | PresentationImportOptions

class ImportOptionsContainer( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER
    SERIALISABLE_NAME = 'Import Options Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options_types_to_import_options = HydrusSerialisable.SerialisableDictionary()
        self._should_be_full = False
        
        self._import_option_types_to_source_labels = {}
        
        self._lock = threading.Lock()
        
    
    def _GetImportOptions( self, import_options_type: int ):
        
        result = self._import_options_types_to_import_options.get( import_options_type, None )
        
        if result is None and self._should_be_full:
            
            raise Exception( f'Hey, an import options container that was supposed to be able to serve any request was just asked for an import options of type {import_options_type_str_lookup[ import_options_type ]}, but it was missing! Please report this to hydev!' )
            
        
        return result
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options = self._import_options_types_to_import_options.GetSerialisableTuple()
        
        return serialisable_import_options
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_import_options = serialisable_info
        
        self._import_options_types_to_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options )
        
    
    def _SetImportOptions( self, import_options_type: int, import_options: HydrusSerialisable.SerialisableBase, source_label: str | None = None ):
        
        self._import_options_types_to_import_options[ import_options_type ] = import_options
        
        if source_label is None:
            
            if import_options_type in self._import_option_types_to_source_labels:
                
                del self._import_option_types_to_source_labels[ import_options_type ]
                
            
        else:
            
            self._import_option_types_to_source_labels[ import_options_type ] = source_label
            
        
    
    def DeleteImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            if import_options_type in self._import_options_types_to_import_options:
                
                del self._import_options_types_to_import_options[ import_options_type ]
                
            
            if import_options_type in self._import_option_types_to_source_labels:
                
                del self._import_option_types_to_source_labels[ import_options_type ]
                
            
        
    
    def FillInWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str | None = None ):
        
        with self._lock:
            
            if import_options_container_slice.IsEmpty():
                
                return
                
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if self._GetImportOptions( import_options_type ) is None:
                    
                    import_options = import_options_container_slice.GetImportOptions( import_options_type )
                    
                    if import_options is not None:
                        
                        self._SetImportOptions( import_options_type, import_options, source_label = source_label )
                        
                    
                
            
        
    
    def OverwriteWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str | None = None ):
        
        if import_options_container_slice.IsEmpty():
            
            return
            
        
        for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
            
            import_options = import_options_container_slice.GetImportOptions( import_options_type )
            
            if import_options is not None:
                
                self._SetImportOptions( import_options_type, import_options, source_label = source_label )
                
            
        
    
    def GetSourceLabel( self, import_options_type: int ) -> str:
        
        if self._should_be_full:
            
            default_label = 'global'
            
        else:
            
            default_label = 'not a default; specifically set; you should not see this'
            
        
        return self._import_option_types_to_source_labels.get( import_options_type, default_label )
        
    
    def GetImportOptions( self, import_options_type: int ) -> ImportOptionsMetatype:
        
        with self._lock:
            
            return self._GetImportOptions( import_options_type )
            
        
    
    def GetSummary( self, show_downloader_options: bool = True ):
        
        with self._lock:
            
            short_summary_components = []
            long_summary_components = []
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if import_options_type in self._import_options_types_to_import_options:
                    
                    short_summary_components.append( import_options_type_str_lookup[ import_options_type ] )
                    long_summary_components.append( self._import_options_types_to_import_options[ import_options_type ].GetSummary( show_downloader_options ) )
                    
                
            
        
        long_summary_components = [ item for item in long_summary_components if item != '' ]
        
        if len( short_summary_components ) == 0:
            
            return ''
            
        else:
            
            if len( short_summary_components ) <= 2 and 1 <= len( long_summary_components ) <= 2:
                
                return ', '.join( short_summary_components ) + ': ' + ' | '.join( long_summary_components )
                
            else:
                
                return ', '.join( short_summary_components )
                
            
        
    
    def HasImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return import_options_type in self._import_options_types_to_import_options
            
        
    
    def IsEmpty( self ):
        
        with self._lock:
            
            return len( self._import_options_types_to_import_options ) == 0
            
        
    
    def SetImportOptions( self, import_options_type: int, import_options: ImportOptionsMetatype, source_label: str | None = None ):
        
        with self._lock:
            
            self._SetImportOptions( import_options_type, import_options, source_label = source_label )
            
        
    
    def SetAndCheckFull( self ):
        
        with self._lock:
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                result = self._GetImportOptions( import_options_type )
                
                if result is None:
                    
                    raise Exception( f'Hey, an import options container that was supposed to be able to serve any request was missing an import options of type {import_options_type_str_lookup[ import_options_type ]} on construction! Please report this to hydev!' )
                    
                
            
            self._should_be_full = True
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER ] = ImportOptionsContainer
