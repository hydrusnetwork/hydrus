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
IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS = 7
IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER = 8

import_options_caller_type_str_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'local hard drive import',
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS : 'gallery downloads',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'subscription',
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS : 'watchers',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'global',
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS : 'url class',
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER : 'specific importer',
}

# TODO: a longer description here yeah

IMPORT_OPTIONS_CALLER_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL,
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT,
    IMPORT_OPTIONS_CALLER_TYPE_POST_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS,
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION,
    IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS,
    IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER,
]

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

IMPORT_OPTIONS_TYPES_CANONICAL_ORDER = [
    IMPORT_OPTIONS_TYPE_PREFETCH,
    IMPORT_OPTIONS_TYPE_FILE_FILTERING,
    IMPORT_OPTIONS_TYPE_TAG_FILTERING,
    IMPORT_OPTIONS_TYPE_LOCATIONS,
    IMPORT_OPTIONS_TYPE_TAGS,
    IMPORT_OPTIONS_TYPE_NOTES,
    IMPORT_OPTIONS_TYPE_PRESENTATION,
]

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
        
    else:
        
        preference_stack.append( import_options_caller_type )
        
    
    preference_stack.append( IMPORT_OPTIONS_CALLER_TYPE_SPECIFIC_IMPORTER )
    
    preference_stack.reverse()
    
    return preference_stack
    

def GetImportOptionsCallerTypesPreferenceOrderDescription( import_options_caller_type: int, url_class_key: bytes | None = None ) -> str:
    """
    Given this type of caller in the options UI, what are we showing to the user to say about what is consulted?
    """
    
    if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_GLOBAL:
        
        return 'the global type is the base. everything else defaults to this'
        
    
    preference_stack = [ import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_GLOBAL ] ]
    
    if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
        
        preference_stack.append( import_options_caller_type_str_lookup[ IMPORT_OPTIONS_CALLER_TYPE_POST_URLS ] )
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        
    elif import_options_caller_type in ( IMPORT_OPTIONS_CALLER_TYPE_POST_URLS, IMPORT_OPTIONS_CALLER_TYPE_WATCHER_URLS ):
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        preference_stack.append( 'any matching URL Class' )
        
    elif import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_URL_CLASS:
        
        it_is_watchable = False
        
        if url_class_key is not None:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromKey( url_class_key )
                
                if url_class.GetURLType() == HC.URL_TYPE_WATCHABLE:
                    
                    it_is_watchable = True
                    
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        preference_stack.append( 'a gallery downloader or a watcher' )
        preference_stack.append( 'maybe a subscription, if it is a gallery downloader' )
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        
    else:
        
        preference_stack.append( import_options_caller_type_str_lookup[ import_options_caller_type ] )
        
    
    preference_stack.append( 'specific import options for the particular importer' )
    
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
            
        
    
    def GetDefaultImportOptionsContainerForCallerType( self, import_options_caller_type: int ) -> "ImportOptionsContainer":
        
        with self._lock:
            
            return self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ]
            
        
    
    def GetDefaultImportOptionsContainerForURLClass( self, url_class_key: bytes ) -> "ImportOptionsContainer | None":
        
        with self._lock:
            
            return self._url_class_keys_to_default_import_options_containers.get( url_class_key, None )
            
        
    
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
                
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER ] = ImportOptionsManager

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
        
    
    def _SetImportOptions( self, import_options_type: int, import_options: HydrusSerialisable.SerialisableBase ):
        
        self._import_options_types_to_import_options[ import_options_type ] = import_options
        
    
    def FillInWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer", source_label: str ):
        
        with self._lock:
            
            if import_options_container_slice.IsEmpty():
                
                return
                
            
            for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
                
                if self._GetImportOptions( import_options_type ) is None:
                    
                    import_options = import_options_container_slice.GetImportOptions( import_options_type )
                    
                    if import_options is not None:
                        
                        self._SetImportOptions( import_options_type, import_options )
                        
                        self._import_option_types_to_source_labels[ import_options_type ] = source_label
                        
                    
                
            
        
    
    def OverwriteWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer" ):
        
        if import_options_container_slice.IsEmpty():
            
            return
            
        
        for import_options_type in IMPORT_OPTIONS_TYPES_CANONICAL_ORDER:
            
            import_options = import_options_container_slice.GetImportOptions( import_options_type )
            
            if import_options is not None:
                
                self._SetImportOptions( import_options_type, import_options )
                
                if import_options_type in self._import_option_types_to_source_labels:
                    
                    del self._import_option_types_to_source_labels[ import_options_type ]
                    
                
            
        
    
    def GetSourceLabel( self, import_options_type: int ) -> str:
        
        if self._should_be_full:
            
            default_label = 'global'
            
        else:
            
            default_label = 'not a default; specifically set; you should not see this'
            
        
        return self._import_option_types_to_source_labels.get( import_options_type, default_label )
        
    
    def GetImportOptions( self, import_options_type: int ):
        
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
                    
                
            
        
        if len( short_summary_components ) == 0:
            
            return 'empty'
            
        else:
            
            return ', '.join( short_summary_components ) + ' | ' + ', '.join( long_summary_components )
            
        
    
    def HasImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return import_options_type in self._import_options_types_to_import_options
            
        
    
    def IsEmpty( self ):
        
        with self._lock:
            
            return len( self._import_options_types_to_import_options ) == 0
            
        
    
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
