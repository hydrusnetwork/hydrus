import re
import traceback
import typing

pdf_failed_reason = 'QtPdf seems ok!'

try:
    
    from qtpy import QtPdf
    
    PDF_OK = True
    
except Exception as e:
    
    pdf_failed_reason = traceback.format_exc()
    
    PDF_OK = False
    

from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core.files import HydrusPDFHandling
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client.gui import ClientGUIFunctions

def LoadPDF( path: str ):
    
    if not PDF_OK:
        
        raise HydrusExceptions.LimitedSupportFileException( 'Sorry, no QtPDF support!' )
        
    
    try:
        
        # it wants an Object in PyQt6, but giving it None is better since we are outside the Qt thread here
        document = QtPdf.QPdfDocument( None )
        
        document.load( path )
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not load PDF file.' )
        
    
    status = document.status()
    
    if status is not QtPdf.QPdfDocument.Status.Ready:
        
        if status is QtPdf.QPdfDocument.Status.Error:
            
            error = document.error()
            
            if error is QtPdf.QPdfDocument.Error.IncorrectPassword:
                
                raise HydrusExceptions.EncryptedFileException( 'PDF is password protected!' )
                
            elif error is QtPdf.QPdfDocument.Error.UnsupportedSecurityScheme:
                
                raise HydrusExceptions.EncryptedFileException( 'PDF uses an unsupported security scheme' )
                
            else:
                
                raise HydrusExceptions.DamagedOrUnusualFileException( f'PDF document error: {document.error()}!' )
                
        else:
            
            raise HydrusExceptions.DamagedOrUnusualFileException( f'PDF document status: {status}!' )
            
        
    
    return document
    

def GenerateThumbnailNumPyFromPDFPath( path: str, target_resolution: typing.Tuple[int, int] ) -> bytes:
    
    try:
        
        document = LoadPDF( path )
        
        ( target_width, target_height ) = target_resolution
        
        resolution = QC.QSize( target_width, target_height )
        
        qt_image = document.render(0, resolution)
        
        # ClientGUIFunctions.ConvertQtImageToNumPy doesn't handle other formats well
        qt_image.convertToFormat( QG.QImage.Format_RGBA8888 )
        
        numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )
        
        document.close()
        
        thumbnail_numpy_image = numpy_image
        
        return thumbnail_numpy_image
        
    except Exception as e:
        
        message = f'PDF at {path} failed to make a thumbnail: {e}'
        
        HydrusData.Print( message )
        
        raise HydrusExceptions.NoThumbnailFileException()
        
    

HydrusPDFHandling.GenerateThumbnailNumPyFromPDFPath = GenerateThumbnailNumPyFromPDFPath

PDF_ASSUMED_DPI = 300

def GetHumanReadableEmbeddedMetadata( path ) -> str:
    
    try:
        
        document = LoadPDF( path )
        
    except:
        
        raise HydrusExceptions.LimitedSupportFileException()
        
    
    result_components = []
    
    jobs = [
        ( 'Title', QtPdf.QPdfDocument.MetaDataField.Title ),
        ( 'Author', QtPdf.QPdfDocument.MetaDataField.Author ),
        ( 'Subject', QtPdf.QPdfDocument.MetaDataField.Subject ),
        ( 'Keywords', QtPdf.QPdfDocument.MetaDataField.Keywords )
    ]
    
    for ( prefix, key ) in jobs:
        
        text = document.metaData( key )
        
        if len( text ) > 0:
            
            result_components.append( f'{prefix}: {text}' )
            
        
    
    return '\n'.join( result_components )
    

def HasHumanReadableEmbeddedMetadata( path ) -> bool:
    
    try:
        
        text = GetHumanReadableEmbeddedMetadata( path )
        
    except HydrusExceptions.LimitedSupportFileException:
        
        return False
        
    
    return len( text ) > 0
    

def GetPDFInfo( path: str ):
    
    try:
        
        document = LoadPDF( path )
        
    except:
        
        raise HydrusExceptions.LimitedSupportFileException()
        
    
    try:
        
        ( width, height ) = GetPDFResolutionFromDocument( document )
        
    except:
        
        ( width, height ) = ( None, None )
        
    
    num_words = 0
    
    num_pages = document.pageCount()
    
    for i in range( num_pages ):
        
        q_selection_gubbins = document.getAllText( i )
        
        text = q_selection_gubbins.text()
        
        depunctuated_text = re.sub( r'[^\w\s]', ' ', text )
        
        despaced_text = re.sub( '\s\s+', ' ', depunctuated_text )
        
        if despaced_text not in ( '', ' ' ):
            
            num_words += despaced_text.count( ' ' ) + 1
            
        
    
    document.close()
    
    return ( num_words, ( width, height ) )
    

def GetPDFModifiedTimestampMS( path ):
    
    # TODO: do something with this
    # I thought about replacing the disk modified time, but it seemed like a minefield
    # I think instead we'll have support for more non-web-domain timestamps and add a 'pdf' domain or similar and add hooks for it in normal local file import and timestamp regen code
    
    try:
        
        document = LoadPDF( path )
        
    except:
        
        raise HydrusExceptions.LimitedSupportFileException()
        
    
    q_modified_date = document.metaData( QtPdf.QPdfDocument.MetaDataField.ModificationDate )
    
    modified_timestamp_ms = q_modified_date.toMSecsSinceEpoch()
    
    return modified_timestamp_ms
    

def GetPDFResolutionFromDocument( document ):
    
    pointSize = document.pagePointSize(0)
    
    # pointSize is in pts which are 1/72 of an inch.
    # this calculates the "resolution" assuming PDF_ASSUMED_DPI dpi
    width = pointSize.width() * ( PDF_ASSUMED_DPI / 72 )
    height = pointSize.height() * ( PDF_ASSUMED_DPI / 72 )
    
    return ( round( width ), round( height ) )
    

HydrusPDFHandling.GetPDFInfo = GetPDFInfo
