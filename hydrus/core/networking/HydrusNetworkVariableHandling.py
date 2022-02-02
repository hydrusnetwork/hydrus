import json
import os
import traceback
import typing
import urllib

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusSerialisable
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
    
def DumpToGETQuery( args ):
    
    args = dict( args )
    
    if 'subject_identifier' in args:
        
        subject_identifier = args[ 'subject_identifier' ]
        
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
            
            args[ name ] = str( args[ name ] )
            
        
    
    for name in BYTE_PARAMS:
        
        if name in args:
            
            args[ name ] = args[ name ].hex()
            
        
    
    for name in STRING_PARAMS:
        
        if name in args:
            
            args[ name ] = urllib.parse.quote( args[ name ] )
            
        
    
    query = '&'.join( [ key + '=' + value for ( key, value ) in args.items() ] )
    
    return query
    
def ParseFileArguments( path, decompression_bombs_ok = False ):
    
    HydrusImageHandling.ConvertToPNGIfBMP( path )
    
    hash = HydrusFileHandling.GetHashFromPath( path )
    
    try:
        
        mime = HydrusFileHandling.GetMime( path )
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and not decompression_bombs_ok:
            
            if HydrusImageHandling.IsDecompressionBomb( path ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'File seemed to be a Decompression Bomb, which you cannot upload!' )
                
            
        
        ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = HydrusFileHandling.GetFileInfo( path, mime = mime )
        
    except Exception as e:
        
        raise HydrusExceptions.BadRequestException( 'File ' + hash.hex() + ' could not parse: ' + str( e ) )
        
    
    args = ParsedRequestArguments()
    
    args[ 'path' ] = path
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if width is not None: args[ 'width' ] = width
    if height is not None: args[ 'height' ] = height
    if duration is not None: args[ 'duration' ] = duration
    if num_frames is not None: args[ 'num_frames' ] = num_frames
    args[ 'has_audio' ] = has_audio
    if num_words is not None: args[ 'num_words' ] = num_words
    
    if mime in HC.MIMES_WITH_THUMBNAILS:
        
        try:
            
            bounding_dimensions = HC.SERVER_THUMBNAIL_DIMENSIONS
            
            ( clip_rect, target_resolution ) = HydrusImageHandling.GetThumbnailResolutionAndClipRegion( ( width, height ), bounding_dimensions, HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY )
            
            thumbnail_bytes = HydrusFileHandling.GenerateThumbnailBytes( path, target_resolution, mime, duration, num_frames, clip_rect = clip_rect )
            
        except Exception as e:
            
            tb = traceback.format_exc()
            
            raise HydrusExceptions.BadRequestException( 'Could not generate thumbnail from that file:' + os.linesep + tb )
            
        
        args[ 'thumbnail' ] = thumbnail_bytes
        
    
    return args
    
def ParseHydrusNetworkGETArgs( requests_args ):
    
    args = ParseTwistedRequestGETArgs( requests_args, INT_PARAMS, BYTE_PARAMS, STRING_PARAMS, JSON_PARAMS, JSON_BYTE_LIST_PARAMS )
    
    if 'subject_account_key' in args:
        
        args[ 'subject_identifier' ] = HydrusNetwork.AccountIdentifier( account_key = args[ 'subject_account_key' ] )
        
    elif 'subject_hash' in args:
        
        hash = args[ 'subject_hash' ]
        
        if 'subject_tag' in args:
            
            tag = args[ 'subject_tag' ]
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
            
        else:
            
            content = HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ hash ] )
            
        
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
    
def ParseTwistedRequestGETArgs( requests_args, int_params, byte_params, string_params, json_params, json_byte_list_params ):
    
    args = ParsedRequestArguments()
    
    for name_bytes in requests_args:
        
        values_bytes = requests_args[ name_bytes ]
        
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
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a percent-encdode string, but it failed.' ) from e
                
            
        elif name in json_params:
            
            try:
                
                args[ name ] = json.loads( urllib.parse.unquote( value ) )
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a json-encoded string, but it failed.' ) from e
                
            
        elif name in json_byte_list_params:
            
            try:
                
                list_of_hex_strings = json.loads( urllib.parse.unquote( value ) )
                
                args[ name ] = [ bytes.fromhex( hex_string ) for hex_string in list_of_hex_strings ]
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'' + name + '\' as a json-encoded hex strings, but it failed.' ) from e
                
            
        
    
    return args
    
class ParsedRequestArguments( dict ):
    
    def __missing__( self, key ):
        
        raise HydrusExceptions.BadRequestException( 'It looks like the parameter "{}" was missing!'.format( key ) )
        
    
    def GetValue( self, key, expected_type, expected_list_type = None, default_value = None ):
        
        # not None because in JSON sometimes people put 'null' to mean 'did not enter this optional parameter'
        if key in self and self[ key ] is not None:
            
            value = self[ key ]
            
            error_text_lookup = {}
            
            error_text_lookup[ int ] = 'integer'
            error_text_lookup[ str ] = 'string'
            error_text_lookup[ bytes ] = 'hex-encoded bytestring'
            error_text_lookup[ bool ] = 'boolean'
            error_text_lookup[ list ] = 'list'
            error_text_lookup[ dict ] = 'object/dict'
            
            if not isinstance( value, expected_type ):
                
                if expected_type in error_text_lookup:
                    
                    type_error_text = error_text_lookup[ expected_type ]
                    
                else:
                    
                    type_error_text = 'unknown!'
                    
                
                raise HydrusExceptions.BadRequestException( 'The parameter "{}" was not the expected type: {}!'.format( key, type_error_text ) )
                
            
            if expected_type is list and expected_list_type is not None:
                
                for item in value:
                    
                    if not isinstance( item, expected_list_type ):
                        
                        if expected_list_type in error_text_lookup:
                            
                            type_error_text = error_text_lookup[ expected_list_type ]
                            
                        else:
                            
                            type_error_text = 'unknown!'
                            
                        
                        raise HydrusExceptions.BadRequestException( 'The list parameter "{}" held an item that was not the expected type: {}!'.format( key, type_error_text ) )
                        
                    
                
            
            return value
            
        else:
            
            if default_value is None:
                
                raise HydrusExceptions.BadRequestException( 'The required parameter "{}" was missing!'.format( key ) )
                
            else:
                
                return default_value
                
            
        
    
