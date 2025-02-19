from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class EditSelectFromListPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list, value_to_select = None, sort_tuples = True ):
        
        super().__init__( parent )
        
        self._list = ClientGUIListBoxes.BetterQListWidget( self )
        self._list.itemDoubleClicked.connect( self.EventSelect )
        
        #
        
        if sort_tuples:
            
            try:
                
                choice_tuples.sort()
                
            except TypeError:
                
                try:
                    
                    choice_tuples.sort( key = lambda t: t[0] )
                    
                except TypeError:
                    
                    pass # fugg
                    
                
            
        
        for ( i, ( label, value ) ) in enumerate( choice_tuples ):
            
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.ItemDataRole.UserRole, value )
            self._list.addItem( item )
            
        
        if value_to_select is not None:
            
            self._list.SelectData( ( value_to_select, ) )
            
        
        if len( list( self._list.selectedItems() ) ) == 0:
            
            self._list.item( 0 ).setSelected( True )
            
        
        #
        
        max_label_width_chars = max( ( len( label ) for ( label, value ) in choice_tuples ) )
        
        width_chars = min( 64, max_label_width_chars + 2 )
        height_chars = min( len( choice_tuples ), 36 )
        
        ( width_px, height_px ) = ClientGUIFunctions.ConvertTextToPixels( self._list, ( width_chars, height_chars ) )
        
        row_height_px = self._list.sizeHintForRow( 0 )
        
        if row_height_px != -1:
            
            height_px = row_height_px * height_chars
            
        
        self._list.setMinimumSize( QC.QSize( width_px, height_px ) )
        
        # wew lad, but it 'works'
        # formalise this and make a 'stretchy qlistwidget' class
        #self._list.sizeHint = lambda: QC.QSize( width_px, height_px )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def EventSelect( self, item ):
        
        self._OKParent()
        
    
    def GetValue( self ):
        
        data = self._list.GetData( only_selected = True )
        
        if len( data ) == 0:
            
            data = self._list.GetData()
            
        
        if len( data ) == 0:
            
            raise HydrusExceptions.CancelledException( 'No data selected!' )
            
        
        return data[0]
        
    

class EditSelectFromListButtonsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choices, message = '' ):
        
        super().__init__( parent )
        
        self._data = None
        
        vbox = QP.VBoxLayout()
        
        if message != '':
            
            st = ClientGUICommon.BetterStaticText( self, label = message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        first_focused = False
        
        for ( text, data, tt ) in choices:
            
            button = ClientGUICommon.BetterButton( self, text, self._ButtonChoice, data )
            
            button.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            if not first_focused:
                
                ClientGUIFunctions.SetFocusLater( button )
                
                first_focused = True
                
            
        
        self.widget().setLayout( vbox )
        
    
    def _ButtonChoice( self, data ):
        
        self._data = data
        
        self._OKParent()
        
    
    def GetValue( self ):
        
        return self._data
        
    

class ReviewSelectFromListButtonsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, choices, message = '' ):
        
        super().__init__( parent )
        
        vbox = QP.VBoxLayout()
        
        if message != '':
            
            st = ClientGUICommon.BetterStaticText( self, label = message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        first_focused = False
        
        for ( text, call, tt ) in choices:
            
            button = ClientGUICommon.BetterButton( self, text, call )
            
            button.SetCall( self._DoButton, button, call )
            
            button.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( button, 20 ) )
            
            button.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            if not first_focused:
                
                ClientGUIFunctions.SetFocusLater( button )
                
                first_focused = True
                
            
        
        self.widget().setLayout( vbox )
        
    
    def _DoButton( self, button: ClientGUICommon.BetterButton, call ):
        
        try:
            
            call()
            
        except HydrusExceptions.VetoException:
            
            button.setEnabled( False )
            
        
    

class EditSelectMultiple( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list ):
        
        super().__init__( parent )
        
        self._checkboxes = ClientGUICommon.BetterCheckBoxList( self )
        
        self._checkboxes.setMinimumSize( QC.QSize( 320, 420 ) )
        
        try:
            
            choice_tuples.sort()
            
        except TypeError:
            
            try:
                
                choice_tuples.sort( key = lambda t: t[0] )
                
            except TypeError:
                
                pass # fugg
                
            
        
        for ( index, ( label, data, selected ) ) in enumerate( choice_tuples ):
            
            self._checkboxes.Append( label, data )
            
            if selected:
                
                self._checkboxes.Check( index )
                
            
        
        self._checkboxes.SetHeightBasedOnContents()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> list:
        
        return self._checkboxes.GetValue()
        
    
