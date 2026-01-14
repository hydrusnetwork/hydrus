from twisted.web.pages import notFound

from hydrus.core.networking import HydrusServer

from hydrus.client.networking.api import ClientLocalServerResourcesAccess
from hydrus.client.networking.api import ClientLocalServerResourcesAddFiles
from hydrus.client.networking.api import ClientLocalServerResourcesAddNotes
from hydrus.client.networking.api import ClientLocalServerResourcesAddTags
from hydrus.client.networking.api import ClientLocalServerResourcesAddURLs
from hydrus.client.networking.api import ClientLocalServerResourcesEditFileViewingStatistics
from hydrus.client.networking.api import ClientLocalServerResourcesEditRatings
from hydrus.client.networking.api import ClientLocalServerResourcesEditTimes
from hydrus.client.networking.api import ClientLocalServerResourcesGetFiles
from hydrus.client.networking.api import ClientLocalServerResourcesManageCookies
from hydrus.client.networking.api import ClientLocalServerResourcesManageDatabase
from hydrus.client.networking.api import ClientLocalServerResourcesManageFileRelationships
from hydrus.client.networking.api import ClientLocalServerResourcesManagePages
from hydrus.client.networking.api import ClientLocalServerResourcesManagePopups
from hydrus.client.networking.api import ClientLocalServerResourcesManageServices
from hydrus.client.networking.api import ClientLocalServerResourcesManageFavouriteTags

class HydrusClientService( HydrusServer.HydrusService ):
    
    def __init__( self, service, allow_non_local_connections ):
        
        if allow_non_local_connections:
            
            self._client_requests_domain = HydrusServer.REMOTE_DOMAIN
            
        else:
            
            self._client_requests_domain = HydrusServer.LOCAL_DOMAIN
            
        
        super().__init__( service )
        
    

