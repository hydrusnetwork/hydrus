from . import ClientCaches
from . import ClientConstants as CC
from . import ClientGUIFunctions
from . import ClientGUIMenus
from . import ClientGUIShortcuts
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP
from . import QtPorting as QP

CHILD_POSITION_PADDING = 24
FUZZY_PADDING = 10

def GetDisplayPosition( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).topLeft()
    
def GetDisplaySize( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).size()
    
def GetSafePosition( position ):
    
    ( p_x, p_y ) = position
    
    # some window managers size the windows just off screen to cut off borders
    # so choose a test position that's a little more lenient
    ( test_x, test_y ) = ( p_x + FUZZY_PADDING, p_y + FUZZY_PADDING )
    
    screen = QW.QApplication.screenAt( QC.QPoint( test_x, test_y ) )
    
    if screen:
    
        display_index = QW.QApplication.screens().index( screen )
        
    else:
        
        display_index = None
    
    if display_index is None:
        
        return ( -1, -1 )
        
    else:
        
        return position
        
    
def GetSafeSize( tlw, min_size, gravity ):
    
    ( min_width, min_height ) = min_size
    
    parent = tlw.parentWidget()
    
    if parent is None:
        
        width = min_width
        height = min_height
        
    else:
        
        ( parent_window_width, parent_window_height ) = parent.window().size().toTuple()
        
        ( width_gravity, height_gravity ) = gravity
        
        if width_gravity == -1:
            
            width = min_width
            
        else:
            
            max_width = parent_window_width - 2 * CHILD_POSITION_PADDING
            
            width = int( width_gravity * max_width )
            
        
        if height_gravity == -1:
            
            height = min_height
            
        else:
            
            max_height = parent_window_height - 2 * CHILD_POSITION_PADDING
            
            height = int( height_gravity * max_height )
            
        
    
    display_size = GetDisplaySize( tlw )
    
    width = min( display_size.width(), width )
    height = min( display_size.height(), height )
    
    return ( width, height )
    
