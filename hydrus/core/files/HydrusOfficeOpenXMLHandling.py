from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core.files.HydrusArchiveHandling import GetZipAsPath
from hydrus.core.files.images import HydrusImageHandling

import xml.etree.ElementTree as ET

from PIL import Image as PILImage

DOCX_XPATH = ".//{*}Override[@PartName='/word/document.xml'][@ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml']"
XLSX_XPATH = ".//{*}Override[@PartName='/xl/workbook.xml'][@ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml']"
PPTX_XPATH = ".//{*}Override[@PartName='/ppt/presentation.xml'][@ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml']"

DOCX_XPATH_DEFAULT = ".//{*}Default[@Extension='xml'][@ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml']"
XLSX_XPATH_DEFAULT = ".//{*}Default[@Extension='xml'][@ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml']"
PPTX_XPATH_DEFAULT = ".//{*}Default[@Extension='xml'][@ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml']"

def MimeFromMicrosoftOpenXMLDocument(path: str):
    
    try:
        
        file = GetZipAsPath( path, '[Content_Types].xml' ).open( 'rb' )
        
        root = ET.parse( file )
        
        if root.find(DOCX_XPATH) is not None:
            
            return HC.APPLICATION_DOCX
            
        elif root.find(XLSX_XPATH) is not None:
            
            return HC.APPLICATION_XLSX
            
        elif root.find(PPTX_XPATH) is not None:
            
            return HC.APPLICATION_PPTX
        
        if root.find(DOCX_XPATH_DEFAULT) is not None:
            
            return HC.APPLICATION_DOCX
            
        elif root.find(XLSX_XPATH_DEFAULT) is not None:
            
            return HC.APPLICATION_XLSX
            
        elif root.find(PPTX_XPATH_DEFAULT) is not None:
            
            return HC.APPLICATION_PPTX
            
        else:
            
            return None
            
        
    except Exception as e:
        
        return None
        
    

def GenerateThumbnailNumPyFromOfficePath( path: str, target_resolution: tuple[ int, int ] ) -> bytes:
    
    try:
        
        zip_path_file_obj = GetZipAsPath( path, 'docProps/thumbnail.jpeg' ).open( 'rb' )
        
    except FileNotFoundError:
        
        raise HydrusExceptions.NoThumbnailFileException( 'No thumbnail.jpeg file!' )
        
    
    pil_image = HydrusImageHandling.GeneratePILImage( zip_path_file_obj )
    
    thumbnail_pil_image = pil_image.resize( target_resolution, PILImage.Resampling.LANCZOS )
    
    numpy_image = HydrusImageHandling.GenerateNumPyImageFromPILImage( thumbnail_pil_image )
    
    return numpy_image
    

PPTX_ASSUMED_DPI = 300

# https://startbigthinksmall.wordpress.com/2010/01/04/points-inches-and-emus-measuring-units-in-office-open-xml/
# PowerPoint uses English Metric Unit (EMU) for vector coordinates
# 1 inch = 914400 EMU

PPTX_PIXEL_PER_EMU = PPTX_ASSUMED_DPI / 914400

def PowerPointResolution( path: str ):
    
    file = GetZipAsPath( path, 'ppt/presentation.xml' ).open( 'rb' )
    
    root = ET.parse( file )
    
    sldSz = root.find('./p:sldSz', {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'})
    
    x_emu = int(sldSz.get('cx'))
    
    y_emu = int(sldSz.get('cy'))
    
    width = round(x_emu * PPTX_PIXEL_PER_EMU)
    
    height = round(y_emu * PPTX_PIXEL_PER_EMU)
    
    return ( width, height) 
    

def OfficeDocumentWordCount( path: str ):
    
    file = GetZipAsPath( path, 'docProps/app.xml' ).open( 'rb' )
    
    root = ET.parse( file )
    
    words = root.findtext('./ep:Words', namespaces = {'ep' : 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'})
    
    num_words = int(words)
    
    return num_words
    

def GetPPTXInfo( path: str ):
    
    try:
        
        ( width, height ) = PowerPointResolution( path )
        
    except Exception as e:
        
        ( width, height ) = ( None, None )
    
    try:
        
        num_words = OfficeDocumentWordCount( path )
        
    except Exception as e:
        
        num_words = None
        
    return ( num_words, ( width, height ) )
    

def GetDOCXInfo( path:str ):
    
    try:
        
        num_words = OfficeDocumentWordCount( path )
        
    except Exception as e:
        
        num_words = None
        
    
    return num_words
    
