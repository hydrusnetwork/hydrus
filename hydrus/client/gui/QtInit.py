import os

# If not explicitly set, prefer PySide instead of PyQt, which is the qtpy default
# It is critical that this runs on startup *before* anything is imported from qtpy.

def get_qt_api_str_status():
    
    try:
        
        if 'QT_API' in os.environ:
            
            qt_api = os.environ[ 'QT_API' ]
            
            import_status = 'imported ok'
            
            if qt_api == 'pyqt5':
                
                try:
                    
                    import PyQt5
                    
                except ImportError as e:
                    
                    import_status = 'did not import ok: {}'.format( e )
                    
                
            elif qt_api == 'pyside2':
                
                try:
                    
                    import PySide2
                    
                except ImportError as e:
                    
                    import_status = 'did not import ok: {}'.format( e )
                    
                
            elif qt_api == 'pyqt6':
                
                try:
                    
                    import PyQt6
                    
                except ImportError as e:
                    
                    import_status = 'did not import ok: {}'.format( e )
                    
                
            elif qt_api == 'pyside6':
                
                try:
                    
                    import PySide6
                    
                except ImportError as e:
                    
                    import_status = 'did not import ok: {}'.format( e )
                    
                
            
            return 'QT_API: {}, {}'.format( qt_api, import_status )
            
        else:
            
            return 'No QT_API set.'
            
        
    except Exception as e:
        
        return 'Unable to get QT_API info: {}'.format( e )
        
    

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

try:
    
    import qtpy
    
except ModuleNotFoundError as e:
    
    qt_str = get_qt_api_str_status()
    
    message = 'Either the qtpy module was not found, or qtpy could not find a Qt to use! Error was: {}'.format(
        e
    )
    message += os.linesep * 2
    message += 'Are you sure you installed and activated your venv correctly? Check the \'running from source\' section of the help if you are confused! Here is info on QT_API: {}'.format(
        qt_str
    )
    
    raise Exception( message )
    

try:
    
    from qtpy import QtCore as QC
    from qtpy import QtWidgets as QW
    from qtpy import QtGui as QG
    
except ModuleNotFoundError as e:
    
    message = 'One of the Qt modules could not be loaded! Error was: {}'.format(
        e
    )
    
    message += os.linesep * 2
    
    try:
        
        message += 'Of the different Qts, qtpy selected: PySide2 ({}), PySide6 ({}), PyQt5 ({}), PyQt6 ({}).'.format(
            'selected' if qtpy.PYSIDE2 else 'not selected',
            'selected' if qtpy.PYSIDE6 else 'not selected',
            'selected' if qtpy.PYQT5 else 'not selected',
            'selected' if qtpy.PYQT6 else 'not selected'
        )
        
    except:
        
        message += 'qtpy had problems saying which module it had selected!'
        
    
    qt_str = get_qt_api_str_status()
    
    message += ' Here is info on QT_API: {}'.format(
        qt_str
    )
    
    message += os.linesep * 2
    
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
    

def DoWinDarkMode():
    
    os.environ[ 'QT_QPA_PLATFORM' ] = 'windows:darkmode=1'
    

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
        
    
