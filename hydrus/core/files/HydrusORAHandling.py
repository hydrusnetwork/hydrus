from hydrus.core import HydrusExceptions
from hydrus.core.files import HydrusArchiveHandling
from hydrus.core.files.images import HydrusImageHandling

import numpy

from PIL import Image as PILImage
import xml.etree.ElementTree as ET

ORA_FILE_THUMB = "Thumbnails/thumbnail.png"
ORA_FILE_MERGED = "mergedimage.png"

def MergedPILImageFromOra( path: str ):
    
    print( "Merging PIL image from ora" )
    
    try:
        
        zip_path_file_obj = HydrusArchiveHandling.GetZipAsPath( path, ORA_FILE_MERGED ).open( 'rb' )
        
        return HydrusImageHandling.GeneratePILImage( zip_path_file_obj )
        
    except FileNotFoundError:
        
        raise HydrusExceptions.NoRenderFileException( f'Could not read {ORA_FILE_MERGED} from this ora file' )
        
    

def ThumbnailPILImageFromOra( path: str ):
    
    try:
        
        zip_path_file_obj = HydrusArchiveHandling.GetZipAsPath( path, ORA_FILE_THUMB ).open( 'rb' )
        
        return HydrusImageHandling.GeneratePILImage( zip_path_file_obj )
        
    except FileNotFoundError:
        
        raise HydrusExceptions.NoThumbnailFileException( f'Could not read {ORA_FILE_THUMB} from this ora file' )
        
    

def GenerateThumbnailNumPyFromOraPath( path: str, target_resolution: tuple[ int, int ] ) -> numpy.ndarray:
    
    try:
        
        pil_image = MergedPILImageFromOra( path )
        
    except Exception as e:
        
        pil_image = ThumbnailPILImageFromOra( path )
        
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.Resampling.LANCZOS )
    
    numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( thumbnail_pil_image )
    
    return numpy_image
    

def GetOraProperties( path: str ):
    
    DOCUMENT_INFO_FILE = "stack.xml"
    
    try:
        
        data_file = HydrusArchiveHandling.GetZipAsPath( path, DOCUMENT_INFO_FILE ).open( 'rb' )
        
        tree = ET.parse( data_file )
        
        root = tree.getroot()
        
        width = int( root.get( 'w' ) )
        
        height = int( root.get( 'h' ) )
        
        print( width, height )
        
        return ( width, height )
        
    except Exception as e:
        
        raise HydrusExceptions.NoResolutionFileException( f'This ora file had no {DOCUMENT_INFO_FILE} or it contains no resolution!' )
        
    
