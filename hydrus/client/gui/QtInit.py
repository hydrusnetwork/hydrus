import os
import traceback
from hydrus.client.gui import QtInitImportTest

# If not explicitly set, prefer PySide instead of PyQt, which is the qtpy default
# It is critical that this runs on startup *before* anything is imported from qtpy.

if 'QT_API' in os.environ:
    
    QT_API_INITIAL_VALUE = os.environ[ 'QT_API' ]
    
else:
    
    from hydrus.core import HydrusConstants as HC
    
    if HC.RUNNING_FROM_MACOS_APP:
        
        os.environ[ 'FORCE_QT_API' ] = '1'
        
    
    QT_API_INITIAL_VALUE = None
    
    if 'QT_API' not in os.environ:
        
        try:
            
            import PySide6 # Qt6
            
            os.environ[ 'QT_API' ] = 'pyside6'
            
        except ImportError as e:
            
            pass
            
        
    
    if 'QT_API' not in os.environ:
        
        try:
            
            import PyQt6 # Qt6
            
            os.environ[ 'QT_API' ] = 'pyqt6'
            
        except ImportError as e:
            
            pass
            
        
    
    if 'QT_API' not in os.environ:
        
        try:
            
            import PySide2 # Qt5
            
            os.environ[ 'QT_API' ] = 'pyside2'
            
        except ImportError as e:
            
            pass
            
        
    
    if 'QT_API' not in os.environ:
        
        try:
            
            import PyQt5 # Qt5
            
            os.environ[ 'QT_API' ] = 'pyqt5'
            
        except ImportError as e:
            
            pass
            
        
    

def get_qt_api_str_status():
    
    try:
        
        if QT_API_INITIAL_VALUE is None:
            
            initial_qt = 'QT_API was initially not set.'
            
        else:
            
            initial_qt = 'QT_API was initially "{}".'.format( QT_API_INITIAL_VALUE )
            
        
        if 'QT_API' in os.environ:
            
            current_qt = 'Current QT_API is "{}".'.format( os.environ[ 'QT_API' ] )
            
        else:
            
            current_qt = 'Currently QT_API is not set.'
            
        
        forced_qt = 'FORCE_QT_API is ON.' if 'FORCE_QT_API' in os.environ else 'FORCE_QT_API is not set.'
        
        return '{} {} {}'.format( initial_qt, current_qt, forced_qt )
        
    except Exception as e:
        
        return 'Unable to get QT_API info: {}'.format( traceback.format_exc() )
        
    

#

try:
    
    import qtpy
    
except ModuleNotFoundError as e:
    
    message = 'Either the qtpy module was not found, or qtpy could not find a Qt to use!'
    
    message += '\n' * 2
    
    message += 'Are you sure you installed and activated your venv correctly? Check the \'running from source\' section of the help if you are confused!'
    
    message += '\n' * 2
    
    message += 'Here is info on QT_API:\n{}'.format( get_qt_api_str_status() )
    
    message += '\n' * 2
    
    message += 'Here is info on your available Qt Libraries:\n{}'.format( QtInitImportTest.get_qt_library_str_status() )
    
    raise Exception( message )
    

try:
    
    from qtpy import QtCore as QC
    from qtpy import QtWidgets as QW
    from qtpy import QtGui as QG
    from qtpy import QtSvg 
    
except ModuleNotFoundError as e:
    
    message = 'One of the Qt modules could not be loaded! Error was:\n{}'.format(
        traceback.format_exc()
    )
    
    message += '\n' * 2
    
    try:
        
        message += 'Of the different Qts, qtpy selected: PySide2 ({}), PySide6 ({}), PyQt5 ({}), PyQt6 ({}).'.format(
            'selected' if qtpy.PYSIDE2 else 'not selected',
            'selected' if qtpy.PYSIDE6 else 'not selected',
            'selected' if qtpy.PYQT5 else 'not selected',
            'selected' if qtpy.PYQT6 else 'not selected'
        )
        
    except Exception as e:
        
        message += 'qtpy had problems saying which module it had selected!'
        
    
    message += '\n' * 2
    
    message += 'Here is info on QT_API:\n{}'.format( get_qt_api_str_status() )
    
    message += '\n' * 2
    
    message += 'Here is info on your available Qt Libraries:\n\n{}'.format( QtInitImportTest.get_qt_library_str_status() )
    
    message += '\n' * 2
    
    message += 'If you are running from a built release, please let hydev know!'
    
    raise Exception( message )
    

# 2022-07
# an older version of qtpy, 1.9 or so, didn't actually have attribute qtpy.PYQT6, so we'll test and assign carefully

WE_ARE_QT5 = False
WE_ARE_QT6 = False

WE_ARE_PYQT = False
WE_ARE_PYSIDE = False

if qtpy.PYQT5:
    
    WE_ARE_QT5 = True
    WE_ARE_PYQT = True
    
    # noinspection PyUnresolvedReferences
    from PyQt5 import sip # pylint: disable=E0401
    
    def isValid( obj ):
        
        if isinstance( obj, sip.simplewrapper ):
            
            return not sip.isdeleted( obj )
            
        
        return True
        
    
elif hasattr( qtpy, 'PYQT6' ) and qtpy.PYQT6:
    
    WE_ARE_QT6 = True
    WE_ARE_PYQT = True
    
    # noinspection PyUnresolvedReferences
    from PyQt6 import sip
    
    def isValid( obj ):
        
        if isinstance( obj, sip.simplewrapper ):
            
            return not sip.isdeleted( obj )
            
        
        return True
        
    
elif qtpy.PYSIDE2:
    
    WE_ARE_QT5 = True
    WE_ARE_PYSIDE = True
    
    # noinspection PyUnresolvedReferences
    import shiboken2
    
    isValid = shiboken2.isValid
    
elif qtpy.PYSIDE6:
    
    WE_ARE_QT6 = True
    WE_ARE_PYSIDE = True
    
    import shiboken6
    
    isValid = shiboken6.isValid
    
else:
    
    raise RuntimeError( 'You need one of PySide2, PySide6, PyQt5, or PyQt6' )
    

def DoWinDarkMode():
    
    os.environ[ 'QT_QPA_PLATFORM' ] = 'windows:darkmode=1'
    

def MonkeyPatchMissingMethods():
    
    if WE_ARE_QT5:
        
        print( 'Qt5 is no longer officially supported. It will simply break one day, sorry!' )
        
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
        
    

def SetupLogging():
    
    # do this before QApplication, it tells QMediaPlayer to not spam the log with ffmpeg info on every media load
    # I'd prefer to keep critical logging, but this thing seems to be more C++ and less python, and the wildcard shuts it off where specific enumerations don't seem to. maybe worth a revisit
    
    QC.QLoggingCategory.setFilterRules( 'qt.multimedia.ffmpeg.*=false' )
    QC.QLoggingCategory.setFilterRules( 'qt.multimedia.*=false' )
    
