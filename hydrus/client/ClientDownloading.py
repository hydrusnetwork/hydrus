import random

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import PrefetchImportOptions

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
        
        super().__init__()
        
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

class QuickDownloadManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller ):
        
        super().__init__( controller, 5 )
        
        self._pending_hashes = set()
        
    
    def DownloadFiles( self, hashes ):
        
        with self._lock:
            
            self._pending_hashes.update( hashes )
            
        
        self.Wake()
        
    
    def GetName( self ) -> str:
        
        return 'quick downloader'
        
    
    def _DoMainLoop( self ):
        
        hashes_still_to_download_in_this_run = set()
        total_hashes_in_this_run = 0
        total_successful_hashes_in_this_run = 0
        
        while True:
            
            with self._lock:
                
                self._CheckShutdown()
                
                if len( self._pending_hashes ) > 0:
                    
                    if total_hashes_in_this_run == 0:
                        
                        job_status = ClientThreading.JobStatus( cancellable = True )
                        
                        job_status.SetStatusTitle( 'downloading' )
                        
                        job_status.SetStatusText( 'initialising downloader' )
                        
                        job_status_pub_job = self._controller.CallLater( 2.0, self._controller.pub, 'message', job_status )
                        
                    
                    num_before = len( hashes_still_to_download_in_this_run )
                    
                    hashes_still_to_download_in_this_run.update( self._pending_hashes )
                    
                    num_after = len( hashes_still_to_download_in_this_run )
                    
                    total_hashes_in_this_run += num_after - num_before
                    
                    self._pending_hashes = set()
                    
                
            
            if len( hashes_still_to_download_in_this_run ) == 0:
                
                total_hashes_in_this_run = 0
                total_successful_hashes_in_this_run = 0
                
                self._wake_from_idle_sleep_event.wait( 5 )
                
                self._wake_from_work_sleep_event.clear()
                self._wake_from_idle_sleep_event.clear()
                
                continue
                
            
            if job_status.IsCancelled():
                
                hashes_still_to_download_in_this_run = set()
                
                continue
                
            
            hash = random.sample( list( hashes_still_to_download_in_this_run ), 1 )[0]
            
            hashes_still_to_download_in_this_run.discard( hash )
            
            total_done = total_hashes_in_this_run - len( hashes_still_to_download_in_this_run )
            
            job_status.SetStatusText( 'downloading files: {}'.format( HydrusNumbers.ValueRangeToPrettyString( total_done, total_hashes_in_this_run ) ) )
            job_status.SetGauge( total_done, total_hashes_in_this_run )
            
            try:
                
                errors_occured = []
                file_successful = False
                
                media_result = self._controller.Read( 'media_result', hash )
                
                service_keys = list( media_result.GetLocationsManager().GetCurrent() )
                
                random.shuffle( service_keys )
                
                if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in service_keys:
                    
                    total_successful_hashes_in_this_run += 1
                    
                    continue
                    
                
                for service_key in service_keys:
                    
                    try:
                        
                        service = self._controller.services_manager.GetService( service_key )
                        
                    except Exception as e:
                        
                        continue
                        
                    
                    try:
                        
                        if service.GetServiceType() == HC.FILE_REPOSITORY:
                            
                            file_repository = service
                            
                            if file_repository.IsFunctional():
                                
                                ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                                
                                try:
                                    
                                    file_repository.Request( HC.GET, 'file', { 'hash' : hash }, temp_path = temp_path )
                                    
                                    prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
                                    
                                    prefetch_import_options.SetPreImportHashCheckType( PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE )
                                    prefetch_import_options.SetPreImportURLCheckType( PrefetchImportOptions.DO_CHECK )
                                    prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( True )
                                    
                                    file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
                                    
                                    file_filtering_import_options.SetAllowsDecompressionBombs( True )
                                    file_filtering_import_options.SetExcludesDeleted( False ) # important
                                    
                                    file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
                                    
                                    file_import_options.SetPrefetchImportOptions( prefetch_import_options )
                                    file_import_options.SetFileFilteringImportOptions( file_filtering_import_options )
                                    
                                    file_import_job = ClientImportFiles.FileImportJob( temp_path, file_import_options, human_file_description = f'Downloaded File - {hash.hex()}' )
                                    
                                    file_import_job.DoWork()
                                    
                                    file_successful = True
                                    
                                    break
                                    
                                finally:
                                    
                                    HydrusTemp.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                            
                        
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
                    
                    job_status.DeleteStatusText()
                    job_status.DeleteGauge()
                    
                    if total_successful_hashes_in_this_run > 0:
                        
                        job_status.SetStatusText( HydrusNumbers.ToHumanInt( total_successful_hashes_in_this_run ) + ' files downloaded' )
                        
                    
                    job_status_pub_job.Cancel()
                    
                    job_status.FinishAndDismiss( 1 )
                    
                
            
        
    
