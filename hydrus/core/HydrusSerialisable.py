import hashlib
import json
import typing

from hydrus.core import HydrusCompression
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

META_SERIALISABLE_TYPE_JSON_OK = 0
META_SERIALISABLE_TYPE_JSON_BYTES = 1
META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE = 2

SERIALISABLE_TYPE_BASE = 0
SERIALISABLE_TYPE_BASE_NAMED = 1
SERIALISABLE_TYPE_SHORTCUT_SET = 2
SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY = 3
SERIALISABLE_TYPE_PERIODIC = 4
SERIALISABLE_TYPE_GALLERY_IDENTIFIER = 5
SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS = 6
SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS = 7
SERIALISABLE_TYPE_FILE_SEED_CACHE = 8
SERIALISABLE_TYPE_HDD_IMPORT = 9
SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE = 10
SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE = 11
SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER = 12
SERIALISABLE_TYPE_GUI_SESSION_LEGACY = 13
SERIALISABLE_TYPE_PREDICATE = 14
SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT = 15
SERIALISABLE_TYPE_EXPORT_FOLDER = 16
SERIALISABLE_TYPE_WATCHER_IMPORT = 17
SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT = 18
SERIALISABLE_TYPE_IMPORT_FOLDER = 19
SERIALISABLE_TYPE_MULTIPLE_GALLERY_IMPORT = 20
SERIALISABLE_TYPE_DICTIONARY = 21
SERIALISABLE_TYPE_CLIENT_OPTIONS = 22
SERIALISABLE_TYPE_CONTENT = 23
SERIALISABLE_TYPE_PETITION = 24
SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER = 25
SERIALISABLE_TYPE_LIST = 26
SERIALISABLE_TYPE_PARSE_FORMULA_HTML = 27
SERIALISABLE_TYPE_URLS_IMPORT = 28
SERIALISABLE_TYPE_PARSE_NODE_CONTENT_LINK = 29
SERIALISABLE_TYPE_CONTENT_PARSER = 30
SERIALISABLE_TYPE_PARSE_FORMULA_JSON = 31
SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP = 32
SERIALISABLE_TYPE_BYTES_DICT = 33
SERIALISABLE_TYPE_CONTENT_UPDATE = 34
SERIALISABLE_TYPE_CREDENTIALS = 35
SERIALISABLE_TYPE_DEFINITIONS_UPDATE = 36
SERIALISABLE_TYPE_METADATA = 37
SERIALISABLE_TYPE_BANDWIDTH_RULES = 38
SERIALISABLE_TYPE_BANDWIDTH_TRACKER = 39
SERIALISABLE_TYPE_CLIENT_TO_SERVER_UPDATE = 40
SERIALISABLE_TYPE_SHORTCUT = 41
SERIALISABLE_TYPE_APPLICATION_COMMAND = 42
SERIALISABLE_TYPE_DUPLICATE_CONTENT_MERGE_OPTIONS = 43
SERIALISABLE_TYPE_TAG_FILTER = 44
SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_LEGACY = 45
SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_LEGACY = 46
SERIALISABLE_TYPE_NETWORK_CONTEXT = 47
SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER = 48
SERIALISABLE_TYPE_MEDIA_SORT = 49
SERIALISABLE_TYPE_URL_CLASS = 50
SERIALISABLE_TYPE_STRING_MATCH = 51
SERIALISABLE_TYPE_CHECKER_OPTIONS = 52
SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER = 53
SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LEGACY = 54
SERIALISABLE_TYPE_STRING_CONVERTER = 55
SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS = 56
SERIALISABLE_TYPE_FILE_SEED = 57
SERIALISABLE_TYPE_PAGE_PARSER = 58
SERIALISABLE_TYPE_PARSE_FORMULA_ZIPPER = 59
SERIALISABLE_TYPE_PARSE_FORMULA_CONTEXT_VARIABLE = 60
SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR = 61
SERIALISABLE_TYPE_PARSE_RULE_HTML = 62
SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_PARSE_FORMULA = 63
SERIALISABLE_TYPE_MULTIPLE_WATCHER_IMPORT = 64
SERIALISABLE_TYPE_SERVICE_TAG_IMPORT_OPTIONS = 65
SERIALISABLE_TYPE_GALLERY_SEED = 66
SERIALISABLE_TYPE_GALLERY_SEED_LOG = 67
SERIALISABLE_TYPE_GALLERY_IMPORT = 68
SERIALISABLE_TYPE_GALLERY_URL_GENERATOR = 69
SERIALISABLE_TYPE_NESTED_GALLERY_URL_GENERATOR = 70
SERIALISABLE_TYPE_DOMAIN_METADATA_PACKAGE = 71
SERIALISABLE_TYPE_LOGIN_CREDENTIAL_DEFINITION = 72
SERIALISABLE_TYPE_LOGIN_SCRIPT_DOMAIN = 73
SERIALISABLE_TYPE_LOGIN_STEP = 74
SERIALISABLE_TYPE_CLIENT_API_MANAGER = 75
SERIALISABLE_TYPE_CLIENT_API_PERMISSIONS = 76
SERIALISABLE_TYPE_SERVICE_KEYS_TO_TAGS = 77
SERIALISABLE_TYPE_MEDIA_COLLECT = 78
SERIALISABLE_TYPE_TAG_DISPLAY_MANAGER = 79
SERIALISABLE_TYPE_tag_context = 80
SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER = 81
SERIALISABLE_TYPE_NOTE_IMPORT_OPTIONS = 82
SERIALISABLE_TYPE_STRING_SPLITTER = 83
SERIALISABLE_TYPE_STRING_PROCESSOR = 84
SERIALISABLE_TYPE_TAG_AUTOCOMPLETE_OPTIONS = 85
SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER = 86
SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_HEADER = 87
SERIALISABLE_TYPE_SUBSCRIPTION = 88
SERIALISABLE_TYPE_FILE_SEED_CACHE_STATUS = 89
SERIALISABLE_TYPE_SUBSCRIPTION_CONTAINER = 90
SERIALISABLE_TYPE_COLUMN_LIST_STATUS = 91
SERIALISABLE_TYPE_COLUMN_LIST_MANAGER = 92
SERIALISABLE_TYPE_NUMBER_TEST = 93
SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER = 94
SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER = 95
SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER = 96
SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER = 97
SERIALISABLE_TYPE_SIDECAR_EXPORTER = 98
SERIALISABLE_TYPE_STRING_SORTER = 99
SERIALISABLE_TYPE_STRING_SLICER = 100
SERIALISABLE_TYPE_TAG_SORT = 101
SERIALISABLE_TYPE_ACCOUNT_TYPE = 102
SERIALISABLE_TYPE_LOCATION_CONTEXT = 103
SERIALISABLE_TYPE_GUI_SESSION_CONTAINER = 104
SERIALISABLE_TYPE_GUI_SESSION_PAGE_DATA = 105
SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_NOTEBOOK = 106
SERIALISABLE_TYPE_GUI_SESSION_CONTAINER_PAGE_SINGLE = 107
SERIALISABLE_TYPE_PRESENTATION_IMPORT_OPTIONS = 108
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_ROUTER = 109
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_TXT = 110
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TAGS = 111
SERIALISABLE_TYPE_STRING_TAG_FILTER = 112
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_JSON = 113
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_JSON = 114
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TAGS = 115
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_TXT = 116
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_URLS = 117
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_URLS = 118
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_NOTES = 119
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_NOTES = 120
SERIALISABLE_TYPE_TIMESTAMP_DATA = 121
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_EXPORTER_MEDIA_TIMESTAMPS = 122
SERIALISABLE_TYPE_METADATA_SINGLE_FILE_IMPORTER_MEDIA_TIMESTAMPS = 123
SERIALISABLE_TYPE_PETITION_HEADER = 124
SERIALISABLE_TYPE_STRING_JOINER = 125
SERIALISABLE_TYPE_FILE_FILTER = 126
SERIALISABLE_TYPE_URL_CLASS_PARAMETER_FIXED_NAME = 127
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE = 128
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR = 129
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_ONE_FILE = 130
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_FILE_INFO = 131
SERIALISABLE_TYPE_METADATA_CONDITIONAL = 132
SERIALISABLE_TYPE_PARSE_FORMULA_NESTED = 133
SERIALISABLE_TYPE_POTENTIAL_DUPLICATES_SEARCH_CONTEXT = 134
SERIALISABLE_TYPE_SUBSIDIARY_PAGE_PARSER = 135
SERIALISABLE_TYPE_PARSE_FORMULA_STATIC = 136
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_HARDCODED = 137
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_VISUAL_DUPLICATES = 138
SERIALISABLE_TYPE_URL_DOMAIN_MASK = 139
SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_OR = 140

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

