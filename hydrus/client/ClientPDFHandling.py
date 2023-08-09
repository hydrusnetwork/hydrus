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
        
    
    if document.status() is not QtPdf.QPdfDocument.Status.Ready :
        
        raise  HydrusExceptions.DamagedOrUnusualFileException( 'PDF document was not ready!' )
        
    
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
        
        raise HydrusExceptions.UnsupportedFileException()
        
    

HydrusPDFHandling.GenerateThumbnailBytesFromPDFPath = GenerateThumbnailBytesFromPDFPath

def GetPDFResolution( path: str ):
    
    document = LoadPDF( path )
    
    pointSize = document.pagePointSize(0)

    # pointSize is in pts which are 1/72 of an inch.
    # this calculates the "resolution" assuming 96 dpi (the traditional standard on windows)
    width = pointSize.width() * (96/72)
    height = pointSize.height() * (96/72)
    
    document.close()

    return (width, height)
    

HydrusPDFHandling.GetPDFResolution = GetPDFResolution
