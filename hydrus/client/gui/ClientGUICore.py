from qtpy import QtCore as QC
from qtpy import QtGui as QG

from hydrus.client.gui import ClientGUIMenus

class GUICore( QC.QObject ):
    
    my_instance = None
    
    def __init__( self ):
        
        QC.QObject.__init__( self )
        
        self._menu_open = False
        
        GUICore.my_instance = self
        
    
    @staticmethod
    def instance() -> 'GUICore':
        
        if GUICore.my_instance is None:
            
            raise Exception( 'GUICore is not yet initialised!' )
            
        else:
            
            return GUICore.my_instance
            
        
    
    def MenubarMenuIsOpen( self ):
        
        self._menu_open = True
        
    
    def MenubarMenuIsClosed( self ):
        
        self._menu_open = False
        
    
    def MenuIsOpen( self ):
        
        return self._menu_open
        
    
    def PopupMenu( self, window, menu ):
        
        if not menu.isEmpty():
            
            self._menu_open = True
            
            menu.exec_( QG.QCursor.pos() ) # This could also be window.mapToGlobal( QC.QPoint( 0, 0 ) ), but in practice, popping up at the current cursor position feels better.
            
            self._menu_open = False
            
        
        ClientGUIMenus.DestroyMenu( menu )
        
    
core = GUICore.instance
