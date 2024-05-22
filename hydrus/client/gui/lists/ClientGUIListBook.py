from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes

class ListBook( QW.QWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QWidget.__init__( self, *args, **kwargs )
        
        self._keys_to_active_pages = {}
        
        self._list_box = ClientGUIListBoxes.BetterQListWidget( self )
        self._list_box.setSelectionMode( QW.QListWidget.SingleSelection )
        
        self._empty_panel = QW.QWidget( self )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._panel_sizer = QP.VBoxLayout()
        
        QP.AddToLayout( self._panel_sizer, self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._list_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( hbox, self._panel_sizer, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.itemSelectionChanged.connect( self._ListBoxSelected )
        
        self.setLayout( hbox )
        
    
    def _GetIndex( self, key ):
        
        for i in range( self._list_box.count() ):
            
            i_key = self._list_box.item( i ).data( QC.Qt.UserRole )
            
            if i_key == key:
                
                return i
                
            
        
        return -1
        
    
    def _ListBoxSelected( self ):
        
        selected_datas = list( self._list_box.GetData( only_selected = True ) )
        
        if len( selected_datas ) > 0:
            
            key = selected_datas[0]
            
            self._ShowPage( key )
            
        
    
    def _ShowPage( self, key ):
        
        self._current_key = key
        
        self._current_panel.setVisible( False )
        
        if self._current_key is None:
            
            self._current_panel = self._empty_panel
            
        else:
            
            self._current_panel = self._keys_to_active_pages[ self._current_key ]
            
        
        self._current_panel.show()
        
        self.update()
        
    
    def AddPage( self, display_name, key, page, select = False ):
        
        if self.HasKey( key ):
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        if not isinstance( page, tuple ):
            
            page.setVisible( False )
            
            QP.AddToLayout( self._panel_sizer, page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        if self._list_box.count() == 0:
            
            select = True
            
        
        self._keys_to_active_pages[ key ] = page
        
        self._list_box.Append( display_name, key, select = select )
        
        self._list_box.sortItems()
        
        if select:
            
            self._list_box.SelectData( [ key ] )
            
        
    
    def DeleteAllPages( self ):
        
        self._panel_sizer.removeWidget( self._empty_panel )
        
        QP.ClearLayout( self._panel_sizer, delete_widgets=True )
        
        QP.AddToLayout( self._panel_sizer, self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._keys_to_active_pages = {}
        
        self._list_box.clear()
        
    
    def DeleteCurrentPage( self ):
        
        if self._list_box.GetNumSelected() > 0:
            
            key_to_delete = self._current_key
            page_to_delete = self._current_panel
            
            selected_indices = self._list_box.GetSelectedIndices()
            
            selection = selected_indices[0]
            
            next_selection = selection + 1
            previous_selection = selection - 1
            
            self._panel_sizer.removeWidget( page_to_delete )
            
            page_to_delete.deleteLater()
            
            del self._keys_to_active_pages[ key_to_delete ]
            
            self._list_box.DeleteSelected()
            
            if next_selection < self._list_box.count():
                
                self._list_box.SelectData( [ self._list_box.item( next_selection ).data( QC.Qt.UserRole ) ] )
                
            elif previous_selection >= 0:
                
                self._list_box.SelectData( [ self._list_box.item( previous_selection ).data( QC.Qt.UserRole ) ] )
                
            else:
                
                self._ShowPage( None )
                
            
        
    
    def GetCurrentKey( self ):
        
        return self._current_key
        
    
    def GetCurrentPage( self ):
        
        if self._current_panel == self._empty_panel:
            
            return None
            
        else:
            
            return self._current_panel
            
        
    
    def GetActivePages( self ):
        
        return list(self._keys_to_active_pages.values())
        
    
    def GetPage( self, key ):
        
        if key in self._keys_to_active_pages:
            
            return self._keys_to_active_pages[ key ]
            
        
        raise Exception( 'That page not found!' )
        
    
    def GetPageCount( self ):
        
        return len( self._keys_to_active_pages )
        
    
    def HasKey( self, key ):
        
        return key in self._keys_to_active_pages
        
    
    def Select( self, key ):
        
        if self.HasKey( key ):
            
            self._list_box.SelectData( [ key ] )
            
        
    
    def SelectPage( self, page_to_select ):
        
        for ( key, page ) in self._keys_to_active_pages.items():
            
            if page == page_to_select:
                
                self._list_box.SelectData( [ key ] )
                
                return
                
            
        
    
