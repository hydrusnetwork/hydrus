import bs4
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals
import HydrusSerialisable
import json
import os
import threading
import time
import traceback
import urlparse
import wx

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
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._paths_cache )
        serialisable_options = HydrusSerialisable.GetSerialisableTuple( self._import_file_options )
        serialisable_paths_to_tags = { path : { service_key.encode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in self._paths_to_tags.items() }
        
        return ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_url_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused ) = serialisable_info
        
        self._paths_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
        
    
    def _RegenerateSeedCacheStatus( self ):
        
        self._seed_cache_status = self._paths_cache.GetStatus()
        
    
    def _WorkOnFiles( self, page_key ):

        path = self._paths_cache.GetNextUnknownSeed()
        
        with self._lock:
            
            if path is not None:
                
                if path in self._paths_to_tags:
                    
                    service_keys_to_tags = self._paths_to_tags[ path ]
                    
                else:
                    
                    service_keys_to_tags = {}
                    
                
            
        
        if path is not None:
            
            try:
                
                ( status, media_result ) = HydrusGlobals.controller.WriteSynchronous( 'import_file', path, import_file_options = self._import_file_options, service_keys_to_tags = service_keys_to_tags, generate_media_result = True )
                
                self._paths_cache.UpdateSeedStatus( path, status )
                
                if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                    
                    HydrusGlobals.controller.pub( 'add_media_results', page_key, ( media_result, ) )
                    
                    if self._delete_after_success:
                        
                        try:
                            
                            HydrusData.DeletePath( path )
                            
                        except:
                            
                            pass
                            
                        
                    
                
            except Exception as e:
                
                traceback.print_exc()
                
                status = CC.STATUS_FAILED
                
                note = HydrusData.ToString( e )
                
                self._paths_cache.UpdateSeedStatus( path, status, note = note )
                
            
            with self._lock:
                
                self._RegenerateSeedCacheStatus()
                
            
            HydrusGlobals.controller.pub( 'update_status', page_key )
            
        else:
            
            time.sleep( 1 )
            
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
        while True:
            
            if HydrusGlobals.view_shutdown:
                
                return
                
            
            while self._paused:
                
                if HydrusGlobals.view_shutdown:
                    
                    return
                    
                
                time.sleep( 0.1 )
                
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HydrusGlobals.controller.WaitUntilPubSubsEmpty()
                
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
            
        
    
    def Pause( self ):
        
        with self._lock:
            
            self._paused = True
            
        
    
    def Resume( self ):
        
        with self._lock:
            
            self._paused = False
            
        
    
    def Start( self, page_key ):
        
        threading.Thread( target = self._THREADWork, args = ( page_key, ) ).start()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class GalleryQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_QUERY
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = None
        self._query_type = None
        self._query = None
        self._get_tags_if_redundant = False
        self._file_limit = 500
        self._paused = False
        self._page_index = 0
        self._url_cache = None
        self._options = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._url_cache )
        
        serialisable_options = { name : HydrusSerialisable.GetSerialisableTuple( options ) for ( name, options ) in self._options.items() }
        
        return ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, self._file_limit, serialisable_url_cache, serialisable_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._query_type, self._query, self._get_tags_if_redundant, serialisable_url_cache_tuple, serialisable_options_tuple ) = serialisable_info
        
        self._url_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache_tuple )
        
        self._options = { name : HydrusSerialisable.CreateFromSerialisableTuple( serialisable_suboptions_tuple ) for ( name, serialisable_suboptions_tuple ) in serialisable_options_tuple.items() }
        
    
    def GetQuery( self ):
        
        return self._query
        
    
    def SetTuple( self, site_type, query_type, query, get_tags_if_redundant, file_limit, options ):
        
        self._site_type = site_type
        self._query_type = query_type
        self._query = query
        self._get_tags_if_redundant = get_tags_if_redundant
        self._file_limit = file_limit
        self._url_cache = SeedCache()
        self._options = options
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_QUERY ] = GalleryQuery

class PageOfImagesImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PAGE_OF_IMAGES_IMPORT
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        result = ClientDefaults.GetDefaultImportFileOptions()
        
        automatic_archive = result[ 'auto_archive' ]
        exclude_deleted = result[ 'exclude_deleted_files' ]
        min_size = result[ 'min_size' ]
        min_resolution = result[ 'min_resolution' ]
        
        import_file_options = ClientData.ImportFileOptions( automatic_archive = automatic_archive, exclude_deleted = exclude_deleted, min_size = min_size, min_resolution = min_resolution )
        
        self._pending_page_urls = []
        self._urls_cache = SeedCache()
        self._import_file_options = import_file_options
        self._download_image_links = True
        self._download_unlinked_images = False
        
        self._file_download_hook = None
        self._paused = False
        
        self._parser_status = ''
        self._seed_cache_status = ( 'initialising', ( 0, 1 ) )
        
        self._lock = threading.Lock()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._urls_cache )
        serialisable_file_options = HydrusSerialisable.GetSerialisableTuple( self._import_file_options )
        
        return ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._pending_page_urls, serialisable_url_cache, serialisable_file_options, self._download_image_links, self._download_unlinked_images, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _RegenerateSeedCacheStatus( self ):
        
        self._seed_cache_status = self._urls_cache.GetStatus()
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_url = self._urls_cache.GetNextUnknownSeed()
        
        if file_url is None:
            
            return
            
        
        try:
            
            ( status, hash ) = HydrusGlobals.controller.Read( 'url_status', file_url )
            
            if status == CC.STATUS_REDUNDANT:
                
                ( media_result, ) = HydrusGlobals.controller.Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
                
            elif status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                
                try:
                    
                    report_hooks = []
                    
                    with self._lock:
                        
                        if self._file_download_hook is not None:
                            
                            report_hooks.append( self._file_download_hook )
                            
                        
                    
                    HydrusGlobals.controller.DoHTTP( HC.GET, file_url, report_hooks = report_hooks, temp_path = temp_path )
                    
                    ( status, media_result ) = HydrusGlobals.controller.WriteSynchronous( 'import_file', temp_path, import_file_options = self._import_file_options, generate_media_result = True, url = file_url )
                    
                finally:
                    
                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                HydrusGlobals.controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except Exception as e:
            
            traceback.print_exc()
            
            status = CC.STATUS_FAILED
            
            note = HydrusData.ToString( e )
            
            self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
    
    def _WorkOnQueue( self, page_key ):
        
        file_url = self._urls_cache.GetNextUnknownSeed()
        
        if file_url is not None:
            
            return
            
        
        if len( self._pending_page_urls ) > 0:
            
            with self._lock:
                
                page_url = self._pending_page_urls.pop( 0 )
                
                self._parser_status = 'checking ' + page_url
                
            
            HydrusGlobals.controller.pub( 'update_status', page_key )
            
            error_occurred = False
            
            try:
                
                html = HydrusGlobals.controller.DoHTTP( HC.GET, page_url )
                
                soup = bs4.BeautifulSoup( html )
                
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
                        
                    
                
                parser_status = 'page checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new files'
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                parser_status = 'page 404'
                
            except Exception as e:
                
                error_occurred = True
                
                parser_status = HydrusData.ToString( e )
                
            
            with self._lock:
                
                self._parser_status = parser_status
                self._RegenerateSeedCacheStatus()
                
            
            if error_occurred:
                
                HydrusGlobals.controller.pub( 'update_status', page_key )
                
                time.sleep( 5 )
                
            
        else:
            
            with self._lock:
                
                self._parser_status = ''
                
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
        while True:
            
            if HydrusGlobals.view_shutdown:
                
                return
                
            
            while self._paused:
                
                if HydrusGlobals.view_shutdown:
                    
                    return
                    
                
                time.sleep( 0.1 )
                
            
            try:
                
                self._WorkOnQueue( page_key )
                
                self._WorkOnFiles( page_key )
                
                time.sleep( 1 )
                
                HydrusGlobals.controller.WaitUntilPubSubsEmpty()
                
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
            
        
    
    def Pause( self ):
        
        with self._lock:
            
            self._paused = True
            
        
    
    def PendPageURL( self, page_url ):
        
        with self._lock:
            
            if page_url not in self._pending_page_urls:
                
                self._pending_page_urls.append( page_url )
                
            
        
    
    def Resume( self ):
        
        with self._lock:
            
            self._paused = False
            
        
    
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

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._site_type = None
        self._query_type = None
        self._query = None
        self._get_tags_if_redundant = False
        self._file_limit = 500
        self._periodic = None
        self._page_index = 0
        self._url_cache = None
        self._options = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return ( HydrusSerialisable.GetSerialisableTuple( self._gallery_query ), HydrusSerialisable.GetSerialisableTuple( self._periodic ) )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialised_gallery_query_tuple, serialised_periodic_tuple ) = serialisable_info
        
        self._gallery_query = HydrusSerialisable.CreateFromSerialisableTuple( serialised_gallery_query_tuple )
        
        self._periodic = HydrusSerialisable.CreateFromSerialisableTuple( serialised_periodic_tuple )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class SeedCache( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE
    SERIALISABLE_VERSION = 1
    
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
            
        
        HydrusGlobals.controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def AdvanceSeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index > 0:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index - 1, seed )
                    
                
            
        
        HydrusGlobals.controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def DelaySeed( self, seed ):
        
        with self._lock:
            
            if seed in self._seeds_to_info:
                
                index = self._seeds_ordered.index( seed )
                
                if index < len( self._seeds_ordered ) - 1:
                    
                    self._seeds_ordered.remove( seed )
                    
                    self._seeds_ordered.insert( index + 1, seed )
                    
                
            
        
        HydrusGlobals.controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def GetNextUnknownSeed( self ):
        
        with self._lock:
            
            for seed in self._seeds_ordered:
                
                seed_info = self._seeds_to_info[ seed ]
                
                if seed_info[ 'status' ] == CC.STATUS_UNKNOWN:
                    
                    return seed
                    
                
            
        
        return None
        
    
    def GetSeeds( self ):
        
        with self._lock:
            
            return list( self._seeds_ordered )
            
        
    
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
            
            if num_successful > 0: status_strings.append( HydrusData.ToString( num_successful ) + ' successful' )
            if num_failed > 0: status_strings.append( HydrusData.ToString( num_failed ) + ' failed' )
            if num_deleted > 0: status_strings.append( HydrusData.ToString( num_deleted ) + ' already deleted' )
            if num_redundant > 0: status_strings.append( HydrusData.ToString( num_redundant ) + ' already in db' )
            
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
                
            
        
        HydrusGlobals.controller.pub( 'seed_cache_seed_updated', seed )
        
    
    def UpdateSeedStatus( self, seed, status, note = '' ):
        
        with self._lock:
            
            seed_info = self._seeds_to_info[ seed ]
            
            seed_info[ 'status' ] = status
            seed_info[ 'last_modified_timestamp' ] = HydrusData.GetNow()
            seed_info[ 'note' ] = note
            
        
        HydrusGlobals.controller.pub( 'seed_cache_seed_updated', seed )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SEED_CACHE ] = SeedCache

class ThreadWatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_THREAD_WATCHER_IMPORT
    SERIALISABLE_VERSION = 1
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        result = ClientDefaults.GetDefaultImportFileOptions()
        
        automatic_archive = result[ 'auto_archive' ]
        exclude_deleted = result[ 'exclude_deleted_files' ]
        min_size = result[ 'min_size' ]
        min_resolution = result[ 'min_resolution' ]
        
        import_file_options = ClientData.ImportFileOptions( automatic_archive = automatic_archive, exclude_deleted = exclude_deleted, min_size = min_size, min_resolution = min_resolution )
        
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
        
        serialisable_url_cache = HydrusSerialisable.GetSerialisableTuple( self._urls_cache )
        serialisable_file_options = HydrusSerialisable.GetSerialisableTuple( self._import_file_options )
        serialisable_tag_options = HydrusSerialisable.GetSerialisableTuple( self._import_tag_options )
        
        return ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_file_options, serialisable_tag_options, self._times_to_check, self._check_period, self._last_time_checked, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._thread_url, serialisable_url_cache, self._urls_to_filenames, self._urls_to_md5_base64, serialisable_file_options, serialisable_tag_options, self._times_to_check, self._check_period, self._last_time_checked, self._paused ) = serialisable_info
        
        self._urls_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_url_cache )
        self._import_file_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._import_tag_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _RegenerateSeedCacheStatus( self ):
        
        self._seed_cache_status = self._urls_cache.GetStatus()
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_url = self._urls_cache.GetNextUnknownSeed()
        
        if file_url is None:
            
            return
            
        
        try:
            
            file_original_filename = self._urls_to_filenames[ file_url ]
            
            tags = [ 'filename:' + file_original_filename ]
            
            with self._lock:
                
                service_keys_to_tags = self._import_tag_options.GetServiceKeysToTags( tags )
                
            
            file_md5_base64 = self._urls_to_md5_base64[ file_url ]
            
            file_md5 = file_md5_base64.decode( 'base64' )
            
            ( status, hash ) = HydrusGlobals.controller.Read( 'md5_status', file_md5 )
            
            if status == CC.STATUS_REDUNDANT:
                
                if len( service_keys_to_tags ) > 0:
                    
                    service_keys_to_content_updates = ClientDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                    
                    HydrusGlobals.controller.Write( 'content_updates', service_keys_to_content_updates )
                    
                
                ( media_result, ) = HydrusGlobals.controller.Read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
                
            elif status == CC.STATUS_NEW:
                
                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                
                try:
                    
                    report_hooks = []
                    
                    with self._lock:
                        
                        if self._file_download_hook is not None:
                            
                            report_hooks.append( self._file_download_hook )
                            
                        
                    
                    HydrusGlobals.controller.DoHTTP( HC.GET, file_url, report_hooks = report_hooks, temp_path = temp_path )
                    
                    ( status, media_result ) = HydrusGlobals.controller.WriteSynchronous( 'import_file', temp_path, import_file_options = self._import_file_options, service_keys_to_tags = service_keys_to_tags, generate_media_result = True, url = file_url )
                    
                finally:
                    
                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                    
                
            
            self._urls_cache.UpdateSeedStatus( file_url, status )
            
            if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                
                HydrusGlobals.controller.pub( 'add_media_results', page_key, ( media_result, ) )
                
            
        except Exception as e:
            
            traceback.print_exc()
            
            status = CC.STATUS_FAILED
            
            note = HydrusData.ToString( e )
            
            self._urls_cache.UpdateSeedStatus( file_url, status, note = note )
            
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
    
    def _WorkOnThread( self, page_key ):
        
        with self._lock:
            
            p1 = self._check_now and HydrusData.TimeHasPassed( self._last_time_checked + self.MIN_CHECK_PERIOD )
            p2 = self._times_to_check > 0 and HydrusData.TimeHasPassed( self._last_time_checked + self._check_period )
            
        
        if p1 or p2:
            
            with self._lock:
                
                self._watcher_status = 'checking thread'
                
            
            HydrusGlobals.controller.pub( 'update_status', page_key )
            
            error_occurred = False
            
            try:
                
                ( json_url, file_base ) = ClientDownloading.GetImageboardThreadURLs( self._thread_url )
                
                raw_json = HydrusGlobals.controller.DoHTTP( HC.GET, json_url )
                
                json_dict = json.loads( raw_json )
                
                posts_list = json_dict[ 'posts' ]
                
                file_infos = []
                
                for post in posts_list:
                    
                    if 'md5' not in post:
                        
                        continue
                        
                    
                    file_url = file_base + HydrusData.ToString( post[ 'tim' ] ) + post[ 'ext' ]
                    file_md5_base64 = post[ 'md5' ]
                    file_original_filename = post[ 'filename' ] + post[ 'ext' ]
                    
                    file_infos.append( ( file_url, file_md5_base64, file_original_filename ) )
                    
                    if 'extra_files' in post:
                        
                        for extra_file in post[ 'extra_files' ]:
                            
                            if 'md5' not in extra_file:
                                
                                continue
                                
                            
                            file_url = file_base + HydrusData.ToString( extra_file[ 'tim' ] ) + extra_file[ 'ext' ]
                            file_md5_base64 = extra_file[ 'md5' ]
                            file_original_filename = extra_file[ 'filename' ] + extra_file[ 'ext' ]
                            
                            file_infos.append( ( file_url, file_md5_base64, file_original_filename ) )
                            
                        
                    
                
                num_new = 0
                
                for ( file_url, file_md5_base64, file_original_filename ) in file_infos:
                    
                    if not self._urls_cache.HasSeed( file_url ):
                        
                        num_new += 1
                        
                        self._urls_cache.AddSeed( file_url )
                        
                        self._urls_to_filenames[ file_url ] = file_original_filename
                        self._urls_to_md5_base64[ file_url ] = file_md5_base64
                        
                    
                
                watcher_status = 'thread checked OK - ' + HydrusData.ConvertIntToPrettyString( num_new ) + ' new files'
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                watcher_status = 'thread 404'
                
                with self._lock:
                    
                    for i in range( self._times_to_check ):
                        
                        HydrusGlobals.controller.pub( 'decrement_times_to_check', page_key )
                        
                    
                    self._times_to_check = 0
                    
                
            except Exception as e:
                
                error_occurred = True
                
                watcher_status = HydrusData.ToString( e )
                
            
            with self._lock:
                
                if self._check_now:
                    
                    self._check_now = False
                    
                else:
                    
                    self._times_to_check -= 1
                    
                    HydrusGlobals.controller.pub( 'decrement_times_to_check', page_key )
                    
                
                self._last_time_checked = HydrusData.GetNow()
                self._watcher_status = watcher_status
                self._RegenerateSeedCacheStatus()
                
            
            if error_occurred:
                
                HydrusGlobals.controller.pub( 'update_status', page_key )
                
                time.sleep( 5 )
                
            
        else:
            
            with self._lock:
                
                if self._check_now or self._times_to_check > 0:
                    
                    if self._check_now:
                        
                        delay = self.MIN_CHECK_PERIOD
                        
                    else:
                        
                        delay = self._check_period
                        
                    
                    self._watcher_status = 'checking again in ' + HydrusData.ToString( HydrusData.TimeUntil( self._last_time_checked + delay ) ) + ' seconds'
                    
                else:
                    
                    self._watcher_status = 'checking finished'
                    
                
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
    
    def _THREADWork( self, page_key ):
        
        with self._lock:
            
            self._RegenerateSeedCacheStatus()
            
        
        HydrusGlobals.controller.pub( 'update_status', page_key )
        
        while True:
            
            if HydrusGlobals.view_shutdown:
                
                return
                
            
            while self._paused:
                
                if HydrusGlobals.view_shutdown:
                    
                    return
                    
                
                time.sleep( 0.1 )
                
            
            try:
                
                if self._thread_url != '':
                    
                    self._WorkOnThread( page_key )
                    
                    self._WorkOnFiles( page_key )
                    
                
                time.sleep( 1 )
                
                HydrusGlobals.controller.WaitUntilPubSubsEmpty()
                
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
            
        
    
    def Pause( self ):
        
        with self._lock:
            
            self._paused = True
            
        
    
    def Resume( self ):
        
        with self._lock:
            
            self._paused = False
            
        
    
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
