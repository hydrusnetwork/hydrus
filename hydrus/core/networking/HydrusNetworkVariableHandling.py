import collections.abc
import json
import traceback
import typing
import urllib
import urllib.parse # if we still need urllib, do not remove this

CBOR_AVAILABLE = False
try:
    import cbor2
    import base64
    CBOR_AVAILABLE = True
except:
    pass

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.networking import HydrusNetwork

INT_PARAMS = { 'expires', 'num', 'since', 'content_type', 'action', 'status' }
BYTE_PARAMS = { 'access_key', 'account_type_key', 'subject_account_key', 'registration_key', 'hash', 'subject_hash', 'update_hash' }
STRING_PARAMS = { 'subject_tag', 'reason', 'message' }
JSON_PARAMS = set()
JSON_BYTE_LIST_PARAMS = { 'registration_keys' }

HASH_BYTE_PARAMS = { 'hash', 'subject_hash', 'update_hash' }

def DumpHydrusArgsToNetworkBytes( args ):
    
    if not isinstance( args, HydrusSerialisable.SerialisableBase ):
        
        args = HydrusSerialisable.SerialisableDictionary( args )
        
    
    for param_name in BYTE_PARAMS:
        
        if param_name in args:
            
            args[ param_name ] = args[ param_name ].hex()
            
        
    
    for param_name in JSON_BYTE_LIST_PARAMS:
        
        if param_name in args:
            
            args[ param_name ] = [ item.hex() for item in args[ param_name ] ]
            
        
    
    if 'account_types' in args:
        
        args[ 'account_types' ] = HydrusSerialisable.SerialisableList( args[ 'account_types' ] )
        
    
    if 'account' in args:
        
        args[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( args[ 'account' ] )
        
    
    if 'accounts' in args:
        
        args[ 'accounts' ] = list( map( HydrusNetwork.Account.GenerateSerialisableTupleFromAccount, args[ 'accounts' ] ) )
        
    
    if 'service_keys_to_access_keys' in args:
        
        args[ 'service_keys_to_access_keys' ] = [ ( service_key.hex(), access_key.hex() ) for ( service_key, access_key ) in list( args[ 'service_keys_to_access_keys' ].items() ) ]
        
    
    if 'services' in args:
        
        args[ 'services' ] = [ service.ToSerialisableTuple() for service in args[ 'services' ] ]
        
    
    network_bytes = args.DumpToNetworkBytes()
    
    return network_bytes
    
def DumpToGETQuery( args: dict[ str, object ] ):
    
    args = dict( args )
    
    if 'subject_identifier' in args:
        
        subject_identifier = typing.cast( HydrusNetwork.AccountIdentifier, args[ 'subject_identifier' ] )
        
        del args[ 'subject_identifier' ]
        
        if subject_identifier.HasAccountKey():
            
            account_key = subject_identifier.GetAccountKey()
            
            args[ 'subject_account_key' ] = account_key
            
        elif subject_identifier.HasContent():
            
            content = subject_identifier.GetContent()
            
            content_type = content.GetContentType()
            content_data = content.GetContentData()
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                hash = content_data[0]
                
                args[ 'subject_hash' ] = hash
                
            elif content_type == HC.CONTENT_TYPE_MAPPING:
                
                ( tag, hash ) = content_data
                
                args[ 'subject_hash' ] = hash
                args[ 'subject_tag' ] = tag
                
            
        
    
    for name in INT_PARAMS:
        
        if name in args:
            
            value = typing.cast( int, args[ name ] )
            
            args[ name ] = str( value )
            
        
    
    for name in BYTE_PARAMS:
        
        if name in args:
            
            value = typing.cast( bytes, args[ name ] )
            
            args[ name ] = value.hex()
            
        
    
    for name in STRING_PARAMS:
        
        if name in args:
            
            value = typing.cast( str, args[ name ] )
            
            args[ name ] = urllib.parse.quote( value )
            
        
    
    query = '&'.join( [ key + '=' + value for ( key, value ) in args.items() ] )
    
    return query
    

def ParseFileArguments( path, decompression_bombs_ok = False ):

    hash = HydrusFileHandling.GetHashFromPath( path )
    
    try:
        
        mime = HydrusFileHandling.GetMime( path )
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and not decompression_bombs_ok:
            
            if HydrusImageHandling.IsDecompressionBomb( path ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'File seemed to be a Decompression Bomb, which you cannot upload!' )
                
            
        
        ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = HydrusFileHandling.GetFileInfo( path, mime = mime )
        
    except Exception as e:
        
        raise HydrusExceptions.BadRequestException( 'File ' + hash.hex() + ' could not parse: ' + str( e ) )
        
    
    args = ParsedRequestArguments()
    
    args[ 'path' ] = path
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if width is not None: args[ 'width' ] = width
    if height is not None: args[ 'height' ] = height
    if duration_ms is not None: args[ 'duration' ] = duration_ms
    if num_frames is not None: args[ 'num_frames' ] = num_frames
    args[ 'has_audio' ] = has_audio
    if num_words is not None: args[ 'num_words' ] = num_words
    
    if mime in HC.MIMES_WITH_THUMBNAILS:
        
        try:
            
            bounding_dimensions = HC.SERVER_THUMBNAIL_DIMENSIONS
            
            target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions, HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY, 100 )
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( path, target_resolution, mime, duration_ms, num_frames )
            
        except Exception as e:
            
            tb = traceback.format_exc()
            
            raise HydrusExceptions.BadRequestException( 'Could not generate thumbnail from that file:' + '\n' + tb )
            
        
        args[ 'thumbnail' ] = thumbnail_bytes
        
    
    return args
    