def CreateFromNetworkBytes( network_bytes: bytes, raise_error_on_future_version = False ) -> typing.Any:
    
    obj_string = HydrusCompression.DecompressBytesToString( network_bytes )
    
    return CreateFromString( obj_string, raise_error_on_future_version = raise_error_on_future_version )
    

def CreateFromNoneableSerialisableTuple( obj_tuple_or_none, raise_error_on_future_version = False ) -> typing.Any:
    
    if obj_tuple_or_none is None:
        
        return None
        
    else:
        
        return CreateFromSerialisableTuple( obj_tuple_or_none, raise_error_on_future_version = raise_error_on_future_version )
        
    

def CreateFromString( obj_string: str, raise_error_on_future_version = False ) -> typing.Any:
    
    obj_tuple = json.loads( obj_string )
    
    return CreateFromSerialisableTuple( obj_tuple, raise_error_on_future_version = raise_error_on_future_version )
    

def CreateFromSerialisableTuple( obj_tuple: tuple, raise_error_on_future_version = False ) -> typing.Any:
    
    if len( obj_tuple ) == 3:
        
        ( serialisable_type, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]()
        
    else:
        
        ( serialisable_type, name, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]( name )
        
    
    obj.InitialiseFromSerialisableInfo( version, serialisable_info, raise_error_on_future_version = raise_error_on_future_version )
    
    return obj
    

