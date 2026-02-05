from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.files import HydrusFileHandling
from hydrus.core.files import HydrusPSDHandling
from hydrus.core.files.images import HydrusBlurhash
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.files import ClientFiles
from hydrus.client.files.images import ClientImagePerceptualHashes
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy

class FileImportStatus( object ):
    
    def __init__( self, status, hash, mime = None, note = '' ):
        
        self.status = status
        self.hash = hash
        self.mime = mime
        self.note = note
        
    
    def __str__( self ):
        
        return 'File Import Status: {}'.format( self.ToString() )
        
    
    def AlreadyInDB( self ):
        
        return self.status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT
        
    
    def Duplicate( self ) -> "FileImportStatus":
        
        return FileImportStatus( self.status, self.hash, mime = self.mime, note = self.note )
        
    
    def ShouldImport( self, file_filtering_import_options: FileFilteringImportOptions.FileFilteringImportOptions ):
        
        if self.status == CC.STATUS_UNKNOWN:
            
            return True
            
        
        if self.status == CC.STATUS_DELETED:
            
            if not file_filtering_import_options.ExcludesDeleted():
                
                return True
                
            
        
        return False
        
    
    def ToString( self ) -> str:
        
        s = CC.status_string_lookup[ self.status ]
        
        if len( self.note ) > 0:
            
            s = '{}, {}'.format( s, self.note )
            
        
        return s
        
    
    @staticmethod
    def STATICGetUnknownStatus() -> "FileImportStatus":
        
        return FileImportStatus( CC.STATUS_UNKNOWN, None )
        
    
def CheckFileImportStatus( file_import_status: FileImportStatus ) -> FileImportStatus:
    
    if file_import_status.AlreadyInDB():
        
        try:
            
            hash = file_import_status.hash
            mime = file_import_status.mime
            
            if hash is None or mime is None:
                
                return file_import_status
                
            
            CG.client_controller.client_files_manager.GetFilePath( hash, mime = mime )
            
        except HydrusExceptions.FileMissingException:
            
            note = 'The client believed this file was already in the db, but it was truly missing! Import will go ahead, in an attempt to fix the situation.'
            
            return FileImportStatus( CC.STATUS_UNKNOWN, hash, mime = mime, note = note )
            
        
    
    return file_import_status
    
