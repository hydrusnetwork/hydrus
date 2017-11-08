import bs4
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientFiles
import ClientImageHandling
import ClientNetworking
import ClientTags
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import json
import os
import random
import shutil
import threading
import time
import traceback
import urlparse
import wx
import HydrusThreading

CHECKER_STATUS_OK = 0
CHECKER_STATUS_DEAD = 1
CHECKER_STATUS_404 = 2

DID_FILE_WORK_MINIMUM_SLEEP_TIME = 0.1

def THREADDownloadURL( job_key, url, url_string ):
    
    job_key.SetVariable( 'popup_title', url_string )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
    
    try:
        
        network_job = ClientNetworking.NetworkJob( 'GET', url, temp_path = temp_path )
        
        network_job.OverrideBandwidth()
        
        HG.client_controller.network_engine.AddJob( network_job )
        
        job_key.SetVariable( 'popup_network_job', network_job )
        
        try:
            
            network_job.WaitUntilDone()
            
        except HydrusExceptions.CancelledException:
            
            job_key.Cancel()
            
            raise
            
        except HydrusExceptions.NetworkException:
            
            job_key.Cancel()
            
            raise
            
        
        job_key.DeleteVariable( 'popup_network_job' )
        
        job_key.SetVariable( 'popup_text_1', 'importing' )
        
        file_import_job = FileImportJob( temp_path )
        
        client_files_manager = HG.client_controller.client_files_manager
        
        ( result, hash ) = client_files_manager.ImportFile( file_import_job )
        
    finally:
        
        HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
        
    
    if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
        
        if result == CC.STATUS_SUCCESSFUL:
            
            job_key.SetVariable( 'popup_text_1', 'successful!' )
            
        else:
            
            job_key.SetVariable( 'popup_text_1', 'was already in the database!' )
            
        
        job_key.SetVariable( 'popup_files', ( { hash }, 'download' ) )
        
    elif result == CC.STATUS_DELETED:
        
        job_key.SetVariable( 'popup_text_1', 'had already been deleted!' )
        
    
    job_key.Finish()
    
def THREADDownloadURLs( job_key, urls, title ):
    
    job_key.SetVariable( 'popup_title', title )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    num_successful = 0
    num_redundant = 0
    num_deleted = 0
    num_failed = 0
    
    successful_hashes = set()
    
    for ( i, url ) in enumerate( urls ):
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            break
            
        
        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, len( urls ) ) )
        job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( urls ) ) )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            network_job = ClientNetworking.NetworkJob( 'GET', url, temp_path = temp_path )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
            except HydrusExceptions.CancelledException:
                
                break
                
            
            try:
                
                job_key.SetVariable( 'popup_text_2', 'importing' )
                
                file_import_job = FileImportJob( temp_path )
                
                client_files_manager = HG.client_controller.client_files_manager
                
                ( result, hash ) = client_files_manager.ImportFile( file_import_job )
                
            except Exception as e:
                
                job_key.DeleteVariable( 'popup_text_2' )
                
                HydrusData.Print( url + ' failed to import!' )
                HydrusData.PrintException( e )
                
                num_failed += 1
                
                continue
                
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
            
            if result == CC.STATUS_SUCCESSFUL:
                
                num_successful += 1
                
            else:
                
                num_redundant += 1
                
            
            successful_hashes.add( hash )
            
        elif result == CC.STATUS_DELETED:
            
            num_deleted += 1
            
        
    
    job_key.DeleteVariable( 'popup_network_job' )
    
    text_components = []
    
    if num_successful > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_successful ) + ' successful' )
        
    
    if num_redundant > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_redundant ) + ' already in db' )
        
    
    if num_deleted > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_deleted ) + ' deleted' )
        
    
    if num_failed > 0:
        
        text_components.append( HydrusData.ConvertIntToPrettyString( num_failed ) + ' failed (errors written to log)' )
        
    
    job_key.SetVariable( 'popup_text_1', ', '.join( text_components ) )
    
    if len( successful_hashes ) > 0:
        
        job_key.SetVariable( 'popup_files', ( successful_hashes, 'downloads' ) )
        
    
    job_key.DeleteVariable( 'popup_gauge_1' )
    job_key.DeleteVariable( 'popup_text_2' )
    
    job_key.Finish()
    
class FileImportJob( object ):
    
    def __init__( self, temp_path, file_import_options = None ):
        
        if file_import_options is None:
            
            file_import_options = ClientDefaults.GetDefaultFileImportOptions()
            
        
        self._temp_path = temp_path
        self._file_import_options = file_import_options
        
        self._hash = None
        self._pre_import_status = None
        
        self._file_info = None
        self._thumbnail = None
        self._phashes = None
        self._extra_hashes = None
        
    
    def GetExtraHashes( self ):
        
        return self._extra_hashes
        
    
    def GetFileImportOptions( self ):
        
        return self._file_import_options
        
    
    def GetFileInfo( self ):
        
        return self._file_info
        
    
    def GetHash( self ):
        
        return self._hash
        
    
    def GetMime( self ):
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        return mime
        
    
    def GetPreImportStatus( self ):
        
        return self._pre_import_status
        
    
    def GetPHashes( self ):
        
        return self._phashes
        
    
    def GetTempPathAndThumbnail( self ):
        
        return ( self._temp_path, self._thumbnail )
        
    
    def PubsubContentUpdates( self ):
        
        if self._pre_import_status == CC.STATUS_REDUNDANT:
            
            ( automatic_archive, exclude_deleted, min_size, min_resolution ) = self._file_import_options.ToTuple()
            
            if automatic_archive:
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, set( ( self._hash, ) ) ) ] }
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
    def IsGoodToImport( self ):
        
        ( automatic_archive, exclude_deleted, min_size, min_resolution ) = self._file_import_options.ToTuple()
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        if width is not None and height is not None:
            
            if min_resolution is not None:
                
                ( min_x, min_y ) = min_resolution
                
                if width < min_x or height < min_y:
                    
                    return ( False, 'Resolution too small.' )
                    
                
            
        
        if min_size is not None:
            
            if size < min_size:
                
                return ( False, 'File too small.' )
                
            
        
        return ( True, 'File looks good.' )
        
    
    def IsNewToDB( self ):
        
        if self._pre_import_status == CC.STATUS_NEW:
            
            return True
            
        
        if self._pre_import_status == CC.STATUS_DELETED:
            
            ( automatic_archive, exclude_deleted, min_size, min_resolution ) = self._file_import_options.ToTuple()
            
            if not exclude_deleted:
                
                return True
                
            
        
        return False
        
    
    def GenerateHashAndStatus( self ):
        
        HydrusImageHandling.ConvertToPngIfBmp( self._temp_path )
        
        self._hash = HydrusFileHandling.GetHashFromPath( self._temp_path )
        
        self._pre_import_status = HG.client_controller.Read( 'hash_status', self._hash )
        
    
    def GenerateInfo( self ):
        
        mime = HydrusFileHandling.GetMime( self._temp_path )
        
        new_options = HG.client_controller.GetNewOptions()
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and new_options.GetBoolean( 'do_not_import_decompression_bombs' ):
            
            if HydrusImageHandling.IsDecompressionBomb( self._temp_path ):
                
                raise HydrusExceptions.SizeException( 'Image seems to be a Decompression Bomb!' )
                
            
        
        self._file_info = HydrusFileHandling.GetFileInfo( self._temp_path, mime )
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            self._thumbnail = HydrusFileHandling.GenerateThumbnail( self._temp_path, mime = mime )
            
        
        if mime in HC.MIMES_WE_CAN_PHASH:
            
            self._phashes = ClientImageHandling.GenerateShapePerceptualHashes( self._temp_path, mime )
            
        
        self._extra_hashes = HydrusFileHandling.GetExtraHashesFromPath( self._temp_path )
        
    
class GalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, gallery_identifier = None ):
        
        if gallery_identifier is None:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._gallery_identifier = gallery_identifier
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        self._current_query = None
        self._current_query_num_urls = 0
        
        self._current_gallery_stream_identifier = None
        self._current_gallery_stream_identifier_page_index = 0
        self._current_gallery_stream_identifier_found_urls = set()
        
        self._pending_gallery_stream_identifiers = []
        
        self._pending_queries = []
        
        new_options = HG.client_controller.GetNewOptions()
        
        self._get_tags_if_url_known_and_file_redundant = new_options.GetBoolean( 'get_tags_if_url_known_and_file_redundant' )
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        self._gallery_paused = False
        self._files_paused = False
        
        self._file_import_options = ClientDefaults.GetDefaultFileImportOptions()
        
        self._tag_import_options = new_options.GetDefaultTagImportOptions( self._gallery_identifier )
        
        self._seed_cache = SeedCache()
        
        self._lock = threading.Lock()
        
        self._new_files_event = threading.Event()
        self._new_query_event = threading.Event()
        
        self._gallery = None
        
        self._gallery_status = ''
        self._current_action = ''
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        
        self._download_control_gallery_set = None
        self._download_control_gallery_clear = None
        
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        
        if self._current_gallery_stream_identifier is None:
            
            serialisable_current_gallery_stream_identifier = None
            
        else:
            
            serialisable_current_gallery_stream_identifier = self._current_gallery_stream_identifier.GetSerialisableTuple()
            
        
        serialisable_current_gallery_stream_identifier_found_urls = list( self._current_gallery_stream_identifier_found_urls )
        
        serialisable_pending_gallery_stream_identifiers = [ pending_gallery_stream_identifier.GetSerialisableTuple() for pending_gallery_stream_identifier in self._pending_gallery_stream_identifiers ]
        
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_seed_cache = self._seed_cache.GetSerialisableTuple()
        
        serialisable_current_query_stuff = ( self._current_query, self._current_query_num_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifiers )
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._get_tags_if_url_known_and_file_redundant, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_options, serialisable_tag_options, serialisable_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._get_tags_if_url_known_and_file_redundant, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_options, serialisable_tag_options, serialisable_seed_cache ) = serialisable_info
        
        ( self._current_query, self._current_query_num_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifier ) = serialisable_current_query_stuff
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        
        if serialisable_current_gallery_stream_identifier is None:
            
            self._current_gallery_stream_identifier = None
            
        else:
            
            self._current_gallery_stream_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_current_gallery_stream_identifier )
            
        
        self._current_gallery_stream_identifier_found_urls = set( serialisable_current_gallery_stream_identifier_found_urls )
        
        self._pending_gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_pending_gallery_stream_identifier ) for serialisable_pending_gallery_stream_identifier in serialisable_pending_gallery_stream_identifier ]
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        self._seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_seed_cache )
        
    
    def _WorkOnFiles( self, page_key ):
        
        url = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if url is None:
            
            return False
            
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworking.NetworkJobDownloaderQueryTemporary( page_key, method, url, **kwargs )
            
            wx.CallAfter( self._download_control_file_set, network_job )
            
            return network_job
            
        
        gallery = ClientDownloading.GetGallery( self._gallery_identifier )
        
        gallery.SetNetworkJobFactory( network_job_factory )
        
        try:
            
            with self._lock:
                
                self._current_action = 'reviewing file'
                
            
            ( status, hash, note ) = HG.client_controller.Read( 'url_status', url )
            
            if status == CC.STATUS_DELETED:
                
                if not self._file_import_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    note = ''
                    
                
            
            downloaded_tags = []
            
            if status == CC.STATUS_REDUNDANT:
                
                if self._get_tags_if_url_known_and_file_redundant and self._tag_import_options.InterestedInTags():
                    
                    downloaded_tags = gallery.GetTags( url )
                    
                
            elif status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    with self._lock:
                        
                        self._current_action = 'downloading file'
                        
                    
                    if self._tag_import_options.InterestedInTags():
                        
                        downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                        
                    else:
                        
                        gallery.GetFile( temp_path, url )
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    client_files_manager = HG.client_controller.client_files_manager
                    
                    with self._lock:
                        
                        self._current_action = 'importing file'
                        
                    
                    ( status, hash ) = client_files_manager.ImportFile( file_import_job )
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( url, ) ) ) ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            self._seed_cache.UpdateSeedStatus( url, status, note = note )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.CancelledException:
            
            status = CC.STATUS_SKIPPED
            
            self._seed_cache.UpdateSeedStatus( url, status )
            
            time.sleep( 2 )
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._seed_cache.UpdateSeedStatus( url, status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            self._seed_cache.UpdateSeedStatus( url, status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._seed_cache.UpdateSeedStatus( url, status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            wx.CallAfter( self._download_control_file_clear )
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        return True
        
    
    def _WorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if self._current_query is None:
                
                if len( self._pending_queries ) == 0:
                    
                    self._gallery_status = ''
                    
                    return False
                    
                else:
                    
                    self._current_query = self._pending_queries.pop( 0 )
                    self._current_query_num_urls = 0
                    
                    self._current_gallery_stream_identifier = None
                    self._pending_gallery_stream_identifiers = list( self._gallery_stream_identifiers )
                    
                
            
            if self._current_gallery_stream_identifier is None:
                
                if len( self._pending_gallery_stream_identifiers ) == 0:
                    
                    self._gallery_status = self._current_query + ' produced ' + HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls'
                    
                    self._current_query = None
                    
                    return False
                    
                else:
                    
                    self._current_gallery_stream_identifier = self._pending_gallery_stream_identifiers.pop( 0 )
                    self._current_gallery_stream_identifier_page_index = 0
                    self._current_gallery_stream_identifier_found_urls = set()
                    
                
            
            def network_job_factory( method, url, **kwargs ):
                
                network_job = ClientNetworking.NetworkJobDownloaderQueryTemporary( page_key, method, url, **kwargs )
                
                network_job.OverrideBandwidth()
                
                wx.CallAfter( self._download_control_gallery_set, network_job )
                
                return network_job
                
            
            gallery = ClientDownloading.GetGallery( self._current_gallery_stream_identifier )
            
            gallery.SetNetworkJobFactory( network_job_factory )
            
            query = self._current_query
            page_index = self._current_gallery_stream_identifier_page_index
            
            self._gallery_status = HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls found, now checking page ' + HydrusData.ConvertIntToPrettyString( self._current_gallery_stream_identifier_page_index + 1 )
            
        
        error_occured = False
        
        num_already_in_seed_cache = 0
        new_urls = []
        
        try:
            
            ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( query, page_index )
            
            with self._lock:
                
                no_urls_found = len( page_of_urls ) == 0
                no_new_urls = len( self._current_gallery_stream_identifier_found_urls.intersection( page_of_urls ) ) == len( page_of_urls )
                
                if definitely_no_more_pages or no_urls_found or no_new_urls:
                    
                    self._current_gallery_stream_identifier = None
                    
                else:
                    
                    self._current_gallery_stream_identifier_page_index += 1
                    self._current_gallery_stream_identifier_found_urls.update( page_of_urls )
                    
                
            
            for url in page_of_urls:
                
                if self._seed_cache.HasSeed( url ):
                    
                    num_already_in_seed_cache += 1
                    
                else:
                    
                    with self._lock:
                        
                        if self._file_limit is not None and self._current_query_num_urls + 1 > self._file_limit:
                            
                            self._current_gallery_stream_identifier = None
                            
                            self._pending_gallery_stream_identifiers = []
                            
                            break
                            
                        
                        self._current_query_num_urls += 1
                        
                    
                    new_urls.append( url )
                    
                
            
            self._seed_cache.AddSeeds( new_urls )
            
            if len( new_urls ) > 0:
                
                self._new_files_event.set()
                
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                text = 'cancelled'
                
            elif isinstance( e, HydrusExceptions.NotFoundException ):
                
                text = 'Gallery 404'
                
            else:
                
                text = HydrusData.ToUnicode( e )
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
            
            with self._lock:
                
                self._current_gallery_stream_identifier = None
                
                self._gallery_status = text
                
            
            time.sleep( 5 )
            
        finally:
            
            wx.CallAfter( self._download_control_gallery_clear )
            
        
        with self._lock:
            
            self._gallery_status = HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls found so far for ' + query
            
            if num_already_in_seed_cache > 0:
                
                self._gallery_status += ' (' + HydrusData.ConvertIntToPrettyString( num_already_in_seed_cache ) + ' of last page already in queue)'
                
            
        
        return True
        
    
    def _THREADWorkOnFiles( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnFiles( page_key )
                    
                    if did_work:
                        
                        time.sleep( DID_FILE_WORK_MINIMUM_SLEEP_TIME )
                        
                    else:
                        
                        self._new_files_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_files_event.clear()
            
        
    
    def _THREADWorkOnGallery( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_query_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnGallery( page_key )
                    
                    if did_work:
                        
                        time.sleep( 5 )
                        
                    else:
                        
                        self._new_query_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_query_event.clear()
            
        
    
    def AdvanceQuery( self, query ):
        
        with self._lock:
            
            if query in self._pending_queries:
                
                index = self._pending_queries.index( query )
                
                if index - 1 >= 0:
                    
                    self._pending_queries.remove( query )
                    
                    self._pending_queries.insert( index - 1, query )
                    
                
            
        
    
    def DelayQuery( self, query ):
        
        with self._lock:
            
            if query in self._pending_queries:
                
                index = self._pending_queries.index( query )
                
                if index + 1 < len( self._pending_queries ):
                    
                    self._pending_queries.remove( query )
                    
                    self._pending_queries.insert( index + 1, query )
                    
                
            
        
    
    def DeleteQuery( self, query ):
        
        with self._lock:
            
            if query in self._pending_queries:
                
                self._pending_queries.remove( query )
                
            
        
    
    def FinishCurrentQuery( self ):
        
        with self._lock:
            
            self._current_query = None
            self._gallery_paused = False
            
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._tag_import_options, self._file_limit )
            
        
    
    def GetSeedCache( self ):
        
        return self._seed_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            cancellable = self._current_query is not None
            
            return ( list( self._pending_queries ), self._gallery_status, self._current_action, self._files_paused, self._gallery_paused, cancellable )
            
        
    
    def GetTagsIfURLKnownAndFileRedundant( self ):
        
        with self._lock:
            
            return self._get_tags_if_url_known_and_file_redundant
            
        
    
    def InvertGetTagsIfURLKnownAndFileRedundant( self ):
        
        with self._lock:
            
            self._get_tags_if_url_known_and_file_redundant = not self._get_tags_if_url_known_and_file_redundant
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            self._new_files_event.set()
            
        
    
    def PausePlayGallery( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
            self._new_query_event.set()
            
        
    
    def PendQuery( self, query ):
        
        with self._lock:
            
            if query not in self._pending_queries:
                
                self._pending_queries.append( query )
                
                self._new_query_event.set()
                
            
        
    
    def SetDownloadControls( self, file_download_control, gallery_download_control ):
        
        with self._lock:
            
            self._download_control_file_set = file_download_control.SetNetworkJob
            self._download_control_file_clear = file_download_control.ClearNetworkJob
            
            self._download_control_gallery_set = gallery_download_control.SetNetworkJob
            self._download_control_gallery_clear = gallery_download_control.ClearNetworkJob
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key ):
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnGallery, page_key )
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnFiles, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT ] = GalleryImport

class FileImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS
    SERIALISABLE_VERSION = 1
    
    def __init__( self, automatic_archive = None, exclude_deleted = None, min_size = None, min_resolution = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._automatic_archive = automatic_archive
        self._exclude_deleted = exclude_deleted
        self._min_size = min_size
        self._min_resolution = min_resolution
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution ) = serialisable_info
        
    
    def FileIsValid( self, size, resolution = None ):
        
        if self._min_size is not None and size < self._min_size:
            
            return False
            
        
        if resolution is not None and self._min_resolution is not None:
            
            ( x, y ) = resolution
            
            ( min_x, min_y ) = self._min_resolution
            
            if x < min_x or y < min_y:
                
                return False
                
            
        
        return True
        
    
    def GetAutomaticArchive( self ):
        
        return self._automatic_archive
        
    
    def GetExcludeDeleted( self ):
        
        return self._exclude_deleted
        
    
    def GetSummary( self ):
        
        statements = []
        
        if self._automatic_archive:
            
            statements.append( 'automatically archiving' )
            
        
        if self._exclude_deleted:
            
            statements.append( 'excluding previously deleted' )
            
        
        if self._min_size is not None:
            
            statements.append( 'excluding < ' + HydrusData.ConvertIntToBytes( self._min_size ) )
            
        
        if self._min_resolution is not None:
            
            ( width, height ) = self._min_resolution
            
            statements.append( 'excluding < ( ' + HydrusData.ConvertIntToPrettyString( width ) + ' x ' + HydrusData.ConvertIntToPrettyString( height ) + ' )' )
            
        
        if len( statements ) == 0:
            
            statements.append( 'no options set' )
            
        
        summary = ', '.join( statements )
        
        return summary
        
    
    def ToTuple( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._min_size, self._min_resolution )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS ] = FileImportOptions

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, paths = None, file_import_options = None, paths_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if paths is None:
            
            self._paths_cache = None
            
        else:
            
            self._paths_cache = SeedCache()
            
            self._paths_cache.AddSeeds( paths )
            
            for path in paths:
                
                try:
                    
                    s = os.stat( path )
                    
                    source_time = min( s.st_mtime, s.st_ctime )
                    
                    self._paths_cache.UpdateSeedSourceTime( path, source_time )
                    
                except:
                    
                    pass
                    
                
            
        
        self._file_import_options = file_import_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
        self._current_action = ''
        self._paused = False
        
        self._lock = threading.Lock()
        
        self._new_files_event = threading.Event()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._paths_cache.GetSerialisableTuple()
        serialisable_options = self._file_import_options.GetSerialisableTuple()
        serialisable_paths_to_tags = { path : { service_key.encode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in self._paths_to_tags.items() }
        
        return ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused ) = serialisable_info
        
        self._paths_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
        
    
    def _WorkOnFiles( self, page_key ):
        
        path = self._paths_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if path is None:
            
            return False
            
        
        with self._lock:
            
            if path in self._paths_to_tags:
                
                service_keys_to_tags = self._paths_to_tags[ path ]
                
            else:
                
                service_keys_to_tags = {}
                
            
        
        try:
            
            if not os.path.exists( path ):
                
                raise Exception( 'Source file does not exist!' )
                
            
            with self._lock:
                
                self._current_action = 'preparing to import'
                
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                copied = HydrusPaths.MirrorFile( path, temp_path )
                
                if not copied:
                    
                    raise Exception( 'File failed to copy--see log for error.' )
                    
                
                with self._lock:
                    
                    self._current_action = 'importing'
                    
                
                file_import_job = FileImportJob( temp_path, self._file_import_options )
                
                client_files_manager = HG.client_controller.client_files_manager
                
                ( status, hash ) = client_files_manager.ImportFile( file_import_job )
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
            self._paths_cache.UpdateSeedStatus( path, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
                if self._delete_after_success:
                    
                    try:
                        
                        ClientData.DeletePath( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'While attempting to delete ' + path + ', the following error occured:' )
                        HydrusData.ShowException( e )
                        
                    
                    txt_path = path + '.txt'
                    
                    if os.path.exists( txt_path ):
                        
                        try:
                            
                            ClientData.DeletePath( txt_path )
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'While attempting to delete ' + txt_path + ', the following error occured:' )
                            HydrusData.ShowException( e )
                            
                        
                    
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._paths_cache.UpdateSeedStatus( path, status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._paths_cache.UpdateSeedStatus( path, status, exception = e )
            
        finally:
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        return True
        
    
    def _THREADWork( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnFiles( page_key )
                    
                    if not did_work:
                        
                        self._new_files_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_files_event.clear()
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            work_to_do = self._paths_cache.WorkToDo()
            
            return work_to_do and not self._paused
            
        
    
    def GetSeedCache( self ):
        
        return self._paths_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._current_action, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            self._new_files_event.set()
            
        
    
    def Start( self, page_key ):
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWork, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_VERSION = 4
    
    def __init__( self, name, path = '', file_import_options = None, tag_import_options = None, txt_parse_tag_service_keys = None, mimes = None, actions = None, action_locations = None, period = 3600, open_popup = True ):
        
        if mimes is None:
            
            mimes = HC.ALLOWED_MIMES
            
        
        if file_import_options is None:
            
            file_import_options = ClientDefaults.GetDefaultFileImportOptions()
            
        
        if tag_import_options is None:
            
            new_options = HG.client_controller.GetNewOptions()
            
            tag_import_options = new_options.GetDefaultTagImportOptions( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEFAULT ) )
            
        
        if txt_parse_tag_service_keys is None:
            
            txt_parse_tag_service_keys = []
            
        
        if actions is None:
            
            actions = {}
            
            actions[ CC.STATUS_SUCCESSFUL ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_REDUNDANT ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_DELETED ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_FAILED ] = CC.IMPORT_FOLDER_IGNORE
            
        
        if action_locations is None:
            
            action_locations = {}
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._path = path
        self._mimes = mimes
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._txt_parse_tag_service_keys = txt_parse_tag_service_keys
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._open_popup = open_popup
        
        self._path_cache = SeedCache()
        self._last_checked = 0
        self._paused = False
        self._check_now = False
        
    
    def _ActionPaths( self ):
        
        for status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_FAILED ):
            
            action = self._actions[ status ]
            
            if action == CC.IMPORT_FOLDER_DELETE:
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( status )
                    
                    if path is None or HG.view_shutdown:
                        
                        break
                        
                    
                    try:
                        
                        if os.path.exists( path ):
                            
                            ClientData.DeletePath( path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            ClientData.DeletePath( txt_path )
                            
                        
                        self._path_cache.RemoveSeeds( ( path, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to delete ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif action == CC.IMPORT_FOLDER_MOVE:
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( status )
                    
                    if path is None or HG.view_shutdown:
                        
                        break
                        
                    
                    try:
                        
                        if os.path.exists( path ):
                            
                            dest_dir = self._action_locations[ status ]
                            
                            filename = os.path.basename( path )
                            
                            dest_path = os.path.join( dest_dir, filename )
                            
                            dest_path = HydrusPaths.AppendPathUntilNoConflicts( dest_path )
                            
                            HydrusPaths.MergeFile( path, dest_path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            dest_dir = self._action_locations[ status ]
                            
                            txt_filename = os.path.basename( txt_path )
                            
                            txt_dest_path = os.path.join( dest_dir, txt_filename )
                            
                            txt_dest_path = HydrusPaths.AppendPathUntilNoConflicts( txt_dest_path )
                            
                            HydrusPaths.MergeFile( txt_path, txt_dest_path )
                            
                        
                        self._path_cache.RemoveSeeds( ( path, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to move ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif status == CC.IMPORT_FOLDER_IGNORE:
                
                pass
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_txt_parse_tag_service_keys = [ service_key.encode( 'hex' ) for service_key in self._txt_parse_tag_service_keys ]
        serialisable_path_cache = self._path_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = self._actions.items()
        action_location_pairs = self._action_locations.items()
        
        return ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, self._period, self._open_popup, serialisable_path_cache, self._last_checked, self._paused, self._check_now )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_service_keys, action_pairs, action_location_pairs, self._period, self._open_popup, serialisable_path_cache, self._last_checked, self._paused, self._check_now ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._txt_parse_tag_service_keys = [ service_key.decode( 'hex' ) for service_key in serialisable_txt_parse_service_keys ]
        self._path_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_cache )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( path, mimes, serialisable_file_import_options, action_pairs, action_location_pairs, period, open_popup, tag, serialisable_path_cache, last_checked, paused ) = old_serialisable_info
            
            service_keys_to_explicit_tags = {}
            
            if tag is not None:
                
                service_keys_to_explicit_tags[ CC.LOCAL_TAG_SERVICE_KEY ] = { tag }
                
            
            tag_import_options = TagImportOptions( service_keys_to_explicit_tags = service_keys_to_explicit_tags )
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused ) = old_serialisable_info
            
            serialisable_txt_parse_tag_service_keys = []
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused, check_now )
            
            return ( 4, new_serialisable_info )
            
        
    
    def CheckNow( self ):
        
        self._check_now = True
        
    
    def DoWork( self ):
        
        if HG.view_shutdown:
            
            return
            
        
        due_by_check_now = self._check_now
        due_by_period = not self._paused and HydrusData.TimeHasPassed( self._last_checked + self._period )
        
        if due_by_check_now or due_by_period:
            
            if os.path.exists( self._path ) and os.path.isdir( self._path ):
                
                filenames = os.listdir( HydrusData.ToUnicode( self._path ) )
                
                raw_paths = [ os.path.join( self._path, filename ) for filename in filenames ]
                
                all_paths = ClientFiles.GetAllPaths( raw_paths )
                
                all_paths = HydrusPaths.FilterFreePaths( all_paths )
                
                new_paths = []
                
                for path in all_paths:
                    
                    if path.endswith( '.txt' ):
                        
                        continue
                        
                    
                    if not self._path_cache.HasSeed( path ):
                        
                        new_paths.append( path )
                        
                    
                
                self._path_cache.AddSeeds( new_paths )
                
                successful_hashes = set()
                
                i = 0
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                    
                    p1 = HC.options[ 'pause_import_folders_sync' ]
                    p2 = HG.view_shutdown
                    
                    if path is None or p1 or p2:
                        
                        break
                        
                    
                    try:
                        
                        mime = HydrusFileHandling.GetMime( path )
                        
                        if mime in self._mimes:
                            
                            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                            
                            try:
                                
                                copied = HydrusPaths.MirrorFile( path, temp_path )
                                
                                if not copied:
                                    
                                    raise Exception( 'File failed to copy--see log for error.' )
                                    
                                
                                file_import_job = FileImportJob( temp_path, self._file_import_options )
                                
                                client_files_manager = HG.client_controller.client_files_manager
                                
                                ( status, hash ) = client_files_manager.ImportFile( file_import_job )
                                
                            finally:
                                
                                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                                
                            
                            self._path_cache.UpdateSeedStatus( path, status )
                            
                            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                                
                                downloaded_tags = []
                                
                                service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags ) # explicit tags
                                
                                if len( service_keys_to_content_updates ) > 0:
                                    
                                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                    
                                
                                txt_path = path + '.txt'
                                
                                if len( self._txt_parse_tag_service_keys ) > 0 and os.path.exists( txt_path ):
                                    
                                    try:
                                        
                                        with open( txt_path, 'rb' ) as f:
                                            
                                            txt_tags_string = f.read()
                                            
                                        
                                        txt_tags = [ HydrusData.ToUnicode( tag ) for tag in HydrusData.SplitByLinesep( txt_tags_string ) ]
                                        
                                        if True in ( len( txt_tag ) > 1024 for txt_tag in txt_tags ):
                                            
                                            HydrusData.ShowText( 'Tags were too long--I think this was not a regular text file!' )
                                            
                                            raise Exception()
                                            
                                        
                                        txt_tags = HydrusTags.CleanTags( txt_tags )
                                        
                                        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
                                        
                                        service_keys_to_tags = { service_key : siblings_manager.CollapseTags( service_key, txt_tags ) for service_key in self._txt_parse_tag_service_keys }
                                        
                                        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                                        
                                        if len( service_keys_to_content_updates ) > 0:
                                            
                                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                            
                                        
                                    except Exception as e:
                                        
                                        HydrusData.ShowText( 'Trying to load tags from the .txt file "' + txt_path + '" in the import folder "' + self._name + '" threw an error!' )
                                        
                                        HydrusData.ShowException( e )
                                        
                                    
                                
                            
                            if status == CC.STATUS_SUCCESSFUL:
                                
                                successful_hashes.add( hash )
                                
                            
                        else:
                            
                            self._path_cache.UpdateSeedStatus( path, CC.STATUS_UNINTERESTING_MIME )
                            
                        
                    except Exception as e:
                        
                        error_text = traceback.format_exc()
                        
                        HydrusData.Print( 'A file failed to import from import folder ' + self._name + ':' )
                        
                        self._path_cache.UpdateSeedStatus( path, CC.STATUS_FAILED, exception = e )
                        
                    
                    i += 1
                    
                    if i % 10 == 0:
                        
                        self._ActionPaths()
                        
                    
                
                if len( successful_hashes ) > 0:
                    
                    HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusData.ConvertIntToPrettyString( len( successful_hashes ) ) + ' files.' )
                    
                    if self._open_popup:
                        
                        job_key = ClientThreading.JobKey()
                        
                        job_key.SetVariable( 'popup_title', 'import folder - ' + self._name )
                        job_key.SetVariable( 'popup_files', ( successful_hashes, self._name ) )
                        
                        HG.client_controller.pub( 'message', job_key )
                        
                    
                
                self._ActionPaths()
                
            
            self._last_checked = HydrusData.GetNow()
            self._check_now = False
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
    
    def GetSeedCache( self ):
        
        return self._path_cache
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._period )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._mimes, self._file_import_options, self._tag_import_options, self._txt_parse_tag_service_keys, self._actions, self._action_locations, self._period, self._open_popup, self._paused, self._check_now )
        
    
    def SetSeedCache( self, seed_cache ):
        
        self._path_cache = seed_cache
        
    
    def SetTuple( self, name, path, mimes, file_import_options, tag_import_options, txt_parse_tag_service_keys, actions, action_locations, period, open_popup, paused, check_now ):
        
        if path != self._path:
            
            self._path_cache = SeedCache()
            
        
        if set( mimes ) != set( self._mimes ):
            
            self._path_cache.RemoveSeedsByStatus( CC.STATUS_UNINTERESTING_MIME )
            
        
        self._name = name
        self._path = path
        self._mimes = mimes
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._txt_parse_tag_service_keys = txt_parse_tag_service_keys
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._open_popup = open_popup
        self._paused = paused
        self._check_now = check_now
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER ] = ImportFolder

class PageOfImagesImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = ClientDefaults.GetDefaultFileImportOptions()
        
        self._pending_page_urls = []
        self._urls_cache = SeedCache()
        self._file_import_options = file_import_options
        self._download_image_links = True
        self._download_unlinked_images = False
        self._queue_paused = False
        self._files_paused = False
        
        self._parser_status = ''
        self._current_action = ''
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        self._download_control_page_set = None
        self._download_control_page_clear = None
        
        self._lock = threading.Lock()
        
        self._new_files_event = threading.Event()
        self._new_page_event = threading.Event()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        
        return ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._queue_paused, self._files_paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._queue_paused, self._files_paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( pending_page_urls, serialisable_url_cache, serialisable_file_options, download_image_links, download_unlinked_images, paused ) = old_serialisable_info
            
            queue_paused = paused
            files_paused = paused
            
            new_serialisable_info = ( pending_page_urls, serialisable_url_cache, serialisable_file_options, download_image_links, download_unlinked_images, queue_paused, files_paused )
            
            return ( 2, new_serialisable_info )
            
        
    def _WorkOnFiles( self, page_key ):
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return False
            
        
        try:
            
            with self._lock:
                
                self._current_action = 'reviewing file'
                
            
            ( status, hash, note ) = HG.client_controller.Read( 'url_status', file_url )
            
            url_not_known_beforehand = status == CC.STATUS_NEW
            
            if status == CC.STATUS_DELETED:
                
                if not self._file_import_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    note = ''
                    
                
            
            if status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    with self._lock:
                        
                        self._current_action = 'downloading file'
                        
                    
                    network_job = ClientNetworking.NetworkJob( 'GET', file_url, temp_path = temp_path )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    with self._lock:
                        
                        if self._download_control_file_set is not None:
                            
                            wx.CallAfter( self._download_control_file_set, network_job )
                            
                        
                    
                    try:
                        
                        network_job.WaitUntilDone()
                        
                    except HydrusExceptions.ShutdownException:
                        
                        return True
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = 'cancelled during download!' )
                        
                        return True
                        
                    except HydrusExceptions.NotFoundException:
                        
                        status = CC.STATUS_FAILED
                        note = '404'
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
                        
                        time.sleep( 2 )
                        
                        return True
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return True
                        
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    with self._lock:
                        
                        self._current_action = 'importing file'
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    self._urls_cache.UpdateSeedStatus( file_url, status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
                
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        return True
        
    
    def _WorkOnQueue( self, page_key ):
        
        if len( self._pending_page_urls ) > 0:
            
            with self._lock:
                
                page_url = self._pending_page_urls.pop( 0 )
                
                self._parser_status = 'checking ' + page_url
                
            
            error_occurred = False
            
            try:
                
                network_job = ClientNetworking.NetworkJob( 'GET', page_url )
                
                network_job.OverrideBandwidth()
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                with self._lock:
                    
                    if self._download_control_page_set is not None:
                        
                        wx.CallAfter( self._download_control_page_set, network_job )
                        
                    
                
                try:
                    
                    network_job.WaitUntilDone()
                    
                finally:
                    
                    if self._download_control_page_clear is not None:
                        
                        wx.CallAfter( self._download_control_page_clear )
                        
                    
                
                html = network_job.GetContent()
                
                soup = ClientDownloading.GetSoup( html )
                
                #
                
                all_links = soup.find_all( 'a' )
                
                links_with_images = [ link for link in all_links if len( link.find_all( 'img' ) ) > 0 ]
                
                all_linked_images = []
                
                for link in all_links:
                    
                    images = link.find_all( 'img' )
                    
                    all_linked_images.extend( images )
                    
                
                all_images = soup.find_all( 'img' )
                
                unlinked_images = [ image for image in all_images if image not in all_linked_images ]
                
                #
                
                file_urls = []
                
                if self._download_image_links:
                    
                    file_urls.extend( [ urlparse.urljoin( page_url, link[ 'href' ] ) for link in links_with_images if link.has_attr( 'href' ) ] )
                    
                
                if self._download_unlinked_images:
                    
                    file_urls.extend( [ urlparse.urljoin( page_url, image[ 'src' ] ) for image in unlinked_images if image.has_attr( 'src' ) ] )
                    
                
                new_urls = [ file_url for file_url in file_urls if not self._urls_cache.HasSeed( file_url ) ]
                
                self._urls_cache.AddSeeds( new_urls )
                
                num_new = len( new_urls )
                
                if num_new > 0:
                    
                    self._new_files_event.set()
                    
                
                parser_status = 'page checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
                
                num_already_in_seed_cache = len( file_urls ) - num_new
                
                if num_already_in_seed_cache > 0:
                    
                    parser_status += ' (' + HydrusData.ConvertIntToPrettyString( num_already_in_seed_cache ) + ' already in queue)'
                    
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                parser_status = 'page 404'
                
            except Exception as e:
                
                error_occurred = True
                
                parser_status = HydrusData.ToUnicode( e )
                
            
            with self._lock:
                
                self._parser_status = parser_status
                
            
            if error_occurred:
                
                time.sleep( 5 )
                
            
            return True
            
        else:
            
            with self._lock:
                
                self._parser_status = ''
                
            
            return False
            
        
    
    def _THREADWorkOnFiles( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnFiles( page_key )
                    
                    if did_work:
                        
                        time.sleep( DID_FILE_WORK_MINIMUM_SLEEP_TIME )
                        
                    else:
                        
                        self._new_files_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_files_event.clear()
            
        
    
    def _THREADWorkOnQueue( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._queue_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_page_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnQueue( page_key )
                    
                    if did_work:
                        
                        time.sleep( 5 )
                        
                    else:
                        
                        self._new_page_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_page_event.clear()
            
        
    
    def AdvancePageURL( self, page_url ):
        
        with self._lock:
            
            if page_url in self._pending_page_urls:
                
                index = self._pending_page_urls.index( page_url )
                
                if index - 1 >= 0:
                    
                    self._pending_page_urls.remove( page_url )
                    
                    self._pending_page_urls.insert( index - 1, page_url )
                    
                
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._urls_cache.WorkToDo() or len( self._pending_page_urls ) > 0
            
            return not finished and not self._files_paused
            
        
    
    def DelayPageURL( self, page_url ):
        
        with self._lock:
            
            if page_url in self._pending_page_urls:
                
                index = self._pending_page_urls.index( page_url )
                
                if index + 1 < len( self._pending_page_urls ):
                    
                    self._pending_page_urls.remove( page_url )
                    
                    self._pending_page_urls.insert( index + 1, page_url )
                    
                
            
        
    
    def DeletePageURL( self, page_url ):
        
        with self._lock:
            
            if page_url in self._pending_page_urls:
                
                self._pending_page_urls.remove( page_url )
                
            
        
    
    def GetSeedCache( self ):
        
        return self._urls_cache
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._download_image_links, self._download_unlinked_images )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( list( self._pending_page_urls ), self._parser_status, self._current_action, self._queue_paused, self._files_paused )
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            self._new_files_event.set()
            
        
    
    def PausePlayQueue( self ):
        
        with self._lock:
            
            self._queue_paused = not self._queue_paused
            
            self._new_page_event.set()
            
        
    
    def PendPageURL( self, page_url ):
        
        with self._lock:
            
            if page_url not in self._pending_page_urls:
                
                self._pending_page_urls.append( page_url )
                
                self._new_page_event.set()
                
            
        
    
    def SetDownloadControlFile( self, download_control ):
        
        with self._lock:
            
            self._download_control_file_set = download_control.SetNetworkJob
            self._download_control_file_clear = download_control.ClearNetworkJob
            
        
    
    def SetDownloadControlPage( self, download_control ):
        
        with self._lock:
            
            self._download_control_page_set = download_control.SetNetworkJob
            self._download_control_page_clear = download_control.ClearNetworkJob
            
        
    
    def SetDownloadImageLinks( self, value ):
        
        with self._lock:
            
            self._download_image_links = value
            
        
    
    def SetDownloadUnlinkedImages( self, value ):
        
        with self._lock:
            
            self._download_unlinked_images = value
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnQueue, page_key )
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnFiles, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT ] = PageOfImagesImport

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_VERSION = 7
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds_ordered = []
        self._seeds_to_info = {}
        
        self._seeds_to_indices = {}
        
        self._seed_cache_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        
        self._dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._seeds_to_info )
        
    
    def _GenerateStatus( self ):
        
        statuses_to_counts = collections.Counter()
        
        for seed_info in self._seeds_to_info.values():
            
            statuses_to_counts[ seed_info[ 'status' ] ] += 1
            
        
        num_successful = statuses_to_counts[ CC.STATUS_SUCCESSFUL ]
        num_failed = statuses_to_counts[ CC.STATUS_FAILED ]
        num_deleted = statuses_to_counts[ CC.STATUS_DELETED ]
        num_redundant = statuses_to_counts[ CC.STATUS_REDUNDANT ]
        num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
        
        status_strings = []
        
        if num_successful > 0: status_strings.append( str( num_successful ) + ' successful' )
        if num_failed > 0: status_strings.append( str( num_failed ) + ' failed' )
        if num_deleted > 0: status_strings.append( str( num_deleted ) + ' previously deleted' )
        if num_redundant > 0: status_strings.append( str( num_redundant ) + ' already in db' )
        
        status = ', '.join( status_strings )
        
        total = len( self._seeds_ordered )
        
        total_processed = total - num_unknown
        
        self._status_cache = ( status, ( total_processed, total ) )
        
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            serialisable_info = []
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                serialisable_info.append( ( seed, seed_info ) )
                
            
            return serialisable_info
            
        
    
    def _GetAddedTimestamp( self, seed ):
        
        seed_info = self._seeds_to_info[ seed ]
        
        added_timestamp = seed_info[ 'added_timestamp' ]
        
        return added_timestamp
        
    
    def _GetSourceTimestamp( self, seed ):
        
        seed_info = self._seeds_to_info[ seed ]
        
        source_timestamp = seed_info[ 'source_timestamp' ]
        
        if source_timestamp is None:
            
            # decent fallback compromise
            # -30 since added and 'last check' timestamps are often the same, and this messes up calculations
            
            source_timestamp = seed_info[ 'added_timestamp' ] - 30
            
        
        return source_timestamp
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            for ( seed, seed_info ) in serialisable_info:
                
                self._seeds_ordered.append( seed )
                
                self._seeds_to_info[ seed ] = seed_info
                
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                if 'note' in seed_info:
                    
                    seed_info[ 'note' ] = HydrusData.ToUnicode( seed_info[ 'note' ] )
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version in ( 2, 3 ):
            
            # gelbooru replaced their thumbnail links with this redirect spam
            # 'https://gelbooru.com/redirect.php?s=Ly9nZWxib29ydS5jb20vaW5kZXgucGhwP3BhZ2U9cG9zdCZzPXZpZXcmaWQ9MzY4ODA1OA=='
            
            # I missed some http ones here, so I've broadened the test and rescheduled it
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                if 'gelbooru.com/redirect.php' in seed:
                    
                    continue
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            def ConvertRegularToRawURL( regular_url ):
                
                # convert this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_500.jpg
                # to this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                # the 500 part can be a bunch of stuff, including letters
                
                url_components = regular_url.split( '_' )
                
                last_component = url_components[ -1 ]
                
                ( number_gubbins, file_ext ) = last_component.split( '.' )
                
                raw_last_component = 'raw.' + file_ext
                
                url_components[ -1 ] = raw_last_component
                
                raw_url = '_'.join( url_components )
                
                return raw_url
                
            
            def Remove68Subdomain( long_url ):
                
                # sometimes the 68 subdomain gives a 404 on the raw url, so:
                
                # convert this:
                # http://68.media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                # to this:
                # http://media.tumblr.com/5af0d991f26ef9fdad5a0c743fb1eca2/tumblr_opl012ZBOu1tiyj7vo1_raw.jpg
                
                # I am not sure if it is always 68, but let's not assume
                
                ( scheme, rest ) = long_url.split( '://', 1 )
                
                if rest.startswith( 'media.tumblr.com' ):
                    
                    return long_url
                    
                
                ( gumpf, shorter_rest ) = rest.split( '.', 1 )
                
                shorter_url = scheme + '://' + shorter_rest
                
                return shorter_url
                
            
            new_serialisable_info = []
            
            good_seeds = set()
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                try:
                    
                    parse = urlparse.urlparse( seed )
                    
                    if 'media.tumblr.com' in parse.netloc:
                        
                        seed = Remove68Subdomain( seed )
                        
                        seed = ConvertRegularToRawURL( seed )
                        
                        seed = ClientData.ConvertHTTPToHTTPS( seed )
                        
                    
                    if 'pixiv.net' in parse.netloc:
                        
                        seed = ClientData.ConvertHTTPToHTTPS( seed )
                        
                    
                    if seed in good_seeds: # we hit a dupe, so skip it
                        
                        continue
                        
                    
                except:
                    
                    pass
                    
                
                good_seeds.add( seed )
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                seed_info[ 'source_timestamp' ] = None
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                try:
                    
                    magic_phrase = '//media.tumblr.com'
                    replacement = '//data.tumblr.com'
                    
                    if magic_phrase in seed:
                        
                        seed = seed.replace( magic_phrase, replacement )
                        
                    
                except:
                    
                    pass
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 7, new_serialisable_info )
            
        
    
    def AddSeeds( self, seeds ):
        
        if len( seeds ) == 0:
            
            return
            
        
        with self._lock:
            
            for seed in seeds:
                
                if seed.startswith( 'http' ): # i.e. it is an url, either http or https, rather than a local file path
                    
                    search_seeds = ClientData.GetSearchURLs( seed )
                    
                else:
                    
                    search_seeds = [ seed ]
                    
                
                already_in_cache = True in ( search_seed in self._seeds_to_info for search_seed in search_seeds )
                
                if already_in_cache:
                    
                    continue
                    
                
                self._seeds_ordered.append( seed )
                
                self._seeds_to_indices[ seed ] = len( self._seeds_ordered ) - 1
                
                now = HydrusData.GetNow()
                
                seed_info = {}
                
                seed_info[ 'status' ] = CC.STATUS_UNKNOWN
                seed_info[ 'added_timestamp' ] = now
                seed_info[ 'last_modified_timestamp' ] = now
                seed_info[ 'source_timestamp' ] = None
                seed_info[ 'note' ] = ''
                
                self._seeds_to_info[ seed ] = seed_info
                
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_to_indices[ seed ]
                
                if index > 0:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index - 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
                
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, ( seed, ) )
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_to_indices[ seed ]
                
                if index < len( self._seeds_ordered ) - 1:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index + 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
                
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, ( seed, ) )
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            earliest_timestamp = min( ( self._GetSourceTimestamp( seed ) for seed in self._seeds_ordered ) )
            
        
        return earliest_timestamp
        
    
    def GetLatestAddedTime( self ):
        
        with self._lock:
            
            if len( self._seeds_ordered ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetAddedTimestamp( seed ) for seed in self._seeds_ordered ) )
            
        
        return latest_timestamp
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._seeds_ordered ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestamp( seed ) for seed in self._seeds_ordered ) )
            
        
        return latest_timestamp
        
    
    def GetNextSeed( self, status ):
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                if seed_info[ 'status' ] == status:
                    
                    return seed
                    
                
            
        
        return None
        
    
    def GetNumNewFilesSince( self, since ):
        
        num_files = 0
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                source_timestamp = self._GetSourceTimestamp( seed )
                
                if source_timestamp > since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetSeedCacheKey( self ):
        
        return self._seed_cache_key
        
    
    def GetSeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._seeds_ordered )
                
            else:
                
                for seed in self._seeds_ordered:
                    
                    seed_info = self._seeds_to_info[ seed ]
                    
                    if seed_info[ 'status' ] == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetSeeds( self, status = None ):
        
        with self._lock:
            
            if status is None:
                
                return list( self._seeds_ordered )
                
            else:
                
                seeds = []
                
                for seed in self._seeds_ordered:
                    
                    seed_info = self._seeds_to_info[ seed ]
                    
                    if seed_info[ 'status' ] == status:
                        
                        seeds.append( seed )
                        
                    
                
                return seeds
                
            
        
    
    def GetSeedInfo( self, seed ):
        
        with self._lock:
            
            seed_index = self._seeds_to_indices[ seed ]
            
            seed_info = self._seeds_to_info[ seed ]
            
            status = seed_info[ 'status' ]
            added_timestamp = seed_info[ 'added_timestamp' ]
            last_modified_timestamp = seed_info[ 'last_modified_timestamp' ]
            source_timestamp = seed_info[ 'source_timestamp' ]
            note = seed_info[ 'note' ]
            
            return ( seed_index, seed, status, added_timestamp, last_modified_timestamp, source_timestamp, note )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def HasSeed( self, seed ):
        
        with self._lock:
            
            if seed.startswith( 'http' ):
                
                search_seeds = ClientData.GetSearchURLs( seed )
                
            else:
                
                search_seeds = [ seed ]
                
            
            for search_seed in search_seeds:
                
                if search_seed in self._seeds_to_info:
                    
                    return True
                    
                
            
            return False
            
        
    
    def RemoveProcessedSeeds( self ):
        
        with self._lock:
            
            seeds_to_delete = set()
            
            for ( seed, seed_info ) in self._seeds_to_info.items():
                
                if seed_info[ 'status' ] != CC.STATUS_UNKNOWN:
                    
                    seeds_to_delete.add( seed )
                    
                
            
            for seed in seeds_to_delete:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds_to_delete )
        
    
    def RemoveSeeds( self, seeds ):
        
        with self._lock:
            
            for seed in seeds:
                
                if seed in self._seeds_to_info:
                    
                    del self._seeds_to_info[ seed ]
                    
                    self._seeds_ordered.remove( seed )
                    
                
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds )
        
    
    def RemoveSeedsByStatus( self, status ):
        
        with self._lock:
            
            seeds_to_delete = set()
            
            for ( seed, seed_info ) in self._seeds_to_info.items():
                
                if seed_info[ 'status' ] == status:
                    
                    seeds_to_delete.add( seed )
                    
                
            
            for seed in seeds_to_delete:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds_ordered ) }
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds_to_delete )
        
    
    def RetryFailures( self ):
        
        failed_seeds = self.GetSeeds( CC.STATUS_FAILED )
        
        self.UpdateSeedsStatus( failed_seeds, CC.STATUS_UNKNOWN )
        
    
    def UpdateSeedSourceTime( self, seed, source_timestamp ):
        
        # this is ugly--this should all be moved to the seed when it becomes a cleverer object, rather than jimmying it through the cache
        
        with self._lock:
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'source_timestamp' ] = source_timestamp
            
        
    
    def UpdateSeedStatus( self, seed, status, note = '', exception = None ):
        
        with self._lock:
            
            if exception is not None:
                
                first_line = HydrusData.ToUnicode( exception ).split( os.linesep )[0]
                
                note = first_line + u'\u2026 (Copy note to see full error)'
                note += os.linesep
                note += HydrusData.ToUnicode( traceback.format_exc() )
                
                HydrusData.Print( 'Error when processing ' + seed + ' !' )
                HydrusData.Print( traceback.format_exc() )
                
            
            note = HydrusData.ToUnicode( note )
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'status' ] = status
            seed_info[ 'last_modified_timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = note
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, ( seed, ) )
        
    
    def UpdateSeedsStatus( self, seeds, status ):
        
        with self._lock:
            
            for seed in seeds:
                
                seed_info = self._seeds_to_info[ seed ]
                
                seed_info[ 'status' ] = status
                seed_info[ 'last_modified_timestamp' ] = HydrusData.GetNow()
                seed_info[ 'note' ] = ''
                
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._GenerateStatus()
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_VERSION = 4
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        self._queries = []
        
        new_options = HG.client_controller.new_options
        
        self._checker_options = ClientData.CheckerOptions( intended_files_per_check = 5, never_faster_than = 86400, never_slower_than = 90 * 86400, death_file_velocity = ( 1, 90 * 86400 ) )
        self._get_tags_if_url_known_and_file_redundant = new_options.GetBoolean( 'get_tags_if_url_known_and_file_redundant' )
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 200
            
        else:
            
            self._initial_file_limit = min( 200, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 50
        self._paused = False
        
        self._file_import_options = ClientDefaults.GetDefaultFileImportOptions()
        
        new_options = HG.client_controller.GetNewOptions()
        
        self._tag_import_options = new_options.GetDefaultTagImportOptions( self._gallery_identifier )
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        serialisable_queries = [ query.GetSerialisableTuple() for query in self._queries ]
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._no_work_until, self._no_work_until_reason )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._no_work_until, self._no_work_until_reason ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        self._queries = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_queries ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _NoDelays( self ):
        
        return HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, last_error, serialisable_seed_cache ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, serialisable_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, serialisable_seed_cache ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_seed_cache )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_seed_cache ) = old_serialisable_info
            
            checker_options = ClientData.CheckerOptions( 5, period / 5, period * 10, ( 1, period * 10 ) )
            
            seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_seed_cache )
            
            query = SubscriptionQuery( query )
            
            query._seed_cache = seed_cache
            query._last_check_time = last_checked
            
            query.UpdateNextCheckTime( checker_options )
            
            queries = [ query ]
            
            serialisable_queries = [ query.GetSerialisableTuple() for query in queries ]
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, job_key ):
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name, method, url, **kwargs )
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
            return network_job
            
        
        gallery = ClientDownloading.GetGallery( self._gallery_identifier )
        
        gallery.SetNetworkJobFactory( network_job_factory )
        
        error_count = 0
        
        for query in self._queries:
            
            ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
            
            num_urls = seed_cache.GetSeedCount()
            
            successful_hashes = set()
            
            while True:
                
                num_unknown = seed_cache.GetSeedCount( CC.STATUS_UNKNOWN )
                num_done = num_urls - num_unknown
                
                url = seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                
                if url is None:
                    
                    break
                    
                
                if job_key.IsCancelled():
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p3 = HG.view_shutdown
                
                example_nj = network_job_factory( 'GET', url )
                
                # just a little padding, to make sure we don't accidentally get into a long wait because we need to fetch file and tags independantly etc...
                expected_requests = 3
                expected_bytes = 1048576
                
                p4 = not HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), expected_requests, expected_bytes )
                
                if p1 or p3 or p4:
                    
                    if p4:
                        
                        job_key.SetVariable( 'popup_text_1', 'no more bandwidth to download files, so stopping for now' )
                        
                        time.sleep( 2 )
                        
                    
                    break
                    
                
                try:
                    
                    x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_urls ) + ': '
                    
                    job_key.SetVariable( 'popup_text_1', x_out_of_y + 'checking url status' )
                    job_key.SetVariable( 'popup_gauge_1', ( num_done, num_urls ) )
                    
                    ( status, hash, note ) = HG.client_controller.Read( 'url_status', url )
                    
                    if status == CC.STATUS_DELETED:
                        
                        if not self._file_import_options.GetExcludeDeleted():
                            
                            status = CC.STATUS_NEW
                            note = ''
                            
                        
                    
                    downloaded_tags = []
                    
                    if status == CC.STATUS_REDUNDANT:
                        
                        if self._get_tags_if_url_known_and_file_redundant and self._tag_import_options.InterestedInTags():
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'found file in db, fetching tags' )
                            
                            downloaded_tags = gallery.GetTags( url )
                            
                        
                    elif status == CC.STATUS_NEW:
                        
                        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                        
                        try:
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'downloading file' )
                            
                            if self._tag_import_options.InterestedInTags():
                                
                                downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                                
                            else:
                                
                                gallery.GetFile( temp_path, url )
                                
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'importing file' )
                            
                            file_import_job = FileImportJob( temp_path, self._file_import_options )
                            
                            ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                            
                            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( url, ) ) ) ] }
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                            if status == CC.STATUS_SUCCESSFUL:
                                
                                job_key.SetVariable( 'popup_text_1', x_out_of_y + 'import successful' )
                                
                                successful_hashes.add( hash )
                                
                            elif status == CC.STATUS_DELETED:
                                
                                job_key.SetVariable( 'popup_text_1', x_out_of_y + 'previously deleted' )
                                
                            elif status == CC.STATUS_REDUNDANT:
                                
                                job_key.SetVariable( 'popup_text_1', x_out_of_y + 'already in db' )
                                
                            
                        finally:
                            
                            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                    
                    seed_cache.UpdateSeedStatus( url, status, note = note )
                    
                    if hash is not None:
                        
                        service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                        
                        if len( service_keys_to_content_updates ) > 0:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                    
                except HydrusExceptions.CancelledException:
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                except HydrusExceptions.MimeException as e:
                    
                    status = CC.STATUS_UNINTERESTING_MIME
                    
                    seed_cache.UpdateSeedStatus( url, status )
                    
                except Exception as e:
                    
                    status = CC.STATUS_FAILED
                    
                    job_key.SetVariable( 'popup_text_1', x_out_of_y + 'file failed' )
                    
                    if isinstance( e, HydrusExceptions.NotFoundException ):
                        
                        seed_cache.UpdateSeedStatus( url, status, note = '404' )
                        
                    else:
                        
                        seed_cache.UpdateSeedStatus( url, status, exception = e )
                        
                    
                    # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                    # this should be richer in any case in the new system
                    if not isinstance( e, HydrusExceptions.DataMissing ):
                        
                        error_count += 1
                        
                        time.sleep( 10 )
                        
                    
                    if error_count > 4:
                        
                        raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                        
                    
                
                if len( successful_hashes ) > 0:
                    
                    job_key.SetVariable( 'popup_files', ( set( successful_hashes ), self._name + ' ' + query_text ) )
                    
                
                time.sleep( 0.1 )
                
                HG.client_controller.WaitUntilViewFree()
                
            
            if len( successful_hashes ) > 0:
                
                files_job_key = ClientThreading.JobKey()
                
                files_job_key.SetVariable( 'popup_files', ( set( successful_hashes ), self._name + ' - ' + query_text ) )
                
                HG.client_controller.pub( 'message', files_job_key )
                
            
        
        job_key.DeleteVariable( 'popup_files' )
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_gauge_1' )
        
    
    def _WorkOnFilesCanDoWork( self ):
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name, method, url, **kwargs )
            
            # this is prob actually a call to the job_key
            #wx.CallAfter( self._download_control_set, network_job )
            
            return network_job
            
        
        for query in self._queries:
            
            if query.CanWorkOnFiles():
                
                ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
                
                url = seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                
                example_nj = network_job_factory( 'GET', url )
                
                # just a little padding here
                expected_requests = 3
                expected_bytes = 1048576
                
                if HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), expected_requests, expected_bytes ):
                    
                    return True
                    
                
            
        
        return False
        
    
    def _SyncQuery( self, job_key ):
        
        for query in self._queries:
            
            if not query.CanSync():
                
                continue
                
            
            ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
            
            this_is_initial_sync = query.IsInitialSync()
            total_new_urls = 0
            
            urls_to_add = set()
            urls_to_add_ordered = []
            
            prefix = 'synchronising gallery query'
            
            job_key.SetVariable( 'popup_text_1', prefix )
            
            for gallery_stream_identifier in self._gallery_stream_identifiers:
                
                if this_is_initial_sync:
                    
                    if self._initial_file_limit is not None and total_new_urls + 1 > self._initial_file_limit:
                        
                        break
                        
                    
                else:
                    
                    if self._periodic_file_limit is not None and total_new_urls + 1 > self._periodic_file_limit:
                        
                        break
                        
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p2 = job_key.IsCancelled()
                p3 = HG.view_shutdown
                
                if p1 or p2 or p3:
                    
                    break
                    
                
                def network_job_factory( method, url, **kwargs ):
                    
                    network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name, method, url, **kwargs )
                    
                    job_key.SetVariable( 'popup_network_job', network_job )
                    
                    network_job.OverrideBandwidth()
                    
                    return network_job
                    
                
                gallery = ClientDownloading.GetGallery( gallery_stream_identifier )
                
                gallery.SetNetworkJobFactory( network_job_factory )
                
                page_index = 0
                num_existing_urls = 0
                keep_checking = True
                
                while keep_checking:
                    
                    new_urls_this_page = 0
                    
                    try:
                        
                        p1 = HC.options[ 'pause_subs_sync' ]
                        p2 = HG.view_shutdown
                        
                        if p1 or p2:
                            
                            return
                            
                        
                        if job_key.IsCancelled():
                            
                            raise HydrusExceptions.CancelledException()
                            
                        
                        ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( query_text, page_index )
                        
                        page_index += 1
                        
                        if definitely_no_more_pages:
                            
                            keep_checking = False
                            
                        
                        for url in page_of_urls:
                            
                            if this_is_initial_sync:
                                
                                if self._initial_file_limit is not None and total_new_urls + 1 > self._initial_file_limit:
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            else:
                                
                                if self._periodic_file_limit is not None and total_new_urls + 1 > self._periodic_file_limit:
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            
                            if url in urls_to_add:
                                
                                # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                                
                                continue
                                
                            
                            if seed_cache.HasSeed( url ):
                                
                                num_existing_urls += 1
                                
                                if num_existing_urls > 5:
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            else:
                                
                                urls_to_add.add( url )
                                urls_to_add_ordered.append( url )
                                
                                new_urls_this_page += 1
                                total_new_urls += 1
                                
                            
                        
                    except HydrusExceptions.CancelledException:
                        
                        self._DelayWork( 300, 'gallery parse was cancelled' )
                        
                        break
                        
                    except HydrusExceptions.NotFoundException:
                        
                        # paheal now 404s when no results, so just move on and naturally break
                        
                        pass
                        
                    
                    if new_urls_this_page == 0:
                        
                        keep_checking = False
                        
                    
                    job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ConvertIntToPrettyString( total_new_urls ) + ' new urls' )
                    
                    time.sleep( 5 )
                    
                
            
            query.RegisterSyncComplete()
            query.UpdateNextCheckTime( self._checker_options )
            
            urls_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the seed_cache should stay roughly in oldest->newest order
            
            new_urls = [ url for url in urls_to_add_ordered if not seed_cache.HasSeed( url ) ]
            
            seed_cache.AddSeeds( new_urls )
            
        
    
    def _SyncQueryCanDoWork( self ):
        
        return True in ( query.CanSync() for query in self._queries )
        
    
    def CanCheckNow( self ):
        
        return True in ( query.CanCheckNow() for query in self._queries )
        
    
    def CanReset( self ):
        
        return True in ( not query.IsInitialSync() for query in self._queries )
        
    
    def CanRetryFailures( self ):
        
        return True in ( query.CanRetryFailed() for query in self._queries )
        
    
    def CanScrubDelay( self ):
        
        return not HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query in self._queries:
            
            query.CheckNow()
            
        
    
    def GetDelayInfo( self ):
        
        return ( self._no_work_until, self._no_work_until_reason )
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetQueries( self ):
        
        return self._queries
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def Merge( self, potential_mergee_subscriptions ):
        
        unmergable_subscriptions = []
        
        for subscription in potential_mergee_subscriptions:
            
            if subscription._gallery_identifier == self._gallery_identifier:
                
                my_new_queries = [ query.Duplicate() for query in subscription._queries ]
                
                self._queries.extend( my_new_queries )
                
            else:
                
                unmergable_subscriptions.append( subscription )
                
            
        
        return unmergable_subscriptions
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def Reset( self ):
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        for query in self._queries:
            
            query.Reset()
            
        
    
    def Separate( self ):
        
        subscriptions = []
        
        for query in self._queries:
            
            subscription = self.Duplicate()
            
            subscription._queries = [ query.Duplicate() ]
            
            subscriptions.append( subscription )
            
        
        return subscriptions
        
    
    def SetTuple( self, gallery_identifier, gallery_stream_identifiers, queries, checker_options, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until ):
        
        self._gallery_identifier = gallery_identifier
        self._gallery_stream_identifiers = gallery_stream_identifiers
        self._queries = queries
        self._checker_options = checker_options
        self._get_tags_if_url_known_and_file_redundant = get_tags_if_url_known_and_file_redundant
        self._initial_file_limit = initial_file_limit
        self._periodic_file_limit = periodic_file_limit
        self._paused = paused
        
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        
        self._no_work_until = no_work_until
        
    
    def ScrubDelay( self ):
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
    
    def Sync( self ):
        
        p1 = not self._paused
        p2 = not HG.view_shutdown
        p3 = self._NoDelays()
        p4 = self._SyncQueryCanDoWork()
        p5 = self._WorkOnFilesCanDoWork()
        
        if p1 and p2 and p3 and ( p4 or p5 ):
            
            job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
            
            try:
                
                job_key.SetVariable( 'popup_title', 'subscriptions - ' + self._name )
                
                HG.client_controller.pub( 'message', job_key )
                
                self._SyncQuery( job_key )
                
                self._WorkOnFiles( job_key )
                
            except HydrusExceptions.NetworkException as e:
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.PrintException( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._DelayWork( HC.UPDATE_DURATION, 'network error: ' + HydrusData.ToUnicode( e ) )
                
                time.sleep( 5 )
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                self._DelayWork( HC.UPDATE_DURATION, 'error: ' + HydrusData.ToUnicode( e ) )
                
            finally:
                
                job_key.DeleteVariable( 'popup_network_job' )
                
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
            if job_key.HasVariable( 'popup_files' ):
                
                job_key.Finish()
                
            else:
                
                job_key.Delete()
                
            
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gallery_identifier, self._gallery_stream_identifiers, self._queries, self._checker_options, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, self._file_import_options, self._tag_import_options, self._no_work_until, self._no_work_until_reason )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class SubscriptionQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY
    SERIALISABLE_VERSION = 1
    
    def __init__( self, query = 'query text' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._query = query
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._status = CHECKER_STATUS_OK
        self._seed_cache = SeedCache()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_seed_cache = self._seed_cache.GetSerialisableTuple()
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_seed_cache ) = serialisable_info
        
        self._seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_seed_cache )
        
    
    def CanWorkOnFiles( self ):
        
        url = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        return url is not None
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanRetryFailed( self ):
        
        return self._seed_cache.GetSeedCount( CC.STATUS_FAILED ) > 0
        
    
    def CanSync( self ):
        
        if self._paused:
            
            return False
            
        
        return HydrusData.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
    
    def GetLastChecked( self ):
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._seed_cache.GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._paused:
            
            return 'paused, but would be ' + HydrusData.ConvertTimestampToPrettyPending( self._next_check_time )
            
        elif self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._status == CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        else:
            
            return HydrusData.ConvertTimestampToPrettyPending( self._next_check_time )
            
        
    
    def GetNumURLsAndFailed( self ):
        
        return ( self._seed_cache.GetSeedCount( CC.STATUS_UNKNOWN ), len( self._seed_cache ), self._seed_cache.GetSeedCount( CC.STATUS_FAILED ) )
        
    
    def GetQueryAndSeedCache( self ):
        
        return ( self._query, self._seed_cache )
        
    
    def IsDead( self ):
        
        return self._status == CHECKER_STATUS_DEAD
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self ):
        
        self._last_check_time = HydrusData.GetNow()
        
        self._check_now = False
        
    
    def Reset( self ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._status = CHECKER_STATUS_OK
        self._paused = False
        
        self._seed_cache = SeedCache()
        
    
    def SetCheckNow( self, check_now ):
        
        self._check_now = check_now
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
    
    def SetQueryAndSeedCache( self, query, seed_cache ):
        
        self._query = query
        self._seed_cache = seed_cache
        
    
    def UpdateNextCheckTime( self, checker_options ):
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._status = CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._seed_cache, self._last_check_time ):
                
                self._status = CHECKER_STATUS_DEAD
                
                self._paused = True
                
            else:
                
                self._status = CHECKER_STATUS_OK
                
            
            self._next_check_time = checker_options.GetNextCheckTime( self._seed_cache, self._last_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, self._seed_cache )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_VERSION = 2
    
    def __init__( self, service_keys_to_namespaces = None, service_keys_to_explicit_tags = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if service_keys_to_namespaces is None:
            
            service_keys_to_namespaces = {}
            
        
        if service_keys_to_explicit_tags is None:
            
            service_keys_to_explicit_tags = {}
            
        
        self._service_keys_to_namespaces = service_keys_to_namespaces
        self._service_keys_to_explicit_tags = service_keys_to_explicit_tags
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            test_func = services_manager.ServiceExists
            
        else:
            
            def test_func( service_key ):
                
                return True
                
            
        
        safe_service_keys_to_namespaces = { service_key.encode( 'hex' ) : list( namespaces ) for ( service_key, namespaces ) in self._service_keys_to_namespaces.items() if test_func( service_key ) }
        safe_service_keys_to_explicit_tags = { service_key.encode( 'hex' ) : list( tags ) for ( service_key, tags ) in self._service_keys_to_explicit_tags.items() if test_func( service_key ) }
        
        return ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags ) = serialisable_info
        
        self._service_keys_to_namespaces = { service_key.decode( 'hex' ) : set( namespaces ) for ( service_key, namespaces ) in safe_service_keys_to_namespaces.items() }
        self._service_keys_to_explicit_tags = { service_key.decode( 'hex' ) : set( tags ) for ( service_key, tags ) in safe_service_keys_to_explicit_tags.items() }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            safe_service_keys_to_namespaces = old_serialisable_info
            
            safe_service_keys_to_explicit_tags = {}
            
            new_serialisable_info = ( safe_service_keys_to_namespaces, safe_service_keys_to_explicit_tags )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetServiceKeysToExplicitTags( self ):
        
        return dict( self._service_keys_to_explicit_tags )
        
    
    def GetServiceKeysToNamespaces( self ):
        
        return dict( self._service_keys_to_namespaces )
        
    
    def GetServiceKeysToContentUpdates( self, hash, tags ):
        
        tags = [ tag for tag in tags if tag is not None ]
        
        service_keys_to_tags = collections.defaultdict( set )
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        
        for ( service_key, namespaces ) in self._service_keys_to_namespaces.items():
            
            tags_to_add_here = []
            
            if len( namespaces ) > 0:
                
                for namespace in namespaces:
                    
                    if namespace == '': tags_to_add_here.extend( [ tag for tag in tags if not ':' in tag ] )
                    else: tags_to_add_here.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                    
                
            
            tags_to_add_here = HydrusTags.CleanTags( tags_to_add_here )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        for ( service_key, explicit_tags ) in self._service_keys_to_explicit_tags.items():
            
            tags_to_add_here = HydrusTags.CleanTags( explicit_tags )
            
            if len( tags_to_add_here ) > 0:
                
                tags_to_add_here = siblings_manager.CollapseTags( service_key, tags_to_add_here )
                tags_to_add_here = parents_manager.ExpandTags( service_key, tags_to_add_here )
                
                service_keys_to_tags[ service_key ].update( tags_to_add_here )
                
            
        
        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
        
        return service_keys_to_content_updates
        
    
    def GetSummary( self ):
        
        service_keys_to_do = set( self._service_keys_to_explicit_tags.keys() ).union( self._service_keys_to_namespaces.keys() )
        
        service_keys_to_do = list( service_keys_to_do )
        
        service_keys_to_do.sort()
        
        service_statements = []
        
        for service_key in service_keys_to_do:
            
            statements = []
            
            if service_key in self._service_keys_to_namespaces:
                
                namespaces = list( self._service_keys_to_namespaces[ service_key ] )
                
                if len( namespaces ) > 0:
                    
                    namespaces = [ ClientTags.RenderNamespaceForUser( namespace ) for namespace in namespaces ]
                    
                    namespaces.sort()
                    
                    statements.append( 'namespaces: ' + ', '.join( namespaces ) )
                    
                
            
            if service_key in self._service_keys_to_explicit_tags:
                
                explicit_tags = list( self._service_keys_to_explicit_tags[ service_key ] )
                
                if len( explicit_tags ) > 0:
                    
                    explicit_tags.sort()
                    
                    statements.append( 'explicit tags: ' + ', '.join( explicit_tags ) )
                    
                
            
            if len( statements ) > 0:
                
                name = HG.client_controller.services_manager.GetName( service_key )
                
                service_statement = name + ':' + os.linesep * 2 + os.linesep.join( statements )
                
                service_statements.append( service_statement )
                
            
        
        if len( service_statements ) > 0:
            
            separator = os.linesep * 2
            
            summary = separator.join( service_statements )
            
        else:
            
            summary = 'not adding any tags'
            
        
        return summary
        
    
    def InterestedInTags( self ):
        
        i_am_interested = len( self._service_keys_to_namespaces ) > 0
        
        return i_am_interested
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS ] = TagImportOptions

class ThreadWatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT
    SERIALISABLE_VERSION = 3
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = ClientDefaults.GetDefaultFileImportOptions()
        
        new_options = HG.client_controller.GetNewOptions()
        
        tag_import_options = new_options.GetDefaultTagImportOptions( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_THREAD_WATCHER ) )
        
        self._thread_url = ''
        self._urls_cache = SeedCache()
        self._urls_to_filenames = {}
        self._urls_to_md5_base64 = {}
        self._checker_options = new_options.GetDefaultThreadCheckerOptions()
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._last_check_time = 0
        self._thread_status = CHECKER_STATUS_OK
        self._thread_subject = 'unknown subject'
        
        self._next_check_time = None
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        self._download_control_thread_set = None
        self._download_control_thread_clear = None
        
        self._check_now = False
        self._files_paused = False
        self._thread_paused = False
        
        self._file_velocity_status = ''
        self._current_action = ''
        self._watcher_status = ''
        
        self._thread_key = HydrusData.GenerateKey()
        
        self._lock = threading.Lock()
        
        self._last_pubbed_page_name = ''
        
        self._new_files_event = threading.Event()
        self._new_thread_event = threading.Event()
        
    
    def _CheckThread( self, page_key ):
        
        error_occurred = False
        watcher_status_should_stick = True
        
        with self._lock:
            
            self._watcher_status = 'checking thread'
            
        
        try:
            
            json_url = ClientDownloading.GetImageboardThreadJSONURL( self._thread_url )
            
            network_job = ClientNetworking.NetworkJobThreadWatcher( self._thread_key, 'GET', json_url )
            
            network_job.OverrideBandwidth()
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            with self._lock:
                
                if self._download_control_thread_set is not None:
                    
                    wx.CallAfter( self._download_control_thread_set, network_job )
                    
                
            
            try:
                
                network_job.WaitUntilDone()
                
            finally:
                
                if self._download_control_thread_clear is not None:
                    
                    wx.CallAfter( self._download_control_thread_clear )
                    
                
            
            raw_json = network_job.GetContent()
            
            with self._lock:
                
                self._thread_subject = ClientDownloading.ParseImageboardThreadSubject( raw_json )
                
            
            file_infos = ClientDownloading.ParseImageboardFileURLsFromJSON( self._thread_url, raw_json )
            
            new_urls = []
            new_urls_set = set()
            
            file_urls_to_source_timestamps = {}
            
            for ( file_url, file_md5_base64, file_original_filename, source_timestamp ) in file_infos:
                
                if not self._urls_cache.HasSeed( file_url ) and not file_url in new_urls_set:
                    
                    new_urls.append( file_url )
                    new_urls_set.add( file_url )
                    
                    self._urls_to_filenames[ file_url ] = file_original_filename
                    
                    if file_md5_base64 is not None:
                        
                        self._urls_to_md5_base64[ file_url ] = file_md5_base64
                        
                    
                    file_urls_to_source_timestamps[ file_url ] = source_timestamp
                    
                
            
            self._urls_cache.AddSeeds( new_urls )
            
            for ( file_url, source_timestamp ) in file_urls_to_source_timestamps.items():
                
                self._urls_cache.UpdateSeedSourceTime( file_url, source_timestamp )
                
            
            num_new = len( new_urls )
            
            watcher_status = 'thread checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
            watcher_status_should_stick = False
            
            if num_new > 0:
                
                self._new_files_event.set()
                
            
        except HydrusExceptions.NotFoundException:
            
            error_occurred = True
            
            with self._lock:
                
                self._thread_status = CHECKER_STATUS_404
                
            
            watcher_status = ''
            
        except Exception as e:
            
            error_occurred = True
            
            watcher_status = HydrusData.ToUnicode( e )
            
            HydrusData.PrintException( e )
            
        
        with self._lock:
            
            if self._check_now:
                
                self._check_now = False
                
            
            self._watcher_status = watcher_status
            
            self._last_check_time = HydrusData.GetNow()
            
            self._UpdateFileVelocityStatus()
            
            self._UpdateNextCheckTime()
            
            if error_occurred:
                
                self._thread_paused = True
                
            
        
        if error_occurred:
            
            time.sleep( 5 )
            
        
        if not watcher_status_should_stick:
            
            time.sleep( 5 )
            
            with self._lock:
                
                self._watcher_status = ''
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, self._last_check_time, self._files_paused, self._thread_paused, self._thread_status, self._thread_subject )
        
    
    def _HasThread( self ):
        
        return self._thread_url != ''
        
    
    def _PublishPageName( self, page_key ):
        
        new_options = HG.client_controller.GetNewOptions()
        
        cannot_rename = not new_options.GetBoolean( 'permit_watchers_to_name_their_pages' )
        
        if cannot_rename:
            
            page_name = 'thread watcher'
            
        elif self._thread_subject in ( '', 'unknown subject' ):
            
            page_name = 'thread watcher'
            
        else:
            
            page_name = self._thread_subject
            
        
        if self._thread_status == CHECKER_STATUS_404:
            
            thread_watcher_not_found_page_string = new_options.GetNoneableString( 'thread_watcher_not_found_page_string' )
            
            if thread_watcher_not_found_page_string is not None:
                
                page_name = thread_watcher_not_found_page_string + ' ' + page_name
                
            
        elif self._thread_status == CHECKER_STATUS_DEAD:
            
            thread_watcher_dead_page_string = new_options.GetNoneableString( 'thread_watcher_dead_page_string' )
            
            if thread_watcher_dead_page_string is not None:
                
                page_name = thread_watcher_dead_page_string + ' ' + page_name
                
            
        
        if page_name != self._last_pubbed_page_name:
            
            HG.client_controller.pub( 'rename_page', page_key, page_name )
            
            self._last_pubbed_page_name = page_name
            
        
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, self._last_check_time, self._files_paused, self._thread_paused, self._thread_status, self._thread_subject ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _UpdateFileVelocityStatus( self ):
        
        self._file_velocity_status = self._checker_options.GetPrettyCurrentVelocity( self._urls_cache, self._last_check_time )
        
    
    def _UpdateNextCheckTime( self ):
        
        if self._check_now:
            
            self._next_check_time = self._last_check_time + self.MIN_CHECK_PERIOD
            
            self._thread_status = CHECKER_STATUS_OK
            
        else:
            
            if self._thread_status != CHECKER_STATUS_404:
                
                if self._checker_options.IsDead( self._urls_cache, self._last_check_time ):
                    
                    self._thread_status = CHECKER_STATUS_DEAD
                    
                    self._watcher_status = ''
                    
                    self._thread_paused = True
                    
                else:
                    
                    self._thread_status = CHECKER_STATUS_OK
                    
                
            
            self._next_check_time = self._checker_options.GetNextCheckTime( self._urls_cache, self._last_check_time )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_file_options, serialisable_tag_options, times_to_check, check_period, last_check_time, paused ) = old_serialisable_info
            
            checker_options = ClientData.CheckerOptions( intended_files_per_check = 8, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
            
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            files_paused = paused
            thread_paused = paused
            
            new_serialisable_info = ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, last_check_time, files_paused, thread_paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, last_check_time, files_paused, thread_paused ) = old_serialisable_info
            
            thread_status = CHECKER_STATUS_OK
            thread_subject = 'unknown subject'
            
            new_serialisable_info = ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, last_check_time, files_paused, thread_paused, thread_status, thread_subject )
            
            return ( 3, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return False
            
        
        try:
            
            with self._lock:
                
                self._current_action = 'reviewing file'
                
            
            file_original_filename = self._urls_to_filenames[ file_url ]
            
            downloaded_tags = [ 'filename:' + file_original_filename ]
            
            # we now do both url and md5 tests here because cloudflare was sometimes giving optimised versions of images, meaning the api's md5 was unreliable
            # if someone set up a thread watcher of a thread they had previously watched, any optimised images would be redownloaded
            
            ( status, hash, note ) = HG.client_controller.Read( 'url_status', file_url )
            
            url_not_known_beforehand = status == CC.STATUS_NEW
            
            if status == CC.STATUS_NEW:
                
                if file_url in self._urls_to_md5_base64:
                    
                    file_md5_base64 = self._urls_to_md5_base64[ file_url ]
                    
                    file_md5 = file_md5_base64.decode( 'base64' )
                    
                    ( status, hash, note ) = HG.client_controller.Read( 'md5_status', file_md5 )
                    
                
            
            if status == CC.STATUS_DELETED:
                
                if not self._file_import_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    note = ''
                    
                
            
            if status == CC.STATUS_NEW:
                
                with self._lock:
                    
                    self._current_action = 'downloading file'
                    
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    network_job = ClientNetworking.NetworkJobThreadWatcher( self._thread_key, 'GET', file_url, temp_path = temp_path )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    with self._lock:
                        
                        if self._download_control_file_set is not None:
                            
                            wx.CallAfter( self._download_control_file_set, network_job )
                            
                        
                    
                    try:
                        
                        network_job.WaitUntilDone()
                        
                    except HydrusExceptions.ShutdownException:
                        
                        return True
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = 'cancelled during download!' )
                        
                        return True
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return True
                        
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    with self._lock:
                        
                        self._current_action = 'importing file'
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    self._urls_cache.UpdateSeedStatus( file_url, status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
                
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                with self._lock:
                    
                    service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                    
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        return True
        
    
    def _THREADWorkOnFiles( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    if self._thread_url == '':
                        
                        self._new_files_event.wait( 5 )
                        
                    else:
                        
                        did_work = self._WorkOnFiles( page_key )
                        
                        if did_work:
                            
                            time.sleep( DID_FILE_WORK_MINIMUM_SLEEP_TIME )
                            
                        else:
                            
                            self._new_files_event.wait( 5 )
                            
                        
                        HG.client_controller.WaitUntilViewFree()
                        
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_files_event.clear()
            
        
    
    def _THREADWorkOnThread( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            with self._lock:
                
                able_to_check = self._HasThread() and not self._thread_paused
                check_due = HydrusData.TimeHasPassed( self._next_check_time )
                
                time_to_check = able_to_check and check_due
                
            
            if not time_to_check or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_thread_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._CheckThread( page_key )
                    
                    with self._lock:
                        
                        self._PublishPageName( page_key )
                        
                    
                    time.sleep( 5 )
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            with self._lock:
                
                self._PublishPageName( page_key )
                
            
            self._new_thread_event.clear()
            
        
    
    def CheckNow( self ):
        
        with self._lock:
            
            self._check_now = True
            
            self._thread_paused = False
            
            self._UpdateNextCheckTime()
            
            self._new_thread_event.set()
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._urls_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def GetSeedCache( self ):
        
        return self._urls_cache
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._thread_url, self._file_import_options, self._tag_import_options )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._thread_status == CHECKER_STATUS_404:
                
                watcher_status = 'Thread 404'
                
            elif self._thread_status == CHECKER_STATUS_DEAD:
                
                watcher_status = 'Thread dead'
                
            else:
                
                watcher_status = self._watcher_status
                
            
            return ( self._current_action, self._files_paused, self._file_velocity_status, self._next_check_time, watcher_status, self._thread_subject, self._thread_status, self._check_now, self._thread_paused )
            
        
    
    def GetCheckerOptions( self ):
        
        with self._lock:
            
            return self._checker_options
            
        
    
    def HasThread( self ):
        
        with self._lock:
            
            return self._HasThread()
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            self._new_files_event.set()
            
        
    
    def PausePlayThread( self ):
        
        with self._lock:
            
            if self._thread_paused and self._checker_options.IsDead( self._urls_cache, self._last_check_time ):
                
                return # thread is dead, so don't unpause until a checknow event
                
            else:
                
                self._thread_paused = not self._thread_paused
                
                self._new_thread_event.set()
                
            
        
    
    def SetDownloadControlFile( self, download_control ):
        
        with self._lock:
            
            self._download_control_file_set = download_control.SetNetworkJob
            self._download_control_file_clear = download_control.ClearNetworkJob
            
        
    
    def SetDownloadControlThread( self, download_control ):
        
        with self._lock:
            
            self._download_control_thread_set = download_control.SetNetworkJob
            self._download_control_thread_clear = download_control.ClearNetworkJob
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def SetThreadURL( self, thread_url ):
        
        with self._lock:
            
            self._thread_url = thread_url
            
            self._new_thread_event.set()
            
        
    
    def SetCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._checker_options = checker_options
            
            self._thread_paused = False
            
            self._UpdateNextCheckTime()
            
            self._UpdateFileVelocityStatus()
            
            self._new_thread_event.set()
            
        
    
    def Start( self, page_key ):
        
        self._UpdateNextCheckTime()
        
        self._PublishPageName( page_key )
        
        self._UpdateFileVelocityStatus()
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnThread, page_key )
        HG.client_controller.CallToThreadLongRunning( self._THREADWorkOnFiles, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT ] = ThreadWatcherImport

class URLsImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = ClientDefaults.GetDefaultFileImportOptions()
        
        self._urls_cache = SeedCache()
        self._file_import_options = file_import_options
        self._paused = False
        
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        self._download_control_file_set = None
        self._download_control_file_clear = None
        
        self._lock = threading.Lock()
        
        self._new_urls_event = threading.Event()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        
        return ( serialisable_url_cache, serialisable_file_options, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_file_options, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _RegenerateSeedCacheStatus( self ):
        
        new_seed_cache_status = self._urls_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return False
            
        
        try:
            
            with self._lock:
                
                self._RegenerateSeedCacheStatus()
                
            
            ( status, hash, note ) = HG.client_controller.Read( 'url_status', file_url )
            
            url_not_known_beforehand = status == CC.STATUS_NEW
            
            if status == CC.STATUS_DELETED:
                
                if not self._file_import_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    note = ''
                    
                
            
            if status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    network_job = ClientNetworking.NetworkJob( 'GET', file_url, temp_path = temp_path )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    with self._lock:
                        
                        if self._download_control_file_set is not None:
                            
                            wx.CallAfter( self._download_control_file_set, network_job )
                            
                        
                    
                    try:
                        
                        network_job.WaitUntilDone()
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = 'cancelled during download!' )
                        
                        return True
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        self._urls_cache.UpdateSeedStatus( file_url, status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return True
                        
                    
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    self._urls_cache.UpdateSeedStatus( file_url, status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
                
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            with self._lock:
                
                self._RegenerateSeedCacheStatus()
                
            
        
        return True
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            if self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_urls_event.wait( 5 )
                
            else:
                
                try:
                    
                    did_work = self._WorkOnFiles( page_key )
                    
                    if did_work:
                        
                        time.sleep( DID_FILE_WORK_MINIMUM_SLEEP_TIME )
                        
                    else:
                        
                        self._new_urls_event.wait( 5 )
                        
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except HydrusExceptions.ShutdownException:
                    
                    return
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_urls_event.clear()
            
        
    
    def GetSeedCache( self ):
        
        return self._urls_cache
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._seed_cache_status, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            self._new_urls_event.set()
            
        
    
    def PendURLs( self, urls ):
        
        with self._lock:
            
            urls = filter( lambda u: len( u ) > 1, urls ) # > _1_ to take out the occasional whitespace
            
            new_urls = [ url for url in urls if not self._urls_cache.HasSeed( url ) ]
            
            if len( new_urls ) > 0:
                
                self._urls_cache.AddSeeds( new_urls )
                
                self._new_urls_event.set()
                
            
        
    
    def SetDownloadControlFile( self, download_control ):
        
        with self._lock:
            
            self._download_control_file_set = download_control.SetNetworkJob
            self._download_control_file_clear = download_control.ClearNetworkJob
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWork, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLsImport
