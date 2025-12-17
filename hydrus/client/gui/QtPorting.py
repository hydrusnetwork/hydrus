#This file is licensed under the Do What the Fuck You Want To Public License aka WTFPL

# hey so this file was made by prkc to bridge innumerate wx->Qt auto-conversion problems
# I, hydev, said 'thank you very much, this is incredible work, I will slowly replace all these functions with proper Qt code within a year or so'
# and we are, of course, now many years later
# so, if I just got hit by a bus and you are wondering what the hell is going on here, that's what's going on here

import collections.abc
import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from collections import defaultdict

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIExceptionHandling
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtInit

isValid = QtInit.isValid

def registerEventType():
    
    if QtInit.WE_ARE_PYSIDE:
        
        return QC.QEvent.Type( QC.QEvent.registerEventType() )
        
    else:
        
        return QC.QEvent.registerEventType()
        
    

class HBoxLayout( QW.QHBoxLayout ):
    
    def __init__( self, margin = 2, spacing = 2 ):
        
        super().__init__()
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        
    
    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    

class VBoxLayout( QW.QVBoxLayout ):
    
    def __init__( self, margin = 2, spacing = 2 ):
        
        super().__init__()
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        

    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    

class LabelledSlider( QW.QWidget ):
    
    valueChanged = QC.Signal( int )
    finishedEditing  = QC.Signal( int )
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        
        vbox = VBoxLayout( spacing = 2 )
        
        self.setLayout( vbox )
        
        top_layout = HBoxLayout( spacing = 2 )
        
        self._min_label = QW.QLabel()
        self._max_label = QW.QLabel()
        self._value_label = QW.QLabel()
        self._slider = QW.QSlider()
        self._slider.setOrientation( QC.Qt.Orientation.Horizontal )
        self._slider.setTickInterval( 1 )
        self._slider.setTickPosition( QW.QSlider.TickPosition.TicksBothSides )
        
        top_layout.addWidget( self._min_label )
        top_layout.addWidget( self._slider )
        top_layout.addWidget( self._max_label )
        
        vbox.addLayout( top_layout )
        vbox.addWidget( self._value_label )
        self._value_label.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignHCenter )
        vbox.setAlignment( self._value_label, QC.Qt.AlignmentFlag.AlignHCenter )
        
        self._slider.valueChanged.connect( self._UpdateLabels )
        self._slider.valueChanged.connect( self.valueChanged )
        self._slider.sliderReleased.connect( lambda: self.finishedEditing.emit( self._slider.value() ) )
        
        self._UpdateLabels()
        
    def _UpdateLabels( self ):
        
        self._min_label.setText( str( self._slider.minimum() ) )
        self._max_label.setText( str( self._slider.maximum() ) )
        self._value_label.setText( str( self._slider.value() ) )
        
    def GetValue( self ):
        
        return self._slider.value()
        
    
    def SetInterval( self, interval ):
        
        self._slider.setTickInterval( interval )
        
        self._UpdateLabels()
        
    def SetRange( self, min, max ):
        
        self._slider.setRange( min, max )
        
        self._UpdateLabels()
        
    def SetValue( self, value ):
        
        self._slider.setValue( value )
        
        self._UpdateLabels()
        

def SplitterVisibleCount( splitter ):
    
    count = 0
    
    for i in range( splitter.count() ):
        
        if splitter.widget( i ).isVisibleTo( splitter ): count += 1
        
    
    return count
    

class DirPickerCtrl( QW.QWidget ):

    dirPickerChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        layout = HBoxLayout( spacing = 2 )
        
        self._path_edit = QW.QLineEdit( self )
        
        self._button = QW.QPushButton( 'browse', self )
        
        self._button.clicked.connect( self._Browse )
        
        self._path_edit.textEdited.connect( self._TextEdited )
        
        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )
        
        self.setLayout( layout )
        
    
    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        
    
    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        kwargs = {}
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            # careful here, QW.QFileDialog.Options doesn't exist on PyQt6
            kwargs[ 'options' ] = QW.QFileDialog.Option.DontUseNativeDialog
            
        
        path = QW.QFileDialog.getExistingDirectory( self, '', existing_path, **kwargs )
        
        if path == '':
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if os.path.exists( path ):
            
            self.dirPickerChanged.emit()
            
        
    
    def _TextEdited( self, text ):
        
        if os.path.exists( text ):
            
            self.dirPickerChanged.emit()
            
        

