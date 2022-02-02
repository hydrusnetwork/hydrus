#This file is licensed under the Do What the Fuck You Want To Public License aka WTFPL

import os

# If not explicitely set, prefer PySide2 instead of the qtpy default which is PyQt5
# It is important that this runs on startup *before* anything is imported from qtpy.
# Since test.py, client.py and client.pyw all import this module first before any other Qt related ones, this requirement is satisfied.

if not 'QT_API' in os.environ:
    
    try:

        import PySide2

        os.environ[ 'QT_API' ] = 'pyside2'
        
    except ImportError as e:
        
        pass
        

# 
import qtpy
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

import math
import typing

from collections import defaultdict
    
if qtpy.PYQT5:
    
    import sip # pylint: disable=E0401
    
    def isValid( obj ):
        
        if isinstance( obj, sip.simplewrapper ):
        
            return not sip.isdeleted( obj )
            
        
        return True
        
    
elif qtpy.PYSIDE2:
    
    import shiboken2
    
    isValid = shiboken2.isValid
    
else:
    
    raise RuntimeError( 'You need either PySide2 or PyQt5' )
    

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC

def MonkeyPatchMissingMethods():
    
    if qtpy.PYQT5:
        
        def MonkeyPatchGetSaveFileName( original_function ):
            
            def new_function( *args, **kwargs ):
                
                if 'selectedFilter' in kwargs:
                    
                    kwargs[ 'initialFilter' ] = kwargs[ 'selectedFilter' ]
                    del kwargs[ 'selectedFilter' ]
                    
                    return original_function( *args, **kwargs )
                    
                
            
            return new_function
            
        
        QW.QFileDialog.getSaveFileName = MonkeyPatchGetSaveFileName( QW.QFileDialog.getSaveFileName )
        


class HBoxLayout( QW.QHBoxLayout ):
    
    def __init__( self, margin = 2, spacing = 2 ):
        
        QW.QHBoxLayout.__init__( self )
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        
    
    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        

class VBoxLayout( QW.QVBoxLayout ):

    def __init__( self, margin = 2, spacing = 2 ):
        
        QW.QVBoxLayout.__init__( self )
        
        self.setMargin( margin )
        self.setSpacing( spacing )
        

    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    
class LabelledSlider( QW.QWidget ):
    
    def __init__( self, parent = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setLayout( VBoxLayout( spacing = 2 ) )
        
        top_layout = HBoxLayout( spacing = 2 )
        
        self._min_label = QW.QLabel()
        self._max_label = QW.QLabel()
        self._value_label = QW.QLabel()
        self._slider = QW.QSlider()
        self._slider.setOrientation( QC.Qt.Horizontal )
        self._slider.setTickInterval( 1 )
        self._slider.setTickPosition( QW.QSlider.TicksBothSides )
        
        top_layout.addWidget( self._min_label )
        top_layout.addWidget( self._slider )
        top_layout.addWidget( self._max_label )
        
        self.layout().addLayout( top_layout )
        self.layout().addWidget( self._value_label )
        self._value_label.setAlignment( QC.Qt.AlignVCenter | QC.Qt.AlignHCenter )
        self.layout().setAlignment( self._value_label, QC.Qt.AlignHCenter )
        
        self._slider.valueChanged.connect( self._UpdateLabels )
        
        self._UpdateLabels()
        
    def _UpdateLabels( self ):
        
        self._min_label.setText( str( self._slider.minimum() ) )
        self._max_label.setText( str( self._slider.maximum() ) )
        self._value_label.setText( str( self._slider.value() ) )
        
    def GetValue( self ):
        
        return self._slider.value()
    
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
        
        QW.QWidget.__init__( self, parent )
        
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
        
        if HG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            options = QW.QFileDialog.Options( QW.QFileDialog.DontUseNativeDialog )
            
        else:
            
            options = QW.QFileDialog.Options()
            
        
        path = QW.QFileDialog.getExistingDirectory( self, '', existing_path, options = options )
        
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
        
        QW.QWidget.__init__( self, parent )

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
            
        
        if HG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            options = QW.QFileDialog.Options( QW.QFileDialog.DontUseNativeDialog )
            
        else:
            
            options = QW.QFileDialog.Options()
            
        
        if self._save_mode:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, options = options )[0]
                
            else:
                
                path = QW.QFileDialog.getSaveFileName( self, '', existing_path, options = options )[0]
                
            
        else:
            
            if self._wildcard:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, filter = self._wildcard, selectedFilter = self._wildcard, options = options )[0]
                
            else:
                
                path = QW.QFileDialog.getOpenFileName( self, '', existing_path, options = options )[0]
                
            
        
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
        
        QW.QTabBar.__init__( self, parent )
        
        self.setMouseTracking( True )
        self.setAcceptDrops( True )
        self._supplementary_drop_target = None
        
        self._last_clicked_tab_index = -1
        self._last_clicked_global_pos = None
        
    
    def AddSupplementaryTabBarDropTarget( self, drop_target ):
        
        self._supplementary_drop_target = drop_target
        
    
    def clearLastClickedTabInfo( self ):
        
        self._last_clicked_tab_index = -1
        
        self._last_clicked_global_pos = None
        
    
    def event( self, event ):
        
        return QW.QTabBar.event( self, event )
        
    
    def mouseMoveEvent( self, e ):
        
        e.ignore()
        
    
    def mousePressEvent( self, event ):
        
        index = self.tabAt( event.pos() )
        
        if event.button() == QC.Qt.LeftButton:
            
            self._last_clicked_tab_index = index
            
            self._last_clicked_global_pos = event.globalPos()
            
        
        QW.QTabBar.mousePressEvent( self, event )
        
    
    def mouseReleaseEvent( self, event ):
        
        index = self.tabAt( event.pos() )
        
        if event.button() == QC.Qt.MiddleButton:
            
            if index != -1:
                
                self.tabMiddleClicked.emit( index )
                
                return
                
            
        
        QW.QTabBar.mouseReleaseEvent( self, event )
        
    
    def mouseDoubleClickEvent( self, event ):
        
        index = self.tabAt( event.pos() )
        
        if event.button() == QC.Qt.LeftButton:
            
            if index == -1:
                
                self.tabSpaceDoubleLeftClicked.emit()
                
            else:
                
                self.tabDoubleLeftClicked.emit( index )
                
            
            return
            
        elif event.button() == QC.Qt.MiddleButton:
            
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
            
            tab_index = self.tabAt( event.pos() )
            
            if tab_index != -1:
                
                self.parentWidget().setCurrentIndex( tab_index )
                
            
        else:
            
            event.ignore()
            
        
    
    def lastClickedTabInfo( self ):
        
        return ( self._last_clicked_tab_index, self._last_clicked_global_pos )
        
    
    def dropEvent( self, event ):
        
        if self._supplementary_drop_target:
            
            self._supplementary_drop_target.eventFilter( self, event )
            
        else:
            
            event.ignore()
            
        

