import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import QtPorting as QP
from hydrus.client.metadata import ClientTagSorting

class TagSortControl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, tag_sort: ClientTagSorting.TagSort, show_siblings = False ):
        
        QW.QWidget.__init__( self, parent )
        
        self._sort_type = ClientGUICommon.BetterChoice( self )
        
        for sort_type in ( ClientTagSorting.SORT_BY_HUMAN_TAG, ClientTagSorting.SORT_BY_HUMAN_SUBTAG, ClientTagSorting.SORT_BY_COUNT ):
            
            self._sort_type.addItem( ClientTagSorting.sort_type_str_lookup[ sort_type ], sort_type )
            
        
        self._sort_order_text = ClientGUICommon.BetterChoice( self )
        
        self._sort_order_text.addItem( 'a-z', CC.SORT_ASC )
        self._sort_order_text.addItem( 'z-a', CC.SORT_DESC )
        
        self._sort_order_count = ClientGUICommon.BetterChoice( self )
        
        self._sort_order_count.addItem( 'most first', CC.SORT_DESC )
        self._sort_order_count.addItem( 'fewest first', CC.SORT_ASC )
        
        self._show_siblings = show_siblings
        
        self._use_siblings = ClientGUICommon.BetterChoice( self )
        
        self._use_siblings.addItem( 'siblings', True )
        self._use_siblings.addItem( 'tags', False )
        
        self._group_by = ClientGUICommon.BetterChoice( self )
        
        self._group_by.addItem( 'no grouping', ClientTagSorting.GROUP_BY_NOTHING )
        self._group_by.addItem( 'group namespace', ClientTagSorting.GROUP_BY_NAMESPACE )
        
        #
        
        self.SetValue( tag_sort )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._sort_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_order_text, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sort_order_count, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._use_siblings, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._group_by, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._sort_type.currentIndexChanged.connect( self._UpdateControlsAfterSortTypeChanged )
        
        self._sort_type.currentIndexChanged.connect( self._HandleValueChanged )
        self._sort_order_text.currentIndexChanged.connect( self._HandleValueChanged )
        self._sort_order_count.currentIndexChanged.connect( self._HandleValueChanged )
        self._use_siblings.currentIndexChanged.connect( self._HandleValueChanged )
        self._group_by.currentIndexChanged.connect( self._HandleValueChanged )
        
    
    def _UpdateControlsAfterSortTypeChanged( self ):
        
        sort_type = self._sort_type.GetValue()
        
        self._sort_order_text.setVisible( sort_type in ( ClientTagSorting.SORT_BY_HUMAN_TAG, ClientTagSorting.SORT_BY_HUMAN_SUBTAG ) )
        self._sort_order_count.setVisible( sort_type == ClientTagSorting.SORT_BY_COUNT )
        
        self._use_siblings.setVisible( self._show_siblings and sort_type != ClientTagSorting.SORT_BY_COUNT )
        self._group_by.setVisible( sort_type != ClientTagSorting.SORT_BY_HUMAN_SUBTAG )
        
    
    def _HandleValueChanged( self ):
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        sort_type = self._sort_type.GetValue()
        
        if sort_type == ClientTagSorting.SORT_BY_COUNT:
            
            sort_order = self._sort_order_count.GetValue()
            
        else:
            
            sort_order = self._sort_order_text.GetValue()
            
        
        tag_sort = ClientTagSorting.TagSort(
            sort_type = sort_type,
            sort_order = sort_order,
            use_siblings = self._use_siblings.GetValue(),
            group_by = self._group_by.GetValue()
        )
        
        return tag_sort
        
    
    def SetValue( self, tag_sort: ClientTagSorting.TagSort ):
        
        self._sort_type.blockSignals( True )
        self._sort_order_text.blockSignals( True )
        self._sort_order_count.blockSignals( True )
        self._use_siblings.blockSignals( True )
        self._group_by.blockSignals( True )
        
        self._sort_type.SetValue( tag_sort.sort_type )
        
        if tag_sort.sort_type == ClientTagSorting.SORT_BY_COUNT:
            
            self._sort_order_count.SetValue( tag_sort.sort_order )
            
        else:
            
            self._sort_order_text.SetValue( tag_sort.sort_order )
            
        
        self._use_siblings.SetValue( tag_sort.use_siblings )
        self._group_by.SetValue( tag_sort.group_by )
        
        self._sort_type.blockSignals( False )
        self._sort_order_text.blockSignals( False )
        self._sort_order_count.blockSignals( False )
        self._use_siblings.blockSignals( False )
        self._group_by.blockSignals( False )
        
        self._UpdateControlsAfterSortTypeChanged()
        
        self._HandleValueChanged()
        
    
