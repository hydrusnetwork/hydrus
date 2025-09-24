import collections.abc
import json
import typing

CBOR_AVAILABLE = False

try:
    
    import cbor2
    
    CBOR_AVAILABLE = True
    
except:
    
    pass
    

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags
from hydrus.core import HydrusTemp
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusServerRequest

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.metadata import ClientRatings
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchParseSystemPredicates
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

# if a variable name isn't defined here, a GET with it won't work
CLIENT_API_INT_PARAMS = {
    'duplicate_pair_sort_type',
    'file_id',
    'file_sort_type',
    'potentials_search_type',
    'pixel_duplicates',
    'max_hamming_distance',
    'max_num_pairs',
    'width',
    'height',
    'render_format',
    'render_quality'
}

CLIENT_API_BYTE_PARAMS = {
    'hash',
    'destination_page_key',
    'page_key',
    'service_key',
    'Hydrus-Client-API-Access-Key',
    'Hydrus-Client-API-Session-Key',
    'file_service_key',
    'deleted_file_service_key',
    'tag_service_key',
    'tag_service_key_1',
    'tag_service_key_2',
    'rating_service_key',
    'job_status_key'
}

CLIENT_API_STRING_PARAMS = {
    'name',
    'url',
    'domain',
    'search',
    'service_name',
    'reason',
    'tag_display_type',
    'source_hash_type',
    'desired_hash_type'
}

CLIENT_API_JSON_PARAMS = {
    'basic_permissions',
    'permits_everything',
    'tags',
    'tags_1',
    'tags_2',
    'file_ids',
    'download',
    'only_return_identifiers',
    'only_return_basic_information',
    'include_blurhash',
    'create_new_file_ids',
    'detailed_url_information',
    'duplicate_pair_sort_asc',
    'hide_service_keys_tags',
    'simple',
    'file_sort_asc',
    'group_mode',
    'return_hashes',
    'return_file_ids',
    'include_thumbnail_filetype',
    'include_notes',
    'include_milliseconds',
    'include_services_object',
    'notes',
    'note_names',
    'doublecheck_file_system',
    'only_in_view',
    'include_current_tags',
    'include_pending_tags'
}

CLIENT_API_JSON_BYTE_LIST_PARAMS = {
    'file_service_keys',
    'deleted_file_service_keys',
    'hashes'
}

CLIENT_API_JSON_BYTE_DICT_PARAMS = {
    'service_keys_to_tags',
    'service_keys_to_actions_to_tags',
    'service_keys_to_additional_tags'
}

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
        
        if isinstance( data, dict ):
            
            if 'version' not in data:
                
                data[ 'version' ] = HC.CLIENT_API_VERSION
                
            
            if 'hydrus_version' not in data:
                
                data[ 'hydrus_version' ] = HC.SOFTWARE_VERSION
                
            
        
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
        
        service = CG.client_controller.services_manager.GetService( file_service_key )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the file service "{}"!'.format( file_service_key.hex() ) )
        
    
    if service.GetServiceType() not in HC.ALL_FILE_SERVICES:
        
        raise HydrusExceptions.BadRequestException( 'Sorry, the service key "{}" did not give a file service!'.format( file_service_key.hex() ) )
        
    
    return service
    

def CheckTagService( tag_service_key: bytes ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( tag_service_key )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the tag service "{}"!'.format( tag_service_key.hex() ) )
        
    
    if service.GetServiceType() not in HC.ALL_TAG_SERVICES:
        
        raise HydrusExceptions.BadRequestException( 'Sorry, the service key "{}" did not give a tag service!'.format( tag_service_key.hex() ) )
        
    
    return service
    

def CheckTags( tags: collections.abc.Collection[ str ] ):
    
    for tag in tags:
        
        try:
            
            clean_tag = HydrusTags.CleanTag( tag )
            
        except Exception as e:
            
            raise HydrusExceptions.BadRequestException( 'Could not parse tag "{}"!'.format( tag ) )
            
        
        if clean_tag == '':
            
            raise HydrusExceptions.BadRequestException( 'Tag "{}" was empty!'.format( tag ) )
            
        
    

def CheckUploadableService( service_key: bytes ):
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_key.hex() ) )
        
    
    if service.GetServiceType() not in ( HC.IPFS, HC.FILE_REPOSITORY, HC.TAG_REPOSITORY ):
        
        raise HydrusExceptions.BadRequestException( f'Sorry, the service key "{service_key.hex()}" was not for an uploadable service!' )
        
    

