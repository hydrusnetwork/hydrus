import collections
import collections.abc
import json
import os
import threading
import time
import traceback
import typing

CBOR_AVAILABLE = False

try:
    
    import cbor2
    CBOR_AVAILABLE = True
    
except:
    
    pass
    

from twisted.web.static import File as FileResource

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags
from hydrus.core import HydrusTemp
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client import ClientSearchParseSystemPredicates
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions

local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

LOCAL_BOORU_INT_PARAMS = set()
LOCAL_BOORU_BYTE_PARAMS = { 'share_key', 'hash' }
LOCAL_BOORU_STRING_PARAMS = set()
LOCAL_BOORU_JSON_PARAMS = set()
LOCAL_BOORU_JSON_BYTE_LIST_PARAMS = set()

# if a variable name isn't defined here, a GET with it won't work

CLIENT_API_INT_PARAMS = { 'file_id', 'file_sort_type', 'potentials_search_type', 'pixel_duplicates', 'max_hamming_distance', 'max_num_pairs' }
CLIENT_API_BYTE_PARAMS = { 'hash', 'destination_page_key', 'page_key', 'service_key', 'Hydrus-Client-API-Access-Key', 'Hydrus-Client-API-Session-Key', 'file_service_key', 'deleted_file_service_key', 'tag_service_key', 'tag_service_key_1', 'tag_service_key_2' }
CLIENT_API_STRING_PARAMS = { 'name', 'url', 'domain', 'search', 'service_name', 'reason', 'tag_display_type', 'source_hash_type', 'desired_hash_type' }
CLIENT_API_JSON_PARAMS = { 'basic_permissions', 'tags', 'tags_1', 'tags_2', 'file_ids', 'only_return_identifiers', 'only_return_basic_information', 'create_new_file_ids', 'detailed_url_information', 'hide_service_keys_tags', 'simple', 'file_sort_asc', 'return_hashes', 'return_file_ids', 'include_notes', 'notes', 'note_names', 'doublecheck_file_system' }
CLIENT_API_JSON_BYTE_LIST_PARAMS = { 'file_service_keys', 'deleted_file_service_keys', 'hashes' }
CLIENT_API_JSON_BYTE_DICT_PARAMS = { 'service_keys_to_tags', 'service_keys_to_actions_to_tags', 'service_keys_to_additional_tags' }

LEGACY_CLIENT_API_SERVICE_NAME_STRING_PARAMS = { 'file_service_name', 'tag_service_name' }
CLIENT_API_STRING_PARAMS.update( LEGACY_CLIENT_API_SERVICE_NAME_STRING_PARAMS )

LEGACY_CLIENT_API_SERVICE_NAME_JSON_DICT_PARAMS = { 'service_names_to_tags', 'service_names_to_actions_to_tags', 'service_names_to_additional_tags' }
CLIENT_API_JSON_PARAMS.update( LEGACY_CLIENT_API_SERVICE_NAME_JSON_DICT_PARAMS )

def ConvertLegacyServiceNameParamToKey( param_name: str ):
    
    # top tier, works for service_name and service_names
    return param_name.replace( 'name', 'key' )
    

def Dumps( data, mime ):
    
    if mime == HC.APPLICATION_CBOR:
        
        if not CBOR_AVAILABLE:
            
            raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
            
        
        return cbor2.dumps( data )
    
    else:
        
        return json.dumps( data )
        
    
def CheckHashLength( hashes, hash_type = 'sha256' ):
    
    if len( hashes ) == 0:
        
        raise HydrusExceptions.BadRequestException( 'Sorry, I was expecting at least 1 {} hash, but none were given!'.format( hash_type ) )
        
    
    hash_types_to_length = {
        'sha256' : 32,
        'md5' : 16,
        'sha1' : 20,
        'sha512' : 64
    }
    
    hash_length = hash_types_to_length[ hash_type ]
    
    for hash in hashes:
        
        if len( hash ) != hash_length:
            
            raise HydrusExceptions.BadRequestException(
                'Sorry, one of the given hashes was the wrong length! {} hashes should be {} bytes long, but {} is {} bytes long!'.format(
                    hash_type,
                    hash_length,
                    hash.hex(),
                    len( hash )
                )
            )
            
        
    

def CheckFileService( file_service_key: bytes ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( file_service_key )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the file service "{}"!'.format( file_service_key.hex() ) )
        
    
    if service.GetServiceType() not in HC.ALL_FILE_SERVICES:
        
        raise HydrusExceptions.BadRequestException( 'Sorry, the service key "{}" did not give a file service!'.format( file_service_key.hex() ) )
        
    
    return service
    

def CheckTagService( tag_service_key: bytes ):
    
    try:
        
        service = HG.client_controller.services_manager.GetService( tag_service_key )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the tag service "{}"!'.format( tag_service_key.hex() ) )
        
    
    if service.GetServiceType() not in HC.ALL_TAG_SERVICES:
        
        raise HydrusExceptions.BadRequestException( 'Sorry, the service key "{}" did not give a tag service!'.format( tag_service_key.hex() ) )
        
    
    return service
    

def GetServiceKeyFromName( service_name: str ):
    
    try:
        
        service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.ALL_SERVICES, service_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with name "{}"!'.format( service_name ) )
        
    
    return service_key
    

def ParseLocalBooruGETArgs( requests_args ):
    
    args = HydrusNetworkVariableHandling.ParseTwistedRequestGETArgs( requests_args, LOCAL_BOORU_INT_PARAMS, LOCAL_BOORU_BYTE_PARAMS, LOCAL_BOORU_STRING_PARAMS, LOCAL_BOORU_JSON_PARAMS, LOCAL_BOORU_JSON_BYTE_LIST_PARAMS )
    
    return args
    

def ParseClientLegacyArgs( args: dict ):
    
    # adding this v514, so delete when appropriate
    
    parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments( args )
    
    legacy_service_string_param_names = LEGACY_CLIENT_API_SERVICE_NAME_STRING_PARAMS.intersection( parsed_request_args.keys() )
    
    for legacy_service_string_param_name in legacy_service_string_param_names:
        
        service_name = parsed_request_args[ legacy_service_string_param_name ]
        
        service_key = GetServiceKeyFromName( service_name )
        
        del parsed_request_args[ legacy_service_string_param_name ]
        
        new_service_bytes_param_name = ConvertLegacyServiceNameParamToKey( legacy_service_string_param_name )
        
        parsed_request_args[ new_service_bytes_param_name ] = service_key
        
    
    legacy_service_dict_param_names = LEGACY_CLIENT_API_SERVICE_NAME_JSON_DICT_PARAMS.intersection( parsed_request_args.keys() )
    
    for legacy_service_dict_param_name in legacy_service_dict_param_names:
        
        service_keys_to_gubbins = {}
        
        service_names_to_gubbins = parsed_request_args[ legacy_service_dict_param_name ]
        
        for ( service_name, gubbins ) in service_names_to_gubbins.items():
            
            service_key = GetServiceKeyFromName( service_name )
            
            service_keys_to_gubbins[ service_key ] = gubbins
            
        
        del parsed_request_args[ legacy_service_dict_param_name ]
        
        new_service_dict_param_name = ConvertLegacyServiceNameParamToKey( legacy_service_dict_param_name )
        
        # little hack for a super old obsolete thing, it got renamed more significantly
        if new_service_dict_param_name == 'service_keys_to_tags':
            
            parsed_request_args[ 'service_keys_to_additional_tags' ] = service_keys_to_gubbins
            
        
        parsed_request_args[ new_service_dict_param_name ] = service_keys_to_gubbins
        
    
    return parsed_request_args
    

def ParseClientAPIGETArgs( requests_args ):
    
    args = HydrusNetworkVariableHandling.ParseTwistedRequestGETArgs( requests_args, CLIENT_API_INT_PARAMS, CLIENT_API_BYTE_PARAMS, CLIENT_API_STRING_PARAMS, CLIENT_API_JSON_PARAMS, CLIENT_API_JSON_BYTE_LIST_PARAMS )
    
    args = ParseClientLegacyArgs( args )
    
    return args
    

def ParseClientAPIPOSTByteArgs( args ):
    
    if not isinstance( args, dict ):
        
        raise HydrusExceptions.BadRequestException( 'The given parameter did not seem to be a JSON Object!' )
        
    
    parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments( args )
    
    for var_name in CLIENT_API_BYTE_PARAMS:
        
        if var_name in parsed_request_args:
            
            try:
                
                raw_value = parsed_request_args[ var_name ]
                
                # In JSON, if someone puts 'null' for an optional value, treat that as 'did not enter anything'
                if raw_value is None:
                    
                    del parsed_request_args[ var_name ]
                    
                    continue
                    
                
                v = bytes.fromhex( raw_value )
                
                if len( v ) == 0:
                    
                    del parsed_request_args[ var_name ]
                    
                else:
                    
                    parsed_request_args[ var_name ] = v
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'{}\' as a hex string, but it failed.'.format( var_name ) )
                
            
        
    
    for var_name in CLIENT_API_JSON_BYTE_LIST_PARAMS:
        
        if var_name in parsed_request_args:
            
            try:
                
                raw_value = parsed_request_args[ var_name ]
                
                # In JSON, if someone puts 'null' for an optional value, treat that as 'did not enter anything'
                if raw_value is None:
                    
                    del parsed_request_args[ var_name ]
                    
                    continue
                    
                
                v_list = [ bytes.fromhex( hash_hex ) for hash_hex in raw_value ]
                
                v_list = [ v for v in v_list if len( v ) > 0 ]
                
                if len( v_list ) == 0:
                    
                    del parsed_request_args[ var_name ]
                    
                else:
                    
                    parsed_request_args[ var_name ] = v_list
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'{}\' as a list of hex strings, but it failed.'.format( var_name ) )
                
            
        
    
    for var_name in CLIENT_API_JSON_BYTE_DICT_PARAMS:
        
        if var_name in parsed_request_args:
            
            try:
                
                raw_dict = parsed_request_args[ var_name ]
                
                # In JSON, if someone puts 'null' for an optional value, treat that as 'did not enter anything'
                if raw_dict is None:
                    
                    del parsed_request_args[ var_name ]
                    
                    continue
                    
                
                bytes_dict = {}
                
                for ( key, value ) in raw_dict.items():
                    
                    if len( key ) == 0:
                        
                        continue
                        
                    
                    bytes_key = bytes.fromhex( key )
                    
                    bytes_dict[ bytes_key ] = value
                    
                
                if len( bytes_dict ) == 0:
                    
                    del parsed_request_args[ var_name ]
                    
                else:
                    
                    parsed_request_args[ var_name ] = bytes_dict
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'{}\' as a dictionary of hex strings to other data, but it failed.'.format( var_name ) )
                
            
        
    
    parsed_request_args = ParseClientLegacyArgs( parsed_request_args )
    
    return parsed_request_args
    
