import collections
from . import ClientAPI
from . import ClientConstants as CC
from . import ClientImportFileSeeds
from . import ClientSearch
from . import ClientTags
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusServerResources
from . import HydrusTags
import json
import os
import time
import traceback
from twisted.web.static import File as FileResource

local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

LOCAL_BOORU_INT_PARAMS = set()
LOCAL_BOORU_BYTE_PARAMS = { 'share_key', 'hash' }
LOCAL_BOORU_STRING_PARAMS = set()
LOCAL_BOORU_JSON_PARAMS = set()
LOCAL_BOORU_JSON_BYTE_LIST_PARAMS = set()

CLIENT_API_INT_PARAMS = { 'file_id' }
CLIENT_API_BYTE_PARAMS = { 'hash', 'destination_page_key', 'page_key', 'Hydrus-Client-API-Access-Key', 'Hydrus-Client-API-Session-Key' }
CLIENT_API_STRING_PARAMS = { 'name', 'url' }
CLIENT_API_JSON_PARAMS = { 'basic_permissions', 'system_inbox', 'system_archive', 'tags', 'file_ids', 'only_return_identifiers' }
CLIENT_API_JSON_BYTE_LIST_PARAMS = { 'hashes' }

def ParseLocalBooruGETArgs( requests_args ):
    
    args = HydrusNetworking.ParseTwistedRequestGETArgs( requests_args, LOCAL_BOORU_INT_PARAMS, LOCAL_BOORU_BYTE_PARAMS, LOCAL_BOORU_STRING_PARAMS, LOCAL_BOORU_JSON_PARAMS, LOCAL_BOORU_JSON_BYTE_LIST_PARAMS )
    
    return args
    
def ParseClientAPIGETArgs( requests_args ):
    
    args = HydrusNetworking.ParseTwistedRequestGETArgs( requests_args, CLIENT_API_INT_PARAMS, CLIENT_API_BYTE_PARAMS, CLIENT_API_STRING_PARAMS, CLIENT_API_JSON_PARAMS, CLIENT_API_JSON_BYTE_LIST_PARAMS )
    
    return args
    
def ParseClientAPIPOSTByteArgs( args ):
    
    if not isinstance( args, dict ):
        
        raise HydrusExceptions.BadRequestException( 'The given parameter did not seem to be a JSON Object!' )
        
    
    parsed_request_args = HydrusNetworking.ParsedRequestArguments( args )
    
    for var_name in CLIENT_API_BYTE_PARAMS:
        
        if var_name in parsed_request_args:
            
            try:
                
                v = bytes.fromhex( parsed_request_args[ var_name ] )
                
                if len( v ) == 0:
                    
                    del parsed_request_args[ var_name ]
                    
                else:
                    
                    parsed_request_args[ var_name ] = v
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'{}\' as a hex string, but it failed.'.format( var_name ) )
                
            
        
    
    for var_name in CLIENT_API_JSON_BYTE_LIST_PARAMS:
        
        if var_name in parsed_request_args:
            
            try:
                
                v_list = [ bytes.fromhex( hash_hex ) for hash_hex in parsed_request_args[ var_name ] ]
                
                v_list = [ v for v in v_list if len( v ) > 0 ]
                
                if len( v_list ) == 0:
                    
                    del parsed_request_args[ var_name ]
                    
                else:
                    
                    parsed_request_args[ var_name ] = v_list
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'I was expecting to parse \'{}\' as a list of hex strings, but it failed.'.format( var_name ) )
                
            
        
    
    return parsed_request_args
    