# A heavily extended/tweaked version of https://forum.qt.io/topic/67542/drag-tabs-between-qtabwidgets/
class TabWidgetWithDnD( QW.QTabWidget ):
    
    pageDragAndDropped = QC.Signal( QW.QWidget, QW.QWidget )
    
    def __init__( self, parent = None ):
        
        QW.QTabWidget.__init__( self, parent )
        
        self.setTabBar( TabBar( self ) )
        
        self.setAcceptDrops( True )
        
        self._tab_bar = self.tabBar()
        
        self._supplementary_drop_target = None
        
    
    def _LayoutPagesHelper( self ):
        
        current_index = self.currentIndex()

        for i in range( self.count() ):

            self.setCurrentIndex( i )

            if isinstance( self.widget( i ), TabWidgetWithDnD ):
                
                self.widget( i )._LayoutPagesHelper()
                
            
        
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
        self.tabBar().AddSupplementaryTabBarDropTarget( drop_target )
        
    
    def mouseMoveEvent( self, e ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.pos() ) ) ):
            
            QW.QTabWidget.mouseMoveEvent( self, e )
            
        
        if e.buttons() != QC.Qt.LeftButton:
            
            return
            
        
        my_mouse_pos = e.pos()
        global_mouse_pos = self.mapToGlobal( my_mouse_pos )
        tab_bar_mouse_pos = self._tab_bar.mapFromGlobal( global_mouse_pos )
        
        if not self._tab_bar.rect().contains( tab_bar_mouse_pos ):
            
            return
            
        
        if not isinstance( self._tab_bar, TabBar ):
            
            return
            
        
        ( clicked_tab_index, clicked_global_pos ) = self._tab_bar.lastClickedTabInfo()
        
        if clicked_tab_index == -1:
            
            return
            
        
        if e.globalPos() == clicked_global_pos:
            
            # don't start a drag until movement
            
            return
            
        
        tab_rect = self._tab_bar.tabRect( clicked_tab_index )
        
        pixmap = QG.QPixmap( tab_rect.size() )
        self._tab_bar.render( pixmap, QC.QPoint(), QG.QRegion( tab_rect ) )
        
        mimeData = QC.QMimeData()
        
        mimeData.setData( 'application/hydrus-tab', b'' )
        
        drag = QG.QDrag( self._tab_bar )
        
        drag.setMimeData( mimeData )
        
        drag.setPixmap( pixmap )
        
        cursor = QG.QCursor( QC.Qt.OpenHandCursor )
        
        drag.setHotSpot( QC.QPoint( 0, 0 ) )
        
        # this puts the tab pixmap exactly where we picked it up, but it looks bad
        # drag.setHotSpot( tab_bar_mouse_pos - tab_rect.topLeft() )
        
        drag.setDragCursor( cursor.pixmap(), QC.Qt.MoveAction )
        
        drag.exec_( QC.Qt.MoveAction )
        

    def dragEnterEvent( self, e ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.pos() ) ) ):
            
            return QW.QTabWidget.dragEnterEvent( self, e )
            
        
        if 'application/hydrus-tab' in e.mimeData().formats():
            
            e.accept()
            
        else:
            
            e.ignore()
            
        
    
    def dragMoveEvent( self, event ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( event.pos() ) ) ): return QW.QTabWidget.dragMoveEvent( self, event )
        
        screen_pos = self.mapToGlobal( event.pos() )
        
        tab_pos = self._tab_bar.mapFromGlobal( screen_pos )
        
        tab_index = self._tab_bar.tabAt( tab_pos )
        
        if tab_index != -1:
            
            shift_down = event.keyboardModifiers() & QC.Qt.ShiftModifier
            
            self.setCurrentIndex( tab_index )
            
        
        if 'application/hydrus-tab' not in event.mimeData().formats():
            
            event.reject()
            

        #return QW.QTabWidget.dragMoveEvent( self, event )
        

    def dragLeaveEvent( self, e ):
        
        #if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.pos() ) ) ): return QW.QTabWidget.dragLeaveEvent( self, e )
        
        e.accept()
        

    def addTab(self, widget, *args, **kwargs ):
        
        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            
        
        QW.QTabWidget.addTab( self, widget, *args, **kwargs )
        
    
    def insertTab(self, index, widget, *args, **kwargs):

        if isinstance( widget, TabWidgetWithDnD ):
            
            widget.AddSupplementaryTabBarDropTarget( self._supplementary_drop_target )
            

        QW.QTabWidget.insertTab( self, index, widget, *args, **kwargs )
        
    
    def dropEvent( self, e ):
        
        if self.currentWidget() and self.currentWidget().rect().contains( self.currentWidget().mapFromGlobal( self.mapToGlobal( e.pos() ) ) ):
            
            return QW.QTabWidget.dropEvent( self, e )
            
       
        if 'application/hydrus-tab' not in e.mimeData().formats(): #Page dnd has no associated mime data
            
            e.ignore()
            
            return
            
        
        w = self
        
        source_tab_bar = e.source()
        
        if not isinstance( source_tab_bar, TabBar ):
            
            return
            
        
        ( source_page_index, source_page_click_global_pos ) = source_tab_bar.lastClickedTabInfo()
        
        source_tab_bar.clearLastClickedTabInfo()
        
        source_notebook = source_tab_bar.parentWidget()
        source_page = source_notebook.widget( source_page_index )
        source_name = source_tab_bar.tabText( source_page_index )
        
        while w is not None:
            
            if source_page == w:
                
                # you cannot drop a page of pages inside itself
                
                return
                
            
            w = w.parentWidget()
            

        e.setDropAction( QC.Qt.MoveAction )
        
        e.accept()
        
        counter = self.count()
        
        screen_pos = self.mapToGlobal( e.pos() )
        
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
            
            dropped_on_left_edge = left_edge_rect.contains( e.pos() )
            dropped_on_right_edge = right_edge_rect.contains( e.pos() )
            
        
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

            shift_down = e.keyboardModifiers() & QC.Qt.ShiftModifier

            follow_dropped_page = not shift_down

            new_options = HG.client_controller.new_options

            if new_options.GetBoolean( 'reverse_page_shift_drag_behaviour' ):
                
                follow_dropped_page = not follow_dropped_page
                
            
            if follow_dropped_page:
                
                self.setCurrentIndex( self.indexOf( source_page ) )
                
            else:
                
                if source_page_index > 1:
                    
                    neighbour_page = source_notebook.widget( source_page_index - 1 )
                    
                    page_key = neighbour_page.GetPageKey()
                    
                else:
                    
                    page_key = source_notebook.GetPageKey()
                    
                
                HG.client_controller.gui.ShowPage( page_key )
                
            
        
        self.pageDragAndDropped.emit( source_page, source_tab_bar )
        
    