def ExpandTLWIfPossible( tlw, frame_key, desired_size_delta ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    if not tlw.isMaximized() and not tlw.isFullScreen():
        
        ( current_width, current_height ) = tlw.size().toTuple()
        
        ( desired_delta_width, desired_delta_height ) = desired_size_delta
        
        desired_width = current_width
        
        if desired_delta_width > 0:
            
            desired_width = current_width + desired_delta_width + FUZZY_PADDING
            
        
        desired_height = current_height
        
        if desired_delta_height > 0:
            
            desired_height = current_height + desired_delta_height + FUZZY_PADDING
            
        
        ( width, height ) = GetSafeSize( tlw, ( desired_width, desired_height ), default_gravity )
        
        if width > current_width or height > current_height:
            
            size = QC.QSize( width, height )
            
            tlw.resize( size )
            
            #tlw.setMinimumSize( tlw.sizeHint() )
            
            SlideOffScreenTLWUpAndLeft( tlw )
            
        
    
def MouseIsOnMyDisplay( window ):
    
    window_handle = window.window().windowHandle()
    
    if window_handle is None:
        
        return False
        
    
    window_screen = window_handle.screen()
    
    mouse_screen = QW.QApplication.screenAt( QG.QCursor.pos() )
    
    return mouse_screen is window_screen
    
def SaveTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    maximised = tlw.isMaximized()
    fullscreen = tlw.isFullScreen()
    
    if not ( maximised or fullscreen ):
        
        safe_position = GetSafePosition( ( tlw.x(), tlw.y() ) )
        
        if safe_position != ( -1, -1 ):
            
            last_size = tlw.size().toTuple()
            last_position = safe_position
            
        
    
    new_options.SetFrameLocation( frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
    
def SetInitialTLWSizeAndPosition( tlw, frame_key ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    parent = tlw.parentWidget()
    
    if remember_size and last_size is not None:
        
        ( width, height ) = last_size
        
        tlw.resize( QC.QSize( width, height ) )
        
    else:
        
        ( min_width, min_height ) = QP.GetEffectiveMinSize( tlw )
        
        ( width, height ) = GetSafeSize( tlw, ( min_width, min_height ), default_gravity )
        
    
    tlw.resize( QC.QSize( width, height ) )
    
    min_width = min( 240, width )
    min_height = min( 240, height )
    
    tlw.setMinimumSize( QP.TupleToQSize( ( min_width, min_height ) ) )
    
    #
    
    if remember_position and last_position is not None:
        
        safe_position = GetSafePosition( last_position )
        
        if safe_position != QC.QPoint( -1, -1 ):
            
            tlw.move( QP.TupleToQPoint( safe_position ) )
            
        
    elif default_position == 'topleft':
        
        if parent is not None:
            
            if isinstance( parent, QW.QWidget ):
                
                parent_tlp = parent.window()
                
            else:
                
                parent_tlp = parent
                
            
            ( parent_x, parent_y ) = parent_tlp.pos().toTuple()
            
            tlw.move( QP.TupleToQPoint( ( parent_x + CHILD_POSITION_PADDING, parent_y + CHILD_POSITION_PADDING ) ) )
            
        else:
            
            safe_position = GetSafePosition( ( 0 + CHILD_POSITION_PADDING, 0 + CHILD_POSITION_PADDING ) )
            
            if safe_position != QC.QPoint( -1, -1 ):
                
                tlw.move( QP.TupleToQPoint( safe_position ) )
                
            
        
        SlideOffScreenTLWUpAndLeft( tlw )
        
    elif default_position == 'center':
        
        QP.CallAfter( QP.Center, tlw )
        
    
    # Comment from before the Qt port: if these aren't callafter, the size and pos calls don't stick if a restore event happens
    
    if maximised:
        
        QP.CallAfter( tlw.showMaximized )
        
    
    if fullscreen and not HC.PLATFORM_OSX:
        
        QP.CallAfter( tlw.showFullScreen )
        
    
def SlideOffScreenTLWUpAndLeft( tlw ):
    
    ( tlw_width, tlw_height ) = tlw.size().toTuple()
    ( tlw_x, tlw_y ) = tlw.pos().toTuple()
    
    tlw_right = tlw_x + tlw_width
    tlw_bottom = tlw_y + tlw_height
    
    display_size = GetDisplaySize( tlw )
    display_pos = GetDisplayPosition( tlw )
    
    display_right = display_pos.x() + display_size.width()
    display_bottom = display_pos.y() + display_size.height()
    
    move_x = tlw_right > display_right
    move_y = tlw_bottom > display_bottom
    
    if move_x or move_y:
        
        delta_x = min( display_right - tlw_right, 0 )
        delta_y = min( display_bottom - tlw_bottom, 0 )
        
        tlw.move( QP.TupleToQPoint( (tlw_x+delta_x,tlw_y+delta_y) ) )
        
    
class NewDialog( QP.Dialog ):
    
    def __init__( self, parent, title ):
        
        QP.Dialog.__init__( self, parent )
        self.setWindowTitle( title )
        
        self._consumed_esc_to_cancel = False
        
        self._last_move_pub = 0.0
        
        self._new_options = HG.client_controller.new_options
        
        QP.SetBackgroundColour( self, QP.GetSystemColour( QG.QPalette.Button ) )
        
        self.setWindowIcon( QG.QIcon( HG.client_controller.frame_icon_pixmap ) )
        
        HG.client_controller.ResetIdleTimer()
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
    
    def moveEvent( self, event ):
        
        if HydrusData.TimeHasPassedFloat( self._last_move_pub + 0.1 ):
            
            HG.client_controller.pub( 'top_level_window_move_event' )
            
            self._last_move_pub = HydrusData.GetNowPrecise()
            
        
        event.ignore()
        
    
    def _CanCancel( self ):
        
        return True
        
    
    def _CanOK( self ):
        
        return True
        
    
    def _ReadyToClose( self, value ):
        
        return True
        
    
    def _SaveOKPosition( self ):
        
        pass
        
    
    def _TryEndModal( self, value ):
        
        if not self.isModal(): # in some rare cases (including spammy AutoHotkey, looks like), this can be fired before the dialog can clean itself up
            
            return
            
        
        if not self._ReadyToClose( value ):
            
            return
            
        
        if value == QW.QDialog.Rejected:
            
            if not self._CanCancel():
                
                return
                
            self.SetCancelled( True )
            
        
        if value == QW.QDialog.Accepted:
            
            if not self._CanOK():
                
                return
                
            
            self._SaveOKPosition()
            
        
        self.CleanBeforeDestroy()
        
        try:
            
            self.done( value )
            
        except Exception as e:
            
            HydrusData.ShowText( 'This dialog seems to have been unable to close for some reason. I am printing the stack to the log. The dialog may have already closed, or may attempt to close now. Please inform hydrus dev of this situation. I recommend you restart the client if you can. If the UI is locked, you will have to kill it via task manager.' )
            
            HydrusData.PrintException( e )
            
            import traceback
            
            HydrusData.DebugPrint( ''.join( traceback.format_stack() ) )
            
            try:
                
                self.close()
                
            except:
                
                HydrusData.ShowText( 'The dialog would not close on command.' )
                
            
            try:
                
                self.deleteLater()
                
            except:
                
                HydrusData.ShowText( 'The dialog would not destroy on command.' )
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def DoOK( self ):
        
        self._TryEndModal( QW.QDialog.Accepted )
        
    
    def EventClose( self, event ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        self._TryEndModal( QW.QDialog.Rejected )
        
    
    def EventDialogButtonApply( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        event_object = self.sender()
        
        if event_object is not None:
            
            tlp = event_object.window()
            
            if tlp != self:
                
                return
                
        self._TryEndModal( QW.QDialog.Accepted )


    def EventDialogButtonCancel( self ):

        if not self or not QP.isValid( self ):
            return

        event_object = self.sender()

        if event_object is not None:

            tlp = event_object.window()

            if tlp != self:
                return

        self._TryEndModal( QW.QDialog.Rejected )
        
    
    def EventOK( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._TryEndModal( QW.QDialog.Accepted )
        
    
    def keyPressEvent( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        current_focus = QW.QApplication.focusWidget()
        
        event_from_us = current_focus is not None and ClientGUIFunctions.IsQtAncestor( current_focus, self )
        
        if event_from_us and key == QC.Qt.Key_Escape and not self._consumed_esc_to_cancel:
            
            self._consumed_esc_to_cancel = True
            
            self._TryEndModal( QW.QDialog.Rejected )
            
        else:
            
            QP.Dialog.keyPressEvent( self, event )
            
        
    
class DialogThatResizes( NewDialog ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key
        
        NewDialog.__init__( self, parent, title )
        
    
    def _SaveOKPosition( self ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
    
class DialogThatTakesScrollablePanel( DialogThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False ):
        
        self._panel = None
        self._hide_buttons = hide_buttons
        
        DialogThatResizes.__init__( self, parent, title, frame_key )
        
        self._InitialiseButtons()
        
    
    def _CanCancel( self ):
        
        return self._panel.CanCancel()
        
    
    def _CanOK( self ):
        
        return self._panel.CanOK()
        
    
    def _GetButtonBox( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseButtons( self ):
        
        raise NotImplementedError()
        
    
    def CleanBeforeDestroy( self ):
        
        DialogThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        if hasattr( self._panel, 'okSignal'): self._panel.okSignal.connect( self.EventOK )
        
        buttonbox = self._GetButtonBox()
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if buttonbox is not None:
            
            QP.AddToLayout( vbox, buttonbox, CC.FLAGS_BUTTON_SIZER )
            
        
        self.setLayout( vbox )
        
        SetInitialTLWSizeAndPosition( self, self._frame_key )
        
    
class DialogNullipotent( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttonbox, self._close )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._close = QW.QPushButton( 'close', self )
        self._close.clicked.connect( self.EventOK )
        
        if self._hide_buttons:
            
            self._close.setVisible( False )
            
            self._widget_event_filter.EVT_CLOSE( lambda ev: self.EventOK() ) # the close event no longer goes to the default button, since it is hidden, wew
            
        
    
    def _ReadyToClose( self, value ):
        
        try:
            
            self._panel.TryToClose()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                QW.QMessageBox.critical( self, 'Error', message )
                
            
            return False
            
        
    
class DialogApplyCancel( DialogThatTakesScrollablePanel ):
    
    def _GetButtonBox( self ):
        
        buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttonbox, self._apply )
        QP.AddToLayout( buttonbox, self._cancel )
        
        return buttonbox
        
    
    def _InitialiseButtons( self ):
        
        self._apply = QW.QPushButton( 'apply', self )
        QP.SetForegroundColour( self._apply, (0,128,0) )
        self._apply.clicked.connect( self.EventDialogButtonApply )
        
        self._cancel = QW.QPushButton( 'cancel', self )
        QP.SetForegroundColour( self._cancel, (128,0,0) )
        self._cancel.clicked.connect( self.EventDialogButtonCancel )
        
        if self._hide_buttons:
            
            self._apply.setVisible( False )
            self._cancel.setVisible( False )
            
            self._widget_event_filter.EVT_CLOSE( self.EventClose ) # the close event no longer goes to the default button, since it is hidden, wew
            
        
    
class DialogEdit( DialogApplyCancel ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False ):
        
        DialogApplyCancel.__init__( self, parent, title, frame_key = frame_key, hide_buttons = hide_buttons )
        
    
    def _ReadyToClose( self, value ):
        
        if value != QW.QDialog.Accepted:
            
            return True
            
        
        try:
            
            value = self._panel.GetValue()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                QW.QMessageBox.critical( self, 'Error', message )
                
            
            return False
            
        
    
class DialogManage( DialogApplyCancel ):
    
    def _ReadyToClose( self, value ):
        
        if value != QW.QDialog.Accepted:
            
            return True
            
        
        try:
            
            self._panel.CommitChanges()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                QW.QMessageBox.critical( self, 'Error', message )
                
            
            return False
            
        
    
class DialogCustomButtonQuestion( DialogThatTakesScrollablePanel ):
    
    def __init__( self, parent, title, frame_key = 'regular_center_dialog' ):
        
        DialogThatTakesScrollablePanel.__init__( self, parent, title, frame_key = frame_key )
        
    
    def _GetButtonBox( self ):
        
        return None
        
    
    def _InitialiseButtons( self ):
        
        pass
        
    
class Frame( QW.QWidget ):
    
    def __init__( self, parent, title ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setWindowTitle( title )
        
        self.setWindowFlags( QC.Qt.Window )
        self.setWindowFlag( QC.Qt.WindowContextHelpButtonHint, on = False )
        self.setAttribute( QC.Qt.WA_DeleteOnClose )
        
        self._new_options = HG.client_controller.new_options
        
        self._last_move_pub = 0.0
        
        QP.SetBackgroundColour( self, QP.GetSystemColour( QG.QPalette.Button ) )
        
        self.setWindowIcon( QG.QIcon( HG.client_controller.frame_icon_pixmap ) )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_CLOSE( self.EventAboutToClose )
        self._widget_event_filter.EVT_MOVE( self.EventMove )
        
        HG.client_controller.ResetIdleTimer()
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def EventAboutToClose( self, event ):
        
        self.CleanBeforeDestroy()
        
        return True # was: event.ignore()
        
    
    def EventMove( self, event ):
        
        if HydrusData.TimeHasPassedFloat( self._last_move_pub + 0.1 ):
            
            HG.client_controller.pub( 'top_level_window_move_event' )
            
            self._last_move_pub = HydrusData.GetNowPrecise()
            
        
        return True # was: event.ignore()
        
    
class MainFrame( QW.QMainWindow ):

    def __init__( self, parent, title ):

        QW.QMainWindow.__init__( self, parent )
        
        self.setWindowTitle( title )
        
        self._new_options = HG.client_controller.new_options
        
        QP.SetBackgroundColour( self, QP.GetSystemColour( QG.QPalette.Button ) )
        
        self.setWindowIcon( QG.QIcon( HG.client_controller.frame_icon_pixmap ) )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_CLOSE( self.EventAboutToClose )
        
        HG.client_controller.ResetIdleTimer()
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def EventAboutToClose( self, event ):
        
        self.CleanBeforeDestroy()
        
        return True # was: event.ignore()
        
    
class FrameThatResizes( Frame ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key
        
        Frame.__init__( self, parent, title )
        
        self._widget_event_filter.EVT_SIZE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MOVE_END( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_CLOSE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MAXIMIZE( self.EventSizeAndPositionChanged )
        
    
    def EventSizeAndPositionChanged( self, event ):
        
        if not self.isMinimized(): SaveTLWSizeAndPosition( self, self._frame_key )
        
        return True # was: event.ignore()
        
    
class MainFrameThatResizes( MainFrame ):

    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key

        MainFrame.__init__( self, parent, title )

        self._widget_event_filter.EVT_SIZE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MOVE_END( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_CLOSE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MAXIMIZE( self.EventSizeAndPositionChanged )

    def EventSizeAndPositionChanged( self, event ):
        
        if not self.isMinimized(): SaveTLWSizeAndPosition( self, self._frame_key )

        return True # was: event.ignore()
        
    
class FrameThatTakesScrollablePanel( FrameThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog' ):
        
        self._panel = None
        
        FrameThatResizes.__init__( self, parent, title, frame_key )
        
        self._ok = QW.QPushButton( 'close', self )
        self._ok.clicked.connect( self.EventClose )
        
    
    def CleanBeforeDestroy( self ):
        
        FrameThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def keyPressEvent( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == QC.Qt.Key_Escape:
            
            self.close()
            
        else:
            
            event.ignore()
            
        
    
    def EventClose( self ):
        
        self.close()
        
    
    def GetPanel( self ):
        
        return self._panel
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        if hasattr( self._panel, 'okSignal' ): self._panel.okSignal.connect( self.EventClose )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel )
        QP.AddToLayout( vbox, self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.setLayout( vbox )
        
        SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.show()
        
    