class FileImportJob( object ):
    
    def __init__( self, temp_path: str, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, human_file_description = None ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( f'File import job created:\nSource: {human_file_description}\nRaw import path: {temp_path}.' )
            
        
        if file_import_options.IsDefault():
            
            file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
        
        self._temp_path = temp_path
        self._file_import_options = file_import_options
        self._human_file_description = human_file_description
        
        self._pre_import_file_status = FileImportStatus.STATICGetUnknownStatus()
        self._post_import_file_status = FileImportStatus.STATICGetUnknownStatus()
        
        self._file_info = None
        self._thumbnail_bytes = None
        self._perceptual_hashes = None
        self._extra_hashes = None
        self._has_transparency = None
        self._has_exif = None
        self._has_human_readable_embedded_metadata = None
        self._has_icc_profile = None
        self._pixel_hash = None
        self._file_modified_timestamp_ms = None
        self._blurhash = None
        
    
    def CheckIsGoodToImport( self ):
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job testing if good to import for file import options' )
            
        
        ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = self._file_info
        
        file_filtering_import_options = self._file_import_options.GetFileFilteringImportOptions()
        
        file_filtering_import_options.CheckFileIsValid( size, mime, width, height )
        
    
    def DoWork( self, status_hook = None ) -> FileImportStatus:
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job starting work.' )
            
        
        self.GeneratePreImportHashAndStatus( status_hook = status_hook )
        
        if self._pre_import_file_status.ShouldImport( self._file_import_options.GetFileFilteringImportOptions() ):
            
            self.GenerateInfo( status_hook = status_hook )
            
            try:
                
                self.CheckIsGoodToImport()
                
                ok_to_go = True
                
            except HydrusExceptions.FileImportRulesException as e:
                
                ok_to_go = False
                
                not_ok_file_import_status = self._pre_import_file_status.Duplicate()
                
                not_ok_file_import_status.status = CC.STATUS_VETOED
                not_ok_file_import_status.note = str( e )
                
                self._post_import_file_status = not_ok_file_import_status
                
            
            if ok_to_go:
                
                hash = self._pre_import_file_status.hash
                mime = self._pre_import_file_status.mime
                
                if status_hook is not None:
                    
                    status_hook( 'copying file into file storage' )
                    
                
                CG.client_controller.client_files_manager.AddFile( hash, mime, self._temp_path, thumbnail_bytes = self._thumbnail_bytes )
                
                if status_hook is not None:
                    
                    status_hook( 'importing to database' )
                    
                
                self._file_import_options.GetLocationImportOptions().CheckReadyToImport()
                
                self._post_import_file_status = CG.client_controller.WriteSynchronous( 'import_file', self )
                
            
        else:
            
            self._post_import_file_status = self._pre_import_file_status.Duplicate()
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job is done, now publishing content updates' )
            
        
        self.WriteContentUpdates()
        
        return self._post_import_file_status
        
    
    def GeneratePreImportHashAndStatus( self, status_hook = None ):
        
        if status_hook is not None:
            
            status_hook( 'calculating hash' )
            
        
        hash = HydrusFileHandling.GetHashFromPath( self._temp_path )
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job hash: {}'.format( hash.hex() ) )
            
        
        if status_hook is not None:
            
            status_hook( 'checking for file status' )
            
        
        self._pre_import_file_status = CG.client_controller.Read( 'hash_status', 'sha256', hash, prefix = 'file recognised' )
        
        if self._pre_import_file_status.hash is None:
            
            self._pre_import_file_status.hash = hash
            
        
        self._pre_import_file_status = CheckFileImportStatus( self._pre_import_file_status )
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job pre-import status: {}'.format( self._pre_import_file_status.ToString() ) )
            
        
    
    def GenerateInfo( self, status_hook = None ):
        
        if self._pre_import_file_status.mime is None:
            
            if status_hook is not None:
                
                status_hook( 'generating filetype' )
                
            
            mime = HydrusFileHandling.GetMime( self._temp_path )
            
            self._pre_import_file_status.mime = mime
            
        else:
            
            mime = self._pre_import_file_status.mime
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job mime: {}'.format( HC.mime_string_lookup[ mime ] ) )
            
        
        new_options = CG.client_controller.new_options
        
        file_filtering_import_options = self._file_import_options.GetFileFilteringImportOptions()
        
        if mime in HC.DECOMPRESSION_BOMB_IMAGES and not file_filtering_import_options.AllowsDecompressionBombs():
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job testing for decompression bomb' )
                
            
            if HydrusImageHandling.IsDecompressionBomb( self._temp_path ):
                
                if HG.file_import_report_mode:
                    
                    HydrusData.ShowText( 'File import job: it was a decompression bomb' )
                    
                
                raise HydrusExceptions.DecompressionBombException( 'Image seems to be a Decompression Bomb!' )
                
            
        
        if status_hook is not None:
            
            status_hook( 'generating file metadata' )
            
        
        self._file_info = HydrusFileHandling.GetFileInfo( self._temp_path, mime = mime )
        
        ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = self._file_info
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job file info: {}'.format( self._file_info ) )
            
        
        if mime in HC.MIMES_WITH_THUMBNAILS:
            
            if status_hook is not None:
                
                status_hook( 'generating thumbnail' )
                
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generating thumbnail' )
                
            
            bounding_dimensions = CG.client_controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = new_options.GetInteger( 'thumbnail_scale_type' )
            thumbnail_dpr_percent = new_options.GetInteger( 'thumbnail_dpr_percent' )
            
            target_resolution = HydrusImageHandling.GetThumbnailResolution( ( width, height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
            
            percentage_in = new_options.GetInteger( 'video_thumbnail_percentage_in' )
            
            extra_description = f'File with hash "{self.GetHash().hex()}".'
            
            thumbnail_numpy = HydrusFileHandling.GenerateThumbnailNumPy( self._temp_path, target_resolution, mime, duration_ms, num_frames, percentage_in = percentage_in, extra_description = extra_description )
            
            # this guy handles almost all his own exceptions now, so no need for clever catching. if it fails, we are prob talking an I/O failure, which is not a 'thumbnail failed' error
            self._thumbnail_bytes = HydrusImageHandling.GenerateThumbnailBytesFromNumPy( thumbnail_numpy )
            
            try:
                
                self._blurhash = HydrusBlurhash.GetBlurhashFromNumPy( thumbnail_numpy )
                
            except Exception as e:
                
                pass
                
            
        
        if mime in HC.FILES_THAT_HAVE_PERCEPTUAL_HASH:
            
            if status_hook is not None:
                
                status_hook( 'generating similar files metadata' )
                
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generating perceptual_hashes' )
                
            
            self._perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashes( self._temp_path, mime )
            
            if HG.file_import_report_mode:
                
                HydrusData.ShowText( 'File import job generated {} perceptual_hashes: {}'.format( len( self._perceptual_hashes ), [ perceptual_hash.hex() for perceptual_hash in self._perceptual_hashes ] ) )
                
            
        
        if HG.file_import_report_mode:
            
            HydrusData.ShowText( 'File import job generating other hashes' )
            
        
        if status_hook is not None:
            
            status_hook( 'generating additional hashes' )
            
        
        self._extra_hashes = HydrusFileHandling.GetExtraHashesFromPath( self._temp_path )
        
        #
        
        self._has_transparency = ClientFiles.HasTransparency( self._temp_path, mime, duration_ms = duration_ms, num_frames = num_frames, resolution = ( width, height ) )
        
        has_exif = False
        
        raw_pil_image = None
        
        if mime in HC.FILES_THAT_CAN_HAVE_EXIF:
            
            try:
                
                if raw_pil_image is None:
                    
                    raw_pil_image = HydrusImageOpening.RawOpenPILImage( self._temp_path, human_file_description = self._human_file_description )
                    
                
                has_exif = HydrusImageMetadata.HasEXIF( raw_pil_image )
                
            except Exception as e:
                
                pass
                
            
        
        self._has_exif = has_exif
        
        self._has_human_readable_embedded_metadata = ClientFiles.HasHumanReadableEmbeddedMetadata( self._temp_path, mime )
        
        has_icc_profile = False
        
        if mime in HC.FILES_THAT_CAN_HAVE_ICC_PROFILE:
            
            try:
                
                if mime == HC.APPLICATION_PSD:
                    
                    has_icc_profile = HydrusPSDHandling.PSDHasICCProfile( self._temp_path )
                    
                else:
                    
                    if raw_pil_image is None:
                        
                        raw_pil_image = HydrusImageOpening.RawOpenPILImage( self._temp_path, human_file_description = self._human_file_description )
                        
                    
                    has_icc_profile = HydrusImageMetadata.HasICCProfile( raw_pil_image )
                    
                
            except Exception as e:
                
                pass
                
            
        
        self._has_icc_profile = has_icc_profile
        
        #
        
        if mime in HC.FILES_THAT_CAN_HAVE_PIXEL_HASH and duration_ms is None:
            
            try:
                
                self._pixel_hash = HydrusImageHandling.GetImagePixelHash( self._temp_path, mime )
                
            except Exception as e:
                
                pass
                
            
        
        self._file_modified_timestamp_ms = HydrusFileHandling.GetFileModifiedTimestampMS( self._temp_path )
        
    
    def GetExtraHashes( self ):
        
        return self._extra_hashes
        
    
    def GetFileImportOptions( self ):
        
        return self._file_import_options
        
    
    def GetFileInfo( self ):
        
        return self._file_info
        
    
    def GetFileModifiedTimestampMS( self ):
        
        return self._file_modified_timestamp_ms
        
    
    def GetHash( self ):
        
        return self._pre_import_file_status.hash
        
    
    def GetMime( self ):
        
        return self._pre_import_file_status.mime
        
    
    def GetPerceptualHashes( self ):
        
        return self._perceptual_hashes
        
    
    def GetPixelHash( self ):
        
        return self._pixel_hash
        
    
    def HasEXIF( self ) -> bool:
        
        return self._has_exif
        
    
    def HasHumanReadableEmbeddedMetadata( self ) -> bool:
        
        return self._has_human_readable_embedded_metadata
        
    
    def HasICCProfile( self ) -> bool:
        
        return self._has_icc_profile
        
    
    def HasTransparency( self ) -> bool:
        
        return self._has_transparency
        
    
    def GetBlurhash( self ) -> str:
        
        return self._blurhash
        
    
    def WriteContentUpdates( self ):
        
        if self._post_import_file_status.AlreadyInDB():
            
            media_result = CG.client_controller.Read( 'media_result', self._post_import_file_status.hash )
            
            content_update_package = self._file_import_options.GetLocationImportOptions().GetAlreadyInDBPostImportContentUpdatePackage( media_result )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    