class FilePickerCtrl( QW.QWidget ):
    
    filePickerChanged = QC.Signal()

    def __init__( self, parent = None, wildcard = None, starting_directory = None ):
        
        super().__init__( parent )

        layout = HBoxLayout( spacing = 2 )

        self._path_edit = QW.QLineEdit( self )

        self._button = QW.QPushButton( 'browse', self )

        self._button.clicked.connect( self._Browse )

        self._path_edit.textEdited.connect( self._TextEdited )

        layout.addWidget( self._path_edit )
        layout.addWidget( self._button )

        self.setLayout( layout )
        
        self._save_mode = False
        
        self._wildcard = wildcard
        
        self._starting_directory = starting_directory
        

    def SetPath( self, path ):
        
        self._path_edit.setText( path )
        

    def GetPath( self ):
        
        return self._path_edit.text()
        
    
    def SetSaveMode( self, save_mode ):
        
        self._save_mode = save_mode
        

    def _Browse( self ):
        
        existing_path = self._path_edit.text()
        
        if existing_path == '' and self._starting_directory is not None:
            
            existing_path = self._starting_directory
            
        
        kwargs = {}
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            # careful here, QW.QFileDialog.Options doesn't exist on PyQt6
            kwargs[ 'options' ] = QW.QFileDialog.Option.DontUseNativeDialog
            
        
        if self._save_mode:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, **kwargs )[0]
                
            else:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, **kwargs )[0]
                
            
        else:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, **kwargs )[0]
                
            else:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, **kwargs )[0]
                
            
        
        if path == '':
            
            return
            
        
        path = os.path.normpath( path )
        
        self._path_edit.setText( path )
        
        if self._save_mode or os.path.exists( path ):
            
            self.filePickerChanged.emit()
            
        

    def _TextEdited( self, text ):
        
        if self._save_mode or os.path.exists( text ):
            
            self.filePickerChanged.emit()
            
        

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
                
            
        except:
            
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
        
    
def DeleteAllNotebookPages( notebook ):
    
    while notebook.count() > 0:
        
        tab = notebook.widget( 0 )
        
        notebook.removeTab( 0 )
        
        tab.deleteLater()
        
    

def SplitVertically( splitter: QW.QSplitter, w1, w2, hpos ):
    
    if w1.parentWidget() != splitter:
        
        splitter.addWidget( w1 )
        

    w1.setVisible( True )

    if w2.parentWidget() != splitter:
        
        splitter.addWidget( w2 )
        

    w2.setVisible( True )
    
    total_sum = sum( splitter.sizes() )

    if hpos < 0:
        
        splitter.setSizes( [ total_sum + hpos, -hpos ] )
        
    elif hpos > 0:
        
        splitter.setSizes( [ hpos, total_sum - hpos ] )
        
    

def SplitHorizontally( splitter: QW.QSplitter, w1, w2, vpos ):
    
    if w1.parentWidget() != splitter:
        
        splitter.addWidget( w1 )
        
    w1.setVisible( True )
        
    if w2.parentWidget() != splitter:
        
        splitter.addWidget( w2 )
        

    w2.setVisible( True )
    
    total_sum = sum( splitter.sizes() )
    
    if vpos < 0:
        
        splitter.setSizes( [ total_sum + vpos, -vpos ] )
        
    elif vpos > 0:
        
        splitter.setSizes( [ vpos, total_sum - vpos ] )
        

class GridLayout( QW.QGridLayout ):
    
    def __init__( self, cols = 1, spacing = 2 ):
        
        super().__init__()
        
        self._col_count = cols
        self.setMargin( 2 )
        self.setSpacing( spacing )
        
        self.next_row = 0
        self.next_col = 0
        
    
    def GetFixedColumnCount( self ):
        
        return self._col_count
        
    
    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    

