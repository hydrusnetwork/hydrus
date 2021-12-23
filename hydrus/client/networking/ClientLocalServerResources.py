import collections
import collections.abc
import json
import os
import threading
import time
import traceback
import typing

from twisted.web.static import File as FileResource

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags
from hydrus.core import HydrusTemp
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client import ClientSearchParseSystemPredicates
from hydrus.client.importing import ClientImportFiles
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain

local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

LOCAL_BOORU_INT_PARAMS = set()
LOCAL_BOORU_BYTE_PARAMS = { 'share_key', 'hash' }
LOCAL_BOORU_STRING_PARAMS = set()
LOCAL_BOORU_JSON_PARAMS = set()
LOCAL_BOORU_JSON_BYTE_LIST_PARAMS = set()

CLIENT_API_INT_PARAMS = { 'file_id', 'file_sort_type' }
CLIENT_API_BYTE_PARAMS = { 'hash', 'destination_page_key', 'page_key', 'Hydrus-Client-API-Access-Key', 'Hydrus-Client-API-Session-Key', 'tag_service_key', 'file_service_key' }
CLIENT_API_STRING_PARAMS = { 'name', 'url', 'domain', 'file_service_name', 'tag_service_name' }
CLIENT_API_JSON_PARAMS = { 'basic_permissions', 'system_inbox', 'system_archive', 'tags', 'file_ids', 'only_return_identifiers', 'detailed_url_information', 'hide_service_names_tags', 'simple', 'file_sort_asc' }
CLIENT_API_JSON_BYTE_LIST_PARAMS = { 'hashes' }
CLIENT_API_JSON_BYTE_DICT_PARAMS = { 'service_keys_to_tags', 'service_keys_to_actions_to_tags', 'service_keys_to_additional_tags' }

def CheckHashLength( hashes, hash_type = 'sha256' ):
    
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
            
        
    
def ConvertServiceNamesDictToKeys( allowed_service_types, service_name_dict ):
    
    service_key_dict = {}
    
    for ( service_name, value ) in service_name_dict.items():
        
        try:
            
            service_key = HG.client_controller.services_manager.GetServiceKeyFromName( allowed_service_types, service_name )
            
        except:
            
            raise HydrusExceptions.BadRequestException( 'Could not find the service "{}", or it was the wrong type!'.format( service_name ) )
            
        
        service_key_dict[ service_key ] = value
        
    
    return service_key_dict
    
def ParseLocalBooruGETArgs( requests_args ):
    
    args = HydrusNetworkVariableHandling.ParseTwistedRequestGETArgs( requests_args, LOCAL_BOORU_INT_PARAMS, LOCAL_BOORU_BYTE_PARAMS, LOCAL_BOORU_STRING_PARAMS, LOCAL_BOORU_JSON_PARAMS, LOCAL_BOORU_JSON_BYTE_LIST_PARAMS )
    
    return args
    
def ParseClientAPIGETArgs( requests_args ):
    
    args = HydrusNetworkVariableHandling.ParseTwistedRequestGETArgs( requests_args, CLIENT_API_INT_PARAMS, CLIENT_API_BYTE_PARAMS, CLIENT_API_STRING_PARAMS, CLIENT_API_JSON_PARAMS, CLIENT_API_JSON_BYTE_LIST_PARAMS )
    
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
                
            
        
    
    return parsed_request_args
    
def ParseClientAPIPOSTArgs( request ):
    
    request.content.seek( 0 )
    
    if not request.requestHeaders.hasHeader( 'Content-Type' ):
        
        parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments()
        
        total_bytes_read = 0
        
    else:
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        if ';' in content_type:
            
            # lmao: application/json;charset=utf-8
            content_type = content_type.split( ';', 1 )[0]
            
        
        try:
            
            mime = HC.mime_enum_lookup[ content_type ]
            
        except:
            
            raise HydrusExceptions.BadRequestException( 'Did not recognise Content-Type header!' )
            
        
        total_bytes_read = 0
        
        if mime == HC.APPLICATION_JSON:
            
            json_bytes = request.content.read()
            
            total_bytes_read += len( json_bytes )
            
            json_string = str( json_bytes, 'utf-8' )
            
            args = json.loads( json_string )
            
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
    
