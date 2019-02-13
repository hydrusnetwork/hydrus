from . import ClientAPI
from . import ClientConstants as CC
from . import ClientFiles
from . import ClientImportFileSeeds
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusServerResources
import json
import os
import traceback
from twisted.web.static import File as FileResource

local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

LOCAL_BOORU_INT_PARAMS = set()
LOCAL_BOORU_BYTE_PARAMS = { 'share_key', 'hash' }
LOCAL_BOORU_STRING_PARAMS = set()
LOCAL_BOORU_JSON_PARAMS = set()

CLIENT_API_INT_PARAMS = set()
CLIENT_API_BYTE_PARAMS = set()
CLIENT_API_STRING_PARAMS = { 'name', 'url' }
CLIENT_API_JSON_PARAMS = { 'basic_permissions' }

def ParseLocalBooruGETArgs( requests_args ):
    
    args = HydrusNetworking.ParseTwistedRequestGETArgs( requests_args, LOCAL_BOORU_INT_PARAMS, LOCAL_BOORU_BYTE_PARAMS, LOCAL_BOORU_STRING_PARAMS, LOCAL_BOORU_JSON_PARAMS )
    
    return args
    
def ParseClientAPIGETArgs( requests_args ):
    
    args = HydrusNetworking.ParseTwistedRequestGETArgs( requests_args, CLIENT_API_INT_PARAMS, CLIENT_API_BYTE_PARAMS, CLIENT_API_STRING_PARAMS, CLIENT_API_JSON_PARAMS )
    
    return args
    
def ParseClientAPIPOSTArgs( request ):
    
    # this is a mangled dupe of the hydrus parsing stuff. I should refactor it all to something neater and pull out the HydrusNetwork.ParseNetworkBytesToHydrusArgs
    
    request.content.seek( 0 )
    
    if not request.requestHeaders.hasHeader( 'Content-Type' ):
        
        hydrus_args = {}
        
        total_bytes_read = 0
        
    else:
        
        content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
        
        content_type = content_types[0]
        
        try:
            
            mime = HC.mime_enum_lookup[ content_type ]
            
        except:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Did not recognise Content-Type header!' )
            
        
        total_bytes_read = 0
        
        if mime == HC.APPLICATION_JSON:
            
            json_bytes = request.content.read()
            
            total_bytes_read += len( json_bytes )
            
            json_string = str( json_bytes, 'utf-8' )
            
            hydrus_args = json.loads( json_string )
            
        else:
            
            hydrus_args = {}
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            with open( temp_path, 'wb' ) as f:
                
                for block in HydrusPaths.ReadFileLikeAsBlocks( request.content ): 
                    
                    f.write( block )
                    
                    total_bytes_read += len( block )
                    
                
            
        
    
    return ( hydrus_args, total_bytes_read )
    