def AddToLayout( layout, item, flag = None, alignment = None ):
    
    # TODO: yo, this whole thing could do with a pass to clear out stuff that isn't doing what I expect and cut down to essentials
    # I think replace the whole thing with a new call and migrate everything over. separate our flags into separate enums for expand, alignment, spacing/whatever
    # figure out a better way to navigate layouts and expand gubbins and anything else with spotty support
    # another thing to think about is (as Qt wants) having widgets saying how they want to size on their own and just simplifying the 'addWidget' stuff a whole lot
    
    if isinstance( layout, GridLayout ):
        
        row = layout.next_row
        
        col = layout.next_col
        
        try:
            
            if isinstance( item, QW.QLayout ):
                
                layout.addLayout( item, row, col )
                
            elif isinstance( item, QW.QWidget ):
                
                layout.addWidget( item, row, col )
                
            elif isinstance( item, tuple ):
                
                spacer = QW.QPushButton()#QW.QSpacerItem( 0, 0, QW.QSizePolicy.Policy.Expanding, QW.QSizePolicy.Policy.Fixed )
                layout.addWidget( spacer, row, col )
                spacer.setVisible(False)
                
                return
                
            
        finally:
            
            if col == layout.GetFixedColumnCount() - 1:
                
                layout.next_row += 1
                layout.next_col = 0
                
            else:
                
                layout.next_col += 1
                
            
        
    else:
        
        if isinstance( item, QW.QLayout ):
            
            layout.addLayout( item )
            
            if alignment is not None:
                
                layout.setAlignment( item, alignment )
                
            
        elif isinstance( item, QW.QWidget ):
            
            layout.addWidget( item )
            
            if alignment is not None:
                
                layout.setAlignment( item, alignment )
                
            
        elif isinstance( item, tuple ):
            
            layout.addStretch( 1 )
            
            return
            
        
    
    zero_border = False
    
    if flag is None or flag == CC.FLAGS_NONE:
        
        pass
        
    elif flag in ( CC.FLAGS_CENTER, CC.FLAGS_ON_LEFT, CC.FLAGS_ON_RIGHT, CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH, CC.FLAGS_SIZER_CENTER ):
        
        if flag in ( CC.FLAGS_CENTER, CC.FLAGS_SIZER_CENTER ):
            
            alignment = QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignHCenter
            
        if flag == CC.FLAGS_ON_LEFT:
            
            alignment = QC.Qt.AlignmentFlag.AlignLeft | QC.Qt.AlignmentFlag.AlignVCenter
            
        elif flag == CC.FLAGS_ON_RIGHT:
            
            alignment = QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter
            
        elif flag in ( CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH ):
            
            if isinstance( layout, ( QW.QHBoxLayout, QW.QGridLayout ) ):
                
                alignment = QC.Qt.AlignmentFlag.AlignVCenter
                
            else:
                
                alignment = QC.Qt.AlignmentFlag.AlignHCenter
                
            
        
        layout.setAlignment( item, alignment )
        
        if flag == CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH:
            
            if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
                
                layout.setStretchFactor( item, 5 )
                
            
        
        if isinstance( item, QW.QLayout ): # what in the
            
            zero_border = True
            
        
    elif flag in ( CC.FLAGS_EXPAND_PERPENDICULAR, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR, CC.FLAGS_ON_RIGHT, CC.FLAGS_EXPAND_PERPENDICULAR_BUT_BOTH_WAYS_LATER ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_PERPENDICULAR:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                h_policy = QW.QSizePolicy.Policy.Fixed
                v_policy = QW.QSizePolicy.Policy.Expanding
                
            else:
                
                h_policy = QW.QSizePolicy.Policy.Expanding
                v_policy = QW.QSizePolicy.Policy.Fixed
                
            
            item.setSizePolicy( h_policy, v_policy )
            
        
        if flag == CC.FLAGS_EXPAND_PERPENDICULAR_BUT_BOTH_WAYS_LATER:
            
            # we used to do this just for expanding guys, and it is ostensibly ignored for Fixed stuff, but if we have expanding boxes that change between Fixed and Expanding, we'll want to set it!
            # default appears to be 0 in the direction of the Layout
            if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
                
                stretch_factor = 50
                
                layout.setStretchFactor( item, stretch_factor )
                
            
        
    elif flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE, CC.FLAGS_EXPAND_BOTH_WAYS_SHY ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_BOTH_WAYS:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            item.setSizePolicy( QW.QSizePolicy.Policy.Expanding, QW.QSizePolicy.Policy.Expanding )
            
        
        if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
            
            if flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS ):
                
                stretch_factor = 50
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_POLITE:
                
                stretch_factor = 30
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_SHY:
                
                stretch_factor = 10
                
            
            layout.setStretchFactor( item, stretch_factor )
            
        
    
    if zero_border:
        
        margin = 0
        
        if isinstance( item, QW.QFrame ):
            
            margin = item.frameWidth()
            
        
        item.setContentsMargins( margin, margin, margin, margin )
        
    