def DeleteAllNotebookPages( notebook ):
    
    while notebook.count() > 0:
        
        tab = notebook.widget( 0 )
        
        notebook.removeTab( 0 )
        
        tab.deleteLater()
        
    
def SplitVertically( splitter: QW.QSplitter, w1, w2, hpos ):

    splitter.setOrientation( QC.Qt.Horizontal )

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
    
    splitter.setOrientation( QC.Qt.Vertical )
    
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


def MakeQLabelWithAlignment( label, parent, align ):
    
    res = QW.QLabel( label, parent )

    res.setAlignment( align )

    return res


class GridLayout( QW.QGridLayout ):
    
    def __init__( self, cols = 1, spacing = 2 ):
        
        QW.QGridLayout.__init__( self )
        
        self._col_count = cols
        self.setMargin( 2 )
        self.setSpacing( spacing )
        
    def GetFixedColumnCount( self ):
        
        return self._col_count

    def setMargin( self, val ):
        
        self.setContentsMargins( val, val, val, val )
        
    
def AddToLayout( layout, item, flag = None, alignment = None ):

    if isinstance( layout, GridLayout ):
        
        cols = layout.GetFixedColumnCount()
        
        count = layout.count()
        
        row = math.floor( count / cols )
        
        col = count % cols
        
        if isinstance( item, QW.QLayout ):
            
            layout.addLayout( item, row, col )
            
        elif isinstance( item, QW.QWidget ):
            
            layout.addWidget( item, row, col )
            
        elif isinstance( item, tuple ):
            
            spacer = QW.QPushButton()#QW.QSpacerItem( 0, 0, QW.QSizePolicy.Expanding, QW.QSizePolicy.Fixed )
            layout.addWidget( spacer, row, col )
            spacer.setVisible(False)
            
            return
            
        
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
        
    elif flag in ( CC.FLAGS_CENTER, CC.FLAGS_ON_LEFT, CC.FLAGS_ON_RIGHT, CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH ):
        
        if flag == CC.FLAGS_CENTER:
            
            alignment = QC.Qt.AlignVCenter | QC.Qt.AlignHCenter
            
        if flag == CC.FLAGS_ON_LEFT:
            
            alignment = QC.Qt.AlignLeft | QC.Qt.AlignVCenter
            
        elif flag == CC.FLAGS_ON_RIGHT:
            
            alignment = QC.Qt.AlignRight | QC.Qt.AlignVCenter
            
        elif flag in ( CC.FLAGS_CENTER_PERPENDICULAR, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH ):
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                alignment = QC.Qt.AlignVCenter
                
            else:
                
                alignment = QC.Qt.AlignHCenter
                
            
        
        layout.setAlignment( item, alignment )
        
        if flag == CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH:
            
            if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
                
                layout.setStretchFactor( item, 5 )
                
            
        
        if isinstance( item, QW.QLayout ):
            
            zero_border = True
            
        
    elif flag in ( CC.FLAGS_EXPAND_PERPENDICULAR, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_PERPENDICULAR:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            if isinstance( layout, QW.QHBoxLayout ):
                
                h_policy = QW.QSizePolicy.Fixed
                v_policy = QW.QSizePolicy.Expanding
                
            else:
                
                h_policy = QW.QSizePolicy.Expanding
                v_policy = QW.QSizePolicy.Fixed
                
            
            item.setSizePolicy( h_policy, v_policy )
            
        
    elif flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE, CC.FLAGS_EXPAND_BOTH_WAYS_SHY ):
        
        if flag == CC.FLAGS_EXPAND_SIZER_BOTH_WAYS:
            
            zero_border = True
            
        
        if isinstance( item, QW.QWidget ):
            
            item.setSizePolicy( QW.QSizePolicy.Expanding, QW.QSizePolicy.Expanding )
            
        
        if isinstance( layout, QW.QVBoxLayout ) or isinstance( layout, QW.QHBoxLayout ):
            
            if flag in ( CC.FLAGS_EXPAND_BOTH_WAYS, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS ):
                
                stretch_factor = 5
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_POLITE:
                
                stretch_factor = 3
                
            elif flag == CC.FLAGS_EXPAND_BOTH_WAYS_SHY:
                
                stretch_factor = 1
                
            
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
    
