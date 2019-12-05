from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
import os
from qtpy import QtWidgets as QW

STYLESHEET_DIR = os.path.join( HC.BASE_DIR, 'static', 'qss' )

ORIGINAL_STYLE = None
ORIGINAL_STYLESHEET = None

def ClearStylesheet():
    
    QW.QApplication.instance().setStyleSheet( ORIGINAL_STYLESHEET )
    
def GetAvailableStyles():
    
    # so eventually expand this to do QStylePlugin or whatever we are doing to add more QStyles
    
    return list( QW.QStyleFactory.keys() )
    
def GetCurrentStyleName():
    
    return QW.QApplication.instance().style().objectName()
    
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
    
    global ORIGINAL_STYLE
    
    ORIGINAL_STYLE = GetCurrentStyleName()
    
    global ORIGINAL_STYLESHEET
    
    ORIGINAL_STYLESHEET = QW.QApplication.instance().styleSheet()
    
def SetStyle( name ):
    
    current_name = GetCurrentStyleName()
    
    if name == current_name:
        
        return
        
    
    if name in QW.QStyleFactory.keys():
        
        QW.QApplication.instance().setStyle( QW.QStyleFactory.create( name ) )
        
    else:
        
        raise HydrusExceptions.DataMissing( 'Style "{}" does not exist!'.format( name ) )
        
    
def SetStylesheet( filename ):
    
    path = os.path.join( STYLESHEET_DIR, filename )
    
    if not os.path.exists( path ):
        
        raise HydrusExceptions.DataMissing( 'Stylesheet "{}" does not exist!'.format( path ) )
        
    
    with open( path, 'r', encoding = 'utf-8' ) as f:
        
        qss = f.read()
        
    
    QW.QApplication.instance().setStyleSheet( qss )
    