def ParseHydrusNetworkGETArgs( requests_args ):
    
    args = ParseTwistedRequestGETArgs( requests_args, INT_PARAMS, BYTE_PARAMS, STRING_PARAMS, JSON_PARAMS, JSON_BYTE_LIST_PARAMS )
    
    if 'subject_hash' in args: # or parent/sib stuff in args
        
        hash = args[ 'subject_hash' ]
        
        if 'subject_tag' in args:
            
            tag = args[ 'subject_tag' ]
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
            
        else:
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ hash ] )
            
        
        # TODO: add siblings and parents here
        
        args[ 'subject_identifier' ] = HydrusNetwork.AccountIdentifier( content = content )
        
    
    return args
    
def ParseNetworkBytesToParsedHydrusArgs( network_bytes ):
    
    if len( network_bytes ) == 0:
        
        return HydrusSerialisable.SerialisableDictionary()
        
    
    args = HydrusSerialisable.CreateFromNetworkBytes( network_bytes )
    
    if not isinstance( args, dict ):
        
        raise HydrusExceptions.BadRequestException( 'The given parameter did not seem to be a JSON Object!' )
        
    
    args = ParsedRequestArguments( args )
    
    for param_name in BYTE_PARAMS:
        
        if param_name in args:
            
            value = args[ param_name ]
            
            if param_name in HASH_BYTE_PARAMS and ':' in value:
                
                value = value.split( ':', 1 )[1]
                
            
            args[ param_name ] = bytes.fromhex( value )
            
        
    
    for param_name in JSON_BYTE_LIST_PARAMS:
        
        if param_name in args:
            
            args[ param_name ] = [ bytes.fromhex( encoded_item ) for encoded_item in args[ param_name ] ]
            
        
    
    # account_types should be a serialisable list, so it just works
    
    if 'account' in args:
        
        args[ 'account' ] = HydrusNetwork.Account.GenerateAccountFromSerialisableTuple( args[ 'account' ] )
        
    
    if 'accounts' in args:
        
        account_tuples = args[ 'accounts' ]
        
        args[ 'accounts' ] = [ HydrusNetwork.Account.GenerateAccountFromSerialisableTuple( account_tuple ) for account_tuple in account_tuples ]
        
    
    if 'service_keys_to_access_keys' in args:
        
        args[ 'service_keys_to_access_keys' ] = { bytes.fromhex( encoded_service_key ) : bytes.fromhex( encoded_access_key ) for ( encoded_service_key, encoded_access_key ) in args[ 'service_keys_to_access_keys' ] }
        
    
    if 'services' in args:
        
        service_tuples = args[ 'services' ]
        
        args[ 'services' ] = [ HydrusNetwork.GenerateServiceFromSerialisableTuple( service_tuple ) for service_tuple in service_tuples ]
        
    
    return args
    
def ParseTwistedRequestGETArgs( requests_args: dict, int_params, byte_params, string_params, json_params, json_byte_list_params ):
    
    args = ParsedRequestArguments()
    
    cbor_requested = b'cbor' in requests_args
    
    if cbor_requested and not CBOR_AVAILABLE:
        
        raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
        
    
    for ( name_bytes, values_bytes ) in requests_args.items():
        
        try:
            
            name = str( name_bytes, 'utf-8' )
            
        except UnicodeDecodeError:
            
            continue
            
        
        value_bytes = values_bytes[0]
        
        try:
            
            value = str( value_bytes, 'utf-8' )
            
        except UnicodeDecodeError:
            
            continue
            
        
        if name in int_params:
            
            try:
                
                args[ name ] = int( value )
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as an integer, but it failed.' ) from e
                
            
        elif name in byte_params:
            
            try:
                
                if name in HASH_BYTE_PARAMS and ':' in value:
                    
                    value = value.split( ':', 1 )[1]
                    
                
                args[ name ] = bytes.fromhex( value )
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a hex string, but it failed.' ) from e
                
            
        elif name in string_params:
            
            try:
                
                args[ name ] = urllib.parse.unquote( value )
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a percent-encoded string, but it failed.' ) from e
                
            
        elif name in json_params:
            
            try:
                
                if cbor_requested:
                    
                    args[ name ] = cbor2.loads( base64.urlsafe_b64decode( value ) )
                    
                else:
                    
                    args[ name ] = json.loads( urllib.parse.unquote( value ) )
                    
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a json-encoded string, but it failed.' ) from e
                
            
        elif name in json_byte_list_params:
            
            try:
                
                if cbor_requested:
                    
                    list_of_hex_strings = cbor2.loads( base64.urlsafe_b64decode( value ) )
                    
                else:
                    
                    list_of_hex_strings = json.loads( urllib.parse.unquote( value ) )
                    
                
                args[ name ] = [ bytes.fromhex( hex_string ) for hex_string in list_of_hex_strings ]
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a json-encoded hex strings, but it failed.' ) from e
                
            
        
    
    return args
    