def ParseClientAPIPOSTArgs( request ):
    
    request.content.seek( 0 )
    
    if not request.requestHeaders.hasHeader( 'Content-Type' ):
        
        parsed_request_args = HydrusNetworking.ParsedRequestArguments()
        
        total_bytes_read = 0
        
    else:
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
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
            
            parsed_request_args = HydrusNetworking.ParsedRequestArguments()
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
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
            
        
    
    tags = request.parsed_request_args[ 'tags' ]
    system_inbox = request.parsed_request_args[ 'system_inbox' ]
    system_archive = request.parsed_request_args[ 'system_archive' ]
    
    negated_tags = [ tag for tag in tags if tag.startswith( '-' ) ]
    tags = [ tag for tag in tags if not tag.startswith( '-' ) ]
    
    negated_tags = HydrusTags.CleanTags( negated_tags )
    tags = HydrusTags.CleanTags( tags )
    
    request.client_api_permissions.CheckCanSearchTags( tags )
    
    predicates = []
    
    for tag in negated_tags:
        
        predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = tag, inclusive = False ) )
        
    
    for tag in tags:
        
        predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = tag ) )
        
    
    if system_inbox:
        
        predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_SYSTEM_INBOX ) )
        
    elif system_archive:
        
        predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
    
    return predicates
    