def ParseClientAPISearchPredicates( request ):
    
    default_search_values = {}
    
    default_search_values[ 'tags' ] = []
    default_search_values[ 'system_inbox' ] = False
    default_search_values[ 'system_archive' ] = False
    
    for ( key, value ) in default_search_values.items():
        
        if key not in request.parsed_request_args:
            
            request.parsed_request_args[ key ] = value
            
        
    
    system_inbox = request.parsed_request_args[ 'system_inbox' ]
    system_archive = request.parsed_request_args[ 'system_archive' ]
    
    tags = request.parsed_request_args[ 'tags' ]
    
    predicates = ConvertTagListToPredicates( request, tags )
    
    if len( predicates ) == 0:
        
        try:
            
            request.client_api_permissions.CheckCanSeeAllFiles()
            
        except HydrusExceptions.InsufficientCredentialsException:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, you do not have permission to see all files on this client. Please add a regular tag to your search.' )
            
        
    
    if system_inbox:
        
        predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX ) )
        
    elif system_archive:
        
        predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
    
    return predicates
    
def ConvertTagListToPredicates( request, tag_list, do_permission_check = True ) -> list:
    
    or_tag_lists = [ tag for tag in tag_list if isinstance( tag, list ) ]
    tag_strings = [ tag for tag in tag_list if isinstance( tag, str ) ]
    
    system_predicate_strings = [ tag for tag in tag_strings if tag.startswith( 'system:' ) ]
    tags = [ tag for tag in tag_strings if not tag.startswith( 'system:' ) ]
    
    negated_tags = [ tag for tag in tags if tag.startswith( '-' ) ]
    tags = [ tag for tag in tags if not tag.startswith( '-' ) ]
    
    negated_tags = HydrusTags.CleanTags( negated_tags )
    tags = HydrusTags.CleanTags( tags )
    
    if do_permission_check:
        
        if len( tags ) == 0:
            
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
            
        elif mime in HC.AUDIO:
            
            path = os.path.join( HC.STATIC_DIR, 'audio.png' )
            
        elif mime == HC.APPLICATION_PDF:
            
            path = os.path.join( HC.STATIC_DIR, 'pdf.png' )
            
        elif mime == HC.APPLICATION_PSD:
            
            path = os.path.join( HC.STATIC_DIR, 'psd.png' )
            
        else:
            
            path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
            
        
        if not os.path.exists( path ):
            
            raise HydrusExceptions.NotFoundException( 'Could not find that thumbnail!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_context_mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPI( HydrusServerResources.HydrusResource ):
    
    BLOCKED_WHEN_BUSY = True
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        parsed_request_args = ParseClientAPIGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        ( parsed_request_args, total_bytes_read ) = ParseClientAPIPOSTArgs( request )
        
        self._reportDataUsed( request, total_bytes_read )
        
        request.parsed_request_args = parsed_request_args
        
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIVersion( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        body_dict = {}
        
        body_dict[ 'version' ] = HC.CLIENT_API_VERSION
        body_dict[ 'hydrus_version' ] = HC.SOFTWARE_VERSION
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAccountVerify( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        api_permissions = request.client_api_permissions
        
        basic_permissions = api_permissions.GetBasicPermissions()
        human_description = api_permissions.ToHumanString()
        
        body_dict = {}
        
        body_dict[ 'basic_permissions' ] = list( basic_permissions ) # set->list for json
        body_dict[ 'human_description' ] = human_description
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetServices( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        jobs = [
            ( ( HC.LOCAL_TAG, ), 'local_tags' ),
            ( ( HC.TAG_REPOSITORY, ), 'tag_repositories' ),
            ( ( HC.LOCAL_FILE_DOMAIN, ), 'local_files' ),
            ( ( HC.FILE_REPOSITORY, ), 'file_repositories' ),
            ( ( HC.COMBINED_LOCAL_FILE, ), 'all_local_files' ),
            ( ( HC.COMBINED_FILE, ), 'all_known_files' ),
            ( ( HC.COMBINED_TAG, ), 'all_known_tags' ),
            ( ( HC.LOCAL_FILE_TRASH_DOMAIN, ), 'trash' )
        ]
        
        body_dict = {}
        
        for ( service_types, name ) in jobs:
            
            services = HG.client_controller.services_manager.GetServices( service_types )
            
            body_dict[ name ] = [ { 'name' : service.GetName(), 'service_key' : service.GetServiceKey().hex() } for service in services ]
            
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options )
        
        try:
            
            file_import_status = file_import_job.DoWork()
            
        except:
            
            file_import_status = ClientImportFiles.FileImportStatus( CC.STATUS_ERROR, file_import_job.GetHash(), note = traceback.format_exc() )
            
        
        body_dict = {}
        
        body_dict[ 'status' ] = file_import_status.status
        body_dict[ 'hash' ] = HydrusData.BytesToNoneOrHex( file_import_status.hash )
        body_dict[ 'note' ] = file_import_status.note
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesArchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            hashes.update( more_hashes )
            
        
        CheckHashLength( hashes )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesDeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            hashes.update( more_hashes )
            
        
        CheckHashLength( hashes )
        
        # expand this to take file service and reason
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesUnarchiveFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            hashes.update( more_hashes )
            
        
        CheckHashLength( hashes )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFilesUndeleteFiles( HydrusResourceClientAPIRestrictedAddFiles ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            hashes.update( more_hashes )
            
        
        CheckHashLength( hashes )
        
        # expand this to take file service, if and when we move to multiple trashes or whatever
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] }
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTags( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
        
    
class HydrusResourceClientAPIRestrictedAddTagsAddTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            hashes.update( more_hashes )
            
        
        CheckHashLength( hashes )
        
        if len( hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'There were no hashes given!' )
            
        
        #
        
        service_keys_to_tags = None
        
        if 'service_keys_to_tags' in request.parsed_request_args:
            
            service_keys_to_tags = request.parsed_request_args.GetValue( 'service_keys_to_tags', dict )
            
        elif 'service_names_to_tags' in request.parsed_request_args:
            
            service_names_to_tags = request.parsed_request_args.GetValue( 'service_names_to_tags', dict )
            
            service_keys_to_tags = ConvertServiceNamesDictToKeys( HC.REAL_TAG_SERVICES, service_names_to_tags )
            
        
        service_keys_to_actions_to_tags = None
        
        if service_keys_to_tags is not None:
            
            service_keys_to_actions_to_tags = {}
            
            for ( service_key, tags ) in service_keys_to_tags.items():
                
                try:
                    
                    service = HG.client_controller.services_manager.GetService( service_key )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service with key {}! Maybe it was recently deleted?'.format( service_key.hex() ) )
                    
                
                if service.GetServiceType() == HC.LOCAL_TAG:
                    
                    content_action = HC.CONTENT_UPDATE_ADD
                    
                else:
                    
                    content_action = HC.CONTENT_UPDATE_PEND
                    
                
                service_keys_to_actions_to_tags[ service_key ] = collections.defaultdict( set )
                
                service_keys_to_actions_to_tags[ service_key ][ content_action ].update( tags )
                
            
        
        if 'service_keys_to_actions_to_tags' in request.parsed_request_args:
            
            service_keys_to_actions_to_tags = request.parsed_request_args.GetValue( 'service_keys_to_actions_to_tags', dict )
            
        elif 'service_names_to_actions_to_tags' in request.parsed_request_args:
            
            service_names_to_actions_to_tags = request.parsed_request_args.GetValue( 'service_names_to_actions_to_tags', dict )
            
            service_keys_to_actions_to_tags = ConvertServiceNamesDictToKeys( HC.REAL_TAG_SERVICES, service_names_to_actions_to_tags )
            
        
        if service_keys_to_actions_to_tags is None:
            
            raise HydrusExceptions.BadRequestException( 'Need a service-names-to-tags parameter!' )
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        for ( service_key, actions_to_tags ) in service_keys_to_actions_to_tags.items():
            
            try:
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                raise HydrusExceptions.BadRequestException( 'Could not find the service with key {}! Maybe it was recently deleted?'.format( service_key.hex() ) )
                
            
            if service.GetServiceType() not in HC.REAL_TAG_SERVICES:
                
                raise HydrusExceptions.BadRequestException( 'Was given a service that is not a tag service!' )
                
            
            for ( content_action, tags ) in actions_to_tags.items():
                
                tags = list( tags )
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                content_action = int( content_action )
                
                actual_tags = []
                
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
                        
                    
                    actual_tags.append( tag )
                    tags_to_reasons[ tag ] = reason
                    
                
                actual_tags = HydrusTags.CleanTags( actual_tags )
                
                if len( actual_tags ) == 0:
                    
                    continue
                    
                
                tags = actual_tags
                
                if service.GetServiceType() == HC.LOCAL_TAG:
                    
                    if content_action not in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                        
                        continue
                        
                    
                else:
                    
                    if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                        
                        continue
                        
                    
                
                if content_action == HC.CONTENT_UPDATE_PETITION:
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ), reason = tags_to_reasons[ tag ] ) for tag in tags ]
                    
                else:
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ) ) for tag in tags ]
                    
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTagsGetTagServices( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        local_tags = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
        tag_repos = HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        body_dict = {}
        
        body_dict[ 'local_tags' ] = [ service.GetName() for service in local_tags ]
        body_dict[ 'tag_repositories' ] = [ service.GetName() for service in tag_repos ]
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTagsCleanTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tags = request.parsed_request_args.GetValue( 'tags', list, expected_list_type = str )
        
        tags = list( HydrusTags.CleanTags( tags ) )
        
        tags = HydrusTags.SortNumericTags( tags )
        
        body_dict = {}
        
        body_dict[ 'tags' ] = tags
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
            
            for url in urls:
                
                if not isinstance( url, str ):
                    
                    continue
                    
                
                urls_to_add.append( url )
                
            
        
        urls_to_delete = []
        
        if 'url_to_delete' in request.parsed_request_args:
            
            url = request.parsed_request_args.GetValue( 'url_to_delete', str )
            
            urls_to_delete.append( url )
            
        
        if 'urls_to_delete' in request.parsed_request_args:
            
            urls = request.parsed_request_args.GetValue( 'urls_to_delete', list, expected_list_type = str )
            
            for url in urls:
                
                if not isinstance( url, str ):
                    
                    continue
                    
                
                urls_to_delete.append( url )
                
            
        
        domain_manager = HG.client_controller.network_engine.domain_manager
        
        try:
            
            urls_to_add = [ domain_manager.NormaliseURL( url ) for url in urls_to_add ]
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        if len( urls_to_add ) == 0 and len( urls_to_delete ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any URLs to add or delete!' )
            
        
        applicable_hashes = []
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args.GetValue( 'hash', bytes )
            
            applicable_hashes.append( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            applicable_hashes.extend( hashes )
            
        
        CheckHashLength( applicable_hashes )
        
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
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        url_statuses = HG.client_controller.Read( 'url_statuses', normalised_url )
        
        json_happy_url_statuses = []
        
        for file_import_status in url_statuses:
            
            file_import_status = ClientImportFiles.CheckFileImportStatus( file_import_status )
            
            d = {}
            
            d[ 'status' ] = file_import_status.status
            d[ 'hash' ] = HydrusData.BytesToNoneOrHex( file_import_status.hash )
            d[ 'note' ] = file_import_status.note
            
            json_happy_url_statuses.append( d )
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_file_statuses' : json_happy_url_statuses }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
            
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
        
        service_keys_to_additional_tags = None
        
        if 'service_names_to_tags' in request.parsed_request_args or 'service_names_to_additional_tags' in request.parsed_request_args:
            
            if 'service_names_to_tags' in request.parsed_request_args:
                
                service_names_to_additional_tags = request.parsed_request_args.GetValue( 'service_names_to_tags', dict )
                
            else:
                
                service_names_to_additional_tags = request.parsed_request_args.GetValue( 'service_names_to_additional_tags', dict )
                
            
            service_keys_to_additional_tags = ConvertServiceNamesDictToKeys( HC.REAL_TAG_SERVICES, service_names_to_additional_tags )
            
        elif 'service_keys_to_additional_tags' in request.parsed_request_args:
            
            service_keys_to_additional_tags = request.parsed_request_args.GetValue( 'service_keys_to_additional_tags', dict )
            
        
        if service_keys_to_additional_tags is not None:
            
            request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
            
            for ( service_key, tags ) in service_keys_to_additional_tags.items():
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                if service.GetServiceType() not in HC.REAL_TAG_SERVICES:
                    
                    raise HydrusExceptions.BadRequestException( 'Was given a service that is not a tag service!' )
                    
                
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFiles( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
class HydrusResourceClientAPIRestrictedGetFilesSearchFiles( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'file_service_key' in request.parsed_request_args or 'file_service_name' in request.parsed_request_args:
            
            if 'file_service_key' in request.parsed_request_args:
                
                file_service_key = request.parsed_request_args[ 'file_service_key' ]
                
            else:
                
                file_service_name = request.parsed_request_args[ 'file_service_name' ]
                
                try:
                    
                    file_service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.ALL_FILE_SERVICES, file_service_name )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( file_service_name ) )
                    
                
            
            try:
                
                service = HG.client_controller.services_manager.GetService( file_service_key )
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'Could not find that file service!' )
                
            
            if service.GetServiceType() not in HC.ALL_FILE_SERVICES:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, that service key did not give a file service!' )
                
            
        else:
            
            # I guess ideally we would go for the 'all local services' umbrella, or a list of them, or however we end up doing that
            # for now we'll fudge it
            
            file_service_key = list( HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )[0]
            
        
        if 'tag_service_key' in request.parsed_request_args or 'tag_service_name' in request.parsed_request_args:
            
            if 'tag_service_key' in request.parsed_request_args:
                
                tag_service_key = request.parsed_request_args[ 'tag_service_key' ]
                
            else:
                
                tag_service_name = request.parsed_request_args[ 'tag_service_name' ]
                
                try:
                    
                    tag_service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.ALL_TAG_SERVICES, tag_service_name )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( tag_service_name ) )
                    
                
            
            try:
                
                service = HG.client_controller.services_manager.GetService( tag_service_key )
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'Could not find that tag service!' )
                
            
            if service.GetServiceType() not in HC.ALL_TAG_SERVICES:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, that service key did not give a tag service!' )
                
            
        else:
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, search for all known tags over all known files is not supported!' )
            
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ file_service_key ] )
        tag_search_context = ClientSearch.TagSearchContext( service_key = tag_service_key )
        predicates = ParseClientAPISearchPredicates( request )
        
        file_search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, tag_search_context = tag_search_context, predicates = predicates )
        
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
        
        hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context, sort_by = sort_by, apply_implicit_limit = False )
        
        request.client_api_permissions.SetLastSearchResults( hash_ids )
        
        body_dict = { 'file_ids' : list( hash_ids ) }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
        
    
