from hydrus.core.networking import HydrusServer

from hydrus.server.networking import ServerServerResources

class HydrusServiceRestricted( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( b'busy', ServerServerResources.HydrusResourceBusyCheck() )
        
        root.putChild( b'access_key', ServerServerResources.HydrusResourceAccessKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'access_key_verification', ServerServerResources.HydrusResourceAccessKeyVerification( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'auto_create_account_types', ServerServerResources.HydrusResourceAutoCreateAccountTypes( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'auto_create_registration_key', ServerServerResources.HydrusResourceRestrictedAutoCreateRegistrationKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'session_key', ServerServerResources.HydrusResourceSessionKey( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'account', ServerServerResources.HydrusResourceRestrictedAccount( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'options', ServerServerResources.HydrusResourceRestrictedOptions( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'all_accounts', ServerServerResources.HydrusResourceRestrictedAllAccounts( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'other_account', ServerServerResources.HydrusResourceRestrictedAccountOtherAccount( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'modify_account_account_type', ServerServerResources.HydrusResourceRestrictedAccountModifyAccountType( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'modify_account_ban', ServerServerResources.HydrusResourceRestrictedAccountModifyBan( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'modify_account_expires', ServerServerResources.HydrusResourceRestrictedAccountModifyExpires( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'modify_account_set_message', ServerServerResources.HydrusResourceRestrictedAccountModifySetMessage( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'modify_account_unban', ServerServerResources.HydrusResourceRestrictedAccountModifyUnban( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'account_info', ServerServerResources.HydrusResourceRestrictedAccountInfo( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'account_key_from_content', ServerServerResources.HydrusResourceRestrictedAccountKeyFromContent( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'account_types', ServerServerResources.HydrusResourceRestrictedAccountTypes( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'options_nullification_period', ServerServerResources.HydrusResourceRestrictedOptionsModifyNullificationPeriod( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'options_update_period', ServerServerResources.HydrusResourceRestrictedOptionsModifyUpdatePeriod( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'registration_keys', ServerServerResources.HydrusResourceRestrictedRegistrationKeys( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        root.putChild( b'service_info', ServerServerResources.HydrusResourceRestrictedServiceInfo( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'maintenance_regen_service_info', ServerServerResources.HydrusResourceRestrictedMaintenanceRegenServiceInfo( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceAdmin( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( b'backup', ServerServerResources.HydrusResourceRestrictedBackup( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'lock_on', ServerServerResources.HydrusResourceRestrictedLockOn( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'lock_off', ServerServerResources.HydrusResourceRestrictedLockOff( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'services', ServerServerResources.HydrusResourceRestrictedServices( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'shutdown', ServerServerResources.HydrusResourceShutdown( self._service, HydrusServer.LOCAL_DOMAIN ) )
        root.putChild( b'vacuum', ServerServerResources.HydrusResourceRestrictedVacuum( self._service, HydrusServer.REMOTE_DOMAIN ) )
        
        return root
        
    
class HydrusServiceRepository( HydrusServiceRestricted ):
    
    def _InitRoot( self ):
        
        root = HydrusServiceRestricted._InitRoot( self )
        
        root.putChild( b'num_petitions', ServerServerResources.HydrusResourceRestrictedNumPetitions( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'petition', ServerServerResources.HydrusResourceRestrictedPetition( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'petition_summary_list', ServerServerResources.HydrusResourceRestrictedPetitionSummaryList( self._service, HydrusServer.REMOTE_DOMAIN ) )
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
    