variable_type_to_text_lookup = collections.defaultdict( lambda: 'unknown!' )

variable_type_to_text_lookup[ int ] = 'integer'
variable_type_to_text_lookup[ float ] = 'float'
variable_type_to_text_lookup[ str ] = 'string'
variable_type_to_text_lookup[ bytes ] = 'hex-encoded bytestring'
variable_type_to_text_lookup[ bool ] = 'boolean'
variable_type_to_text_lookup[ list ] = 'list'
variable_type_to_text_lookup[ dict ] = 'object/dict'

def GetValueFromDict( dictionary: dict, key, expected_type, expected_list_type = None, expected_dict_types = None, default_value = None, none_on_missing = False ):
    
    # not None because in JSON sometimes people put 'null' to mean 'did not enter this optional parameter'
    if key in dictionary and dictionary[ key ] is not None:
        
        value = dictionary[ key ]
        
        TestVariableType( key, value, expected_type, expected_list_type = expected_list_type, expected_dict_types = expected_dict_types )
        
        return value
        
    else:
        
        if default_value is None and not none_on_missing:
            
            raise HydrusExceptions.BadRequestException( 'The required parameter "{}" was missing!'.format( key ) )
            
        else:
            
            return default_value
            
        
    

def TestVariableType( name: str, value: typing.Any, expected_type, expected_list_type = None, expected_dict_types = None, allowed_values = None ):
    
    if not isinstance( value, expected_type ):
        
        if expected_type is float and isinstance( value, int ):
            
            return
            
        
        type_error_text = variable_type_to_text_lookup[ expected_type ]
        
        raise HydrusExceptions.BadRequestException( 'The parameter "{}", with value "{}", was not the expected type: {}!'.format( name, value, type_error_text ) )
        
    
    if allowed_values is not None and value not in allowed_values:
        
        raise HydrusExceptions.BadRequestException( 'The parameter "{}", with value "{}", was not in the allowed values: {}!'.format( name, value, allowed_values ) )
        
    
    if expected_type is list and expected_list_type is not None:
        
        for item in value:
            
            if not isinstance( item, expected_list_type ):
                
                raise HydrusExceptions.BadRequestException( 'The list parameter "{}" held an item, "{}" that was {} and not the expected type: {}!'.format( name, item, type( item ), variable_type_to_text_lookup[ expected_list_type ] ) )
                
            
        
    
    if expected_type is dict and expected_dict_types is not None:
        
        ( expected_key_type, expected_value_type ) = expected_dict_types
        
        for ( dict_key, dict_value ) in value.items():
            
            if not isinstance( dict_key, expected_key_type ):
                
                raise HydrusExceptions.BadRequestException( 'The Object parameter "{}" held a key, "{}" that was {} and not the expected type: {}!'.format( name, dict_key, type( dict_key ), variable_type_to_text_lookup[ expected_key_type ] ) )
                
            
            if not isinstance( dict_value, expected_value_type ):
                
                raise HydrusExceptions.BadRequestException( 'The Object parameter "{}" held a value, "{}" that was {} and not the expected type: {}!'.format( name, dict_value, type( dict_value ), variable_type_to_text_lookup[ expected_value_type ] ) )
                
            
        
    

EXPECTED_TYPE = typing.TypeVar( 'EXPECTED_TYPE' )

class ParsedRequestArguments( dict ):
    
    def __missing__( self, key ):
        
        raise HydrusExceptions.BadRequestException( 'It looks like the parameter "{}" was missing!'.format( key ) )
        
    
    def GetValue( self, key, expected_type: EXPECTED_TYPE, expected_list_type = None, expected_dict_types = None, default_value = None ) -> EXPECTED_TYPE:
        
        return GetValueFromDict( self, key, expected_type, expected_list_type = expected_list_type, expected_dict_types = expected_dict_types, default_value = default_value )
        
    
    def GetValueOrNone( self, key, expected_type: EXPECTED_TYPE, expected_list_type = None, expected_dict_types = None ) -> EXPECTED_TYPE | None:
        
        return GetValueFromDict( self, key, expected_type, expected_list_type = expected_list_type, expected_dict_types = expected_dict_types, none_on_missing = True )
        
    
