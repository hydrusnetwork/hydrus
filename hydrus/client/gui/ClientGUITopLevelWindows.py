import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP

CHILD_POSITION_PADDING = 24
FUZZY_PADDING = 10

# saw a ( 24, -14 ) child position off a top-left corner, which means the frameGeometry topleft was ( 0, -38 )????
# let's see what happens if we forgive such madness
FORGIVE_FRAME_GUBBINS_FUZZY_PADDING = 40

def GetSafePosition( position: QC.QPoint, frame_key ):
    
    if CG.client_controller.new_options.GetBoolean( 'disable_get_safe_position_test' ):
        
        return ( position, None )
        
    
    # some window managers size the windows just off screen to cut off borders
    # so choose a test position that's a little more lenient
    
    fuzzy_point = QC.QPoint( FORGIVE_FRAME_GUBBINS_FUZZY_PADDING, FORGIVE_FRAME_GUBBINS_FUZZY_PADDING )
    
    test_position = position + fuzzy_point
    
    # note that some version of Qt cannot figure this out, they just deliver None for a particular monitor!
    # https://github.com/hydrusnetwork/hydrus/issues/1511
    
    screen = QW.QApplication.screenAt( test_position )
    
    if screen is None:
        
        try:
            
            first_display = QW.QApplication.screens()[0]
            
            rescue_position = first_display.availableGeometry().topLeft() + fuzzy_point
            
            rescue_screen = QW.QApplication.screenAt( rescue_position )
            
            if rescue_screen == first_display:
                
                message = 'A window with frame key "{}" that wanted to display at "{}" was rescued from apparent off-screen to the new location at "{}".'.format( frame_key, position, rescue_position )
                
                return ( rescue_position, message )
                
            
        except Exception as e:
            
            # user is using IceMongo Linux, a Free Libre Open Source derivation of WeasleBlue Linux, with the iJ4 5-D inverted Window Managing system, which has a holographically virtualised desktop system
            
            HydrusData.PrintException( e )
            
        
        message = 'A window with frame key "{}" that wanted to display at "{}" could not be rescued from off-screen! Please let hydrus dev know!'.format( frame_key, position )
        
        return ( None, message )
        
    else:
        
        return ( position, None )
        
    

def GetSafeSize( tlw: QW.QWidget, min_size: QC.QSize, gravity ) -> QC.QSize:
    
    min_width = min_size.width()
    min_height = min_size.height()
    
    frame_padding = tlw.frameGeometry().size() - tlw.size()
    
    parent_widget = tlw.parentWidget()
    
    if parent_widget is None:
        
        main_gui = CG.client_controller.GetMainGUI()
        
        if main_gui is not None and tlw != main_gui:
            
            parent_window = main_gui
            
        else:
            
            parent_window = None
            
        
    else:
        
        parent_window = parent_widget.window()
        
    
    if parent_window is None:
        
        width = min_width
        height = min_height
        
    else:
        
        # when we initialise, we might not have a frame yet because we haven't done show() yet
        # so borrow main gui's
        if frame_padding.isEmpty():
            
            main_gui = CG.client_controller.GetMainGUI()
            
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
            
        
    
    display_size = ClientGUIFunctions.GetDisplaySize( tlw )
    
    display_available_size = display_size - frame_padding
    
    width = min( display_available_size.width() - 2 * CHILD_POSITION_PADDING, width )
    height = min( display_available_size.height() - 2 * CHILD_POSITION_PADDING, height )
    
    return QC.QSize( width, height )
    

def ExpandTLWIfPossible( tlw: QW.QWidget, frame_key, desired_size_delta: QC.QSize ):
    
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
        
        # we don't want to expand to parent size here
        gravity_for_expand_time = ( -1, -1 )
        
        new_size = GetSafeSize( tlw, desired_size, gravity_for_expand_time )
        
        if new_size.width() > current_width or new_size.height() > current_height:
            
            tlw.resize( new_size )
            
            #tlw.setMinimumSize( tlw.sizeHint() )
            
            SlideOffScreenTLWUpAndLeft( tlw )
            
        
    

