import os
import sys
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.widgets import ClientGUICommon

class PopupWindow( QW.QFrame ):
    
    def __init__( self, parent, manager ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Plain )
        
        self._manager = manager
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventDismiss )
        
    
    def TryToDismiss( self ):
        
        self._manager.Dismiss( self )
        
    
    def EventDismiss( self, event ):
        
        self.TryToDismiss()
        
    
class PopupMessage( PopupWindow ):
    
    TEXT_CUTOFF = 1024
    
    def __init__( self, parent, manager, job_key: ClientThreading.JobKey ):
        
        PopupWindow.__init__( self, parent, manager )
        
        self.setSizePolicy( QW.QSizePolicy.MinimumExpanding, QW.QSizePolicy.Fixed )
        
        self._job_key = job_key
        
        vbox = QP.VBoxLayout()
        
        self._title = ClientGUICommon.BetterStaticText( self )
        self._title.setAlignment( QC.Qt.AlignHCenter | QC.Qt.AlignVCenter )
        
        font = self._title.font()
        font.setBold( True )
        self._title.setFont( font )
        
        popup_message_character_width = HG.client_controller.new_options.GetInteger( 'popup_message_character_width' )
        
        popup_char_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._title, popup_message_character_width )
        
        if HG.client_controller.new_options.GetBoolean( 'popup_message_force_min_width' ):
            
            #QP.SetMinClientSize( self, ( wrap_width, -1 ) )
            self.setFixedWidth( popup_char_width )
            
        else:
            
            self.setMaximumWidth( popup_char_width )
            
        
        self._title.setWordWrap( True )
        self._title_ev = QP.WidgetEventFilter( self._title )
        self._title_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._title.hide()
        
        self._text_1 = ClientGUICommon.BetterStaticText( self )
        self._text_1.setWordWrap( True )
        self._text_1_ev = QP.WidgetEventFilter( self._text_1 )
        self._text_1_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._text_1.hide()
        
        self._gauge_1 = ClientGUICommon.Gauge( self )
        self._gauge_1_ev = QP.WidgetEventFilter( self._gauge_1 )
        self._gauge_1_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._gauge_1.setMinimumWidth( int( popup_char_width * 0.9 ) )
        self._gauge_1.hide()
        
        self._text_2 = ClientGUICommon.BetterStaticText( self )
        self._text_2.setWordWrap( True )
        self._text_2_ev = QP.WidgetEventFilter( self._text_2 )
        self._text_2_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._text_2.hide()
        
        self._gauge_2 = ClientGUICommon.Gauge( self )
        self._gauge_2_ev = QP.WidgetEventFilter( self._gauge_2 )
        self._gauge_2_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._gauge_2.setMinimumWidth( int( popup_char_width * 0.9 ) )
        self._gauge_2.hide()
        
        self._text_yes_no = ClientGUICommon.BetterStaticText( self )
        self._text_yes_no_ev = QP.WidgetEventFilter( self._text_yes_no )
        self._text_yes_no_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._text_yes_no.hide()
        
        self._yes = ClientGUICommon.BetterButton( self, 'yes', self._YesButton )
        self._yes.hide()
        
        self._no = ClientGUICommon.BetterButton( self, 'no', self._NoButton )
        self._no.hide()
        
        self._network_job_ctrl = ClientGUINetworkJobControl.NetworkJobControl( self )
        self._network_job_ctrl.hide()
        
        self._copy_to_clipboard_button = ClientGUICommon.BetterButton( self, 'copy to clipboard', self.CopyToClipboard )
        self._copy_to_clipboard_button_ev = QP.WidgetEventFilter( self._copy_to_clipboard_button )
        self._copy_to_clipboard_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._copy_to_clipboard_button.hide()
        
        self._show_files_button = ClientGUICommon.BetterButton( self, 'show files', self.ShowFiles )
        self._show_files_button_ev = QP.WidgetEventFilter( self._show_files_button )
        self._show_files_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._show_files_button.hide()
        
        self._user_callable_button = ClientGUICommon.BetterButton( self, 'run command', self.CallUserCallable )
        self._user_callable_button_ev = QP.WidgetEventFilter( self._user_callable_button )
        self._user_callable_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._user_callable_button.hide()
        
        self._show_tb_button = ClientGUICommon.BetterButton( self, 'show traceback', self.ShowTB )
        self._show_tb_button_ev = QP.WidgetEventFilter( self._show_tb_button )
        self._show_tb_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._show_tb_button.hide()
        
        self._tb_text = ClientGUICommon.BetterStaticText( self )
        self._tb_text_ev = QP.WidgetEventFilter( self._tb_text )
        self._tb_text_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._tb_text.setWordWrap( True )
        self._tb_text.hide()
        
        self._copy_tb_button = ClientGUICommon.BetterButton( self, 'copy traceback information', self.CopyTB )
        self._copy_tb_button_ev = QP.WidgetEventFilter( self._copy_tb_button )
        self._copy_tb_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._copy_tb_button.hide()
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self.PausePlay )
        self._pause_button_ev = QP.WidgetEventFilter( self._pause_button )
        self._pause_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._pause_button.hide()
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, self.Cancel )
        self._cancel_button_ev = QP.WidgetEventFilter( self._cancel_button )
        self._cancel_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._cancel_button.hide()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        yes_no_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( yes_no_hbox, self._yes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( yes_no_hbox, self._no, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._title, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._text_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gauge_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._text_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gauge_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._text_yes_no, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, yes_no_hbox )
        QP.AddToLayout( vbox, self._network_job_ctrl )
        QP.AddToLayout( vbox, self._copy_to_clipboard_button )
        QP.AddToLayout( vbox, self._show_files_button )
        QP.AddToLayout( vbox, self._user_callable_button )
        QP.AddToLayout( vbox, self._show_tb_button )
        QP.AddToLayout( vbox, self._tb_text )
        QP.AddToLayout( vbox, self._copy_tb_button )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
    
    def _NoButton( self ):
        
        self._job_key.SetVariable( 'popup_yes_no_answer', False )
        
        self._job_key.Delete()
        
        self._yes.hide()
        self._no.hide()
        
    
    def _ProcessText( self, text ):
        
        text = str( text )
        
        if len( text ) > self.TEXT_CUTOFF:
            
            new_text = 'The text is too long to display here. Here is the start of it (the rest is printed to the log):'
            
            new_text += os.linesep * 2
            
            new_text += text[ : self.TEXT_CUTOFF ]
            
            text = new_text
            
        
        return text
        
    
    def _YesButton( self ):
        
        self._job_key.SetVariable( 'popup_yes_no_answer', True )
        
        self._job_key.Delete()
        
        self._yes.hide()
        self._no.hide()
        
    
    def CallUserCallable( self ):
        
        user_callable = self._job_key.GetUserCallable()
        
        if user_callable is not None:
            
            user_callable()
            
        
    
    def Cancel( self ):
        
        self._job_key.Cancel()
        
        self._pause_button.setEnabled( False )
        self._cancel_button.setEnabled( False )
        
    
    def CopyTB( self ):
        
        info = 'v{}, {}, {}'.format( HC.SOFTWARE_VERSION, sys.platform.lower(), 'frozen' if HC.RUNNING_FROM_FROZEN_BUILD else 'source' )
        trace = self._job_key.ToString()
        
        full_text = info + os.linesep + trace
        
        HG.client_controller.pub( 'clipboard', 'text', full_text )
        
    
    def CopyToClipboard( self ):
        
        result = self._job_key.GetIfHasVariable( 'popup_clipboard' )
        
        if result is not None:
            
            ( title, text ) = result
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def PausePlay( self ):
        
        self._job_key.PausePlay()
        
        if self._job_key.IsPaused():
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().pause )
            
        
    
    def ShowFiles( self ):
        
        result = self._job_key.GetIfHasVariable( 'popup_files' )
        
        if result is not None:
            
            ( popup_files, popup_files_name ) = result
            
            HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = popup_files, page_name = popup_files_name )
            
        
    
    def ShowTB( self ):
        
        if self._tb_text.isVisible():
            
            self._show_tb_button.setText( 'show traceback' )
            
            self._tb_text.hide()
            
        else:
            
            self._show_tb_button.setText( 'hide traceback' )
            
            self._tb_text.show()
            
        
        self._manager.MakeSureEverythingFits()
        
    
    def GetJobKey( self ):
        
        return self._job_key
        
    
    def IsDeleted( self ):
        
        return self._job_key.IsDeleted()
        
    
    def TryToDismiss( self ):
        
        if self._job_key.IsPausable() or self._job_key.IsCancellable():
            
            return
            
        else:
            
            PopupWindow.TryToDismiss( self )
            
        
    
    def UpdateMessage( self ):
        
        title = self._job_key.GetStatusTitle()
        
        if title is not None:
            
            self._title.show()
            
            self._title.setText( title )
            
        else:
            
            self._title.hide()
            
        
        #
        
        paused = self._job_key.IsPaused()
        
        popup_text_1 = self._job_key.GetIfHasVariable( 'popup_text_1' )
        
        if popup_text_1 is not None or paused:
            
            if paused:
                
                text = 'paused'
                
            else:
                
                text = popup_text_1
                
            
            self._text_1.show()
            
            self._text_1.setText( text )
            
        else:
            
            self._text_1.hide()
            
        
        #
        
        popup_gauge_1 = self._job_key.GetIfHasVariable( 'popup_gauge_1' )
        
        if popup_gauge_1 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_1
            
            self._gauge_1.SetRange( gauge_range )
            self._gauge_1.SetValue( gauge_value )
            
            self._gauge_1.show()
            
        else:
            
            self._gauge_1.hide()
            
        
        #
        
        popup_text_2 = self._job_key.GetIfHasVariable( 'popup_text_2' )
        
        if popup_text_2 is not None and not paused:
            
            text = popup_text_2
            
            self._text_2.setText( self._ProcessText( text ) )
            
            self._text_2.show()
            
        else:
            
            self._text_2.hide()
            
        
        #
        
        popup_gauge_2 = self._job_key.GetIfHasVariable( 'popup_gauge_2' )
        
        if popup_gauge_2 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_2
            
            self._gauge_2.SetRange( gauge_range )
            self._gauge_2.SetValue( gauge_value )
            
            self._gauge_2.show()
            
        else:
            
            self._gauge_2.hide()
            
        
        #
        
        popup_yes_no_question = self._job_key.GetIfHasVariable( 'popup_yes_no_question' )
        
        if popup_yes_no_question is not None and not paused:
            
            text = popup_yes_no_question
            
            self._text_yes_no.setText( self._ProcessText( text ) )
            
            self._text_yes_no.show()
            
            self._yes.show()
            self._no.show()
            
        else:
            
            self._text_yes_no.hide()
            self._yes.hide()
            self._no.hide()
            
        
        #
        
        network_job = self._job_key.GetNetworkJob()
        
        if network_job is None:
            
            self._network_job_ctrl.ClearNetworkJob()
            
            self._network_job_ctrl.hide()
            
        else:
            
            self._network_job_ctrl.SetNetworkJob( network_job )
            
            self._network_job_ctrl.show()
            
        
        #
        
        popup_clipboard = self._job_key.GetIfHasVariable( 'popup_clipboard' )
        
        if popup_clipboard is not None:
            
            ( title, text ) = popup_clipboard
            
            if self._copy_to_clipboard_button.text() != title:
                
                self._copy_to_clipboard_button.setText( title )
                
            
            self._copy_to_clipboard_button.show()
            
        else:
            
            self._copy_to_clipboard_button.hide()
            
        
        #
        
        result = self._job_key.GetIfHasVariable( 'popup_files' )
        
        if result is not None:
            
            ( popup_files, popup_files_name ) = result
            
            hashes = popup_files
            
            text = popup_files_name + ' - show ' + HydrusData.ToHumanInt( len( hashes ) ) + ' files'
            
            if self._show_files_button.text() != text:
                
                self._show_files_button.setText( text )
                
            
            self._show_files_button.show()
            
        else:
            
            self._show_files_button.hide()
            
        
        #
        
        user_callable = self._job_key.GetUserCallable()
        
        if user_callable is None:
            
            self._user_callable_button.hide()
            
        else:
            
            self._user_callable_button.setText( user_callable.GetLabel() )
            
            self._user_callable_button.show()
            
        
        #
        
        popup_traceback = self._job_key.GetTraceback()
        
        if popup_traceback is not None:
            
            self._copy_tb_button.show()
            self._show_tb_button.show()
            
            text = popup_traceback
            
            self._tb_text.setText( self._ProcessText( text ) )
            
            # do not show automatically--that is up to the show button
            
        else:
            
            self._copy_tb_button.hide()
            self._show_tb_button.hide()
            self._tb_text.hide()
            
        
        #
        
        if self._job_key.IsPausable():
            
            self._pause_button.show()
            
        else:
            
            self._pause_button.hide()
            
        
        if self._job_key.IsCancellable():
            
            self._cancel_button.show()
            
        else:
            
            self._cancel_button.hide()
        
        # Dirty hack to reduce unnecessary resizing
        
        if self.minimumWidth() < self.sizeHint().width():
            
            self.setMinimumWidth( self.sizeHint().width() )
            
        
    
