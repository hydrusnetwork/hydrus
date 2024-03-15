import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core.files.HydrusArchiveHandling import GetZipAsPath
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core import HydrusExceptions

import xml.etree.ElementTree as ET

from PIL import Image as PILImage


DOCX_XPATH = ".//{*}Override[@PartName='/word/document.xml'][@ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml']"
XLSX_XPATH = ".//{*}Override[@PartName='/xl/workbook.xml'][@ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml']"
PPTX_XPATH = ".//{*}Override[@PartName='/ppt/presentation.xml'][@ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml']"

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
            
        else:
            
                return None
        
    except:
        
        return None

        
    