def ParseClientAPIPOSTArgs( request ):
    
    request.content.seek( 0 )
    
    if not request.requestHeaders.hasHeader( 'Content-Type' ):
        
        request_content_type_mime = HC.APPLICATION_JSON
        
        parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments()
        
        total_bytes_read = 0
        
    else:
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        if ';' in content_type:
            
            # lmao: application/json;charset=utf-8
            content_type = content_type.split( ';', 1 )[0]
            
        
        try:
            
            request_content_type_mime = HC.mime_enum_lookup[ content_type ]
            
        except:
            
            raise HydrusExceptions.BadRequestException( 'Did not recognise Content-Type header!' )
            
        
        total_bytes_read = 0
        
        if request_content_type_mime == HC.APPLICATION_JSON:
            
            json_bytes = request.content.read()
            
            total_bytes_read += len( json_bytes )
            
            json_string = str( json_bytes, 'utf-8' )
            
            try:
                
                args = json.loads( json_string )
                
            except json.decoder.JSONDecodeError as e:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, did not understand the JSON you gave me: {}'.format( str( e ) ) )
                
            
            parsed_request_args = ParseClientAPIPOSTByteArgs( args )
            
        elif request_content_type_mime == HC.APPLICATION_CBOR:
            
            if not CBOR_AVAILABLE:
                
                raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
                
            
            cbor_bytes = request.content.read()
            
            total_bytes_read += len( cbor_bytes )
            
            args = cbor2.loads( cbor_bytes )
            
            parsed_request_args = ParseClientAPIPOSTByteArgs( args )
            
        else:
            
            parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments()
            
            ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            with open( temp_path, 'wb' ) as f:
                
                for block in HydrusPaths.ReadFileLikeAsBlocks( request.content ): 
                    
                    f.write( block )
                    
                    total_bytes_read += len( block )
                    
                
            
        
    
    return ( parsed_request_args, total_bytes_read )
    
def ParseClientAPISearchPredicates( request ) -> typing.List[ ClientSearch.Predicate ]:
    
    default_search_values = {}
    
    default_search_values[ 'tags' ] = []
    
    for ( key, value ) in default_search_values.items():
        
        if key not in request.parsed_request_args:
            
            request.parsed_request_args[ key ] = value
            
        
    
    tags = request.parsed_request_args[ 'tags' ]
    
    predicates = ConvertTagListToPredicates( request, tags )
    
    if len( predicates ) == 0:
        
        return predicates
        
    
    we_have_at_least_one_inclusive_tag = True in ( predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG and predicate.IsInclusive() for predicate in predicates )
    
    if not we_have_at_least_one_inclusive_tag:
        
        try:
            
            request.client_api_permissions.CheckCanSeeAllFiles()
            
        except HydrusExceptions.InsufficientCredentialsException:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, you do not have permission to see all files on this client. Please add a regular tag to your search.' )
            
        
    
    return predicates
    

def ParseDuplicateSearch( request: HydrusServerRequest.HydrusRequest ):
    
    location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
    
    tag_service_key_1 = request.parsed_request_args.GetValue( 'tag_service_key_1', bytes, default_value = CC.COMBINED_TAG_SERVICE_KEY )
    tag_service_key_2 = request.parsed_request_args.GetValue( 'tag_service_key_2', bytes, default_value = CC.COMBINED_TAG_SERVICE_KEY )
    
    CheckTagService( tag_service_key_1 )
    CheckTagService( tag_service_key_2 )
    
    tag_context_1 = ClientSearch.TagContext( service_key = tag_service_key_1 )
    tag_context_2 = ClientSearch.TagContext( service_key = tag_service_key_2 )
    
    tags_1 = request.parsed_request_args.GetValue( 'tags_1', list, default_value = [] )
    tags_2 = request.parsed_request_args.GetValue( 'tags_2', list, default_value = [] )
    
    if len( tags_1 ) == 0:
        
        predicates_1 = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
    else:
        
        predicates_1 = ConvertTagListToPredicates( request, tags_1, do_permission_check = False )
        
    
    if len( tags_2 ) == 0:
        
        predicates_2 = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
    else:
        
        predicates_2 = ConvertTagListToPredicates( request, tags_2, do_permission_check = False )
        
    
    
    file_search_context_1 = ClientSearch.FileSearchContext( location_context = location_context, tag_context = tag_context_1, predicates = predicates_1 )
    file_search_context_2 = ClientSearch.FileSearchContext( location_context = location_context, tag_context = tag_context_2, predicates = predicates_2 )
    
    dupe_search_type = request.parsed_request_args.GetValue( 'potentials_search_type', int, default_value = CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
    pixel_dupes_preference = request.parsed_request_args.GetValue( 'pixel_duplicates', int, default_value = CC.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
    max_hamming_distance = request.parsed_request_args.GetValue( 'max_hamming_distance', int, default_value = 4 )
    
    return (
        file_search_context_1,
        file_search_context_2,
        dupe_search_type,
        pixel_dupes_preference,
        max_hamming_distance
    )
    

def ParseLocationContext( request: HydrusServerRequest.HydrusRequest, default: ClientLocation.LocationContext, deleted_allowed = True ):
    
    current_file_service_keys = set()
    deleted_file_service_keys = set()
    
    if 'file_service_key' in request.parsed_request_args:
        
        file_service_key = request.parsed_request_args.GetValue( 'file_service_key', bytes )
        
        current_file_service_keys.add( file_service_key )
        
    
    if 'file_service_keys' in request.parsed_request_args:
        
        file_service_keys = request.parsed_request_args.GetValue( 'file_service_keys', list, expected_list_type = bytes )
        
        current_file_service_keys.update( file_service_keys )
        
    
    if deleted_allowed:
        
        if 'deleted_file_service_key' in request.parsed_request_args:
            
            file_service_key = request.parsed_request_args.GetValue( 'deleted_file_service_key', bytes )
            
            deleted_file_service_keys.add( file_service_key )
            
        
        if 'deleted_file_service_keys' in request.parsed_request_args:
            
            file_service_keys = request.parsed_request_args.GetValue( 'deleted_file_service_keys', list, expected_list_type = bytes )
            
            deleted_file_service_keys.update( file_service_keys )
            
        
    
    for service_key in current_file_service_keys:
        
        CheckFileService( service_key )
        
    
    for service_key in deleted_file_service_keys:
        
        CheckFileService( service_key )
        
    
    if len( current_file_service_keys ) > 0 or len( deleted_file_service_keys ) > 0:
        
        return ClientLocation.LocationContext( current_service_keys = current_file_service_keys, deleted_service_keys = deleted_file_service_keys )
        
    else:
        
        return default
        
    

def ParseHashes( request: HydrusServerRequest.HydrusRequest ):
    
    something_was_set = False
    
    hashes = []
    
    if 'hash' in request.parsed_request_args:
        
        something_was_set = True
        
        hash = request.parsed_request_args.GetValue( 'hash', bytes )
        
        hashes.append( hash )
        
    
    if 'hashes' in request.parsed_request_args:
        
        something_was_set = True
        
        more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
        
        hashes.extend( more_hashes )
        
    
    if 'file_id' in request.parsed_request_args:
        
        something_was_set = True
        
        hash_id = request.parsed_request_args.GetValue( 'file_id', int )
        
        hash_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = [ hash_id ] )
        
        if len( hash_ids_to_hashes ) > 0:
            
            hashes.extend( hash_ids_to_hashes[ hash_id ] )
            
        
    
    if 'file_ids' in request.parsed_request_args:
        
        something_was_set = True
        
        hash_ids = request.parsed_request_args.GetValue( 'file_ids', list, expected_list_type = int )
        
        hash_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = hash_ids )
        
        hashes.extend( [ hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] )
        
    
    if not something_was_set: # subtly different to 'no hashes'
        
        raise HydrusExceptions.BadRequestException( 'Please include some files in your request--file_id or hash based!' )
        
    
    hashes = HydrusData.DedupeList( hashes )
    
    CheckHashLength( hashes )
    
    return hashes
    

def ParseRequestedResponseMime( request: HydrusServerRequest.HydrusRequest ):
    
    # let them ask for something specifically, else default to what they asked in, finally default to json
    
    if request.requestHeaders.hasHeader( 'Accept' ):
        
        accepts = request.requestHeaders.getRawHeaders( 'Accept' )
        
        accept = accepts[0]
        
        if 'cbor' in accept and 'json' not in accept:
            
            return HC.APPLICATION_CBOR
            
        elif 'json' in accept and 'cbor' not in accept:
            
            return HC.APPLICATION_JSON
            
        
    
    if request.requestHeaders.hasHeader( 'Content-Type' ):
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        if 'cbor' in content_type:
            
            return HC.APPLICATION_CBOR
            
        elif 'json' in content_type:
            
            return HC.APPLICATION_JSON
            
        
        
    
    if b'cbor' in request.args:
        
        return HC.APPLICATION_CBOR
        
    
    return HC.APPLICATION_JSON
    

def ParseTagServiceKey( request: HydrusServerRequest.HydrusRequest ):
    
    if 'tag_service_key' in request.parsed_request_args:
        
        if 'tag_service_key' in request.parsed_request_args:
            
            tag_service_key = request.parsed_request_args[ 'tag_service_key' ]
            
        
        CheckTagService( tag_service_key )
        
    else:
        
        tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
        
    
    return tag_service_key
    

def ConvertTagListToPredicates( request, tag_list, do_permission_check = True, error_on_invalid_tag = True ) -> typing.List[ ClientSearch.Predicate ]:
    
    or_tag_lists = [ tag for tag in tag_list if isinstance( tag, list ) ]
    tag_strings = [ tag for tag in tag_list if isinstance( tag, str ) ]
    
    system_predicate_strings = [ tag for tag in tag_strings if tag.startswith( 'system:' ) ]
    tags = [ tag for tag in tag_strings if not tag.startswith( 'system:' ) ]
    
    negated_tags = [ tag for tag in tags if tag.startswith( '-' ) ]
    tags = [ tag for tag in tags if not tag.startswith( '-' ) ]
    
    dirty_negated_tags = negated_tags
    dirty_tags = tags
    
    negated_tags = HydrusTags.CleanTags( dirty_negated_tags )
    tags = HydrusTags.CleanTags( dirty_tags )
    
    if error_on_invalid_tag:
        
        jobs = [
            ( dirty_negated_tags, negated_tags ),
            ( dirty_tags, tags )
        ]
        
        for ( dirty_ts, ts ) in jobs:
            
            if len( ts ) != dirty_ts:
                
                for dirty_t in dirty_ts:
                    
                    try:
                        
                        clean_t = HydrusTags.CleanTag( dirty_t )
                        
                        HydrusTags.CheckTagNotEmpty( clean_t )
                        
                    except Exception as e:
                        
                        message = 'Could not understand the tag: "{}"'.format( dirty_t )
                        
                        raise HydrusExceptions.BadRequestException( message )
                        
                    
                
            
        
    
    if do_permission_check:
        
        raw_inclusive_tags = [ tag for tag in tags if '*' not in tags ]
        
        if len( raw_inclusive_tags ) == 0:
            
            if len( negated_tags ) > 0:
                
                try:
                    
                    request.client_api_permissions.CheckCanSeeAllFiles()
                    
                except HydrusExceptions.InsufficientCredentialsException:
                    
                    raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, if you want to search negated tags without regular tags, you need permission to search everything!' )
                    
                
            
            if len( system_predicate_strings ) > 0:
                
                try:
                    
                    request.client_api_permissions.CheckCanSeeAllFiles()
                    
                except HydrusExceptions.InsufficientCredentialsException:
                    
                    raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, if you want to search system predicates without regular tags, you need permission to search everything!' )
                    
                
            
            if len( or_tag_lists ) > 0:
                
                try:
                    
                    request.client_api_permissions.CheckCanSeeAllFiles()
                    
                except HydrusExceptions.InsufficientCredentialsException:
                    
                    raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, if you want to search OR predicates without regular tags, you need permission to search everything!' )
                    
                
            
        else:
            
            # check positive tags, not negative!
            request.client_api_permissions.CheckCanSearchTags( tags )
            
        
    
    predicates = []
    
    for or_tag_list in or_tag_lists:
        
        or_preds = ConvertTagListToPredicates( request, or_tag_list, do_permission_check = False )
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, or_preds ) )
        
    
    predicates.extend( ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( system_predicate_strings ) )
    
    search_tags = [ ( True, tag ) for tag in tags ]
    search_tags.extend( ( ( False, tag ) for tag in negated_tags ) )
    
    for ( inclusive, tag ) in search_tags:
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if '*' in tag:
            
            if subtag == '*':
                
                tag = namespace
                predicate_type = ClientSearch.PREDICATE_TYPE_NAMESPACE
                
            else:
                
                predicate_type = ClientSearch.PREDICATE_TYPE_WILDCARD
                
            
        else:
            
            predicate_type = ClientSearch.PREDICATE_TYPE_TAG
            
        
        predicates.append( ClientSearch.Predicate( predicate_type = predicate_type, value = tag, inclusive = inclusive ) )
        
    
    return predicates
    
