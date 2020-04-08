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
    
def GetSafePosition( position: QC.QPoint ):
    
    # some window managers size the windows just off screen to cut off borders
    # so choose a test position that's a little more lenient
    
    fuzzy_point = QC.QPoint( FUZZY_PADDING, FUZZY_PADDING )
    
    test_position = position + fuzzy_point
    
    screen = QW.QApplication.screenAt( test_position )
    
    if screen is None:
        
        try:
            
            first_display = QW.QApplication.screens()[0]
            
            rescue_position = first_display.availableGeometry().topLeft() + fuzzy_point
            
            rescue_screen = QW.QApplication.screenAt( rescue_position )
            
            if rescue_screen == first_display:
                
                message = 'A window that wanted to display at "{}" was rescued from apparent off-screen to the new location at "{}".'.format( position, rescue_position )
                
                return ( rescue_position, message )
                
            
        except Exception as e:
            
            # user is using IceMongo Linux, a Free Libre Open Source derivation of WeasleBlue Linux, with the iJ4 5-D inverted Window Managing system, which has a holographically virtualised desktop system
            
            HydrusData.PrintException( e )
            
        
        message = 'A window that wanted to display at "{}" could not be rescued from off-screen! Please let hydrus dev know!'
        
        return ( None, message )
        
    else:
        
        return ( position, None )
        
    
def GetSafeSize( tlw: QW.QWidget, min_size: QC.QSize, gravity ) -> QC.QSize:
    
    min_width = min_size.width()
    min_height = min_size.height()
    
    frame_padding = tlw.frameGeometry().size() - tlw.size()
    
    parent = tlw.parentWidget()
    
    if parent is None:
        
        width = min_width
        height = min_height
        
    else:
        
        parent_window = parent.window()
        
        # when we initialise, we might not have a frame yet because we haven't done show() yet
        # so borrow main gui's
        if frame_padding.isEmpty():
            
            main_gui = HG.client_controller.gui
            
            if main_gui is not None and QP.isValid( main_gui ) and not main_gui.isFullScreen():
                
                frame_padding = main_gui.frameGeometry().size() - main_gui.size()
                
            
        
        if parent_window.isFullScreen():
            
            parent_available_size = parent_window.size()
            
        else:
            
            parent_frame_size = parent_window.frameGeometry().size()
            
            parent_available_size = parent_frame_size - frame_padding
            
        
        parent_available_width = parent_available_size.width()
        parent_available_height = parent_available_size.height()
        
        ( width_gravity, height_gravity ) = gravity
        
        if width_gravity == -1:
            
            width = min_width
            
        else:
            
            max_width = parent_available_width - ( 2 * CHILD_POSITION_PADDING )
            
            width = int( width_gravity * max_width )
            
        
        if height_gravity == -1:
            
            height = min_height
            
        else:
            
            max_height = parent_available_height - ( 2 * CHILD_POSITION_PADDING )
            
            height = int( height_gravity * max_height )
            
        
    
    display_size = GetDisplaySize( tlw )
    
    display_available_size = display_size - frame_padding
    
    width = min( display_available_size.width() - 2 * CHILD_POSITION_PADDING, width )
    height = min( display_available_size.height() - 2 * CHILD_POSITION_PADDING, height )
    
    return QC.QSize( width, height )
    
def ExpandTLWIfPossible( tlw: QW.QWidget, frame_key, desired_size_delta: QC.QSize ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    if not tlw.isMaximized() and not tlw.isFullScreen():
        
        current_size = tlw.size()
        
        current_width = current_size.width()
        current_height = current_size.height()
        
        desired_delta_width = desired_size_delta.width()
        desired_delta_height = desired_size_delta.height()
        
        desired_width = current_width
        
        if desired_delta_width > 0:
            
            desired_width = current_width + desired_delta_width + FUZZY_PADDING
            
        
        desired_height = current_height
        
        if desired_delta_height > 0:
            
            desired_height = current_height + desired_delta_height + FUZZY_PADDING
            
        
        desired_size = QC.QSize( desired_width, desired_height )
        
        new_size = GetSafeSize( tlw, desired_size, default_gravity )
        
        if new_size.width() > current_width or new_size.height() > current_height:
            
            tlw.resize( new_size )
            
            #tlw.setMinimumSize( tlw.sizeHint() )
            
            SlideOffScreenTLWUpAndLeft( tlw )
            
        
    
def GetMouseScreen():
    
    return QW.QApplication.screenAt( QG.QCursor.pos() )
    
def MouseIsOnMyDisplay( window ):
    
    window_handle = window.window().windowHandle()
    
    if window_handle is None:
        
        return False
        
    
    window_screen = window_handle.screen()
    
    mouse_screen = GetMouseScreen()
    
    return mouse_screen is window_screen
    
def SaveTLWSizeAndPosition( tlw: QW.QWidget, frame_key ):
    
    if tlw.isMinimized():
        
        return
        
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    maximised = tlw.isMaximized()
    fullscreen = tlw.isFullScreen()
    
    if not ( maximised or fullscreen ):
        
        ( safe_position, position_message ) = GetSafePosition( tlw.pos() )
        
        if safe_position is not None:
            
            last_size = ( tlw.size().width(), tlw.size().height() )
            last_position = ( safe_position.x(), safe_position.y() )
            
        
    
    new_options.SetFrameLocation( frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
    
def SetInitialTLWSizeAndPosition( tlw: QW.QWidget, frame_key ):
    
    new_options = HG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    parent = tlw.parentWidget()
    
    if parent is None:
        
        parent_window = None
        
    else:
        
        parent_window = parent.window()
        
    
    if remember_size and last_size is not None:
        
        ( width, height ) = last_size
        
        new_size = QC.QSize( width, height )
        
    else:
        
        new_size = GetSafeSize( tlw, tlw.sizeHint(), default_gravity )
        
    
    tlw.resize( new_size )
    
    min_width = min( 240, new_size.width() )
    min_height = min( 240, new_size.height() )
    
    tlw.setMinimumSize( QC.QSize( min_width, min_height ) )
    
    #
    
    child_position_point = QC.QPoint( CHILD_POSITION_PADDING, CHILD_POSITION_PADDING )
    
    desired_position = child_position_point
    
    we_care_about_off_screen_messages = True
    slide_up_and_left = False
    
    if remember_position and last_position is not None:
        
        ( x, y ) = last_position
        
        desired_position = QC.QPoint( x, y )
        
    elif default_position == 'topleft':
        
        if parent_window is None:
            
            we_care_about_off_screen_messages = False
            
            screen = GetMouseScreen()
            
            if screen is not None:
                
                desired_position = screen.availableGeometry().topLeft() + QC.QPoint( CHILD_POSITION_PADDING, CHILD_POSITION_PADDING )
                
            
        else:
            
            parent_tlw = parent_window.window()
            
            desired_position = parent_tlw.pos() + QC.QPoint( CHILD_POSITION_PADDING, CHILD_POSITION_PADDING )
            
        
        slide_up_and_left = True
        
    elif default_position == 'center':
        
        if parent_window is None:
            
            we_care_about_off_screen_messages = False
            
            screen = GetMouseScreen()
            
            if screen is not None:
                
                desired_position = screen.availableGeometry().center()
                
            
        else:
            
            desired_position = parent_window.frameGeometry().center() - tlw.rect().center()
            
        
    
    ( safe_position, position_message ) = GetSafePosition( desired_position )
    
    if we_care_about_off_screen_messages and position_message is not None:
        
        HydrusData.ShowText( position_message )
        
    
    if safe_position is not None:
        
        tlw.move( safe_position )
        
    
    if slide_up_and_left:
        
        SlideOffScreenTLWUpAndLeft( tlw )
        
    
    # Comment from before the Qt port: if these aren't callafter, the size and pos calls don't stick if a restore event happens
    
    if maximised:
        
        tlw.showMaximized()
        
    
    if fullscreen and not HC.PLATFORM_MACOS:
        
        tlw.showFullScreen()
        
    
def SlideOffScreenTLWUpAndLeft( tlw ):
    
    tlw_frame_rect = tlw.frameGeometry()
    
    tlw_top_left = tlw_frame_rect.topLeft()
    tlw_bottom_right = tlw_frame_rect.bottomRight()
    
    tlw_right = tlw_bottom_right.x()
    tlw_bottom = tlw_bottom_right.y()
    
    display_size = GetDisplaySize( tlw )
    display_pos = GetDisplayPosition( tlw )
    
    display_right = display_pos.x() + display_size.width() - CHILD_POSITION_PADDING
    display_bottom = display_pos.y() + display_size.height() - CHILD_POSITION_PADDING
    
    move_x = tlw_right > display_right
    move_y = tlw_bottom > display_bottom
    
    if move_x or move_y:
        
        delta_x = min( display_right - tlw_right, 0 )
        delta_y = min( display_bottom - tlw_bottom, 0 )
        
        delta_point = QC.QPoint( delta_x, delta_y )
        
        safe_pos = tlw_top_left + delta_point
        
        tlw.move( safe_pos )
        
    
class NewDialog( QP.Dialog ):
    
    def __init__( self, parent, title, do_not_activate = False ):
        
        QP.Dialog.__init__( self, parent )
        
        if do_not_activate:
            
            self.setAttribute( QC.Qt.WA_ShowWithoutActivating )
            
        
        self.setWindowTitle( title )
        
        self._last_move_pub = 0.0
        
        self._new_options = HG.client_controller.new_options
        
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
            
            return False
            
        
        if not self._ReadyToClose( value ):
            
            return False
            
        
        if value == QW.QDialog.Rejected:
            
            if not self._CanCancel():
                
                return False
                
            
            self.SetCancelled( True )
            
        
        if value == QW.QDialog.Accepted:
            
            if not self._CanOK():
                
                return False
                
            
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
                
            
        
        return True
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def DoOK( self ):
        
        self._TryEndModal( QW.QDialog.Accepted )
        
    
    def closeEvent( self, event ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        was_ended = self._TryEndModal( QW.QDialog.Rejected )
        
        if was_ended:
            
            event.accept()
            
        else:
            
            event.ignore()
            
        
    
    def EventDialogButtonApply( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        event_object = self.sender()
        
        if event_object is not None:
            
            tlw = event_object.window()
            
            if tlw != self:
                
                return
                
            
        
        self._TryEndModal( QW.QDialog.Accepted )
        

    def EventDialogButtonCancel( self ):

        if not self or not QP.isValid( self ):
            
            return
            

        event_object = self.sender()

        if event_object is not None:

            tlw = event_object.window()

            if tlw != self:
                
                return
                
            

        self._TryEndModal( QW.QDialog.Rejected )
        
    
    def keyPressEvent( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        current_focus = QW.QApplication.focusWidget()
        
        event_from_us = current_focus is not None and ClientGUIFunctions.IsQtAncestor( current_focus, self )
        
        if event_from_us and key == QC.Qt.Key_Escape:
            
            self._TryEndModal( QW.QDialog.Rejected )
            
        else:
            
            QP.Dialog.keyPressEvent( self, event )
            
        
    
class DialogThatResizes( NewDialog ):
    
    def __init__( self, parent, title, frame_key, do_not_activate = False ):
        
        self._frame_key = frame_key
        
        NewDialog.__init__( self, parent, title, do_not_activate = do_not_activate )
        
    
    def _SaveOKPosition( self ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
    
class DialogThatTakesScrollablePanel( DialogThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False, do_not_activate = False ):
        
        self._panel = None
        self._hide_buttons = hide_buttons
        
        DialogThatResizes.__init__( self, parent, title, frame_key, do_not_activate = do_not_activate )
        
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
        
        if hasattr( self._panel, 'okSignal'): self._panel.okSignal.connect( self.DoOK )
        
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
        self._close.clicked.connect( self.DoOK )
        
        if self._hide_buttons:
            
            self._close.setVisible( False )
            
        
    
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
        self._apply.setObjectName( 'HydrusAccept' )
        self._apply.clicked.connect( self.EventDialogButtonApply )
        
        self._cancel = QW.QPushButton( 'cancel', self )
        self._cancel.setObjectName( 'HydrusCancel' )
        self._cancel.clicked.connect( self.EventDialogButtonCancel )
        
        if self._hide_buttons:
            
            self._apply.setVisible( False )
            self._cancel.setVisible( False )
            
        
    
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
        
        # maximise sends a pre-maximise size event that poisons last_size if this is immediate
        HG.client_controller.CallLaterQtSafe( self, 0.1, SaveTLWSizeAndPosition, self, self._frame_key )
        
        return True # was: event.ignore()
        
    
class FrameThatResizesWithHovers( FrameThatResizes ): pass
class MainFrameThatResizes( MainFrame ):

    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key

        MainFrame.__init__( self, parent, title )

        self._widget_event_filter.EVT_SIZE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MOVE_END( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_CLOSE( self.EventSizeAndPositionChanged )
        self._widget_event_filter.EVT_MAXIMIZE( self.EventSizeAndPositionChanged )

    def EventSizeAndPositionChanged( self, event ):
        
        # maximise sends a pre-maximise size event that poisons last_size if this is immediate
        HG.client_controller.CallLaterQtSafe( self, 0.1, SaveTLWSizeAndPosition, self, self._frame_key )

        return True # was: event.ignore()
        
    
class FrameThatTakesScrollablePanel( FrameThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog' ):
        
        self._panel = None
        
        FrameThatResizes.__init__( self, parent, title, frame_key )
        
        self._ok = QW.QPushButton( 'close', self )
        self._ok.clicked.connect( self.close )
        
    
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
            
        
    
    def GetPanel( self ):
        
        return self._panel
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        if hasattr( self._panel, 'okSignal' ):
            
            self._panel.okSignal.connect( self.close )
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel )
        QP.AddToLayout( vbox, self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.setLayout( vbox )
        
        SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.show()
        
    
