import typing

from qtpy import QtSvg
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling

from hydrus.client.gui import ClientGUIFunctions

def BaseGenerateThumbnailBytesFromSVGPath( path: str, target_resolution: typing.Tuple[int, int], clip_rect = None ) -> bytes:
    
    raise HydrusExceptions.UnsupportedFileException()
    

def BaseGetSVGResolution( path: str ):
    
    return ( None, None )
    

GenerateThumbnailBytesFromSVGPath = BaseGenerateThumbnailBytesFromSVGPath
GetSVGResolution = BaseGetSVGResolution