class HydrusResourceBooru( HydrusServerResources.HydrusResource ):
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        parsed_request_args = ParseLocalBooruGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
    
    def _reportRequestUsed( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._service.ReportRequestUsed()
        
    
    def _checkService( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    
class HydrusResourceBooruFile( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        share_key = request.parsed_request_args[ 'share_key' ]
        hash = request.parsed_request_args[ 'hash' ]
        
        HG.client_controller.local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = HG.client_controller.local_booru_manager.GetMediaResult( share_key, hash )
        
        try:
            
            mime = media_result.GetMime()
            
            path = HG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that file!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
class HydrusResourceBooruGallery( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        # in future, make this a standard frame with a search key that'll load xml or yaml AJAX stuff
        # with file info included, so the page can sort and whatever
        
        share_key = request.parsed_request_args.GetValue( 'share_key', bytes )
        
        local_booru_manager = HG.client_controller.local_booru_manager
        
        local_booru_manager.CheckShareAuthorised( share_key )
        
        ( name, text, timeout, media_results ) = local_booru_manager.GetGalleryInfo( share_key )
        
        body = '''<html>
    <head>'''
        
        if name == '': body += '''
        <title>hydrus network local booru share</title>'''
        else: body += '''
        <title>''' + name + '''</title>'''
        
        body += '''
        
        <link href="hydrus.ico" rel="shortcut icon" />
        <link href="style.css" rel="stylesheet" type="text/css" />'''
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        body += '''
        <style>
            .thumbnail_container { width: ''' + str( thumbnail_width ) + '''px; height: ''' + str( thumbnail_height ) + '''px; }
        </style>'''
        
        body += '''
    </head>
    <body>'''
        
        body += '''
        <div class="timeout">This share ''' + HydrusData.ConvertTimestampToPrettyExpires( timeout ) + '''.</div>'''
        
        if name != '': body += '''
        <h3>''' + name + '''</h3>'''
        
        if text != '':
            
            newline = '''</p>
        <p>'''
            
            body += '''
        <p>''' + text.replace( os.linesep, newline ).replace( '\n', newline ) + '''</p>'''
        
        body+= '''
        <div class="media">'''
        
        for media_result in media_results:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            # if mime in flash or pdf or whatever, get other thumbnail
            
            body += '''
            <span class="thumbnail">
                <span class="thumbnail_container">
                    <a href="page?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''">
                        <img src="thumbnail?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''" />
                    </a>
                </span>
            </span>'''
            
        
        body += '''
        </div>
        <div class="footer"><a href="https://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceBooruPage( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        share_key = request.parsed_request_args.GetValue( 'share_key', bytes )
        hash = request.parsed_request_args.GetValue( 'hash', bytes )
        
        local_booru_manager = HG.client_controller.local_booru_manager
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        ( name, text, timeout, media_result ) = local_booru_manager.GetPageInfo( share_key, hash )
        
        body = '''<html>
    <head>'''
        
        if name == '': body += '''
        <title>hydrus network local booru share</title>'''
        else: body += '''
        <title>''' + name + '''</title>'''
        
        body += '''
        
        <link href="hydrus.ico" rel="shortcut icon" />
        <link href="style.css" rel="stylesheet" type="text/css" />'''
        
        body += '''
    </head>
    <body>'''
        
        body += '''
        <div class="timeout">This share ''' + HydrusData.ConvertTimestampToPrettyExpires( timeout ) + '''.</div>'''
        
        if name != '': body += '''
        <h3>''' + name + '''</h3>'''
        
        if text != '':
            
            newline = '''</p>
        <p>'''
            
            body += '''
        <p>''' + text.replace( os.linesep, newline ).replace( '\n', newline ) + '''</p>'''
        
        body+= '''
        <div class="media">'''
        
        mime = media_result.GetMime()
        
        if mime in HC.IMAGES or mime in HC.ANIMATIONS:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <img width="''' + str( width ) + '''" height="''' + str( height ) + '''" src="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''" />'''
            
        elif mime in HC.VIDEO:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <video width="''' + str( width ) + '''" height="''' + str( height ) + '''" controls="" loop="" autoplay="" src="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''" />
            <p><a href="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        elif mime == HC.APPLICATION_FLASH:
            
            ( width, height ) = media_result.GetResolution()
            
            body += '''
            <embed width="''' + str( width ) + '''" height="''' + str( height ) + '''" src="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''" />
            <p><a href="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        else:
            
            body += '''
            <p><a href="file?share_key=''' + share_key.hex() + '''&hash=''' + hash.hex() + '''">link to ''' + HC.mime_string_lookup[ mime ] + ''' file</a></p>'''
            
        
        body += '''
        </div>
        <div class="footer"><a href="https://hydrusnetwork.github.io/hydrus/">hydrus network</a></div>
    </body>
</html>'''
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.TEXT_HTML, body = body )
        
        return response_context
        
    
class HydrusResourceBooruThumbnail( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        share_key = request.parsed_request_args.GetValue( 'share_key', bytes )
        hash = request.parsed_request_args.GetValue( 'hash', bytes )
        
        local_booru_manager = HG.client_controller.local_booru_manager
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = local_booru_manager.GetMediaResult( share_key, hash )
        
        mime = media_result.GetMime()
        
        response_context_mime = HC.IMAGE_PNG
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetThumbnailPath( media_result )
            
            response_context_mime = HC.APPLICATION_UNKNOWN
            
            if not os.path.exists( path ):
                
                path = HydrusPaths.mimes_to_default_thumbnail_paths[ mime ]
                
            
        else:
            
            path = HydrusPaths.mimes_to_default_thumbnail_paths[ mime ]
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_context_mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPI( HydrusServerResources.HydrusResource ):
    
    BLOCKED_WHEN_BUSY = True
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        parsed_request_args = ParseClientAPIGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        requested_response_mime = ParseRequestedResponseMime( request )
        
        if requested_response_mime == HC.APPLICATION_CBOR and not CBOR_AVAILABLE:
            
            raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
            
        
        request.preferred_mime = requested_response_mime
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        ( parsed_request_args, total_bytes_read ) = ParseClientAPIPOSTArgs( request )
        
        self._reportDataUsed( request, total_bytes_read )
        
        request.parsed_request_args = parsed_request_args
        
        requested_response_mime = ParseRequestedResponseMime( request )
        
        if requested_response_mime == HC.APPLICATION_CBOR and not CBOR_AVAILABLE:
            
            raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
            
        
        request.preferred_mime = requested_response_mime
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
    
    def _reportRequestUsed( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._service.ReportRequestUsed()
        
        HG.client_controller.ResetIdleTimerFromClientAPI()
        
    
    def _checkService( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if self.BLOCKED_WHEN_BUSY and HG.client_busy.locked():
            
            raise HydrusExceptions.ServerBusyException( 'This server is busy, please try again later.' )
            
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    
class HydrusResourceClientAPIPermissionsRequest( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not ClientAPI.api_request_dialog_open:
            
            raise HydrusExceptions.ConflictException( 'The permission registration dialog is not open. Please open it under "review services" in the hydrus client.' )
            
        
        name = request.parsed_request_args.GetValue( 'name', str )
        
        basic_permissions = request.parsed_request_args.GetValue( 'basic_permissions', list, expected_list_type = int )
        
        basic_permissions = [ int( value ) for value in basic_permissions ]
        
        api_permissions = ClientAPI.APIPermissions( name = name, basic_permissions = basic_permissions )
        
        ClientAPI.last_api_permissions_request = api_permissions
        
        access_key = api_permissions.GetAccessKey()
        
        body_dict = {}
        
        body_dict[ 'access_key' ] = access_key.hex()
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIVersion( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        body_dict = {}
        
        body_dict[ 'version' ] = HC.CLIENT_API_VERSION
        body_dict[ 'hydrus_version' ] = HC.SOFTWARE_VERSION
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestricted( HydrusResourceClientAPI ):
    
    def _callbackCheckAccountRestrictions( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusResourceClientAPI._callbackCheckAccountRestrictions( self, request )
        
        self._CheckAPIPermissions( request )
        
        return request
        
    
    def _callbackEstablishAccountFromHeader( self, request: HydrusServerRequest.HydrusRequest ):
        
        access_key = self._ParseClientAPIAccessKey( request, 'header' )
        
        if access_key is not None:
            
            self._EstablishAPIPermissions( request, access_key )
            
        
        return request
        
    
    def _callbackEstablishAccountFromArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.client_api_permissions is None:
            
            access_key = self._ParseClientAPIAccessKey( request, 'args' )
            
            if access_key is not None:
                
                self._EstablishAPIPermissions( request, access_key )
                
            
        
        if request.client_api_permissions is None:
            
            raise HydrusExceptions.MissingCredentialsException( 'No access key or session key provided!' )
            
        
        return request
        
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        raise NotImplementedError()
        
    
    def _EstablishAPIPermissions( self, request, access_key ):
        
        try:
            
            api_permissions = HG.client_controller.client_api_manager.GetPermissions( access_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.InsufficientCredentialsException( str( e ) )
            
        
        request.client_api_permissions = api_permissions
        
    
    def _ParseClientAPIKey( self, request, source, name_of_key ):
        
        key = None
        
        if source == 'header':
            
            if request.requestHeaders.hasHeader( name_of_key ):
                
                key_texts = request.requestHeaders.getRawHeaders( name_of_key )
                
                key_text = key_texts[0]
                
                try:
                    
                    key = bytes.fromhex( key_text )
                    
                except:
                    
                    raise Exception( 'Problem parsing {}!'.format( name_of_key ) )
                    
                
            
        elif source == 'args':
            
            if name_of_key in request.parsed_request_args:
                
                key = request.parsed_request_args.GetValue( name_of_key, bytes )
                
            
        
        return key
        
    
    def _ParseClientAPIAccessKey( self, request, source ):
        
        access_key = self._ParseClientAPIKey( request, source, 'Hydrus-Client-API-Access-Key' )
        
        if access_key is None:
            
            session_key = self._ParseClientAPIKey( request, source, 'Hydrus-Client-API-Session-Key' )
            
            if session_key is None:
                
                return None
                
            
            try:
                
                access_key = HG.client_controller.client_api_manager.GetAccessKey( session_key )
                
            except HydrusExceptions.DataMissing as e:
                
                raise HydrusExceptions.SessionException( str( e ) )
                
            
        
        return access_key
        
    
class HydrusResourceClientAPIRestrictedAccount( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        pass
        
    
class HydrusResourceClientAPIRestrictedAccountSessionKey( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        new_session_key = HG.client_controller.client_api_manager.GenerateSessionKey( request.client_api_permissions.GetAccessKey() )
        
        body_dict = {}
        
        body_dict[ 'session_key' ] = new_session_key.hex()
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAccountVerify( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        api_permissions = request.client_api_permissions
        
        basic_permissions = api_permissions.GetBasicPermissions()
        human_description = api_permissions.ToHumanString()
        
        body_dict = {}
        
        body_dict[ 'basic_permissions' ] = list( basic_permissions ) # set->list for json
        body_dict[ 'human_description' ] = human_description
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetService( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        allowed_service_types = {
            HC.LOCAL_TAG,
            HC.TAG_REPOSITORY,
            HC.LOCAL_FILE_DOMAIN,
            HC.LOCAL_FILE_UPDATE_DOMAIN,
            HC.FILE_REPOSITORY,
            HC.COMBINED_LOCAL_FILE,
            HC.COMBINED_LOCAL_MEDIA,
            HC.COMBINED_FILE,
            HC.COMBINED_TAG,
            HC.LOCAL_FILE_TRASH_DOMAIN
        }
        
        if 'service_key' in request.parsed_request_args:
            
            service_key = request.parsed_request_args.GetValue( 'service_key', bytes )
            
        elif 'service_name' in request.parsed_request_args:
            
            service_name = request.parsed_request_args.GetValue( 'service_name', str )
            
            try:
                
                service_key = HG.client_controller.services_manager.GetServiceKeyFromName( allowed_service_types, service_name )
                
            except HydrusExceptions.DataMissing:
                
                raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with name "{}"!'.format( service_name ) )
                
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you need to give a service_key or service_name!' )
            
        
        try:
            
            service = HG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with key "{}"!'.format( service_key.hex() ) )
            
        
        if service.GetServiceType() not in allowed_service_types:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, for now, you cannot ask about this service!' )
            
        
        body_dict = {
            'service' : {
                'name' : service.GetName(),
                'type' : service.GetServiceType(),
                'type_pretty' : HC.service_string_lookup[ service.GetServiceType() ],
                'service_key' : service.GetServiceKey().hex()
            }
        }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetServices( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        jobs = [
            ( ( HC.LOCAL_TAG, ), 'local_tags' ),
            ( ( HC.TAG_REPOSITORY, ), 'tag_repositories' ),
            ( ( HC.LOCAL_FILE_DOMAIN, ), 'local_files' ),
            ( ( HC.LOCAL_FILE_UPDATE_DOMAIN, ), 'local_updates' ),
            ( ( HC.FILE_REPOSITORY, ), 'file_repositories' ),
            ( ( HC.COMBINED_LOCAL_FILE, ), 'all_local_files' ),
            ( ( HC.COMBINED_LOCAL_MEDIA, ), 'all_local_media' ),
            ( ( HC.COMBINED_FILE, ), 'all_known_files' ),
            ( ( HC.COMBINED_TAG, ), 'all_known_tags' ),
            ( ( HC.LOCAL_FILE_TRASH_DOMAIN, ), 'trash' )
        ]
        
        body_dict = {}
        
        for ( service_types, name ) in jobs:
            
            services = HG.client_controller.services_manager.GetServices( service_types )
            
            services_list = []
            
            for service in services:
                
                service_dict = {
                    'name' : service.GetName(),
                    'type' : service.GetServiceType(),
                    'type_pretty' : HC.service_string_lookup[ service.GetServiceType() ],
                    'service_key' : service.GetServiceKey().hex()
                }
                
                services_list.append( service_dict )
                
            
            body_dict[ name ] = services_list
            
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFiles( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_FILES )
        
    
class HydrusResourceClientAPIRestrictedAddFilesAddFile( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not hasattr( request, 'temp_file_info' ):
            
            path = request.parsed_request_args.GetValue( 'path', str )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" does not exist!'.format( path ) )
                
            
            ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            HydrusPaths.MirrorFile( path, temp_path )
            
        
        ( os_file_handle, temp_path ) = request.temp_file_info
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( FileImportOptions.IMPORT_TYPE_QUIET )
        
        file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options )
        
        try:
            
            file_import_status = file_import_job.DoWork()
            
        except:
            
            file_import_status = ClientImportFiles.FileImportStatus( CC.STATUS_ERROR, file_import_job.GetHash(), note = traceback.format_exc() )
            
        
        body_dict = {}
        
        body_dict[ 'status' ] = file_import_status.status
        body_dict[ 'hash' ] = HydrusData.BytesToNoneOrHex( file_import_status.hash )
        body_dict[ 'note' ] = file_import_status.note
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesArchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ParseHashes( request ) )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesDeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ), deleted_allowed = False )
        
        if 'reason' in request.parsed_request_args:
            
            reason = request.parsed_request_args.GetValue( 'reason', str )
            
        else:
            
            reason = 'Deleted via Client API.'
            
        
        hashes = set( ParseHashes( request ) )
        
        # expand this to take reason
        
        location_context.LimitToServiceTypes( HG.client_controller.services_manager.GetServiceType, ( HC.COMBINED_LOCAL_FILE, HC.COMBINED_LOCAL_MEDIA, HC.LOCAL_FILE_DOMAIN ) )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = reason )
        
        for service_key in location_context.current_service_keys:
            
            service_keys_to_content_updates = { service_key : [ content_update ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesUnarchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ParseHashes( request ) )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesUndeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
        
        hashes = set( ParseHashes( request ) )
        
        location_context.LimitToServiceTypes( HG.client_controller.services_manager.GetServiceType, ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_MEDIA ) )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes )
        
        for service_key in location_context.current_service_keys:
            
            service_keys_to_content_updates = { service_key : [ content_update ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddNotes( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES )
        
    
class HydrusResourceClientAPIRestrictedAddNotesSetNotes( HydrusResourceClientAPIRestrictedAddNotes ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
        elif 'file_id' in request.parsed_request_args:
            
            hash_id = request.parsed_request_args.GetValue( 'file_id', int )
            
            hash_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = [ hash_id ] )
            
            hash = hash_ids_to_hashes[ hash_id ]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'There was no file identifier or hash given!' )
            
        
        new_names_to_notes = request.parsed_request_args.GetValue( 'notes', dict, expected_dict_types = ( str, str ) )
        
        merge_cleverly = request.parsed_request_args.GetValue( 'merge_cleverly', bool, default_value = False )
        
        if merge_cleverly:
            
            from hydrus.client.importing.options import NoteImportOptions
            
            extend_existing_note_if_possible = request.parsed_request_args.GetValue( 'extend_existing_note_if_possible', bool, default_value = True )
            conflict_resolution = request.parsed_request_args.GetValue( 'conflict_resolution', int, default_value = NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
            
            if conflict_resolution not in NoteImportOptions.note_import_conflict_str_lookup:
                
                raise HydrusExceptions.BadRequestException( 'The given conflict resolution type was not in the allowed range!' )
                
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            
            note_import_options.SetIsDefault( False )
            note_import_options.SetExtendExistingNoteIfPossible( extend_existing_note_if_possible )
            note_import_options.SetConflictResolution( conflict_resolution )
            
            media_result = HG.client_controller.Read( 'media_result', hash )
            
            existing_names_to_notes = media_result.GetNotesManager().GetNamesToNotes()
            
            names_and_notes = list( new_names_to_notes.items() )
            
            new_names_to_notes = note_import_options.GetUpdateeNamesToNotes( existing_names_to_notes, names_and_notes )
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in new_names_to_notes.items() ]
        
        if len( content_updates ) > 0:
            
            service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        body_dict = {}
        
        body_dict[ 'notes' ] = new_names_to_notes
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddNotesDeleteNotes( HydrusResourceClientAPIRestrictedAddNotes ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
        
        elif 'file_id' in request.parsed_request_args:
            
            hash_id = request.parsed_request_args.GetValue( 'file_id', int )
            
            hash_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = [ hash_id ] )
            
            hash = hash_ids_to_hashes[ hash_id ]
        
        else:
            
            raise HydrusExceptions.BadRequestException( 'There was no file identifier or hash given!' )
        
        note_names = request.parsed_request_args.GetValue( 'note_names', list, expected_list_type = str )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in note_names ]
        
        service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
        
        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTags( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
        
    
class HydrusResourceClientAPIRestrictedAddTagsAddTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ParseHashes( request ) )
        
        #
        
        service_keys_to_tags = None
        
        service_keys_to_actions_to_tags = None
        
        if 'service_keys_to_tags' in request.parsed_request_args:
            
            service_keys_to_tags = request.parsed_request_args.GetValue( 'service_keys_to_tags', dict )
            
            service_keys_to_actions_to_tags = {}
            
            for ( service_key, tags ) in service_keys_to_tags.items():
                
                service = CheckTagService( service_key )
                
                HydrusNetworkVariableHandling.TestVariableType( 'tags in service_keys_to_tags', tags, list, expected_list_type = str )
                
                tags = HydrusTags.CleanTags( tags )
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                if service.GetServiceType() == HC.LOCAL_TAG:
                    
                    content_action = HC.CONTENT_UPDATE_ADD
                    
                else:
                    
                    content_action = HC.CONTENT_UPDATE_PEND
                    
                
                service_keys_to_actions_to_tags[ service_key ] = collections.defaultdict( set )
                
                service_keys_to_actions_to_tags[ service_key ][ content_action ].update( tags )
                
            
        
        if 'service_keys_to_actions_to_tags' in request.parsed_request_args:
            
            parsed_service_keys_to_actions_to_tags = request.parsed_request_args.GetValue( 'service_keys_to_actions_to_tags', dict )
            
            service_keys_to_actions_to_tags = {}
            
            for ( service_key, parsed_actions_to_tags ) in parsed_service_keys_to_actions_to_tags.items():
                
                service = CheckTagService( service_key )
                
                HydrusNetworkVariableHandling.TestVariableType( 'actions_to_tags', parsed_actions_to_tags, dict )
                
                actions_to_tags = {}
                
                for ( parsed_content_action, tags ) in parsed_actions_to_tags.items():
                    
                    HydrusNetworkVariableHandling.TestVariableType( 'action in actions_to_tags', parsed_content_action, str )
                    
                    try:
                        
                        content_action = int( parsed_content_action )
                        
                    except:
                        
                        raise HydrusExceptions.BadRequestException( 'Sorry, got an action, "{}", that was not an integer!'.format( parsed_content_action ) )
                        
                    
                    if service.GetServiceType() == HC.LOCAL_TAG:
                        
                        if content_action not in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            raise HydrusExceptions.BadRequestException( 'Sorry, you submitted a content action of "{}" for service "{}", but you can only add/delete on a local tag service!'.format( parsed_content_action, service_key.hex() ) )
                            
                        
                    else:
                        
                        if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            raise HydrusExceptions.BadRequestException( 'Sorry, you submitted a content action of "{}" for service "{}", but you cannot add/delete on a remote tag service!'.format( parsed_content_action, service_key.hex() ) )
                            
                        
                    
                    HydrusNetworkVariableHandling.TestVariableType( 'tags in actions_to_tags', tags, list ) # do not test for str here, it can be reason tuples!
                    
                    actions_to_tags[ content_action ] = tags
                    
                
                if len( actions_to_tags ) == 0:
                    
                    continue
                    
                
                service_keys_to_actions_to_tags[ service_key ] = actions_to_tags
                
            
        
        if service_keys_to_actions_to_tags is None:
            
            raise HydrusExceptions.BadRequestException( 'Need a service-names-to-tags parameter!' )
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        for ( service_key, actions_to_tags ) in service_keys_to_actions_to_tags.items():
            
            for ( content_action, tags ) in actions_to_tags.items():
                
                tags = list( tags )
                
                content_action = int( content_action )
                
                content_update_tags = []
                
                tags_to_reasons = {}
                
                for tag_item in tags:
                    
                    reason = 'Petitioned from API'
                    
                    if isinstance( tag_item, str ):
                        
                        tag = tag_item
                        
                    elif isinstance( tag_item, collections.abc.Collection ) and len( tag_item ) == 2:
                        
                        ( tag, reason ) = tag_item
                        
                        if not ( isinstance( tag, str ) and isinstance( reason, str ) ):
                            
                            continue
                            
                        
                    else:
                        
                        continue
                        
                    
                    try:
                        
                        tag = HydrusTags.CleanTag( tag )
                        
                    except:
                        
                        continue
                        
                    
                    content_update_tags.append( tag )
                    tags_to_reasons[ tag ] = reason
                    
                
                if len( content_update_tags ) == 0:
                    
                    continue
                    
                
                if content_action == HC.CONTENT_UPDATE_PETITION:
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ), reason = tags_to_reasons[ tag ] ) for tag in content_update_tags ]
                    
                else:
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ) ) for tag in content_update_tags ]
                    
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddTagsSearchTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
    def _GetParsedAutocompleteText( self, search, tag_service_key ) -> ClientSearch.ParsedAutocompleteText:
        
        tag_autocomplete_options = HG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
        
        collapse_search_characters = True
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( search, tag_autocomplete_options, collapse_search_characters )
        
        parsed_autocomplete_text.SetInclusive( True )
        
        return parsed_autocomplete_text
        
    
    def _GetTagMatches( self, request: HydrusServerRequest.HydrusRequest, tag_display_type: int, tag_service_key: bytes, parsed_autocomplete_text: ClientSearch.ParsedAutocompleteText ) -> typing.List[ ClientSearch.Predicate ]:
        
        matches = []
        
        if parsed_autocomplete_text.IsAcceptableForTagSearches():
            
            tag_context = ClientSearch.TagContext( service_key = tag_service_key )
            
            autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
            
            location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
            
            file_search_context = ClientSearch.FileSearchContext( location_context = location_context, tag_context = tag_context )
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            request.disconnect_callables.append( job_key.Cancel )
            
            search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
            
            predicates = HG.client_controller.Read( 'autocomplete_predicates', tag_display_type, file_search_context, search_text = autocomplete_search_text, job_key = job_key, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
            
            display_tag_service_key = tag_context.display_service_key
            
            matches = ClientSearch.FilterPredicatesBySearchText( display_tag_service_key, autocomplete_search_text, predicates )
            
            matches = ClientSearch.SortPredicates( matches )
            
        
        return matches
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        search = request.parsed_request_args.GetValue( 'search', str )
        
        tag_display_type_str = request.parsed_request_args.GetValue( 'tag_display_type', str, default_value = 'storage' )
        
        tag_display_type = ClientTags.TAG_DISPLAY_STORAGE if tag_display_type_str == 'storage' else ClientTags.TAG_DISPLAY_ACTUAL
        
        tag_service_key = ParseTagServiceKey( request )
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText( search, tag_service_key )
        
        matches = self._GetTagMatches( request, tag_display_type, tag_service_key, parsed_autocomplete_text )
        
        matches = request.client_api_permissions.FilterTagPredicateResponse( matches )
        
        body_dict = {}
        
        # TODO: Ok so we could add sibling/parent info here if the tag display type is storage, or in both cases. probably only if client asks for it
        
        tags = [ { 'value' : match.GetValue(), 'count' : match.GetCount().GetMinCount() } for match in matches ]
        
        body_dict[ 'tags' ] = tags
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTagsCleanTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tags = request.parsed_request_args.GetValue( 'tags', list, expected_list_type = str )
        
        tags = list( HydrusTags.CleanTags( tags ) )
        
        tags = HydrusTags.SortNumericTags( tags )
        
        body_dict = {}
        
        body_dict[ 'tags' ] = tags
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLs( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_URLS )
        
    
class HydrusResourceClientAPIRestrictedAddURLsAssociateURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        urls_to_add = []
        
        if 'url_to_add' in request.parsed_request_args:
            
            url = request.parsed_request_args.GetValue( 'url_to_add', str )
            
            urls_to_add.append( url )
            
        
        if 'urls_to_add' in request.parsed_request_args:
            
            urls = request.parsed_request_args.GetValue( 'urls_to_add', list, expected_list_type = str )
            
            urls_to_add.extend( urls )
            
        
        urls_to_delete = []
        
        if 'url_to_delete' in request.parsed_request_args:
            
            url = request.parsed_request_args.GetValue( 'url_to_delete', str )
            
            urls_to_delete.append( url )
            
        
        if 'urls_to_delete' in request.parsed_request_args:
            
            urls = request.parsed_request_args.GetValue( 'urls_to_delete', list, expected_list_type = str )
            
            for url in urls:
                
                urls_to_delete.extend( urls )
                
            
        
        domain_manager = HG.client_controller.network_engine.domain_manager
        
        try:
            
            urls_to_add = [ domain_manager.NormaliseURL( url ) for url in urls_to_add ]
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        if len( urls_to_add ) == 0 and len( urls_to_delete ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any URLs to add or delete!' )
            
        
        applicable_hashes = set( ParseHashes( request ) )
        
        if len( applicable_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the urls to!' )
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        if len( urls_to_add ) > 0:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( urls_to_add, applicable_hashes ) )
            
            service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
            
        
        if len( urls_to_delete ) > 0:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( urls_to_delete, applicable_hashes ) )
            
            service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ].append( content_update )
            
        
        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsGetURLFiles( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        url = request.parsed_request_args.GetValue( 'url', str )
        
        do_file_system_check = request.parsed_request_args.GetValue( 'doublecheck_file_system', bool, default_value = False )
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        url_statuses = HG.client_controller.Read( 'url_statuses', normalised_url )
        
        json_happy_url_statuses = []
        
        for file_import_status in url_statuses:
            
            if do_file_system_check:
                
                file_import_status = ClientImportFiles.CheckFileImportStatus( file_import_status )
                
            
            d = {}
            
            d[ 'status' ] = file_import_status.status
            d[ 'hash' ] = HydrusData.BytesToNoneOrHex( file_import_status.hash )
            d[ 'note' ] = file_import_status.note
            
            json_happy_url_statuses.append( d )
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_file_statuses' : json_happy_url_statuses }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsGetURLInfo( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        url = request.parsed_request_args.GetValue( 'url', str )
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
        
        if not can_parse:
            
            body_dict[ 'cannot_parse_reason' ] = cannot_parse_reason
            
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsImportURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        url = request.parsed_request_args.GetValue( 'url', str )
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        filterable_tags = set()
        
        if 'filterable_tags' in request.parsed_request_args:
            
            request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
            
            filterable_tags = request.parsed_request_args.GetValue( 'filterable_tags', list, expected_list_type = str )
            
            filterable_tags = HydrusTags.CleanTags( filterable_tags )
            
        
        additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        if 'service_keys_to_additional_tags' in request.parsed_request_args:
            
            service_keys_to_additional_tags = request.parsed_request_args.GetValue( 'service_keys_to_additional_tags', dict )
            
            request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
            
            for ( service_key, tags ) in service_keys_to_additional_tags.items():
                
                CheckTagService( service_key )
                
                tags = HydrusTags.CleanTags( tags )
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                additional_service_keys_to_tags[ service_key ] = tags
                
            
        
        destination_page_name = None
        
        if 'destination_page_name' in request.parsed_request_args:
            
            destination_page_name = request.parsed_request_args.GetValue( 'destination_page_name', str )
            
        
        destination_page_key = None
        
        if 'destination_page_key' in request.parsed_request_args:
            
            destination_page_key = request.parsed_request_args.GetValue( 'destination_page_key', bytes )
            
        
        show_destination_page = request.parsed_request_args.GetValue( 'show_destination_page', bool, default_value = False )
        
        def do_it():
            
            return HG.client_controller.gui.ImportURLFromAPI( url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page )
            
        
        try:
            
            ( normalised_url, result_text ) = HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        time.sleep( 0.05 ) # yield and give the ui time to catch up with new URL pubsubs in case this is being spammed
        
        body_dict = { 'human_result_text' : result_text, 'normalised_url' : normalised_url }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFiles( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
class HydrusResourceClientAPIRestrictedGetFilesSearchFiles( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
        
        tag_service_key = ParseTagServiceKey( request )
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and location_context.IsAllKnownFiles():
            
            raise HydrusExceptions.BadRequestException( 'Sorry, search for all known tags over all known files is not supported!' )
            
        
        tag_context = ClientSearch.TagContext( service_key = tag_service_key )
        predicates = ParseClientAPISearchPredicates( request )
        
        return_hashes = False
        return_file_ids = True
        
        if len( predicates ) == 0:
            
            hash_ids = []
            
        else:
            
            file_search_context = ClientSearch.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
            
            file_sort_type = CC.SORT_FILES_BY_IMPORT_TIME
            
            if 'file_sort_type' in request.parsed_request_args:
                
                file_sort_type = request.parsed_request_args[ 'file_sort_type' ]
                
            
            if file_sort_type not in CC.SYSTEM_SORT_TYPES:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, did not understand that sort type!' )
                
            
            file_sort_asc = False
            
            if 'file_sort_asc' in request.parsed_request_args:
                
                file_sort_asc = request.parsed_request_args.GetValue( 'file_sort_asc', bool )
                
            
            sort_order = CC.SORT_ASC if file_sort_asc else CC.SORT_DESC
            
            # newest first
            sort_by = ClientMedia.MediaSort( sort_type = ( 'system', file_sort_type ), sort_order = sort_order )
            
            if 'return_hashes' in request.parsed_request_args:
                
                return_hashes = request.parsed_request_args.GetValue( 'return_hashes', bool )
                
            
            if 'return_file_ids' in request.parsed_request_args:
                
                return_file_ids = request.parsed_request_args.GetValue( 'return_file_ids', bool )
                
            
            job_key = ClientThreading.JobKey( cancellable = True )
            
            request.disconnect_callables.append( job_key.Cancel )
            
            hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context, job_key = job_key, sort_by = sort_by, apply_implicit_limit = False )
            
        
        request.client_api_permissions.SetLastSearchResults( hash_ids )
        
        body_dict = {}
        
        if return_hashes:
            
            hash_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = hash_ids )
            
            # maintain sort
            body_dict[ 'hashes' ] = [ hash_ids_to_hashes[ hash_id ].hex() for hash_id in hash_ids ]
            
        
        if return_file_ids:
            
            body_dict[ 'file_ids' ] = list( hash_ids )
            
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesGetFile( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        try:
            
            if 'file_id' in request.parsed_request_args:
                
                file_id = request.parsed_request_args.GetValue( 'file_id', int )
                
                request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
                
                ( media_result, ) = HG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
                
            elif 'hash' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hash = request.parsed_request_args.GetValue( 'hash', bytes )
                
                media_result = HG.client_controller.Read( 'media_result', hash )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
        try:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            path = HG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.FileMissingException()
                
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that file!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesFileHashes( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        supported_hash_types = ( 'sha256', 'md5', 'sha1', 'sha512' )
        
        source_hash_type = request.parsed_request_args.GetValue( 'source_hash_type', str, default_value = 'sha256' )
        
        if source_hash_type not in supported_hash_types:
            
            raise HydrusExceptions.BadRequestException( 'I do not support that hash type!' )
            
        
        desired_hash_type = request.parsed_request_args.GetValue( 'desired_hash_type', str )
        
        if desired_hash_type not in supported_hash_types:
            
            raise HydrusExceptions.BadRequestException( 'I do not support that hash type!' )
            
        
        source_hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            request_hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            source_hashes.add( request_hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            request_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            source_hashes.update( request_hashes )
            
        
        if len( source_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'You have to specify a hash to look up!' )
            
        
        CheckHashLength( source_hashes, hash_type = source_hash_type )
        
        source_to_desired = HG.client_controller.Read( 'file_hashes', source_hashes, source_hash_type, desired_hash_type )
        
        encoded_source_to_desired = { source_hash.hex() : desired_hash.hex() for ( source_hash, desired_hash ) in source_to_desired.items() }
        
        body_dict = {
            'hashes' : encoded_source_to_desired
        }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesFileMetadata( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        only_return_identifiers = request.parsed_request_args.GetValue( 'only_return_identifiers', bool, default_value = False )
        only_return_basic_information = request.parsed_request_args.GetValue( 'only_return_basic_information', bool, default_value = False )
        hide_service_keys_tags = request.parsed_request_args.GetValue( 'hide_service_keys_tags', bool, default_value = True )
        detailed_url_information = request.parsed_request_args.GetValue( 'detailed_url_information', bool, default_value = False )
        include_notes = request.parsed_request_args.GetValue( 'include_notes', bool, default_value = False )
        create_new_file_ids = request.parsed_request_args.GetValue( 'create_new_file_ids', bool, default_value = False )
        
        hashes = ParseHashes( request )
        
        file_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hashes = hashes, create_new_hash_ids = create_new_file_ids )
        
        missing_hashes = set( hashes ).difference( file_ids_to_hashes.values() )
        
        file_ids = set( file_ids_to_hashes.keys() )
        
        request.client_api_permissions.CheckPermissionToSeeFiles( file_ids )
        
        body_dict = {}
        
        metadata = []
        
        for hash in missing_hashes:
            
            metadata_row = {
                'file_id' : None,
                'hash' : hash.hex()
            }
            
            metadata.append( metadata_row )
            
        
        if only_return_identifiers:
            
            for ( file_id, hash ) in file_ids_to_hashes.items():
                
                metadata_row = {
                    'file_id' : file_id,
                    'hash' : hash.hex()
                }
                
                metadata.append( metadata_row )
                
            
        elif only_return_basic_information:
            
            file_info_managers = HG.client_controller.Read( 'file_info_managers_from_ids', file_ids, sorted = True )
            
            for file_info_manager in file_info_managers:
                
                metadata_row = {
                    'file_id' : file_info_manager.hash_id,
                    'hash' : file_info_manager.hash.hex(),
                    'size' : file_info_manager.size,
                    'mime' : HC.mime_mimetype_string_lookup[ file_info_manager.mime ],
                    'ext' : HC.mime_ext_lookup[ file_info_manager.mime ],
                    'width' : file_info_manager.width,
                    'height' : file_info_manager.height,
                    'duration' : file_info_manager.duration,
                    'num_frames' : file_info_manager.num_frames,
                    'num_words' : file_info_manager.num_words,
                    'has_audio' : file_info_manager.has_audio
                }
                
                metadata.append( metadata_row )
                
            
        else:
            
            media_results = HG.client_controller.Read( 'media_results_from_ids', file_ids, sorted = True )
            
            services_manager = HG.client_controller.services_manager
            
            tag_service_keys = services_manager.GetServiceKeys( HC.ALL_TAG_SERVICES )
            service_keys_to_types = { service.GetServiceKey() : service.GetServiceType() for service in services_manager.GetServices() }
            service_keys_to_names = services_manager.GetServiceKeysToNames()
            
            ipfs_service_keys = services_manager.GetServiceKeys( ( HC.IPFS, ) )
            
            thumbnail_bounding_dimensions = HG.client_controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = HG.client_controller.new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = HG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            for media_result in media_results:
                
                file_info_manager = media_result.GetFileInfoManager()
                
                mime = file_info_manager.mime
                width = file_info_manager.width
                height = file_info_manager.height
                
                metadata_row = {
                    'file_id' : file_info_manager.hash_id,
                    'hash' : file_info_manager.hash.hex(),
                    'size' : file_info_manager.size,
                    'mime' : HC.mime_mimetype_string_lookup[ mime ],
                    'ext' : HC.mime_ext_lookup[ mime ],
                    'width' : width,
                    'height' : height,
                    'duration' : file_info_manager.duration,
                    'num_frames' : file_info_manager.num_frames,
                    'num_words' : file_info_manager.num_words,
                    'has_audio' : file_info_manager.has_audio
                }
                
                if file_info_manager.mime in HC.MIMES_WITH_THUMBNAILS:
                    
                    if width is not None and height is not None and width > 0 and height > 0:
                        
                        ( clip_rect, ( expected_thumbnail_width, expected_thumbnail_height ) ) = HydrusImageHandling.GetThumbnailResolutionAndClipRegion( ( width, height ), thumbnail_bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                        
                        metadata_row[ 'thumbnail_width' ] = expected_thumbnail_width
                        metadata_row[ 'thumbnail_height' ] = expected_thumbnail_height
                        
                    
                
                if include_notes:
                    
                    metadata_row[ 'notes' ] = media_result.GetNotesManager().GetNamesToNotes()
                
                locations_manager = media_result.GetLocationsManager()
                
                metadata_row[ 'file_services' ] = {
                    'current' : {},
                    'deleted' : {}
                }
                
                current = locations_manager.GetCurrent()
                
                for file_service_key in current:
                    
                    timestamp = locations_manager.GetCurrentTimestamp( file_service_key )
                    
                    metadata_row[ 'file_services' ][ 'current' ][ file_service_key.hex() ] = {
                        'name' : service_keys_to_names[ file_service_key ],
                        'type' : service_keys_to_types[ file_service_key ],
                        'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                        'time_imported' : timestamp
                    }
                    
                
                deleted = locations_manager.GetDeleted()
                
                for file_service_key in deleted:
                    
                    ( timestamp, original_timestamp ) = locations_manager.GetDeletedTimestamps( file_service_key )
                    
                    metadata_row[ 'file_services' ][ 'deleted' ][ file_service_key.hex() ] = {
                        'name' : service_keys_to_names[ file_service_key ],
                        'type' : service_keys_to_types[ file_service_key ],
                        'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ file_service_key ] ],
                        'time_deleted' : timestamp,
                        'time_imported' : original_timestamp
                    }
                    
                
                timestamp_manager = locations_manager.GetTimestampManager()
                
                metadata_row[ 'time_modified' ] = timestamp_manager.GetAggregateModifiedTimestamp()
                
                time_modified_details = timestamp_manager.GetDomainModifiedTimestamps()
                
                local_modified = timestamp_manager.GetFileModifiedTimestamp()
                
                if local_modified is not None:
                    
                    time_modified_details[ 'local' ] = local_modified
                    
                
                metadata_row[ 'time_modified_details' ] = time_modified_details
                
                metadata_row[ 'is_inbox' ] = locations_manager.inbox
                metadata_row[ 'is_local' ] = locations_manager.IsLocal()
                metadata_row[ 'is_trashed' ] = locations_manager.IsTrashed()
                metadata_row[ 'is_deleted' ] = CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY in locations_manager.GetDeleted() or locations_manager.IsTrashed()
                
                metadata_row[ 'has_exif' ] = file_info_manager.has_exif
                metadata_row[ 'has_human_readable_embedded_metadata' ] = file_info_manager.has_human_readable_embedded_metadata
                metadata_row[ 'has_icc_profile' ] = file_info_manager.has_icc_profile
                
                known_urls = sorted( locations_manager.GetURLs() )
                
                metadata_row[ 'known_urls' ] = known_urls
                
                metadata_row[ 'ipfs_multihashes' ] = { ipfs_service_key.hex() : multihash for ( ipfs_service_key, multihash ) in locations_manager.GetServiceFilenames().items() if ipfs_service_key in ipfs_service_keys }
                
                if detailed_url_information:
                    
                    detailed_known_urls = []
                    
                    for known_url in known_urls:
                        
                        try:
                            
                            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( known_url )
                            
                            ( url_type, match_name, can_parse, cannot_parse_reason ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
                            
                        except HydrusExceptions.URLClassException as e:
                            
                            continue
                            
                        
                        detailed_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
                        
                        if not can_parse:
                            
                            detailed_dict[ 'cannot_parse_reason' ] = cannot_parse_reason
                            
                        
                        detailed_known_urls.append( detailed_dict )
                        
                    
                    metadata_row[ 'detailed_known_urls' ] = detailed_known_urls
                    
                
                tags_manager = media_result.GetTagsManager()
                
                tags_dict = {}
                
                for tag_service_key in tag_service_keys:
                    
                    storage_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    storage_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in storage_statuses_to_tags.items() if len( tags ) > 0 }
                    
                    display_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_ACTUAL )
                    
                    display_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in display_statuses_to_tags.items() if len( tags ) > 0 }
                    
                    tags_dict_object = {
                        'name' : service_keys_to_names[ tag_service_key ],
                        'type' : service_keys_to_types[ tag_service_key ],
                        'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ tag_service_key ] ],
                        'storage_tags' : storage_tags_json_serialisable,
                        'display_tags' : display_tags_json_serialisable
                    }
                    
                    tags_dict[ tag_service_key.hex() ] = tags_dict_object
                    
                
                metadata_row[ 'tags' ] = tags_dict
                
                # Old stuff starts here
                
                api_service_keys_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( statuses_to_tags_json_serialisable ) > 0:
                        
                        api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                        
                    
                
                if not hide_service_keys_tags:
                    
                    metadata_row[ 'service_keys_to_statuses_to_tags' ] = api_service_keys_to_statuses_to_tags
                    
                
                #
                
                api_service_keys_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_ACTUAL )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( statuses_to_tags_json_serialisable ) > 0:
                        
                        api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                        
                    
                
                if not hide_service_keys_tags:
                    
                    metadata_row[ 'service_keys_to_statuses_to_display_tags' ] = api_service_keys_to_statuses_to_tags
                    
                
                # old stuff ends here
                
                #
                
                metadata.append( metadata_row )
                
            
        
        body_dict[ 'metadata' ] = metadata
        
        mime = request.preferred_mime
        body = Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetFilesGetThumbnail( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        try:
            
            if 'file_id' in request.parsed_request_args:
                
                file_id = request.parsed_request_args.GetValue( 'file_id', int )
                
                request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
                
                ( media_result, ) = HG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
                
            elif 'hash' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hash = request.parsed_request_args.GetValue( 'hash', bytes )
                
                media_result = HG.client_controller.Read( 'media_result', hash )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
        try:
            
            path = HG.client_controller.client_files_manager.GetThumbnailPath( media_result )
            
            if not os.path.exists( path ):
                
                # not _supposed_ to happen, but it seems in odd situations it can
                raise HydrusExceptions.FileMissingException()
                
            
        except HydrusExceptions.FileMissingException:
            
            path = HydrusPaths.mimes_to_default_thumbnail_paths[ media_result.GetMime() ]
            
        
        mime = HydrusFileHandling.GetThumbnailMime( path )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageCookies( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_HEADERS )
        
    

class HydrusResourceClientAPIRestrictedManageCookiesGetCookies( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        domain = request.parsed_request_args.GetValue( 'domain', str )
        
        if '.' not in domain:
            
            raise HydrusExceptions.BadRequestException( 'The value "{}" does not seem to be a domain!'.format( domain ) )
            
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
        session = HG.client_controller.network_engine.session_manager.GetSession( network_context )
        
        body_cookies_list = []
        
        for cookie in session.cookies:
            
            name = cookie.name
            value = cookie.value
            domain = cookie.domain
            path = cookie.path
            expires = cookie.expires
            
            body_cookies_list.append( [ name, value, domain, path, expires ] )
            
        
        body_dict = {}
        
        body_dict = { 'cookies' : body_cookies_list }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageCookiesSetCookies( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        cookie_rows = request.parsed_request_args.GetValue( 'cookies', list )
        
        domains_cleared = set()
        domains_set = set()
        
        # TODO: This all sucks. replace the rows in this and the _set_ with an Object, and the domains_cleared/set stuff should say more, like count removed from each etc...
        # refer to get/set_headers for example
        
        for cookie_row in cookie_rows:
            
            if len( cookie_row ) != 5:
                
                raise HydrusExceptions.BadRequestException( 'The cookie "{}" did not come in the format [ name, value, domain, path, expires ]!'.format( cookie_row ) )
                
            
            ( name, value, domain, path, expires ) = cookie_row
            
            ndp_bad = True in ( not isinstance( var, str ) for var in ( name, domain, path ) )
            v_bad = value is not None and not isinstance( value, str )
            e_bad = expires is not None and not isinstance( expires, int )
            
            if ndp_bad or v_bad or e_bad:
                
                raise HydrusExceptions.BadRequestException( 'In the row [ name, value, domain, path, expires ], which I received as "{}", name, domain, and path need to be strings, value needs to be null or a string, and expires needs to be null or an integer!'.format( cookie_row ) )
                
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
            
            session = HG.client_controller.network_engine.session_manager.GetSession( network_context )
            
            if value is None:
                
                domains_cleared.add( domain )
                
                session.cookies.clear( domain, path, name )
                
            else:
                
                domains_set.add( domain )
                
                ClientNetworkingFunctions.AddCookieToSession( session, name, value, domain, path, expires )
                
            
            HG.client_controller.network_engine.session_manager.SetSessionDirty( network_context )
            
        
        if HG.client_controller.new_options.GetBoolean( 'notify_client_api_cookies' ) and len( domains_cleared ) + len( domains_set ) > 0:
            
            domains_cleared = sorted( domains_cleared )
            domains_set = sorted( domains_set )
            
            message = 'Cookies sent from API:'
            
            if len( domains_cleared ) > 0:
                
                message = '{} ({} cleared)'.format( message, ', '.join( domains_cleared ) )
                
            
            if len( domains_set ) > 0:
                
                message = '{} ({} set)'.format( message, ', '.join( domains_set ) )
                
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetStatusText( message )
            
            job_key.Delete( 5 )
            
            HG.client_controller.pub( 'message', job_key )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageCookiesSetUserAgent( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        user_agent = request.parsed_request_args.GetValue( 'user-agent', str )
        
        if user_agent == '':
            
            from hydrus.client import ClientDefaults
            
            user_agent = ClientDefaults.DEFAULT_USER_AGENT
            
        
        HG.client_controller.network_engine.domain_manager.SetCustomHeader( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, 'User-Agent', value = user_agent )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

def GenerateNetworkContextFromRequest( request: HydrusServerRequest.Request ):
    
    domain = request.parsed_request_args.GetValueOrNone( 'domain', str )
    
    if domain is None:
        
        network_context = ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT
        
    else:
        
        if '.' not in domain:
            
            raise HydrusExceptions.BadRequestException( 'The value "{}" does not seem to be a domain!'.format( domain ) )
            
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
    
    return network_context
    

def RenderNetworkContextToJSONObject( network_context: ClientNetworkingContexts.NetworkContext ) -> dict:
    
    result = {}
    
    result[ 'type' ] = network_context.context_type
    
    if isinstance( network_context.context_data, bytes ):
        
        result[ 'data' ] = network_context.context_data.hex()
        
    elif isinstance( network_context.context_data, str ) or network_context.context_data is None:
        
        result[ 'data' ] = network_context.context_data
        
    else:
        
        result[ 'data' ] = repr( network_context.context_data )
        
    
    return result
    

class HydrusResourceClientAPIRestrictedManageCookiesGetHeaders( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        network_context = GenerateNetworkContextFromRequest( request )
        
        ncs_to_header_dicts = HG.client_controller.network_engine.domain_manager.GetNetworkContextsToCustomHeaderDicts()
        
        body_dict = {}
        
        body_dict[ 'network_context' ] = RenderNetworkContextToJSONObject( network_context )
        
        headers_dict = ncs_to_header_dicts.get( network_context, {} )
        
        body_headers_dict = {}
        
        for ( key, ( value, approved, reason ) ) in headers_dict.items():
            
            body_headers_dict[ key ] = {
                'value' : value,
                'approved' : ClientNetworkingDomain.valid_str_lookup[ approved ],
                'reason' : reason
            }
            
        
        body_dict[ 'headers' ] = body_headers_dict
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageCookiesSetHeaders( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        network_context = GenerateNetworkContextFromRequest( request )
        http_header_objects = request.parsed_request_args.GetValue( 'headers', dict )
        
        headers_cleared = set()
        headers_set = set()
        headers_altered = set()
        
        for ( key, info_dict ) in http_header_objects.items():
            
            ncs_to_header_dicts = HG.client_controller.network_engine.domain_manager.GetNetworkContextsToCustomHeaderDicts()
            
            if network_context in ncs_to_header_dicts:
                
                headers_dict = ncs_to_header_dicts[ network_context ]
                
            else:
                
                headers_dict = {}
                
            
            approved = None
            reason = None
            
            if 'approved' in info_dict:
                
                approved_str = info_dict[ 'approved' ]
                
                approved = ClientNetworkingDomain.valid_enum_lookup.get( approved_str, None )
                
                if approved is None:
                    
                    raise HydrusExceptions.BadRequestException( 'The value "{}" was not in the permitted list!'.format( approved_str ) )
                    
                
            
            if 'reason' in info_dict:
                
                reason = info_dict[ 'reason' ]
                
                if not isinstance( reason, str ):
                    
                    raise HydrusExceptions.BadRequestException( 'The reason "{}" was not a string!'.format( reason ) )
                    
                
            
            if 'value' in info_dict:
                
                value = info_dict[ 'value' ]
                
                if value is None:
                    
                    if key in headers_dict:
                        
                        HG.client_controller.network_engine.domain_manager.DeleteCustomHeader( network_context, key )
                        
                        headers_cleared.add( key )
                        
                    
                else:
                    
                    if not isinstance( value, str ):
                        
                        raise HydrusExceptions.BadRequestException( 'The value "{}" was not a string!'.format( value ) )
                        
                    
                    do_it = True
                    
                    if key in headers_dict:
                        
                        old_value = headers_dict[ key ][0]
                        
                        if old_value == value:
                            
                            do_it = False
                            
                        else:
                            
                            headers_altered.add( key )
                            
                        
                    else:
                        
                        headers_set.add( key )
                        
                    
                    if do_it:
                        
                        HG.client_controller.network_engine.domain_manager.SetCustomHeader( network_context, key, value = value, approved = approved, reason = reason )
                        
                    
                
            else:
                
                if approved is None and reason is None:
                    
                    raise HydrusExceptions.BadRequestException( 'Sorry, you have to set a value, approved, or reason parameter!' )
                    
                
                if key not in headers_dict:
                    
                    raise HydrusExceptions.BadRequestException( 'Sorry, you tried to set approved/reason on "{}" for "{}", but that entry does not exist, so there is no value to set them to! Please give a value!'.format( key, network_context ) )
                    
                
                headers_altered.add( key )
                
                HG.client_controller.network_engine.domain_manager.SetCustomHeader( network_context, key, approved = approved, reason = reason )
                
            
        
        if HG.client_controller.new_options.GetBoolean( 'notify_client_api_cookies' ) and len( headers_cleared ) + len( headers_set ) + len( headers_altered ) > 0:
            
            message_lines = [ 'Headers sent from API:' ]
            
            if len( headers_cleared ) > 0:
                
                message_lines.extend( [ 'Cleared: {}'.format( key ) for key in sorted( headers_cleared ) ] )
                
            
            if len( headers_set ) > 0:
                
                message_lines.extend( [ 'Set: {}'.format( key ) for key in sorted( headers_set ) ] )
                
            
            if len( headers_set ) > 0:
                
                message_lines.extend( [ 'Altered: {}'.format( key ) for key in sorted( headers_altered ) ] )
                
            
            message = os.linesep.join( message_lines )
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetStatusText( message )
            
            job_key.Delete( 5 )
            
            HG.client_controller.pub( 'message', job_key )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageDatabase( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_DATABASE )
        
    
class HydrusResourceClientAPIRestrictedManageDatabaseLockOff( HydrusResourceClientAPIRestrictedManageDatabase ):
    
    BLOCKED_WHEN_BUSY = False
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        try:
            
            HG.client_busy.release()
            
        except threading.ThreadError:
            
            raise HydrusExceptions.BadRequestException( 'The server is not busy!' )
            
        
        HG.client_controller.db.PauseAndDisconnect( False )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManageDatabaseLockOn( HydrusResourceClientAPIRestrictedManageDatabase ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        locked = HG.client_busy.acquire( False ) # pylint: disable=E1111
        
        if not locked:
            
            raise HydrusExceptions.BadRequestException( 'The client was already locked!' )
            
        
        HG.client_controller.db.PauseAndDisconnect( True )
        
        TIME_BLOCK = 0.25
        
        for i in range( int( 5 / TIME_BLOCK ) ):
            
            if not HG.client_controller.db.IsConnected():
                
                break
                
            
            time.sleep( TIME_BLOCK )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManageDatabaseMrBones( HydrusResourceClientAPIRestrictedManageDatabase ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        boned_stats = HG.client_controller.Read( 'boned_stats' )
        
        body_dict = { 'boned_stats' : boned_stats }
        
        mime = request.preferred_mime
        body = Dumps( body_dict, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationships( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS )
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsGetRelationships( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
        
        hashes = ParseHashes( request )
        
        # maybe in future we'll just get the media results and dump the dict from there, but whatever
        hashes_to_file_duplicates = HG.client_controller.Read( 'file_relationships_for_api', location_context, hashes )
        
        body_dict = { 'file_relationships' : hashes_to_file_duplicates }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsGetPotentialsCount( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        (
            file_search_context_1,
            file_search_context_2,
            dupe_search_type,
            pixel_dupes_preference,
            max_hamming_distance
        ) = ParseDuplicateSearch( request )
        
        count = HG.client_controller.Read( 'potential_duplicates_count', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
        body_dict = { 'potential_duplicates_count' : count }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsGetPotentialPairs( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        (
            file_search_context_1,
            file_search_context_2,
            dupe_search_type,
            pixel_dupes_preference,
            max_hamming_distance
        ) = ParseDuplicateSearch( request )
        
        max_num_pairs = request.parsed_request_args.GetValue( 'max_num_pairs', int, default_value = HG.client_controller.new_options.GetInteger( 'duplicate_filter_max_batch_size' ) )
        
        filtering_pairs_media_results = HG.client_controller.Read( 'duplicate_pairs_for_filtering', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance, max_num_pairs = max_num_pairs )
        
        filtering_pairs_hashes = [ ( m1.GetHash().hex(), m2.GetHash().hex() ) for ( m1, m2 ) in filtering_pairs_media_results ]
        
        body_dict = { 'potential_duplicate_pairs' : filtering_pairs_hashes }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsGetRandomPotentials( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        (
            file_search_context_1,
            file_search_context_2,
            dupe_search_type,
            pixel_dupes_preference,
            max_hamming_distance
        ) = ParseDuplicateSearch( request )
        
        hashes = HG.client_controller.Read( 'random_potential_duplicate_hashes', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
        body_dict = { 'random_potential_duplicate_hashes' : [ hash.hex() for hash in hashes ] }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsSetKings( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = ParseHashes( request )
        
        for hash in hashes:
            
            HG.client_controller.WriteSynchronous( 'duplicate_set_king', hash )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFileRelationshipsSetRelationships( HydrusResourceClientAPIRestrictedManageFileRelationships ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        database_write_rows = []
        
        raw_rows = []
        
        all_hashes = set()
        
        pair_rows_old_arg_raw_rows = request.parsed_request_args.GetValue( 'pair_rows', list, expected_list_type = list, default_value = [] )
        
        for row in pair_rows_old_arg_raw_rows:
            
            if len( row ) != 6:
                
                raise HydrusExceptions.BadRequestException( 'One of the pair rows was the wrong length!' )
                
            
            raw_rows.append( row )
            
        
        raw_relationship_dicts = request.parsed_request_args.GetValue( 'relationships', list, expected_list_type = dict, default_value = [] )
        
        for raw_relationship_dict in raw_relationship_dicts:
            
            duplicate_type = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'relationship', int )
            hash_a_hex = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'hash_a', str )
            hash_b_hex = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'hash_b', str )
            do_default_content_merge = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'do_default_content_merge', bool )
            delete_a = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'delete_a', bool, default_value = False )
            delete_b = HydrusNetworkVariableHandling.GetValueFromDict( raw_relationship_dict, 'delete_b', bool, default_value = False )
            
            raw_rows.append( ( duplicate_type, hash_a_hex, hash_b_hex, do_default_content_merge, delete_a, delete_b ) )
            
        
        allowed_duplicate_types = {
            HC.DUPLICATE_FALSE_POSITIVE,
            HC.DUPLICATE_ALTERNATE,
            HC.DUPLICATE_BETTER,
            HC.DUPLICATE_WORSE,
            HC.DUPLICATE_SAME_QUALITY,
            HC.DUPLICATE_POTENTIAL
        }
        
        # variable type testing
        for row in raw_rows:
            
            ( duplicate_type, hash_a_hex, hash_b_hex, do_default_content_merge, delete_first, delete_second ) = row
            
            HydrusNetworkVariableHandling.TestVariableType( 'relationship', duplicate_type, int, allowed_values = allowed_duplicate_types )
            HydrusNetworkVariableHandling.TestVariableType( 'hash_a', hash_a_hex, str )
            HydrusNetworkVariableHandling.TestVariableType( 'hash_b', hash_b_hex, str )
            HydrusNetworkVariableHandling.TestVariableType( 'do_default_content_merge', do_default_content_merge, bool )
            HydrusNetworkVariableHandling.TestVariableType( 'delete_first', delete_first, bool )
            HydrusNetworkVariableHandling.TestVariableType( 'delete_second', delete_second, bool )
            
            try:
                
                hash_a = bytes.fromhex( hash_a_hex )
                hash_b = bytes.fromhex( hash_b_hex )
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, did not understand one of the hashes {} or {}!'.format( hash_a_hex, hash_b_hex ) )
                
            
            CheckHashLength( ( hash_a, hash_b ) )
            
            all_hashes.update( ( hash_a, hash_b ) )
            
        
        media_results = HG.client_controller.Read( 'media_results', all_hashes )
        
        hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
        
        for row in raw_rows:
            
            ( duplicate_type, hash_a_hex, hash_b_hex, do_default_content_merge, delete_first, delete_second ) = row
            
            hash_a = bytes.fromhex( hash_a_hex )
            hash_b = bytes.fromhex( hash_b_hex )
            
            list_of_service_keys_to_content_updates = []
            
            first_media = ClientMedia.MediaSingleton( hashes_to_media_results[ hash_a ] )
            second_media = ClientMedia.MediaSingleton( hashes_to_media_results[ hash_b ] )
            
            file_deletion_reason = 'From Client API (duplicates processing).'
            
            if do_default_content_merge:
                
                duplicate_content_merge_options = HG.client_controller.new_options.GetDuplicateContentMergeOptions( duplicate_type )
                
                list_of_service_keys_to_content_updates.append( duplicate_content_merge_options.ProcessPairIntoContentUpdates( first_media, second_media, file_deletion_reason = file_deletion_reason, delete_first = delete_first, delete_second = delete_second ) )
                
            elif delete_first or delete_second:
                
                service_keys_to_content_updates = collections.defaultdict( list )
                
                deletee_media = set()
                
                if delete_first:
                    
                    deletee_media.add( first_media )
                    
                
                if delete_second:
                    
                    deletee_media.add( second_media )
                    
                
                for media in deletee_media:
                    
                    if media.HasDeleteLocked():
                        
                        ClientMedia.ReportDeleteLockFailures( [ media ] )
                        
                        continue
                        
                    
                    if media.GetLocationsManager().IsTrashed():
                        
                        deletee_service_keys = ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, )
                        
                    else:
                        
                        local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
                        
                        deletee_service_keys = media.GetLocationsManager().GetCurrent().intersection( local_file_service_keys )
                        
                    
                    for deletee_service_key in deletee_service_keys:
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, media.GetHashes(), reason = file_deletion_reason )
                        
                        service_keys_to_content_updates[ deletee_service_key ].append( content_update )
                        
                    
                
                list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
                
            
            database_write_rows.append( ( duplicate_type, hash_a, hash_b, list_of_service_keys_to_content_updates ) )
            
        
        if len( database_write_rows ) > 0:
            
            HG.client_controller.WriteSynchronous( 'duplicate_pair_status', database_write_rows )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePages( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES )
        
    

class HydrusResourceClientAPIRestrictedManagePagesAddFiles( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key, media_results ):
            
            page = HG.client_controller.gui.GetPageFromPageKey( page_key )
            
            from hydrus.client.gui.pages import ClientGUIPages
            
            if page is None:
                
                raise HydrusExceptions.DataMissing()
                
            
            if not isinstance( page, ClientGUIPages.Page ):
                
                raise HydrusExceptions.BadRequestException( 'That page key was not for a normal media page!' )
                
            
            page.AddMediaResults( media_results )
            
        
        if 'page_key' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'You need a page key for this request!' )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        hashes = ParseHashes( request )
        
        media_results = HG.client_controller.Read( 'media_results', hashes, sorted = True )
        
        try:
            
            HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it, page_key, media_results )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesFocusPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key ):
            
            return HG.client_controller.gui.ShowPage( page_key )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        try:
            
            HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it, page_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManagePagesGetPages( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it():
            
            return HG.client_controller.gui.GetCurrentSessionPageAPIInfoDict()
            
        
        page_info_dict = HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it )
        
        body_dict = { 'pages' : page_info_dict }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesGetPageInfo( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key, simple ):
            
            return HG.client_controller.gui.GetPageAPIInfoDict( page_key, simple )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        simple = request.parsed_request_args.GetValue( 'simple', bool, default_value = True )
        
        page_info_dict = HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it, page_key, simple )
        
        if page_info_dict is None:
            
            raise HydrusExceptions.NotFoundException( 'Did not find a page for "{}"!'.format( page_key.hex() ) )
            
        
        body_dict = { 'page_info' : page_info_dict }
        
        body = Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesRefreshPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key ):
            
            return HG.client_controller.gui.RefreshPage( page_key )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        try:
            
            HG.client_controller.CallBlockingToQt( HG.client_controller.gui, do_it, page_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
