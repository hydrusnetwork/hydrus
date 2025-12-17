import collections
import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTags
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources
from hydrus.client.search import ClientSearchAutocomplete
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext


class HydrusResourceClientAPIRestrictedAddTags( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
        
    

class HydrusResourceClientAPIRestrictedAddTagsAddTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        #
        
        override_previously_deleted_mappings = request.parsed_request_args.GetValue( 'override_previously_deleted_mappings', bool, default_value = True )
        create_new_deleted_mappings = request.parsed_request_args.GetValue( 'create_new_deleted_mappings', bool, default_value = True )
        
        service_keys_to_actions_to_tags = None
        
        if 'service_keys_to_tags' in request.parsed_request_args:
            
            service_keys_to_tags = request.parsed_request_args.GetValue( 'service_keys_to_tags', dict )
            
            service_keys_to_actions_to_tags = {}
            
            for ( service_key, tags ) in service_keys_to_tags.items():
                
                service = ClientLocalServerCore.CheckTagService( service_key )
                
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
                
                service = ClientLocalServerCore.CheckTagService( service_key )
                
                HydrusNetworkVariableHandling.TestVariableType( 'actions_to_tags', parsed_actions_to_tags, dict )
                
                actions_to_tags = {}
                
                for ( parsed_content_action, tags ) in parsed_actions_to_tags.items():
                    
                    HydrusNetworkVariableHandling.TestVariableType( 'parsed_content_action', parsed_content_action, str )
                    
                    try:
                        
                        content_action = int( parsed_content_action )
                        
                    except:
                        
                        raise HydrusExceptions.BadRequestException( 'Sorry, got an action, "{}", that was not an integer!'.format( parsed_content_action ) )
                        
                    
                    if service.GetServiceType() == HC.LOCAL_TAG:
                        
                        if content_action not in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            raise HydrusExceptions.BadRequestException( 'Sorry, you submitted a content action of "{}" for service "{}", but you can only add/delete on a local tag domain!'.format( parsed_content_action, service_key.hex() ) )
                            
                        
                    else:
                        
                        if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ):
                            
                            raise HydrusExceptions.BadRequestException( 'Sorry, you submitted a content action of "{}" for service "{}", but you cannot add/delete on a remote tag repository!'.format( parsed_content_action, service_key.hex() ) )
                            
                        
                    
                    HydrusNetworkVariableHandling.TestVariableType( 'tags in actions_to_tags', tags, list ) # do not test for str here, it can be reason tuples!
                    
                    actions_to_tags[ content_action ] = tags
                    
                
                if len( actions_to_tags ) == 0:
                    
                    continue
                    
                
                service_keys_to_actions_to_tags[ service_key ] = actions_to_tags
                
            
        
        if service_keys_to_actions_to_tags is None:
            
            raise HydrusExceptions.BadRequestException( 'Need a service_keys_to_tags or service_keys_to_actions_to_tags parameter!' )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        media_results = []
        
        if not override_previously_deleted_mappings or not create_new_deleted_mappings:
            
            media_results = CG.client_controller.Read( 'media_results', hashes )
            
        
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
                        
                    elif HydrusLists.IsAListLikeCollection( tag_item ) and len( tag_item ) == 2:
                        
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
                    
                
                content_updates = []
                
                for tag in content_update_tags:
                    
                    hashes_for_this_package = hashes
                    
                    if content_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ) and not override_previously_deleted_mappings:
                        
                        hashes_for_this_package = ClientImportOptions.FilterNotPreviouslyDeletedTagHashes( service_key, media_results, tag )
                        
                    
                    if content_action in ( HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PETITION ) and not create_new_deleted_mappings:
                        
                        hashes_for_this_package = ClientImportOptions.FilterCurrentTagHashes( service_key, media_results, tag )
                        
                    
                    if content_action == HC.CONTENT_UPDATE_PETITION:
                        
                        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes_for_this_package ), reason = tags_to_reasons[ tag ] )
                        
                    else:
                        
                        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, hashes_for_this_package ) )
                        
                    
                    content_updates.append( content_update )
                    
                
                content_update_package.AddContentUpdates( service_key, content_updates )
                
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddTagsSearchTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # this doesn't need 'add tags' atm. I was going to add it, but I'm not sure it is actually appropriate
        # this thing probably should have been in search files space, but whatever
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES )
        
    
    def _GetParsedAutocompleteText( self, search, tag_service_key ) -> ClientSearchAutocomplete.ParsedAutocompleteText:
        
        tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
        
        collapse_search_characters = True
        
        parsed_autocomplete_text = ClientSearchAutocomplete.ParsedAutocompleteText( search, tag_autocomplete_options, collapse_search_characters )
        
        parsed_autocomplete_text.SetInclusive( True )
        
        return parsed_autocomplete_text
        
    
    def _GetTagMatches( self, request: HydrusServerRequest.HydrusRequest, tag_display_type: int, tag_service_key: bytes, parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText ) -> list[ ClientSearchPredicate.Predicate ]:
        
        matches = []
        
        if parsed_autocomplete_text.IsAcceptableForTagSearches():
            
            tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key )
            
            autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
            
            location_context = ClientLocalServerCore.ParseLocationContext( request, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
            
            file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context )
            
            job_status = ClientThreading.JobStatus( cancellable = True )
            
            request.disconnect_callables.append( job_status.Cancel )
            
            search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
            
            predicates = CG.client_controller.Read( 'autocomplete_predicates', tag_display_type, file_search_context, search_text = autocomplete_search_text, job_status = job_status, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
            
            display_tag_service_key = tag_context.display_service_key
            
            matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( display_tag_service_key, autocomplete_search_text, predicates )
            
            matches = ClientSearchPredicate.SortPredicates( matches )
            
        
        return matches
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        search = request.parsed_request_args.GetValue( 'search', str )
        
        tag_display_type_str = request.parsed_request_args.GetValue( 'tag_display_type', str, default_value = 'storage' )
        
        tag_display_type = ClientTags.TAG_DISPLAY_STORAGE if tag_display_type_str == 'storage' else ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL
        
        tag_service_key = ClientLocalServerCore.ParseTagServiceKey( request )
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText( search, tag_service_key )
        
        matches = self._GetTagMatches( request, tag_display_type, tag_service_key, parsed_autocomplete_text )
        
        matches = request.client_api_permissions.FilterTagPredicateResponse( matches )
        
        body_dict = {}
        
        # TODO: Ok so we could add sibling/parent info here if the tag display type is storage, or in both cases. probably only if client asks for it
        
        tags = [ { 'value' : match.GetValue(), 'count' : match.GetCount().GetMinCount() } for match in matches ]
        
        body_dict[ 'tags' ] = tags
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddTagsGetTagSiblingsParents( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tags = request.parsed_request_args.GetValue( 'tags', list, expected_list_type = str )
        
        ClientLocalServerCore.CheckTags( tags )
        
        tags = HydrusTags.CleanTags( tags )
        
        tags_to_service_keys_to_siblings_and_parents = CG.client_controller.Read( 'tag_siblings_and_parents_lookup', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, tags )
        
        tags_dict = {}
        
        for ( tag, service_keys_to_siblings_parents ) in tags_to_service_keys_to_siblings_and_parents.items():
            
            tag_dict = {}
            
            for ( service_key, siblings_parents ) in service_keys_to_siblings_parents.items():
                
                tag_dict[ service_key.hex() ] = {
                    'siblings': list( siblings_parents[0] ),
                    'ideal_tag': siblings_parents[1],
                    'descendants': list( siblings_parents[2] ),
                    'ancestors': list( siblings_parents[3] )
                }
                
            
            tags_dict[ tag ] = tag_dict
            
        
        body_dict = {
            'tags' : tags_dict,
            'services' : ClientLocalServerCore.GetServicesDict()
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAddTagsCleanTags( HydrusResourceClientAPIRestrictedAddTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tags = request.parsed_request_args.GetValue( 'tags', list, expected_list_type = str )
        
        tags = list( HydrusTags.CleanTags( tags ) )
        
        tags = HydrusTags.SortNumericTags( tags )
        
        body_dict = {
            'tags' : tags
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
