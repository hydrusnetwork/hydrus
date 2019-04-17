from . import HydrusServer
from . import ServerServerResources

class HydrusServiceRestricted( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( b'access_key', ServerServerResources.HydrusResourceAccessKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'access_key_verification', ServerServerResources.HydrusResourceAccessKeyVerification( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'session_key', ServerServerResources.HydrusResourceSessionKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'account', ServerServerResources.HydrusResourceRestrictedAccount( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'account_info', ServerServerResources.HydrusResourceRestrictedAccountInfo( self._service, HydrusServer.REMOTE_DOMAIN ) )
        #root.putChild( b'account_modification', ServerServerResources.HydrusResourceRestrictedAccountModification( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'account_types', ServerServerResources.HydrusResourceRestrictedAccountTypes( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'registration_keys', ServerServerResources.HydrusResourceRestrictedRegistrationKeys( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceAdmin( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( b'busy', ServerServerResources.HydrusResourceBusyCheck() )
        root.putChild( b'backup', ServerServerResources.HydrusResourceRestrictedBackup( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'services', ServerServerResources.HydrusResourceRestrictedServices( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'shutdown', ServerServerResources.HydrusResourceShutdown( self._service, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepository( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( b'num_petitions', ServerServerResources.HydrusResourceRestrictedNumPetitions( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'petition', ServerServerResources.HydrusResourceRestrictedPetition( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'update', ServerServerResources.HydrusResourceRestrictedUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        #root.putChild( b'immediate_update', ServerServerResources.HydrusResourceRestrictedImmediateUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'metadata', ServerServerResources.HydrusResourceRestrictedMetadataUpdate( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryFile( HydrusServiceRepository ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRepository._InitRoot( self )
        
        root.putChild( b'file', ServerServerResources.HydrusResourceRestrictedRepositoryFile( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'ip', ServerServerResources.HydrusResourceRestrictedIP( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'thumbnail', ServerServerResources.HydrusResourceRestrictedRepositoryThumbnail( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepositoryTag( HydrusServiceRepository ):
    
    pass
    