class HydrusResourceClientAPIRestrictedGetFilesFileMetadata( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        only_return_identifiers = request.parsed_request_args.GetValue( 'only_return_identifiers', bool, default_value = False )
        hide_service_names_tags = request.parsed_request_args.GetValue( 'hide_service_names_tags', bool, default_value = False )
        detailed_url_information = request.parsed_request_args.GetValue( 'detailed_url_information', bool, default_value = False )
        
        try:
            
            if 'file_ids' in request.parsed_request_args:
                
                file_ids = request.parsed_request_args.GetValue( 'file_ids', list, expected_list_type = int )
                
                request.client_api_permissions.CheckPermissionToSeeFiles( file_ids )
                
                if only_return_identifiers:
                    
                    file_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = file_ids )
                    
                else:
                    
                    media_results = HG.client_controller.Read( 'media_results_from_ids', file_ids, sorted = True )
                    
                
            elif 'hashes' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
                
                CheckHashLength( hashes )
                
                if only_return_identifiers:
                    
                    file_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hashes = hashes )
                    
                else:
                    
                    media_results = HG.client_controller.Read( 'media_results', hashes, sorted = True )
                    
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_ids or hashes parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers did not exist in the database!' )
            
        
        body_dict = {}
        
        metadata = []
        
        if only_return_identifiers:
            
            for ( file_id, hash ) in file_ids_to_hashes.items():
                
                metadata_row = {}
                
                metadata_row[ 'file_id' ] = file_id
                metadata_row[ 'hash' ] = hash.hex()
                
                metadata.append( metadata_row )
                
            
        else:
            
            services_manager = HG.client_controller.services_manager
            
            service_keys_to_names = {}
            
            for media_result in media_results:
                
                metadata_row = {}
                
                file_info_manager = media_result.GetFileInfoManager()
                
                metadata_row[ 'file_id' ] = file_info_manager.hash_id
                metadata_row[ 'hash' ] = file_info_manager.hash.hex()
                metadata_row[ 'size' ] = file_info_manager.size
                metadata_row[ 'mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.mime ]
                metadata_row[ 'ext' ] = HC.mime_ext_lookup[ file_info_manager.mime ]
                metadata_row[ 'width' ] = file_info_manager.width
                metadata_row[ 'height' ] = file_info_manager.height
                metadata_row[ 'duration' ] = file_info_manager.duration
                metadata_row[ 'num_frames' ] = file_info_manager.num_frames
                metadata_row[ 'num_words' ] = file_info_manager.num_words
                metadata_row[ 'has_audio' ] = file_info_manager.has_audio
                
                locations_manager = media_result.GetLocationsManager()
                
                metadata_row[ 'is_inbox' ] = locations_manager.inbox
                metadata_row[ 'is_local' ] = locations_manager.IsLocal()
                metadata_row[ 'is_trashed' ] = locations_manager.IsTrashed()
                
                known_urls = sorted( locations_manager.GetURLs() )
                
                metadata_row[ 'known_urls' ] = known_urls
                
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
                
                service_names_to_statuses_to_tags = {}
                api_service_keys_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    if service_key not in service_keys_to_names:
                        
                        service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                        
                    
                    statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( statuses_to_tags_json_serialisable ) > 0:
                        
                        service_name = service_keys_to_names[ service_key ]
                        
                        service_names_to_statuses_to_tags[ service_name ] = statuses_to_tags_json_serialisable
                        
                        api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                        
                    
                
                if not hide_service_names_tags:
                    
                    metadata_row[ 'service_names_to_statuses_to_tags' ] = service_names_to_statuses_to_tags
                    
                
                metadata_row[ 'service_keys_to_statuses_to_tags' ] = api_service_keys_to_statuses_to_tags
                
                #
                
                service_names_to_statuses_to_tags = {}
                api_service_keys_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_ACTUAL )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    if service_key not in service_keys_to_names:
                        
                        service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                        
                    
                    statuses_to_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( statuses_to_tags_json_serialisable ) > 0:
                        
                        service_name = service_keys_to_names[ service_key ]
                        
                        service_names_to_statuses_to_tags[ service_name ] = statuses_to_tags_json_serialisable
                        
                        api_service_keys_to_statuses_to_tags[ service_key.hex() ] = statuses_to_tags_json_serialisable
                        
                    
                
                if not hide_service_names_tags:
                    
                    metadata_row[ 'service_names_to_statuses_to_display_tags' ] = service_names_to_statuses_to_tags
                    
                
                metadata_row[ 'service_keys_to_statuses_to_display_tags' ] = api_service_keys_to_statuses_to_tags
                
                #
                
                metadata.append( metadata_row )
                
            
        
        body_dict[ 'metadata' ] = metadata
        
        mime = HC.APPLICATION_JSON
        body = json.dumps( body_dict )
        
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
            
            raise HydrusExceptions.NotFoundException( 'Could not find that file!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManageCookies( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_COOKIES )
        
    
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManageCookiesSetCookies( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        cookie_rows = request.parsed_request_args.GetValue( 'cookies', list )
        
        domains_cleared = set()
        domains_set = set()
        
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
                
                ClientNetworkingDomain.AddCookieToSession( session, name, value, domain, path, expires )
                
            
            HG.client_controller.network_engine.session_manager.SetSessionDirty( network_context )
            
        
        if HG.client_controller.new_options.GetBoolean( 'notify_client_api_cookies' ) and len( domains_cleared ) + len( domains_set ) > 0:
            
            domains_cleared = sorted( domains_cleared )
            domains_set = sorted( domains_set )
            
            message = 'Cookies sent from API:'
            
            if len( domains_cleared ) > 0:
                
                message = '{} ({} cleared)'.format( message, ', '.join( domains_cleared ) )
                
            
            if len( domains_set ) > 0:
                
                message = '{} ({} set)'.format( message, ', '.join( domains_set ) )
                
            
            from hydrus.client import ClientThreading
            
            job_key = ClientThreading.JobKey()
            
            job_key.SetVariable( 'popup_text_1', message )
            
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
            
        
        HG.client_controller.network_engine.domain_manager.SetGlobalUserAgent( user_agent )
        
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
        
        mime = HC.APPLICATION_JSON
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
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
        
        if 'hashes' in request.parsed_request_args:
            
            hashes = request.parsed_request_args.GetValue( 'hashes', list, expected_list_type = bytes )
            
            CheckHashLength( hashes )
            
            media_results = HG.client_controller.Read( 'media_results', hashes, sorted = True )
            
        elif 'file_ids' in request.parsed_request_args:
            
            hash_ids = request.parsed_request_args.GetValue( 'file_ids', list, expected_list_type = int )
            
            media_results = HG.client_controller.Read( 'media_results_from_ids', hash_ids, sorted = True )
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'You need hashes or hash_ids for this request!' )
            
        
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
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
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
