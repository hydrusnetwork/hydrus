import bs4
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientFiles
import ClientImageHandling
import ClientNetworking
import ClientParsing
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
import HydrusText
import json
import os
import random
import re
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

DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME = 0.1

def GetInitialSeedStatus( seed ):
    
    ( status, hash, note ) = ( CC.STATUS_NEW, None, '' )
    
    url_not_known_beforehand = True
    
    if seed.seed_type == SEED_TYPE_URL:
        
        url = seed.seed_data
        
        ( status, hash, note ) = HG.client_controller.Read( 'url_status', url )
        
        url_not_known_beforehand = status == CC.STATUS_NEW
        
    
    if status == CC.STATUS_NEW:
        
        for ( hash_type, found_hash ) in seed.GetHashes().items():
            
            ( status, hash, note ) = HG.client_controller.Read( 'hash_status', hash_type, found_hash )
            
            if status != CC.STATUS_NEW:
                
                break
                
            
        
    
    return ( url_not_known_beforehand, ( status, hash, note ) )

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
            
        except HydrusExceptions.ShutdownException:
            
            job_key.Cancel()
            
            return
            
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
            
        
        job_key.SetVariable( 'popup_files', ( [ hash ], 'download' ) )
        
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
    
    presentation_hashes = []
    presentation_hashes_fast = set()
    
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
                
            except HydrusExceptions.ShutdownException:
                
                break
                
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
                
            
            if hash not in presentation_hashes_fast:
                
                presentation_hashes.append( hash )
                
            
            presentation_hashes_fast.add( hash )
            
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
    
    if len( presentation_hashes ) > 0:
        
        job_key.SetVariable( 'popup_files', ( presentation_hashes, 'downloads' ) )
        
    
    job_key.DeleteVariable( 'popup_gauge_1' )
    job_key.DeleteVariable( 'popup_text_2' )
    
    job_key.Finish()
    
def UpdateSeedCacheWithAllParseResults( seed_cache, all_parse_results ):
    
    # need a limit param here for 'stop at 40 total new because of file limit'
    
    new_seeds = []
    
    num_new = 0
    num_already_in = 0
    
    for parse_results in all_parse_results:
        
        parsed_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ) )
        
        urls_to_add = filter( lambda u: not seed_cache.HasURL( u ), parsed_urls )
        
        num_new += len( urls_to_add )
        num_already_in += len( parsed_urls ) - len( urls_to_add )
        
        if len( urls_to_add ) == 0:
            
            continue
            
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        hashes = ClientParsing.GetHashesFromParseResults( parse_results )
        source_timestamp = ClientParsing.GetTimestampFromParseResults( parse_results, HC.TIMESTAMP_TYPE_SOURCE )
        
        for url in urls_to_add:
            
            seed = Seed( SEED_TYPE_URL, url )
            
            seed.AddTags( tags )
            
            for ( hash_type, hash ) in hashes:
                
                seed.SetHash( hash_type, hash )
                
            
            if source_timestamp is not None:
                
                seed.source_time = source_timestamp
                
            
            new_seeds.append( seed )
            
        
    
    seed_cache.AddSeeds( new_seeds )
    
    return ( num_new, num_already_in )
    
class FileImportJob( object ):
    
    def __init__( self, temp_path, file_import_options = None ):
        
        if file_import_options is None:
            
            file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
            
        
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
            
            if self._file_import_options.GetAutomaticArchive():
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, set( ( self._hash, ) ) ) ] }
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
    def IsGoodToImport( self ):
        
        ( automatic_archive, exclude_deleted, present_new_files, present_already_in_inbox_files, present_archived_files, min_size, min_resolution ) = self._file_import_options.ToTuple()
        
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
            
            if not self._file_import_options.GetExcludeDeleted():
                
                return True
                
            
        
        return False
        
    
    def GenerateHashAndStatus( self ):
        
        HydrusImageHandling.ConvertToPngIfBmp( self._temp_path )
        
        self._hash = HydrusFileHandling.GetHashFromPath( self._temp_path )
        
        ( self._pre_import_status, hash, note ) = HG.client_controller.Read( 'hash_status', 'sha256', self._hash )
        
    
    def GenerateInfo( self ):
        
        mime = HydrusFileHandling.GetMime( self._temp_path )
        
        new_options = HG.client_controller.new_options
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and new_options.GetBoolean( 'do_not_import_decompression_bombs' ):
            
            if HydrusImageHandling.IsDecompressionBomb( self._temp_path ):
                
                raise HydrusExceptions.SizeException( 'Image seems to be a Decompression Bomb!' )
                
            
        
        self._file_info = HydrusFileHandling.GetFileInfo( self._temp_path, mime )
        
        ( size, mime, width, height, duration, num_frames, num_words ) = self._file_info
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            self._thumbnail = HydrusFileHandling.GenerateThumbnail( self._temp_path, mime )
            
        
        if mime in HC.MIMES_WE_CAN_PHASH:
            
            self._phashes = ClientImageHandling.GenerateShapePerceptualHashes( self._temp_path, mime )
            
        
        self._extra_hashes = HydrusFileHandling.GetExtraHashesFromPath( self._temp_path )
        
    
class GalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT
    SERIALISABLE_NAME = 'Gallery Import'
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
        
        new_options = HG.client_controller.new_options
        
        self._get_tags_if_url_known_and_file_redundant = new_options.GetBoolean( 'get_tags_if_url_known_and_file_redundant' )
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        self._gallery_paused = False
        self._files_paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
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
        
        seed = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if seed is None:
            
            return
            
        
        did_substantial_work = False
        
        url = seed.seed_data
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworking.NetworkJobDownloaderQueryTemporary( page_key, method, url, **kwargs )
            
            wx.CallAfter( self._download_control_file_set, network_job )
            
            return network_job
            
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            with self._lock:
                
                self._files_paused = True
                self._gallery_paused = True
                
                HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                
                return
                
            
        
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
                    
                    did_substantial_work = True
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( url, ) ) ) ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            seed.SetStatus( status, note = note )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                    did_substantial_work = True
                    
                
                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                
                if self._file_import_options.ShouldPresent( status, in_inbox ):
                    
                    ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                    
                    HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                    did_substantial_work = True
                    
                
            
        except HydrusExceptions.CancelledException:
            
            status = CC.STATUS_SKIPPED
            
            seed.SetStatus( status )
            
            time.sleep( 2 )
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            seed.SetStatus( status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._seed_cache.NotifySeedsUpdated( ( seed, ) )
            
            wx.CallAfter( self._download_control_file_clear )
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
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
                
            
            try:
                
                gallery = ClientDownloading.GetGallery( self._current_gallery_stream_identifier )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                with self._lock:
                    
                    self._files_paused = True
                    self._gallery_paused = True
                    
                    HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                    
                    return
                    
                
            
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
                
                if self._seed_cache.HasURL( url ):
                    
                    num_already_in_seed_cache += 1
                    
                else:
                    
                    with self._lock:
                        
                        if self._file_limit is not None and self._current_query_num_urls + 1 > self._file_limit:
                            
                            self._current_gallery_stream_identifier = None
                            
                            self._pending_gallery_stream_identifiers = []
                            
                            break
                            
                        
                        self._current_query_num_urls += 1
                        
                    
                    new_urls.append( url )
                    
                
            
            self._seed_cache.AddURLs( new_urls )
            
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
            
            no_work_to_do = self._files_paused or not self._seed_cache.WorkToDo()
            
            if no_work_to_do or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
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
            
        
    
    def AdvanceQueries( self, queries ):
        
        with self._lock:
            
            queries_lookup = set( queries )
            
            for query in queries:
                
                if query in self._pending_queries:
                    
                    index = self._pending_queries.index( query )
                    
                    if index > 0 and self._pending_queries[ index - 1 ] not in queries_lookup:
                        
                        self._pending_queries.remove( query )
                        
                        self._pending_queries.insert( index - 1, query )
                        
                    
                
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._seed_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def DelayQueries( self, queries ):
        
        with self._lock:
            
            queries = list( queries )
            
            queries.reverse()
            
            queries_lookup = set( queries )
            
            for query in queries:
                
                if query in self._pending_queries:
                    
                    index = self._pending_queries.index( query )
                    
                    if index + 1 < len( self._pending_queries ) and self._pending_queries[ index + 1] not in queries_lookup:
                        
                        self._pending_queries.remove( query )
                        
                        self._pending_queries.insert( index + 1, query )
                        
                    
                
            
        
    
    def DeleteQueries( self, queries ):
        
        with self._lock:
            
            for query in queries:
                
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

class FilenameTaggingOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS
    SERIALISABLE_NAME = 'Filename Tagging Options'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tags_for_all = set()
        
        self._load_from_neighbouring_txt_files = False
        
        self._add_filename = ( False, '' )
        self._add_first_directory = ( False, '' )
        self._add_second_directory = ( False, '' )
        self._add_third_directory = ( False, '' )
        
        self._quick_namespaces = []
        self._regexes = []
        
    
    def _GetSerialisableInfo( self ):
        
        return ( list( self._tags_for_all ), self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory, self._quick_namespaces, self._regexes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( tags_for_all_list, self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory, self._quick_namespaces, self._regexes ) = serialisable_info
        
        # converting [ namespace, regex ] to ( namespace, regex ) for listctrl et al to handle better
        self._quick_namespaces = [ tuple( item ) for item in self._quick_namespaces ]
        self._tags_for_all = set( tags_for_all_list )
        
    
    def AdvancedSetTuple( self, quick_namespaces, regexes ):
        
        self._quick_namespaces = quick_namespaces
        self._regexes = regexes
        
    
    def AdvancedToTuple( self ):
        
        return ( self._quick_namespaces, self._regexes )
        
    
    def GetTags( self, service_key, path ):
        
        tags = set()
        
        tags.update( self._tags_for_all )
        
        if self._load_from_neighbouring_txt_files:
            
            txt_path = path + '.txt'
            
            if os.path.exists( txt_path ):
                
                with open( txt_path, 'rb' ) as f:
                    
                    txt_tags_string = f.read()
                    
                
                try:
                    
                    txt_tags_string = HydrusData.ToUnicode( txt_tags_string )
                    
                    txt_tags = [ tag for tag in HydrusText.DeserialiseNewlinedTexts( txt_tags_string ) ]
                    
                    if True in ( len( txt_tag ) > 1024 for txt_tag in txt_tags ):
                        
                        HydrusData.ShowText( 'Tags were too long--I think this was not a regular text file!' )
                        
                        raise Exception()
                        
                    
                    tags.update( txt_tags )
                    
                except:
                    
                    HydrusData.ShowText( 'Could not parse the tags from ' + txt_path + '!' )
                    
                    tags.add( '___had problem parsing .txt file' )
                    
                
            
        
        ( base, filename ) = os.path.split( path )
        
        ( filename, any_ext_gumpf ) = os.path.splitext( filename )
        
        ( filename_boolean, filename_namespace ) = self._add_filename
        
        if filename_boolean:
            
            if filename_namespace != '':
                
                tag = filename_namespace + ':' + filename
                
            else:
                
                tag = filename
                
            
            tags.add( tag )
            
        
        ( drive, dirs ) = os.path.splitdrive( base )
        
        while dirs.startswith( os.path.sep ):
            
            dirs = dirs[1:]
            
        
        dirs = dirs.split( os.path.sep )
        
        ( dir_1_boolean, dir_1_namespace ) = self._add_first_directory
        
        if len( dirs ) > 0 and dir_1_boolean:
            
            if dir_1_namespace != '':
                
                tag = dir_1_namespace + ':' + dirs[0]
                
            else:
                
                tag = dirs[0]
                
            
            tags.add( tag )
            
        
        ( dir_2_boolean, dir_2_namespace ) = self._add_second_directory
        
        if len( dirs ) > 1 and dir_2_boolean:
            
            if dir_2_namespace != '':
                
                tag = dir_2_namespace + ':' + dirs[1]
                
            else:
                
                tag = dirs[1]
                
            
            tags.add( tag )
            
        
        ( dir_3_boolean, dir_3_namespace ) = self._add_third_directory
        
        if len( dirs ) > 2 and dir_3_boolean:
            
            if dir_3_namespace != '':
                
                tag = dir_3_namespace + ':' + dirs[2]
                
            else:
                
                tag = dirs[2]
                
            
            tags.add( tag )
            
        
        #
        
        for regex in self._regexes:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( submatch )
                            
                        
                    else:
                        
                        tags.add( match )
                        
                    
                
            except:
                
                pass
                
            
        
        for ( namespace, regex ) in self._quick_namespaces:
            
            try:
                
                result = re.findall( regex, path )
                
                for match in result:
                    
                    if isinstance( match, tuple ):
                        
                        for submatch in match:
                            
                            tags.add( namespace + ':' + submatch )
                            
                        
                    else:
                        
                        tags.add( namespace + ':' + match )
                        
                    
                
            except:
                
                pass
                
            
        
        #
        
        tags = HydrusTags.CleanTags( tags )
        
        siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
        parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        tag_censorship_manager = HG.client_controller.GetManager( 'tag_censorship' )
        
        tags = siblings_manager.CollapseTags( service_key, tags )
        tags = parents_manager.ExpandTags( service_key, tags )
        tags = tag_censorship_manager.FilterTags( service_key, tags )
        
        return tags
        
    
    def SimpleSetTuple( self, tags_for_all, load_from_neighbouring_txt_files, add_filename, add_first_directory, add_second_directory, add_third_directory ):
        
        self._tags_for_all = tags_for_all
        self._load_from_neighbouring_txt_files = load_from_neighbouring_txt_files
        self._add_filename = add_filename
        self._add_first_directory = add_first_directory
        self._add_second_directory = add_second_directory
        self._add_third_directory = add_third_directory
        
    
    def SimpleToTuple( self ):
        
        return ( self._tags_for_all, self._load_from_neighbouring_txt_files, self._add_filename, self._add_first_directory, self._add_second_directory, self._add_third_directory )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILENAME_TAGGING_OPTIONS ] = FilenameTaggingOptions    

class FileImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'File Import Options'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, automatic_archive = None, exclude_deleted = None, present_new_files = None, present_already_in_inbox_files = None, present_archived_files = None, min_size = None, min_resolution = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if automatic_archive is None:
            
            automatic_archive = False
            
        
        if exclude_deleted is None:
            
            exclude_deleted = True
            
        
        if present_new_files is None:
            
            present_new_files = True
            
        
        if present_already_in_inbox_files is None:
            
            present_already_in_inbox_files = True
            
        
        if present_archived_files is None:
            
            present_archived_files = True
            
        
        self._automatic_archive = automatic_archive
        self._exclude_deleted = exclude_deleted
        self._present_new_files = present_new_files
        self._present_already_in_inbox_files = present_already_in_inbox_files
        self._present_archived_files = present_archived_files
        self._min_size = min_size
        self._min_resolution = min_resolution
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._present_new_files, self._present_already_in_inbox_files, self._present_archived_files, self._min_size, self._min_resolution )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._automatic_archive, self._exclude_deleted, self._present_new_files, self._present_already_in_inbox_files, self._present_archived_files, self._min_size, self._min_resolution ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( automatic_archive, exclude_deleted, min_size, min_resolution ) = old_serialisable_info
            
            present_new_files = True
            present_already_in_inbox_files = False
            present_archived_files = False
            
            new_serialisable_info = ( automatic_archive, exclude_deleted, present_new_files, present_already_in_inbox_files, present_archived_files, min_size, min_resolution )
            
            return ( 2, new_serialisable_info )
            
        
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
            
        
        presentation_statements = []
        
        if self._present_new_files:
            
            presentation_statements.append( 'new' )
            
        
        if self._present_already_in_inbox_files:
            
            presentation_statements.append( 'already in inbox' )
            
        
        if self._present_archived_files:
            
            presentation_statements.append( 'already in archive' )
            
        
        if len( presentation_statements ) == 0:
            
            statements.append( 'not presenting any files' )
            
        elif len( presentation_statements ) == 3:
            
            statements.append( 'presenting all files' )
            
        else:
            
            statements.append( 'presenting ' + ', '.join( presentation_statements ) + ' files' )
            
        
        if self._min_size is not None:
            
            statements.append( 'excluding < ' + HydrusData.ConvertIntToBytes( self._min_size ) )
            
        
        if self._min_resolution is not None:
            
            ( width, height ) = self._min_resolution
            
            statements.append( 'excluding < ( ' + HydrusData.ConvertIntToPrettyString( width ) + ' x ' + HydrusData.ConvertIntToPrettyString( height ) + ' )' )
            
        
        summary = os.linesep.join( statements )
        
        return summary
        
    
    def ShouldPresent( self, status, inbox ):
        
        if status == CC.STATUS_SUCCESSFUL and self._present_new_files:
            
            return True
            
        elif status == CC.STATUS_REDUNDANT:
            
            if inbox and self._present_already_in_inbox_files:
                
                return True
                
            elif not inbox and self._present_archived_files:
                
                return True
                
            
        
        return False
        
    
    def ToTuple( self ):
        
        return ( self._automatic_archive, self._exclude_deleted, self._present_new_files, self._present_already_in_inbox_files, self._present_archived_files, self._min_size, self._min_resolution )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_IMPORT_OPTIONS ] = FileImportOptions

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_NAME = 'Local File Import'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, paths = None, file_import_options = None, paths_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if paths is None:
            
            self._paths_cache = None
            
        else:
            
            self._paths_cache = SeedCache()
            
            seeds = []
            
            for path in paths:
                
                seed = Seed( SEED_TYPE_HDD, path )
                
                try:
                    
                    s = os.stat( path )
                    
                    seed.source_time = int( min( s.st_mtime, s.st_ctime ) )
                    
                except:
                    
                    pass
                    
                
                seeds.append( seed )
                
            
            self._paths_cache.AddSeeds( seeds )
            
        
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
        
        seed = self._paths_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if seed is None:
            
            return
            
        
        did_substantial_work = False
        
        path = seed.seed_data
        
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
                
                did_substantial_work = True
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
            seed.SetStatus( status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                    did_substantial_work = True
                    
                
                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                
                if self._file_import_options.ShouldPresent( status, in_inbox ):
                    
                    ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                    
                    HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                    did_substantial_work = True
                    
                
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
            
            seed.SetStatus( status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            seed.SetStatus( status, exception = e )
            
        finally:
            
            self._paths_cache.NotifySeedsUpdated( ( seed, ) )
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _THREADWork( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            no_work_to_do = self._paused or not self._paths_cache.WorkToDo()
            
            if no_work_to_do or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
            self._new_files_event.clear()
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            work_to_do = self._paths_cache.WorkToDo()
            
            return work_to_do and not self._paused
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetSeedCache( self ):
        
        return self._paths_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._current_action, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            self._new_files_event.set()
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        HG.client_controller.CallToThreadLongRunning( self._THREADWork, page_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_NAME = 'Import Folder'
    SERIALISABLE_VERSION = 6
    
    def __init__( self, name, path = '', file_import_options = None, tag_import_options = None, tag_service_keys_to_filename_tagging_options = None, mimes = None, actions = None, action_locations = None, period = 3600, check_regularly = True, show_working_popup = True, publish_files_to_popup_button = True, publish_files_to_page = False ):
        
        if mimes is None:
            
            mimes = HC.ALLOWED_MIMES
            
        
        if file_import_options is None:
            
            file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
            
        
        if tag_import_options is None:
            
            tag_import_options = HG.client_controller.new_options.GetDefaultTagImportOptions( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEFAULT ) )
            
        
        if tag_service_keys_to_filename_tagging_options is None:
            
            tag_service_keys_to_filename_tagging_options = {}
            
        
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
        self._tag_service_keys_to_filename_tagging_options = tag_service_keys_to_filename_tagging_options
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._check_regularly = check_regularly
        
        self._path_cache = SeedCache()
        self._last_checked = 0
        self._paused = False
        self._check_now = False
        
        self._show_working_popup = show_working_popup
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        
    
    def _ActionPaths( self ):
        
        for status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_FAILED ):
            
            action = self._actions[ status ]
            
            if action == CC.IMPORT_FOLDER_DELETE:
                
                while True:
                    
                    seed = self._path_cache.GetNextSeed( status )
                    
                    if seed is None or HG.view_shutdown:
                        
                        break
                        
                    
                    path = seed.seed_data
                    
                    try:
                        
                        if os.path.exists( path ):
                            
                            ClientData.DeletePath( path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            ClientData.DeletePath( txt_path )
                            
                        
                        self._path_cache.RemoveSeeds( ( seed, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to delete ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif action == CC.IMPORT_FOLDER_MOVE:
                
                while True:
                    
                    seed = self._path_cache.GetNextSeed( status )
                    
                    if seed is None or HG.view_shutdown:
                        
                        break
                        
                    
                    path = seed.seed_data
                    
                    try:
                        
                        dest_dir = self._action_locations[ status ]
                        
                        if not os.path.exists( dest_dir ):
                            
                            raise HydrusExceptions.DataMissing( 'The move location "' + dest_dir + '" does not exist!' )
                            
                        
                        if os.path.exists( path ):
                            
                            filename = os.path.basename( path )
                            
                            dest_path = os.path.join( dest_dir, filename )
                            
                            dest_path = HydrusPaths.AppendPathUntilNoConflicts( dest_path )
                            
                            HydrusPaths.MergeFile( path, dest_path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            txt_filename = os.path.basename( txt_path )
                            
                            txt_dest_path = os.path.join( dest_dir, txt_filename )
                            
                            txt_dest_path = HydrusPaths.AppendPathUntilNoConflicts( txt_dest_path )
                            
                            HydrusPaths.MergeFile( txt_path, txt_dest_path )
                            
                        
                        self._path_cache.RemoveSeeds( ( seed, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to move ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif status == CC.IMPORT_FOLDER_IGNORE:
                
                pass
                
            
        
    
    def _CheckFolder( self, job_key ):
        
        filenames = os.listdir( HydrusData.ToUnicode( self._path ) )
        
        raw_paths = [ os.path.join( self._path, filename ) for filename in filenames ]
        
        all_paths = ClientFiles.GetAllPaths( raw_paths )
        
        all_paths = HydrusPaths.FilterFreePaths( all_paths )
        
        new_paths = []
        
        for path in all_paths:
            
            if job_key.IsCancelled():
                
                break
                
            
            if path.endswith( '.txt' ):
                
                continue
                
            
            if not self._path_cache.HasPath( path ):
                
                new_paths.append( path )
                
            
            job_key.SetVariable( 'popup_text_1', 'checking: found ' + HydrusData.ConvertIntToPrettyString( len( new_paths ) ) + ' new files' )
            
        
        self._path_cache.AddPaths( new_paths )
        
        self._last_checked = HydrusData.GetNow()
        self._check_now = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.encode( 'hex' ), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in self._tag_service_keys_to_filename_tagging_options.items() ]
        serialisable_path_cache = self._path_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = self._actions.items()
        action_location_pairs = self._action_locations.items()
        
        return ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, self._period, self._check_regularly, serialisable_path_cache, self._last_checked, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page )
        
    
    def _ImportFiles( self, job_key ):
        
        did_work = False
        
        time_to_save = HydrusData.GetNow() + 600
        
        num_files_imported = 0
        presentation_hashes = []
        presentation_hashes_fast = set()
        
        i = 0
        
        num_total = len( self._path_cache )
        num_total_unknown = self._path_cache.GetSeedCount( CC.STATUS_UNKNOWN )
        num_total_done = num_total - num_total_unknown
        
        while True:
            
            seed = self._path_cache.GetNextSeed( CC.STATUS_UNKNOWN )
            
            p1 = HC.options[ 'pause_import_folders_sync' ] or self._paused
            p2 = HydrusThreading.IsThreadShuttingDown()
            p3 = job_key.IsCancelled()
            
            if seed is None or p1 or p2 or p3:
                
                break
                
            
            if HydrusData.TimeHasPassed( time_to_save ):
                
                HG.client_controller.WriteSynchronous( 'serialisable', self )
                
                time_to_save = HydrusData.GetNow() + 600
                
            
            gauge_num_done = num_total_done + num_files_imported + 1
            
            job_key.SetVariable( 'popup_text_1', 'importing file ' + HydrusData.ConvertValueRangeToPrettyString( gauge_num_done, num_total ) )
            job_key.SetVariable( 'popup_gauge_1', ( gauge_num_done, num_total ) )
            
            path = seed.seed_data
            
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
                        
                    
                    seed.SetStatus( status )
                    
                    if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                        
                        downloaded_tags = []
                        
                        service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags ) # explicit tags
                        
                        if len( service_keys_to_content_updates ) > 0:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                        service_keys_to_tags = {}
                        
                        for ( tag_service_key, filename_tagging_options ) in self._tag_service_keys_to_filename_tagging_options.items():
                            
                            if not HG.client_controller.services_manager.ServiceExists( tag_service_key ):
                                
                                continue
                                
                            
                            try:
                                
                                tags = filename_tagging_options.GetTags( tag_service_key, path )
                                
                                if len( tags ) > 0:
                                    
                                    service_keys_to_tags[ tag_service_key ] = tags
                                    
                                
                            except Exception as e:
                                
                                HydrusData.ShowText( 'Trying to parse filename tags in the import folder "' + self._name + '" threw an error!' )
                                
                                HydrusData.ShowException( e )
                                
                            
                        
                        if len( service_keys_to_tags ) > 0:
                            
                            service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                        num_files_imported += 1
                        
                        if hash not in presentation_hashes_fast:
                            
                            in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                            
                            if self._file_import_options.ShouldPresent( status, in_inbox ):
                                
                                presentation_hashes.append( hash )
                                
                                presentation_hashes_fast.add( hash )
                                
                            
                        
                    
                else:
                    
                    seed.SetStatus( CC.STATUS_UNINTERESTING_MIME )
                    
                
            except Exception as e:
                
                error_text = traceback.format_exc()
                
                HydrusData.Print( 'A file failed to import from import folder ' + self._name + ':' + path )
                
                seed.SetStatus( CC.STATUS_FAILED, exception = e )
                
            finally:
                
                did_work = True
                
            
            i += 1
            
            if i % 10 == 0:
                
                self._ActionPaths()
                
            
        
        if num_files_imported > 0:
            
            HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusData.ConvertIntToPrettyString( num_files_imported ) + ' files.' )
            
            if len( presentation_hashes ) > 0:
                
                if self._publish_files_to_popup_button:
                    
                    job_key = ClientThreading.JobKey()
                    
                    job_key.SetVariable( 'popup_files_mergable', True )
                    job_key.SetVariable( 'popup_files', ( list( presentation_hashes ), self._name ) )
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                
                if self._publish_files_to_page:
                    
                    HG.client_controller.pub( 'imported_files_to_page', list( presentation_hashes ), self._name )
                    
                
            
        
        self._ActionPaths()
        
        return did_work
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, self._period, self._check_regularly, serialisable_path_cache, self._last_checked, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._tag_service_keys_to_filename_tagging_options = dict( [ ( encoded_service_key.decode( 'hex' ), HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_tagging_options ) ) for ( encoded_service_key, serialisable_filename_tagging_options ) in serialisable_tag_service_keys_to_filename_tagging_options ] )
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
            
        
        if version == 4:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused, check_now ) = old_serialisable_info
            
            txt_parse_tag_service_keys = [ service_key.decode( 'hex' ) for service_key in serialisable_txt_parse_tag_service_keys ]
            
            tag_service_keys_to_filename_tagging_options = {}
            
            for service_key in txt_parse_tag_service_keys:
                
                filename_tagging_options = FilenameTaggingOptions()
                
                filename_tagging_options._load_from_neighbouring_txt_files = True
                
                tag_service_keys_to_filename_tagging_options[ service_key ] = filename_tagging_options
                
            
            serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.encode( 'hex' ), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in tag_service_keys_to_filename_tagging_options.items() ]
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused, check_now )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused, check_now ) = old_serialisable_info
            
            check_regularly = not paused
            show_working_popup = True
            publish_files_to_page = False
            publish_files_to_popup_button = open_popup
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_path_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
            
            return ( 6, new_serialisable_info )
            
        
    
    def CheckNow( self ):
        
        self._check_now = True
        
    
    def DoWork( self ):
        
        if HG.view_shutdown:
            
            return
            
        
        if HC.options[ 'pause_import_folders_sync' ] or self._paused:
            
            return
            
        
        if not os.path.exists( self._path ) or not os.path.isdir( self._path ):
            
            return
            
        
        pubbed_job_key = False
        
        job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'import folder - ' + self._name )
        
        due_by_check_now = self._check_now
        due_by_period = self._check_regularly and HydrusData.TimeHasPassed( self._last_checked + self._period )
        
        checked_folder = False
        
        if due_by_check_now or due_by_period:
            
            if not pubbed_job_key and self._show_working_popup:
                
                HG.client_controller.pub( 'message', job_key )
                
                pubbed_job_key = True
                
            
            self._CheckFolder( job_key )
            
            checked_folder = True
            
        
        seed = self._path_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        did_import_file_work = False
        
        if seed is not None:
            
            if not pubbed_job_key and self._show_working_popup:
                
                HG.client_controller.pub( 'message', job_key )
                
                pubbed_job_key = True
                
            
            did_import_file_work = self._ImportFiles( job_key )
            
        
        if checked_folder or did_import_file_work:
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
        job_key.Delete()
        
    
    def GetSeedCache( self ):
        
        return self._path_cache
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._period )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._mimes, self._file_import_options, self._tag_import_options, self._tag_service_keys_to_filename_tagging_options, self._actions, self._action_locations, self._period, self._check_regularly, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page )
        
    
    def SetSeedCache( self, seed_cache ):
        
        self._path_cache = seed_cache
        
    
    def SetTuple( self, name, path, mimes, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ):
        
        if path != self._path:
            
            self._path_cache = SeedCache()
            
        
        if set( mimes ) != set( self._mimes ):
            
            self._path_cache.RemoveSeedsByStatus( CC.STATUS_UNINTERESTING_MIME )
            
        
        self._name = name
        self._path = path
        self._mimes = mimes
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._tag_service_keys_to_filename_tagging_options = tag_service_keys_to_filename_tagging_options
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._check_regularly = check_regularly
        self._paused = paused
        self._check_now = check_now
        self._show_working_popup = show_working_popup
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER ] = ImportFolder

class PageOfImagesImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT
    SERIALISABLE_NAME = 'Page Of Images Import'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
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
        
        seed = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if seed is None:
            
            return
            
        
        did_substantial_work = False
        
        file_url = seed.seed_data
        
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
                        
                        return
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        seed.SetStatus( status, note = 'cancelled during download!' )
                        
                        return
                        
                    except HydrusExceptions.NotFoundException:
                        
                        status = CC.STATUS_FAILED
                        note = '404'
                        
                        seed.SetStatus( status, note = note )
                        
                        time.sleep( 2 )
                        
                        return
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        seed.SetStatus( status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return
                        
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    with self._lock:
                        
                        self._current_action = 'importing file'
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    did_substantial_work = True
                    
                    seed.SetStatus( status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                        did_substantial_work = True
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                seed.SetStatus( status, note = note )
                
            
            in_inbox = HG.client_controller.Read( 'in_inbox', hash )
            
            if self._file_import_options.ShouldPresent( status, in_inbox ):
                
                ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                
                HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
                did_substantial_work = True
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            seed.SetStatus( status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._urls_cache.NotifySeedsUpdated( ( seed, ) )
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
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
                    
                
                new_urls = [ file_url for file_url in file_urls if not self._urls_cache.HasURL( file_url ) ]
                
                self._urls_cache.AddURLs( new_urls )
                
                num_new = len( new_urls )
                
                if num_new > 0:
                    
                    self._new_files_event.set()
                    
                
                parser_status = 'page checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
                
                num_already_in_seed_cache = len( file_urls ) - num_new
                
                if num_already_in_seed_cache > 0:
                    
                    parser_status += ' (' + HydrusData.ConvertIntToPrettyString( num_already_in_seed_cache ) + ' already in queue)'
                    
                
            except HydrusExceptions.ShutdownException:
                
                return
                
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
            
            no_work_to_do = self._files_paused or not self._urls_cache.WorkToDo()
            
            if no_work_to_do or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
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

SEED_TYPE_HDD = 0
SEED_TYPE_URL = 1

class Seed( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED
    SERIALISABLE_NAME = 'File Import'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, seed_type = None, seed_data = None ):
        
        if seed_type is None:
            
            seed_type = SEED_TYPE_URL
            
        
        if seed_data is None:
            
            seed_data = 'https://big-guys.4u/monica_lewinsky_hott.tiff.exe.vbs'
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.seed_type = seed_type
        self.seed_data = seed_data
        
        self.created = HydrusData.GetNow()
        self.modified = self.created
        self.source_time = None
        self.status = CC.STATUS_UNKNOWN
        self.note = ''
        
        self._urls = set()
        self._tags = set()
        self._hashes = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_urls = list( self._urls )
        serialisable_tags = list( self._tags )
        serialisable_hashes = [ ( hash_type, hash.encode( 'hex' ) ) for ( hash_type, hash ) in self._hashes.items() ]
        
        return ( self.seed_type, self.seed_data, self.created, self.modified, self.source_time, self.status, self.note, serialisable_urls, serialisable_tags, serialisable_hashes )
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.seed_type, self.seed_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.seed_type, self.seed_data, self.created, self.modified, self.source_time, self.status, self.note, serialisable_urls, serialisable_tags, serialisable_hashes ) = serialisable_info
        
        self._urls = set( serialisable_urls )
        self._service_keys_to_tags = set( serialisable_tags )
        self._hashes = { hash_type : encoded_hash.decode( 'hex' ) for ( hash_type, encoded_hash ) in serialisable_hashes }
        
    
    def _UpdateModified( self ):
        
        self.modified = HydrusData.GetNow()
        
    
    def AddTags( self, tags ):
        
        self._tags.update( tags )
        
        self._UpdateModified()
        
    
    def AddURL( self, url ):
        
        self._urls.add( url )
        
        self._UpdateModified()
        
    
    def GetContentUpdates( self, hash ):
        
        # apply urls and tags appropriately, return the sk_to_cu dict
        
        pass
        
    
    def GetHashes( self ):
        
        return dict( self._hashes )
        
    
    def GetSearchSeeds( self ):
        
        if self.seed_type == SEED_TYPE_URL:
            
            search_urls = ClientData.GetSearchURLs( self.seed_data )
            
            search_seeds = [ Seed( SEED_TYPE_URL, search_url ) for search_url in search_urls ]
            
        else:
            
            search_seeds = [ self ]
            
        
        return search_seeds
        
    
    def GetTags( self ):
        
        return set( self._tags )
        
    
    def SetHash( self, hash_type, hash ):
        
        self._hashes[ hash_type ] = hash
        
    
    def SetSourceTime( self, source_time ):
        
        self.source_time = source_time
        
        self._UpdateModified()
        
    
    def SetStatus( self, status, note = '', exception = None ):
        
        if exception is not None:
            
            first_line = HydrusData.ToUnicode( exception ).split( os.linesep )[0]
            
            note = first_line + u'\u2026 (Copy note to see full error)'
            note += os.linesep
            note += HydrusData.ToUnicode( traceback.format_exc() )
            
            HydrusData.Print( 'Error when processing ' + self.seed_data + ' !' )
            HydrusData.Print( traceback.format_exc() )
            
        
        self.status = status
        self.note = note
        
        self._UpdateModified()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED ] = Seed

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_NAME = 'Import File Status Cache'
    SERIALISABLE_VERSION = 8
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds = HydrusSerialisable.SerialisableList()
        
        self._seeds_to_indices = {}
        
        self._seed_cache_key = HydrusData.GenerateKey()
        
        self._status_cache = None
        
        self._dirty = True
        
        self._lock = threading.Lock()
        
    
    def __len__( self ):
        
        return len( self._seeds )
        
    
    def _GenerateStatus( self ):
        
        statuses_to_counts = collections.Counter()
        
        for seed in self._seeds:
            
            statuses_to_counts[ seed.status ] += 1
            
        
        num_successful = statuses_to_counts[ CC.STATUS_SUCCESSFUL ]
        num_failed = statuses_to_counts[ CC.STATUS_FAILED ]
        num_deleted = statuses_to_counts[ CC.STATUS_DELETED ]
        num_redundant = statuses_to_counts[ CC.STATUS_REDUNDANT ]
        num_unknown = statuses_to_counts[ CC.STATUS_UNKNOWN ]
        
        status_strings = []
        
        if num_successful > 0:
            
            status_strings.append( str( num_successful ) + ' successful' )
            
        
        if num_failed > 0:
            
            status_strings.append( str( num_failed ) + ' failed' )
            
        
        if num_deleted > 0:
            
            status_strings.append( str( num_deleted ) + ' previously deleted' )
            
        
        if num_redundant > 0:
            
            status_strings.append( str( num_redundant ) + ' already in db' )
            
        
        status = ', '.join( status_strings )
        
        total = len( self._seeds )
        
        total_processed = total - num_unknown
        
        self._status_cache = ( status, ( total_processed, total ) )
        
        self._dirty = False
        
    
    def _GetSeeds( self, status = None ):
        
        if status is None:
            
            return list( self._seeds )
            
        else:
            
            return [ seed for seed in self._seeds if seed.status == status ]
            
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            return self._seeds.GetSerialisableTuple()
            
        
    
    def _GetSourceTimestamp( self, seed ):
        
        source_timestamp = seed.source_time
        
        if source_timestamp is None:
            
            # decent fallback compromise
            # -30 since added and 'last check' timestamps are often the same, and this messes up calculations
            
            source_timestamp = seed.created - 30
            
        
        return source_timestamp
        
    
    def _HasSeed( self, seed ):
        
        search_seeds = seed.GetSearchSeeds()
        
        has_seed = True in ( search_seed in self._seeds_to_indices for search_seed in search_seeds )
        
        return has_seed
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            self._seeds = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
        
    
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
            
        
        if version == 7:
            
            seeds = HydrusSerialisable.SerialisableList()
            
            for ( seed_text, seed_info ) in old_serialisable_info:
                
                if seed_text.startswith( 'http' ):
                    
                    seed_type = SEED_TYPE_URL
                    
                else:
                    
                    seed_type = SEED_TYPE_HDD
                    
                
                seed = Seed( seed_type, seed_text )
                
                seed.status = seed_info[ 'status' ]
                seed.created = seed_info[ 'added_timestamp' ]
                seed.modified = seed_info[ 'last_modified_timestamp' ]
                seed.source_time = seed_info[ 'source_timestamp' ]
                seed.note = seed_info[ 'note' ]
                
                seeds.append( seed )
                
            
            new_serialisable_info = seeds.GetSerialisableTuple()
            
            return ( 8, new_serialisable_info )
            
        
    
    def AddPaths( self, paths ):
        
        seeds = [ Seed( SEED_TYPE_HDD, path ) for path in paths if not self.HasPath( path ) ]
        
        self.AddSeeds( seeds )
        
    
    def AddSeeds( self, seeds ):
        
        if len( seeds ) == 0:
            
            return
            
        
        with self._lock:
            
            for seed in seeds:
                
                if self._HasSeed( seed ):
                    
                    continue
                    
                
                self._seeds.append( seed )
                
                self._seeds_to_indices[ seed ] = len( self._seeds ) - 1
                
            
            self._SetDirty()
            
        
        self.NotifySeedsUpdated( seeds )
        
    
    def AddURLs( self, urls ):
        
        seeds = [ Seed( SEED_TYPE_URL, url ) for url in urls if not self.HasURL( url ) ]
        
        self.AddSeeds( seeds )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_indices:
                
                index = self._seeds_to_indices[ seed ]
                
                if index > 0:
                    
                    self._seeds.remove( seed )
                    
                    self._seeds.insert( index - 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
                
            
        
        self.NotifySeedsUpdated( ( seed, ) )
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_indices:
                
                index = self._seeds_to_indices[ seed ]
                
                if index < len( self._seeds ) - 1:
                    
                    self._seeds.remove( seed )
                    
                    self._seeds.insert( index + 1, seed )
                    
                
                self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
                
            
        
        self.NotifySeedsUpdated( ( seed, ) )
        
    
    def GetEarliestSourceTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return None
                
            
            earliest_timestamp = min( ( self._GetSourceTimestamp( seed ) for seed in self._seeds ) )
            
        
        return earliest_timestamp
        
    
    def GetLatestAddedTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( seed.created for seed in self._seeds ) )
            
        
        return latest_timestamp
        
    
    def GetLatestSourceTime( self ):
        
        with self._lock:
            
            if len( self._seeds ) == 0:
                
                return 0
                
            
            latest_timestamp = max( ( self._GetSourceTimestamp( seed ) for seed in self._seeds ) )
            
        
        return latest_timestamp
        
    
    def GetNextSeed( self, status ):
        
        with self._lock:
            
            for seed in self._seeds:
                
                if seed.status == status:
                    
                    return seed
                    
                
            
        
        return None
        
    
    def GetNumNewFilesSince( self, since ):
        
        num_files = 0
        
        with self._lock:
            
            for seed in self._seeds:
                
                source_timestamp = self._GetSourceTimestamp( seed )
                
                if source_timestamp >= since:
                    
                    num_files += 1
                    
                
            
        
        return num_files
        
    
    def GetSeedCacheKey( self ):
        
        return self._seed_cache_key
        
    
    def GetSeedCount( self, status = None ):
        
        result = 0
        
        with self._lock:
            
            if status is None:
                
                result = len( self._seeds )
                
            else:
                
                for seed in self._seeds:
                    
                    if seed.status == status:
                        
                        result += 1
                        
                    
                
            
        
        return result
        
    
    def GetSeeds( self, status = None ):
        
        with self._lock:
            
            return self._GetSeeds( status )
            
        
    
    def GetSeedIndex( self, seed ):
        
        with self._lock:
            
            return self._seeds_to_indices[ seed ]
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._GenerateStatus()
                
            
            return self._status_cache
            
        
    
    def HasPath( self, path ):
        
        seed = Seed( SEED_TYPE_HDD, path )
        
        return self.HasSeed( seed )
        
    
    def HasSeed( self, seed ):
        
        with self._lock:
            
            return self._HasSeed( seed )
            
        
    
    def HasURL( self, url ):
        
        seed = Seed( SEED_TYPE_URL, url )
        
        return self.HasSeed( seed )
        
    
    def NotifySeedsUpdated( self, seeds ):
        
        with self._lock:
            
            self._SetDirty()
            
        
        HG.client_controller.pub( 'seed_cache_seeds_updated', self._seed_cache_key, seeds )
        
    
    def RemoveProcessedSeeds( self ):
        
        with self._lock:
            
            seeds_to_delete = [ seed for seed in self._seeds if seed.status != CC.STATUS_UNKNOWN ]
            
        
        self.RemoveSeeds( seeds_to_delete )
        
    
    def RemoveSeeds( self, seeds ):
        
        with self._lock:
            
            seeds_to_delete = set( seeds )
            
            self._seeds = HydrusSerialisable.SerialisableList( [ seed for seed in self._seeds if seed not in seeds_to_delete ] )
            
            self._seeds_to_indices = { seed : index for ( index, seed ) in enumerate( self._seeds ) }
            
            self._SetDirty()
            
        
        self.NotifySeedsUpdated( seeds_to_delete )
        
    
    def RemoveSeedsByStatus( self, status ):
        
        with self._lock:
            
            seeds_to_delete = [ seed for seed in self._seeds if seed.status == status ]
            
        
        self.RemoveSeeds( seeds_to_delete )
        
    
    def RemoveSuccessfulSeeds( self ):
        
        with self._lock:
            
            seeds_to_delete = [ seed for seed in self._seeds if seed.status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ) ]
            
        
        self.RemoveSeeds( seeds_to_delete )
        
    
    def RetryFailures( self ):
        
        with self._lock:
            
            failed_seeds = self._GetSeeds( CC.STATUS_FAILED )
            
            for seed in failed_seeds:
                
                seed.SetStatus( CC.STATUS_UNKNOWN )
                
            
        
        self.NotifySeedsUpdated( failed_seeds )
        
    
    def WorkToDo( self ):
        
        with self._lock:
            
            if self._dirty:
                
                self._GenerateStatus()
                
            
            ( status, ( total_processed, total ) ) = self._status_cache
            
            return total_processed < total
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
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
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        new_options = HG.client_controller.new_options
        
        self._tag_import_options = new_options.GetDefaultTagImportOptions( self._gallery_identifier )
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetQueriesForProcessing( self ):
        
        queries = list( self._queries )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            random.shuffle( queries )
            
        else:
            
            def key( q ):
                
                return q.GetQueryText()
                
            
            queries.sort( key = key )
            
        
        return queries
        
    
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
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            self._DelayWork( HC.UPDATE_DURATION, 'gallery would not load' )
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription ' + self._name + ' could not load its gallery! It has been paused and the full error has been written to the log!' )
            
            return
            
        
        error_count = 0
        
        all_presentation_hashes = []
        
        queries = self._GetQueriesForProcessing()
        
        for query in queries:
            
            this_query_has_done_work = False
            
            ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
            
            def network_job_factory( method, url, **kwargs ):
                
                network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name + ': ' + query_text, method, url, **kwargs )
                
                job_key.SetVariable( 'popup_network_job', network_job )
                
                return network_job
                
            
            gallery.SetNetworkJobFactory( network_job_factory )
            
            text_1 = 'downloading files'
            file_popup_text = self._name
            
            if query_text != self._name:
                
                text_1 += ' for "' + query_text + '"'
                file_popup_text += ': ' + query_text
                
            
            job_key.SetVariable( 'popup_text_1', text_1 )
            
            num_urls = seed_cache.GetSeedCount()
            
            presentation_hashes = []
            presentation_hashes_fast = set()
            
            while True:
                
                num_unknown = seed_cache.GetSeedCount( CC.STATUS_UNKNOWN )
                num_done = num_urls - num_unknown
                
                seed = seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                
                if seed is None:
                    
                    break
                    
                
                url = seed.seed_data
                
                if job_key.IsCancelled():
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p3 = HG.view_shutdown
                
                example_nj = network_job_factory( 'GET', url )
                
                # just a little padding, to make sure we don't accidentally get into a long wait because we need to fetch file and tags independantly etc...
                expected_requests = 3
                expected_bytes = 1048576
                threshold = 600
                
                p4 = not HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), expected_requests = expected_requests, expected_bytes = expected_bytes, threshold = threshold )
                
                if p1 or p3 or p4:
                    
                    if p4 and this_query_has_done_work:
                        
                        job_key.SetVariable( 'popup_text_2', 'no more bandwidth to download files, so stopping for now' )
                        
                        time.sleep( 2 )
                        
                    
                    break
                    
                
                try:
                    
                    x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_urls ) + ': '
                    
                    job_key.SetVariable( 'popup_text_2', x_out_of_y + 'checking url status' )
                    job_key.SetVariable( 'popup_gauge_2', ( num_done, num_urls ) )
                    
                    ( status, hash, note ) = HG.client_controller.Read( 'url_status', url )
                    
                    if status == CC.STATUS_DELETED:
                        
                        if not self._file_import_options.GetExcludeDeleted():
                            
                            status = CC.STATUS_NEW
                            note = ''
                            
                        
                    
                    downloaded_tags = []
                    
                    if status == CC.STATUS_REDUNDANT:
                        
                        if self._get_tags_if_url_known_and_file_redundant and self._tag_import_options.InterestedInTags():
                            
                            job_key.SetVariable( 'popup_text_2', x_out_of_y + 'found file in db, fetching tags' )
                            
                            downloaded_tags = gallery.GetTags( url )
                            
                        
                    elif status == CC.STATUS_NEW:
                        
                        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                        
                        try:
                            
                            job_key.SetVariable( 'popup_text_2', x_out_of_y + 'downloading file' )
                            
                            if self._tag_import_options.InterestedInTags():
                                
                                downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                                
                            else:
                                
                                gallery.GetFile( temp_path, url )
                                
                            
                            job_key.SetVariable( 'popup_text_2', x_out_of_y + 'importing file' )
                            
                            file_import_job = FileImportJob( temp_path, self._file_import_options )
                            
                            ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                            
                            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( url, ) ) ) ] }
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                            if status == CC.STATUS_SUCCESSFUL:
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'import successful' )
                                
                            elif status == CC.STATUS_DELETED:
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'previously deleted' )
                                
                            elif status == CC.STATUS_REDUNDANT:
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'already in db' )
                                
                            
                            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                                
                                if hash not in presentation_hashes_fast:
                                    
                                    in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                                    
                                    if self._file_import_options.ShouldPresent( status, in_inbox ):
                                        
                                        all_presentation_hashes.append( hash )
                                        
                                        presentation_hashes.append( hash )
                                        
                                        presentation_hashes_fast.add( hash )
                                        
                                    
                                
                            
                        finally:
                            
                            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                    
                    seed.SetStatus( status, note = note )
                    
                    if hash is not None:
                        
                        service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                        
                        if len( service_keys_to_content_updates ) > 0:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                    
                except HydrusExceptions.CancelledException:
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                except HydrusExceptions.MimeException as e:
                    
                    status = CC.STATUS_UNINTERESTING_MIME
                    
                    seed.SetStatus( status )
                    
                except Exception as e:
                    
                    status = CC.STATUS_FAILED
                    
                    job_key.SetVariable( 'popup_text_2', x_out_of_y + 'file failed' )
                    
                    if isinstance( e, HydrusExceptions.NotFoundException ):
                        
                        seed.SetStatus( status, note = '404' )
                        
                    else:
                        
                        seed.SetStatus( status, exception = e )
                        
                    
                    # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                    # this should be richer in any case in the new system
                    if not isinstance( e, HydrusExceptions.DataMissing ):
                        
                        error_count += 1
                        
                        time.sleep( 10 )
                        
                    
                    if error_count > 4:
                        
                        raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                        
                    
                
                this_query_has_done_work = True
                
                if len( presentation_hashes ) > 0:
                    
                    job_key.SetVariable( 'popup_files', ( list( presentation_hashes ), file_popup_text ) )
                    
                
                time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                
                HG.client_controller.WaitUntilViewFree()
                
            
        
        if len( all_presentation_hashes ) > 0:
            
            file_popup_text = self._name
            
            files_job_key = ClientThreading.JobKey()
            
            files_job_key.SetVariable( 'popup_files_mergable', True )
            files_job_key.SetVariable( 'popup_files', ( all_presentation_hashes, file_popup_text ) )
            
            HG.client_controller.pub( 'message', files_job_key )
            
        
        job_key.DeleteVariable( 'popup_files' )
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_text_2' )
        job_key.DeleteVariable( 'popup_gauge_2' )
        
    
    def _WorkOnFilesCanDoWork( self ):
        
        for query in self._queries:
            
            if query.CanWorkOnFiles():
                
                ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
                
                seed = seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                
                if seed is None:
                    
                    return False
                    
                
                def network_job_factory( method, url, **kwargs ):
                    
                    network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name + ': ' + query_text, method, url, **kwargs )
                    
                    # this is prob actually a call to the job_key
                    #wx.CallAfter( self._download_control_set, network_job )
                    
                    return network_job
                    
                
                url = seed.seed_data
                
                example_nj = network_job_factory( 'GET', url )
                
                # just a little padding here
                expected_requests = 3
                expected_bytes = 1048576
                threshold = 30
                
                if HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_nj.GetNetworkContexts(), expected_requests = expected_requests, expected_bytes = expected_bytes, threshold = threshold ):
                    
                    return True
                    
                
            
        
        return False
        
    
    def _SyncQuery( self, job_key ):
        
        queries = self._GetQueriesForProcessing()
        
        for query in queries:
            
            if not query.CanSync():
                
                continue
                
            
            ( query_text, seed_cache ) = query.GetQueryAndSeedCache()
            
            this_is_initial_sync = query.IsInitialSync()
            total_new_urls = 0
            
            urls_to_add = set()
            urls_to_add_ordered = []
            
            prefix = 'synchronising'
            
            if query_text != self._name:
                
                prefix += ' "' + query_text + '"'
                
            
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
                    
                
                try:
                    
                    gallery = ClientDownloading.GetGallery( gallery_stream_identifier )
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    self._DelayWork( HC.UPDATE_DURATION, 'gallery would not load' )
                    
                    self._paused = True
                    
                    HydrusData.ShowText( 'The subscription ' + self._name + ' could not load its gallery! It has been paused and the full error has been written to the log!' )
                    
                    return
                    
                
                def network_job_factory( method, url, **kwargs ):
                    
                    network_job = ClientNetworking.NetworkJobSubscriptionTemporary( self._name + ': ' + query_text, method, url, **kwargs )
                    
                    job_key.SetVariable( 'popup_network_job', network_job )
                    
                    network_job.OverrideBandwidth()
                    
                    return network_job
                    
                
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
                                
                            
                            if seed_cache.HasURL( url ):
                                
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
                    
                
            
            if query.IsDead():
                
                HydrusData.ShowText( 'The query "' + query_text + '" for subscription ' + self._name + ' appears to be dead!' )
                
            
            urls_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the seed_cache should stay roughly in oldest->newest order
            
            new_urls = [ url for url in urls_to_add_ordered if not seed_cache.HasURL( url ) ]
            
            seed_cache.AddURLs( new_urls )
            
            query.RegisterSyncComplete()
            query.UpdateNextCheckTime( self._checker_options )
            
        
    
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
        
    
    def HasQuerySearchText( self, search_text ):
        
        for query in self._queries:
            
            query_text = query.GetQueryText()
            
            if search_text in query_text:
                
                return True
                
            
        
        return False
        
    
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
            
        
    
    def RetryFailures( self ):
        
        for query in self._queries:
            
            query.RetryFailures()
            
        
    
    def Separate( self ):
        
        subscriptions = []
        
        for query in self._queries:
            
            subscription = self.Duplicate()
            
            subscription._queries = [ query.Duplicate() ]
            
            subscription.SetName( self._name + ': ' + query.GetQueryText() )
            
            subscriptions.append( subscription )
            
        
        return subscriptions
        
    
    def SetCheckerOptions( self, checker_options ):
        
        self._checker_options = checker_options
        
        for query in self._queries:
            
            query.UpdateNextCheckTime( self._checker_options )
            
        
    
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
                
                if isinstance( e, HydrusExceptions.NetworkInfrastructureException ):
                    
                    delay = 3600
                    
                else:
                    
                    delay = HC.UPDATE_DURATION
                    
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.PrintException( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._DelayWork( delay, 'network error: ' + HydrusData.ToUnicode( e ) )
                
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
    SERIALISABLE_NAME = 'Subscription Query'
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
        
        seed = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        return seed is not None
        
    
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
        
    
    def GetQueryText( self ):
        
        return self._query
        
    
    def GetSeedCache( self ):
        
        return self._seed_cache
        
    
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
        
    
    def RetryFailures( self ):
        
        self._seed_cache.RetryFailures()    
        
    
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
                
            
            self._next_check_time = checker_options.GetNextCheckTime( self._seed_cache, self._last_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, self._seed_cache )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery

class TagImportOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_IMPORT_OPTIONS
    SERIALISABLE_NAME = 'Tag Import Options'
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
    SERIALISABLE_NAME = 'Thread Watcher'
    SERIALISABLE_VERSION = 4
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        new_options = HG.client_controller.new_options
        
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
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
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
        
        ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( self._thread_url )
        
        if url_type != HC.URL_TYPE_WATCHABLE:
            
            error_occurred = True
            
            watcher_status = 'Did not understand the given URL as watchable!'
            
        elif not can_parse:
            
            error_occurred = True
            
            watcher_status = 'Could not parse the given URL!'
            
        
        if not error_occurred:
            
            # convert to API url as appropriate
            ( url_to_check, parser ) = HG.client_controller.network_engine.domain_manager.GetURLToFetchAndParser( self._thread_url )
            
            if parser is None:
                
                error_occurred = True
                
                watcher_status = 'Could not find a parser for the given URL!'
                
            
        
        if error_occurred:
            
            self._FinishCheck( page_key, watcher_status, error_occurred, watcher_status_should_stick )
            
            return
            
        
        #
        
        with self._lock:
            
            self._watcher_status = 'checking thread'
            
        
        try:
            
            network_job = ClientNetworking.NetworkJobThreadWatcher( self._thread_key, 'GET', url_to_check )
            
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
                    
                
            
            data = network_job.GetContent()
            
            parser = HG.client_controller.network_engine.domain_manager.GetParser( url_to_check )
            
            parse_context = {}
            
            parse_context[ 'thread_url' ] = self._thread_url
            parse_context[ 'url' ] = url_to_check
            
            all_parse_results = parser.Parse( parse_context, data )
            
            subject = ClientParsing.GetTitleFromAllParseResults( all_parse_results )
            
            if subject is None:
                
                subject = ''
                
            
            with self._lock:
                
                self._thread_subject = subject
                
            
            ( num_new, num_already_in ) = UpdateSeedCacheWithAllParseResults( self._urls_cache, all_parse_results )
            
            watcher_status = 'thread checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
            watcher_status_should_stick = False
            
            if num_new > 0:
                
                self._new_files_event.set()
                
            
        except HydrusExceptions.ShutdownException:
            
            return
            
        except HydrusExceptions.ParseException as e:
            
            error_occurred = True
            
            watcher_status = 'Was unable to parse the returned data! Full error written to log!'
            
            HydrusData.PrintException( e )
            
        except HydrusExceptions.NotFoundException:
            
            error_occurred = True
            
            with self._lock:
                
                self._thread_status = CHECKER_STATUS_404
                
            
            watcher_status = ''
            
        except HydrusExceptions.NetworkException as e:
            
            self._DelayWork( 4 * 3600, 'Network problem: ' + HydrusData.ToUnicode( e ) )
            
            watcher_status = ''
            
            HydrusData.PrintException( e )
            
        except Exception as e:
            
            error_occurred = True
            
            watcher_status = HydrusData.ToUnicode( e )
            
            HydrusData.PrintException( e )
            
        
        self._FinishCheck( page_key, watcher_status, error_occurred, watcher_status_should_stick )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _FinishCheck( self, page_key, watcher_status, error_occurred, watcher_status_should_stick ):
        
        if error_occurred:
            
            # the [DEAD] stuff can override watcher status, so let's give a brief time for this to display the error
            
            with self._lock:
                
                self._thread_paused = True
                
                self._watcher_status = watcher_status
                
            
            time.sleep( 5 )
            
        
        with self._lock:
            
            if self._check_now:
                
                self._check_now = False
                
            
            self._watcher_status = watcher_status
            
            self._last_check_time = HydrusData.GetNow()
            
            self._UpdateFileVelocityStatus()
            
            self._UpdateNextCheckTime()
            
            self._PublishPageName( page_key )
            
        
        if not watcher_status_should_stick:
            
            time.sleep( 5 )
            
            with self._lock:
                
                self._watcher_status = ''
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, self._last_check_time, self._files_paused, self._thread_paused, self._thread_status, self._thread_subject, self._no_work_until, self._no_work_until_reason )
        
    
    def _HasThread( self ):
        
        return self._thread_url != ''
        
    
    def _PublishPageName( self, page_key ):
        
        new_options = HG.client_controller.new_options
        
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
                
            
        elif self._thread_paused:
            
            thread_watcher_paused_page_string = new_options.GetNoneableString( 'thread_watcher_paused_page_string' )
            
            if thread_watcher_paused_page_string is not None:
                
                page_name = thread_watcher_paused_page_string + ' ' + page_name
                
            
        
        if page_name != self._last_pubbed_page_name:
            
            HG.client_controller.pub( 'rename_page', page_key, page_name )
            
            self._last_pubbed_page_name = page_name
            
        
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, self._last_check_time, self._files_paused, self._thread_paused, self._thread_status, self._thread_subject, self._no_work_until, self._no_work_until_reason ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _UpdateFileVelocityStatus( self ):
        
        self._file_velocity_status = self._checker_options.GetPrettyCurrentVelocity( self._urls_cache, self._last_check_time )
        
    
    def _UpdateNextCheckTime( self ):
        
        if self._check_now:
            
            self._next_check_time = self._last_check_time + self.MIN_CHECK_PERIOD
            
        else:
            
            if not HydrusData.TimeHasPassed( self._no_work_until ):
                
                self._next_check_time = self._no_work_until + 1
                
            else:
                
                if self._thread_status != CHECKER_STATUS_404:
                    
                    if self._checker_options.IsDead( self._urls_cache, self._last_check_time ):
                        
                        self._thread_status = CHECKER_STATUS_DEAD
                        
                        self._thread_paused = True
                        
                    
                
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
            
        
        if version == 3:
            
            ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, last_check_time, files_paused, thread_paused, thread_status, thread_subject ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( thread_url, serialisable_url_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_options, serialisable_tag_options, last_check_time, files_paused, thread_paused, thread_status, thread_subject, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        seed = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if seed is None:
            
            return
            
        
        did_substantial_work = False
        
        file_url = seed.seed_data
        
        try:
            
            with self._lock:
                
                self._current_action = 'reviewing file'
                
            
            # we now do both url and md5 tests here because cloudflare was sometimes giving optimised versions of images, meaning the api's md5 was unreliable
            # if someone set up a thread watcher of a thread they had previously watched, any optimised images would be redownloaded
            
            ( url_not_known_beforehand, ( status, hash, note ) ) = GetInitialSeedStatus( seed )
            
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
                        
                        return
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        seed.SetStatus( status, note = 'cancelled during download!' )
                        
                        return
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        seed.SetStatus( status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return
                        
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    with self._lock:
                        
                        self._current_action = 'importing file'
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    did_substantial_work = True
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    seed.SetStatus( status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                        did_substantial_work = True
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                seed.SetStatus( status, note = note )
                
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                with self._lock:
                    
                    tags = seed.GetTags()
                    
                    service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( hash, tags )
                    
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                    did_substantial_work = True
                    
                
                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                
                if self._file_import_options.ShouldPresent( status, in_inbox ):
                    
                    ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                    
                    HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                    did_substantial_work = True
                    
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            seed.SetStatus( status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._urls_cache.NotifySeedsUpdated( ( seed, ) )
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _THREADWorkOnFiles( self, page_key ):
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            no_work_to_do = self._files_paused or self._thread_url == '' or not self._urls_cache.WorkToDo()
            
            if no_work_to_do or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_files_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
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
                no_delays = HydrusData.TimeHasPassed( self._no_work_until )
                
                time_to_check = able_to_check and check_due and no_delays
                
            
            if not time_to_check or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_thread_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._CheckThread( page_key )
                    
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
            
            self._no_work_until = 0
            self._no_work_until_reason = ''
            
            self._thread_status = CHECKER_STATUS_OK
            
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
            
            if not HydrusData.TimeHasPassed( self._no_work_until ):
                
                watcher_status = self._no_work_until_reason + ' - ' + 'next check ' + HydrusData.ConvertTimestampToPrettyPending( self._next_check_time )
                
            elif self._thread_status == CHECKER_STATUS_404:
                
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
        
        if thread_url is None:
            
            thread_url = ''
            
        
        if thread_url != '':
            
            thread_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( thread_url )
            
        
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
    SERIALISABLE_NAME = 'Raw URL Import'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
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
        
        seed = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if seed is None:
            
            return
            
        
        did_substantial_work = False
        
        file_url = seed.seed_data
        
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
                        
                    except HydrusExceptions.ShutdownException:
                        
                        return
                        
                    except HydrusExceptions.CancelledException:
                        
                        status = CC.STATUS_SKIPPED
                        
                        seed.SetStatus( status, note = 'cancelled during download!' )
                        
                        return
                        
                    except HydrusExceptions.NetworkException:
                        
                        status = CC.STATUS_FAILED
                        
                        seed.SetStatus( status, note = network_job.GetErrorText() )
                        
                        time.sleep( 2 )
                        
                        return
                        
                    
                    finally:
                        
                        if self._download_control_file_clear is not None:
                            
                            wx.CallAfter( self._download_control_file_clear )
                            
                        
                    
                    file_import_job = FileImportJob( temp_path, self._file_import_options )
                    
                    ( status, hash ) = HG.client_controller.client_files_manager.ImportFile( file_import_job )
                    
                    did_substantial_work = True
                    
                    seed.SetStatus( status )
                    
                    if url_not_known_beforehand and hash is not None:
                        
                        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, ( file_url, ) ) ) ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                        did_substantial_work = True
                        
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                seed.SetStatus( status, note = note )
                
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                
                if self._file_import_options.ShouldPresent( status, in_inbox ):
                    
                    ( media_result, ) = HG.client_controller.Read( 'media_results', ( hash, ) )
                    
                    HG.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                    did_substantial_work = True
                    
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            seed.SetStatus( status )
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_FAILED
            note = '404'
            
            seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._urls_cache.NotifySeedsUpdated( ( seed, ) )
            
            with self._lock:
                
                self._RegenerateSeedCacheStatus()
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        while not ( HG.view_shutdown or HG.client_controller.PageCompletelyDestroyed( page_key ) ):
            
            no_work_to_do = self._paused or not self._urls_cache.WorkToDo()
            
            if no_work_to_do or HG.client_controller.PageClosedButNotDestroyed( page_key ):
                
                self._new_urls_event.wait( 5 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
                    HG.client_controller.WaitUntilViewFree()
                    
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
            
            new_urls = [ url for url in urls if not self._urls_cache.HasURL( url ) ]
            
            if len( new_urls ) > 0:
                
                self._urls_cache.AddURLs( new_urls )
                
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