def ScrollAreaVisibleRect( scroll_area ):
    
    if not scroll_area.widget(): return QC.QRect( 0, 0, 0, 0 )
    
    rect = scroll_area.widget().visibleRegion().boundingRect()

    # Do not allow it to be smaller than the scroll area's viewport size:
    
    if rect.width() < scroll_area.viewport().width():
        
        rect.setWidth( scroll_area.viewport().width() )

    if rect.height() < scroll_area.viewport().height():
        
        rect.setHeight( scroll_area.viewport().height() )
        
    
    return rect
    

def AdjustOpacity( image: QG.QImage, opacity_factor ):
    
    new_image = QG.QImage( image.width(), image.height(), QG.QImage.Format.Format_RGBA8888 )
    
    new_image.setDevicePixelRatio( image.devicePixelRatio() )
    
    new_image.fill( QC.Qt.GlobalColor.transparent )
    
    painter = QG.QPainter( new_image )
    
    painter.setOpacity( opacity_factor )
    
    painter.drawImage( 0, 0, image )
    
    return new_image
    

def ToKeySequence( modifiers, key ):
    
    if QtInit.WE_ARE_QT5:
        
        # noinspection PyUnresolvedReferences
        if isinstance( modifiers, QC.Qt.KeyboardModifiers ):
            
            seq_str = ''
            
            for modifier in [ QC.Qt.KeyboardModifier.ShiftModifier, QC.Qt.KeyboardModifier.ControlModifier, QC.Qt.KeyboardModifier.AltModifier, QC.Qt.KeyboardModifier.MetaModifier, QC.Qt.KeyboardModifier.KeypadModifier, QC.Qt.KeyboardModifier.GroupSwitchModifier ]:
                
                if modifiers & modifier: seq_str += QG.QKeySequence( modifier ).toString()
                
            
            seq_str += QG.QKeySequence( key ).toString()
            
            return QG.QKeySequence( seq_str )
            
        else:
            
            return QG.QKeySequence( key + modifiers )
            
        
    else:
        
        return QG.QKeySequence( QC.QKeyCombination( modifiers, key ) ) # pylint: disable=E1101
        
    

def AddShortcut( widget, modifier, key, func: collections.abc.Callable, *args ):
    
    shortcut = QW.QShortcut( widget )
    
    shortcut.setKey( ToKeySequence( modifier, key ) )
    
    shortcut.setContext( QC.Qt.ShortcutContext.WidgetWithChildrenShortcut )
    
    shortcut.activated.connect( lambda: func( *args ) )
    

def GetBackgroundColour( widget ):
    
    return widget.palette().color( QG.QPalette.ColorRole.Window )
    

def ClearLayout( layout, delete_widgets = False ):
    
    while layout.count() > 0:
        
        item = layout.itemAt( 0 )

        if delete_widgets:
            
            if item.widget():
                
                item.widget().deleteLater()
                
            elif item.layout():
                
                ClearLayout( item.layout(), delete_widgets = True )
                item.layout().deleteLater()
                
            else:
                
                spacer = item.layout().spacerItem()
                
                del spacer
                
            

        layout.removeItem( item )
        
    

