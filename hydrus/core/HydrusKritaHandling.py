
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTemp

import zipfile
import re 

KRITA_FILE_THUMB = "preview.png"
KRITA_FILE_MERGED = "mergedimage.png"


def ExtractSingleFileFromZip( path_to_zip, filename_to_extract, extract_into_file_path ):

    with zipfile.ZipFile( path_to_zip ) as zip_handle:

        with zip_handle.open( filename_to_extract ) as reader:

            with open( extract_into_file_path, "wb" ) as writer:

                writer.write( reader.read() )


def ExtractZippedImageToPath( path_to_zip, temp_path_file ):

    try:
        
        ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_MERGED, temp_path_file )

        return
        
    except KeyError:

        pass
            
        
    try:
        
        ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_THUMB, temp_path_file )            
        
    except KeyError:

        raise HydrusExceptions.DamagedOrUnusualFileException( f'This krita file had no {KRITA_FILE_MERGED} or {KRITA_FILE_THUMB}, so no PNG thumb could be extracted!' )


# TODO: animation and frame stuff which is also in the maindoc.xml
def GetKraProperties( path ):

    ( os_file_handle, maindoc_xml ) = HydrusTemp.GetTempPath()

    DOCUMENT_INFO_FILE = "maindoc.xml"

    # TODO: probably actually parse the xml instead of using regex
    FIND_KEY_VALUE = re.compile(r"([a-z\-\_]+)\s*=\s*['\"]([^'\"]+)", re.IGNORECASE)

    width = None 
    height = None

    try:

        ExtractSingleFileFromZip( path, DOCUMENT_INFO_FILE, maindoc_xml ) 

        with open(maindoc_xml, "r") as reader:

            for line in reader:

                for match in FIND_KEY_VALUE.findall( line ):

                    key, value = match 

                    if key == "width" and value.isdigit():

                        width = int(value)

                    if key == "height" and value.isdigit():

                        height = int(value)

                    if width is not None and height is not None:

                        break

    except KeyError:

        raise HydrusExceptions.DamagedOrUnusualFileException( f'This krita file had no {DOCUMENT_INFO_FILE}, so no information could be extracted!' )

    finally:

        HydrusTemp.CleanUpTempPath( os_file_handle, maindoc_xml ) 

    return width, height



