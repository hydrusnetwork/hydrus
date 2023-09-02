import typing

from qtpy import QtPdf
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPDFHandling

from hydrus.client.gui import ClientGUIFunctions

def LoadPDF( path: str ):
    
    try:
        
        document = QtPdf.QPdfDocument()

        document.load(path)
        
    except:
        
        raise  HydrusExceptions.DamagedOrUnusualFileException( 'Could not load PDF file.' )
        
    status = document.status()
    
    if status is not QtPdf.QPdfDocument.Status.Ready:

        if status is QtPdf.QPdfDocument.Status.Error:

            error = document.error()

            if error is QtPdf.QPdfDocument.Error.IncorrectPassword:

                raise  HydrusExceptions.EncryptedFileException( f'PDF is password protected!' )
            
            elif error is QtPdf.QPdfDocument.Error.UnsupportedSecurityScheme:

                raise  HydrusExceptions.EncryptedFileException( f'PDF uses an unsupported security scheme' )
            
            else:

                raise  HydrusExceptions.DamagedOrUnusualFileException( f'PDF document error: {document.error()}!' )
        
        else:

            raise  HydrusExceptions.DamagedOrUnusualFileException( f'PDF document status: {status}!' )
        
    return document
    

def GenerateThumbnailBytesFromPDFPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
        
    document = LoadPDF( path )

    resolution = QC.QSize( target_resolution[0], target_resolution[1] )
    
    try:
        
        qt_image = document.render(0, resolution)

        # ClientGUIFunctions.ConvertQtImageToNumPy doesn't handle other formats well
        qt_image.convertToFormat(QG.QImage.Format_RGBA8888)

        
        numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )

        document.close()
            
        return HydrusImageHandling.GenerateThumbnailBytesNumPy( numpy_image )
        
    except:
        
        raise HydrusExceptions.DamagedOrUnusualFileException()
        
    
HydrusPDFHandling.GenerateThumbnailBytesFromPDFPath = GenerateThumbnailBytesFromPDFPath

PDF_ASSUMED_DPI = 300

def GetPDFResolution( path: str ):
    
    try:

        document = LoadPDF( path )
    
        pointSize = document.pagePointSize(0)

        # pointSize is in pts which are 1/72 of an inch.
        # this calculates the "resolution" assuming PDF_ASSUMED_DPI dpi
        width = pointSize.width() * (PDF_ASSUMED_DPI/72)
        height = pointSize.height() * (PDF_ASSUMED_DPI/72)
        
        document.close()

        return (width, height)
    
    except HydrusExceptions.EncryptedFileException:

        return (None, None)

    
HydrusPDFHandling.GetPDFResolution = GetPDFResolution