def Unsplit( splitter, widget ):
    
    if widget.parentWidget() == splitter:
        
        widget.setVisible( False )
        
    

def CenterOnWindow( parent, window ):
    
    parent_window = parent.window()
    
    window.move( parent_window.frameGeometry().center() - window.rect().center() )
    

def SetInitialSize( widget, size ):
    
    if hasattr( widget, 'SetInitialSize' ):
        
        widget.SetInitialSize( size )
        
        return
    
    if isinstance( size, tuple ):
        
        size = QC.QSize( size[0], size[1] )
        
    
    if size.width() >= 0: widget.setMinimumWidth( size.width() )
    if size.height() >= 0: widget.setMinimumHeight( size.height() )
    

def SetBackgroundColour( widget, colour ):
    
    widget.setAutoFillBackground( True )

    object_name = widget.objectName()

    if not object_name:
        
        object_name = str( id( widget ) )

        widget.setObjectName( object_name )
    
    if isinstance( colour, QG.QColor ):
        
        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, colour.name()) )
        
    elif isinstance( colour, tuple ):
        
        colour = QG.QColor( *colour )
        
        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, colour.name() ) )
        
    else:

        widget.setStyleSheet( '#{} {{ background-color: {} }}'.format( object_name, QG.QColor( colour ).name() ) )
        
    

def SetMinClientSize( widget, size ):
    
    if isinstance( size, tuple ):
        
        size = QC.QSize( size[0], size[1] )
        
    
    if size.width() >= 0: widget.setMinimumWidth( size.width() )
    if size.height() >= 0: widget.setMinimumHeight( size.height() )
    

class StatusBar( QW.QStatusBar ):
    
    def __init__( self, status_widths ):
        
        super().__init__()
        
        self._labels = []
        
        for w in status_widths:
            
            label = QW.QLabel()
            
            self._labels.append( label )
            
            if w < 0:
                
                self.addWidget( label, -1 * w )
                
            else:
                
                label.setFixedWidth( w )
                
                self.addWidget( label )
                
            
        
    
    def SetStatusText( self, text, index, tooltip = None ):
        
        if tooltip is None:
            
            tooltip = text
            
        
        cell = self._labels[ index ]
        
        if cell.text() != text:
            
            cell.setText( text )
            
        
        if cell.toolTip() != tooltip:
            
            cell.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
            
        
    

class UIActionSimulator:
    
    def __init__( self ):
        
        pass
        
    
    def Char( self, widget, key, text = None ):
        
        if widget is None:
            
            widget = QW.QApplication.focusWidget()
            
        
        ev1 = QG.QKeyEvent( QC.QEvent.Type.KeyPress, key, QC.Qt.KeyboardModifier.NoModifier, text = text )
        ev2 = QG.QKeyEvent( QC.QEvent.Type.KeyRelease, key, QC.Qt.KeyboardModifier.NoModifier, text = text )
        
        QW.QApplication.postEvent( widget, ev1 )
        QW.QApplication.postEvent( widget, ev2 )
        
    