class HydrusServiceClientAPI( HydrusClientService ):
    
    def _InitRoot( self ):
        
        root = HydrusClientService._InitRoot( self )
        
        root.putChild( b'api_version', ClientLocalServerResourcesAccess.HydrusResourceClientAPIVersion( self._service, self._client_requests_domain ) )
        root.putChild( b'request_new_permissions', ClientLocalServerResourcesAccess.HydrusResourceClientAPIPermissionsRequest( self._service, self._client_requests_domain ) )
        root.putChild( b'session_key', ClientLocalServerResourcesAccess.HydrusResourceClientAPIRestrictedAccountSessionKey( self._service, self._client_requests_domain ) )
        root.putChild( b'verify_access_key', ClientLocalServerResourcesAccess.HydrusResourceClientAPIRestrictedAccountVerify( self._service, self._client_requests_domain ) )
        root.putChild( b'get_services', ClientLocalServerResourcesAccess.HydrusResourceClientAPIRestrictedGetServices( self._service, self._client_requests_domain ) )
        root.putChild( b'get_service', ClientLocalServerResourcesAccess.HydrusResourceClientAPIRestrictedGetService( self._service, self._client_requests_domain ) )
        root.putChild( b'get_service_rating_svg', ClientLocalServerResourcesAccess.HydrusResourceClientAPIRestrictedGetServiceRatingSVG( self._service, self._client_requests_domain ) )
        
        add_files = notFound()
        
        root.putChild( b'add_files', add_files )
        
        add_files.putChild( b'add_file', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesAddFile( self._service, self._client_requests_domain ) )
        add_files.putChild( b'clear_file_deletion_record', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesClearDeletedFileRecord( self._service, self._client_requests_domain ) )
        add_files.putChild( b'delete_files', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesDeleteFiles( self._service, self._client_requests_domain ) )
        add_files.putChild( b'undelete_files', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesUndeleteFiles( self._service, self._client_requests_domain ) )
        add_files.putChild( b'migrate_files', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesMigrateFiles( self._service, self._client_requests_domain ) )
        add_files.putChild( b'archive_files', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesArchiveFiles( self._service, self._client_requests_domain ) )
        add_files.putChild( b'unarchive_files', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesUnarchiveFiles( self._service, self._client_requests_domain ) )
        add_files.putChild( b'generate_hashes', ClientLocalServerResourcesAddFiles.HydrusResourceClientAPIRestrictedAddFilesGenerateHashes( self._service, self._client_requests_domain ) )
        
        edit_ratings = notFound()
        
        root.putChild( b'edit_ratings', edit_ratings )
        
        edit_ratings.putChild( b'set_rating', ClientLocalServerResourcesEditRatings.HydrusResourceClientAPIRestrictedEditRatingsSetRating( self._service, self._client_requests_domain ) )
        
        edit_times = notFound()
        
        root.putChild( b'edit_times', edit_times )
        
        edit_times.putChild( b'set_time', ClientLocalServerResourcesEditTimes.HydrusResourceClientAPIRestrictedEditTimesSetTime( self._service, self._client_requests_domain ) )
        edit_times.putChild( b'increment_file_viewtime', ClientLocalServerResourcesEditFileViewingStatistics.HydrusResourceClientAPIRestrictedEditFileViewingStatisticsIncrementFileViewingStatistics( self._service, self._client_requests_domain ) )
        edit_times.putChild( b'set_file_viewtime', ClientLocalServerResourcesEditFileViewingStatistics.HydrusResourceClientAPIRestrictedEditFileViewingStatisticsSetFileViewingStatistics( self._service, self._client_requests_domain ) )
        
        add_tags = notFound()
        
        root.putChild( b'add_tags', add_tags )
        
        add_tags.putChild( b'add_tags', ClientLocalServerResourcesAddTags.HydrusResourceClientAPIRestrictedAddTagsAddTags( self._service, self._client_requests_domain ) )
        add_tags.putChild( b'clean_tags', ClientLocalServerResourcesAddTags.HydrusResourceClientAPIRestrictedAddTagsCleanTags( self._service, self._client_requests_domain ) )
        add_tags.putChild( b'search_tags', ClientLocalServerResourcesAddTags.HydrusResourceClientAPIRestrictedAddTagsSearchTags( self._service, self._client_requests_domain ) )
        add_tags.putChild( b'get_siblings_and_parents', ClientLocalServerResourcesAddTags.HydrusResourceClientAPIRestrictedAddTagsGetTagSiblingsParents( self._service, self._client_requests_domain ) )
        add_tags.putChild( b'get_favourite_tags', ClientLocalServerResourcesManageFavouriteTags.HydrusResourceClientAPIRestrictedManageFavouriteTagsGetFavouriteTags( self._service, self._client_requests_domain ) )
        add_tags.putChild( b'set_favourite_tags', ClientLocalServerResourcesManageFavouriteTags.HydrusResourceClientAPIRestrictedManageFavouriteTagsSetFavouriteTags( self._service, self._client_requests_domain ) )
        
        add_urls = notFound()
        
        root.putChild( b'add_urls', add_urls )
        
        add_urls.putChild( b'get_url_info', ClientLocalServerResourcesAddURLs.HydrusResourceClientAPIRestrictedAddURLsGetURLInfo( self._service, self._client_requests_domain ) )
        add_urls.putChild( b'get_url_files', ClientLocalServerResourcesAddURLs.HydrusResourceClientAPIRestrictedAddURLsGetURLFiles( self._service, self._client_requests_domain ) )
        add_urls.putChild( b'add_url', ClientLocalServerResourcesAddURLs.HydrusResourceClientAPIRestrictedAddURLsImportURL( self._service, self._client_requests_domain ) )
        add_urls.putChild( b'associate_url', ClientLocalServerResourcesAddURLs.HydrusResourceClientAPIRestrictedAddURLsAssociateURL( self._service, self._client_requests_domain ) )
        
        get_files = notFound()
        
        root.putChild( b'get_files', get_files )
        
        get_files.putChild( b'search_files', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesSearchFiles( self._service, self._client_requests_domain ) )
        get_files.putChild( b'file_metadata', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesFileMetadata( self._service, self._client_requests_domain ) )
        get_files.putChild( b'file_hashes', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesFileHashes( self._service, self._client_requests_domain ) )
        get_files.putChild( b'file', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetFile( self._service, self._client_requests_domain ) )
        get_files.putChild( b'file_path', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetFilePath( self._service, self._client_requests_domain) )
        get_files.putChild( b'local_file_storage_locations', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetLocalFileStorageLocations( self._service, self._client_requests_domain ) )
        get_files.putChild( b'thumbnail', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetThumbnail( self._service, self._client_requests_domain ) )
        get_files.putChild( b'thumbnail_path', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetThumbnailPath( self._service, self._client_requests_domain) )
        get_files.putChild( b'render', ClientLocalServerResourcesGetFiles.HydrusResourceClientAPIRestrictedGetFilesGetRenderedFile( self._service, self._client_requests_domain) )
        
        add_notes = notFound()
        
        root.putChild( b'add_notes', add_notes )
        
        add_notes.putChild( b'set_notes', ClientLocalServerResourcesAddNotes.HydrusResourceClientAPIRestrictedAddNotesSetNotes( self._service, self._client_requests_domain ) )
        add_notes.putChild( b'delete_notes', ClientLocalServerResourcesAddNotes.HydrusResourceClientAPIRestrictedAddNotesDeleteNotes( self._service, self._client_requests_domain ) )
        
        manage_cookies = notFound()
        
        root.putChild( b'manage_cookies', manage_cookies )
        
        manage_cookies.putChild( b'get_cookies', ClientLocalServerResourcesManageCookies.HydrusResourceClientAPIRestrictedManageCookiesGetCookies( self._service, self._client_requests_domain ) )
        manage_cookies.putChild( b'set_cookies', ClientLocalServerResourcesManageCookies.HydrusResourceClientAPIRestrictedManageCookiesSetCookies( self._service, self._client_requests_domain ) )
        
        manage_database = notFound()
        
        root.putChild( b'manage_database', manage_database )
        
        manage_database.putChild( b'force_commit', ClientLocalServerResourcesManageDatabase.HydrusResourceClientAPIRestrictedManageDatabaseForceCommit( self._service, self._client_requests_domain ) )
        manage_database.putChild( b'get_client_options', ClientLocalServerResourcesManageDatabase.HydrusResourceClientAPIRestrictedManageDatabaseGetClientOptions( self._service, self._client_requests_domain ) )
        manage_database.putChild( b'lock_on', ClientLocalServerResourcesManageDatabase.HydrusResourceClientAPIRestrictedManageDatabaseLockOn( self._service, self._client_requests_domain ) )
        manage_database.putChild( b'lock_off', ClientLocalServerResourcesManageDatabase.HydrusResourceClientAPIRestrictedManageDatabaseLockOff( self._service, self._client_requests_domain ) )
        manage_database.putChild( b'mr_bones', ClientLocalServerResourcesManageDatabase.HydrusResourceClientAPIRestrictedManageDatabaseMrBones( self._service, self._client_requests_domain ) )
        
        manage_services = notFound()
        
        root.putChild( b'manage_services', manage_services )
        
        manage_services.putChild( b'get_pending_counts', ClientLocalServerResourcesManageServices.HydrusResourceClientAPIRestrictedManageServicesPendingCounts( self._service, self._client_requests_domain ) )
        manage_services.putChild( b'commit_pending', ClientLocalServerResourcesManageServices.HydrusResourceClientAPIRestrictedManageServicesCommitPending( self._service, self._client_requests_domain ) )
        manage_services.putChild( b'forget_pending', ClientLocalServerResourcesManageServices.HydrusResourceClientAPIRestrictedManageServicesForgetPending( self._service, self._client_requests_domain ) )
        
        manage_file_relationships = notFound()
        
        root.putChild( b'manage_file_relationships', manage_file_relationships )
        
        manage_file_relationships.putChild( b'get_file_relationships', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsGetRelationships( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'get_potentials_count', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsGetPotentialsCount( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'get_potential_pairs', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsGetPotentialPairs( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'get_random_potentials', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsGetRandomPotentials( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'remove_potentials', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsRemovePotentials( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'set_file_relationships', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsSetRelationships( self._service, self._client_requests_domain ) )
        manage_file_relationships.putChild( b'set_kings', ClientLocalServerResourcesManageFileRelationships.HydrusResourceClientAPIRestrictedManageFileRelationshipsSetKings( self._service, self._client_requests_domain ) )
        
        manage_headers = notFound()
        
        root.putChild( b'manage_headers', manage_headers )
        
        manage_headers.putChild( b'set_user_agent', ClientLocalServerResourcesManageCookies.HydrusResourceClientAPIRestrictedManageCookiesSetUserAgent( self._service, self._client_requests_domain ) )
        manage_headers.putChild( b'get_headers', ClientLocalServerResourcesManageCookies.HydrusResourceClientAPIRestrictedManageCookiesGetHeaders( self._service, self._client_requests_domain ) )
        manage_headers.putChild( b'set_headers', ClientLocalServerResourcesManageCookies.HydrusResourceClientAPIRestrictedManageCookiesSetHeaders( self._service, self._client_requests_domain ) )
        
        manage_pages = notFound()
        
        root.putChild( b'manage_pages', manage_pages )
        
        manage_pages.putChild( b'add_files', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesAddFiles( self._service, self._client_requests_domain ) )
        manage_pages.putChild( b'focus_page', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesFocusPage( self._service, self._client_requests_domain ) )
        manage_pages.putChild( b'get_media_viewers', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesGetMediaViewers( self._service, self._client_requests_domain ) )
        manage_pages.putChild( b'get_pages', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesGetPages( self._service, self._client_requests_domain ) )
        manage_pages.putChild( b'get_page_info', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesGetPageInfo( self._service, self._client_requests_domain ) )
        manage_pages.putChild( b'refresh_page', ClientLocalServerResourcesManagePages.HydrusResourceClientAPIRestrictedManagePagesRefreshPage( self._service, self._client_requests_domain ) )
        
        manage_popups = notFound()
        
        root.putChild( b'manage_popups', manage_popups )
        
        manage_popups.putChild( b'get_popups', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsGetPopups( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'cancel_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsCancelPopup( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'dismiss_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsDismissPopup( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'finish_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsFinishPopup( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'finish_and_dismiss_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsFinishAndDismissPopup( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'call_user_callable', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsCallUserCallable( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'add_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsAddPopup( self._service, self._client_requests_domain ) )
        manage_popups.putChild( b'update_popup', ClientLocalServerResourcesManagePopups.HydrusResourceClientAPIRestrictedManagePopupsUpdatePopup( self._service, self._client_requests_domain ) )
        
        return root
        
    
