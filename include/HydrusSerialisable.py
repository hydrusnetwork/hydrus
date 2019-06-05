import json
import zlib

LZ4_OK = False

try:
    
    import lz4
    import lz4.block
    
    LZ4_OK = True
    
except: # ImportError wasn't enough here as Linux went up the shoot with a __version__ doesn't exist bs
    
    print( 'Could not import lz4--nbd.' )
    
SERIALISABLE_TYPE_BASE = 0
SERIALISABLE_TYPE_BASE_NAMED = 1
SERIALISABLE_TYPE_SHORTCUT_SET = 2
SERIALISABLE_TYPE_SUBSCRIPTION = 3
SERIALISABLE_TYPE_PERIODIC = 4
SERIALISABLE_TYPE_GALLERY_IDENTIFIER = 5
SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS = 6
SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS = 7
SERIALISABLE_TYPE_FILE_SEED_CACHE = 8
SERIALISABLE_TYPE_HDD_IMPORT = 9
SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE = 10
SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE = 11
SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER = 12
SERIALISABLE_TYPE_GUI_SESSION = 13
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
SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS = 43
SERIALISABLE_TYPE_TAG_FILTER = 44
SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER = 45
SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER = 46
SERIALISABLE_TYPE_NETWORK_CONTEXT = 47
SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER = 48
SERIALISABLE_TYPE_MEDIA_SORT = 49
SERIALISABLE_TYPE_URL_CLASS = 50
SERIALISABLE_TYPE_STRING_MATCH = 51
SERIALISABLE_TYPE_CHECKER_OPTIONS = 52
SERIALISABLE_TYPE_NETWORK_DOMAIN_MANAGER = 53
SERIALISABLE_TYPE_SUBSCRIPTION_QUERY = 54
SERIALISABLE_TYPE_STRING_CONVERTER = 55
SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS = 56
SERIALISABLE_TYPE_FILE_SEED = 57
SERIALISABLE_TYPE_PAGE_PARSER = 58
SERIALISABLE_TYPE_PARSE_FORMULA_COMPOUND = 59
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

SERIALISABLE_TYPES_TO_OBJECT_TYPES = {}

def CreateFromNetworkBytes( network_string ):
    
    try:
        
        obj_bytes = zlib.decompress( network_string )
        
    except zlib.error:
        
        if LZ4_OK:
            
            obj_bytes = lz4.block.decompress( network_string )
            
        else:
            
            raise
            
        
    
    obj_string = str( obj_bytes, 'utf-8' )
    
    return CreateFromString( obj_string )
    
def CreateFromString( obj_string ):
    
    obj_tuple = json.loads( obj_string )
    
    return CreateFromSerialisableTuple( obj_tuple )
    
def CreateFromSerialisableTuple( obj_tuple ):
    
    if len( obj_tuple ) == 3:
        
        ( serialisable_type, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]()
        
    else:
        
        ( serialisable_type, name, version, serialisable_info ) = obj_tuple
        
        obj = SERIALISABLE_TYPES_TO_OBJECT_TYPES[ serialisable_type ]( name )
        
    
    obj.InitialiseFromSerialisableInfo( version, serialisable_info )
    
    return obj
    
def GetNonDupeName( original_name, disallowed_names ):
    
    i = 1
    
    non_dupe_name = original_name
    
    while non_dupe_name in disallowed_names:
        
        non_dupe_name = original_name + ' (' + str( i ) + ')'
        
        i += 1
        
    
    return non_dupe_name
    
def SetNonDupeName( obj, disallowed_names ):
    
    non_dupe_name = GetNonDupeName( obj.GetName(), disallowed_names )
    
    obj.SetName( non_dupe_name )

