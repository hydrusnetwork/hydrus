import typing

from qtpy import QtPdf
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling

from hydrus.client.gui import ClientGUIFunctions

def BaseGenerateThumbnailBytesFromPDFPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.UnsupportedFileException()
    

def BaseGetPDFResolution( path: str ):
    
    return ( None, None )
    

GenerateThumbnailBytesFromPDFPath = BaseGenerateThumbnailBytesFromPDFPath
GetPDFResolution = BaseGetPDFResolution
