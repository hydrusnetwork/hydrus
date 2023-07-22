import typing
from qtpy import QtSvg
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusImageHandling

from hydrus.client.gui import ClientGUIFunctions

def LoadSVGRenderer(path: str): 

    renderer = QtSvg.QSvgRenderer();

    try:
        renderer.load(path)
        
    except:
        
        raise  HydrusExceptions.DamagedOrUnusualFileException('Could not load SVG file.')

    if not renderer.isValid():
      
      raise  HydrusExceptions.DamagedOrUnusualFileException('SVG file is invalid!')
    
    return renderer

def GenerateThumbnailBytesFromSVGPath(path: str, target_resolution: typing.Tuple[int, int], clip_rect = None) -> bytes:
    
    # TODO handle clipping

    ( target_width, target_height ) = target_resolution

    renderer = LoadSVGRenderer(path)

    # Seems to help for some weird floating point dimension SVGs
    renderer.setAspectRatioMode(QC.Qt.AspectRatioMode.KeepAspectRatio)
    
    try:
        
        qt_image = QG.QImage( target_width, target_height, QG.QImage.Format_RGBA8888 )

        qt_image.fill( QC.Qt.transparent )
    
        painter = QG.QPainter(qt_image)

        renderer.render(painter)

        numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy(qt_image)

        painter.end()

        return HydrusImageHandling.GenerateThumbnailBytesNumPy(numpy_image)
    
    except:

        raise HydrusExceptions.UnsupportedFileException()


def GetSVGResolution( path: str ):

    renderer = LoadSVGRenderer(path)

    resolution = renderer.defaultSize().toTuple()

    return resolution