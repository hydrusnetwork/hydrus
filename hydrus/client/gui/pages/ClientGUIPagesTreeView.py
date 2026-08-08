from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.client.gui.pages import ClientGUIPagesTreeModel
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTime
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton

class TabBar( QW.QTabBar ):
    
    tabDoubleLeftClicked = QC.Signal( int )
    tabMiddleClicked = QC.Signal( int )
    
    tabSpaceDoubleLeftClicked = QC.Signal()
    tabSpaceDoubleMiddleClicked = QC.Signal()
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        if HC.PLATFORM_MACOS:
            
            self.setDocumentMode( True )
            
        
        self.setMouseTracking( True )
        self.setAcceptDrops( True )
        self._supplementary_drop_target = None
        
        self._last_clicked_tab_index = -1
        self._last_clicked_global_pos = None
        self._last_clicked_timestamp_ms = 0
        
    
    def AddSupplementaryTabBarDropTarget( self, drop_target ):
        
        self._supplementary_drop_target = drop_target
        
    
    def clearLastClickedTabInfo( self ):
        
        self._last_clicked_tab_index = -1
        
        self._last_clicked_global_pos = None
        
        self._last_clicked_timestamp_ms = 0
        
    
    def event( self, event ):
        
        return QW.QTabBar.event( self, event )
        
    
    def mouseMoveEvent( self, e ):
        
        e.ignore()
        
    
    def mousePressEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            self._last_clicked_tab_index = index
            
            self._last_clicked_global_pos = event.globalPosition().toPoint()
            
            self._last_clicked_timestamp_ms = HydrusTime.GetNowMS()
            
        
        QW.QTabBar.mousePressEvent( self, event )
        
    
    def mouseReleaseEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.MouseButton.MiddleButton:
            
            if index != -1:
                
                self.tabMiddleClicked.emit( index )
                
                return
                
            
        
        QW.QTabBar.mouseReleaseEvent( self, event )
        
    
    def mouseDoubleClickEvent( self, event ):
        
        index = self.tabAt( event.position().toPoint() )
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            if index == -1:
                
                self.tabSpaceDoubleLeftClicked.emit()
                
            else:
                
                self.tabDoubleLeftClicked.emit( index )
                
            
            return
            
        elif event.button() == QC.Qt.MouseButton.MiddleButton:
            
            if index == -1:
                
                self.tabSpaceDoubleMiddleClicked.emit()
                
            else:
                
                self.tabMiddleClicked.emit( index )
                
            
            return
            
        
        QW.QTabBar.mouseDoubleClickEvent( self, event )
        
    
    def dragEnterEvent(self, event):

        if 'application/hydrus-tab' in event.mimeData().formats():
            
            event.ignore()
            
        else:
            
            event.accept()
            
        
    
    def dragMoveEvent( self, event ):
        
        if 'application/hydrus-tab' not in event.mimeData().formats():
            
            tab_index = self.tabAt( event.position().toPoint() )
            
            if tab_index != -1:
                
                shift_down = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
                
                if shift_down:
                    
                    do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_with_shift' )
                    
                else:
                    
                    do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_normally' )
                    
                
                if do_navigate:
                    
                    self.parentWidget().setCurrentIndex( tab_index )
                    
                
            
        else:
            
            event.ignore()
            
        
    
    def lastClickedTabInfo( self ):
        
        return ( self._last_clicked_tab_index, self._last_clicked_global_pos, self._last_clicked_timestamp_ms )
        
    
    def dropEvent( self, event ):
        
        if self._supplementary_drop_target:
            
            self._supplementary_drop_target.eventFilter( self, event )
            
        else:
            
            event.ignore()
            
        
    
    def wheelEvent( self, event ):
        
        try:
            
            if CG.client_controller.new_options.GetBoolean( 'wheel_scrolls_tab_bar' ):
                
                children = self.children()
                
                if len( children ) >= 2:
                    
                    scroll_left = children[0]
                    scroll_right = children[1]
                    
                    if event.angleDelta().y() > 0:
                        
                        b = scroll_left
                        
                    else:
                        
                        b = scroll_right
                        
                    
                    if isinstance( b, QW.QAbstractButton ):
                        
                        b.click()
                        
                    
                
                event.accept()
                
                return
                
            
        except Exception as e:
            
            pass
            
        
        QW.QTabBar.wheelEvent( self, event )
        
    