def GetServicesDict():
    
    service_types = [
        HC.LOCAL_TAG,
        HC.TAG_REPOSITORY,
        HC.LOCAL_FILE_DOMAIN,
        HC.LOCAL_FILE_UPDATE_DOMAIN,
        HC.FILE_REPOSITORY,
        HC.COMBINED_LOCAL_FILE,
        HC.COMBINED_LOCAL_MEDIA,
        HC.COMBINED_FILE,
        HC.COMBINED_TAG,
        HC.LOCAL_RATING_LIKE,
        HC.LOCAL_RATING_NUMERICAL,
        HC.LOCAL_RATING_INCDEC,
        HC.LOCAL_FILE_TRASH_DOMAIN
    ]
    
    services = CG.client_controller.services_manager.GetServices( service_types )
    
    services_dict = {}
    
    for service in services:
        
        service_dict = {
            'name' : service.GetName(),
            'type' : service.GetServiceType(),
            'type_pretty' : HC.service_string_lookup[ service.GetServiceType() ]
        }
        
        if service.GetServiceType() in HC.STAR_RATINGS_SERVICES:
            
            star_type = service.GetStarType()
            
            if star_type.HasShape():
                
                shape_label = ClientRatings.shape_to_str_lookup_dict[ star_type.GetShape() ]
                
            else:
                
                shape_label = 'svg'
                
            
            service_dict[ 'star_shape' ] =  shape_label
            
        
        if service.GetServiceType() == HC.LOCAL_RATING_NUMERICAL:
            
            allows_zero = service.AllowZero()
            num_stars = service.GetNumStars()
            
            service_dict[ 'min_stars' ] = 0 if allows_zero else 1
            service_dict[ 'max_stars' ] = num_stars
            
        
        services_dict[ service.GetServiceKey().hex() ] = service_dict
        
    
    return services_dict
    