class HydrusResourceBooru( HydrusServerResources.HydrusResource ):
    
    def _callbackParseGETArgs( self, request ):
        
        hydrus_args = ParseLocalBooruGETArgs( request.args )
        
        request.hydrus_args = hydrus_args
        
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
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
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
        
        share_key = request.hydrus_args[ 'share_key' ]
        
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
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
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
        
        share_key = request.hydrus_args[ 'share_key' ]
        hash = request.hydrus_args[ 'hash' ]
        
        local_booru_manager = HG.client_controller.local_booru_manager
        
        local_booru_manager.CheckFileAuthorised( share_key, hash )
        
        media_result = local_booru_manager.GetMediaResult( share_key, hash )
        
        mime = media_result.GetMime()
        
        response_context_mime = HC.IMAGE_PNG
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFullSizeThumbnailPath( hash )
            
            response_context_mime = HC.APPLICATION_UNKNOWN
            
        elif mime in HC.AUDIO:
            
            path = os.path.join( HC.STATIC_DIR, 'audio.png' )
            
        elif mime == HC.APPLICATION_PDF:
            
            path = os.path.join( HC.STATIC_DIR, 'pdf.png' )
            
        else:
            
            path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = response_context_mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPI( HydrusServerResources.HydrusResource ):
    
    def _callbackParseGETArgs( self, request ):
        
        hydrus_args = ParseClientAPIGETArgs( request.args )
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        ( hydrus_args, total_bytes_read ) = ParseClientAPIPOSTArgs( request )
        
        self._reportDataUsed( request, total_bytes_read )
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _ParseClientAPIAccessKey( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Hydrus-Client-API-Access-Key' ):
            
            raise HydrusExceptions.MissingCredentialsException( 'No Hydrus-Client-API-Access-Key header!' )
            
        
        access_key_texts = request.requestHeaders.getRawHeaders( 'Hydrus-Client-API-Access-Key' )
        
        access_key_text = access_key_texts[0]
        
        try:
            
            access_key = bytes.fromhex( access_key_text )
            
        except:
            
            raise Exception( 'Problem parsing api access key!' )
            
        
        return access_key
        
    
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
            
        
        name = request.hydrus_args[ 'name' ]
        basic_permissions = request.hydrus_args[ 'basic_permissions' ]
        
        basic_permissions = [ int( value ) for value in basic_permissions ]
        
        api_permissions = ClientAPI.APIPermissions( name = name, basic_permissions = basic_permissions )
        
        ClientAPI.last_api_permissions_request = api_permissions
        
        access_key = api_permissions.GetAccessKey()
        
        body_dict = {}
        
        body_dict[ 'access_key' ] = access_key.hex()
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIVerify( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._ParseClientAPIAccessKey( request )
        
        client_api_manager = HG.client_controller.client_api_manager
        
        try:
            
            api_permissions = client_api_manager.GetPermissions( access_key )
            
            basic_permissions = api_permissions.GetBasicPermissions()
            human_description = api_permissions.ToHumanString()
            
            body_dict = {}
            
            body_dict[ 'basic_permissions' ] = list( basic_permissions ) # set->list for json
            body_dict[ 'human_description' ] = human_description
            
            body = json.dumps( body_dict )
            
            response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Could not find that access key!' )
            
        
        return response_context
        
    
class HydrusResourceClientAPIVersion( HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request ):
        
        body_dict = {}
        
        body_dict[ 'version' ] = HC.CLIENT_API_VERSION
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestricted( HydrusResourceClientAPI ):
    
    def _callbackCheckRestrictions( self, request ):
        
        HydrusResourceClientAPI._callbackCheckRestrictions( self, request )
        
        self._EstablishAPIPermissions( request )
        
        self._CheckAPIPermissions( request )
        
        return request
        
    
    def _CheckAPIPermissions( self, request ):
        
        raise NotImplementedError()
        
    
    def _EstablishAPIPermissions( self, request ):
        
        access_key = self._ParseClientAPIAccessKey( request )
        
        try:
            
            api_permissions = HG.client_controller.client_api_manager.GetPermissions( access_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Could not find that access key in the list of permissions!' )
            
        
        request.client_api_permissions = api_permissions
        
    
class HydrusResourceClientAPIRestrictedAddFile( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_FILES )
        
    
    def _threadDoPOSTJob( self, request ):
        
        if not hasattr( request, 'temp_file_info' ):
            
            path = request.hydrus_args[ 'path' ]
            
            if not os.path.exists( path ):
                
                raise HydrusExceptions.InsufficientCredentialsException( 'Path "{}" does not exist!'.format( path ) )
                
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            request.temp_file_info = ( os_file_handle, temp_path )
            
            HydrusPaths.MirrorFile( path, temp_path )
            
        
        ( os_file_handle, temp_path ) = request.temp_file_info
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( temp_path, file_import_options )
        
        try:
            
            ( status, hash, note ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
            
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
        
        # grab hash and tags from POST args
        
        # do it to db
        
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
        
    
class HydrusResourceClientAPIRestrictedAddURLs( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_URLS )
        
    
class HydrusResourceClientAPIRestrictedAddURLsGetURLFiles( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request ):
        
        url = request.hydrus_args[ 'url' ]
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
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
        
        url = request.hydrus_args[ 'url' ]
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
        
        body_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsImportURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request ):
        
        url = request.hydrus_args[ 'url' ]
        
        service_keys_to_tags = {}
        
        if 'service_names_to_tags' in request.hydrus_args:
            
            request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
            
            service_names_to_tags = request.hydrus_args
            
            for ( service_name, tags ) in service_names_to_tags.items():
                
                try:
                    
                    service_key = HG.client_controller.service_manager.GetServiceKeyFromName( HC.TAG_SERVICES, service_name )
                    
                except:
                    
                    raise KeyError( 'Could not find the service "{}"!'.format( service_name ) )
                    
                
                service_keys_to_tags[ service_key ] = tags
                
            
        
        gui = HG.client_controller.gui
        
        ( normalised_url, result_text ) = HG.client_controller.CallBlockingToWX( gui, gui.ImportURLFromAPI, url, service_keys_to_tags )
        
        body_dict = { 'human_result_text' : result_text, 'normalised_url' : normalised_url }
        
        body = json.dumps( body_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedSearchFiles( HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
class HydrusResourceClientAPIRestrictedSearchFilesDoSearch( HydrusResourceClientAPIRestrictedSearchFiles ):
    
    def _threadDoGETJob( self, request ):
        
        # get tags from GET args
        
        tags = { 'blah' }
        
        # maybe checkcansearchtags
        request.client_api_permissions.CanSearchTags( tags )
        
        # do the search, get file_ids back
        
        # turn media results into json/xml result. maybe start with json to keep it simple
        
        mime = HC.APPLICATION_JSON
        body = 'blah'
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedSearchFilesGetFile( HydrusResourceClientAPIRestrictedSearchFiles ):
    
    def _threadDoGETJob( self, request ):
        
        file_id = request.hydrus_args[ 'file_id' ]
        
        request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
        
        media_result = 'blah' # get it from controller
        
        mime = media_result.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedSearchFilesGetMetadata( HydrusResourceClientAPIRestrictedSearchFiles ):
    
    def _threadDoGETJob( self, request ):
        
        file_ids = request.hydrus_args[ 'file_ids' ]
        
        request.client_api_permissions.CheckPermissionToSeeFiles( file_ids )
        
        media_results = 'blah' # get it from controller
        
        # turn media results into json/xml result. maybe start with json to keep it simple
        
        mime = HC.APPLICATION_JSON
        body = 'blah'
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedSearchFilesGetThumbnail( HydrusResourceClientAPIRestrictedSearchFiles ):
    
    def _threadDoGETJob( self, request ):
        
        file_id = request.hydrus_args[ 'file_id' ]
        
        request.client_api_permissions.CheckPermissionToSeeFiles( ( file_id, ) )
        
        media_result = 'blah' # get it from controller
        
        mime = media_result.GetMime() # jpg or png
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
