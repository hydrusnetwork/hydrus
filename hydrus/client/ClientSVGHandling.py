from qtpy import QtSvg
from qtpy import QtGui as QG
from qtpy import QtCore as QC

from hydrus.core import HydrusExceptions
from hydrus.core.files import HydrusSVGHandling

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions

def QtLoadSVGRenderer( path: str ):
    
    renderer = QtSvg.QSvgRenderer()
    
    try:
        
        renderer.load( path )
        
    except Exception as e:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Could not load SVG file.' )
        
    
    if not renderer.isValid():
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'SVG file is invalid!' )
        
    
    return renderer
    

def GenerateThumbnailNumPyFromSVGPath( path: str, target_resolution: tuple[int, int] ) -> bytes:
    
    # TODO: SVGs have no inherent resolution, so all this is pretty stupid. we should render to exactly the res we want and then clip the result, not beforehand
    
    def qt_code():
        
        try:
            
            renderer = QtLoadSVGRenderer( path )
            
            # Seems to help for some weird floating point dimension SVGs
            renderer.setAspectRatioMode( QC.Qt.AspectRatioMode.KeepAspectRatio )
            
            ( target_width, target_height ) = target_resolution
            
            qt_image = QG.QImage( target_width, target_height, QG.QImage.Format.Format_RGBA8888 )
            
            qt_image.fill( QC.Qt.GlobalColor.transparent )
            
            painter = QG.QPainter( qt_image )
            
            renderer.render( painter )
            
            painter.end()
            
            numpy_image = ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )
            
            thumbnail_numpy_image = numpy_image
            
            return thumbnail_numpy_image
            
        except Exception as e:
            
            raise HydrusExceptions.NoThumbnailFileException()
            
        
    
    return CG.client_controller.CallBlockingToQtTLW( qt_code )
    

HydrusSVGHandling.GenerateThumbnailNumPyFromSVGPath = GenerateThumbnailNumPyFromSVGPath

def GetSVGResolution( path: str ):
    
    def qt_code():
        
        try:
            
            renderer = QtLoadSVGRenderer( path )
            
            default_size = renderer.defaultSize()
            
            resolution = ( default_size.width(), default_size.height() )
            
            return resolution
            
        except Exception as e:
            
            raise HydrusExceptions.NoResolutionFileException( e )
            
        
    
    return CG.client_controller.CallBlockingToQtTLW( qt_code )
    

HydrusSVGHandling.GetSVGResolution = GetSVGResolution