class PopupMessageManager( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setWindowFlags( QC.Qt.Tool | QC.Qt.FramelessWindowHint )
        
        self.setAttribute( QC.Qt.WA_ShowWithoutActivating )
        
        self.setSizePolicy( QW.QSizePolicy.MinimumExpanding, QW.QSizePolicy.Preferred )
        
        self._last_best_size_i_fit_on = ( 0, 0 )
        
        self._max_messages_to_display = 10
        
        vbox = QP.VBoxLayout()
        
        self._message_panel = QW.QWidget( self )
        
        self._message_vbox = QP.VBoxLayout( margin = 0 )
        
        vbox.setSizeConstraint( QW.QLayout.SetFixedSize )
        
        self._message_panel.setLayout( self._message_vbox )
        self._message_panel.setSizePolicy( QW.QSizePolicy.MinimumExpanding, QW.QSizePolicy.Preferred )
        
        self._summary_bar = PopupMessageSummaryBar( self, self )
        self._summary_bar.setSizePolicy( QW.QSizePolicy.MinimumExpanding, QW.QSizePolicy.Preferred )
        
        QP.AddToLayout( vbox, self._message_panel )
        QP.AddToLayout( vbox, self._summary_bar )
        
        self.setLayout( vbox )
        
        self._pending_job_keys = []
        
        self._gui_event_filter = QP.WidgetEventFilter( parent )
        self._gui_event_filter.EVT_SIZE( self.EventParentMovedOrResized )
        self._gui_event_filter.EVT_MOVE( self.EventParentMovedOrResized )
        
        HG.client_controller.sub( self, 'AddMessage', 'message' )
        
        self._old_excepthook = sys.excepthook
        self._old_show_exception = HydrusData.ShowException
        self._old_show_exception_tuple = HydrusData.ShowExceptionTuple
        self._old_show_text = HydrusData.ShowText
        
        sys.excepthook = ClientData.CatchExceptionClient
        HydrusData.ShowException = ClientData.ShowExceptionClient
        HydrusData.ShowExceptionTuple = ClientData.ShowExceptionTupleClient
        HydrusData.ShowText = ClientData.ShowTextClient
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'initialising popup message manager\u2026' )
        
        self._update_job = HG.client_controller.CallRepeatingQtSafe( self, 0.25, 0.5, 'repeating popup message update', self.REPEATINGUpdate )
        
        self._summary_bar.expandCollapse.connect( self.ExpandCollapse )
        
        HG.client_controller.CallLaterQtSafe( self, 0.5, 'initialise message', self.AddMessage, job_key )
        
        HG.client_controller.CallLaterQtSafe( self, 1.0, 'delete initial message', job_key.Delete )
        
    
    def _CheckPending( self ):
        
        self._pending_job_keys = [ job_key for job_key in self._pending_job_keys if not job_key.IsDeleted() ]
        
        while len( self._pending_job_keys ) > 0 and self._message_vbox.count() < self._max_messages_to_display:
            
            job_key = self._pending_job_keys.pop( 0 )
            
            window = PopupMessage( self._message_panel, self, job_key )
            
            window.UpdateMessage()
            
            QP.AddToLayout( self._message_vbox, window )
            
        
        total_messages = len( self._pending_job_keys ) + self._message_vbox.count()
        
        self._summary_bar.SetNumMessages( total_messages )            
        
        if self._NeedsSizeOrShow():
            
            self._SizeAndPositionAndShow()
            
        
    
    def _DisplayingError( self ):
        
        for i in range( self._message_vbox.count() ):
            
            sizer_item = self._message_vbox.itemAt( i )
            
            message_window = sizer_item.widget()
            
            if not message_window:
                
                continue
                
            
            job_key = message_window.GetJobKey()
            
            if job_key.HadError():
                
                return True
                
            
        
        return False
        
    
    def _DoDebugHide( self ):
        
        if not QP.isValid( self ):
            
            return
            
        
        parent = self.parentWidget()
        
        possibly_on_hidden_virtual_desktop = not ClientGUIFunctions.MouseIsOnMyDisplay( parent )
        
        going_to_bug_out_at_hide_or_show = possibly_on_hidden_virtual_desktop
        
        new_options = HG.client_controller.new_options
        
        if new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ) and not self._DisplayingError():
            
            if parent.isMinimized():
                
                self.hide()
                
                return
                
            
        
        current_focus_tlw = QW.QApplication.activeWindow()
        
        main_gui_is_active = current_focus_tlw in ( self, parent )
        
        if new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ) and not self._DisplayingError():
            
            if not main_gui_is_active:
                
                if not going_to_bug_out_at_hide_or_show:
                    
                    self.hide()
                    
                
            
        
    
    def _NeedsSizeOrShow( self ):
        
        num_messages_displayed = self._message_vbox.count()
        
        there_is_stuff_to_display = num_messages_displayed > 0
        
        is_shown = self.isVisible()
        
        if there_is_stuff_to_display:
            
            if not is_shown:
                
                return True
                
            
            best_size = self.sizeHint()
            
            if best_size != self.size():
                
                return True
                
            
        else:
            
            if is_shown:
                
                return True
                
            
        
        return False
        
    
    def _SizeAndPositionAndShow( self ):
        
        try:
            
            gui_frame = self.parentWidget()
            
            gui_is_hidden = not gui_frame.isVisible()
            
            going_to_bug_out_at_hide_or_show = gui_is_hidden
            
            current_focus_tlw = QW.QApplication.activeWindow()
            
            self_is_active = current_focus_tlw == self
            
            main_gui_or_child_window_is_active = ClientGUIFunctions.TLWOrChildIsActive( gui_frame )
            
            num_messages_displayed = self._message_vbox.count()
            
            there_is_stuff_to_display = num_messages_displayed > 0
            
            if there_is_stuff_to_display:
                
                parent_size = gui_frame.size()
                
                my_size = self.size()
                
                my_x = ( parent_size.width() - my_size.width() ) - 20
                my_y = ( parent_size.height() - my_size.height() ) - 25
                
                if gui_frame.isVisible():
                    
                    my_position = ClientGUIFunctions.ClientToScreen( gui_frame, QC.QPoint( my_x, my_y ) )
                    
                    if my_position != self.pos():
                        
                        self.move( my_position )
                        
                    
                
                # Unhiding tends to raise the main gui tlw in some window managers, which is annoying if a media viewer window has focus
                show_is_not_annoying = main_gui_or_child_window_is_active or self._DisplayingError()
                
                ok_to_show = show_is_not_annoying and not going_to_bug_out_at_hide_or_show
                
                if ok_to_show:
                    
                    self.show()
                    
                
            else:
                
                if not going_to_bug_out_at_hide_or_show:
                    
                    self.hide()
                    
                
            
        except:
            
            text = 'The popup message manager experienced a fatal error and will now stop working! Please restart the client as soon as possible! If this keeps happening, please email the details and your client.log to the hydrus developer.'
            
            HydrusData.Print( text )
            
            HydrusData.Print( traceback.format_exc() )
            
            QW.QMessageBox.critical( gui_frame, 'Error', text )
            
            self._update_job.Cancel()
            
            self.CleanBeforeDestroy()
            
            self.deleteLater()
            
        
    
    def _GetAllMessageJobKeys( self ):
        
        job_keys = []

        for i in range( self._message_vbox.count() ):
            
            sizer_item = self._message_vbox.itemAt( i )
            
            message_window = sizer_item.widget()
            
            if not message_window: continue
            
            job_key = message_window.GetJobKey()
            
            job_keys.append( job_key )
            
        
        job_keys.extend( self._pending_job_keys )
        
        return job_keys
        
    
    def _OKToAlterUI( self ):

        if not QP.isValid( self ): return
        
        main_gui = self.parentWidget()
        
        gui_is_hidden = not main_gui.isVisible()
        
        if gui_is_hidden:
            
            return False
            
        
        if HG.client_controller.new_options.GetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor' ):
            
            # test both because when user uses a shortcut to send gui to a diff monitor, we can't chase it
            # this may need a better test for virtual display dismissal
            # this is also a proxy for hidden/virtual displays, which is really what it is going on about
            on_my_monitor = ClientGUIFunctions.MouseIsOnMyDisplay( main_gui ) or ClientGUIFunctions.MouseIsOnMyDisplay( self )
            
            if not on_my_monitor:
                
                return False
                
            
        
        if HG.client_controller.new_options.GetBoolean( 'freeze_message_manager_when_main_gui_minimised' ):
            
            main_gui_up = not main_gui.isMinimized()
            
            if not main_gui_up:
                
                return False
                
            
        
        return True
        
    
    def _TryToMergeMessage( self, job_key ):
        
        if not job_key.HasVariable( 'popup_files_mergable' ):
            
            return False
            
        
        result = job_key.GetIfHasVariable( 'popup_files' )
        
        if result is not None:
            
            ( hashes, name ) = result
            
            existing_job_keys = self._GetAllMessageJobKeys()
            
            for existing_job_key in existing_job_keys:
                
                if existing_job_key.HasVariable( 'popup_files_mergable' ):
                    
                    result = existing_job_key.GetIfHasVariable( 'popup_files' )
                    
                    if result is not None:
                        
                        ( existing_hashes, existing_name ) = result
                        
                        if existing_name == name:
                            
                            if isinstance( existing_hashes, list ):
                                
                                existing_hashes.extend( hashes )
                                
                            elif isinstance( existing_hashes, set ):
                                
                                existing_hashes.update( hashes )
                                
                            
                            return True
                            
                        
                    
                
            
        
        return False
        
    
    def _Update( self ):
        
        if HG.view_shutdown:
            
            self._update_job.Cancel()
            
            self.CleanBeforeDestroy()
            
            self.deleteLater()
            
            return
            
        
        for i in range( self._message_vbox.count() ):
            
            sizer_item = self._message_vbox.itemAt( i )
            
            message_window = sizer_item.widget()
            
            if message_window:
                
                if message_window.IsDeleted():
                    
                    message_window.TryToDismiss()
                    
                    break
                    
                else:
                    
                    message_window.UpdateMessage()
                    
                
            
        
    
    def AddMessage( self, job_key ):
        
        try:
            
            was_merged = self._TryToMergeMessage( job_key )
            
            if was_merged:
                
                return
                
            
            self._pending_job_keys.append( job_key )
            
            if self._OKToAlterUI():
                
                self._CheckPending()
                
            
        except:
            
            HydrusData.Print( traceback.format_exc() )
            
        
    
    def CleanBeforeDestroy( self ):
        
        for job_key in self._pending_job_keys:
            
            if job_key.IsCancellable():
                
                job_key.Cancel()
                
            
        
        for i in range( self._message_vbox.count() ):
            
            message_window = self._message_vbox.itemAt( i ).widget()
            
            if not message_window: continue
            
            job_key = message_window.GetJobKey()
            
            if job_key.IsCancellable():
                
                job_key.Cancel()
                
            
        
        sys.excepthook = self._old_excepthook
        
        HydrusData.ShowException = self._old_show_exception
        HydrusData.ShowExceptionTuple = self._old_show_exception_tuple
        HydrusData.ShowText = self._old_show_text
        
    
    def Dismiss( self, window ):
        
        self._message_vbox.removeWidget( window )
        
        window.deleteLater()
        
        if self._OKToAlterUI():
            
            self._CheckPending()
            
        
    
    def DismissAll( self ):
        
        self._pending_job_keys = [ job_key for job_key in self._pending_job_keys if job_key.IsPausable() or job_key.IsCancellable() ]
        
        items = []
        
        for i in range( self._message_vbox.count() ):
            
            items.append( self._message_vbox.itemAt( i ) )
            
        
        for item in items:

            message_window = item.widget()
            
            if not message_window: continue
            
            message_window.TryToDismiss()
            
        
        self._CheckPending()
        
    
    def ExpandCollapse( self ):
        
        if self._message_panel.isVisible():
            
            self._message_panel.setVisible( False )
            
        else:
            
            self._message_panel.show()
            
        
        self.MakeSureEverythingFits()
        
    
    def resizeEvent( self, event ):
        
        if not self or not QP.isValid( self ): # funny runtime error caused this
            
            return
            
        
        if self._OKToAlterUI():
            
            self._SizeAndPositionAndShow()
            
        
        event.ignore()
        
    
    def EventParentMovedOrResized( self, event ):
        
        if not self or not QP.isValid( self ): # funny runtime error caused this
            
            return
            
        
        if self._OKToAlterUI():
            
            self._SizeAndPositionAndShow()
            
        
        return True # was: event.ignore()
        
    
    def MakeSureEverythingFits( self ):
        
        if self._OKToAlterUI():
            
            self._SizeAndPositionAndShow()
            
        
    
    def REPEATINGUpdate( self ):
        
        try:
            
            self._DoDebugHide()
            
            if self._OKToAlterUI():
                
                self._Update()
                
                self._CheckPending()
                
            
        except:
            
            self._update_job.Cancel()
            
            raise
            
        
    
