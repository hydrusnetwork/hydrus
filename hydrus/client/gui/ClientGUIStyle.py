import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime

STYLESHEET_DIR = os.path.join( HC.STATIC_DIR, 'qss' )

DEFAULT_HYDRUS_STYLESHEET = ''
ORIGINAL_STYLE_NAME = None
CURRENT_STYLE_NAME = None
ORIGINAL_STYLESHEET = None
CURRENT_STYLESHEET = None

def ClearStylesheet():
    
    SetStyleSheet( ORIGINAL_STYLESHEET )
    
def GetAvailableStyles():
    
    # so eventually expand this to do QStylePlugin or whatever we are doing to add more QStyles
    
    return list( QW.QStyleFactory.keys() )
    
def GetAvailableStylesheets():
    
    if not os.path.exists( STYLESHEET_DIR ) or not os.path.isdir( STYLESHEET_DIR ):
        
        raise HydrusExceptions.DataMissing( 'Stylesheet dir "{}" is missing or not a directory!'.format( STYLESHEET_DIR ) )
        
    
    stylesheet_filenames = []
    
    extensions = [ '.qss', '.css' ]
    
    for filename in os.listdir( STYLESHEET_DIR ):
        
        if True in ( filename.endswith( ext ) for ext in extensions ):
            
            stylesheet_filenames.append( filename )
            
        
    
    return stylesheet_filenames
    
def InitialiseDefaults():
    
    global DEFAULT_HYDRUS_STYLESHEET
    
    try:
        
        with open( os.path.join( STYLESHEET_DIR, 'default_hydrus.qss' ), 'r', encoding = 'utf-8' ) as f:
            
            DEFAULT_HYDRUS_STYLESHEET = f.read()
            
        
    except Exception as e:
        
        HydrusData.Print( 'Failed to load default hydrus qss:' )
        HydrusData.PrintException( e )
        
        DEFAULT_HYDRUS_STYLESHEET = ''
        
    
    global ORIGINAL_STYLE_NAME
    global CURRENT_STYLE_NAME
    
    ORIGINAL_STYLE_NAME = QW.QApplication.instance().style().objectName()
    CURRENT_STYLE_NAME = ORIGINAL_STYLE_NAME
    
    global ORIGINAL_STYLESHEET
    global CURRENT_STYLESHEET
    
    ORIGINAL_STYLESHEET = QW.QApplication.instance().styleSheet()
    CURRENT_STYLESHEET = ORIGINAL_STYLESHEET
    
def SetStyleFromName( name ):
    
    global CURRENT_STYLE_NAME
    
    if name == CURRENT_STYLE_NAME:
        
        return
        
    
    if name in GetAvailableStyles():
        
        try:
            
            QW.QApplication.instance().setStyle( name )
            
            CURRENT_STYLE_NAME = name
            
        except Exception as e:
            
            raise HydrusExceptions.DataMissing( 'Style "{}" could not be generated/applied. If this is the default, perhaps a third-party custom style, you may have to restart the client to re-set it. Extra error info: {}'.format( name, e ) )
            
        
    else:
        
        raise HydrusExceptions.DataMissing( 'Style "{}" does not exist! If this is the default, perhaps a third-party custom style, you may have to restart the client to re-set it.'.format( name ) )
        
    
def SetStyleSheet( stylesheet, prepend_hydrus = True ):
    
    stylesheet_to_use = stylesheet
    
    if prepend_hydrus:
        
        global DEFAULT_HYDRUS_STYLESHEET
        
        stylesheet_to_use = DEFAULT_HYDRUS_STYLESHEET + os.linesep * 2 + stylesheet
        
    
    global CURRENT_STYLESHEET
    
    if CURRENT_STYLESHEET != stylesheet_to_use:
        
        QW.QApplication.instance().setStyleSheet( stylesheet_to_use )
        
        CURRENT_STYLESHEET = stylesheet_to_use
        
    
def SetStylesheetFromPath( filename ):
    
    path = os.path.join( STYLESHEET_DIR, filename )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.DataMissing( 'Stylesheet "{}" does not exist!'.format( path ) )
        
    
    with open( path, 'r', encoding = 'utf-8' ) as f:
        
        qss = f.read()
        
    
    SetStyleSheet( qss )
    