def AdjustOpacity( image, opacity_factor ):
    
    new_image = QG.QImage( image.width(), image.height(), QG.QImage.Format_RGBA8888 )
    
    new_image.fill( QC.Qt.transparent )
    
    painter = QG.QPainter( new_image )
    
    painter.setOpacity( opacity_factor )
    
    painter.drawImage( 0, 0, image )
    
    return new_image

def ToKeySequence( modifiers, key ):
    
    if isinstance( modifiers, QC.Qt.KeyboardModifiers ):
        
        seq_str = ''
        
        for modifier in [ QC.Qt.ShiftModifier, QC.Qt.ControlModifier, QC.Qt.AltModifier, QC.Qt.MetaModifier, QC.Qt.KeypadModifier, QC.Qt.GroupSwitchModifier ]:
            
            if modifiers & modifier: seq_str += QG.QKeySequence( modifier ).toString()
            
        seq_str += QG.QKeySequence( key ).toString()
            
        return QG.QKeySequence( seq_str )
            
    else: return QG.QKeySequence( key + modifiers )


def AddShortcut( widget, modifier, key, callable, *args ):
    
    shortcut = QW.QShortcut( widget )
    
    shortcut.setKey( ToKeySequence( modifier, key ) )
    
    shortcut.setContext( QC.Qt.WidgetWithChildrenShortcut )
    
    shortcut.activated.connect( lambda: callable( *args ) )
    
class BusyCursor:
    
    def __enter__( self ):
        
        QW.QApplication.setOverrideCursor( QC.Qt.WaitCursor )
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        QW.QApplication.restoreOverrideCursor()


def GetBackgroundColour( widget ):
    
    return widget.palette().color( QG.QPalette.Window )


CallAfterEventType = QC.QEvent.Type( QC.QEvent.registerEventType() )

class CallAfterEvent( QC.QEvent ):
    
    def __init__( self, fn, *args, **kwargs ):
        
        QC.QEvent.__init__( self, CallAfterEventType )
        
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        
    
    def Execute( self ):
        
        if self._fn is not None:
            
            self._fn( *self._args, **self._kwargs )
            
        
    
class CallAfterEventCatcher( QC.QObject ):
    
    def __init__( self, parent ):
        
        QC.QObject.__init__( self, parent )
        
        self.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == CallAfterEventType and isinstance( event, CallAfterEvent ):
            
            if HG.profile_mode:
                
                summary = 'Profiling CallAfter Event: {}'.format( event._fn )
                
                HydrusData.Profile( summary, 'event.Execute()', globals(), locals(), min_duration_ms = HG.callto_profile_min_job_time_ms )
                
            else:
                
                event.Execute()
                
            
            event.accept()
            
            return True
            
        
        return False
        

def CallAfter( fn, *args, **kwargs ):
    
    QW.QApplication.instance().postEvent( QW.QApplication.instance().call_after_catcher, CallAfterEvent( fn, *args, **kwargs ) )
    
    QW.QApplication.instance().eventDispatcher().wakeUp()
    
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
        
    
def GetClientData( widget, idx ):
    
    if isinstance( widget, QW.QComboBox ):
        
        return widget.itemData( idx, QC.Qt.UserRole )
    
    
    elif isinstance( widget, QW.QTreeWidget ):
        
        return widget.topLevelItem( idx ).data( 0, QC.Qt.UserRole )
    
    elif isinstance( widget, QW.QListWidget ):
        
        return widget.item( idx ).data( QC.Qt.UserRole )
    
    else:
        
        raise ValueError( 'Unknown widget class in GetClientData' )


def Unsplit( splitter, widget ):
    
    if widget.parentWidget() == splitter:
        
        widget.setVisible( False )
        
    
def GetSystemColour( colour ):
    
    return QG.QPalette().color( colour )

def CenterOnWindow( parent, window ):
    
    parent_window = parent.window()
    
    window.move( parent_window.frameGeometry().center() - window.rect().center() )

def ListWidgetDelete( widget, idx ):
    
    if isinstance( idx, QC.QModelIndex ):
        
        idx = idx.row()
    
    if idx != -1:
        
        item = widget.takeItem( idx )
        
        del item


def ListWidgetGetSelection( widget ):
    
    for i in range( widget.count() ):

        if widget.item( i ).isSelected(): return i

    return -1


def ListWidgetGetStrings( widget ):
    
    strings = []
    
    for i in range( widget.count() ):
        
        strings.append( widget.item( i ).text() )
        
    return strings


def ListWidgetIsSelected( widget, idx ):
    
    if idx == -1: return False
    
    return widget.item( idx ).isSelected()


def ListWidgetSetSelection( widget, idxs ):
    
    widget.clearSelection()

    if not isinstance( idxs, list ):
        
        idxs = [ idxs ]
        
    
    count = widget.count()
    
    for idx in idxs:
        
        if 0 <= idx <= count -1:
            
            widget.item( idx ).setSelected( True )
            
        
    
def MakeQSpinBox( parent = None, initial = None, min = None, max = None, width = None ):
    
    spinbox = QW.QSpinBox( parent )
    
    if min is not None: spinbox.setMinimum( min )
    
    if max is not None: spinbox.setMaximum( max )
    
    if initial is not None: spinbox.setValue( initial )
    
    if width is not None: spinbox.setMinimumWidth( width )

    return spinbox


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
        
    
def SetStringSelection( combobox, string ):
    
    index = combobox.findText( string )
    
    if index != -1:
        
        combobox.setCurrentIndex( index )


def SetClientSize( widget, size ):
    
    if isinstance( size, tuple ):

        size = QC.QSize( size[ 0 ], size[ 1 ] )

    if size.width() < 0: size.setWidth( widget.width() )
    if size.height() < 0: size.setHeight( widget.height() )

    widget.resize( size )