# Adapted from https://doc.qt.io/qt-5/qtwidgets-widgets-elidedlabel-example.html
class EllipsizedLabel( QW.QLabel ):
    
    def __init__( self, parent = None, ellipsize_end = False, ellipsized_ideal_width_chars = 24 ):
        
        super().__init__( parent )
        
        self._ellipsize_end = ellipsize_end
        self._ellipsized_ideal_width_chars = ellipsized_ideal_width_chars
        
    
    def minimumSizeHint( self ):
        
        if self._ellipsize_end:
            
            num_lines = self.text().count( '\n' ) + 1
            
            line_width = self.fontMetrics().lineWidth()
            line_height = self.fontMetrics().lineSpacing()
            
            return QC.QSize( 3 * line_width, num_lines * line_height )
            
        else:
            
            return QW.QLabel.minimumSizeHint( self )
            
        
    
    def setText( self, text ):
        
        try:
            
            QW.QLabel.setText( self, text )
            
        except ValueError:
            
            QW.QLabel.setText( self, repr( text ) )
            
        
        self.update()
        
    
    def sizeHint( self ):
        
        if self._ellipsize_end:
            
            parent_size_hint = QW.QLabel.sizeHint( self )
            
            line_width = self.fontMetrics().lineWidth()
            
            size_hint = QC.QSize( min( parent_size_hint.width(), self._ellipsized_ideal_width_chars * line_width ), parent_size_hint.height() )
            
        else:
            
            size_hint = QW.QLabel.sizeHint( self )
            
        
        return size_hint
        
    
    def paintEvent( self, event ):
        
        try:
            
            if not self._ellipsize_end:
                
                QW.QLabel.paintEvent( self, event )
                
                return
                
            
            painter = QG.QPainter( self )
            
            fontMetrics = painter.fontMetrics()
            
            text_lines = self.text().splitlines()
            
            line_spacing = fontMetrics.lineSpacing()
            
            current_y = 0
            
            done = False
            
            my_width = self.width()
            
            for text_line in text_lines:
                
                elided_line = fontMetrics.elidedText( text_line, QC.Qt.TextElideMode.ElideRight, my_width )
                
                x = 0
                width = my_width
                height = line_spacing
                flags = self.alignment()
                
                painter.drawText( x, current_y, width, height, flags, elided_line )
                
                # old hacky line that doesn't support alignment flags
                #painter.drawText( QC.QPoint( 0, current_y + fontMetrics.ascent() ), elided_line )
                
                current_y += line_spacing
                
                # old code that did multiline wrap width stuff
                '''
                text_layout = QG.QTextLayout( text_line, painter.font() )
                
                text_layout.beginLayout()
                
                while True:
                    
                    line = text_layout.createLine()
                    
                    if not line.isValid(): break
                    
                    line.setLineWidth( self.width() )
                    
                    next_line_y = y + line_spacing
                    
                    if self.height() >= next_line_y + line_spacing:
                        
                        line.draw( painter, QC.QPoint( 0, y ) )
                        
                        y = next_line_y
                        
                    else:
                        
                        last_line = text_line[ line.textStart(): ]
                        
                        elided_last_line = fontMetrics.elidedText( last_line, QC.Qt.TextElideMode.ElideRight, self.width() )
                        
                        painter.drawText( QC.QPoint( 0, y + fontMetrics.ascent() ), elided_last_line )
                        
                        done = True
                        
                        break
                        
                    
                
                text_layout.endLayout()
                
                if done: break
                '''
                
            
        except Exception as e:
            
            ClientGUIExceptionHandling.HandlePaintEventException( self, e )
            
        
    

class Dialog( QW.QDialog ):
    
    def __init__( self, parent = None, **kwargs ):

        title = None 
        
        if 'title' in kwargs:
            
            title = kwargs['title']
            
            del kwargs['title']
            
        
        super().__init__( parent, **kwargs )
        
        self.setWindowFlag( QC.Qt.WindowType.WindowContextHelpButtonHint, on = False )
        
        if title is not None:
            
            self.setWindowTitle( title )
            
        
        self._closed_by_user = False
        
    
    def closeEvent( self, event ):
        
        if event.spontaneous():
            
            self._closed_by_user = True
            
        
        QW.QDialog.closeEvent( self, event )
        
    
    # True if the dialog was closed by the user clicking on the X on the titlebar (so neither reject nor accept was chosen - the dialog result is still reject in this case though)    
    def WasCancelled( self ):
        
        return self._closed_by_user
        
    
    def SetCancelled( self, closed ):
        
        self._closed_by_user = closed
        
    
    def __enter__( self ):
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        if isValid( self ):
            
            self.deleteLater()
            
        
    

