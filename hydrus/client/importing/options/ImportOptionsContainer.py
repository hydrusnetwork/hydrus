import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG

IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT = 0
IMPORT_OPTIONS_CALLER_TYPE_POST_URLS = 1
IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION = 2
IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS = 3
IMPORT_OPTIONS_CALLER_TYPE_GLOBAL = 4
IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOAD_PAGES = 6
IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS = 7
IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER = 8
IMPORT_OPTIONS_CALLER_TYPE_WATCHER_PAGES = 9

import_options_caller_type_str_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'local hard drive import',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'post/gallery urls',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'subscription',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'watcher urls',
    IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOAD_PAGES : 'gallery download pages',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'global',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'url class',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'specific importer',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_PAGES : 'watcher pages',
}

IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS,
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_PAGES,
    IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOAD_PAGES,
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION,
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER,
]

IMPORT_OPTIONS_TYPE_PREFETCH = 0
IMPORT_OPTIONS_TYPE_FILE_FILTERING = 1
IMPORT_OPTIONS_TYPE_TAG_FILTERING = 2
IMPORT_OPTIONS_TYPE_LOCATION_IMPORT_OPTIONS = 3
IMPORT_OPTIONS_TYPE_TAG_IMPORT_OPTIONS = 4
IMPORT_OPTIONS_TYPE_NOTE_IMPORT_OPTIONS = 5
IMPORT_OPTIONS_TYPE_PRESENTATION_IMPORT_OPTIONS = 6

import_options_type_str_lookup = {    
    IMPORT_OPTIONS_TYPE_PREFETCH : 'prefetch logic',
    IMPORT_OPTIONS_TYPE_FILE_FILTERING : 'file filtering',
    IMPORT_OPTIONS_TYPE_TAG_FILTERING : 'tag filtering',
    IMPORT_OPTIONS_TYPE_LOCATION_IMPORT_OPTIONS : 'locations',
    IMPORT_OPTIONS_TYPE_TAG_IMPORT_OPTIONS : 'tags',
    IMPORT_OPTIONS_TYPE_NOTE_IMPORT_OPTIONS : 'notes',
    IMPORT_OPTIONS_TYPE_PRESENTATION_IMPORT_OPTIONS : 'presentation',
}

IMPORT_OPTIONS_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_FILE_FILTERING,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_LOCATION_IMPORT_OPTIONS,
    IMPORT_OPTIONS_TYPE_TAG_IMPORT_OPTIONS,
    IMPORT_OPTIONS_TYPE_NOTE_IMPORT_OPTIONS,
    IMPORT_OPTIONS_TYPE_PRESENTATION_IMPORT_OPTIONS,
]

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
        
    
    def _GetImportOptionsCallerTypesPreferenceOrder( self, import_options_caller_type: int, url_class_key: bytes | None = None ):
        """
        The types of caller we should examine, from most to least specific, to layer our swiss cheese model.
        """
        
        preference_stack = [ IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ]
        
        if import_options_caller_type in ( IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION, IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOAD_PAGES ):
            
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_WATCHER_PAGES:
            
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS )
            preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS )
            
        elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
            
            if url_class_key is not None:
                
                try:
                    
                    url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                    
                    if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                        
                        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS )
                        
                    else:
                        
                        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
                        
                    
                except HydrusExceptions.DataMissing:
                    
                    preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
                    
                
            else:
                
                preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS )
                
            
        
        preference_stack.append( import_options_caller_type )
        preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
        
        preference_stack.reverse()
        
        return preference_stack
        
    
    def _GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( self, import_options_caller_type: int, url_class_key: bytes | None = None, specific_import_options_container: "ImportOptionsContainer | None" = None ) -> "list[ ImportOptionsContainer ]":
        
        preference_stack = self._GetImportOptionsCallerTypesPreferenceOrder( import_options_caller_type, url_class_key = url_class_key )
        
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
            serialisable_names_to_favourite_import_options,
        ) = serialisable_info
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options_caller_types_to_default_import_options_containers )
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_default_import_options_containers )
        self._names_to_favourite_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_names_to_favourite_import_options_containers )
        
    
    def GenerateFullImportOptionsContainer( self, caller_import_options_container_slice: "ImportOptionsContainer", import_options_caller_type: int, url_class_key: bytes | None = None ) -> "ImportOptionsContainer":
        
        with self._lock:
            
            import_options_container_slices_in_preference_order_with_source_labels = self._GetImportOptionsContainerSlicesInPreferenceOrderWithSourceLabels( import_options_caller_type, url_class_key = url_class_key, specific_import_options_container = caller_import_options_container_slice )
            
            import_options_container_result = ImportOptionsContainer()
            
            # we have a bunch of slices, now we fill in all the holes
            for ( import_options_container_slice, source_label ) in import_options_container_slices_in_preference_order_with_source_labels:
                
                import_options_container_result.FillInWithThisSlice( import_options_container_slice, source_label )
                
            
            import_options_container_result.SetAndCheckFull()
            
            # this guy is now ready to answer any import question the caller has
            return import_options_container_result
            
        
    
    def GetFavouriteImportOptionContainers( self ):
        
        with self._lock:
            
            return dict( self._names_to_favourite_import_options_containers )
            
        
    
    def GetImportOptionsCallerTypesToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._import_options_caller_types_to_default_import_options_containers )
            
        
    
    def GetURLClassKeysToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._url_class_keys_to_default_import_options_containers )
            
        
    
    def SetFavouriteImportOptionContainers( self, names_to_favourite_import_options_containers ):
        
        with self._lock:
            
            self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary( names_to_favourite_import_options_containers )
            
        
    
    def SetImportOptionsCallerTypesToDefaultImportOptionsContainers( self, import_options_caller_types_to_default_import_options_containers ):
        
        with self._lock:
            
            self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary( import_options_caller_types_to_default_import_options_containers )
            
        
    
    def SetURLClassKeysToDefaultImportOptionsContainers( self, url_class_keys_to_default_import_options_containers ):
        
        with self._lock:
            
            self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary( url_class_keys_to_default_import_options_containers )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER ] = ImportOptionsManager