# This was originally a reviewpanel subclass which is a scroll area subclass, but having it in a scroll area didn't work out with dynamically updating size as the widget contents change.
class PopupMessageDialogPanel( QW.QWidget ):
    
    def __init__( self, parent, job_key, hide_main_gui = False ):
        
        QW.QWidget.__init__( self, parent )
        
        self._yesno_open = False
        
        self._hide_main_gui = hide_main_gui
        
        self._job_key = job_key
        
        self._message_window = PopupMessage( self, self, self._job_key )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._message_window )
        
        self.setLayout( vbox )
        
        self._windows_hidden = []
        
        self._HideOtherWindows()
        
        self._message_pubbed = False
        
        self._update_job = HG.client_controller.CallRepeatingQtSafe( self, 0.25, 0.5, 'repeating popup dialog update', self.REPEATINGUpdate )
        
    
    def CleanBeforeDestroy( self ):

        pass
        

    def _HideOtherWindows( self ):
        
        from hydrus.client.gui import ClientGUI
        
        for tlw in QW.QApplication.topLevelWidgets():
            
            if isinstance( tlw, ClientGUI.FrameGUI ):
                
                pass
                
            
            if tlw == self.window():
                
                continue
                
            
            if not isinstance( tlw, ( ClientGUITopLevelWindows.Frame, ClientGUITopLevelWindows.MainFrame, ClientGUITopLevelWindows.NewDialog ) ):
                
                continue
                
            
            if ClientGUIFunctions.IsQtAncestor( self, tlw, through_tlws = True ):
                
                continue
                
            
            if isinstance( tlw, ClientGUI.FrameGUI ) and not self._hide_main_gui:
                
                continue
                
            
            if not tlw.isVisible() or tlw.isMinimized():
                
                continue
                
            
            tlw.hide()
            
            self._windows_hidden.append( tlw )
            
        
    
    def _ReleaseMessage( self ):
        
        if not self._message_pubbed:
            
            HG.client_controller.pub( 'message', self._job_key )
            
            self._message_pubbed = True
            
            self._RestoreOtherWindows()
            
        
    
    def _RestoreOtherWindows( self ):
        
        for tlw in self._windows_hidden:
            
            tlw.show()
            
        
        self._windows_hidden = []
        
    
    def _Update( self ):
        
        self._message_window.UpdateMessage()
        
        # Resize the window after updates
        # The problem is that when the window is created, the initial size is too small because all widgets are empty before the first update,
        # but after it updates it doesn't want to resize the window, rather it just adds scrollbars.
        # This is a manual fix. Need to find a better solution...
        
        self.layout().update()
        self._message_window.adjustSize()
        self.adjustSize()
        self.window().adjustSize()
        
    
    def Dismiss( self, window ):
        
        return
        
    
    def CheckValid( self ):
        
        return True
        
    
    def UserIsOKToOK( self ):
        
        return self.UserIsOKToCancel()
        
    
    def UserIsOKToCancel( self ):
        
        if self._job_key.IsDone():
            
            self._ReleaseMessage()
            
        elif self._job_key.IsCancellable():
            
            text = 'Cancel/stop job?'
            
            self._yesno_open = True
            
            try:
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text )
                
            finally:
                
                self._yesno_open = False
                
            
            if result == QW.QDialog.Accepted:
                
                self._job_key.Cancel()
                
                self._ReleaseMessage()
                
            else:
                
                return False
                
            
        else:
            
            QW.QMessageBox.warning( self, 'Warning', 'Unfortunately, this job cannot be cancelled. If it really is taking too long, please kill the client through task manager.' )
            
            return False
            
        
        return True
        
    
    def REPEATINGUpdate( self ):
        
        try:
            
            if self._job_key.IsDone():
                
                if not self._yesno_open: # don't close while a child dialog open m8
                    
                    parent = self.parentWidget()
                    
                    if parent.isModal(): # event sometimes fires after modal done
                        
                        parent.DoOK()
                        
                    
                
            else:
                
                self._Update()
                
            
        except:
            
            self._update_job.Cancel()
            
            raise
            
        