def GetNoneableSerialisableTuple( obj_or_none ):
    
    if obj_or_none is None:
        
        return None
        
    else:
        
        return obj_or_none.GetSerialisableTuple()
        
    

def SetNonDupeName( obj, disallowed_names, do_casefold = False ):
    
    non_dupe_name = HydrusData.GetNonDupeName( obj.GetName(), disallowed_names, do_casefold = do_casefold )
    
    obj.SetName( non_dupe_name )
    

def ObjectVersionIsFromTheFuture( obj_tuple ):
    
    if len( obj_tuple ) == 3:
        
        ( serialisable_type, version, serialisable_info ) = obj_tuple
        
    else:
        
        ( serialisable_type, name, version, serialisable_info ) = obj_tuple
        
    
    return SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ].SERIALISABLE_VERSION > version
    

SerialisableBaseSubclass = typing.TypeVar( 'SerialisableBaseSubclass', bound = 'SerialisableBase' )

class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    SERIALISABLE_NAME = 'Base Serialisable Object'
    SERIALISABLE_VERSION = 1
    
    # don't make an __eq__ here without more testing and research, it messes a bunch of things up in sets and hashing and stuff
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        return old_serialisable_info
        
    
    def DumpToNetworkBytes( self ):
        
        obj_string = self.DumpToString()
        
        return HydrusCompression.CompressStringToBytes( obj_string )
        
    
    def DumpToString( self ):
        
        obj_tuple = self.GetSerialisableTuple()
        
        return json.dumps( obj_tuple )
        
    
    # this magically tells type checkers that this delivers whatever 'self' type is, subclasses whatever
    def Duplicate( self: SerialisableBaseSubclass ) -> SerialisableBaseSubclass:
        
        return CreateFromString( self.DumpToString() )
        
    
    def GetSerialisedHash( self ):
        
        # as a note, this should not be relied on in future--the serialised string could change due to object updates, or in rare cases, because the contained objects are still hot
        return hashlib.sha256( bytes( self.DumpToString(), 'utf-8' ) ).digest()
        
    
    def GetSerialisableTuple( self ):
        
        if hasattr( self, '_lock' ):
            
            with getattr( self, '_lock' ):
                
                serialisable_info = self._GetSerialisableInfo()
                
            
        else:
            
            serialisable_info = self._GetSerialisableInfo()
            
        
        return ( self.SERIALISABLE_TYPE, self.SERIALISABLE_VERSION, serialisable_info )
        
    
    def InitialiseFromSerialisableInfo( self, original_version, serialisable_info, raise_error_on_future_version = False ):
        
        object_is_newer = original_version > self.SERIALISABLE_VERSION
        
        if object_is_newer:
            
            if raise_error_on_future_version:
                
                message = 'Unfortunately, an object of type {} could not be loaded because it was created in a client/server that uses an updated version of that object! We support up to version {}, but the object was version {}.'.format( self.SERIALISABLE_NAME, self.SERIALISABLE_VERSION, original_version )
                message += '\n' * 2
                message += 'Please update your client/server to import this object.'
                
                raise HydrusExceptions.SerialisationException( message )
                
            else:
                
                message = 'An object of type {} was created in a client/server that uses an updated version of that object! We support versions up to {}, but the object was version {}. For now, we will try to continue work, but things may break. If you know why this has occured, please correct it. If you do not, please let hydrus dev know.'.format( self.SERIALISABLE_NAME, self.SERIALISABLE_VERSION, original_version )
                
                HydrusData.ShowText( message )
                
            
        
        try:
            
            current_version = original_version
            
            while current_version < self.SERIALISABLE_VERSION:
                
                ( current_version, serialisable_info ) = self._UpdateSerialisableInfo( current_version, serialisable_info )
                
            
        except:
            
            raise HydrusExceptions.SerialisationException( 'Could not update this object of type {} from version {} to {}!'.format( self.SERIALISABLE_NAME, original_version, self.SERIALISABLE_VERSION ) )
            
        
        try:
            
            self._InitialiseFromSerialisableInfo( serialisable_info )
            
        except:
            
            if object_is_newer:
                
                raise HydrusExceptions.SerialisationException( 'An object of type {} was created in a client/server that uses an updated version of that object! We support versions up to {}, but the object was version {}. I tried to load it, but the initialisation failed. You probably need to update your client/server.'.format( self.SERIALISABLE_NAME, self.SERIALISABLE_VERSION, original_version ) )
                
            else:
                
                raise HydrusExceptions.SerialisationException( 'Could not initialise this object of type {}!'.format( self.SERIALISABLE_NAME ) )
                
            
        
    

