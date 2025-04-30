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

def GetAllFilePaths( raw_paths, do_human_sort = True, clear_out_sidecars = True ):
    
    file_paths = []
    
    paths_to_process = list( raw_paths )
    
    while len( paths_to_process ) > 0:
        
        next_paths_to_process = []
        
        for path in paths_to_process:
            
            if HG.started_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
            if os.path.isdir( path ):
                
                try:
                    
                    # on Windows, some network file paths return True on isdir(). maybe something to do with path length or number of subdirs
                    path_listdir = os.listdir( path )
                    
                except NotADirectoryError:
                    
                    file_paths.append( path )
                    
                    continue
                    
                
                subpaths = [ os.path.join( path, filename ) for filename in path_listdir ]
                
                next_paths_to_process.extend( subpaths )
                
            else:
                
                file_paths.append( path )
                
            
        
        paths_to_process = next_paths_to_process
        
    
    if do_human_sort:
        
        HydrusText.HumanTextSort( file_paths )
        
    
    num_files_with_sidecars = len( file_paths )
    
    if clear_out_sidecars:
        
        exts = [ '.txt', '.json', '.xml' ]
        
        def has_sidecar_ext( p ):
            
            if True in ( p.endswith( ext ) for ext in exts ):
                
                return True
                
            
            return False
            
        
        def get_base_prefix_component( p ):
            
            base_prefix = os.path.basename( p )
            
            if '.' in base_prefix:
                
                base_prefix = base_prefix.split( '.', 1 )[0]
                
            
            return base_prefix
            
        
        # let's get all the 'Image123' in our 'path/to/Image123.jpg' list
        all_non_ext_prefix_components = { get_base_prefix_component( file_path ) for file_path in file_paths if not has_sidecar_ext( file_path ) }
        
        def looks_like_a_sidecar( p ):
            
            # if we have Image123.txt, that's probably a sidecar!
            return has_sidecar_ext( p ) and get_base_prefix_component( p ) in all_non_ext_prefix_components
            
        
        file_paths = [ path for path in file_paths if not looks_like_a_sidecar( path ) ]
        
    
    num_sidecars = num_files_with_sidecars - len( file_paths )
    
    return ( file_paths, num_sidecars )
    

def HasHumanReadableEmbeddedMetadata( path, mime, human_file_description = None ):
    
    if mime not in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
        
        return False
        
    
    if mime == HC.APPLICATION_PDF:
        
        has_human_readable_embedded_metadata = ClientPDFHandling.HasHumanReadableEmbeddedMetadata( path )
        
    else:
        
        try:
            
            pil_image = HydrusImageOpening.RawOpenPILImage( path, human_file_description = human_file_description )
            
        except:
            
            return False
            
        
        has_human_readable_embedded_metadata = HydrusImageMetadata.HasHumanReadableEmbeddedMetadata( pil_image )
        
    
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
                
            
            we_checked_alpha_channel = False
            
            if mime in ( HC.ANIMATION_GIF, HC.ANIMATION_WEBP ):
                
                renderer = ClientVideoHandling.AnimationRendererPIL( path, num_frames, resolution )
                
            else:
                
                renderer = HydrusVideoHandling.VideoRendererFFMPEG( path, mime, duration_ms, num_frames, resolution )
                
            
            for i in range( num_frames ):
                
                numpy_image = renderer.read_frame()
                
                if not we_checked_alpha_channel:
                    
                    if not HydrusImageColours.NumPyImageHasAlphaChannel( numpy_image ):
                        
                        return False
                        
                    
                    we_checked_alpha_channel = True
                    
                
                if HydrusImageColours.NumPyImageHasUsefulAlphaChannel( numpy_image ):
                    
                    return True
                    
                
            
        
    except HydrusExceptions.DamagedOrUnusualFileException as e:
        
        HydrusData.Print( 'Problem determining transparency for "{}":'.format( path ) )
        HydrusData.PrintException( e )
        
        return False
        
    
    return False
    