class SerialisableBase( object ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE
    SERIALISABLE_NAME = 'Base Serialisable Object'
    SERIALISABLE_VERSION = 1
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        return old_serialisable_info
        
    
    def DumpToNetworkBytes( self ):
        
        obj_string = self.DumpToString()
        
        obj_bytes = bytes( obj_string, 'utf-8' )
        
        return zlib.compress( obj_bytes, 9 )
        
    
    def DumpToString( self ):
        
        obj_tuple = self.GetSerialisableTuple()
        
        return json.dumps( obj_tuple )
        
    
    def Duplicate( self ):
        
        return CreateFromString( self.DumpToString() )
        
    
    def GetSerialisableTuple( self ):
        
        if hasattr( self, '_lock' ):
            
            with getattr( self, '_lock' ):
                
                serialisable_info = self._GetSerialisableInfo()
                
            
        else:
            
            serialisable_info = self._GetSerialisableInfo()
            
        
        return ( self.SERIALISABLE_TYPE, self.SERIALISABLE_VERSION, serialisable_info )
        
    
    def InitialiseFromSerialisableInfo( self, version, serialisable_info ):
        
        while version < self.SERIALISABLE_VERSION:
            
            ( version, serialisable_info ) = self._UpdateSerialisableInfo( version, serialisable_info )
            
        
        self._InitialiseFromSerialisableInfo( serialisable_info )
        
    
class SerialisableBaseNamed( SerialisableBase ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BASE_NAMED
    SERIALISABLE_NAME = 'Named Base Serialisable Object'
    
    def __init__( self, name ):
        
        SerialisableBase.__init__( self )
        
        self._name = name
        
    
    def GetSerialisableTuple( self ):
        
        return ( self.SERIALISABLE_TYPE, self._name, self.SERIALISABLE_VERSION, self._GetSerialisableInfo() )
        
    
    def GetName( self ): return self._name
    
    def SetName( self, name ): self._name = name
    
    def SetNonDupeName( self, disallowed_names ):
        
        self._name = GetNonDupeName( self._name, disallowed_names )
        
    
class SerialisableDictionary( SerialisableBase, dict ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_DICTIONARY
    SERIALISABLE_NAME = 'Serialisable Dictionary'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        dict.__init__( self, *args, **kwargs )
        SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        simple_key_simple_value_pairs = []
        simple_key_serialisable_value_pairs = []
        serialisable_key_simple_value_pairs = []
        serialisable_key_serialisable_value_pairs = []
        
        for ( key, value ) in list(self.items()):
            
            if isinstance( key, SerialisableBase ):
                
                serialisable_key = key.GetSerialisableTuple()
                
                if isinstance( value, SerialisableBase ):
                    
                    serialisable_value = value.GetSerialisableTuple()
                    
                    serialisable_key_serialisable_value_pairs.append( ( serialisable_key, serialisable_value ) )
                    
                else:
                    
                    serialisable_value = value
                    
                    serialisable_key_simple_value_pairs.append( ( serialisable_key, serialisable_value ) )
                    
                
            else:
                
                serialisable_key = key
                
                if isinstance( value, SerialisableBase ):
                    
                    serialisable_value = value.GetSerialisableTuple()
                    
                    simple_key_serialisable_value_pairs.append( ( serialisable_key, serialisable_value ) )
                    
                else:
                    
                    serialisable_value = value
                    
                    simple_key_simple_value_pairs.append( ( serialisable_key, serialisable_value ) )
                    
                
            
        
        return ( simple_key_simple_value_pairs, simple_key_serialisable_value_pairs, serialisable_key_simple_value_pairs, serialisable_key_serialisable_value_pairs )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( simple_key_simple_value_pairs, simple_key_serialisable_value_pairs, serialisable_key_simple_value_pairs, serialisable_key_serialisable_value_pairs ) = serialisable_info
        
        for ( key, value ) in simple_key_simple_value_pairs:
            
            self[ key ] = value
            
        
        for ( key, serialisable_value ) in simple_key_serialisable_value_pairs:
            
            value = CreateFromSerialisableTuple( serialisable_value )
            
            self[ key ] = value
            
        
        for ( serialisable_key, value ) in serialisable_key_simple_value_pairs:
            
            key = CreateFromSerialisableTuple( serialisable_key )
            
            self[ key ] = value
            
        
        for ( serialisable_key, serialisable_value ) in serialisable_key_serialisable_value_pairs:
            
            key = CreateFromSerialisableTuple( serialisable_key )
            
            value = CreateFromSerialisableTuple( serialisable_value )
            
            self[ key ] = value
            
        
    
SERIALISABLE_TYPES_TO_OBJECT_TYPES[ SERIALISABLE_TYPE_DICTIONARY ] = SerialisableDictionary

class SerialisableBytesDictionary( SerialisableBase, dict ):
    
    SERIALISABLE_TYPE = SERIALISABLE_TYPE_BYTES_DICT
    SERIALISABLE_NAME = 'Serialisable Dictionary With Bytestring Key/Value Support'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        dict.__init__( self, *args, **kwargs )
        SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        pairs = []
        
        for ( key, value ) in list(self.items()):
            
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
    SERIALISABLE_VERSION = 1
    
    def __init__( self, *args, **kwargs ):
        
        list.__init__( self, *args, **kwargs )
        SerialisableBase.__init__( self )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ obj.GetSerialisableTuple() for obj in self ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for obj_tuple in serialisable_info:
            
            self.append( CreateFromSerialisableTuple( obj_tuple ) )
            
        
    
SERIALISABLE_TYPES_TO_OBJECT_TYPES[ SERIALISABLE_TYPE_LIST ] = SerialisableList