def ConvertObjectToMetaSerialisableTuple( obj ):
    
    if isinstance( obj, SerialisableBase ):
        
        metatype = META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE
        serialisable = obj.GetSerialisableTuple()
        
    elif isinstance( obj, bytes ):
        
        metatype = META_SERIALISABLE_TYPE_JSON_BYTES
        serialisable = obj.hex()
        
    else:
        
        metatype = META_SERIALISABLE_TYPE_JSON_OK
        serialisable = obj
        
    
    return ( metatype, serialisable )
    

def ConvertMetaSerialisableTupleToObject( meta_tuple ):
    
    ( metatype, serialisable ) = meta_tuple
    
    if metatype == META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE:
        
        obj = CreateFromSerialisableTuple( serialisable )
        
    elif metatype == META_SERIALISABLE_TYPE_JSON_BYTES:
        
        obj = bytes.fromhex( serialisable )
        
    else:
        
        obj = serialisable
        
    
    return obj
    

class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    SERIALISABLE_NAME = 'Named Base Serialisable Object'
    
    def __init__( self, name ):
        
        super().__init__()
        
        self._name = name
        
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def GetSerialisableTuple( self ):
        
        return ( self.SERIALISABLE_TYPE, self._name, self.SERIALISABLE_VERSION, self._GetSerialisableInfo() )
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    
    def SetNonDupeName( self, disallowed_names, do_casefold = False ):
        
        self._name = HydrusData.GetNonDupeName( self._name, disallowed_names, do_casefold = do_casefold )
        
    