class PasswordEntryDialog( Dialog ):
    
    def __init__( self, parent, message, caption ):
        
        super().__init__( parent )
        
        self.setWindowTitle( caption )
        
        self._ok_button = QW.QPushButton( 'OK', self )
        self._ok_button.clicked.connect( self.accept )
        
        self._cancel_button = QW.QPushButton( 'Cancel', self )
        self._cancel_button.clicked.connect( self.reject )
        
        self._password = QW.QLineEdit( self )
        self._password.setEchoMode( QW.QLineEdit.EchoMode.Password )
        
        vbox = QW.QVBoxLayout()
        
        self.setLayout( vbox )
        
        entry_layout = QW.QHBoxLayout()
        
        entry_layout.addWidget( QW.QLabel( message, self ) )
        entry_layout.addWidget( self._password )
        
        button_layout = QW.QHBoxLayout()
        
        button_layout.addStretch( 1 )
        button_layout.addWidget( self._cancel_button )
        button_layout.addWidget( self._ok_button )
        
        vbox.addLayout( entry_layout )
        vbox.addLayout( button_layout )
        

    def GetValue( self ):
        
        return self._password.text()
        
    

class DirDialog( QW.QFileDialog ):
    
    def __init__( self, parent = None, message = None ):
        
        super().__init__( parent )
        
        if message is not None:
            
            self.setWindowTitle( message )
            
        
        self.setAcceptMode( QW.QFileDialog.AcceptMode.AcceptOpen )
        
        self.setFileMode( QW.QFileDialog.FileMode.Directory )
        
        self.setOption( QW.QFileDialog.Option.ShowDirsOnly, True )
        
        self.setOption( QW.QFileDialog.Option.ReadOnly, False )
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.Option.DontUseNativeDialog, True )
            
        
    
    def __enter__( self ):
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self.deleteLater()
        
    
    def _GetSelectedFiles( self ):
        
        return [ os.path.normpath( path ) for path in self.selectedFiles() ]
        
    
    def GetPath(self):
        
        sel = self._GetSelectedFiles()
        
        if len( sel ) > 0:
            
            return sel[0]
            
        
        return None
        
    

class FileDialog( QW.QFileDialog ):
    
    def __init__( self, parent = None, message = None, acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFile, default_filename = None, default_directory = None, wildcard = None, defaultSuffix = None ):
        
        super().__init__( parent )
        
        if message is not None:
            
            self.setWindowTitle( message )
            
        
        self.setAcceptMode( acceptMode )
        
        self.setFileMode( fileMode )
        
        if default_directory is not None:
            
            self.setDirectory( default_directory )
            
        
        if defaultSuffix is not None:
            
            self.setDefaultSuffix( defaultSuffix )
            
        
        if default_filename is not None:
            
            self.selectFile( default_filename )
            
        
        if wildcard:
            
            self.setNameFilters( [ wildcard, 'Any files (*)' ] )
            
        
        if CG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.Option.DontUseNativeDialog, True )
            
        
    
    def __enter__( self ):
        
        return self
        

    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self.deleteLater()
        

    def _GetSelectedFiles( self ):
        
        return [ os.path.normpath( path ) for path in self.selectedFiles() ]
        
    
    def GetPath( self ):
        
        sel = self._GetSelectedFiles()

        if len( sel ) > 0:
            
            return sel[ 0 ]
            

        return None
        
    
    def GetPaths( self ):
        
        return self._GetSelectedFiles()
        
    

