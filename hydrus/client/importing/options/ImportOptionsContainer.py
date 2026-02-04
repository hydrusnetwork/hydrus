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
        
        self._favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary() # names to containers
        self._favourite_import_options = HydrusSerialisable.SerialisableDictionary( { import_options_type : HydrusSerialisable.SerialisableDictionary() for import_options_type in IMPORT_OPTIONS_CANONICAL_ORDER } )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options_caller_types_to_default_import_options_containers = self._import_options_caller_types_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_url_class_keys_to_default_import_options_containers = self._url_class_keys_to_default_import_options_containers.GetSerialisableTuple()
        serialisable_favourite_import_options_containers = self._favourite_import_options_containers.GetSerialisableTuple()
        serialisable_favourite_import_options = self._favourite_import_options.GetSerialisableTuple()
        
        return (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_favourite_import_options_containers,
            serialisable_favourite_import_options,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_import_options_caller_types_to_default_import_options_containers,
            serialisable_url_class_keys_to_default_import_options_containers,
            serialisable_favourite_import_options_containers,
            serialisable_favourite_import_options,
        ) = serialisable_info
        
        self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options_caller_types_to_default_import_options_containers )
        self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_class_keys_to_default_import_options_containers )
        self._favourite_import_options_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_favourite_import_options_containers )
        self._favourite_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_favourite_import_options )
        
    
    def GetDerivedImportOptionsFromContainer( self, import_options_container: "ImportOptionsContainer", import_options_type: int, import_options_caller_type: int, url_class_key = None ):
        
        # TODO: Yeah rewrite this guy to a 'convert my swiss cheese slice and import options caller type to a solid base and I'll never talk to you again this file import'
        
        with self._lock:
            
            possible_import_options = import_options_container.GetImportOptions( import_options_type )
            
            if possible_import_options is not None:
                
                return possible_import_options
                
            
            # the importer's primary container doesn't have an entry for this type, so we are looking at the defaults. let's check urls if that's what we are
            
            if url_class_key is not None and url_class_key in self._url_class_keys_to_default_import_options_containers:
                
                possible_import_options = self._url_class_keys_to_default_import_options_containers[ url_class_key ].GetImportOptions( import_options_type )
                
                if possible_import_options is not None:
                    
                    return possible_import_options
                    
                
            
            # ok, let's set up the order we want to consult things
            
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
                
                possible_import_options = self._import_options_caller_types_to_default_import_options_containers[ import_options_caller_type ].GetImportOptions( import_options_type )
                
                if possible_import_options is not None:
                    
                    return possible_import_options
                    
                
            
            raise Exception( f'Your global default import options have a hole! This should never happen. The problem originated from {import_options_caller_type_str_lookup[ import_options_caller_type ]}/{import_options_type_str_lookup[ import_options_type ]}! Please tell hydev, and try opening and re-saving your default import options to see if it re-fills-in the default.' )
            
        
    
    def GetFavouriteImportOptionContainers( self ):
        
        with self._lock:
            
            return dict( self._favourite_import_options_containers )
            
        
    
    def GetFavouriteImportOptions( self, import_options_type ):
        
        with self._lock:
            
            return dict( self._favourite_import_options[ import_options_type ] )
            
        
    
    def GetImportOptionsCallerTypesToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._import_options_caller_types_to_default_import_options_containers )
            
        
    
    def GetURLClassKeysToDefaultImportOptionsContainers( self ):
        
        with self._lock:
            
            return dict( self._url_class_keys_to_default_import_options_containers )
            
        
    
    def SetFavouriteImportOptionContainers( self, favourite_import_options_containers ):
        
        with self._lock:
            
            self._favourite_import_options_containers = HydrusSerialisable.SerialisableDictionary( favourite_import_options_containers )
            
        
    
    def SetFavouriteImportOptions( self, import_options_type, favourite_import_options ):
        
        with self._lock:
            
            self._favourite_import_options[ import_options_type ] = HydrusSerialisable.SerialisableDictionary( favourite_import_options )
            
        
    
    def SetImportOptionsCallerTypesToDefaultImportOptionsContainers( self, import_options_caller_types_to_default_import_options_containers ):
        
        with self._lock:
            
            self._import_options_caller_types_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary( import_options_caller_types_to_default_import_options_containers )
            
        
    
    def SetURLClassKeysToDefaultImportOptionsContainers( self, url_class_keys_to_default_import_options_containers ):
        
        with self._lock:
            
            self._url_class_keys_to_default_import_options_containers = HydrusSerialisable.SerialisableDictionary( url_class_keys_to_default_import_options_containers )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_MANAGER ] = ImportOptionsManager

# TODO: Ok splitting this guy into Swiss Cheese vs Solid. come up with better names.
# he is so simple though, I could just have a bool that changes his None-return to an exception etc.., and alter any edit panel based on that bool
# I do need names for this transition though
# ditch the 'getderivedimportoptionsfromcontainer' stuff in the manager above. collapse a swiss cheese template and importer context to a frozen solid base early in the pipeline, and pass that around thereafter for that file import

class ImportOptionsContainer( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER
    SERIALISABLE_NAME = 'Import Options Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._import_options = HydrusSerialisable.SerialisableDictionary()
        
        self._lock = threading.Lock()
        
    
    def _GetImportOptions( self, import_options_type: int ):
        
        return self._import_options.get( import_options_type, None )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_options = self._import_options.GetSerialisableTuple()
        
        return serialisable_import_options
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_import_options = serialisable_info
        
        self._import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_options )
        
    
    def GetImportOptions( self, import_options_type: int ):
        
        with self._lock:
            
            return self._GetImportOptions( import_options_type )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_OPTIONS_CONTAINER ] = ImportOptionsContainer