class SerialisableDictionary( SerialisableBase, dict ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_DICTIONARY
    SERIALISABLE_NAME = 'Serialisable Dictionary'
    SERIALISABLE_VERSION = 2 # this is used in the network, do not update it casually!
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
    
    def _GetSerialisableInfo( self ):
        
        meta_keys_and_meta_values = []
        
        for ( key, value ) in self.items():
            
            # after being caught out on a recursive legacy thing here, we now coerce. I'm 99.7% confident it can't hurt
            if isinstance( value, list ) and not isinstance( value, SerialisableBase ):
                
                value = SerialisableList( value )
                
            elif isinstance( value, dict ) and not isinstance( value, SerialisableBase ):
                
                value = SerialisableDictionary( value )
                
            
            meta_key = ConvertObjectToMetaSerialisableTuple( key )
            meta_value = ConvertObjectToMetaSerialisableTuple( value )
            
            meta_keys_and_meta_values.append( ( meta_key, meta_value ) )
            
        
        return meta_keys_and_meta_values
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        have_shown_load_error = False
        
        meta_keys_and_meta_values = serialisable_info
        
        for ( meta_key, meta_value ) in meta_keys_and_meta_values:
            
            try:
                
                key = ConvertMetaSerialisableTupleToObject( meta_key )
                
                if isinstance( key, list ):
                    
                    key = tuple( key )
                    
                
                value = ConvertMetaSerialisableTupleToObject( meta_value )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    HydrusData.ShowText( 'An object in a dictionary could not load. It has been discarded from the dictionary. More may also have failed to load, but to stop error spam, they will go silently. Your client may be running on code versions behind its database. Depending on the severity of this error, you may need to rollback to a previous backup. If you have no backup, you may want to kill your hydrus process now to stop the cleansed dictionary ever being saved back to the db.' )
                    HydrusData.ShowException( e )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            
            self[ key ] = value
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( simple_key_simple_value_pairs, simple_key_serialisable_value_pairs, serialisable_key_simple_value_pairs, serialisable_key_serialisable_value_pairs ) = old_serialisable_info
            
            meta_keys_and_meta_values = []
            
            for ( key, value ) in simple_key_simple_value_pairs:
                
                meta_keys_and_meta_values.append( ( ( META_SERIALISABLE_TYPE_JSON_OK, key ), ( META_SERIALISABLE_TYPE_JSON_OK, value ) ) )
                
            
            for ( key, serialisable_value ) in simple_key_serialisable_value_pairs:
                
                meta_keys_and_meta_values.append( ( ( META_SERIALISABLE_TYPE_JSON_OK, key ), ( META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE, serialisable_value ) ) )
                
            
            for ( serialisable_key, value ) in serialisable_key_simple_value_pairs:
                
                meta_keys_and_meta_values.append( ( ( META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE, serialisable_key ), ( META_SERIALISABLE_TYPE_JSON_OK, value ) ) )
                
            
            for ( serialisable_key, serialisable_value ) in serialisable_key_serialisable_value_pairs:
                
                meta_keys_and_meta_values.append( ( ( META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE, serialisable_key ), ( META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE, serialisable_value ) ) )
                
            
            new_serialisable_info = meta_keys_and_meta_values
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetSerialisableTuple( self ):
        
        if hasattr( self, '_lock' ):
            
            with getattr( self, '_lock' ):
                
                serialisable_info = self._GetSerialisableInfo()
                
            
        else:
            
            serialisable_info = self._GetSerialisableInfo()
            
        
        return ( self.SERIALISABLE_TYPE, self.SERIALISABLE_VERSION, serialisable_info )
        
    

SERIALISABLE_TYPES_TO_OBJECT_TYPES[ SERIALISABLE_TYPE_DICTIONARY ] = SerialisableDictionary

# yo now that SerialisableDict can handle bytes anywhere, is this guy obsolete?
class SerialisableBytesDictionary( SerialisableBase, dict ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BYTES_DICT
    SERIALISABLE_NAME = 'Serialisable Dictionary With Bytestring Key/Value Support'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
    
    def _GetSerialisableInfo( self ):
        
        pairs = []
        
        for ( key, value ) in self.items():
            
            if isinstance( key, int ):
                
                encoded_key = key
                
            else:
                
                encoded_key = key.hex()
                
            
            if isinstance( value, ( list, tuple, set ) ):
                
                encoded_value = [ item.hex() for item in value ]
                
            elif value is None:
                
                encoded_value = value
                
            else:
                
                encoded_value = value.hex()
                
            
            pairs.append( ( encoded_key, encoded_value ) )
            
        
        return pairs
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( encoded_key, encoded_value ) in serialisable_info:
            
            if isinstance( encoded_key, int ):
                
                key = encoded_key
                
            else:
                
                key = bytes.fromhex( encoded_key )
                
            
            if isinstance( encoded_value, ( list, tuple, set ) ):
                
                value = [ bytes.fromhex( encoded_item ) for encoded_item in encoded_value ]
                
            elif encoded_value is None:
                
                value = encoded_value
                
            else:
                
                value = bytes.fromhex( encoded_value )
                
            
            self[ key ] = value
            
        
    
SERIALISABLE_TYPES_TO_OBJECT_TYPES[ SERIALISABLE_TYPE_BYTES_DICT ] = SerialisableBytesDictionary

class SerialisableList( SerialisableBase, list ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_LIST
    SERIALISABLE_NAME = 'Serialisable List'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
    
    def _GetSerialisableInfo( self ):
        
        meta_tuples = []
        
        for obj in self:
            
            # after being caught out on a recursive legacy thing here, we now coerce. I'm 99.7% confident it can't hurt
            # careful not to do it through for SerialisableBase--don't want to coerce a SerialisableBytesDict to a SerialisableDict
            if isinstance( obj, list ) and not isinstance( obj, SerialisableBase ):
                
                obj = SerialisableList( obj )
                
            elif isinstance( obj, dict ) and not isinstance( obj, SerialisableBase ):
                
                obj = SerialisableDictionary( obj )
                
            
            meta_tuple = ConvertObjectToMetaSerialisableTuple( obj )
            
            meta_tuples.append( meta_tuple )
            
        
        return meta_tuples
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        have_shown_load_error = False
        
        meta_tuples = serialisable_info
        
        for meta_tuple in meta_tuples:
            
            try:
                
                obj = ConvertMetaSerialisableTupleToObject( meta_tuple )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    HydrusData.ShowText( 'An object in a list could not load. It has been discarded from the list. More may also have failed to load, but to stop error spam, they will go silently. Your client may be running on code versions behind its database. Depending on the severity of this error, you may need to rollback to a previous backup. If you have no backup, you may want to kill your hydrus process now to stop the cleansed list ever being saved back to the db.' )
                    HydrusData.ShowException( e )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            
            self.append( obj )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            serialised_objects = old_serialisable_info
            
            is_serialised = True
            
            new_serialisable_info = [ ( is_serialised, serialised_object ) for serialised_object in serialised_objects ]
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            meta_items = []
            
            serialised_object_tuples = old_serialisable_info
            
            for ( is_serialised, serialised_obj ) in serialised_object_tuples:
                
                if is_serialised:
                    
                    meta_items.append( ( META_SERIALISABLE_TYPE_HYDRUS_SERIALISABLE, serialised_obj ) )
                    
                else:
                    
                    meta_items.append( ( META_SERIALISABLE_TYPE_JSON_OK, serialised_obj ) )
                    
                
            
            new_serialisable_info = meta_items
            
            return ( 3, new_serialisable_info )
            
        
    

SERIALISABLE_TYPES_TO_OBJECT_TYPES[ SERIALISABLE_TYPE_LIST ] = SerialisableList