# A heavily extended/tweaked version of https://forum.qt.io/topic/67542/drag-tabs-between-qtabwidgets/
class TabWidgetWithDnD( QW.QTabWidget ):
    
    pageDragAndDropped = QC.Signal( QW.QWidget, QW.QWidget )
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self.setTabBar( TabBar( self ) )
        
        self.setAcceptDrops( True )
        
        self._tab_bar = self.tabBar()
        
        self._my_current_drag_object = None
        
        self._supplementary_drop_target = None
        
    
    def _CheckDnDIsOK( self, drag_object ):
        
        # drag.cancel is not supported on macOS
        if HC.PLATFORM_MACOS:
            
            return
            
        
        # QW.QApplication.mouseButtons() doesn't work unless mouse is over!
        if not ClientGUIFunctions.MouseIsOverOneOfOurWindows():
            
            return
            
        
        if self._my_current_drag_object == drag_object and QW.QApplication.mouseButtons() != QC.Qt.MouseButton.LeftButton:
            
            # awkward situation where, it seems, the DnD is spawned while the 'release left-click' event is in the queue
            # the DnD spawns after the click release and sits there until the user clicks again
            # I think this is because I am spawning the DnD in the move event rather than the mouse press
            
            self._my_current_drag_object.cancel()
            
            self._my_current_drag_object = None
            
        
    
    def _LayoutPagesHelper( self ):
        
        current_index = self.currentIndex()

        for i in range( self.count() ):
            
            self.setCurrentIndex( i )
            
            widget = self.widget( i )
            
            if isinstance( widget, TabWidgetWithDnD ):
                
                widget._LayoutPagesHelper()
                
            
        
        self.setCurrentIndex( current_index )
        
    
    def LayoutPages( self ):
        
        # hydev adds: I no longer call this, as I moved splitter setting to a thing called per page when page is first visibly shown
        # leaving it here for now in case I need it again
        
        # Momentarily switch to each page, then back, forcing a layout update.
        # If this is not done, the splitters on the hidden pages won't resize their widgets properly when we restore
        # splitter sizes after this, since they would never became visible.
        # We first have to climb up the widget hierarchy and go down recursively from the root tab widget,
        # since it's not enough to make a page visible if its a nested page: all of its ancestor pages have to be visible too.
        # This shouldn't be visible to users since we switch back immediately.
        # There is probably a proper way to do this...

        highest_ancestor_of_same_type = self

        parent = self.parentWidget()

        while parent is not None:

            if isinstance( parent, TabWidgetWithDnD ):
                
                highest_ancestor_of_same_type = parent
                

            parent = parent.parentWidget()
            
        
        highest_ancestor_of_same_type._LayoutPagesHelper() # This does the actual recursive descent and making pages visible
        
    
    # This is a hack that adds an additional drop target to the tab bar. The added drop target will get drop events from the tab bar.
    # Used to make the case of files/media droppend onto tabs work.
    def AddSupplementaryTabBarDropTarget( self, drop_target ):
        
        self._supplementary_drop_target = drop_target
        # noinspection PyUnresolvedReferences
        self.tabBar().AddSupplementaryTabBarDropTarget( drop_target )
        
    
    def mouseMoveEvent( self, e ):
        
        mouse_is_over_actual_page = self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) )
        
        if mouse_is_over_actual_page or CG.client_controller.new_options.GetBoolean( 'disable_page_tab_dnd' ):
            
            QW.QTabWidget.mouseMoveEvent( self, e )
            
            return
            
        
        if e.buttons() != QC.Qt.MouseButton.LeftButton:
            
            return
            
        
        my_mouse_pos = e.position().toPoint()
        global_mouse_pos = self.mapToGlobal( my_mouse_pos )
        tab_bar_mouse_pos = self._tab_bar.mapFromGlobal( global_mouse_pos )
        
        if not self._tab_bar.rect().contains( tab_bar_mouse_pos ):
            
            return
            
        
        if not isinstance( self._tab_bar, TabBar ):
            
            return
            
        
        ( clicked_tab_index, clicked_global_pos, clicked_timestamp_ms ) = self._tab_bar.lastClickedTabInfo()
        
        if clicked_tab_index == -1:
            
            return
            
        
        # I used to do manhattanlength stuff, but tbh this works better
        # delta_pos = e.globalPosition().toPoint() - clicked_global_pos
        
        if not HydrusTime.TimeHasPassedMS( clicked_timestamp_ms + 100 ):
            
            # don't start a drag until decent movement
            
            return
            
        
        tab_rect = self._tab_bar.tabRect( clicked_tab_index )
        
        pixmap = QG.QPixmap( tab_rect.size() )
        self._tab_bar.render( pixmap, QC.QPoint(), QG.QRegion( tab_rect ) )
        
        mimeData = QC.QMimeData()
        
        mimeData.setData( 'application/hydrus-tab', b'' )
        
        self._my_current_drag_object = QG.QDrag( self._tab_bar )
        
        self._my_current_drag_object.setMimeData( mimeData )
        
        self._my_current_drag_object.setPixmap( pixmap )
        
        self._my_current_drag_object.setHotSpot( QC.QPoint( 0, 0 ) )
        
        # this puts the tab pixmap exactly where we picked it up, but it looks bad
        # self._my_current_drag_object.setHotSpot( tab_bar_mouse_pos - tab_rect.topLeft() )
        
        cursor = QG.QCursor( QC.Qt.CursorShape.ClosedHandCursor )
        
        self._my_current_drag_object.setDragCursor( cursor.pixmap(), QC.Qt.DropAction.MoveAction )
        
        CG.client_controller.CallLaterQtSafe( self, 0.1, 'checking DnD is ok', self._CheckDnDIsOK, self._my_current_drag_object )
        
        self._my_current_drag_object.exec_( QC.Qt.DropAction.MoveAction )
        
        self._my_current_drag_object = None
        
    
    def dragEnterEvent( self, e: QG.QDragEnterEvent ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ):
            
            return QW.QTabWidget.dragEnterEvent( self, e )
            
        
        if 'application/hydrus-tab' in e.mimeData().formats():
            
            e.accept()
            
        else:
            
            e.ignore()
            
        
    
    def dragMoveEvent( self, event: QG.QDragMoveEvent ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( event.position().toPoint() ) ) ): return QW.QTabWidget.dragMoveEvent( self, event )
        
        if 'application/hydrus-tab' not in event.mimeData().formats():
            
            event.ignore()
            
            return
            
        
        screen_pos = self.mapToGlobal( event.position().toPoint() )
        
        tab_pos = self._tab_bar.mapFromGlobal( screen_pos )
        
        tab_index = self._tab_bar.tabAt( tab_pos )
        
        if tab_index != -1:
            
            shift_down = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
            
            if shift_down:
                
                do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_with_shift' )
                
            else:
                
                do_navigate = CG.client_controller.new_options.GetBoolean( 'page_drag_change_tab_normally' )
                
            
            if do_navigate:
                
                self.setCurrentIndex( tab_index )
                
            
        

    def dragLeaveEvent( self, e: QG.QDragLeaveEvent ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ): return QW.QTabWidget.dragLeaveEvent( self, e )
        
        e.accept()
        

    def addTab(self, widget, *args, **kwargs ):
        
        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            
        
        QW.QTabWidget.addTab( self, widget, *args, **kwargs )
        
    
    def insertTab(self, index, widget, *args, **kwargs):

        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            

        QW.QTabWidget.insertTab( self, index, widget, *args, **kwargs )
        
    
    def dropEvent( self, e: QG.QDropEvent ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.position().toPoint() ) ) ):
            
            return QW.QTabWidget.dropEvent( self, e )
            
        
        if 'application/hydrus-tab' not in e.mimeData().formats(): #Page dnd has no associated mime data
            
            e.ignore()
            
            return
            
        
        w = self
        
        source_tab_bar = e.source()
        
        if not isinstance( source_tab_bar, TabBar ):
            
            return
            
        
        ( source_page_index, source_page_click_global_pos, source_page_clicked_timestamp_ms ) = source_tab_bar.lastClickedTabInfo()
        
        source_tab_bar.clearLastClickedTabInfo()
        
        source_notebook: TabWidgetWithDnD = source_tab_bar.parentWidget()
        source_page = source_notebook.widget( source_page_index )
        source_name = source_tab_bar.tabText( source_page_index )
        
        while w is not None:
            
            if source_page == w:
                
                # you cannot drop a page of pages inside itself
                
                return
                
            
            w = w.parentWidget()
            

        e.setDropAction( QC.Qt.DropAction.MoveAction )
        
        e.accept()
        
        counter = self.count()
        
        screen_pos = self.mapToGlobal( e.position().toPoint() )
        
        tab_pos = self.tabBar().mapFromGlobal( screen_pos )
        
        dropped_on_tab_index = self.tabBar().tabAt( tab_pos )
        
        if source_notebook == self and dropped_on_tab_index == source_page_index:
            
            return # if we drop on ourself, make no action, even on the right edge
            
        
        dropped_on_left_edge = False
        dropped_on_right_edge = False
        
        if dropped_on_tab_index != -1:
            
            EDGE_PADDING = 15
            
            tab_rect = self.tabBar().tabRect( dropped_on_tab_index )
            
            edge_size = QC.QSize( EDGE_PADDING, tab_rect.height() )
            
            left_edge_rect = QC.QRect( tab_rect.topLeft(), edge_size )
            right_edge_rect = QC.QRect( tab_rect.topRight() - QC.QPoint( EDGE_PADDING, 0 ), edge_size )
            
            drop_pos = e.position().toPoint()
            
            dropped_on_left_edge = left_edge_rect.contains( drop_pos )
            dropped_on_right_edge = right_edge_rect.contains( drop_pos )
            
        
        if counter == 0:
            
            self.addTab( source_page, source_name )
            
        else:
            
            if dropped_on_tab_index == -1:
                
                insert_index = counter
                
            else:
                
                insert_index = dropped_on_tab_index
                
                if dropped_on_right_edge:
                    
                    insert_index += 1
                    
                
                if self == source_notebook:
                    
                    if insert_index == source_page_index + 1 and not dropped_on_left_edge:
                        
                        pass # in this special case, moving it confidently one to the right, we will disobey the normal rules and indeed move one to the right, rather than no-op
                        
                    elif insert_index > source_page_index:
                        
                        # we are inserting to our right, which needs a shift since we will be removing ourselves from the list
                        
                        insert_index -= 1
                        
                    
                
            
            if source_notebook == self and insert_index == source_page_index:
                
                return # if we mean to insert on ourself, make no action
                
            
            self.insertTab( insert_index, source_page, source_name )

            shift_down = e.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
            
            follow_dropped_page = not shift_down

            new_options = CG.client_controller.new_options
            
            if shift_down:
                
                follow_dropped_page = new_options.GetBoolean( 'page_drop_chase_with_shift' )
                
            else:
                
                follow_dropped_page = new_options.GetBoolean( 'page_drop_chase_normally' )
                
            
            if follow_dropped_page:
                
                self.setCurrentIndex( self.indexOf( source_page ) )
                
            else:
                
                if source_page_index > 1:
                    
                    neighbour_page = source_notebook.widget( source_page_index - 1 )
                    
                    # TODO: Probably ditch this for signals somehow
                    # noinspection PyUnresolvedReferences
                    page_key = neighbour_page.GetPageKey()
                    
                else:
                    
                    # TODO: Probably ditch this for signals somehow
                    # noinspection PyUnresolvedReferences
                    page_key = source_notebook.GetPageKey()
                    
                
                CG.client_controller.CallAfterQtSafe( self, CG.client_controller.gui.ShowPage, page_key )
                
            
        
        self.pageDragAndDropped.emit( source_page, source_tab_bar )
        
    