def GetServiceKeyFromName( service_name: str ):
    
    try:
        
        service_key = CG.client_controller.services_manager.GetServiceKeyFromName( HC.ALL_SERVICES, service_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with name "{}"!'.format( service_name ) )
        
    
    return service_key
    

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
                
                raise HydrusExceptions.BadRequestException( 'Sorry, did not understand the JSON you gave me: {}'.format( e ) )
                
            
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
    
def ParseClientAPISearchPredicates( request ) -> list[ ClientSearchPredicate.Predicate ]:
    
    default_search_values = {}
    
    default_search_values[ 'tags' ] = []
    
    for ( key, value ) in default_search_values.items():
        
        if key not in request.parsed_request_args:
            
            request.parsed_request_args[ key ] = value
            
        
    
    tags = request.parsed_request_args[ 'tags' ]
    
    predicates = ConvertTagListToPredicates( request, tags )
    
    if len( predicates ) == 0:
        
        return predicates
        
    
    we_have_at_least_one_inclusive_tag = True in ( predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG and predicate.IsInclusive() for predicate in predicates )
    
    if not we_have_at_least_one_inclusive_tag:
        
        try:
            
            request.client_api_permissions.CheckCanSeeAllFiles()
            
        except HydrusExceptions.InsufficientCredentialsException:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, you do not have permission to see all files on this client. Please add a regular tag to your search.' )
            
        
    
    return predicates
    

def ParsePotentialDuplicatesSearchContext( request: HydrusServerRequest.HydrusRequest ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext:
    
    location_context = ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
    
    tag_service_key_1 = request.parsed_request_args.GetValue( 'tag_service_key_1', bytes, default_value = CC.COMBINED_TAG_SERVICE_KEY )
    tag_service_key_2 = request.parsed_request_args.GetValue( 'tag_service_key_2', bytes, default_value = CC.COMBINED_TAG_SERVICE_KEY )
    
    CheckTagService( tag_service_key_1 )
    CheckTagService( tag_service_key_2 )
    
    tag_context_1 = ClientSearchTagContext.TagContext( service_key = tag_service_key_1 )
    tag_context_2 = ClientSearchTagContext.TagContext( service_key = tag_service_key_2 )
    
    tags_1 = request.parsed_request_args.GetValue( 'tags_1', list, default_value = [] )
    tags_2 = request.parsed_request_args.GetValue( 'tags_2', list, default_value = [] )
    
    if len( tags_1 ) == 0:
        
        predicates_1 = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
    else:
        
        predicates_1 = ConvertTagListToPredicates( request, tags_1, do_permission_check = False )
        
    
    if len( tags_2 ) == 0:
        
        predicates_2 = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
    else:
        
        predicates_2 = ConvertTagListToPredicates( request, tags_2, do_permission_check = False )
        
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context_1, predicates = predicates_1 )
    file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context_2, predicates = predicates_2 )
    
    dupe_search_type = request.parsed_request_args.GetValue( 'potentials_search_type', int, default_value = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
    pixel_dupes_preference = request.parsed_request_args.GetValue( 'pixel_duplicates', int, default_value = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
    max_hamming_distance = request.parsed_request_args.GetValue( 'max_hamming_distance', int, default_value = 4 )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetFileSearchContext2( file_search_context_2 )
    potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
    potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
    potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
    
    return potential_duplicates_search_context
    

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
        
    

def ParseLocalFileDomainLocationContext( request: HydrusServerRequest.HydrusRequest ) -> typing.Optional[ ClientLocation.LocationContext ]:
    
    custom_location_context = ParseLocationContext( request, ClientLocation.LocationContext(), deleted_allowed = False )
    
    if not custom_location_context.IsEmpty():
        
        for service_key in custom_location_context.current_service_keys:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            if service.GetServiceType() not in ( HC.LOCAL_FILE_DOMAIN, ):
                
                raise HydrusExceptions.BadRequestException( 'Sorry, any custom file domain here must only declare local file domains.' )
                
            
        
        return custom_location_context
        
    
    return None
    

def ParseHashes( request: HydrusServerRequest.HydrusRequest, optional = False ):
    
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
        
    
    if 'file_id' in request.parsed_request_args or 'file_ids' in request.parsed_request_args:
        
        something_was_set = True
        
        hash_ids = []
        
        if 'file_id' in request.parsed_request_args:
            
            hash_ids.append( request.parsed_request_args.GetValue( 'file_id', int ) )
            
        
        if 'file_ids' in request.parsed_request_args:
            
            hash_ids.extend( request.parsed_request_args.GetValue( 'file_ids', list, expected_list_type = int ) )
            
        
        if True in ( hash_id < 0 for hash_id in hash_ids ):
            
            raise HydrusExceptions.BadRequestException( 'Was asked about a negative hash_id!' )
            
        
        too_big_m8 = 1024 ** 5 # a quadrillion
        
        if True in ( hash_id > too_big_m8 for hash_id in hash_ids ):
            
            raise HydrusExceptions.BadRequestException( 'Was asked about a hash_id that was way too big!' )
            
        
        try:
            
            hash_ids_to_hashes = CG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = hash_ids, error_on_missing_hash_ids = True )
            
        except HydrusExceptions.DBException as e:
            
            if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                
                raise HydrusExceptions.NotFoundException( f'It seems you gave a file_id that does not exist! {e.db_e}' )
                
            else:
                
                raise
                
            
        
        if len( hash_ids_to_hashes ) > 0:
            
            hashes.extend( [ hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] )
            
        
    
    if not something_was_set: # subtly different to 'no hashes'
        
        if optional:
            
            return None
            
        
        raise HydrusExceptions.BadRequestException( 'Please include some files in your request--file_id or hash based!' )
        
    
    hashes = HydrusLists.DedupeList( hashes )
    
    if not optional or len( hashes ) > 0:
        
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
    

def ConvertTagListToPredicates( request, tag_list, do_permission_check = True, error_on_invalid_tag = True ) -> list[ ClientSearchPredicate.Predicate ]:
    
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
        
        predicates.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, or_preds ) )
        
    
    predicates.extend( ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( system_predicate_strings ) )
    
    search_tags = [ ( True, tag ) for tag in tags ]
    search_tags.extend( ( ( False, tag ) for tag in negated_tags ) )
    
    for ( inclusive, tag ) in search_tags:
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        if '*' in tag:
            
            if subtag == '*':
                
                tag = namespace
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE
                
            else:
                
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_WILDCARD
                
            
        else:
            
            predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG
            
        
        predicates.append( ClientSearchPredicate.Predicate( predicate_type = predicate_type, value = tag, inclusive = inclusive ) )
        
    
    return predicates
    
