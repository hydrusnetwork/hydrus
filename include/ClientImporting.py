import bs4
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientFiles
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals
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
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._get_tags_if_url_known_and_file_redundant = new_options.GetBoolean( 'get_tags_if_url_known_and_file_redundant' )
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        self._gallery_paused = False
        self._files_paused = False
        
        self._import_file_options = ClientDefaults.GetDefaultImportFileOptions()
        
        self._import_tag_options = new_options.GetDefaultImportTagOptions( self._gallery_identifier )
        
        self._seed_cache = SeedCache()
        
        self._lock = threading.Lock()
        
        self._gallery = None
        
        self._gallery_status = 'ready to start'
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        self._file_download_hook = None
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        
        if self._current_gallery_stream_identifier is None:
            
            serialisable_current_gallery_stream_identifier = None
            
        else:
            
            serialisable_current_gallery_stream_identifier = self._current_gallery_stream_identifier.GetSerialisableTuple()
            
        
        serialisable_current_gallery_stream_identifier_found_urls = list( self._current_gallery_stream_identifier_found_urls )
        
        serialisable_pending_gallery_stream_identifiers = [ pending_gallery_stream_identifier.GetSerialisableTuple() for pending_gallery_stream_identifier in self._pending_gallery_stream_identifiers ]
        
        serialisable_file_options = self._import_file_options.GetSerialisableTuple()
        serialisable_tag_options = self._import_tag_options.GetSerialisableTuple()
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
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._import_tag_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        self._seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_seed_cache )
        
    
    def _RegenerateSeedCacheStatus( self, page_key ):
        
        new_seed_cache_status = self._seed_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _SetGalleryStatus( self, page_key, text ):
        
        if self._gallery_status != text:
            
            self._gallery_status = text
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        if self._files_paused:
            
            return
            
        
        do_wait = True
        
        url = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if url is None:
            
            return
            
        
        gallery = ClientDownloading.GetGallery( self._gallery_identifier )
        
        try:
            
            ( status, hash ) = HydrusGlobals.client_controller.Read( 'url_status', url )
            
            if status == CC.STATUS_DELETED:
                
                if not self._import_file_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    
                
            
            downloaded_tags = []
            
            if status == CC.STATUS_REDUNDANT:
                
                if self._get_tags_if_url_known_and_file_redundant and self._import_tag_options.InterestedInTags():
                    
                    downloaded_tags = gallery.GetTags( url, report_hooks = [ self._file_download_hook ] )
                    
                else:
                    
                    do_wait = False
                    
                
            elif status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    # status: x_out_of_y + 'downloading file'
                    
                    if self._import_tag_options.InterestedInTags():
                        
                        downloaded_tags = gallery.GetFileAndTags( temp_path, url, report_hooks = [ self._file_download_hook ] )
                        
                    else:
                        
                        gallery.GetFile( temp_path, url, report_hooks = [ self._file_download_hook ] )
                        
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options, url = url )
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                do_wait = False
                
            
            self._seed_cache.UpdateSeedStatus( url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = self._import_tag_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', ( hash, ) )
                
                HydrusGlobals.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._seed_cache.UpdateSeedStatus( url, status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._seed_cache.UpdateSeedStatus( url, status, exception = e )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        if do_wait:
            
            ClientData.WaitPolitely( page_key )
            
        
    
    def _WorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if self._gallery_paused:
                
                self._SetGalleryStatus( page_key, 'paused' )
                
                return
                
            
            if self._current_query is None:
                
                if len( self._pending_queries ) == 0:
                    
                    self._SetGalleryStatus( page_key, '' )
                    
                    return
                    
                else:
                    
                    self._current_query = self._pending_queries.pop( 0 )
                    self._current_query_num_urls = 0
                    
                    self._current_gallery_stream_identifier = None
                    self._pending_gallery_stream_identifiers = list( self._gallery_stream_identifiers )
                    
                
            
            if self._current_gallery_stream_identifier is None:
                
                if len( self._pending_gallery_stream_identifiers ) == 0:
                    
                    self._SetGalleryStatus( page_key, self._current_query + ' produced ' + HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls' )
                    
                    self._current_query = None
                    
                    return
                    
                else:
                    
                    self._current_gallery_stream_identifier = self._pending_gallery_stream_identifiers.pop( 0 )
                    self._current_gallery_stream_identifier_page_index = 0
                    self._current_gallery_stream_identifier_found_urls = set()
                    
                
            
            gallery = ClientDownloading.GetGallery( self._current_gallery_stream_identifier )
            query = self._current_query
            page_index = self._current_gallery_stream_identifier_page_index
            
            self._SetGalleryStatus( page_key, HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls found, now checking page ' + HydrusData.ConvertIntToPrettyString( self._current_gallery_stream_identifier_page_index + 1 ) )
            
        
        error_occured = False
        
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
                
                if not self._seed_cache.HasSeed( url ):
                    
                    with self._lock:
                        
                        if self._file_limit is not None and self._current_query_num_urls + 1 > self._file_limit:
                            
                            self._current_gallery_stream_identifier = None
                            
                            self._pending_gallery_stream_identifiers = []
                            
                            break
                            
                        
                        self._current_query_num_urls += 1
                        
                    
                    self._seed_cache.AddSeed( url )
                    
                
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.NotFoundException ):
                
                text = 'Gallery 404'
                
            else:
                
                text = HydrusData.ToUnicode( e )
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
            
            with self._lock:
                
                self._current_gallery_stream_identifier = None
                
                self._SetGalleryStatus( page_key, text )
                
            
            time.sleep( 5 )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
            self._SetGalleryStatus( page_key, HydrusData.ConvertIntToPrettyString( self._current_query_num_urls ) + ' urls found so far for ' + query )
            
        
        ClientData.WaitPolitely( page_key )
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        while not ( HydrusGlobals.view_shutdown or HydrusGlobals.client_controller.PageDeleted( page_key ) ):
            
            if HydrusGlobals.client_controller.PageHidden( page_key ):
                
                time.sleep( 0.1 )
                
            else:
                
                try:
                    
                    if not self._gallery_paused:
                        
                        self._WorkOnGallery( page_key )
                        
                    
                    if not self._files_paused:
                        
                        self._WorkOnFiles( page_key )
                        
                    
                    time.sleep( 0.1 )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
        
    
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
            
            return ( self._import_file_options, self._import_tag_options, self._file_limit )
            
        
    
    def GetSeedCache( self ):
        
        return self._seed_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            cancellable = self._current_query is not None
            
            return ( list( self._pending_queries ), self._gallery_status, self._seed_cache_status, self._files_paused, self._gallery_paused, cancellable )
            
        
    
    def GetTagsIfURLKnownAndFileRedundant( self ):
        
        with self._lock:
            
            return self._get_tags_if_url_known_and_file_redundant
            
        
    
    def InvertGetTagsIfURLKnownAndFileRedundant( self ):
        
        with self._lock:
            
            self._get_tags_if_url_known_and_file_redundant = not self._get_tags_if_url_known_and_file_redundant
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
        
    
    def PausePlayGallery( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
        
    
    def PendQuery( self, query ):
        
        with self._lock:
            
            if query not in self._pending_queries:
                
                self._pending_queries.append( query )
                
            
        
    
    def SetDownloadHook( self, hook ):
        
        with self._lock:
            
            self._file_download_hook = hook
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetImportFileOptions( self, import_file_options ):
        
        with self._lock:
            
            self._import_file_options = import_file_options
            
        
    
    def SetImportTagOptions( self, import_tag_options ):
        
        with self._lock:
            
            self._import_tag_options = import_tag_options
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT ] = GalleryImport

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, paths = None, import_file_options = None, paths_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if paths is None:
            
            self._paths_cache = None
            
        else:
            
            self._paths_cache = SeedCache()
            
            for path in paths:
                
                self._paths_cache.AddSeed( path )
                
            
        
        self._import_file_options = import_file_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        self._paused = False
        
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._paths_cache.GetSerialisableTuple()
        serialisable_options = self._import_file_options.GetSerialisableTuple()
        serialisable_paths_to_tags = { path : { service_key.encode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in self._paths_to_tags.items() }
        
        return ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused ) = serialisable_info
        
        self._paths_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
        
    
    def _RegenerateSeedCacheStatus( self, page_key ):
        
        new_seed_cache_status = self._paths_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _WorkOnFiles( self, page_key ):

        path = self._paths_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if path is None:
            
            time.sleep( 1 )
            
            return
            
        
        with self._lock:
            
            if path in self._paths_to_tags:
                
                service_keys_to_tags = self._paths_to_tags[ path ]
                
            else:
                
                service_keys_to_tags = {}
                
            
        
        try:
            
            if not os.path.exists( path ):
                
                raise Exception( 'Source file does not exist!' )
                
            
            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
            
            try:
                
                copied = HydrusPaths.MirrorFile( path, temp_path )
                
                if not copied:
                    
                    raise Exception( 'File failed to copy--see log for error.' )
                    
                
                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                
                ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options )
                
            finally:
                
                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                
            
            self._paths_cache.UpdateSeedStatus( path, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', ( hash, ) )
                
                HydrusGlobals.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
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
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        while not ( HydrusGlobals.view_shutdown or HydrusGlobals.client_controller.PageDeleted( page_key ) ):
            
            if self._paused or HydrusGlobals.client_controller.PageHidden( page_key ):
                
                time.sleep( 0.1 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
        
    
    def GetSeedCache( self ):
        
        return self._paths_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._seed_cache_status, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_VERSION = 3
    
    def __init__( self, name, path = '', import_file_options = None, import_tag_options = None, txt_parse_tag_service_keys = None, mimes = None, actions = None, action_locations = None, period = 3600, open_popup = True ):
        
        if mimes is None:
            
            mimes = HC.ALLOWED_MIMES
            
        
        if import_file_options is None:
            
            import_file_options = ClientDefaults.GetDefaultImportFileOptions()
            
        
        if import_tag_options is None:
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            import_tag_options = new_options.GetDefaultImportTagOptions( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEFAULT ) )
            
        
        if txt_parse_tag_service_keys is None:
            
            txt_parse_tag_service_keys = []
            
        
        if actions is None:
            
            actions = {}
            
            actions[ CC.STATUS_SUCCESSFUL ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_REDUNDANT ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_DELETED ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_FAILED ] = CC.IMPORT_FOLDER_IGNORE
            
        
        if action_locations is None:
            
            action_locations = {}
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._path = path
        self._mimes = mimes
        self._import_file_options = import_file_options
        self._import_tag_options = import_tag_options
        self._txt_parse_tag_service_keys = txt_parse_tag_service_keys
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._open_popup = open_popup
        
        self._path_cache = SeedCache()
        self._last_checked = 0
        self._paused = False
        
    
    def _ActionPaths( self ):
        
        for status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_FAILED ):
            
            action = self._actions[ status ]
            
            if action == CC.IMPORT_FOLDER_DELETE:
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( status )
                    
                    if path is None or HydrusGlobals.view_shutdown:
                        
                        break
                        
                    
                    try:
                        
                        if os.path.exists( path ):
                            
                            ClientData.DeletePath( path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            ClientData.DeletePath( txt_path )
                            
                        
                        self._path_cache.RemoveSeed( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to delete ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif action == CC.IMPORT_FOLDER_MOVE:
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( status )
                    
                    if path is None or HydrusGlobals.view_shutdown:
                        
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
                            
                        
                        self._path_cache.RemoveSeed( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to move ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif status == CC.IMPORT_FOLDER_IGNORE:
                
                pass
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_import_file_options = self._import_file_options.GetSerialisableTuple()
        serialisable_import_tag_options = self._import_tag_options.GetSerialisableTuple()
        serialisable_txt_parse_tag_service_keys = [ service_key.encode( 'hex' ) for service_key in self._txt_parse_tag_service_keys ]
        serialisable_path_cache = self._path_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = self._actions.items()
        action_location_pairs = self._action_locations.items()
        
        return ( self._path, self._mimes, serialisable_import_file_options, serialisable_import_tag_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, self._period, self._open_popup, serialisable_path_cache, self._last_checked, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._mimes, serialisable_import_file_options, serialisable_import_tag_options, serialisable_txt_parse_service_keys, action_pairs, action_location_pairs, self._period, self._open_popup, serialisable_path_cache, self._last_checked, self._paused ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_file_options )
        self._import_tag_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_import_tag_options )
        self._txt_parse_tag_service_keys = [ service_key.decode( 'hex' ) for service_key in serialisable_txt_parse_service_keys ]
        self._path_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_path_cache )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( path, mimes, serialisable_import_file_options, action_pairs, action_location_pairs, period, open_popup, tag, serialisable_path_cache, last_checked, paused ) = old_serialisable_info
            
            service_keys_to_explicit_tags = {}
            
            if tag is not None:
                
                service_keys_to_explicit_tags[ CC.LOCAL_TAG_SERVICE_KEY ] = { tag }
                
            
            import_tag_options = ClientData.ImportTagOptions( service_keys_to_explicit_tags = service_keys_to_explicit_tags )
            
            serialisable_import_tag_options = import_tag_options.GetSerialisableTuple()
            
            new_serialisable_info = ( path, mimes, serialisable_import_file_options, serialisable_import_tag_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( path, mimes, serialisable_import_file_options, serialisable_import_tag_options, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused ) = old_serialisable_info
            
            serialisable_txt_parse_tag_service_keys = []
            
            new_serialisable_info = ( path, mimes, serialisable_import_file_options, serialisable_import_tag_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_path_cache, last_checked, paused )
            
            return ( 3, new_serialisable_info )
            
        
    
    def DoWork( self ):
        
        if HydrusGlobals.view_shutdown:
            
            return
            
        
        if not self._paused and HydrusData.TimeHasPassed( self._last_checked + self._period ):
            
            if os.path.exists( self._path ) and os.path.isdir( self._path ):
                
                filenames = os.listdir( HydrusData.ToUnicode( self._path ) )
                
                raw_paths = [ os.path.join( self._path, filename ) for filename in filenames ]
                
                all_paths = ClientFiles.GetAllPaths( raw_paths )
                
                all_paths = HydrusPaths.FilterFreePaths( all_paths )
                
                for path in all_paths:
                    
                    if path.endswith( '.txt' ):
                        
                        continue
                        
                    
                    if not self._path_cache.HasSeed( path ):
                        
                        self._path_cache.AddSeed( path )
                        
                    
                
                successful_hashes = set()
                
                while True:
                    
                    path = self._path_cache.GetNextSeed( CC.STATUS_UNKNOWN )
                    
                    if path is None or HydrusGlobals.view_shutdown:
                        
                        break
                        
                    
                    try:
                        
                        mime = HydrusFileHandling.GetMime( path )
                        
                        if mime in self._mimes:
                            
                            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                            
                            try:
                                
                                copied = HydrusPaths.MirrorFile( path, temp_path )
                                
                                if not copied:
                                    
                                    raise Exception( 'File failed to copy--see log for error.' )
                                    
                                
                                client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                                
                                ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options )
                                
                            finally:
                                
                                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                                
                            
                            self._path_cache.UpdateSeedStatus( path, status )
                            
                            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                                
                                downloaded_tags = []
                                
                                service_keys_to_content_updates = self._import_tag_options.GetServiceKeysToContentUpdates( hash, downloaded_tags ) # explicit tags
                                
                                if len( service_keys_to_content_updates ) > 0:
                                    
                                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                    
                                
                                txt_path = path + '.txt'
                                
                                if len( self._txt_parse_tag_service_keys ) > 0 and os.path.exists( txt_path ):
                                    
                                    try:
                                        
                                        with open( txt_path, 'rb' ) as f:
                                            
                                            txt_tags_string = f.read()
                                            
                                        
                                        txt_tags = [ HydrusData.ToUnicode( tag ) for tag in HydrusData.SplitByLinesep( txt_tags_string ) ]
                                        
                                        txt_tags = HydrusTags.CleanTags( txt_tags )
                                        
                                        service_keys_to_tags = { service_key : txt_tags for service_key in self._txt_parse_tag_service_keys }
                                        
                                        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                                        
                                        if len( service_keys_to_content_updates ) > 0:
                                            
                                            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                            
                                        
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
                        
                    
                
                if len( successful_hashes ) > 0:
                    
                    HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusData.ConvertIntToPrettyString( len( successful_hashes ) ) + ' files.' )
                    
                    if self._open_popup:
                        
                        job_key = ClientThreading.JobKey()
                        
                        job_key.SetVariable( 'popup_title', 'import folder - ' + self._name )
                        job_key.SetVariable( 'popup_files', successful_hashes )
                        
                        HydrusGlobals.client_controller.pub( 'message', job_key )
                        
                    
                
                self._ActionPaths()
                
            
            self._last_checked = HydrusData.GetNow()
            
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self )
            
        
    
    def GetSeedCache( self ):
        
        return self._path_cache
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._period )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._mimes, self._import_file_options, self._import_tag_options, self._txt_parse_tag_service_keys, self._actions, self._action_locations, self._period, self._open_popup, self._paused )
        
    
    def SetSeedCache( self, seed_cache ):
        
        self._path_cache = seed_cache
        
    
    def SetTuple( self, name, path, mimes, import_file_options, import_tag_options, txt_parse_tag_service_keys, actions, action_locations, period, open_popup, paused ):
        
        if path != self._path:
            
            self._path_cache = SeedCache()
            
        
        if set( mimes ) != set( self._mimes ):
            
            self._path_cache.RemoveSeeds( CC.STATUS_UNINTERESTING_MIME )
            
        
        self._name = name
        self._path = path
        self._mimes = mimes
        self._import_file_options = import_file_options
        self._import_tag_options = import_tag_options
        self._txt_parse_tag_service_keys = txt_parse_tag_service_keys
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._open_popup = open_popup
        self._paused = paused
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER ] = ImportFolder

class PageOfImagesImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        import_file_options = ClientDefaults.GetDefaultImportFileOptions()
        
        self._pending_page_urls = []
        self._urls_cache = SeedCache()
        self._import_file_options = import_file_options
        self._download_image_links = True
        self._download_unlinked_images = False
        self._paused = False
        
        self._parser_status = ''
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        self._file_download_hook = None
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_file_options = self._import_file_options.GetSerialisableTuple()
        
        return ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _RegenerateSeedCacheStatus( self, page_key ):
        
        new_seed_cache_status = self._urls_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _SetParserStatus( self, page_key, text ):
        
        if self._parser_status != text:
            
            self._parser_status = text
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        do_wait = True
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return
            
        
        try:
            
            ( status, hash ) = HydrusGlobals.client_controller.Read( 'url_status', file_url )
            
            if status == CC.STATUS_DELETED:
                
                if not self._import_file_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    
                
            
            if status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    report_hooks = []
                    
                    with self._lock:
                        
                        if self._file_download_hook is not None:
                            
                            report_hooks.append( self._file_download_hook )
                            
                        
                    
                    HydrusGlobals.client_controller.DoHTTP( HC.GET, file_url, report_hooks = report_hooks, temp_path = temp_path )
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options, url = file_url )
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                do_wait = False
                
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', ( hash, ) )
                
                HydrusGlobals.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        if do_wait:
            
            ClientData.WaitPolitely( page_key )
            
        
    
    def _WorkOnQueue( self, page_key ):
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is not None:
            
            return
            
        
        if len( self._pending_page_urls ) > 0:
            
            with self._lock:
                
                page_url = self._pending_page_urls.pop( 0 )
                
                self._SetParserStatus( page_key, 'checking ' + page_url )
                
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
            error_occurred = False
            
            try:
                
                html = HydrusGlobals.client_controller.DoHTTP( HC.GET, page_url )
                
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
                    
                    file_urls.extend( [ urlparse.urljoin( page_url, link[ 'href' ] ) for link in links_with_images ] )
                    
                
                if self._download_unlinked_images:
                    
                    file_urls.extend( [ urlparse.urljoin( page_url, image[ 'src' ] ) for image in unlinked_images ] )
                    
                
                num_new = 0
                
                for file_url in file_urls:
                    
                    if not self._urls_cache.HasSeed( file_url ):
                        
                        num_new += 1
                        
                        self._urls_cache.AddSeed( file_url )
                        
                    
                
                parser_status = 'page checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                parser_status = 'page 404'
                
            except Exception as e:
                
                error_occurred = True
                
                parser_status = HydrusData.ToUnicode( e )
                
            
            with self._lock:
                
                self._SetParserStatus( page_key, parser_status )
                self._RegenerateSeedCacheStatus( page_key )
                
            
            if error_occurred:
                
                time.sleep( 5 )
                
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
            ClientData.WaitPolitely( page_key )
            
        else:
            
            with self._lock:
                
                self._SetParserStatus( page_key, '' )
                
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        while not ( HydrusGlobals.view_shutdown or HydrusGlobals.client_controller.PageDeleted( page_key ) ):
            
            if self._paused or HydrusGlobals.client_controller.PageHidden( page_key ):
                
                time.sleep( 0.1 )
                
            else:
                
                try:
                    
                    self._WorkOnQueue( page_key )
                    
                    self._WorkOnFiles( page_key )
                    
                    time.sleep( 0.1 )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
        
    
    def AdvancePageURL( self, page_url ):
        
        with self._lock:
            
            if page_url in self._pending_page_urls:
                
                index = self._pending_page_urls.index( page_url )
                
                if index - 1 >= 0:
                    
                    self._pending_page_urls.remove( page_url )
                    
                    self._pending_page_urls.insert( index - 1, page_url )
                    
                
            
        
    
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
            
            return ( self._import_file_options, self._download_image_links, self._download_unlinked_images )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( list( self._pending_page_urls ), self._parser_status, self._seed_cache_status, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
        
    
    def PendPageURL( self, page_url ):
        
        with self._lock:
            
            if page_url not in self._pending_page_urls:
                
                self._pending_page_urls.append( page_url )
                
            
        
    
    def SetDownloadHook( self, hook ):
        
        with self._lock:
            
            self._file_download_hook = hook
            
        
    
    def SetDownloadImageLinks( self, value ):
        
        with self._lock:
            
            self._download_image_links = value
            
        
    
    def SetDownloadUnlinkedImages( self, value ):
        
        with self._lock:
            
            self._download_unlinked_images = value
            
        
    
    def SetImportFileOptions( self, import_file_options ):
        
        with self._lock:
            
            self._import_file_options = import_file_options
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT ] = PageOfImagesImport

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._seeds_ordered = []
        self._seeds_to_info = {}
        
        self._lock = threading.Lock()
        
    
    def _GetSeedTuple( self, seed ):
        
        seed_info = self._seeds_to_info[ seed ]
        
        status = seed_info[ 'status' ]
        added_timestamp = seed_info[ 'added_timestamp' ]
        last_modified_timestamp = seed_info[ 'last_modified_timestamp' ]
        note = seed_info[ 'note' ]
        
        return ( seed, status, added_timestamp, last_modified_timestamp, note )
        
    
    def _GetSerialisableInfo( self ):
        
        with self._lock:
            
            serialisable_info = []
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                serialisable_info.append( ( seed, seed_info ) )
                
            
            return serialisable_info
            
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        with self._lock:
            
            for ( seed, seed_info ) in serialisable_info:
                
                self._seeds_ordered.append( seed )
                
                self._seeds_to_info[ seed ] = seed_info
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( seed, seed_info ) in old_serialisable_info:
                
                if 'note' in seed_info:
                    
                    seed_info[ 'note' ] = HydrusData.ToUnicode( seed_info[ 'note' ] )
                    
                
                new_serialisable_info.append( ( seed, seed_info ) )
                
            
            return ( 2, new_serialisable_info )
            
        
    
    def AddSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                self._seeds_ordered.remove( seed )
                
            
            self._seeds_ordered.append( seed )
            
            now = HydrusData.GetNow()
            
            seed_info = {}
            
            seed_info[ 'status' ] = CC.STATUS_UNKNOWN
            seed_info[ 'added_timestamp' ] = now
            seed_info[ 'last_modified_timestamp' ] = now
            seed_info[ 'note' ] = ''
            
            self._seeds_to_info[ seed ] = seed_info
            
        
        HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index > 0:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index - 1, seed )
                    
                
            
        
        HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index < len( self._seeds_ordered ) - 1:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index + 1, seed )
                    
                
            
        
        HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def GetNextSeed( self, status ):
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                if seed_info[ 'status' ] == status:
                    
                    return seed
                    
                
            
        
        return None
        
    
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
                
            
        
    
    def GetSeedsWithInfo( self ):
        
        with self._lock:
            
            all_info = []
            
            for seed in self._seeds_ordered:
                
                seed_tuple = self._GetSeedTuple( seed )
                
                all_info.append( seed_tuple )
                
            
            return all_info
            
        
    
    def GetSeedInfo( self, seed ):
        
        with self._lock:
            
            return self._GetSeedTuple( seed )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
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
            
            total_processed = len( self._seeds_ordered ) - num_unknown
            total = len( self._seeds_ordered )
            
            return ( status, ( total_processed, total ) )
            
        
    
    def HasSeed( self, seed ):
        
        with self._lock:
            
            return seed in self._seeds_to_info
            
        
    
    def RemoveSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
        
        HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def RemoveSeeds( self, status ):
        
        with self._lock:
            
            seeds_to_delete = set()
            
            for ( seed, seed_info ) in self._seeds_to_info.items():
                
                if seed_info[ 'status' ] == status:
                    
                    seeds_to_delete.add( seed )
                    
                
            
            for seed in seeds_to_delete:
                
                del self._seeds_to_info[ seed ]
                
                self._seeds_ordered.remove( seed )
                
            
        
        for seed in seeds_to_delete:
            
            HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
            
        
    
    def UpdateSeedStatus( self, seed, status, note = '', exception = None ):
        
        with self._lock:
            
            if exception is not None:
                
                first_line = HydrusData.ToUnicode( exception ).split( os.linesep )[0]
                
                note = first_line + u'\u2026 (Copy note to see full error)'
                note += os.linesep
                note += HydrusData.ToUnicode( traceback.format_exc() )
                
                HydrusData.Print( 'Error when processing ' + seed + '!' )
                HydrusData.Print( traceback.format_exc() )
                
            
            note = HydrusData.ToUnicode( note )
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'status' ] = status
            seed_info[ 'last_modified_timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = note
            
        
        HydrusGlobals.client_controller.pub( 'seed_cache_seed_updated', seed )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( self._gallery_identifier )
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._query = search_value
        self._period = 86400 * 7
        self._get_tags_if_url_known_and_file_redundant = new_options.GetBoolean( 'get_tags_if_url_known_and_file_redundant' )
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 200
            
        else:
            
            self._initial_file_limit = min( 200, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = None
        self._paused = False
        
        self._import_file_options = ClientDefaults.GetDefaultImportFileOptions()
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._import_tag_options = new_options.GetDefaultImportTagOptions( self._gallery_identifier )
        
        self._last_checked = 0
        self._last_error = 0
        self._check_now = False
        self._seed_cache = SeedCache()
        
    
    def _GetErrorProhibitionTime( self ):
        
        return self._last_error + HC.UPDATE_DURATION
        
    
    def _GetNextPeriodicSyncTime( self ):
        
        return self._last_checked + self._period
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        serialisable_file_options = self._import_file_options.GetSerialisableTuple()
        serialisable_tag_options = self._import_tag_options.GetSerialisableTuple()
        serialisable_seed_cache = self._seed_cache.GetSerialisableTuple()
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, self._query, self._period, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._last_checked, self._check_now, self._last_error, serialisable_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, self._query, self._period, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._last_checked, self._check_now, self._last_error, serialisable_seed_cache ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._import_tag_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        self._seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_seed_cache )
        
    
    def _NoRecentErrors( self ):
        
        return HydrusData.TimeHasPassed( self._GetErrorProhibitionTime() )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, last_error, serialisable_seed_cache ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, serialisable_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, job_key ):
        
        error_count = 0
        
        num_urls = self._seed_cache.GetSeedCount()
        
        successful_hashes = set()
        
        gallery = ClientDownloading.GetGallery( self._gallery_identifier )
        
        def hook( gauge_range, gauge_value ):
            
            job_key.SetVariable( 'popup_gauge_2', ( gauge_value, gauge_range ) )
            
        
        while True:
            
            num_unknown = self._seed_cache.GetSeedCount( CC.STATUS_UNKNOWN )
            num_done = num_urls - num_unknown
            
            do_wait = True
            
            url = self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN )
            
            if url is None:
                
                break
                
            
            p1 = HC.options[ 'pause_subs_sync' ]
            p2 = job_key.IsCancelled()
            p3 = HydrusGlobals.view_shutdown
            
            if p1 or p2 or p3:
                
                break
                
            
            try:
                
                x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_urls ) + ': '
                
                job_key.SetVariable( 'popup_text_1', x_out_of_y + 'checking url status' )
                job_key.SetVariable( 'popup_gauge_1', ( num_done, num_urls ) )
                
                ( status, hash ) = HydrusGlobals.client_controller.Read( 'url_status', url )
                
                if status == CC.STATUS_DELETED:
                    
                    if not self._import_file_options.GetExcludeDeleted():
                        
                        status = CC.STATUS_NEW
                        
                    
                
                downloaded_tags = []
                
                if status == CC.STATUS_REDUNDANT:
                    
                    if self._get_tags_if_url_known_and_file_redundant and self._import_tag_options.InterestedInTags():
                        
                        job_key.SetVariable( 'popup_text_1', x_out_of_y + 'found file in db, fetching tags' )
                        
                        downloaded_tags = gallery.GetTags( url, report_hooks = [ hook ] )
                        
                    else:
                        
                        do_wait = False
                        
                    
                elif status == CC.STATUS_NEW:
                    
                    ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                    
                    try:
                        
                        job_key.SetVariable( 'popup_text_1', x_out_of_y + 'downloading file' )
                        
                        if self._import_tag_options.InterestedInTags():
                            
                            downloaded_tags = gallery.GetFileAndTags( temp_path, url, report_hooks = [ hook ] )
                            
                        else:
                            
                            gallery.GetFile( temp_path, url, report_hooks = [ hook ] )
                            
                        
                        job_key.SetVariable( 'popup_text_1', x_out_of_y + 'importing file' )
                        
                        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                        
                        ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options, url = url )
                        
                        if status == CC.STATUS_SUCCESSFUL:
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'import successful' )
                            
                            successful_hashes.add( hash )
                            
                        elif status == CC.STATUS_DELETED:
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'previously deleted' )
                            
                        elif status == CC.STATUS_REDUNDANT:
                            
                            job_key.SetVariable( 'popup_text_1', x_out_of_y + 'already in db' )
                            
                        
                    finally:
                        
                        HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                else:
                    
                    do_wait = False
                    
                
                self._seed_cache.UpdateSeedStatus( url, status )
                
                if hash is not None:
                    
                    service_keys_to_content_updates = self._import_tag_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                    
                    if len( service_keys_to_content_updates ) > 0:
                        
                        HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                
            except HydrusExceptions.MimeException as e:
                
                status = CC.STATUS_UNINTERESTING_MIME
                
                self._seed_cache.UpdateSeedStatus( url, status )
                
            except Exception as e:
                
                status = CC.STATUS_FAILED
                
                job_key.SetVariable( 'popup_text_1', x_out_of_y + 'file failed' )
                
                self._seed_cache.UpdateSeedStatus( url, status, exception = e )
                
                # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                # this should be richer in any case in the new system
                if not isinstance( e, HydrusExceptions.DataMissing ):
                    
                    error_count += 1
                    
                    time.sleep( 10 )
                    
                
                if error_count > 4:
                    
                    raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                    
                
            
            if len( successful_hashes ) > 0:
                
                job_key.SetVariable( 'popup_files', set( successful_hashes ) )
                
            
            if do_wait:
                
                ClientData.WaitPolitely()
                
            
        
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.DeleteVariable( 'popup_gauge_2' )
        
    
    def _WorkOnFilesCanDoWork( self ):
        
        return self._seed_cache.GetNextSeed( CC.STATUS_UNKNOWN ) is not None
        
    
    def _SyncQuery( self, job_key ):
        
        if self._SyncQueryCanDoWork():
            
            this_is_initial_sync = self._last_checked == 0
            total_new_urls = 0
            
            urls_to_add = set()
            urls_to_add_ordered = []
            
            prefix = 'synchronising gallery query'
            
            job_key.SetVariable( 'popup_text_1', prefix )
            
            for gallery_stream_identifier in self._gallery_stream_identifiers:
                
                if this_is_initial_sync:
                    
                    if self._initial_file_limit is not None and total_new_urls + 1 > self._initial_file_limit:
                        
                        continue
                        
                    
                else:
                    
                    if self._periodic_file_limit is not None and total_new_urls + 1 > self._periodic_file_limit:
                        
                        continue
                        
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p2 = job_key.IsCancelled()
                p3 = HydrusGlobals.view_shutdown
                
                if p1 or p2 or p3:
                    
                    return
                    
                
                gallery = ClientDownloading.GetGallery( gallery_stream_identifier )
                page_index = 0
                keep_checking = True
                
                while keep_checking:
                    
                    new_urls_this_page = 0
                    
                    try:
                        
                        ( page_of_urls, definitely_no_more_pages ) = gallery.GetPage( self._query, page_index )
                        
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
                                
                            
                            if self._seed_cache.HasSeed( url ):
                                
                                keep_checking = False
                                
                                break
                                
                            else:
                                
                                urls_to_add.add( url )
                                urls_to_add_ordered.append( url )
                                
                                new_urls_this_page += 1
                                total_new_urls += 1
                                
                            
                        
                    except HydrusExceptions.NotFoundException:
                        
                        # paheal now 404s when no results, so just move on and naturally break
                        
                        pass
                        
                    
                    if new_urls_this_page == 0:
                        
                        keep_checking = False
                        
                    
                    job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ConvertIntToPrettyString( total_new_urls ) + ' new urls' )
                    
                    ClientData.WaitPolitely()
                    
                
            
            self._last_checked = HydrusData.GetNow()
            
            urls_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the seed_cache should stay roughly in oldest->newest order
            
            for url in urls_to_add_ordered:
                
                if not self._seed_cache.HasSeed( url ):
                    
                    self._seed_cache.AddSeed( url )
                    
                
            
        
    
    def _SyncQueryCanDoWork( self ):
        
        return HydrusData.TimeHasPassed( self._GetNextPeriodicSyncTime() ) or self._check_now
        
    
    def CheckNow( self ):
        
        self._check_now = True
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetQuery( self ):
        
        return self._query
        
    
    def GetImportTagOptions( self ):
        
        return self._import_tag_options
        
    
    def GetSeedCache( self ):
        
        return self._seed_cache
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def Reset( self ):
        
        self._last_checked = 0
        self._last_error = 0
        self._seed_cache = SeedCache()
        
    
    def SetTuple( self, gallery_identifier, gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options, last_checked, last_error, check_now, seed_cache ):
        
        self._gallery_identifier = gallery_identifier
        self._gallery_stream_identifiers = gallery_stream_identifiers
        self._query = query
        self._period = period
        self._get_tags_if_url_known_and_file_redundant = get_tags_if_url_known_and_file_redundant
        self._initial_file_limit = initial_file_limit
        self._periodic_file_limit = periodic_file_limit
        self._paused = paused
        
        self._import_file_options = import_file_options
        self._import_tag_options = import_tag_options
        
        self._last_checked = last_checked
        self._last_error = last_error
        self._check_now = check_now
        self._seed_cache = seed_cache
        
    
    def Sync( self ):
        
        p1 = not self._paused
        p2 = not HydrusGlobals.view_shutdown
        p3 = self._check_now
        p4 = self._NoRecentErrors()
        p5 = self._SyncQueryCanDoWork()
        p6 = self._WorkOnFilesCanDoWork()
        
        if p1 and p2 and ( p3 or p4 ) and ( p5 or p6 ):
            
            job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
            
            try:
                
                job_key.SetVariable( 'popup_title', 'subscriptions - ' + self._name )
                
                HydrusGlobals.client_controller.pub( 'message', job_key )
                
                self._SyncQuery( job_key )
                
                self._WorkOnFiles( job_key )
                
            except HydrusExceptions.NetworkException as e:
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.PrintException( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._last_error = HydrusData.GetNow()
                
                time.sleep( 5 )
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                self._last_error = HydrusData.GetNow()
                
            finally:
                
                self._check_now = False
                
            
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self )
            
            if job_key.HasVariable( 'popup_files' ):
                
                job_key.Finish()
                
            else:
                
                job_key.Delete()
                
            
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gallery_identifier, self._gallery_stream_identifiers, self._query, self._period, self._get_tags_if_url_known_and_file_redundant, self._initial_file_limit, self._periodic_file_limit, self._paused, self._import_file_options, self._import_tag_options, self._last_checked, self._last_error, self._check_now, self._seed_cache )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class ThreadWatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT
    SERIALISABLE_VERSION = 1
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        import_file_options = ClientDefaults.GetDefaultImportFileOptions()
        
        ( times_to_check, check_period ) = HC.options[ 'thread_checker_timings' ]
        
        self._thread_url = ''
        self._urls_cache = SeedCache()
        self._urls_to_filenames = {}
        self._urls_to_md5_base64 = {}
        self._import_file_options = import_file_options
        self._import_tag_options = ClientData.ImportTagOptions()
        self._times_to_check = times_to_check
        self._check_period = check_period
        self._last_time_checked = 0
        
        self._file_download_hook = None
        self._check_now = False
        self._paused = False
        
        self._watcher_status = 'ready to start'
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_file_options = self._import_file_options.GetSerialisableTuple()
        serialisable_tag_options = self._import_tag_options.GetSerialisableTuple()
        
        return ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_file_options, serialisable_tag_options, self._times_to_check, self._check_period, self._last_time_checked, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_file_options, serialisable_tag_options, self._times_to_check, self._check_period, self._last_time_checked, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._import_tag_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _RegenerateSeedCacheStatus( self, page_key ):
        
        new_seed_cache_status = self._urls_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _SetWatcherStatus( self, page_key, text ):
        
        if self._watcher_status != text:
            
            self._watcher_status = text
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    
    def _WorkOnFiles( self, page_key ):
        
        do_wait = True
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return
            
        
        try:
            
            file_original_filename = self._urls_to_filenames[ file_url ]
            
            downloaded_tags = [ 'filename:' + file_original_filename ]
            
            # we now do both url and md5 tests here because cloudflare was sometimes giving optimised versions of images, meaning the api's md5 was unreliable
            # if someone set up a thread watcher of a thread they had previously watched, any optimised images would be redownloaded
            
            ( status, hash ) = HydrusGlobals.client_controller.Read( 'url_status', file_url )
            
            if status == CC.STATUS_NEW:
                
                if file_url in self._urls_to_md5_base64:
                    
                    file_md5_base64 = self._urls_to_md5_base64[ file_url ]
                    
                    file_md5 = file_md5_base64.decode( 'base64' )
                    
                    ( status, hash ) = HydrusGlobals.client_controller.Read( 'md5_status', file_md5 )
                    
                
            
            if status == CC.STATUS_DELETED:
                
                if not self._import_file_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    
                
            
            if status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    report_hooks = []
                    
                    with self._lock:
                        
                        if self._file_download_hook is not None:
                            
                            report_hooks.append( self._file_download_hook )
                            
                        
                    
                    HydrusGlobals.client_controller.DoHTTP( HC.GET, file_url, report_hooks = report_hooks, temp_path = temp_path )
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options, url = file_url )
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                do_wait = False
                
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                with self._lock:
                    
                    service_keys_to_content_updates = self._import_tag_options.GetServiceKeysToContentUpdates( hash, downloaded_tags )
                    
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', ( hash, ) )
                
                HydrusGlobals.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        if do_wait:
            
            ClientData.WaitPolitely( page_key )
            
        
    
    def _WorkOnThread( self, page_key ):
        
        do_wait = False
        error_occurred = False
        
        with self._lock:
            
            p1 = self._check_now and HydrusData.TimeHasPassed( self._last_time_checked + self.MIN_CHECK_PERIOD )
            p2 = self._times_to_check > 0 and HydrusData.TimeHasPassed( self._last_time_checked + self._check_period )
            
        
        if p1 or p2:
            
            with self._lock:
                
                self._SetWatcherStatus( page_key, 'checking thread' )
                
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
            try:
                
                json_url = ClientDownloading.GetImageboardThreadJSONURL( self._thread_url )
                
                do_wait = True
                
                raw_json = HydrusGlobals.client_controller.DoHTTP( HC.GET, json_url )
                
                file_infos = ClientDownloading.ParseImageboardFileURLsFromJSON( self._thread_url, raw_json )
                
                num_new = 0
                
                for ( file_url, file_md5_base64, file_original_filename ) in file_infos:
                    
                    if not self._urls_cache.HasSeed( file_url ):
                        
                        num_new += 1
                        
                        self._urls_cache.AddSeed( file_url )
                        
                        self._urls_to_filenames[ file_url ] = file_original_filename
                        
                        if file_md5_base64 is not None:
                            
                            self._urls_to_md5_base64[ file_url ] = file_md5_base64
                            
                        
                    
                
                watcher_status = 'thread checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new urls'
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                watcher_status = 'thread 404'
                
                with self._lock:
                    
                    for i in range( self._times_to_check ):
                        
                        HydrusGlobals.client_controller.pub( 'decrement_times_to_check', page_key )
                        
                    
                    self._times_to_check = 0
                    
                
            except Exception as e:
                
                error_occurred = True
                
                watcher_status = HydrusData.ToUnicode( e )
                
            
            with self._lock:
                
                if self._check_now:
                    
                    self._check_now = False
                    
                else:
                    
                    self._times_to_check -= 1
                    
                    HydrusGlobals.client_controller.pub( 'decrement_times_to_check', page_key )
                    
                
                self._last_time_checked = HydrusData.GetNow()
                
            
        else:
            
            with self._lock:
                
                if self._check_now or self._times_to_check > 0:
                    
                    if self._check_now:
                        
                        delay = self.MIN_CHECK_PERIOD
                        
                    else:
                        
                        delay = self._check_period
                        
                    
                    watcher_status = 'checking again ' + HydrusData.ConvertTimestampToPrettyPending( self._last_time_checked + delay )
                    
                else:
                    
                    watcher_status = 'checking finished'
                    
                
            
        
        with self._lock:
            
            self._SetWatcherStatus( page_key, watcher_status )
            self._RegenerateSeedCacheStatus( page_key )
            
        
        if do_wait:
            
            ClientData.WaitPolitely( page_key )
            
        
        if error_occurred:
            
            time.sleep( 5 )
            
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        while not ( HydrusGlobals.view_shutdown or HydrusGlobals.client_controller.PageDeleted( page_key ) ):
            
            if self._paused or HydrusGlobals.client_controller.PageHidden( page_key ):
                
                time.sleep( 0.1 )
                
            else:
                
                try:
                    
                    if self._thread_url != '':
                        
                        self._WorkOnThread( page_key )
                        
                        self._WorkOnFiles( page_key )
                        
                    
                    time.sleep( 0.1 )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
        
    
    def CheckNow( self ):
        
        with self._lock:
            
            self._check_now = True
            
        
    
    def GetSeedCache( self ):
        
        return self._urls_cache
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._thread_url, self._import_file_options, self._import_tag_options, self._times_to_check, self._check_period )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._watcher_status, self._seed_cache_status, self._check_now, self._paused )
            
        
    
    def HasThread( self ):
        
        with self._lock:
            
            return self._thread_url != ''
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
        
    
    def SetCheckPeriod( self, check_period ):
        
        with self._lock:
            
            self._check_period = max( self.MIN_CHECK_PERIOD, check_period )
            
        
    
    def SetDownloadHook( self, hook ):
        
        with self._lock:
            
            self._file_download_hook = hook
            
        
    
    def SetImportFileOptions( self, import_file_options ):
        
        with self._lock:
            
            self._import_file_options = import_file_options
            
        
    
    def SetImportTagOptions( self, import_tag_options ):
        
        with self._lock:
            
            self._import_tag_options = import_tag_options
            
        
    
    def SetThreadURL( self, thread_url ):
        
        with self._lock:
            
            self._thread_url = thread_url
            
        
    
    def SetTimesToCheck( self, times_to_check ):
        
        with self._lock:
            
            self._times_to_check = times_to_check
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT ] = ThreadWatcherImport

class URLsImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        import_file_options = ClientDefaults.GetDefaultImportFileOptions()
        
        self._urls_cache = SeedCache()
        self._import_file_options = import_file_options
        self._paused = False
        
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        self._file_download_hook = None
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = self._urls_cache.GetSerialisableTuple()
        serialisable_file_options = self._import_file_options.GetSerialisableTuple()
        
        return ( serialisable_url_cache, serialisable_file_options, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_file_options, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _RegenerateSeedCacheStatus( self, page_key ):
        
        new_seed_cache_status = self._urls_cache.GetStatus()
        
        if self._seed_cache_status != new_seed_cache_status:
            
            self._seed_cache_status = new_seed_cache_status
            
            HydrusGlobals.client_controller.pub( 'update_status', page_key )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        do_wait = True
        
        file_url = self._urls_cache.GetNextSeed( CC.STATUS_UNKNOWN )
        
        if file_url is None:
            
            return
            
        
        try:
            
            ( status, hash ) = HydrusGlobals.client_controller.Read( 'url_status', file_url )
            
            if status == CC.STATUS_DELETED:
                
                if not self._import_file_options.GetExcludeDeleted():
                    
                    status = CC.STATUS_NEW
                    
                
            
            if status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                try:
                    
                    report_hooks = []
                    
                    with self._lock:
                        
                        if self._file_download_hook is not None:
                            
                            report_hooks.append( self._file_download_hook )
                            
                        
                    
                    HydrusGlobals.client_controller.DoHTTP( HC.GET, file_url, report_hooks = report_hooks, temp_path = temp_path )
                    
                    client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                    
                    ( status, hash ) = client_files_manager.ImportFile( temp_path, import_file_options = self._import_file_options, url = file_url )
                    
                finally:
                    
                    HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            else:
                
                do_wait = False
                
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', ( hash, ) )
                
                HydrusGlobals.client_controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except HydrusExceptions.MimeException as e:
            
            status = CC.STATUS_UNINTERESTING_MIME
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
        except Exception as e:
            
            status = CC.STATUS_FAILED
            
            self._urls_cache.UpdateSeedStatus( file_url, status, exception = e )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        if do_wait:
            
            ClientData.WaitPolitely( page_key )
            
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus( page_key )
            
        
        HydrusGlobals.client_controller.pub( 'update_status', page_key )
        
        while not ( HydrusGlobals.view_shutdown or HydrusGlobals.client_controller.PageDeleted( page_key ) ):
            
            if self._paused or HydrusGlobals.client_controller.PageHidden( page_key ):
                
                time.sleep( 0.1 )
                
            else:
                
                try:
                    
                    self._WorkOnFiles( page_key )
                    
                    time.sleep( 0.1 )
                    
                    HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
            
        
    
    def GetSeedCache( self ):
        
        return self._urls_cache
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return self._import_file_options
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._seed_cache_status, self._paused )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
        
    
    def PendURLs( self, urls ):
        
        with self._lock:
            
            for url in urls:
                
                if not self._urls_cache.HasSeed( url ):
                    
                    self._urls_cache.AddSeed( url )
                    
                
            
        
    
    def SetDownloadHook( self, hook ):
        
        with self._lock:
            
            self._file_download_hook = hook
            
        
    
    def SetImportFileOptions( self, import_file_options ):
        
        with self._lock:
            
            self._import_file_options = import_file_options
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLsImport
