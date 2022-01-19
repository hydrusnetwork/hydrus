import random
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp
from hydrus.core import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptions

def ConvertGalleryIdentifierToGUGKeyAndName( gallery_identifier ):
    
    gug_name = ConvertGalleryIdentifierToGUGName( gallery_identifier )
    
    from hydrus.client import ClientDefaults
    
    gugs = ClientDefaults.GetDefaultGUGs()
    
    for gug in gugs:
        
        if gug.GetName() == gug_name:
            
            return gug.GetGUGKeyAndName()
            
        
    
    return ( HydrusData.GenerateKey(), gug_name )
    
def ConvertGalleryIdentifierToGUGName( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_DEVIANT_ART:
        
        return 'deviant art artist lookup'
        
    elif site_type == HC.SITE_TYPE_TUMBLR:
        
        return 'tumblr username lookup'
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        return 'newgrounds artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST:
        
        return 'hentai foundry artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS:
        
        return 'hentai foundry tag search'
        
    elif site_type == HC.SITE_TYPE_PIXIV_ARTIST_ID:
        
        return 'pixiv artist lookup'
        
    elif site_type == HC.SITE_TYPE_PIXIV_TAG:
        
        return 'pixiv tag search'
        
    elif site_type == HC.SITE_TYPE_BOORU:
        
        booru_name_converter = {}
        
        booru_name_converter[ 'gelbooru' ] = 'gelbooru tag search'
        booru_name_converter[ 'safebooru' ] = 'safebooru tag search'
        booru_name_converter[ 'e621' ] = 'e621 tag search'
        booru_name_converter[ 'rule34@paheal' ] = 'rule34.paheal tag search'
        booru_name_converter[ 'danbooru' ] = 'danbooru tag search'
        booru_name_converter[ 'rule34@booru.org' ] = 'rule34.xxx tag search'
        booru_name_converter[ 'furry@booru.org' ] = 'furry.booru.org tag search'
        booru_name_converter[ 'xbooru' ] = 'xbooru tag search'
        booru_name_converter[ 'konachan' ] = 'konachan tag search'
        booru_name_converter[ 'yande.re' ] = 'yande.re tag search'
        booru_name_converter[ 'tbib' ] = 'tbib tag search'
        booru_name_converter[ 'sankaku chan' ] = 'sankaku channel tag search'
        booru_name_converter[ 'sankaku idol' ] = 'sankaku idol tag search'
        booru_name_converter[ 'rule34hentai' ] = 'rule34hentai tag search'
        
        booru_name = gallery_identifier.GetAdditionalInfo()
        
        if booru_name in booru_name_converter:
            
            return booru_name_converter[ booru_name ]
            
        else:
            
            return booru_name
            
        
    else:
        
        return 'unknown site'
        
    
class GalleryIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER
    SERIALISABLE_NAME = 'Gallery Identifier'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, site_type = None, additional_info = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = site_type
        self._additional_info = additional_info
        
    
    def __eq__( self, other ):
        
        if isinstance( other, GalleryIdentifier ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._site_type, self._additional_info ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        text = 'Gallery Identifier: ' + HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            text += ': ' + str( self._additional_info )
            
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._site_type, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._additional_info ) = serialisable_info
        
    
    def GetAdditionalInfo( self ):
        
        return self._additional_info
        
    
    def GetSiteType( self ):
        
        return self._site_type
        
    
    def ToString( self ):
        
        text = HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU and self._additional_info is not None:
            
            booru_name = self._additional_info
            
            text = booru_name
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER ] = GalleryIdentifier

class QuickDownloadManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._pending_hashes = set()
        
        self._lock = threading.Lock()
        
        self._shutting_down = False
        
        self._new_files_event = threading.Event()
        
        self._controller.sub( self, 'Wake', 'wake_daemons' )
        
    
    def DownloadFiles( self, hashes ):
        
        with self._lock:
            
            self._pending_hashes.update( hashes )
            
            self._new_files_event.set()
            
        
    
    def MainLoop( self ):
        
        hashes_still_to_download_in_this_run = set()
        total_hashes_in_this_run = 0
        total_successful_hashes_in_this_run = 0
        
        while not ( HydrusThreading.IsThreadShuttingDown() or self._shutting_down or HG.started_shutdown ):
            
            with self._lock:
                
                if len( self._pending_hashes ) > 0:
                    
                    if total_hashes_in_this_run == 0:
                        
                        job_key = ClientThreading.JobKey( cancellable = True )
                        
                        job_key.SetStatusTitle( 'downloading' )
                        
                        job_key.SetVariable( 'popup_text_1', 'initialising downloader' )
                        
                        job_key_pub_job = self._controller.CallLater( 2.0, self._controller.pub, 'message', job_key )
                        
                    
                    num_before = len( hashes_still_to_download_in_this_run )
                    
                    hashes_still_to_download_in_this_run.update( self._pending_hashes )
                    
                    num_after = len( hashes_still_to_download_in_this_run )
                    
                    total_hashes_in_this_run += num_after - num_before
                    
                    self._pending_hashes = set()
                    
                
            
            if len( hashes_still_to_download_in_this_run ) == 0:
                
                total_hashes_in_this_run = 0
                total_successful_hashes_in_this_run = 0
                
                self._new_files_event.wait( 5 )
                
                self._new_files_event.clear()
                
                continue
                
            
            if job_key.IsCancelled():
                
                hashes_still_to_download_in_this_run = set()
                
                continue
                
            
            hash = random.sample( hashes_still_to_download_in_this_run, 1 )[0]
            
            hashes_still_to_download_in_this_run.discard( hash )
            
            total_done = total_hashes_in_this_run - len( hashes_still_to_download_in_this_run )
            
            job_key.SetVariable( 'popup_text_1', 'downloading files from remote services: {}'.format( HydrusData.ConvertValueRangeToPrettyString( total_done, total_hashes_in_this_run ) ) )
            job_key.SetVariable( 'popup_gauge_1', ( total_done, total_hashes_in_this_run ) )
            
            try:
                
                errors_occured = []
                file_successful = False
                
                media_result = self._controller.Read( 'media_result', hash )
                
                service_keys = list( media_result.GetLocationsManager().GetCurrent() )
                
                random.shuffle( service_keys )
                
                if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in service_keys:
                    
                    total_successful_hashes_in_this_run += 1
                    
                    continue
                    
                
                for service_key in service_keys:
                    
                    try:
                        
                        service = self._controller.services_manager.GetService( service_key )
                        
                    except:
                        
                        continue
                        
                    
                    try:
                        
                        if service.GetServiceType() == HC.FILE_REPOSITORY:
                            
                            file_repository = service
                            
                            if file_repository.IsFunctional():
                                
                                ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                                
                                try:
                                    
                                    file_repository.Request( HC.GET, 'file', { 'hash' : hash }, temp_path = temp_path )
                                    
                                    exclude_deleted = False # this is the important part here
                                    do_not_check_known_urls_before_importing = False
                                    do_not_check_hashes_before_importing = False
                                    allow_decompression_bombs = True
                                    min_size = None
                                    max_size = None
                                    max_gif_size = None
                                    min_resolution = None
                                    max_resolution = None
                                    automatic_archive = False
                                    associate_primary_urls = True
                                    associate_source_urls = True
                                    
                                    file_import_options = FileImportOptions.FileImportOptions()
                                    
                                    file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                                    file_import_options.SetPostImportOptions( automatic_archive, associate_primary_urls, associate_source_urls )
                                    
                                    file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options )
                                    
                                    file_import_job.DoWork()
                                    
                                    file_successful = True
                                    
                                    break
                                    
                                finally:
                                    
                                    HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                            
                        elif service.GetServiceType() == HC.IPFS:
                            
                            multihashes = HG.client_controller.Read( 'service_filenames', service_key, { hash } )
                            
                            if len( multihashes ) > 0:
                                
                                multihash = multihashes[0]
                                
                                service.ImportFile( multihash, silent = True )
                                
                                file_successful = True
                                
                                break
                                
                            
                        
                    except Exception as e:
                        
                        errors_occured.append( e )
                        
                    
                
                if file_successful:
                    
                    total_successful_hashes_in_this_run += 1
                    
                
                if len( errors_occured ) > 0:
                    
                    if not file_successful:
                        
                        raise errors_occured[0]
                        
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                hashes_still_to_download_in_this_run = 0
                
            finally:
                
                if len( hashes_still_to_download_in_this_run ) == 0:
                    
                    job_key.DeleteVariable( 'popup_text_1' )
                    job_key.DeleteVariable( 'popup_gauge_1' )
                    
                    if total_successful_hashes_in_this_run > 0:
                        
                        job_key.SetVariable( 'popup_text_1', HydrusData.ToHumanInt( total_successful_hashes_in_this_run ) + ' files downloaded' )
                        
                    
                    job_key_pub_job.Cancel()
                    
                    job_key.Finish()
                    
                    job_key.Delete( 1 )
                    
                
            
        
    
    def Shutdown( self ):
        
        self._shutting_down = True
        
        self._new_files_event.set()
        
    
    def Wake( self ):
        
        self._new_files_event.set()
        