class HydrusResourceBooru( HydrusServerResources.HydrusResource ):
    
    def _callbackParseGETArgs( self, request ):
        
        parsed_request_args = ParseLocalBooruGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
    
    def _reportRequestUsed( self, request ):
        
        self._service.ReportRequestUsed()
        
    
    def _checkService( self, request ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    
class HydrusResourceBooruFile( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.parsed_request_args[ 'share_key' ]
        hash = request.parsed_request_args[ 'hash' ]
        
        HG.client_controller.local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = HG.client_controller.local_booru_manager.GetMediaResult( share_key, hash )
        
        mime = media_result.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
class HydrusResourceBooruGallery( HydrusResourceBooru ):
    
    def _threadDoGETJob( self, request ):
        
        # in future, make this a standard frame with a search key that'll load xml or yaml AJAX stuff
        # with file info included, so the page can sort and whatever
        
        share_key = request.parsed_request_args[ 'share_key' ]
        
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
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.parsed_request_args[ 'share_key' ]
        hash = request.parsed_request_args[ 'hash' ]
        
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
        
        if mime in HC.IMAGES:
            
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
    
    def _threadDoGETJob( self, request ):
        
        share_key = request.parsed_request_args[ 'share_key' ]
        hash = request.parsed_request_args[ 'hash' ]
        
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
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_context_mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPI( HydrusServerResources.HydrusResource ):
    
    def _callbackParseGETArgs( self, request ):
        
        parsed_request_args = ParseClientAPIGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        ( parsed_request_args, total_bytes_read ) = ParseClientAPIPOSTArgs( request )
        
        self._reportDataUsed( request, total_bytes_read )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
    
    def _reportRequestUsed( self, request ):
        
        self._service.ReportRequestUsed()
        
    
    def _checkService( self, request ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    
class HydrusResourceClientAPIPermissionsRequest( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request ):
        
        if not ClientAPI.api_request_dialog_open:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'The permission registration dialog is not open. Please open it under "review services" in the hydrus client.' )
            
        
        name = request.parsed_request_args[ 'name' ]
        basic_permissions = request.parsed_request_args[ 'basic_permissions' ]
        
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
    
    def _threadDoGETJob( self, request ):
        
        body_dict = {}
        
        body_dict[ 'version' ] = HC.CLIENT_API_VERSION
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestricted( HydrusResourceClientAPI ):
    
    def _callbackCheckAccountRestrictions( self, request ):
        
        HydrusResourceClientAPI._callbackCheckAccountRestrictions( self, request )
        
        self._CheckAPIPermissions( request )
        
        return request
        
    
    def _callbackEstablishAccountFromHeader( self, request ):
        
        access_key = self._ParseClientAPIAccessKey( request, 'header' )
        
        if access_key is not None:
            
            self._EstablishAPIPermissions( request, access_key )
            
        
        return request
        
    
    def _callbackEstablishAccountFromArgs( self, request ):
        
        if request.client_api_permissions is None:
            
            access_key = self._ParseClientAPIAccessKey( request, 'args' )
            
            if access_key is not None:
                
                self._EstablishAPIPermissions( request, access_key )
                
            
        
        if request.client_api_permissions is None:
            
            raise HydrusExceptions.MissingCredentialsException( 'No access key or session key provided!' )
            
        
        return request
        
    
    def _CheckAPIPermissions( self, request ):
        
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
                
                key = request.parsed_request_args[ name_of_key ]
                
            
        
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
    
    def _CheckAPIPermissions( self, request ):
        
        pass
        
    
class HydrusResourceClientAPIRestrictedAccountSessionKey( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request ):
        
        new_session_key = HG.client_controller.client_api_manager.GenerateSessionKey( request.client_api_permissions.GetAccessKey() )
        
        body_dict = {}
        
        body_dict[ 'session_key' ] = new_session_key.hex()
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAccountVerify( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request ):
        
        api_permissions = request.client_api_permissions
        
        basic_permissions = api_permissions.GetBasicPermissions()
        human_description = api_permissions.ToHumanString()
        
        body_dict = {}
        
        body_dict[ 'basic_permissions' ] = list( basic_permissions ) # set->list for json
        body_dict[ 'human_description' ] = human_description
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddFile( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_FILES )
        
    
    def _threadDoPOSTJob( self, request ):
        
        if not hasattr( request, 'temp_file_info' ):
            
            path = request.parsed_request_args[ 'path' ]
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.BadRequestException( 'Path "{}" does not exist!'.format( path ) )
                
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            HydrusPaths.MirrorFile( path, temp_path )
            
        
        ( os_file_handle, temp_path ) = request.temp_file_info
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( temp_path, file_import_options )
        
        try:
            
            ( status, hash, note ) = file_import_job.DoWork()
            
        except:
            
            status = CC.STATUS_ERROR
            hash = file_import_job.GetHash()
            note = traceback.format_exc()
            
        
        body_dict = {}
        
        body_dict[ 'status' ] = status
        body_dict[ 'hash' ] = hash.hex()
        body_dict[ 'note' ] = note
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTags( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
        
    
class HydrusResourceClientAPIRestrictedAddTagsAddTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoPOSTJob( self, request ):
        
        hashes = set()
        
        if 'hash' in request.parsed_request_args:
            
            hash = request.parsed_request_args[ 'hash' ]
            
            hashes.add( hash )
            
        
        if 'hashes' in request.parsed_request_args:
            
            more_hashes = request.parsed_request_args[ 'hashes' ]
            
            hashes.update( more_hashes )
            
        
        if len( hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'There were no hashes given!' )
            
        
        #
        
        add_siblings_and_parents = True
        
        if 'add_siblings_and_parents' in request.parsed_request_args:
            
            add_siblings_and_parents = request.parsed_request_args[ 'add_siblings_and_parents' ]
            
        
        service_keys_to_content_updates = collections.defaultdict( list )
        
        if 'service_names_to_tags' in request.parsed_request_args:
            
            service_names_to_tags = request.parsed_request_args[ 'service_names_to_tags' ]
            
            for ( service_name, tags ) in service_names_to_tags.items():
                
                try:
                    
                    service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.TAG_SERVICES, service_name )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
                    
                
                tags = HydrusTags.CleanTags( tags )
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                if service_key == CC.LOCAL_TAG_SERVICE_KEY:
                    
                    content_action = HC.CONTENT_UPDATE_ADD
                    
                else:
                    
                    content_action = HC.CONTENT_UPDATE_PEND
                    
                
                if add_siblings_and_parents:
                    
                    siblings_manager = HG.client_controller.tag_siblings_manager
                    
                    tags = siblings_manager.CollapseTags( service_key, tags )
                    
                    parents_manager = HG.client_controller.tag_parents_manager
                    
                    tags = parents_manager.ExpandTags( service_key, tags )
                    
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ) ) for tag in tags ]
                
                service_keys_to_content_updates[ service_key ].extend( content_updates )
                
            
        
        if 'service_names_to_actions_to_tags' in request.parsed_request_args:
            
            service_names_to_actions_to_tags = request.parsed_request_args[ 'service_names_to_actions_to_tags' ]
            
            for ( service_name, actions_to_tags ) in service_names_to_actions_to_tags.items():
                
                try:
                    
                    service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.TAG_SERVICES, service_name )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
                    
                
                for ( content_action, tags ) in actions_to_tags.items():
                    
                    content_action = int( content_action )
                    
                    tags = HydrusTags.CleanTags( tags )
                    
                    if len( tags ) == 0:
                        
                        continue
                        
                    
                    if service_key == CC.LOCAL_TAG_SERVICE_KEY:
                        
                        if content_action not in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            continue
                            
                        
                    else:
                        
                        if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            continue
                            
                        
                    
                    if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ) and add_siblings_and_parents:
                        
                        siblings_manager = HG.client_controller.tag_siblings_manager
                        
                        tags = siblings_manager.CollapseTags( service_key, tags )
                        
                        parents_manager = HG.client_controller.tag_parents_manager
                        
                        tags = parents_manager.ExpandTags( service_key, tags )
                        
                    
                    if content_action == HC.CONTENT_UPDATE_PETITION:
                        
                        if isinstance( tags[0], str ):
                            
                            tags_and_reasons = [ ( tag, 'Petitioned from API' ) for tag in tags ]
                            
                        else:
                            
                            tags_and_reasons = tags
                            
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ), reason = reason ) for ( tag, reason ) in tags_and_reasons ]
                        
                    else:
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes ) ) for tag in tags ]
                        
                    
                    service_keys_to_content_updates[ service_key ].extend( content_updates )
                    
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTagsGetTagServices( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request ):
        
        local_tags = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
        tag_repos = HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        body_dict = {}
        
        body_dict[ 'local_tags' ] = [ service.GetName() for service in local_tags ]
        body_dict[ 'tag_repositories' ] = [ service.GetName() for service in tag_repos ]
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddTagsCleanTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request ):
        
        tags = request.parsed_request_args[ 'tags' ]
        
        tags = list( HydrusTags.CleanTags( tags ) )
        
        tags = HydrusTags.SortNumericTags( tags )
        
        body_dict = {}
        
        body_dict[ 'tags' ] = tags
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLs( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_URLS )
        
    
class HydrusResourceClientAPIRestrictedAddURLsAssociateURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request ):
        
        urls_to_add = []
        
        if 'url_to_add' in request.parsed_request_args:
            
            url = request.parsed_request_args[ 'url_to_add' ]
            
            if not isinstance( url, str ):
                
                raise HydrusExceptions.BadRequestException( 'Did not understand the given URL "{}"!'.format( url ) )
                
            
            urls_to_add.append( url )
            
        
        if 'urls_to_add' in request.parsed_request_args:
            
            urls = request.parsed_request_args[ 'urls_to_add' ]
            
            if not isinstance( urls, list ):
                
                raise HydrusExceptions.BadRequestException( 'Did not understand the given URLs!' )
                
            
            for url in urls:
                
                if not isinstance( url, str ):
                    
                    continue
                    
                
                urls_to_add.append( url )
                
            
        
        urls_to_delete = []
        
        if 'url_to_delete' in request.parsed_request_args:
            
            url = request.parsed_request_args[ 'url_to_delete' ]
            
            if not isinstance( url, str ):
                
                raise HydrusExceptions.BadRequestException( 'Did not understand the given URL "{}"!'.format( url ) )
                
            
            urls_to_delete.append( url )
            
        
        if 'urls_to_delete' in request.parsed_request_args:
            
            urls = request.parsed_request_args[ 'urls_to_delete' ]
            
            if not isinstance( urls, list ):
                
                raise HydrusExceptions.BadRequestException( 'Did not understand the given URLs!' )
                
            
            for url in urls:
                
                if not isinstance( url, str ):
                    
                    continue
                    
                
                urls_to_delete.append( url )
                
            
        
        applicable_hashes = []
        
        if 'hash' in request.parsed_request_args:
            
            applicable_hashes.append( request.parsed_request_args[ 'hash' ] )
            
        
        if 'hashes' in request.parsed_request_args:
            
            applicable_hashes.extend( request.parsed_request_args[ 'hashes' ] )
            
        
        if len( urls_to_add ) == 0 and len( urls_to_delete ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any URLs to add!' )
            
        
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
    
    def _threadDoGETJob( self, request ):
        
        url = request.parsed_request_args[ 'url' ]
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        url_statuses = HG.client_controller.Read( 'url_statuses', normalised_url )
        
        json_happy_url_statuses = []
        
        for ( status, hash, note ) in url_statuses:
            
            d = {}
            
            d[ 'status' ] = status
            d[ 'hash' ] = hash.hex()
            d[ 'note' ] = note
            
            json_happy_url_statuses.append( d )
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_file_statuses' : json_happy_url_statuses }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsGetURLInfo( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request ):
        
        url = request.parsed_request_args[ 'url' ]
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
        
        body_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsImportURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request ):
        
        url = request.parsed_request_args[ 'url' ]
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        service_keys_to_tags = None
        
        if 'service_names_to_tags' in request.parsed_request_args:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
            
            service_names_to_tags = request.parsed_request_args[ 'service_names_to_tags' ]
            
            for ( service_name, tags ) in service_names_to_tags.items():
                
                try:
                    
                    service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.TAG_SERVICES, service_name )
                    
                except:
                    
                    raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
                    
                
                tags = HydrusTags.CleanTags( tags )
                
                if len( tags ) == 0:
                    
                    continue
                    
                
                service_keys_to_tags[ service_key ] = tags
                
            
        
        destination_page_name = None
        
        if 'destination_page_name' in request.parsed_request_args:
            
            destination_page_name = request.parsed_request_args[ 'destination_page_name' ]
            
            if not isinstance( destination_page_name, str ):
                
                raise HydrusExceptions.BadRequestException( '"destination_page_name" did not seem to be a string!' )
                
            
        
        destination_page_key = None
        
        if 'destination_page_key' in request.parsed_request_args:
            
            destination_page_key = request.parsed_request_args[ 'destination_page_key' ]
            
            if not isinstance( destination_page_key, bytes ):
                
                raise HydrusExceptions.BadRequestException( '"destination_page_key" did not seem to be a hex string!' )
                
            
        
        show_destination_page = False
        
        if 'show_destination_page' in request.parsed_request_args:
            
            show_destination_page = request.parsed_request_args[ 'show_destination_page' ]
            
            if not isinstance( show_destination_page, bool ):
                
                raise HydrusExceptions.BadRequestException( '"show_destination_page" did not seem to be a boolean!' )
                
            
        
        def do_it():
            
            return HG.client_controller.gui.ImportURLFromAPI( url, service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page )
            
        
        try:
            
            ( normalised_url, result_text ) = HG.client_controller.CallBlockingToWX( HG.client_controller.gui, do_it )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        time.sleep( 0.05 ) # yield and give the ui time to catch up with new URL pubsubs in case this is being spammed
        
        body_dict = { 'human_result_text' : result_text, 'normalised_url' : normalised_url }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFiles( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
class HydrusResourceClientAPIRestrictedGetFilesSearchFiles( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request ):
        
        predicates = ParseClientAPISearchPredicates( request )
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, predicates = predicates )
        
        hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context )
        
        request.client_api_permissions.SetLastSearchResults( hash_ids )
        
        body_dict = { 'file_ids' : list( hash_ids ) }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesGetFile( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request ):
        
        try:
            
            if 'file_id' in request.parsed_request_args:
                
                file_id = request.parsed_request_args[ 'file_id' ]
                
                request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
                
                ( media_result, ) = HG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
                
            elif 'hash' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hash = request.parsed_request_args[ 'hash' ]
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
        try:
            
            hash = media_result.GetHash()
            mime = media_result.GetMime()
            
            path = HG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that file!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesFileMetadata( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request ):
        
        only_return_identifiers = False
        
        if 'only_return_identifiers' in request.parsed_request_args:
            
            only_return_identifiers = request.parsed_request_args[ 'only_return_identifiers' ]
            
        
        try:
            
            if 'file_ids' in request.parsed_request_args:
                
                file_ids = request.parsed_request_args[ 'file_ids' ]
                
                request.client_api_permissions.CheckPermissionToSeeFiles( file_ids )
                
                if only_return_identifiers:
                    
                    file_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hash_ids = file_ids )
                    
                else:
                    
                    media_results = HG.client_controller.Read( 'media_results_from_ids', file_ids )
                    
                
            elif 'hashes' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hashes = request.parsed_request_args[ 'hashes' ]
                
                if only_return_identifiers:
                    
                    file_ids_to_hashes = HG.client_controller.Read( 'hash_ids_to_hashes', hashes = hashes )
                    
                else:
                    
                    media_results = HG.client_controller.Read( 'media_results', hashes )
                    
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_ids or hashes parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
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
                metadata_row[ 'mime' ] = HC.mime_string_lookup[ file_info_manager.mime ]
                metadata_row[ 'width' ] = file_info_manager.width
                metadata_row[ 'height' ] = file_info_manager.height
                metadata_row[ 'duration' ] = file_info_manager.duration
                metadata_row[ 'num_frames' ] = file_info_manager.num_frames
                metadata_row[ 'num_words' ] = file_info_manager.num_words
                
                tags_manager = media_result.GetTagsManager()
                
                service_names_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags()
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    if service_key not in service_keys_to_names:
                        
                        service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                        
                    
                    service_name = service_keys_to_names[ service_key ]
                    
                    service_names_to_statuses_to_tags[ service_name ] = { str( status ) : list( tags ) for ( status, tags ) in statuses_to_tags.items() }
                    
                
                metadata_row[ 'service_names_to_statuses_to_tags' ] = service_names_to_statuses_to_tags
                
                metadata.append( metadata_row )
                
            
        
        body_dict[ 'metadata' ] = metadata
        
        mime = HC.APPLICATION_JSON
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetFilesGetThumbnail( HydrusResourceClientAPIRestrictedGetFiles ):
    
    def _threadDoGETJob( self, request ):
        
        try:
            
            if 'file_id' in request.parsed_request_args:
                
                file_id = request.parsed_request_args[ 'file_id' ]
                
                request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
                
                ( media_result, ) = HG.client_controller.Read( 'media_results_from_ids', ( file_id, ) )
                
            elif 'hash' in request.parsed_request_args:
                
                request.client_api_permissions.CheckCanSeeAllFiles()
                
                hash = request.parsed_request_args[ 'hash' ]
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Please include a file_id or hash parameter!' )
                
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'One or more of those file identifiers was missing!' )
            
        
        try:
            
            path = HG.client_controller.client_files_manager.GetThumbnailPath( media_result )
            
        except HydrusExceptions.FileMissingException:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that file!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManagePages( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES )
        
    
class HydrusResourceClientAPIRestrictedManagePagesFocusPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request ):
        
        def do_it( page_key ):
            
            return HG.client_controller.gui.ShowPage( page_key )
            
        
        if 'page_key' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'No "page_key" given!' )
            
        
        page_key = request.parsed_request_args[ 'page_key' ]
        
        if not isinstance( page_key, bytes ):
            
            raise HydrusExceptions.BadRequestException( '"page_key" did not seem to be a hex string!' )
            
        
        try:
            
            HG.client_controller.CallBlockingToWX( HG.client_controller.gui, do_it, page_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManagePagesGetPages( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request ):
        
        def do_it():
            
            return HG.client_controller.gui.GetCurrentSessionPageInfoDict()
            
        
        page_info_dict = HG.client_controller.CallBlockingToWX( HG.client_controller.gui, do_it )
        
        body_dict = { 'pages' : page_info_dict }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