# A QTreeWidget where if an item is (un)checked, all its children are also (un)checked, recursively
class TreeWidgetWithInheritedCheckState( QW.QTreeWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
        self.itemChanged.connect( self._HandleItemCheckStateUpdate )
        
    
    def _GetChildren( self, item: QW.QTreeWidgetItem ) -> list[ QW.QTreeWidgetItem ]:
        
        children = [ item.child( i ) for i in range( item.childCount() ) ]
        
        return children
        
    
    def _HandleItemCheckStateUpdate( self, item, column ):
        
        self.blockSignals( True )
        
        self._UpdateChildrenCheckState( item, item.checkState( 0 ) )
        self._UpdateParentCheckState( item )
        
        self.blockSignals( False )
        
    
    def _UpdateChildrenCheckState( self, item, check_state ):
        
        for child in self._GetChildren( item ):
            
            child.setCheckState( 0, check_state )
            
            self._UpdateChildrenCheckState( child, check_state )
            
        
    
    def _UpdateParentCheckState( self, item: QW.QTreeWidgetItem ):
        
        parent = item.parent()
        
        if isinstance( parent, QW.QTreeWidgetItem ):
            
            all_values = { child.checkState( 0 ) for child in self._GetChildren( parent ) }
            
            if all_values == { QC.Qt.CheckState.Checked }:
                
                end_state = QC.Qt.CheckState.Checked
                
            elif all_values == { QC.Qt.CheckState.Unchecked }:
                
                end_state = QC.Qt.CheckState.Unchecked
                
            else:
                
                end_state = QC.Qt.CheckState.PartiallyChecked
                
            
            if end_state != parent.checkState( 0 ):
                
                parent.setCheckState( 0, end_state )
                
                self._UpdateParentCheckState( parent )
                
            
        
    

def ListsToTuples( potentially_nested_lists ):
    
    if HydrusLists.IsAListLikeCollection( potentially_nested_lists ):
        
        return tuple( map( ListsToTuples, potentially_nested_lists ) )
        
    else:
        
        return potentially_nested_lists
        
    

class WidgetEventFilter ( QC.QObject ):
    
    _strong_focus_required = { 'EVT_KEY_DOWN' }
    
    def __init__( self, parent_widget ):
    
        self._parent_widget = parent_widget
        
        super().__init__( parent_widget )
        
        parent_widget.installEventFilter( self )
        
        self._callback_map = defaultdict( list )
        
    
    def _ExecuteCallbacks( self, event_name, event ):
        
        if event_name not in self._callback_map: return
        
        event_killed = False
        
        for callback in self._callback_map[ event_name ]:
            
            if not callback( event ): event_killed = True
            
        return event_killed


    def eventFilter( self, watched, event ):
        
        try:
            
            # Once somehow this got called with no _parent_widget set - which is probably fixed now but leaving the check just in case, wew
            # Might be worth debugging this later if it still occurs - the only way I found to reproduce it is to run the help > debug > initialize server command
            if not hasattr( self, '_parent_widget') or not isValid( self._parent_widget ): return False
            
            type = event.type()
            
            event_killed = False
            
            if type == QC.QEvent.Type.MouseButtonDblClick:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.button() == QC.Qt.MouseButton.LeftButton:
                    
                    event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DCLICK', event )
                    
                elif event.button() == QC.Qt.MouseButton.RightButton:
                    
                    event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DCLICK', event )
                    
                
            elif type == QC.QEvent.Type.MouseButtonPress:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.buttons() & QC.Qt.MouseButton.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DOWN', event )
                
                if event.buttons() & QC.Qt.MouseButton.MiddleButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MIDDLE_DOWN', event )
                
                if event.buttons() & QC.Qt.MouseButton.RightButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DOWN', event )
                
            elif type == QC.QEvent.Type.MouseButtonRelease:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.buttons() & QC.Qt.MouseButton.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_UP', event )
                
            elif type == QC.QEvent.Type.Resize:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_SIZE', event )
                
            if event_killed:
                
                event.accept()
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def _AddCallback( self, evt_name, callback ):
        
        if evt_name in self._strong_focus_required:
            
            self._parent_widget.setFocusPolicy( QC.Qt.FocusPolicy.StrongFocus )
            
        
        self._callback_map[ evt_name ].append( callback )
        
    
    def EVT_LEFT_DCLICK( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DCLICK', callback )

    def EVT_RIGHT_DCLICK( self, callback ):

        self._AddCallback( 'EVT_RIGHT_DCLICK', callback )
        
    def EVT_LEFT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DOWN', callback )

    def EVT_LEFT_UP( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_UP', callback )

    def EVT_MIDDLE_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_MIDDLE_DOWN', callback )

    def EVT_RIGHT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_RIGHT_DOWN', callback )

    def EVT_SIZE( self, callback ):
        
        self._AddCallback( 'EVT_SIZE', callback )