class PopupMessageSummaryBar( PopupWindow ):
    
    expandCollapse = QC.Signal()
    
    def __init__( self, parent, manager ):
        
        PopupWindow.__init__( self, parent, manager )
        
        hbox = QP.HBoxLayout()
        
        self._text = ClientGUICommon.BetterStaticText( self )
        
        self._expand_collapse = ClientGUICommon.BetterButton( self, '\u25bc', self.ExpandCollapse )
        
        dismiss_all = ClientGUICommon.BetterButton( self, 'dismiss all', self._manager.DismissAll )
        
        QP.AddToLayout( hbox, self._text, CC.FLAGS_CENTER_PERPENDICULAR )
        hbox.addStretch( 1 )
        QP.AddToLayout( hbox, dismiss_all, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._expand_collapse, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def ExpandCollapse( self ):
        
        self.expandCollapse.emit()
        
        current_text = self._expand_collapse.text()
        
        if current_text == '\u25bc':
            
            new_text = '\u25b2'
            
        else:
            
            new_text = '\u25bc'
            
        
        self._expand_collapse.setText( new_text )
        
    
    def TryToDismiss( self ):
        
        pass
        
    
    def SetNumMessages( self, num_messages_pending ):
        
        if num_messages_pending == 1:
            
            self._text.setText( '1 message' )
            
        else:
            
            self._text.setText( HydrusData.ToHumanInt(num_messages_pending)+' messages' )
            
        