class ImportOptionsContainer( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER
    SERIALISABLE_NAME = 'Import Options Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options = HydrusSerialisable.SerialisableDictionary()
        self._should_be_full = False
        
        self._import_option_types_to_source_labels = {}
        
        self._lock = threading.Lock()
        
    
    def _GetImportOptions( self, import_options_type: int ):
        
        result = self._import_options.get( import_options_type, None )
        
        if result is None and self._should_be_full:
            
            raise Exception( f'Hey, an import options container that was supposed to be able to serve any request was just asked for an import options of type {import_options_type_str_lookup[ import_options_type ]}, but it was missing! Please report this to hydev!' )
            
        
        return result
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options = self._import_options.GetSerialisableTuple()
        
        return serialisable_import_options
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_import_options = serialisable_info
        
        self._import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options )
        
    
    def _SetImportOptions( self, import_options_type: int, import_options: HydrusSerialisable.SerialisableBase ):
        
        self._import_options[ import_options_type ] = import_options
        
    
    def FillInWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str ):
        
        with self._lock:
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if self._GetImportOptions( import_options_type ) is None:
                    
                    import_options = import_options_container_slice.GetImportOptions( import_options_type )
                    
                    if import_options is not None:
                        
                        self._SetImportOptions( import_options_type, import_options )
                        
                        self._import_option_types_to_source_labels[ import_options_type ] = source_label
                        
                    
                
            
        
    
    def GetSourceLabel( self, import_options_type: int ) -> str:
        
        if self._should_be_full:
            
            default_label = 'global'
            
        else:
            
            default_label = 'not a default; specifically set; you should not see this'
            
        
        return self._import_option_types_to_source_labels.get( import_options_type, default_label )
        
    
    def GetImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return self._GetImportOptions( import_options_type )
            
        
    
    def HasImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return import_options_type in self._import_options
            
        
    
    def SetImportOptions( self, import_options_type: int, import_options: HydrusSerialisable.SerialisableBase ):
        
        with self._lock:
            
            self._SetImportOptions( import_options_type, import_options )
            
        
    
    def SetAndCheckFull( self ):
        
        with self._lock:
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                result = self._GetImportOptions( import_options_type )
                
                if result is None:
                    
                    raise Exception( f'Hey, an import options container that was supposed to be able to serve any request was missing an import options of type {import_options_type_str_lookup[ import_options_type ]} on construction! Please report this to hydev!' )
                    
                
            
            self._should_be_full = True
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER ] = ImportOptionsContainer
