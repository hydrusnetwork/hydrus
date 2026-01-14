import warnings

from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources


class HydrusResourceClientAPIRestrictedManageCookies( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_HEADERS )
        
    

class HydrusResourceClientAPIRestrictedManageCookiesGetCookies( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        domain = request.parsed_request_args.GetValue( 'domain', str )
        
        if '.' not in domain:
            
            raise HydrusExceptions.BadRequestException( 'The value "{}" does not seem to be a domain!'.format( domain ) )
            
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
        session = CG.client_controller.network_engine.session_manager.GetSession( network_context )
        
        body_cookies_list = []
        
        for cookie in session.cookies:
            
            name = cookie.name
            value = cookie.value
            domain = cookie.domain
            path = cookie.path
            expires = cookie.expires
            
            body_cookies_list.append( [ name, value, domain, path, expires ] )
            
        
        body_dict = { 'cookies' : body_cookies_list }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
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
            
            session = CG.client_controller.network_engine.session_manager.GetSession( network_context )
            
            if value is None:
                
                domains_cleared.add( domain )
                
                session.cookies.clear( domain, path, name )
                
            else:
                
                domains_set.add( domain )
                
                ClientNetworkingFunctions.AddCookieToSession( session, name, value, domain, path, expires )
                
            
            CG.client_controller.network_engine.session_manager.SetSessionDirty( network_context )
            
        
        if CG.client_controller.new_options.GetBoolean( 'notify_client_api_cookies' ) and len( domains_cleared ) + len( domains_set ) > 0:
            
            domains_cleared = sorted( domains_cleared )
            domains_set = sorted( domains_set )
            
            message = 'Cookies sent from API:'
            
            if len( domains_cleared ) > 0:
                
                message = '{} ({} cleared)'.format( message, ', '.join( domains_cleared ) )
                
            
            if len( domains_set ) > 0:
                
                message = '{} ({} set)'.format( message, ', '.join( domains_set ) )
                
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusText( message )
            
            job_status.FinishAndDismiss( 5 )
            
            CG.client_controller.pub( 'message', job_status )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageCookiesSetUserAgent( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        warnings.warn(
            'Hey, the the "set_user_agent" command is deprecated, but a Client API script you are using it just called it! That script may stop working in v668 if it is not updated to use the newer "set_headers" command!',
            FutureWarning,
            stacklevel = 1
        )
        
        user_agent = request.parsed_request_args.GetValue( 'user-agent', str )
        
        if user_agent == '':
            
            from hydrus.client import ClientDefaults
            
            user_agent = ClientDefaults.DEFAULT_USER_AGENT
            
        
        CG.client_controller.network_engine.domain_manager.SetCustomHeader( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, 'User-Agent', value = user_agent )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

def GenerateNetworkContextFromRequest( request: HydrusServerRequest.HydrusRequest ):
    
    domain = request.parsed_request_args.GetValueOrNone( 'domain', str )
    
    if domain is None:
        
        network_context = ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT
        
    else:
        
        if '.' not in domain:
            
            raise HydrusExceptions.BadRequestException( 'The value "{}" does not seem to be a domain!'.format( domain ) )
            
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
        
    
    return network_context
    

def RenderNetworkContextToJSONObject( network_context: ClientNetworkingContexts.NetworkContext ) -> dict:
    
    result = {
        'type': network_context.context_type
    }
    
    if isinstance( network_context.context_data, bytes ):
        
        result[ 'data' ] = network_context.context_data.hex()
        
    elif network_context.context_data is None or isinstance( network_context.context_data, str ):
        
        result[ 'data' ] = network_context.context_data
        
    else:
        
        result[ 'data' ] = repr( network_context.context_data )
        
    
    return result
    

class HydrusResourceClientAPIRestrictedManageCookiesGetHeaders( HydrusResourceClientAPIRestrictedManageCookies ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        network_context = GenerateNetworkContextFromRequest( request )
        
        ncs_to_header_dicts = CG.client_controller.network_engine.domain_manager.GetNetworkContextsToCustomHeaderDicts()
        
        body_dict = {
            'network_context': RenderNetworkContextToJSONObject( network_context )
        }
        
        headers_dict = ncs_to_header_dicts.get( network_context, {} )
        
        body_headers_dict = {}
        
        for ( key, ( value, approved, reason ) ) in headers_dict.items():
            
            body_headers_dict[ key ] = {
                'value' : value,
                'approved' : ClientNetworkingDomain.valid_str_lookup[ approved ],
                'reason' : reason
            }
            
        
        body_dict[ 'headers' ] = body_headers_dict
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
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
            
            ncs_to_header_dicts = CG.client_controller.network_engine.domain_manager.GetNetworkContextsToCustomHeaderDicts()
            
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
                        
                        CG.client_controller.network_engine.domain_manager.DeleteCustomHeader( network_context, key )
                        
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
                        
                        CG.client_controller.network_engine.domain_manager.SetCustomHeader( network_context, key, value = value, approved = approved, reason = reason )
                        
                    
                
            else:
                
                if approved is None and reason is None:
                    
                    raise HydrusExceptions.BadRequestException( 'Sorry, you have to set a value, approved, or reason parameter!' )
                    
                
                if key not in headers_dict:
                    
                    raise HydrusExceptions.BadRequestException( 'Sorry, you tried to set approved/reason on "{}" for "{}", but that entry does not exist, so there is no value to set them to! Please give a value!'.format( key, network_context ) )
                    
                
                headers_altered.add( key )
                
                CG.client_controller.network_engine.domain_manager.SetCustomHeader( network_context, key, approved = approved, reason = reason )
                
            
        
        if CG.client_controller.new_options.GetBoolean( 'notify_client_api_cookies' ) and len( headers_cleared ) + len( headers_set ) + len( headers_altered ) > 0:
            
            message_lines = [ 'Headers sent from API:' ]
            
            if len( headers_cleared ) > 0:
                
                message_lines.extend( [ 'Cleared: {}'.format( key ) for key in sorted( headers_cleared ) ] )
                
            
            if len( headers_set ) > 0:
                
                message_lines.extend( [ 'Set: {}'.format( key ) for key in sorted( headers_set ) ] )
                
            
            if len( headers_set ) > 0:
                
                message_lines.extend( [ 'Altered: {}'.format( key ) for key in sorted( headers_altered ) ] )
                
            
            message = '\n'.join( message_lines )
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusText( message )
            
            job_status.FinishAndDismiss( 5 )
            
            CG.client_controller.pub( 'message', job_status )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