class TreeViewRowHeightDelegate( QW.QStyledItemDelegate ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._row_height = 20
        
    
    def SetRowHeight( self, row_height: int ):
        
        self._row_height = row_height
        
    
    def sizeHint( self, option: QW.QStyleOptionViewItem, index: QC.QModelIndex ) -> QC.QSize:
        
        size_hint = super().sizeHint( option, index )
        
        size_hint.setHeight( self._row_height )
        
        return size_hint
        
    

# TODO: THIS WHOLE THING IS A MESS OF FIVE DIFFERENT REWRITES, it needs a good look and cleanup and perhaps pulling into different pieces
# Base tree view that uses a PagesNotebookTreeModel( QC.QAbstractItemModel ) to allow more control over pages/notebooks
class TreeViewWithDnD( QW.QTreeView ):
    
    leafDragAndDropped = QC.Signal( QW.QWidget, QW.QWidget )
    currentPagePathChanged = QC.Signal( str )
    currentPageNameChanged = QC.Signal( str, str )
    emptySpaceDoubleLeftClicked = QC.Signal()
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        self._row_height_delegate = TreeViewRowHeightDelegate( self )
        
        self.setItemDelegate( self._row_height_delegate )
        self.setUniformRowHeights( True )
        self.setIndentation( CG.client_controller.new_options.GetInteger( 'treeview_indentation' ) )
        self.SetRowHeight( CG.client_controller.new_options.GetInteger( 'treeview_row_height' ) )
        
        self.setHeaderHidden( True )
        self.setAlternatingRowColors( CG.client_controller.new_options.GetBoolean( 'treeview_alternating_row_colours' ) )
        
        self.setContextMenuPolicy( QC.Qt.ContextMenuPolicy.CustomContextMenu )
        
        self.customContextMenuRequested.connect( self._ShowContextMenu )
        
        self.setDragEnabled( True )
        self.setAcceptDrops( True )
        self.setDropIndicatorShown( True )
        self.setDragDropMode( QW.QAbstractItemView.DragDropMode.InternalMove )
        self.setDefaultDropAction( QC.Qt.DropAction.MoveAction )
        
        self.setSelectionBehavior( QW.QAbstractItemView.SelectionBehavior.SelectRows )
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        self._saved_expanded_node_keys = set()
        self._saved_current_node_key = None
        
        self._filter_text = ''
        
        self.collapsed.connect( self._OnTreeCollapsed )
        self.expanded.connect( self._OnTreeExpanded )
        
        self.activated.connect( self._OnTreeActivated )
        self.doubleClicked.connect( self._OnTreeActivated )
        
    
    def model( self ) -> ClientGUIPagesTreeModel.PagesNotebookTreeModel:
        
        return super().model()
        
    
    def setModel( self, model: ClientGUIPagesTreeModel.PagesNotebookTreeModel ):
        
        old_model = self.model()
        
        if old_model is not None:
            
            try:
                
                old_model.modelReset.disconnect( self._ModelResetReapplyFilter )
                
            except Exception as e:
                
                pass
                
            
        
        super().setModel( model )
        
        if model is not None:
            
            model.modelReset.connect( self._ModelResetReapplyFilter )
            
        
    
    def SetRowHeight( self, row_height: int ):
    
        self._row_height_delegate.SetRowHeight( row_height )
        self.doItemsLayout()
        self.viewport().update()
        
    
    def _EmitCurrentIndexText( self, index: QC.QModelIndex ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        full_name = model.GetFullNameFromIndex( index )
        
        if hasattr( model, 'GetPageNameAndTooltipFromIndex' ):
            
            page_name, tooltip = model.GetPageNameAndTooltipFromIndex( index )
            
        else:
            
            page_name = full_name
            tooltip = full_name
            
        
        self.currentPagePathChanged.emit( full_name )
        self.currentPageNameChanged.emit( page_name, tooltip )
        
    
    def _ApplyFilterToParent( self, parent: QC.QModelIndex ) -> bool:
        
        model = self.model()
        
        if model is None:
            
            return False
            
        
        any_visible = False
        
        for row in range( model.rowCount( parent ) ):
            
            index = model.index( row, 0, parent )
            
            if not index.isValid():
                
                continue
                
            
            child_visible = self._ApplyFilterToParent( index )
            
            text = model.data( index, QC.Qt.ItemDataRole.DisplayRole )
            text_matches = self._filter_text == '' or self._filter_text in str( text or '' ).casefold()
            
            visible = text_matches or child_visible
            
            self.setRowHidden( row, parent, not visible )
            
            if visible:
                
                any_visible = True
                
            
        
        return any_visible
        
    
    def _CollapseAllChildren( self, parent: QC.QModelIndex ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        for row in range( model.rowCount( parent ) ):
            
            child = model.index( row, 0, parent )
            
            if not child.isValid():
                
                continue
                
            
            self._CollapseAllChildren( child )
            self.collapse( child )
            
        
    
    def _EmitCurrentPageText( self, index: QC.QModelIndex ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        full_name = ''
        page_name = ''
        tooltip = ''
        
        if hasattr( model, 'GetFullNameFromIndex' ):
            
            full_name = model.GetFullNameFromIndex( index )
            
        
        if hasattr( model, 'GetPageNameAndTooltipFromIndex' ):
            
            page_name, tooltip = model.GetPageNameAndTooltipFromIndex( index )
            
        else:
            
            page_name = full_name
            tooltip = full_name
            
        
        self.currentPagePathChanged.emit( full_name )
        self.currentPageNameChanged.emit( page_name, tooltip )
        
    
    def _ExpandAncestors( self, index: QC.QModelIndex ):
        
        parents = []
        parent = index.parent()
        
        while parent.isValid():
            
            parents.append( parent )
            parent = parent.parent()
            
        
        for parent in reversed( parents ):
            
            self.expand( parent )
            
        
    
    def _ModelResetReapplyFilter( self ):
        
        QC.QTimer.singleShot( 0, self.ReapplyFilter )
        
    
    def _OnTreeActivated( self, index: QC.QModelIndex ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        page_key = model.GetPageKeyFromIndex( index )
        
        if page_key is not None:
            
            CG.client_controller.gui.ShowPage( page_key )
            
        
    
    def _OnTreeExpanded( self, index: QC.QModelIndex ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        node_key = model.GetNodeKeyFromIndex( index )
        
        if node_key is not None:
            
            self._saved_expanded_node_keys.add( node_key )
            
        
    
    def _OnTreeCollapsed( self, index: QC.QModelIndex ):
        
        model = self.model()
        
        if model is not None:
            
            node_key = model.GetNodeKeyFromIndex( index )
            
            if node_key is not None:
                
                self._saved_expanded_node_keys.discard( node_key )
                
            
        
        if CG.client_controller.new_options.GetBoolean( 'treeview_collapse_all_children_upon_parent_closed' ):
            
            self._CollapseAllChildren( index )
            
        
    
    def _SetCurrentIndex( self, index: QC.QModelIndex, scroll = True ):
        
        if not index.isValid():
            
            return
            
        
        self._ExpandAncestors( index )
        self.setCurrentIndex( index )
        
        selection_model = self.selectionModel()
        
        if selection_model is not None:
            
            selection_model.select(
                index,
                QC.QItemSelectionModel.SelectionFlag.ClearAndSelect |
                QC.QItemSelectionModel.SelectionFlag.Rows
            )
            
        
        self._EmitCurrentIndexText( index )
        
    
    def _SelectIndex( self, index: QC.QModelIndex, scroll = True ):
        
        if not index.isValid():
            
            return
            
        
        self._ExpandAncestors( index )
        self._SetCurrentIndex( index )
        
        if scroll:
            
            self.scrollTo( index, QW.QAbstractItemView.ScrollHint.PositionAtCenter )
            
        
    
    def _ShowContextMenu( self, point ):
        
        index = self.indexAt( point )
        
        if not index.isValid():
            
            return
            
        
        model = self.model()
        
        kind = model.GetKindFromIndex( index )
        
        if kind not in ( 'page', 'notebook' ):
            
            return
            
        
        page_key = model.GetPageKeyFromIndex( index )
        notebook = model.GetParentNotebookFromIndex( index )
        
        notebook.ShowMenuForPageKey( page_key )
        
    
    def mouseDoubleClickEvent( self, event ):
        
        index = self.indexAt( event.position().toPoint() )
        
        if ( event.button() == QC.Qt.MouseButton.LeftButton and not index.isValid() ):
            
            self.emptySpaceDoubleLeftClicked.emit()
            
            event.accept()
            
            return
            
        
        QW.QTreeView.mouseDoubleClickEvent( self, event )
        
    
    def SelectLeafFromNotebookPage( self, notebook, tab_index ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        parent_index = model._FindNotebookIndex( notebook )
        index = model.index( tab_index, 0, parent_index )
        
        if index.isValid():
            
            self._SetCurrentIndex( index )
            
        
    
    def RevealCurrentSelection( self ):
        
        current_page_index = self.model().FindIndexForPageKey( CG.client_controller.gui.GetCurrentPage().GetPageKey() )
        
        if current_page_index.isValid():
            
            self._SelectIndex( current_page_index, scroll = True )
            
        
    
    def SaveState( self ):
        
        model = self.model()
        
        if model is None:
            
            self._saved_current_node_key = None
            
            return
            
        
        self._saved_current_node_key = model.GetNodeKeyFromIndex( self.currentIndex() )
        
    
    def RestoreState( self ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        node_keys = getattr( self, '_saved_expanded_node_keys', set() ) or set()
        
        stack = [ QC.QModelIndex() ]
        
        while stack:
            
            parent = stack.pop()
            
            for row in range( model.rowCount( parent ) ):
                
                index = model.index( row, 0, parent )
                
                if not index.isValid():
                    
                    continue
                    
                
                node_key = model.GetNodeKeyFromIndex( index )
                
                if node_key is not None and node_key in node_keys:
                    
                    self.expand( index )
                    
                
                stack.append( index )
                
            
        
        current_node_key = getattr( self, '_saved_current_node_key', None )
        
        if current_node_key is not None and hasattr( model, 'FindIndexForNodeKey' ):
            
            current_index = model.FindIndexForNodeKey( current_node_key )
            
            if current_index.isValid():
                
                self._SetCurrentIndex( current_index )
                
                if CG.client_controller.new_options.GetBoolean( 'treeview_always_expand_to_current_tab_after_reset' ):
                    
                    self.RevealCurrentSelection()
                    
                
            
        
        self.ReapplyFilter()
        
    
    def SetFilterText( self, text: str ):
        
        self._filter_text = str( text ).strip().casefold()
        
        self.ReapplyFilter()
        
    
    def ClearFilterText( self ):
        
        self.SetFilterText( '' )
        
    
    def ReapplyFilter( self ):
        
        model = self.model()
        
        if model is None:
            
            return
            
        
        self._ApplyFilterToParent( QC.QModelIndex() )
        
    

class FilterPanel( QW.QWidget ):
    
    iWantToClose = QC.Signal()
    clearFilter = QC.Signal()
    setFilterText = QC.Signal( str )
    expandVisibleFilterResults = QC.Signal()
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent, QC.Qt.WindowType.Tool | QC.Qt.WindowType.FramelessWindowHint )
        self.setObjectName( 'HydrusTreeViewFilterPanel' )
        self.hide()
        
        hbox = QW.QHBoxLayout( self )
        hbox.setContentsMargins( 4, 4, 4, 4 )
        hbox.setSpacing( 2 )
        
        self._text_entry = QW.QLineEdit( self )
        self._text_entry.setPlaceholderText( 'filter pages' )
        self._text_entry.textChanged.connect( self._TextChanged )
        
        self._expand_button = QW.QPushButton( '+', self )
        self._expand_button.setEnabled( False )
        self._expand_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand all currently visible matches' ) )
        self._expand_button.clicked.connect( self.expandVisibleFilterResults )
        
        self._clear_button = QW.QPushButton( 'X', self )
        self._clear_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Clear filter' ) )
        self._clear_button.clicked.connect( self._Clear )
        
        hbox.addWidget( self._text_entry )
        hbox.addWidget( self._expand_button )
        hbox.addWidget( self._clear_button )
        
    
    def _Clear( self ):
        
        self._text_entry.clear()
        
        self.clearFilter.emit()
        
        self.iWantToClose.emit()
        
    
    def _TextChanged( self, text: str ):
        
        self._expand_button.setEnabled( len( text ) >= 2 )
        
        self.setFilterText.emit( text )
        
    
    def HasText( self ):
        
        return self._text_entry.text() != ''
        
    
    def TakeFocus( self ):
        
        self._text_entry.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    

class HistoryPanel( QW.QWidget ):
    
    iWantToClose = QC.Signal()
    iNeedAReposition = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, model: ClientGUIPagesTreeModel.PagesNotebookTreeModel ):
        
        super().__init__( parent, QC.Qt.WindowType.Tool | QC.Qt.WindowType.FramelessWindowHint )
        self.setObjectName( 'HydrusTreeViewHistoryPanel' )
        
        self._model = model
        
        self.setMinimumWidth( 260 )
        self.setMinimumHeight( 120 )
        self.hide()
        
        vbox = QW.QVBoxLayout( self )
        vbox.setContentsMargins( 4, 4, 4, 4 )
        vbox.setSpacing( 2 )
        
        self._title = QW.QLabel( 'Tab History', self )
        self._title.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._scroll_area = QW.QScrollArea( self )
        self._scroll_area.setWidgetResizable( True )
        self._scroll_area.setVerticalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAsNeeded )
        
        self._page_list = QW.QWidget( self._scroll_area )
        self._page_list_layout = QW.QVBoxLayout( self._page_list )
        self._page_list_layout.setContentsMargins( 0, 0, 0, 0 )
        self._page_list_layout.setSpacing( 1 )
        self._page_list_layout.addStretch( 1 )
        
        self._scroll_area.setWidget( self._page_list )
        
        self._button_bar = QW.QWidget( self )
        bar = QW.QHBoxLayout( self._button_bar )
        bar.setContentsMargins( 0, 0, 0, 0 )
        bar.setSpacing( 2 )
        
        self._close_button = QW.QPushButton( 'X', self._button_bar )
        self._close_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Close history' ) )
        self._close_button.clicked.connect( self.iWantToClose )
        
        self._pin_button = QW.QPushButton( '', self._button_bar )
        self._pin_button.setCheckable( True )
        self._pin_button.setChecked( CG.client_controller.new_options.GetBoolean( 'treeview_history_box_pinned' ) )
        self._pin_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Keep history box open' ) )
        self._pin_button.toggled.connect( self._PinChanged )
        self._SetPinIcon()
        
        self._size_grip = QW.QSizeGrip( self )
        bar.addWidget( self._close_button )
        bar.addWidget( self._pin_button )
        bar.addStretch( 1 )
        bar.addWidget( self._size_grip )
        
        vbox.addWidget( self._title )
        vbox.addWidget( self._scroll_area, 1 )
        vbox.addWidget( self._button_bar )
        
    
    def _ActivatePage( self, page_key ):
        
        CG.client_controller.gui.ShowPage( page_key )
        
        if not CG.client_controller.new_options.GetBoolean( 'treeview_history_box_pinned' ):
            
            self.iWantToClose.emit()
            
        
    
    def _ClearPageList( self ):
        
        while self._page_list_layout.count() > 0:
            
            item = self._page_list_layout.takeAt( 0 )
            
            widget = item.widget()
            
            if widget is not None:
                
                widget.deleteLater()
                
            
        
    
    def _CreatePageRow( self, history_index: int, page_key ):
        
        ( page_name, tooltip ) = self._model.GetPageNameAndTooltipFromPageKey( page_key )
        page_name = HydrusText.ElideText( page_name, 100, elide_center = True )
        
        row = QW.QWidget( self._page_list )
        hbox = QW.QHBoxLayout( row )
        hbox.setContentsMargins( 0, 0, 0, 0 )
        hbox.setSpacing( 2 )
        
        number = QW.QLabel( f'{history_index + 1}.', row )
        number.setToolTip( tooltip )
        
        button = QW.QPushButton( page_name, row )
        button.setToolTip( tooltip )
        button.setFlat( True )
        button.clicked.connect( lambda checked = False, page_key = page_key: self._ActivatePage( page_key ) )
        
        remove = QW.QPushButton( 'X', row )
        remove.setToolTip( ClientGUIFunctions.WrapToolTip( 'Remove this page from history' ) )
        remove.clicked.connect( lambda checked = False, page_key = page_key: self._RemovePage( page_key ) )
        
        hbox.addWidget( number )
        hbox.addWidget( button, 1 )
        hbox.addWidget( remove )
        
        return row
        
    
    def _PinChanged( self, value: bool ):
        
        CG.client_controller.new_options.SetBoolean( 'treeview_history_box_pinned', value )
        
        self._SetPinIcon()
        
    
    def _RemovePage( self, page_key ):
        
        CG.client_controller.gui.page_nav_history.RemovePageKey( page_key )
        
        self.Repopulate()
        
        self.iNeedAReposition.emit()
        
    
    def _ResizeToRows( self, num_rows: int ):
        
        num_rows = max( 1, num_rows )
        visible_rows = min( 10, num_rows )
        
        row_height = 24
        
        for i in range( self._page_list_layout.count() ):
            
            item = self._page_list_layout.itemAt( i )
            widget = item.widget()
            
            if widget is not None:
                
                row_height = max( row_height, widget.sizeHint().height() )
                
            
        
        margins = self.layout().contentsMargins()
        spacing = self.layout().spacing()
        
        title_height = self._title.sizeHint().height()
        bar_height = self._button_bar.sizeHint().height()
        scroll_height = ( row_height * visible_rows ) + 8
        
        self._scroll_area.setMinimumHeight( scroll_height )
        
        target_height = (
            margins.top() +
            margins.bottom() +
            title_height +
            bar_height +
            scroll_height +
            ( spacing * 2 )
        )
        
        self.resize( max( self.width(), 260 ), target_height )
        
        self.iNeedAReposition.emit()
        
    
    def _SetPinIcon( self ):
        
        if self._pin_button.isChecked():
            
            self._pin_button.setIcon( CC.global_icons().lock )
            
        else:
            
            self._pin_button.setIcon( CC.global_icons().lock_open )
            
        
    
    def IsPinned( self ):
        
        return self._pin_button.isChecked()
        
    
    def Repopulate( self ):
        
        self._ClearPageList()
        
        self._pin_button.setChecked( CG.client_controller.new_options.GetBoolean( 'treeview_history_box_pinned' ) )
        
        history = CG.client_controller.gui.GetPagesHistory()
        
        if len( history ) == 0:
            
            self._title.setText( 'Tab History' )
            
            label = QW.QLabel( 'no page history', self._page_list )
            label.setWordWrap( True )
            self._page_list_layout.addWidget( label )
            self._page_list_layout.addStretch( 1 )
            self._ResizeToRows( 1 )
            return
            
        
        self._title.setText( f'Tab History ({len(history)} pages)' )
        
        row_count = 0
        
        for history_index, ( page_key, page_name ) in enumerate( reversed( history ) ):
            
            row = self._CreatePageRow( history_index, page_key )
            
            if row is not None:
                
                row_count += 1
                self._page_list_layout.addWidget( row )
                
            
        
        self._page_list_layout.addStretch( 1 )
        self._ResizeToRows( row_count )
        
    

# TODO: Although this guy adds some neat features, it ultimately increases the coupling problem
# If we want a modular future, we want to drag the splitters out of the panels to a LayoutOverseer and all subcomponents need to be their own clear thing

# TODO: when you go through an options cycle, this guy shrinks in width width, so some layout flag is missing maybe?
class TreeViewWithControls( QW.QWidget ):
    
    widgetAlignmentChanged = QC.Signal()
    tagBarAlignmentChanged = QC.Signal()
    tabBarVisibilityChanged = QC.Signal()
    treeSidebarCollapsibilityChanged = QC.Signal()
    
    def __init__( self, tree: TreeViewWithDnD, parent = None, on_toggle_alignment = None ):
        
        super().__init__( parent )
        
        self._on_toggle_alignment = on_toggle_alignment
        
        self._tree = tree
        self._current_depth = 2
        
        self._controls_at_top = CG.client_controller.new_options.GetBoolean( 'treeview_controls_at_top' )
        self._panel_at_top = CG.client_controller.new_options.GetBoolean( 'treeview_expanding_panel_at_top' )
        
        #
        
        self._controls = QW.QWidget( self )
        self._controls_layout = QW.QHBoxLayout( self._controls )
        self._controls_layout.setContentsMargins( 0, 0, 0, 0 ) 
        self._controls_layout.setSpacing( 2 )
        
        #
        
        self.collapse_all = ClientGUICommon.IconButton( self, CC.global_icons().position_first, lambda: self.expandToDepth( -1 ) )
        self.collapse_all.setToolTip( ClientGUIFunctions.WrapToolTip( 'Collapse all' ) )
        
        self.depth_decrement = ClientGUICommon.IconButton( self, CC.global_icons().position_previous, lambda: self.expandToDepth( self._current_depth - 1 ) )
        self.depth_decrement.setToolTip( ClientGUIFunctions.WrapToolTip( 'Collapse to one less than last' ) )
        
        # depth_1 = QW.QPushButton( '1', self._controls )
        # depth_1.clicked.connect( lambda: self.expandToDepth( 0 ) )
        # depth_1.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand to depth 1' ) )
        
        # depth_2 = QW.QPushButton( '2', self._controls )
        # depth_2.clicked.connect( lambda: self.expandToDepth( 1 ) )
        # depth_2.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand to depth 2' ) )
        
        # depth_3 = QW.QPushButton( '3', self._controls )
        # depth_3.clicked.connect( lambda: self.expandToDepth( 2 ) )
        # depth_3.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand to depth 3' ) )
        
        self.depth_increment = ClientGUICommon.IconButton( self._controls, CC.global_icons().position_next, lambda: self.expandToDepth( self._current_depth + 1 ) )
        self.depth_increment.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand to one more than last' ) )
        
        self.expand_all = ClientGUICommon.IconButton( self._controls, CC.global_icons().position_last, lambda: self.expandToDepth( self._tree.model().GetViewDepth() ) )
        self.expand_all.setToolTip( ClientGUIFunctions.WrapToolTip( 'Expand all' ) )
        
        self._filter_button = ClientGUICommon.IconButton( self._controls, CC.global_icons().zoom_switch, self._ToggleFilterPanel )
        self._filter_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Filter page tree' ) )
        
        self._history_button = ClientGUICommon.IconButton( self._controls, CC.global_icons().page_of_pages, self._ToggleHistoryPanel )
        self._history_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show page history' ) )
        
        #
        
        self._current_page_path = QW.QLabel( '', self._controls )
        self._current_page_path.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Sunken )
        self._current_page_path.setToolTip( ClientGUIFunctions.WrapToolTip( 'Current page' ) )
        self._current_page_path.setSizePolicy( QW.QSizePolicy.Policy.Ignored, QW.QSizePolicy.Policy.Preferred )
        self._current_page_path.setCursor( QC.Qt.CursorShape.PointingHandCursor )
        self._current_page_path.mousePressEvent = self._CurrentPagePathClicked
        
        if hasattr( self._tree, 'currentPageNameChanged' ):
            
            self._tree.currentPageNameChanged.connect( self._SetCurrentPagePathText )
            self._tree.currentPagePathChanged.connect( self.PopulateHistoryIfOpen )
            
        elif hasattr( self._tree, 'currentPagePathChanged' ):
            
            self._tree.currentPagePathChanged.connect( self._current_page_path.setText )
            self._tree.currentPagePathChanged.connect( self.PopulateHistoryIfOpen )
            
        
        self._controls_button = ClientGUIMenuButton.CogIconButton( self._controls, self._GetCogMenuTemplateItems() )
        self._controls_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Tree view controls' ) )
        
        #
        
        self._filter_panel = FilterPanel( self )
        
        self._filter_panel.iWantToClose.connect( self._HideFilterPanel )
        self._filter_panel.expandVisibleFilterResults.connect( self._tree.expandAll )
        self._filter_panel.clearFilter.connect( self._tree.ClearFilterText )
        self._filter_panel.setFilterText.connect( self._tree.SetFilterText )
        
        self._history_panel = HistoryPanel( self, self._tree.model() )
        
        self._history_panel.iWantToClose.connect( self._HideHistoryPanel )
        self._history_panel.iNeedAReposition.connect( self._QueueFloatingPanelReposition )
        
        selection_model = self._tree.selectionModel()
        
        if selection_model is not None:
            
            selection_model.currentChanged.connect( self._TreeCurrentChanged )
            
        
        self._expanding_panel_splitter = QW.QSplitter( QC.Qt.Orientation.Vertical )
        
        if self._panel_at_top:
            #self._expanding_panel_splitter.addWidget( self._expanding_panel )
            self._expanding_panel_splitter.addWidget( self._tree )
            
        else:
            self._expanding_panel_splitter.addWidget( self._tree )
            #self._expanding_panel_splitter.addWidget( self._expanding_panel )
        
        self._expanding_panel_splitter.setSizes( CG.client_controller.new_options.GetIntegerList( 'treeview_expanding_panel_splitter_size' ) )
        self._expanding_panel_splitter.splitterMoved.connect( self._SplitterSizeChanged )
        
        #
        
        # self._controls_layout.addWidget( depth_1 )
        # self._controls_layout.addWidget( depth_2 )
        # self._controls_layout.addWidget( depth_3 )
        self._controls_layout.addWidget( self.collapse_all )
        self._controls_layout.addWidget( self.depth_decrement )
        self._controls_layout.addWidget( self.depth_increment )
        self._controls_layout.addWidget( self.expand_all )
        
        self._controls_layout.addWidget( self._filter_button )
        self._controls_layout.addWidget( self._history_button )
        
        self._controls_layout.addWidget( self._current_page_path, 1 )
        
        self._controls_layout.addWidget( self._controls_button )
        
        self._vbox = QW.QVBoxLayout( self )
        self._vbox.setContentsMargins( 0, 0, 0, 0 )
        self._vbox.setSpacing( 2 )
        
        if self._controls_at_top:
            
            self._vbox.addWidget( self._controls )
            self._vbox.addWidget( self._expanding_panel_splitter )
            
        else:
            
            self._vbox.addWidget( self._expanding_panel_splitter )
            self._vbox.addWidget( self._controls )
            
        
        app = QW.QApplication.instance()
        
        if app is not None:
            
            if isinstance( app, QG.QGuiApplication ):
                
                app.focusObjectChanged.connect( self.ApplicationFocusChangingUpdate )
                
            
        
        self._queued_floating_panel_reposition = False
        
    
    def _CurrentPagePathClicked( self, event ):
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            if hasattr( self._tree, 'RevealCurrentSelection' ):
                
                self._tree.RevealCurrentSelection()
                
            
            event.accept()
            return
            
        
        if event.button() == QC.Qt.MouseButton.RightButton:
            
            if hasattr( self._tree, 'ShowContextMenuForCurrentSelection' ):
                
                self._tree.ShowContextMenuForCurrentSelection()
                
            
            event.accept()
            return
            
        
        event.ignore()
        
    
    def _EmitAlignmentToggle( self, direction: int ):
        
        CG.client_controller.new_options.SetNoneableInteger( 'treeview_alignment', direction )
        
        self.widgetAlignmentChanged.emit()
        
        if self._on_toggle_alignment is not None:
            
            self._on_toggle_alignment( direction )
            
        
    
    def _EmitTagViewAlignmentToggle( self, direction: int ):
        
        CG.client_controller.new_options.SetInteger( 'page_sidebar_alignment', direction )
        
        self.tagBarAlignmentChanged.emit()
        
    
    def _GetDepthFromIndex( self, index: QC.QModelIndex ) -> int:
        
        if not index.isValid():
            
            return -1
            
        
        depth = 0
        parent = index.parent()
        
        while parent.isValid():
            
            depth += 1
            parent = parent.parent()
            
        
        return depth
        
    
    def _GetEventGlobalPos( self, event ):
        
        if hasattr( event, 'globalPosition' ):
            
            return event.globalPosition().toPoint()
            
        
        return event.globalPos()
        
    
    def _GlobalPointInsideWidget( self, global_pos, widget ) -> bool:
        
        if widget is None or not widget.isVisible():
            
            return False
            
        
        top_left = widget.mapToGlobal( widget.rect().topLeft() )
        rect = QC.QRect( top_left, widget.rect().size() )
        
        return rect.contains( global_pos )
        
    
    def _HideFilterPanel( self ):
        
        self._filter_panel.hide()
        self._QueueFloatingPanelReposition()
        
    
    def _HideHistoryPanel( self ):
        
        self._history_panel.hide()
        self._QueueFloatingPanelReposition()
        
    
    def _MoveControlBarUp( self ):
        
        if self._controls_at_top:
            return
            
        self._vbox.removeWidget( self._controls )
        self._vbox.insertWidget( 0, self._controls )
        
        self._controls_at_top = True
        CG.client_controller.new_options.SetBoolean( 'treeview_controls_at_top', True )
        
    
    def _MoveControlBarDown( self ):
        
        if not self._controls_at_top:
            return
            
        self._vbox.removeWidget( self._controls )
        self._vbox.addWidget( self._controls )
        
        self._controls_at_top = False
        CG.client_controller.new_options.SetBoolean( 'treeview_controls_at_top', False )
        
    
    def _MoveExpandingPanelToTop( self ):
        
        if self._panel_at_top:
            
            return
            
        
        self._expanding_panel_splitter.widget(0).deleteLater()
        self._expanding_panel_splitter.insertWidget( 0, self._expanding_panel )
        
        self._panel_at_top = True
        CG.client_controller.new_options.SetBoolean( 'treeview_expanding_panel_at_top', True )
        
    
    def _MoveExpandingPanelToBottom( self ):
        
        if not self._panel_at_top:
            
            return
            
        
        self._expanding_panel_splitter.widget(0).deleteLater()
        self._expanding_panel_splitter.addWidget( self._expanding_panel )
        
        self._panel_at_top = False
        CG.client_controller.new_options.SetBoolean( 'treeview_expanding_panel_at_top', False )
        
    
    def _PositionPanelNearWidget( self, panel: QW.QWidget, widget: QW.QWidget, avoid_widgets = None ):
        
        panel.adjustSize()
        
        if avoid_widgets is None:
            
            avoid_widgets = []
            
        
        widget_top_left = widget.mapToGlobal( widget.rect().topLeft() )
        widget_rect = QC.QRect( widget_top_left, widget.rect().size() )
        
        x = widget_rect.left()
        
        if self._controls_at_top:
            
            y = widget_rect.bottom() + 2
            
        else:
            
            y = widget_rect.top() - panel.height() - 2
            
        
        panel_rect = QC.QRect( x, y, panel.width(), panel.height() )
        
        for avoid_widget in avoid_widgets:
            
            if avoid_widget is None or not avoid_widget.isVisible():
                
                continue
                
            
            avoid_rect = avoid_widget.frameGeometry()
            
            if not panel_rect.intersects( avoid_rect ):
                
                continue
                
            
            if self._controls_at_top:
                
                y = avoid_rect.bottom() + 2
                
            else:
                
                y = avoid_rect.top() - panel.height() - 2
                
            
            panel_rect = QC.QRect( x, y, panel.width(), panel.height() )
            
        
        panel.move( x, y )
        
    
    def _QueueFloatingPanelReposition( self ):
        
        if self._queued_floating_panel_reposition:
            
            return
            
        
        self._queued_floating_panel_reposition = True
        
        QC.QTimer.singleShot( 0, self._RepositionFloatingPanels )
        
    
    def _RepositionFloatingPanels( self ):
        
        self._queued_floating_panel_reposition = False
        
        if self._history_panel.isVisible():
            
            self._PositionPanelNearWidget( self._history_panel, self._history_button, [ self._filter_panel ] )
            
        
        if self._filter_panel.isVisible():
            
            self._PositionPanelNearWidget( self._filter_panel, self._filter_button, [ self._history_panel ] )
            
        
    
    def _SetCurrentDepth( self, depth: int ):
        
        model = self._tree.model()
        
        if model is None:
            
            return
            
        
        max_depth = model.GetViewDepth() - 1
        
        self._current_depth = max( -1, min( depth, max_depth ) )
        
        self.depth_decrement.setEnabled( self._current_depth > -1 )
        self.depth_increment.setEnabled( self._current_depth < max_depth )
        self.collapse_all.setEnabled( self._current_depth > -1 )
        self.expand_all.setEnabled( self._current_depth < max_depth )
        
    
    def _SetCurrentPagePathText( self, page_name: str, tooltip: str ):
        
        self._current_page_path.setText( page_name )
        self._current_page_path.setToolTip( tooltip )
        
    
    def _SetTreeViewIndentation( self, value: int ):
        
        CG.client_controller.new_options.SetInteger( 'treeview_indentation', value )
        
        self._tree.setIndentation( value )
        
    
    def _SetTreeViewRowHeight( self, value: int ):
        
        CG.client_controller.new_options.SetInteger( 'treeview_row_height', value )
        
        self._tree.SetRowHeight( value )
        
    
    def _GetCogMenuTemplateItems( self ) -> list[ ClientGUIMenuButton.MenuTemplateItem ]:
        
        def control_bar_position_title_call():
            
            if self._controls_at_top:
                
                return 'Move this control bar to the bottom'
                
            else:
                
                return 'Move this control bar to the top'
                
            
        
        def tree_sidebar_position_title_call():
            
            if CG.client_controller.new_options.GetNoneableInteger( 'treeview_alignment' ) == CC.DIRECTION_LEFT:
                
                return 'Move tree sidebar to right'
                
            else:
                
                return 'Move tree sidebar to left'
                
            
        
        def tag_sidebar_position_title_call():
            
            if CG.client_controller.new_options.GetInteger( 'page_sidebar_alignment' ) == CC.DIRECTION_LEFT:
                
                return 'Move tags/preview sidebar to right'
                
            else:
                
                return 'Move tags/preview sidebar to left'
                
            
        
        def tab_bar_visibility_title_call():
            
            if CG.client_controller.new_options.GetBoolean( 'treeview_hides_tabs' ):
                
                return 'Show the normal tab bar'
                
            else:
                
                return 'Hide the normal tab bar'
                
            
        
        def tree_sidebar_collapsibility_title_call():
            
            if CG.client_controller.new_options.GetBoolean( 'treeview_sidebar_can_collapse' ):
                
                return 'Prevent tree sidebar from collapsing'
                
            else:
                
                return 'Allow collapsing tree sidebar (drag)'
                
            
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( control_bar_position_title_call, 'Move the tree view control bar.', lambda: self._MoveControlBarDown() if self._controls_at_top else self._MoveControlBarUp() ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( tree_sidebar_position_title_call, 'Move the tree sidebar to the other side.', lambda: self._EmitAlignmentToggle( CC.DIRECTION_RIGHT if CG.client_controller.new_options.GetNoneableInteger( 'treeview_alignment' ) == CC.DIRECTION_LEFT else CC.DIRECTION_LEFT ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( tag_sidebar_position_title_call, 'Move the tags and preview sidebar to the other side.', lambda: self._EmitTagViewAlignmentToggle( CC.DIRECTION_RIGHT if CG.client_controller.new_options.GetInteger( 'page_sidebar_alignment' ) == CC.DIRECTION_LEFT else CC.DIRECTION_LEFT ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( tab_bar_visibility_title_call, 'Show or hide the normal notebook tab bar.', self._ToggleTabBarVisibility ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'treeview_always_expand_to_current_tab_after_reset' )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'Always expand to current tab after reset', 'If this is unchecked, any refresh will respect all collapsed states, even if the current page is not showing. Otherwise, it will force expand nodes and highlight the current page every time.', check_manager ) )

        check_manager = ClientGUICommon.CheckboxManagerOptions( 'treeview_collapse_all_children_upon_parent_closed' )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'Collapse all children when parent is closed', 'If this is unchecked, collapsing a page-of-pages node will remember the expanded state of all its sub-pages. Otherwise, it will be collapsed completely.', check_manager ) )

        check_manager = ClientGUICommon.CheckboxManagerOptions( 'treeview_alternating_row_colours' )
        check_manager.AddNotifyCall( lambda: self._tree.setAlternatingRowColors( CG.client_controller.new_options.GetBoolean( 'treeview_alternating_row_colours' ) ) )

        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'Shade alternating rows', 'Style the tree view with alternating colour shading per row.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        spacing_template_items = []
        spacing_template_items.append( ClientGUIMenuButton.MenuTemplateItemSlider( 'indent width', 'The horizontal indentation added for each nested tree level.', lambda: CG.client_controller.new_options.GetInteger( 'treeview_indentation' ), 4, 64, 1, self._SetTreeViewIndentation ) )
        spacing_template_items.append( ClientGUIMenuButton.MenuTemplateItemSlider( 'row height', 'The vertical height of each tree row.', lambda: CG.client_controller.new_options.GetInteger( 'treeview_row_height' ), 16, 64, 1, self._SetTreeViewRowHeight ) )

        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'tree row dimensions', spacing_template_items ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( tree_sidebar_collapsibility_title_call, 'Allow or prevent the tree sidebar from being collapsed.', self._ToggleCollapsibility ) )
        
        return menu_template_items
        
    
    def _SplitterSizeChanged( self ):
        
        sizes = self._expanding_panel_splitter.sizes()
        
        CG.client_controller.new_options.SetIntegerList( 'treeview_expanding_panel_splitter_size', sizes )
        
    
    def _ToggleFilterPanel( self ):
        
        if self._filter_panel.HasText():
            
            return
            
        
        if self._filter_panel.isVisible():
            
            self._HideFilterPanel()
            
            return
            
        
        self._PositionPanelNearWidget( self._filter_panel, self._filter_button, [ self._history_panel ] )
        
        self._filter_panel.show()
        
        self._filter_panel.activateWindow()
        self._filter_panel.TakeFocus()
        
    
    def _ToggleHistoryPanel( self ):
        
        if self._history_panel.isVisible():
            
            self._HideHistoryPanel()
            
            return
            
        
        self._history_panel.Repopulate()
        self._PositionPanelNearWidget( self._history_panel, self._history_button, [ self._filter_panel ] )
        self._history_panel.show()
        
    
    def _ToggleTabBarVisibility( self ):
        
        CG.client_controller.new_options.FlipBoolean( 'treeview_hides_tabs' )
        
        self.tabBarVisibilityChanged.emit()
        
    
    def _ToggleCollapsibility( self ):
        
        CG.client_controller.new_options.FlipBoolean( 'treeview_sidebar_can_collapse' )
        
        self.treeSidebarCollapsibilityChanged.emit()
        
    
    def _TreeCurrentChanged( self, current: QC.QModelIndex, previous: QC.QModelIndex ):
        
        self._SetCurrentDepth( self._GetDepthFromIndex( current ) )
        
    
    def ApplicationFocusChangingUpdate( self, new_focus_widget ):
        
        if self._filter_panel.isVisible() and not self._filter_panel.HasText():
            
            focus_is_on_button = new_focus_widget == self._filter_button
            focus_is_on_panel = ClientGUIFunctions.WidgetOrAnyTLWChildHasFocus( self._filter_panel )
            
            if not ( focus_is_on_button or focus_is_on_panel ):
                
                self._HideFilterPanel()
                
            
        
        if self._history_panel.isVisible() and not self._history_panel.IsPinned():
            
            focus_is_on_button = new_focus_widget == self._history_button
            focus_is_on_panel = ClientGUIFunctions.WidgetOrAnyTLWChildHasFocus( self._history_panel )
            
            if not ( focus_is_on_button or focus_is_on_panel ):
                
                self._HideHistoryPanel()
                
            
        
    
    def expandToDepth( self, depth ):
        
        model = self._tree.model()
        
        if model is None:
            
            return
            
        
        if depth < 0:
            
            self.depth_decrement.setEnabled( False )
            self.depth_increment.setEnabled( True )
            self.collapse_all.setEnabled( False )
            self.expand_all.setEnabled( True )
            self._current_depth = -1
            
            self._tree.collapseAll()
            
        
        elif depth >= model.GetViewDepth() - 1:
            
            self.depth_decrement.setEnabled( True )
            self.depth_increment.setEnabled( False )
            self.collapse_all.setEnabled( True )
            self.expand_all.setEnabled( False )
            self._current_depth = model.GetViewDepth() - 1
            
            self._tree.expandAll()
            
        else:
            
            self.depth_decrement.setEnabled( True )
            self.depth_increment.setEnabled( True )
            self.collapse_all.setEnabled( True )
            self.expand_all.setEnabled( True )
            
            self._current_depth = depth
            self._tree.expandToDepth( depth )
            
        
    
    def GetTreeView( self ) -> QW.QTreeView:
        
        return self._tree
        
    
    def GetControlWidget( self ) -> QW.QWidget:
        
        return self._controls
        
    
    def NotifyWindowGeometryOrStateChange( self ):
        
        self._QueueFloatingPanelReposition()
        
    
    def PopulateHistoryIfOpen( self ):
        
        if self._history_panel.isVisible():
            
            self._history_panel.Repopulate()
            
        
    
