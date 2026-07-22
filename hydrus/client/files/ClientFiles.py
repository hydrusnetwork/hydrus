import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files.images import HydrusImageColours
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

# noinspection PyUnresolvedReferences
from hydrus.client import ClientSVGHandling # important to keep this in, even if not being used, since there's initialisation stuff in here
# noinspection PyUnresolvedReferences
from hydrus.client import ClientPDFHandling # important to keep this in, even if not being used, since there's initialisation stuff in here

from hydrus.client import ClientVideoHandling

class PathParsingJob( object ):
    
    def __init__( self, path: str, search_subdirectories: bool = True, parent_dirs = None ):
        
        if parent_dirs is None:
            
            parent_dirs = set()
            
        
        self.path = path
        self.search_subdirectories = search_subdirectories
        self._parent_dirs = set( parent_dirs )
        
    
    def GetFilePathsAndSubPathParsingJobs( self ) -> tuple[ list[ str ], list[ "PathParsingJob" ] ]:
        
        file_paths = []
        sub_path_parsing_jobs = []
        
        if self.IsDir():
            
            with os.scandir( self.path ) as scan:
                
                for entry in scan:
                    
                    if entry.is_dir():
                        
                        if self.search_subdirectories and os.path.normpath( entry.path ) not in self._parent_dirs:
                            
                            sub_parent_dirs = set( self._parent_dirs )
                            sub_parent_dirs.add( os.path.normpath( self.path ) )
                            
                            sub_path_parsing_jobs.append( PathParsingJob( entry.path, search_subdirectories = self.search_subdirectories, parent_dirs = sub_parent_dirs ) )
                            
                        
                    elif entry.is_file():
                        
                        file_paths.append( entry.path )
                        
                    
                
            
        else:
            
            file_paths.append( self.path )
            
        
        return ( file_paths, sub_path_parsing_jobs )
        
    
    def IsDir( self ):
        
        return os.path.isdir( self.path )
        
    

def has_sidecar_ext( p ):
    
    return True in ( p.endswith( ext ) for ext in [ '.txt', '.json', '.xml' ] )
    

def get_comparable_sidecar_prefix( p ):
    
    ( path_dir, path_basename ) = os.path.split( p )
    
    if '.' in path_basename:
        
        path_basename_with_no_ext_guaranteed = path_basename.split( '.', 1 )[0]
        
    else:
        
        path_basename_with_no_ext_guaranteed = path_basename
        
    
    return os.path.join( path_dir, path_basename_with_no_ext_guaranteed )
    

def GetAllFilePaths( path: str, search_subdirectories: bool, clear_out_sidecars = True, comparable_sidecar_prefixes = None ):
    
    if comparable_sidecar_prefixes is None:
        
        comparable_sidecar_prefixes = set()
        
    
    file_paths = []
    sidecar_paths = []
    
    jobs_to_process = [ PathParsingJob( path, search_subdirectories ) ]
    
    while len( jobs_to_process ) > 0:
        
        next_jobs_to_process = []
        
        for path_parsing_job in jobs_to_process:
            
            if HG.started_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
            ( sub_file_paths, sub_path_parsing_jobs ) = path_parsing_job.GetFilePathsAndSubPathParsingJobs()
            
            file_paths.extend( sub_file_paths )
            
            next_jobs_to_process.extend( sub_path_parsing_jobs )
            
        
        jobs_to_process = next_jobs_to_process
        
    
    HydrusText.HumanTextSort( file_paths )
    
    PopulateComparableSidecarPrefixes( file_paths, comparable_sidecar_prefixes )
    
    if clear_out_sidecars:
        
        ( file_paths, sidecar_paths ) = DifferentiateSidecarPaths( file_paths, comparable_sidecar_prefixes )
        
    
    return ( file_paths, sidecar_paths )
    

def DifferentiateSidecarPaths( file_paths, comparable_sidecar_prefixes ):
    
    undifferentiated_file_paths = file_paths
    
    file_paths = []
    sidecar_paths = []
    
    for path in undifferentiated_file_paths:
        
        if LooksLikeSidecarPath( path, comparable_sidecar_prefixes ):
            
            sidecar_paths.append( path )
            
        else:
            
            file_paths.append( path )
            
        
    
    return ( file_paths, sidecar_paths )
    

def LooksLikeSidecarPath( file_path, comparable_sidecar_prefixes ):
    
    return has_sidecar_ext( file_path ) and get_comparable_sidecar_prefix( file_path ) in comparable_sidecar_prefixes
    

def PopulateComparableSidecarPrefixes( file_paths, comparable_sidecar_prefixes ):
    
    for file_path in file_paths:
        
        if not has_sidecar_ext( file_path ):
            
            comparable_sidecar_prefixes.add( get_comparable_sidecar_prefix( file_path ) )
            
        
    

def HasHumanReadableEmbeddedMetadata( path, mime, human_file_description = None, possible_raw_pil_image = None ):
    
    if mime not in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
        
        return False
        
    
    if mime == HC.APPLICATION_PDF:
        
        has_human_readable_embedded_metadata = ClientPDFHandling.HasHumanReadableEmbeddedMetadata( path )
        
    else:
        
        try:
            
            if possible_raw_pil_image is None:
                
                pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
                
            else:
                
                pil_image = possible_raw_pil_image
                
            
            try:
                
                has_human_readable_embedded_metadata = HydrusImageMetadata.HasHumanReadableEmbeddedMetadata( pil_image )
                
            finally:
                
                pil_image.close()
                
            
        except Exception as e:
            
            return False
            
        
    
    return has_human_readable_embedded_metadata
    

def HasTransparency( path, mime, duration_ms = None, num_frames = None, resolution = None ):
    
    if mime not in HC.MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY:
        
        return False
        
    
    try:
        
        if mime in HC.IMAGES:
            
            numpy_image = HydrusImageHandling.GenerateNumPyImage( path, mime )
            
            return HydrusImageColours.NumPyImageHasUsefulAlphaChannel( numpy_image )
            
        elif mime in HC.ANIMATIONS:
            
            if num_frames is None or resolution is None:
                
                return False # something crazy going on, so let's bail out
                
            
            if mime in ( HC.ANIMATION_GIF, HC.ANIMATION_WEBP ):
                
                renderer = ClientVideoHandling.AnimationRendererPIL( path, num_frames, resolution )
                
            else:
                
                renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration_ms, num_frames, resolution )
                
            
            try:
                
                we_checked_for_just_alpha_channel = False
                
                for i in range( num_frames ):
                    
                    numpy_image = renderer.read_frame()
                    
                    if not we_checked_for_just_alpha_channel:
                        
                        if not HydrusImageColours.NumPyImageHasAlphaChannel( numpy_image ):
                            
                            return False
                            
                        
                        we_checked_for_just_alpha_channel = True
                        
                    
                    if HydrusImageColours.NumPyImageHasUsefulAlphaChannel( numpy_image ):
                        
                        return True
                        
                    
                
            finally:
                
                renderer.close()
                
            
        
    except HydrusExceptions.DamagedOrUnusualFileException as e:
        
        HydrusData.Print( 'Problem determining transparency for "{}":'.format( path ) )
        HydrusData.PrintException( e )
        
        return False
        
    
    return False
    