def SaveTLWSizeAndPosition( tlw: QW.QWidget, frame_key ):
    
    if tlw.isMinimized() or not tlw.isVisible():
        
        return
        
    
    new_options = CG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    if remember_size:
        
        maximised = tlw.isMaximized()
        fullscreen = tlw.isFullScreen()
        
    
    # I am informed that tlw.frameGeometry().topLeft() will account for a macOS system bar at the top
    # tlw.pos() grabs from the client area, not the screen area
    
    # Note this important information about frameGeometry in X11 from https://doc.qt.io/qt-6/application-windows.html#window-geometry
    # "Basic rule: There's always one user who uses a window manager that breaks your assumption, and who will complain to you."
    
    ( safe_position, position_message ) = GetSafePosition( tlw.frameGeometry().topLeft(), frame_key )
    
    if safe_position is not None:
        
        worth_saving_size = True
        worth_saving_position = True
        
        if ( maximised or fullscreen ) and last_position is not None:
            
            worth_saving_size = False
            
            # if we saved a position when it was non-maximised, we'll want to keep that in our options
            # UNLESS the user just transported a maximised screen from another monitor using their window manager etc...
            # in this case, where the maximised screen just teleported across screens, we want to save the new screen for the next open
            
            last_position_pos = QC.QPoint( last_position[0], last_position[1] )
            
            tlw_screen = tlw.screen()
            saved_position_screen = QW.QApplication.screenAt( last_position_pos )
            
            if tlw_screen is None:
                
                worth_saving_position = False
                
            
            if saved_position_screen == tlw_screen:
                
                worth_saving_position = False
                
            
            if worth_saving_position:
                
                # nice 'just off the corner' on current maximised screen position
                safe_position += QC.QPoint( 20, 20 )
                
                if tlw_screen is not None and saved_position_screen is not None:
                    
                    # let's see if we can move it to the same basic position on the new monitor
                    
                    previous_local_screen_pos = last_position_pos - saved_position_screen.geometry().topLeft()
                    tlw_screen_pos = previous_local_screen_pos + tlw_screen.geometry().topLeft()
                    
                    if tlw_screen.geometry().contains( tlw_screen_pos ) and tlw_screen.geometry().contains( tlw_screen_pos + QC.QPoint( last_size[0], last_size[1] ) ):
                        
                        safe_position = tlw_screen_pos
                        
                    
                
                
            
        
        if remember_size and worth_saving_size:
            
            last_size = ( tlw.size().width(), tlw.size().height() )
            
        
        if remember_position and worth_saving_position:
            
            last_position = ( safe_position.x(), safe_position.y() )
            
        
    
    new_options.SetFrameLocation( frame_key, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
    

def SetInitialTLWSizeAndPosition( tlw: QW.QWidget, frame_key ):
    
    new_options = CG.client_controller.new_options
    
    ( remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = new_options.GetFrameLocation( frame_key )
    
    parent = tlw.parentWidget()
    
    if parent is None:
        
        main_gui = CG.client_controller.GetMainGUI()
        
        if main_gui is not None and tlw != main_gui:
            
            parent_window = main_gui
            
        else:
            
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
            
            screen = ClientGUIFunctions.GetMouseScreen()
            
            if screen is not None:
                
                desired_position = screen.availableGeometry().topLeft() + QC.QPoint( CHILD_POSITION_PADDING, CHILD_POSITION_PADDING )
                
            
        else:
            
            parent_tlw = parent_window.window()
            
            desired_position = parent_tlw.frameGeometry().topLeft() + QC.QPoint( CHILD_POSITION_PADDING, CHILD_POSITION_PADDING )
            
        
        slide_up_and_left = True
        
    elif default_position == 'center':
        
        if parent_window is None:
            
            we_care_about_off_screen_messages = False
            
            screen = ClientGUIFunctions.GetMouseScreen()
            
            if screen is not None:
                
                desired_position = screen.availableGeometry().center()
                
            
        else:
            
            desired_position = parent_window.frameGeometry().center() - tlw.rect().center()
            
        
    
    ( safe_position, position_message ) = GetSafePosition( desired_position, frame_key )
    
    if we_care_about_off_screen_messages and position_message is not None:
        
        HydrusData.ShowText( position_message )
        
    
    if safe_position is not None:
        
        tlw.move( safe_position )
        
        if HC.PLATFORM_MACOS:
            
            # macOS seems to move dialogs down like 26 pixels right after open. Our investigation suggested this was something OS side, rather than Qt
            # we schedule this to overwrite whatever macOS wanted with what we want
            # https://github.com/hydrusnetwork/hydrus/issues/1673
            # https://github.com/hydrusnetwork/hydrus/issues/1681
            
            from hydrus.client.gui import ClientGUI
            
            if not isinstance( tlw, ClientGUI.FrameGUI ):
                
                CG.client_controller.CallLaterQtSafe( tlw, 0.1, 'macOS position fix', tlw.move, safe_position )
                
            
        
    
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
    
    display_size = ClientGUIFunctions.GetDisplaySize( tlw )
    display_pos = ClientGUIFunctions.GetDisplayPosition( tlw )
    
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
        
        super().__init__( parent )
        
        if do_not_activate:
            
            self.setAttribute( QC.Qt.WidgetAttribute.WA_ShowWithoutActivating )
            
        
        self.setWindowTitle( title )
        
        self._new_options = CG.client_controller.new_options
        
        self.setWindowIcon( CC.global_icons().hydrus_frame )
        
        CG.client_controller.ResetIdleTimer()
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
    
    def _DoClose( self, value ):
        
        return
        
    
    def _SaveOKPosition( self ):
        
        pass
        
    
    def _TestValidityAndPresentVetoMessage( self, value ):
        
        return True
        
    
    def _TryEndModal( self, value ):
        
        if not self.isModal(): # in some rare cases (including spammy AutoHotkey, looks like), this can be fired before the dialog can clean itself up
            
            return False
            
        
        try:
            
            if not self._TestValidityAndPresentVetoMessage( value ):
                
                return False
                
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            message = 'Hey, there was a problem when trying to check if this dialog was all good before close! This is probably because the data in the dialog was invalid somehow and my code cannot examine it properly. This error window is a last-ditch catch to ensure that you do not get locked into a non-closable dialog. Here is the summary of your error:'
            message += '\n\n'
            message += str( e )
            message += '\n\n'
            message += 'But the full trace has been written to your log. Please contact hydrus dev so he can fix whatever happened here!'
            message += '\n\n'
            
            if value == QW.QDialog.DialogCode.Accepted:
                
                message += 'I will now dump you back to the dialog. Please hit "cancel".'
                
                ClientGUIDialogsMessage.ShowCritical( self, 'problem closing dialog', message )
                
                return False
                
            else:
                
                message += 'Somehow you got to this position despite not hitting "apply". I will now proceed, despite the error, trusting that a cancel will be safe.'
                
                ClientGUIDialogsMessage.ShowCritical( self, 'problem closing dialog', message )
                
            
        
        try:
            
            if not self._UserIsOKToClose( value ):
                
                return False
                
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            message = 'Hey, there was a problem when trying to check if we could close this dialog! This is probably because the data in the dialog was invalid somehow and my code cannot examine it properly. This error window is a last-ditch catch to ensure that you do not get locked into a non-closable dialog. Here is the summary of your error:'
            message += '\n\n'
            message += str( e )
            message += '\n\n'
            message += 'But the full trace has been written to your log. Please contact hydrus dev so he can fix whatever happened here!'
            
            if value == QW.QDialog.DialogCode.Accepted:
                
                message += '\n\n'
                message += 'It looks like you were applying, so you have to make a decision before any bad data is saved:'
                message += '\n'
                message += '- If there is a parent dialog, cancel it immediately after moving on from this error notification.'
                message += '\n'
                message += '- If there is no parent dialog--i.e. when this dialog closes, you will be going back to the Main GUI--I think you should kill your hydrus process now. Do not risk saving broken data!'
                
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem closing dialog', message )
            
        
        if value == QW.QDialog.DialogCode.Rejected:
            
            self.SetCancelled( True )
            
        elif value == QW.QDialog.DialogCode.Accepted:
            
            self._SaveOKPosition()
            
        
        self._DoClose( value )
        
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
                
            except Exception as e:
                
                HydrusData.ShowText( 'The dialog would not close on command.' )
                
            
            try:
                
                self.deleteLater()
                
            except Exception as e:
                
                HydrusData.ShowText( 'The dialog would not destroy on command.' )
                
            
        
        return True
        
    
    def _UserIsOKToClose( self, value ):
        
        return True
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def DoOK( self ):
        
        self._TryEndModal( QW.QDialog.DialogCode.Accepted )
        
    
    def closeEvent( self, event ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        was_ended = self._TryEndModal( QW.QDialog.DialogCode.Rejected )
        
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
                
            
        
        self._TryEndModal( QW.QDialog.DialogCode.Accepted )
        

    def EventDialogButtonCancel( self ):

        if not self or not QP.isValid( self ):
            
            return
            

        event_object = self.sender()

        if event_object is not None:

            tlw = event_object.window()

            if tlw != self:
                
                return
                
            

        self._TryEndModal( QW.QDialog.DialogCode.Rejected )
        
    
    def keyPressEvent( self, event ):
        
        current_focus = QW.QApplication.focusWidget()
        
        event_from_us = current_focus is not None and ClientGUIFunctions.IsQtAncestor( current_focus, self )
        
        shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event )
        
        escape_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        command_w_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'W' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        
        if event_from_us and ( shortcut == escape_shortcut or ( HC.PLATFORM_MACOS and shortcut == command_w_shortcut ) ):
            
            self._TryEndModal( QW.QDialog.DialogCode.Rejected )
            
        else:
            
            QP.Dialog.keyPressEvent( self, event )
            
        
    

class DialogThatResizes( NewDialog ):
    
    def __init__( self, parent, title, frame_key, do_not_activate = False ):
        
        self._frame_key = frame_key
        
        super().__init__( parent, title, do_not_activate = do_not_activate )
        
    
    def _SaveOKPosition( self ):
        
        SaveTLWSizeAndPosition( self, self._frame_key )
        
    

class Frame( QW.QWidget ):
    
    def __init__( self, parent, title ):
        
        super().__init__( parent )
        
        self.setWindowTitle( title )
        
        self.setWindowFlags( QC.Qt.WindowType.Window )
        self.setWindowFlag( QC.Qt.WindowType.WindowContextHelpButtonHint, on = False )
        
        self.setAttribute( QC.Qt.WidgetAttribute.WA_DeleteOnClose )
        
        self._new_options = CG.client_controller.new_options
        
        self.setWindowIcon( CC.global_icons().hydrus_frame )
        
        CG.client_controller.ResetIdleTimer()
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def closeEvent( self, event ):
        
        self.CleanBeforeDestroy()
        
    

class MainFrame( QW.QMainWindow ):
    
    def __init__( self, parent, title ):
        
        super().__init__( parent )
        
        self.setWindowTitle( title )
        
        self._new_options = CG.client_controller.new_options
        
        self.setWindowIcon( CC.global_icons().hydrus_frame )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        CG.client_controller.ResetIdleTimer()
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def closeEvent( self, event ):
        
        self.CleanBeforeDestroy()
        
    

class MaximiseRestoreCatcher( QC.QObject ):
    
    def __init__( self, parent: QW.QWidget, call ):
        
        self._call = call
        
        self._parent = parent
        
        super().__init__( parent )
        
        parent.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            type = event.type()
            
            if type == QC.QEvent.Type.WindowStateChange:
                
                event = typing.cast( QG.QWindowStateChangeEvent, event )
                
                if self._parent.isMaximized() or ( event.oldState() & QC.Qt.WindowState.WindowMaximized):
                    
                    self._call()
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e, do_wait = False )
            
        
        return False
        
    

class FrameThatResizes( Frame ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key
        
        super().__init__( parent, title )
        
        self._maximise_restore_catcher = MaximiseRestoreCatcher( self, self._StartSaveTLWSizeAndPositionTimer )
        
        self._move_end_timer = QC.QTimer( self )
        self._move_end_timer.setSingleShot( True )
        self._move_end_timer.timeout.connect( self.moveEnded )
        
        self._save_size_and_position_timer = QC.QTimer( self )
        self._save_size_and_position_timer.setSingleShot( True )
        self._save_size_and_position_timer.timeout.connect( self._SaveTLWSizeAndPosition )
        
    
    def _SaveTLWSizeAndPosition( self ):
        
        # maximise sends a pre-maximise size event that poisons last_size if this is immediate
        # and generally a good idea to wait here to handle some init states
        CG.client_controller.CallLaterQtSafe( self, 0.1, 'save frame size and position: {}'.format( self._frame_key ), SaveTLWSizeAndPosition, self, self._frame_key )
        
    
    def _StartSaveTLWSizeAndPositionTimer( self ):
        
        self._save_size_and_position_timer.start( 100 )
        
    
    def CleanBeforeDestroy( self ):
        
        Frame.CleanBeforeDestroy( self )
        
        self._StartSaveTLWSizeAndPositionTimer()
        
    
    def moveEnded( self ):
        
        self._StartSaveTLWSizeAndPositionTimer()
        
    
    def moveEvent( self, event ):
        
        self._move_end_timer.start( 200 )
        
        super().moveEvent( event )
        
    
    def resizeEvent( self, event ):
        
        self._StartSaveTLWSizeAndPositionTimer()
        
        super().resizeEvent( event )
        
    

class FrameThatResizesWithHovers( FrameThatResizes ):
    
    pass
    

class MainFrameThatResizes( MainFrame ):
    
    def __init__( self, parent, title, frame_key ):
        
        self._frame_key = frame_key
        
        super().__init__( parent, title )
        
        self._maximise_restore_catcher = MaximiseRestoreCatcher( self, self._StartSaveTLWSizeAndPositionTimer )
        
        self._move_end_timer = QC.QTimer( self )
        self._move_end_timer.setSingleShot( True )
        self._move_end_timer.timeout.connect( self.moveEnded )
        
        self._save_size_and_position_timer = QC.QTimer( self )
        self._save_size_and_position_timer.setSingleShot( True )
        self._save_size_and_position_timer.timeout.connect( self._SaveTLWSizeAndPosition )
        
    
    def _SaveTLWSizeAndPosition( self ):
        
        # maximise sends a pre-maximise size event that poisons last_size if this is immediate
        # and generally a good idea to wait here to handle some init states
        CG.client_controller.CallLaterQtSafe( self, 0.1, 'save frame size and position: {}'.format( self._frame_key ), SaveTLWSizeAndPosition, self, self._frame_key )
        
    
    def _StartSaveTLWSizeAndPositionTimer( self ):
        
        self._save_size_and_position_timer.start( 100 )
        
    
    def CleanBeforeDestroy( self ):
        
        MainFrame.CleanBeforeDestroy( self )
        
        self._StartSaveTLWSizeAndPositionTimer()
        
    
    def moveEnded( self ):
        
        self._StartSaveTLWSizeAndPositionTimer()
        
    
    def moveEvent( self, event ):
        
        self._move_end_timer.start( 200 )
        
        super().moveEvent( event )
        
    

def ResizableWindowIsOpenAndItIsMyWindowsChild( win: QW.QWidget ):
    
    window = win.window()
    
    tlws = QW.QApplication.topLevelWidgets()
    
    for tlw in tlws:
        
        if tlw == window:
            
            continue
            
        
        if isinstance( tlw, ( QP.Dialog, DialogThatResizes, FrameThatResizes ) ) and tlw.isVisible() and ClientGUIFunctions.IsQtAncestor( tlw, window, through_tlws = True ):
            
            return True
            
        
    
    return False
    
