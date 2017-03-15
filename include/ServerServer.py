import HydrusServer
import ServerServerResources

class HydrusRequestRestricted( HydrusServer.HydrusRequest ):
    
    def __init__( self, *args, **kwargs ):
        
        HydrusServer.HydrusRequest.__init__( self, *args, **kwargs )
        
        self.hydrus_account = None
        
    
class HydrusServiceRestricted( HydrusServer.HydrusService ):
    
    def __init__( self, service ):
        
        HydrusServer.HydrusService.__init__( self, service )
        
        self.requestFactory = HydrusRequestRestricted
        
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'access_key', ServerServerResources.HydrusResourceAccessKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'access_key_verification', ServerServerResources.HydrusResourceAccessKeyVerification( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'session_key', ServerServerResources.HydrusResourceSessionKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( 'account', ServerServerResources.HydrusResourceRestrictedAccount( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'account_info', ServerServerResources.HydrusResourceRestrictedAccountInfo( self._service, HydrusServer.REMOTE_DOMAIN ) )
        #root.putChild( 'account_modification', ServerServerResources.HydrusResourceRestrictedAccountModification( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'account_types', ServerServerResources.HydrusResourceRestrictedAccountTypes( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'registration_keys', ServerServerResources.HydrusResourceRestrictedRegistrationKeys( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceAdmin( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'busy', ServerServerResources.HydrusResourceBusyCheck() )
        root.putChild( 'backup', ServerServerResources.HydrusResourceRestrictedBackup( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'services', ServerServerResources.HydrusResourceRestrictedServices( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'shutdown', ServerServerResources.HydrusResourceShutdown( self._service, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepository( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( 'num_petitions', ServerServerResources.HydrusResourceRestrictedNumPetitions( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'petition', ServerServerResources.HydrusResourceRestrictedPetition( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'update', ServerServerResources.HydrusResourceRestrictedUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        #root.putChild( 'immediate_update', ServerServerResources.HydrusResourceRestrictedImmediateUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'metadata', ServerServerResources.HydrusResourceRestrictedMetadataUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryFile( HydrusServiceRepository ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRepository._InitRoot( self )
        
        root.putChild( 'file', ServerServerResources.HydrusResourceRestrictedRepositoryFile( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'ip', ServerServerResources.HydrusResourceRestrictedIP( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'thumbnail', ServerServerResources.HydrusResourceRestrictedRepositoryThumbnail( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryTag( HydrusServiceRepository ):
    
    pass
    
