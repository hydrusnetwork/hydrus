import os

# If not explicitly set, prefer PySide instead of PyQt, which is the qtpy default
# It is critical that this runs on startup *before* anything is imported from qtpy.

if 'QT_API' not in os.environ:
    
    try:
        
        import PySide6 # Qt6
        
        os.environ[ 'QT_API' ] = 'pyside6'
        
    except ImportError as e:
        
        try:
            
            import PySide2 # Qt5
            
            os.environ[ 'QT_API' ] = 'pyside2'
            
        except ImportError as e:
            
            pass
            
        
    

#

import qtpy

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

# 2022-07
# an older version of qtpy, 1.9 or so, didn't actually have attribute qtpy.PYQT6, so we'll test and assign carefully

WE_ARE_QT5 = False
WE_ARE_QT6 = False

WE_ARE_PYQT = False
WE_ARE_PYSIDE = False

if qtpy.PYQT5:
    
    WE_ARE_QT5 = True
    WE_ARE_PYQT = True
    
    from PyQt5 import sip # pylint: disable=E0401
    
    def isValid( obj ):
        
        if isinstance( obj, sip.simplewrapper ):
            
            return not sip.isdeleted( obj )
            
        
        return True
        
    
elif hasattr( qtpy, 'PYQT6' ) and qtpy.PYQT6:
    
    WE_ARE_QT6 = True
    WE_ARE_PYQT = True
    
    from PyQt6 import sip # pylint: disable=E0401
    
    def isValid( obj ):
        
        if isinstance( obj, sip.simplewrapper ):
            
            return not sip.isdeleted( obj )
            
        
        return True
    
elif qtpy.PYSIDE2:
    
    WE_ARE_QT5 = True
    WE_ARE_PYSIDE = True
    
    import shiboken2
    
    isValid = shiboken2.isValid
    
elif qtpy.PYSIDE6:
    
    WE_ARE_QT6 = True
    WE_ARE_PYSIDE = True
    
    import shiboken6
    
    isValid = shiboken6.isValid
    
else:
    
    raise RuntimeError( 'You need one of PySide2, PySide6, PyQt5, or PyQt6' )
    

def MonkeyPatchMissingMethods():
    
    if WE_ARE_QT5:
        
        QG.QMouseEvent.globalPosition = lambda self, *args, **kwargs: QC.QPointF( self.globalPos( *args, **kwargs ) )
        
        QG.QMouseEvent.position = lambda self, *args, **kwargs: QC.QPointF( self.pos( *args, **kwargs ) )
        
        QG.QDropEvent.position = lambda self, *args, **kwargs: QC.QPointF( self.pos( *args, **kwargs ) )
        
        QG.QDropEvent.modifiers = lambda self, *args, **kwargs: self.keyboardModifiers( *args, **kwargs )
        
    
    if WE_ARE_PYQT:
        
        def MonkeyPatchGetSaveFileName( original_function ):
            
            def new_function( *args, **kwargs ):
                
                if 'selectedFilter' in kwargs:
                    
                    kwargs[ 'initialFilter' ] = kwargs[ 'selectedFilter' ]
                    del kwargs[ 'selectedFilter' ]
                    
                    return original_function( *args, **kwargs )
                    
                
            
            return new_function
            
        
        QW.QFileDialog.getSaveFileName = MonkeyPatchGetSaveFileName( QW.QFileDialog.getSaveFileName )
        
    