def SetMinClientSize( widget, size ):
    
    if isinstance( size, tuple ):
        
        size = QC.QSize( size[0], size[1] )
        
    
    if size.width() >= 0: widget.setMinimumWidth( size.width() )
    if size.height() >= 0: widget.setMinimumHeight( size.height() )


class StatusBar( QW.QStatusBar ):
    
    def __init__( self, status_widths ):
        
        QW.QStatusBar.__init__( self )
        
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
            
            cell.setToolTip( tooltip )
            
        
    
class AboutDialogInfo:
    
    def __init__( self ):
        
        self.name = ''
        self.version = ''
        self.description = ''
        self.license = ''
        self.developers = []
        self.website = ''

    def SetName( self, name ):
        
        self.name = name


    def SetVersion( self, version ):
        
        self.version = version


    def SetDescription( self, description ):
        
        self.description = description


    def SetLicense( self, license ):
        
        self.license = license


    def SetDevelopers( self, developers_list ):
        
        self.developers = developers_list


    def SetWebSite( self, url ):
        
        self.website = url


class UIActionSimulator:
    
    def __init__( self ):
        
        pass
        
    
    def Char( self, widget, key, text = None ):
        
        if widget is None:
            
            widget = QW.QApplication.focusWidget()
            
        
        ev1 = QG.QKeyEvent( QC.QEvent.KeyPress, key, QC.Qt.NoModifier, text = text )
        ev2 = QG.QKeyEvent( QC.QEvent.KeyRelease, key, QC.Qt.NoModifier, text = text )
        
        QW.QApplication.instance().postEvent( widget, ev1 )
        QW.QApplication.instance().postEvent( widget, ev2 )
        

class AboutBox( QW.QDialog ):
    
    def __init__( self, parent, about_info ):
        
        QW.QDialog.__init__( self, parent )
        
        self.setWindowFlag( QC.Qt.WindowContextHelpButtonHint, on = False )
        
        self.setAttribute( QC.Qt.WA_DeleteOnClose )
        
        self.setWindowIcon( QG.QIcon( HG.client_controller.frame_icon_pixmap ) )
        
        layout = QW.QVBoxLayout( self )
        
        self.setWindowTitle( 'About ' + about_info.name )
        
        icon_label = QW.QLabel( self )
        name_label = QW.QLabel( about_info.name, self )
        version_label = QW.QLabel( about_info.version, self )
        tabwidget = QW.QTabWidget( self )
        desc_panel = QW.QWidget( self )
        desc_label = QW.QLabel( about_info.description, self )
        url_label = QW.QLabel( '<a href="{0}">{0}</a>'.format( about_info.website ), self )
        credits = QW.QTextEdit( self )
        license = QW.QTextEdit( self )
        close_button = QW.QPushButton( 'close', self )
        icon_label.setPixmap( HG.client_controller.frame_icon_pixmap )
        layout.addWidget( icon_label, alignment = QC.Qt.AlignHCenter )
        
        name_label_font = name_label.font()
        name_label_font.setBold( True )
        name_label.setFont( name_label_font )
        layout.addWidget( name_label, alignment = QC.Qt.AlignHCenter )
        
        layout.addWidget( version_label, alignment = QC.Qt.AlignHCenter )
        
        layout.addWidget( tabwidget, alignment =  QC.Qt.AlignHCenter )
        tabwidget.addTab( desc_panel, 'Description' )
        tabwidget.addTab( credits, 'Credits' )
        tabwidget.addTab( license, 'License' )
        tabwidget.setCurrentIndex( 0 )
        
        credits.setPlainText( 'Created by ' + ', '.join(about_info.developers) )
        credits.setReadOnly( True )
        credits.setAlignment( QC.Qt.AlignHCenter )
        
        license.setPlainText( about_info.license )
        license.setReadOnly( True )
        
        desc_layout = QW.QVBoxLayout()
        
        desc_layout.addWidget( desc_label, alignment = QC.Qt.AlignHCenter )
        desc_label.setWordWrap( True )
        desc_label.setAlignment( QC.Qt.AlignHCenter | QC.Qt.AlignVCenter )
        desc_layout.addWidget( url_label, alignment = QC.Qt.AlignHCenter )
        url_label.setTextFormat( QC.Qt.RichText )
        url_label.setTextInteractionFlags( QC.Qt.TextBrowserInteraction )
        url_label.setOpenExternalLinks( True )
        desc_panel.setLayout( desc_layout )
        
        layout.addWidget( close_button, alignment = QC.Qt.AlignRight )
        close_button.clicked.connect( self.accept )
        
        self.setLayout( layout )
        
        self.exec_()

class RadioBox( QW.QFrame ):
    
    radioBoxChanged = QC.Signal()
    
    def __init__( self, parent = None, choices = [], vertical = False ):
    
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        
        if vertical:
            
            self.setLayout( VBoxLayout() )
            
        else:
            
            self.setLayout( HBoxLayout() )
            
        
        self._choices = []
        
        for choice in choices:
            
            radiobutton = QW.QRadioButton( choice, self )
            
            self._choices.append( radiobutton )
            
            radiobutton.clicked.connect( self.radioBoxChanged )
            
            self.layout().addWidget( radiobutton )
            
        if vertical and len( self._choices ):
            
            self._choices[0].setChecked( True )
        
        elif len( self._choices ):
            
            self._choices[-1].setChecked( True )
        
        
    def GetCurrentIndex( self ):
        
        for i in range( len( self._choices ) ):
            
            if self._choices[ i ].isChecked(): return i
            
        return -1
    
    
    def SetStringSelection( self, str ):

        for i in range( len( self._choices ) ):

            if self._choices[ i ].text() == str:
                
                self._choices[ i ].setChecked( True )
                
                return
                
            
        
    
    def GetStringSelection( self ):

        for i in range( len( self._choices ) ):

            if self._choices[ i ].isChecked(): return self._choices[ i ].text()

        return None
    
    def SetValue( self, data ):
        
        pass
        
    
    def Select( self, idx ):
    
        self._choices[ idx ].setChecked( True )


