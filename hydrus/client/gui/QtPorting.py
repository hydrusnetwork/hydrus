#This file is licensed under the Do What the Fuck You Want To Public License aka WTFPL

# hey so this file was made by prkc to bridge innumerate wx->Qt auto-conversion problems
# I, hydev, said 'thank you very much, this is incredible work, I will slowly replace all these functions with proper Qt code within a year or so'
# and we are, of course, now many years later
# so, if I just got hit by a bus and you are wondering what the hell is going on here, that's what's going on here

import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from collections import defaultdict

from hydrus.core import HydrusData
from hydrus.core import HydrusLists

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIExceptionHandling
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtInit

isValid = QtInit.isValid

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
        
    

def AdjustOpacity( image: QG.QImage, opacity_factor ):
    
    new_image = QG.QImage( image.width(), image.height(), QG.QImage.Format.Format_RGBA8888 )
    
    new_image.setDevicePixelRatio( image.devicePixelRatio() )
    
    new_image.fill( QC.Qt.GlobalColor.transparent )
    
    painter = QG.QPainter( new_image )
    
    painter.setOpacity( opacity_factor )
    
    painter.drawImage( 0, 0, image )
    
    return new_image
    

def CenterOnWindow( parent, window ):
    
    parent_window = parent.window()
    
    window.move( parent_window.frameGeometry().center() - window.rect().center() )
    

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
        
    

def DeleteAllNotebookPages( notebook ):
    
    while notebook.count() > 0:
        
        tab = notebook.widget( 0 )
        
        notebook.removeTab( 0 )
        
        tab.deleteLater()
        
    

def GetBackgroundColour( widget ):
    
    return widget.palette().color( QG.QPalette.ColorRole.Window )
    

def ListsToTuples( potentially_nested_lists ):
    
    if HydrusLists.IsAListLikeCollection( potentially_nested_lists ):
        
        return tuple( map( ListsToTuples, potentially_nested_lists ) )
        
    else:
        
        return potentially_nested_lists
        
    

def registerEventType():
    
    if QtInit.WE_ARE_PYSIDE:
        
        return QC.QEvent.Type( QC.QEvent.registerEventType() )
        
    else:
        
        return QC.QEvent.registerEventType()
        
    

def ScrollAreaVisibleRect( scroll_area ):
    
    if not scroll_area.widget(): return QC.QRect( 0, 0, 0, 0 )
    
    rect = scroll_area.widget().visibleRegion().boundingRect()

    # Do not allow it to be smaller than the scroll area's viewport size:
    
    if rect.width() < scroll_area.viewport().width():
        
        rect.setWidth( scroll_area.viewport().width() )

    if rect.height() < scroll_area.viewport().height():
        
        rect.setHeight( scroll_area.viewport().height() )
        
    
    return rect
    

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
    

def SplitterVisibleCount( splitter ):
    
    count = 0
    
    for i in range( splitter.count() ):
        
        if splitter.widget( i ).isVisibleTo( splitter ): count += 1
        
    
    return count
    

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
        
    

def ToKeySequence( modifiers, key ):
    
    return QG.QKeySequence( QC.QKeyCombination( modifiers, key ) ) # pylint: disable=E1101
    

def Unsplit( splitter, widget ):
    
    if widget.parentWidget() == splitter:
        
        widget.setVisible( False )
        
    

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
