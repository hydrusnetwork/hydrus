from hydrus.core import HydrusArchiveHandling
from hydrus.core import HydrusExceptions
from hydrus.core.images import HydrusImageHandling
from hydrus.core import HydrusTemp

import re 
import io

from PIL import Image as PILImage
import xml.etree.ElementTree as ET

KRITA_FILE_THUMB = "preview.png"
KRITA_FILE_MERGED = "mergedimage.png"

def ExtractZippedImageToPath( path_to_zip, temp_path_file ):
    
    try:
        
        HydrusArchiveHandling.ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_MERGED, temp_path_file )
        
        return
        
    except KeyError:
        
        pass
        
    
    try:
        
        HydrusArchiveHandling.ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_THUMB, temp_path_file )
        
    except KeyError:
        
        raise HydrusExceptions.NoThumbnailFileException( f'This krita file had no {KRITA_FILE_MERGED} or {KRITA_FILE_THUMB}!' )
        

def MergedPILImageFromKRA(path):

    try:

        file_obj = HydrusArchiveHandling.GetZipAsPath( path, KRITA_FILE_MERGED ).open('rb')

        return HydrusImageHandling.GeneratePILImage( file_obj )
        
    except FileNotFoundError:
        
        raise HydrusExceptions.UnsupportedFileException( f'Could not read {KRITA_FILE_MERGED} from this Krita file' )
    

# TODO: animation and frame stuff which is also in the maindoc.xml
def GetKraProperties( path ):
    
    DOCUMENT_INFO_FILE = "maindoc.xml"

    try:

        data_file = HydrusArchiveHandling.GetZipAsPath( path, DOCUMENT_INFO_FILE ).open('rb')

        root = ET.parse(data_file)

        image_tag = root.find('{http://www.calligra.org/DTD/krita}IMAGE')

        width = int(image_tag.attrib['width'])
        
        height = int(image_tag.attrib['height'])
        
        return ( width, height )

    except:
        
        raise HydrusExceptions.NoResolutionFileException( f'This krita file had no {DOCUMENT_INFO_FILE} or it contains no resolution!' )
