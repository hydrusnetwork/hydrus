from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes

class ListBook( QW.QWidget ):
    
    currentChanged = QC.Signal( int )
    
    def __init__( self, parent: QW.QWidget, list_chars_width = 28 ):
        
        super().__init__( parent )
        
        self._page_list = ClientGUIListBoxes.BetterQListWidget( self )
        self._page_list.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        self._page_list.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._page_list, list_chars_width ) )
        
        self._widget_stack = QW.QStackedWidget( self )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._page_list, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( hbox, self._widget_stack, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( hbox )
        
        #
        
        self._page_list.itemSelectionChanged.connect( self._ChangePage )
        self._widget_stack.currentChanged.connect( self.currentChanged )
        
    
    def _ChangePage( self ):
        
        # we avoid index here which allows us to resort the list and not have to worry about the widget stack's sort
        
        num_selected = self._page_list.GetNumSelected()
        
        if num_selected != 1:
            
            return
            
        
        page = self._page_list.GetData( only_selected = True )[0]
        
        self._widget_stack.setCurrentWidget( page )
        
    
    def _ShiftSelection( self, delta ):
        
        count = self._page_list.count()
        
        if count < 2:
            
            return
            
        
        current_index = self._page_list.currentRow()
        
        new_index = ( current_index + delta ) % count
        
        self._page_list.setCurrentRow( new_index )
        
    
    def AddPage( self, name: str, page: QW.QWidget, select = False ):
        
        if self._page_list.count() == 0:
            
            select = True
            
        
        self._widget_stack.addWidget( page )
        
        self._page_list.Append( name, page, select = select )
        
    
    def addTab( self, page: QW.QWidget, name: str, select = False ):
        
        self.AddPage( name, page, select = select )
        
    
    def count( self ) -> int:
        
        return self._page_list.count()
        
    
    def currentWidget( self ) -> QW.QWidget | None:
        
        if self._widget_stack.count() == 0:
            
            return None
            
        
        return self._widget_stack.currentWidget()
        
    
    def DeleteAllPages( self ):
        
        self._page_list.clear()
        
        while self._widget_stack.count() > 0:
            
            page = self._widget_stack.widget( 0 )
            
            self._widget_stack.removeWidget( page )
            
            page.deleteLater()
            
        
    
    def GetPages( self ) -> list[ QW.QWidget ]:
        
        return self._page_list.GetData()
        
    
    def GetCurrentPageIndex( self ) :
        
        return self._page_list.currentRow()
        
    
    def setTabText( self, index, text ):
        
        self._page_list.item( index ).setText( text )
        
    
    def SelectLeft( self ):
        
        self._ShiftSelection( -1 )
        
    
    def SelectPage( self, page: QW.QWidget ):
        
        for list_item in [ self._page_list.item( i ) for i in range( self._page_list.count() ) ]:
            
            if list_item.data( QC.Qt.ItemDataRole.UserRole ) == page:
                
                self._page_list.setCurrentItem( list_item )
                
                return
                
            
        
    
    setCurrentWidget = SelectPage
    
    def SelectRight( self ):
        
        self._ShiftSelection( 1 )
        
    
    def SelectName( self, name: str ):
        
        items = self._page_list.findItems( name, QC.Qt.MatchFlag.MatchExactly )
        
        if items:
            
            self._page_list.setCurrentItem( items[0] )
            
        
    
    def SortList( self ):
        
        self._page_list.sortItems( QC.Qt.SortOrder.AscendingOrder )
        
    
    def tabText( self, index ):
        
        return self._page_list.item( index ).text()
        
    
    def widget( self, index: int ):
        
        return self._page_list.item( index ).data( QC.Qt.ItemDataRole.UserRole )
        
    
