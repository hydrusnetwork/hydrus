import HydrusServer
import ServerServerResources

class HydrusRequestRestricted( HydrusServer.HydrusRequest ):
    
    def __init__( self, *args, **kwargs ):
        
        HydrusServer.HydrusRequest.__init__( self, *args, **kwargs )
        
        self.hydrus_account = None
        
    
class HydrusServiceRestricted( HydrusServer.HydrusService ):
    
    def __init__( self, service_key, service_type, message ):
        
        HydrusServer.HydrusService.__init__( self, service_key, service_type, message )
        
        self.requestFactory = HydrusRequestRestricted
        
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'access_key', ServerServerResources.HydrusResourceCommandAccessKey( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'access_key_verification', ServerServerResources.HydrusResourceCommandAccessKeyVerification( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'session_key', ServerServerResources.HydrusResourceCommandSessionKey( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( 'account', ServerServerResources.HydrusResourceCommandRestrictedAccount( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'account_info', ServerServerResources.HydrusResourceCommandRestrictedAccountInfo( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'account_types', ServerServerResources.HydrusResourceCommandRestrictedAccountTypes( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'registration_keys', ServerServerResources.HydrusResourceCommandRestrictedRegistrationKeys( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'stats', ServerServerResources.HydrusResourceCommandRestrictedStats( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceAdmin( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'busy', ServerServerResources.HydrusResourceBusyCheck() )
        root.putChild( 'backup', ServerServerResources.HydrusResourceCommandRestrictedBackup( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'init', ServerServerResources.HydrusResourceCommandInit( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'services', ServerServerResources.HydrusResourceCommandRestrictedServices( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'services_info', ServerServerResources.HydrusResourceCommandRestrictedServicesInfo( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'shutdown', ServerServerResources.HydrusResourceCommandShutdown( self._service_key, self._service_type, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepository( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'news', ServerServerResources.HydrusResourceCommandRestrictedNews( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'num_petitions', ServerServerResources.HydrusResourceCommandRestrictedNumPetitions( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'petition', ServerServerResources.HydrusResourceCommandRestrictedPetition( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'content_update_package', ServerServerResources.HydrusResourceCommandRestrictedContentUpdate( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'immediate_content_update_package', ServerServerResources.HydrusResourceCommandRestrictedImmediateContentUpdate( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'service_update_package', ServerServerResources.HydrusResourceCommandRestrictedServiceUpdate( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryFile( HydrusServiceRepository ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRepository._InitRoot( self )
        
        root.putChild( 'file', ServerServerResources.HydrusResourceCommandRestrictedRepositoryFile( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'ip', ServerServerResources.HydrusResourceCommandRestrictedIP( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'thumbnail', ServerServerResources.HydrusResourceCommandRestrictedRepositoryThumbnail( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryTag( HydrusServiceRepository ): pass