# Adapted from https://doc.qt.io/qt-5/qtwidgets-widgets-elidedlabel-example.html
class EllipsizedLabel( QW.QLabel ):
    
    def __init__( self, parent = None, ellipsize_end = False ):
        
        QW.QLabel.__init__( self, parent )
        
        self._ellipsize_end = ellipsize_end
        
    
    def minimumSizeHint( self ):
        
        if self._ellipsize_end:
            
            return self.sizeHint()
            
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
            
            num_lines = self.text().count( '\n' ) + 1
            
            line_width = self.fontMetrics().lineWidth()
            line_height = self.fontMetrics().lineSpacing()
            
            size_hint = QC.QSize( 3 * line_width, num_lines * line_height )
            
        else:
            
            size_hint = QW.QLabel.sizeHint( self )
            
        
        return size_hint
        
    
    def paintEvent( self, event ):

        if not self._ellipsize_end:
            
            QW.QLabel.paintEvent( self, event )
            
            return
            
        
        painter = QG.QPainter( self )

        fontMetrics = painter.fontMetrics()

        text_lines = self.text().split( '\n' )
        
        line_spacing = fontMetrics.lineSpacing()
        
        current_y = 0
        
        done = False
        
        my_width = self.width()
        
        for text_line in text_lines:
            
            elided_line = fontMetrics.elidedText( text_line, QC.Qt.ElideRight, my_width )
            
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
                
                    elided_last_line = fontMetrics.elidedText( last_line, QC.Qt.ElideRight, self.width() )
                
                    painter.drawText( QC.QPoint( 0, y + fontMetrics.ascent() ), elided_last_line )
                    
                    done = True
                    
                    break
                    
                

            text_layout.endLayout()
            
            if done: break
            '''
            
        

class Dialog( QW.QDialog ):
    
    def __init__( self, parent = None, **kwargs ):

        title = None 
        
        if 'title' in kwargs:
            
            title = kwargs['title']
            
            del kwargs['title']
            
        
        QW.QDialog.__init__( self, parent, **kwargs )
        
        self.setWindowFlag( QC.Qt.WindowContextHelpButtonHint, on = False )
        
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
        
        Dialog.__init__( self, parent )
        
        self.setWindowTitle( caption )
        
        self._ok_button = QW.QPushButton( 'OK', self )
        self._ok_button.clicked.connect( self.accept )
        
        self._cancel_button = QW.QPushButton( 'Cancel', self )
        self._cancel_button.clicked.connect( self.reject )
        
        self._password = QW.QLineEdit( self )
        self._password.setEchoMode( QW.QLineEdit.Password )
        
        self.setLayout( QW.QVBoxLayout() )
        
        entry_layout = QW.QHBoxLayout()
        
        entry_layout.addWidget( QW.QLabel( message, self ) )
        entry_layout.addWidget( self._password )
        
        button_layout = QW.QHBoxLayout()
        
        button_layout.addStretch( 1 )
        button_layout.addWidget( self._cancel_button )
        button_layout.addWidget( self._ok_button )
        
        self.layout().addLayout( entry_layout )
        self.layout().addLayout( button_layout )
        

    def GetValue( self ):
        
        return self._password.text()
        

class DirDialog( QW.QFileDialog ):

    def __init__( self, parent = None, message = None ):
        
        QW.QFileDialog.__init__( self, parent )
        
        if message is not None: self.setWindowTitle( message )
        
        self.setAcceptMode( QW.QFileDialog.AcceptOpen )
        
        self.setFileMode( QW.QFileDialog.Directory )
        
        self.setOption( QW.QFileDialog.ShowDirsOnly, True )
        
        if HG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.DontUseNativeDialog, True )
            
        
    
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
    
    def __init__( self, parent = None, message = None, acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFile, default_filename = None, default_directory = None, wildcard = None, defaultSuffix = None ):
        
        QW.QFileDialog.__init__( self, parent )
        
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
            
            self.setNameFilter( wildcard )
            
        
        if HG.client_controller.new_options.GetBoolean( 'use_qt_file_dialogs' ):
            
            self.setOption( QW.QFileDialog.DontUseNativeDialog, True )
            
        

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
        
        QW.QTreeWidget.__init__( self, *args, **kwargs )
        
        self.itemClicked.connect( self._HandleItemClickedForCheckStateUpdate )
        
    
    def _HandleItemClickedForCheckStateUpdate( self, item, column ):
        
        self._UpdateCheckState( item, item.checkState( 0 ) )
        
    
    def _UpdateCheckState( self, item, check_state ):
        
        # this is an int, should be a checkstate
        item.setCheckState( 0, check_state )
        
        for i in range( item.childCount() ):
            
            self._UpdateCheckState( item.child( i ), check_state )
            
        
    
class ColourPickerCtrl( QW.QPushButton ):
    
    def __init__( self, parent = None ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._colour = QG.QColor( 0, 0, 0, 0 )
        
        self.clicked.connect( self._ChooseColour )
        
        self._highlighted = False
    
    
    def SetColour( self, colour ):
        
        self._colour = colour

        self._UpdatePixmap()
        

    def _UpdatePixmap( self ):
        
        px = QG.QPixmap( self.contentsRect().height(), self.contentsRect().height() )
        
        painter = QG.QPainter( px )
        
        colour = self._colour
        
        if self._highlighted:
            
            colour = self._colour.lighter( 125 ) # 25% lighter
            
        
        painter.fillRect( px.rect(), QG.QBrush( colour ) )
        
        painter.end()
        
        self.setIcon( QG.QIcon( px ) )
        
        self.setIconSize( px.size() )
        
        self.setFlat( True )
        
        self.setFixedSize( px.size() )
        
    
    def enterEvent( self, event ):
        
        self._highlighted = True
        
        self._UpdatePixmap()
        
    
    def leaveEvent( self, event ):
        
        self._highlighted = False
        
        self._UpdatePixmap()
        
    
    def GetColour( self ):
        
        return self._colour
        
    
    def _ChooseColour( self ):
        
        new_colour = QW.QColorDialog.getColor( initial = self._colour )
        
        if new_colour.isValid():
            
            self.SetColour( new_colour )
            
        
    
def ListsToTuples( l ): # Since lists are not hashable, we need to (recursively) convert lists to tuples in data that is to be added to BetterListCtrl
    
    if isinstance( l, list ) or isinstance( l, tuple ):

        return tuple( map( ListsToTuples, l ) )

    else:
        
        return l


class WidgetEventFilter ( QC.QObject ):
    
    _mouse_tracking_required = { 'EVT_MOUSE_EVENTS' }

    _strong_focus_required = { 'EVT_KEY_DOWN' }

    def __init__( self, parent_widget ):

        self._parent_widget = parent_widget
        
        QC.QObject.__init__( self, parent_widget )
        
        parent_widget.installEventFilter( self )
        
        self._callback_map = defaultdict( list )
        
        self._user_moved_window = False # There is no EVT_MOVE_END in Qt so some trickery is required.

    def _ExecuteCallbacks( self, event_name, event ):
        
        if not event_name in self._callback_map: return
        
        event_killed = False
        
        for callback in self._callback_map[ event_name ]:
            
            if not callback( event ): event_killed = True
            
        return event_killed


    def eventFilter( self, watched, event ):
        
        # Once somehow this got called with no _parent_widget set - which is probably fixed now but leaving the check just in case, wew
        # Might be worth debugging this later if it still occurs - the only way I found to reproduce it is to run the help > debug > initialize server command
        if not hasattr( self, '_parent_widget') or not isValid( self._parent_widget ): return False
        
        type = event.type()
        
        event_killed = False
        
        if type == QC.QEvent.KeyPress:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_KEY_DOWN', event )
            
        elif type == QC.QEvent.Close:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_CLOSE', event )
            
        elif type == QC.QEvent.WindowStateChange:
            
            if isValid( self._parent_widget ):
                
                if self._parent_widget.isMinimized() or (event.oldState() & QC.Qt.WindowMinimized): event_killed = event_killed or self._ExecuteCallbacks( 'EVT_ICONIZE', event )
            
                if self._parent_widget.isMaximized() or (event.oldState() & QC.Qt.WindowMaximized): event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MAXIMIZE', event )
        
        elif type == QC.QEvent.MouseMove:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
            
        elif type == QC.QEvent.MouseButtonDblClick:
            
            if event.button() == QC.Qt.LeftButton:
            
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DCLICK', event )
                
            elif event.button() == QC.Qt.RightButton:

                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DCLICK', event )

            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
            
        elif type == QC.QEvent.MouseButtonPress:
            
            if event.buttons() & QC.Qt.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_DOWN', event )
            
            if event.buttons() & QC.Qt.MiddleButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MIDDLE_DOWN', event )
            
            if event.buttons() & QC.Qt.RightButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_RIGHT_DOWN', event )

            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
            
        elif type == QC.QEvent.MouseButtonRelease:
            
            if event.buttons() & QC.Qt.LeftButton: event_killed = event_killed or self._ExecuteCallbacks( 'EVT_LEFT_UP', event )

            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
            
        elif type == QC.QEvent.Wheel:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSEWHEEL', event )
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOUSE_EVENTS', event )
        
        elif type == QC.QEvent.Scroll:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_SCROLLWIN', event )
            
        elif type == QC.QEvent.Move:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOVE', event )
            
            if isValid( self._parent_widget ) and self._parent_widget.isVisible():
                
                self._user_moved_window = True
            
        elif type == QC.QEvent.Resize:
            
            event_killed = event_killed or self._ExecuteCallbacks( 'EVT_SIZE', event )
            
        elif type == QC.QEvent.NonClientAreaMouseButtonPress:
            
            self._user_moved_window = False
        
        elif type == QC.QEvent.NonClientAreaMouseButtonRelease:
            
            if self._user_moved_window:
                
                event_killed = event_killed or self._ExecuteCallbacks( 'EVT_MOVE_END', event )
                
                self._user_moved_window = False
                
            
        
        if event_killed:
            
            event.accept()
            
            return True
            
        
        return False

    
    def _AddCallback( self, evt_name, callback ):
        
        if evt_name in self._mouse_tracking_required:
            
            self._parent_widget.setMouseTracking( True )
            
        if evt_name in self._strong_focus_required:
            
            self._parent_widget.setFocusPolicy( QC.Qt.StrongFocus )
            
        self._callback_map[ evt_name ].append( callback )

    def EVT_CLOSE( self, callback ):
        
        self._AddCallback( 'EVT_CLOSE', callback )

    def EVT_ICONIZE( self, callback ):
        
        self._AddCallback( 'EVT_ICONIZE', callback )

    def EVT_KEY_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_KEY_DOWN', callback )

    def EVT_LEFT_DCLICK( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DCLICK', callback )

    def EVT_RIGHT_DCLICK( self, callback ):

        self._AddCallback( 'EVT_RIGHT_DCLICK', callback )
        
    def EVT_LEFT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_DOWN', callback )

    def EVT_LEFT_UP( self, callback ):
        
        self._AddCallback( 'EVT_LEFT_UP', callback )

    def EVT_MAXIMIZE( self, callback ):
        
        self._AddCallback( 'EVT_MAXIMIZE', callback )

    def EVT_MIDDLE_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_MIDDLE_DOWN', callback )

    def EVT_MOUSE_EVENTS( self, callback ):
        
        self._AddCallback( 'EVT_MOUSE_EVENTS', callback )

    def EVT_MOUSEWHEEL( self, callback ):
        
        self._AddCallback( 'EVT_MOUSEWHEEL', callback )

    def EVT_MOVE( self, callback ):
        
        self._AddCallback( 'EVT_MOVE', callback )

    def EVT_MOVE_END( self, callback ):
        
        self._AddCallback( 'EVT_MOVE_END', callback )

    def EVT_RIGHT_DOWN( self, callback ):
        
        self._AddCallback( 'EVT_RIGHT_DOWN', callback )

    def EVT_SCROLLWIN( self, callback ):
        
        self._AddCallback( 'EVT_SCROLLWIN', callback )

    def EVT_SIZE( self, callback ):
        
        self._AddCallback( 'EVT_SIZE', callback )

# wew lad
# https://stackoverflow.com/questions/46456238/checkbox-not-visible-inside-combobox
class CheckBoxDelegate(QW.QStyledItemDelegate):
    
    def __init__(self, parent=None):
        
        super( CheckBoxDelegate, self ).__init__(parent)
        

    def createEditor( self, parent, op, idx ):
        
        self.editor = QW.QCheckBox( parent )
        

class CollectComboCtrl( QW.QComboBox ):
    
    itemChanged = QC.Signal()
    
    def __init__( self, parent, media_collect ):
        
        QW.QComboBox.__init__( self, parent )
        
        self.view().pressed.connect( self._HandleItemPressed )
        
        # this was previously 'if Fusion style only', but as it works for normal styles too, it is more helpful to have it always on
        self.setItemDelegate( CheckBoxDelegate() )
        
        self.setModel( QG.QStandardItemModel( self ) )
        
        text_and_data_tuples = set()
        
        for media_sort in HG.client_controller.new_options.GetDefaultNamespaceSorts():
            
            namespaces = media_sort.GetNamespaces()
            
            try:
                
                text_and_data_tuples.update( namespaces )
                
            except:
                
                HydrusData.DebugPrint( 'Bad namespaces: {}'.format( namespaces ) )
                
                HydrusData.ShowText( 'Hey, your namespace-based sorts are likely damaged. Details have been written to the log, please let hydev know!' )
                
            
        
        text_and_data_tuples = sorted( ( ( namespace, ( 'namespace', namespace ) ) for namespace in text_and_data_tuples ) )
        
        ratings_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for ratings_service in ratings_services:
            
            text_and_data_tuples.append( ( ratings_service.GetName(), ('rating', ratings_service.GetServiceKey() ) ) )
            
        
        for ( text, data ) in text_and_data_tuples:

            self.Append( text, data )
            
        # Trick to display custom text
        
        self._cached_text = ''
        
        if media_collect.DoesACollect():
            
            CallAfter( self.SetCollectByValue, media_collect )
            
        

    def paintEvent( self, e ):
        
        painter = QW.QStylePainter( self )
        painter.setPen( self.palette().color( QG.QPalette.Text ) )

        opt = QW.QStyleOptionComboBox()
        self.initStyleOption( opt )

        opt.currentText = self._cached_text

        painter.drawComplexControl( QW.QStyle.CC_ComboBox, opt )

        painter.drawControl( QW.QStyle.CE_ComboBoxLabel, opt )
        
    
    def GetValues( self ):

        namespaces = []
        rating_service_keys = []

        for index in self.GetCheckedIndices():

            (collect_type, collect_data) = self.itemData( index, QC.Qt.UserRole )

            if collect_type == 'namespace':

                namespaces.append( collect_data )

            elif collect_type == 'rating':

                rating_service_keys.append( collect_data )

        collect_strings = self.GetCheckedStrings()

        if len( collect_strings ) > 0:
            
            description = 'collect by ' + '-'.join( collect_strings )
            
        else:

            description = 'no collections'
            

        return ( namespaces, rating_service_keys, description )


    def hidePopup(self):

        if not self.view().underMouse():
            
            QW.QComboBox.hidePopup( self )
            
            
    def SetValue( self, text ):
        
        self._cached_text = text
           
        self.setCurrentText( text )
        
        
    def SetCollectByValue( self, media_collect ):

        try:

            indices_to_check = []

            for index in range( self.count() ):

                ( collect_type, collect_data ) = self.itemData( index, QC.Qt.UserRole )

                p1 = collect_type == 'namespace' and collect_data in media_collect.namespaces
                p2 = collect_type == 'rating' and collect_data in media_collect.rating_service_keys

                if p1 or p2:
                    
                    indices_to_check.append( index )

            self.SetCheckedIndices( indices_to_check )
            
            self.itemChanged.emit()

        except Exception as e:

            HydrusData.ShowText( 'Failed to set a collect-by value!' )

            HydrusData.ShowException( e )


    def SetCheckedIndices( self, indices_to_check ):
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if idx in indices_to_check:
                
                item.setCheckState( QC.Qt.Checked )
                
            else:
                
                item.setCheckState( QC.Qt.Unchecked )
                
            
        
    
    def GetCheckedIndices( self ):
        
        indices = []
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if item.checkState() == QC.Qt.Checked: indices.append( idx )
            
        return indices


    def GetCheckedStrings( self ):

        strings = [ ]

        for idx in range( self.count() ):

            item = self.model().item( idx )

            if item.checkState() == QC.Qt.Checked: strings.append( item.text() )

        return strings


    def Append( self, str, data ):
        
        self.addItem( str, userData = data )
        
        item = self.model().item( self.count() - 1, 0 )
        
        item.setCheckState( QC.Qt.Unchecked )


    def _HandleItemPressed( self, index ):
        
        item = self.model().itemFromIndex( index )
        
        if item.checkState() == QC.Qt.Checked:
            
            item.setCheckState( QC.Qt.Unchecked )
            
        else:
            
            item.setCheckState( QC.Qt.Checked )
            
        self.SetValue( self._cached_text )
        self.itemChanged.emit()
