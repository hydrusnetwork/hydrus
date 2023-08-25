from hydrus.core import HydrusArchiveHandling
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTemp

import re 

KRITA_FILE_THUMB = "preview.png"
KRITA_FILE_MERGED = "mergedimage.png"
KRITA_MIMETYPE = 'mimetype'

def ExtractZippedImageToPath( path_to_zip, temp_path_file ):
    
    try:
        
        HydrusArchiveHandling.ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_MERGED, temp_path_file )
        
        return
        
    except KeyError:
        
        pass
        
    
    try:
        
        HydrusArchiveHandling.ExtractSingleFileFromZip( path_to_zip, KRITA_FILE_THUMB, temp_path_file )
        
    except KeyError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( f'This krita file had no {KRITA_FILE_MERGED} or {KRITA_FILE_THUMB}, so no PNG thumb could be extracted!' )
        
    

# TODO: animation and frame stuff which is also in the maindoc.xml
def GetKraProperties( path ):
    
    DOCUMENT_INFO_FILE = "maindoc.xml"
    
    # TODO: probably actually parse the xml instead of using regex
    FIND_KEY_VALUE = re.compile(r"([a-z\-_]+)\s*=\s*['\"]([^'\"]+)", re.IGNORECASE)
    
    width = None 
    height = None
    
    try:
        
        with HydrusArchiveHandling.GetZipAsPath( path, DOCUMENT_INFO_FILE ).open('r') as reader:
            
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

    
    return width, height
    

def ZipLooksLikeAKrita( path ):
    
    try:
        
        mimetype_data = HydrusArchiveHandling.ReadSingleFileFromZip( path, KRITA_MIMETYPE )
        
        return b'application/x-krita' in mimetype_data
        
    except KeyError:
        
        return False
        
    
