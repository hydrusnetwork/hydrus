import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.importing import ClientImportFiles
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedAddURLs( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_URLS )
        
    

class HydrusResourceClientAPIRestrictedAddURLsAssociateURL( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        normalise_urls = request.parsed_request_args.GetValue( 'normalise_urls', bool, default_value = True )
        
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
            
            urls_to_delete.extend( urls )
            
        
        domain_manager = CG.client_controller.network_engine.domain_manager
        
        if normalise_urls:
            
            try:
                
                urls_to_add = [ domain_manager.NormaliseURL( url ) for url in urls_to_add ]
                
            except HydrusExceptions.URLClassException as e:
                
                raise HydrusExceptions.BadRequestException( e )
                
            
        
        if len( urls_to_add ) == 0 and len( urls_to_delete ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any URLs to add or delete!' )
            
        
        applicable_hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( applicable_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the urls to!' )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        if len( urls_to_add ) > 0:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( urls_to_add, applicable_hashes ) )
            
            content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
            
        
        if len( urls_to_delete ) > 0:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( urls_to_delete, applicable_hashes ) )
            
            content_update_package.AddContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddURLsGetURLFiles( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        url = request.parsed_request_args.GetValue( 'url', str )
        
        do_file_system_check = request.parsed_request_args.GetValue( 'doublecheck_file_system', bool, default_value = False )
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        url_statuses = CG.client_controller.Read( 'url_statuses', normalised_url )
        
        json_happy_url_statuses = []
        
        we_only_saw_successful = True
        
        for file_import_status in url_statuses:
            
            if do_file_system_check:
                
                file_import_status = ClientImportFiles.CheckFileImportStatus( file_import_status )
                
            
            d = {
                'status': file_import_status.status,
                'hash': HydrusData.BytesToNoneOrHex( file_import_status.hash ),
                'note': file_import_status.note
            }
            
            json_happy_url_statuses.append( d )
            
            if file_import_status.status not in CC.SUCCESSFUL_IMPORT_STATES:
                
                we_only_saw_successful = False
                
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_file_statuses' : json_happy_url_statuses }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        if we_only_saw_successful:
            
            # not likely to change much, so no worries about reducing overhead here
            response_context.SetMaxAge( 30 )
            
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAddURLsGetURLInfo( HydrusResourceClientAPIRestrictedAddURLs ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        url = request.parsed_request_args.GetValue( 'url', str )
        
        if url == '':
            
            raise HydrusExceptions.BadRequestException( 'Given URL was empty!' )
            
        
        try:
            
            normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
            ( url_type, match_name, can_parse, cannot_parse_reason ) = CG.client_controller.network_engine.domain_manager.GetURLParseCapability( normalised_url )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        body_dict = { 'normalised_url' : normalised_url, 'url_type' : url_type, 'url_type_string' : HC.url_type_string_lookup[ url_type ], 'match_name' : match_name, 'can_parse' : can_parse }
        
        if not can_parse:
            
            body_dict[ 'cannot_parse_reason' ] = cannot_parse_reason
            
        
        try:
            
            url_to_fetch = CG.client_controller.network_engine.domain_manager.GetURLToFetch( normalised_url )
            
        except Exception as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        body_dict[ 'request_url' ] = url_to_fetch
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        # max age of ten minutes here
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body, max_age = 600 )
        
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
                
                ClientLocalServerCore.CheckTagService( service_key )
                
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
        
        destination_location_context = ClientLocalServerCore.ParseLocalFileDomainLocationContext( request )
        
        def do_it():
            
            return CG.client_controller.gui.ImportURLFromAPI( url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page, destination_location_context )
            
        
        try:
            
            ( normalised_url, result_text ) = CG.client_controller.CallBlockingToQt( CG.client_controller.gui, do_it )
            
        except HydrusExceptions.URLClassException as e:
            
            raise HydrusExceptions.BadRequestException( e )
            
        
        time.sleep( 0.05 ) # yield and give the ui time to catch up with new URL pubsubs in case this is being spammed
        
        body_dict = { 'human_result_text' : result_text, 'normalised_url' : normalised_url }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
