import threading

from hydrus.core import HydrusSerialisable

IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT = 0
IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOADER = 1
IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION = 2
IMPORT_OPTIONS_CALLER_TYPE_THREAD_WATCHER = 3
IMPORT_OPTIONS_CALLER_TYPE_GLOBAL = 4

import_options_caller_type_str_lookup = {
    IMPORT_OPTIONS_CALLER_TYPE_LOCAL_IMPORT : 'local hard drive import',
    IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOADER : 'gallery downloader',
    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION : 'subscription',
    IMPORT_OPTIONS_CALLER_TYPE_THREAD_WATCHER : 'watcher',
    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL : 'global',
}

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

IMPORT_OPTIONS_CANONICAL_ORDER = [
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
        self._import_options_types_to_names_to_favourite_import_options = HydrusSerialisable.SerialisableDictionary( { import_options_type : HydrusSerialisable.SerialisableDictionary() for import_options_type in IMPORT_OPTIONS_CANONICAL_ORDER } )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options_caller_types_to_default_import_options_containers = self._import_options_caller_types_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_import_options_containers = self._url_class_keys_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_names_to_favourite_import_options_containers = self._names_to_favourite_import_options_containers.GetSerialisableTuple()
        serialisable_names_to_favourite_import_options = self._import_options_types_to_names_to_favourite_import_options.GetSerialisableTuple()
        
        return (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_names_to_favourite_import_options_containers,
            serialisable_names_to_favourite_import_options,
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
        self._import_options_types_to_names_to_favourite_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_names_to_favourite_import_options )
        
    
    def GenerateFullImportOptionsContainer( self, caller_import_options_container_slice: "ImportOptionsContainer", import_options_caller_type: int, url_class_key = None ) -> "ImportOptionsContainer":
        
        import_options_container_slices_in_preference_order = [ caller_import_options_container_slice ]
        
        with self._lock:
            
            if url_class_key is not None and url_class_key in self._url_class_keys_to_default_import_options_containers:
                
                import_options_container_slices_in_preference_order.append( self._url_class_keys_to_default_import_options_containers[ url_class_key ] )
                
            
            if import_options_caller_type == IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION:
                
                preference_stack = [
                    IMPORT_OPTIONS_CALLER_TYPE_SUBSCRIPTION,
                    IMPORT_OPTIONS_CALLER_TYPE_GALLERY_DOWNLOADER,
                    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL
                ]
                
            else:
                
                preference_stack = [
                    import_options_caller_type,
                    IMPORT_OPTIONS_CALLER_TYPE_GLOBAL
                ]
                
            
            for import_options_caller_type in preference_stack:
                
                import_options_container_slices_in_preference_order.append( self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ] )
                
            
            import_options_container_result = ImportOptionsContainer()
            
            # we have a bunch of slices, now we fill in all the holes
            for import_options_container_slice in import_options_container_slices_in_preference_order:
                
                import_options_container_result.FillInWithThisSlice( import_options_container_slice )
                
            
            import_options_container_result.SetAndCheckFull()
            
            # this guy is now ready to answer any import question the caller has
            return import_options_container_result
            
        
    
    def GetFavouriteImportOptionContainers( self ):
        
        with self._lock:
            
            return dict( self._names_to_favourite_import_options_containers )
            
        
    
    def GetFavouriteImportOptions( self, import_options_type ):
        
        with self._lock:
            
            return dict( self._import_options_types_to_names_to_favourite_import_options[ import_options_type ] )
            
        
    
    def GetImportOptionsCallerTypesToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._import_options_caller_types_to_default_import_options_containers )
            
        
    
    def GetURLClassKeysToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._url_class_keys_to_default_import_options_containers )
            
        
    
    def SetFavouriteImportOptionContainers( self, names_to_favourite_import_options_containers ):
        
        with self._lock:
            
            self._names_to_favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary( names_to_favourite_import_options_containers )
            
        
    
    def SetFavouriteImportOptions( self, import_options_type, names_to_favourite_import_options ):
        
        with self._lock:
            
            self._import_options_types_to_names_to_favourite_import_options[ import_options_type ] = HydrusSerialisable.SerialisableDictionary( names_to_favourite_import_options )
            
        
    
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
        
    
    def FillInWithThisSlice( self, import_options_container_slice: "ImportOptionsContainer" ):
        
        with self._lock:
            
            for import_options_type in IMPORT_OPTIONS_CANONICAL_ORDER:
                
                if self._GetImportOptions( import_options_type ) is None:
                    
                    import_options = import_options_container_slice.GetImportOptions( import_options_type )
                    
                    if import_options is not None:
                        
                        self._SetImportOptions( import_options_type, import_options )
                        
                    
                
            
        
    
    def GetImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return self._GetImportOptions( import_options_type )
            
        
    
    def SetImportOptions( self, import_options_type: int, import_options: HydrusSerialisable.SerialisableBase ):
        
        with self._lock:
            
            self._SetImportOptions( import_options_type, import_options )
            
        
    
    def SetAndCheckFull( self ):
        
        with self._lock:
            
            for import_options_type in IMPORT_OPTIONS_CANONICAL_ORDER:
                
                result = self._GetImportOptions( import_options_type )
                
                if result is None:
                    
                    raise Exception( f'Hey, an import options container that was supposed to be able to serve any request was missing an import options of type {import_options_type_str_lookup[ import_options_type ]} on construction! Please report this to hydev!' )
                    
                
            
            self._should_be_full = True
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER ] = ImportOptionsContainer
