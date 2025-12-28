import collections
import collections.abc
import sys
import threading
import traceback
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.widgets import ClientGUICommon

class PopupWindow( QW.QFrame ):
    
    dismiss = QC.Signal( QW.QWidget )
    iJustChangedSize = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Plain )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventDismiss )
        
    
    def TryToDismiss( self ):
        
        self.dismiss.emit( self )
        
    
    def EventDismiss( self, event ):
        
        self.TryToDismiss()
        
    

class PopupMessage( PopupWindow ):
    
    TEXT_CUTOFF = 1024
    
    def __init__( self, parent, job_status: ClientThreading.JobStatus ):
        
        super().__init__( parent )
        
        self._job_status = job_status
        
        vbox_margin = 2
        
        vbox = QP.VBoxLayout( vbox_margin )
        
        self._title = ClientGUICommon.BetterStaticText( self )
        self._title.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignVCenter )
        
        font = self._title.font()
        font.setBold( True )
        self._title.setFont( font )
        
        popup_message_character_width = CG.client_controller.new_options.GetInteger( 'popup_message_character_width' )
        
        popup_char_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._title, popup_message_character_width )
        
        if CG.client_controller.new_options.GetBoolean( 'popup_message_force_min_width' ):
            
            self.setFixedWidth( popup_char_width )
            
        else:
            
            self.setMaximumWidth( popup_char_width )
            
        
        popup_char_width_sub_widget = popup_char_width - ( vbox_margin * 2 )
        
        # I discovered if I set the maxWidth to the static texts themselves, the sizehints here stop borking out and long multiline text paragraphs will happily size themselves
        # if not set, they will be clipped by higher sizeHint somehow. 500x90 is told to fit in a 400x90 hole, the QWidget PopupWindow is not clever enough to propagate the max width down to (dynamic, height-for-width) children?
        
        self._title.setWordWrap( True )
        self._title.setMaximumWidth( popup_char_width_sub_widget )
        self._title_ev = QP.WidgetEventFilter( self._title )
        self._title_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._title.hide()
        
        self._text_1 = ClientGUICommon.BetterStaticText( self )
        self._text_1.setWordWrap( True )
        self._text_1.setMaximumWidth( popup_char_width_sub_widget )
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
        self._text_2.setMaximumWidth( popup_char_width_sub_widget )
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
        self._network_job_ctrl.SetShouldUpdateFreely( True )
        self._network_job_ctrl.hide()
        self._time_network_job_disappeared = 0
        
        # this is kind of stupid, but whatever for now
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._network_job_ctrl, 58 )
        self._network_job_ctrl.setMinimumWidth( width )
        
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
        self._tb_text.setWordWrap( True )
        self._tb_text.setMaximumWidth( popup_char_width_sub_widget )
        self._tb_text_ev = QP.WidgetEventFilter( self._tb_text )
        self._tb_text_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._tb_text.hide()
        
        self._copy_tb_button = ClientGUICommon.BetterButton( self, 'copy traceback information', self.CopyTB )
        self._copy_tb_button_ev = QP.WidgetEventFilter( self._copy_tb_button )
        self._copy_tb_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._copy_tb_button.hide()
        
        self._pause_button = ClientGUICommon.IconButton( self, CC.global_icons().pause, self.PausePlay )
        self._pause_button_ev = QP.WidgetEventFilter( self._pause_button )
        self._pause_button_ev.EVT_RIGHT_DOWN( self.EventDismiss )
        self._pause_button.hide()
        
        self._cancel_button = ClientGUICommon.IconButton( self, CC.global_icons().stop, self.Cancel )
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
        QP.AddToLayout( vbox, yes_no_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._network_job_ctrl, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._copy_to_clipboard_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._show_files_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._user_callable_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._show_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tb_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._copy_tb_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
    
    def _NoButton( self ):
        
        self._job_status.SetVariable( 'popup_yes_no_answer', False )
        
        self._job_status.FinishAndDismiss()
        
        self._yes.hide()
        self._no.hide()
        
    
    def _ProcessText( self, text ):
        
        text = str( text )
        
        if len( text ) > self.TEXT_CUTOFF:
            
            new_text = 'The text is too long to display here. Here is the start of it (the rest is printed to the log):'
            
            new_text += '\n'
            
            new_text += text[ : self.TEXT_CUTOFF ]
            
            text = new_text
            
        
        return text
        
    
    def _YesButton( self ):
        
        self._job_status.SetVariable( 'popup_yes_no_answer', True )
        
        self._job_status.FinishAndDismiss()
        
        self._yes.hide()
        self._no.hide()
        
    
    def CallUserCallable( self ):
        
        user_callable = self._job_status.GetUserCallable()
        
        if user_callable is not None:
            
            user_callable()
            
        
    
    def Cancel( self ):
        
        self._job_status.Cancel()
        
        self._pause_button.setEnabled( False )
        self._cancel_button.setEnabled( False )
        
    
    def CopyTB( self ):
        
        info = 'v{}, {}, {}'.format( HC.SOFTWARE_VERSION, sys.platform.lower(), 'frozen' if HC.RUNNING_FROM_FROZEN_BUILD else 'source' )
        trace = self._job_status.ToString()
        
        full_text = info + '\n' + trace
        
        CG.client_controller.pub( 'clipboard', 'text', full_text )
        
    
    def CopyToClipboard( self ):
        
        result = self._job_status.GetIfHasVariable( 'popup_clipboard' )
        
        if result is not None:
            
            ( title, text ) = result
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def PausePlay( self ):
        
        self._job_status.PausePlay()
        
        if self._job_status.IsPaused():
            
            self._pause_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._pause_button.SetIconSmart( CC.global_icons().pause )
            
        
    
    def ShowFiles( self ):
        
        result = self._job_status.GetFiles()
        
        if result is not None:
            
            ( hashes, attached_files_label ) = result
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
            
            self._show_files_button.setEnabled( False )
            
            def work_callable():
                
                presented_hashes = CG.client_controller.Read( 'filter_hashes', location_context, hashes )
                
                return presented_hashes
                
            
            def publish_callable( presented_hashes ):
                
                if len( presented_hashes ) != len( hashes ):
                    
                    self._job_status.SetFiles( presented_hashes, attached_files_label )
                    
                    if len( presented_hashes ) == 0:
                        
                        self.TryToDismiss()
                        
                    
                
                if len( presented_hashes ) > 0:
                    
                    CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = presented_hashes, page_name = attached_files_label )
                    
                
                self._show_files_button.setEnabled( True )
                
            
            def errback_callable( etype, value, tb ):
                
                HydrusData.ShowText( 'Sorry, unable to show those files:' )
                HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
                
                self._show_files_button.setEnabled( True )
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
            
            job.start()
            
        
    
    def ShowTB( self ):
        
        if self._tb_text.isHidden():
            
            self._show_tb_button.setText( 'hide traceback' )
            
            self._tb_text.show()
            
        else:
        
            self._show_tb_button.setText( 'show traceback' )
            
            self._tb_text.hide()
            
        
        self.updateGeometry()
        
        self.iJustChangedSize.emit()
        
    
    def GetJobStatus( self ):
        
        return self._job_status
        
    
    def IsDismissed( self ):
        
        return self._job_status.IsDismissed()
        
    
    def TryToDismiss( self ):
        
        if self._job_status.IsDone():
            
            self._job_status.FinishAndDismiss()
            
            PopupWindow.TryToDismiss( self )
            
        
    
    def UpdateMessage( self ):
        
        title = self._job_status.GetStatusTitle()
        
        if title is not None:
            
            self._title.show()
            
            self._title.setText( title )
            
        else:
            
            self._title.hide()
            
        
        #
        
        paused = self._job_status.IsPaused()
        
        popup_text_1 = self._job_status.GetStatusText()
        
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
        
        popup_gauge_1 = self._job_status.GetGauge()
        
        if popup_gauge_1 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_1
            
            self._gauge_1.SetRange( gauge_range )
            self._gauge_1.SetValue( gauge_value )
            
            self._gauge_1.show()
            
        else:
            
            self._gauge_1.hide()
            
        
        #
        
        popup_text_2 = self._job_status.GetStatusText( 2 )
        
        if popup_text_2 is not None and not paused:
            
            text = popup_text_2
            
            self._text_2.setText( self._ProcessText( text ) )
            
            self._text_2.show()
            
        else:
            
            self._text_2.hide()
            
        
        #
        
        popup_gauge_2 = self._job_status.GetIfHasVariable( 'popup_gauge_2' )
        
        if popup_gauge_2 is not None and not paused:
            
            ( gauge_value, gauge_range ) = popup_gauge_2
            
            self._gauge_2.SetRange( gauge_range )
            self._gauge_2.SetValue( gauge_value )
            
            self._gauge_2.show()
            
        else:
            
            self._gauge_2.hide()
            
        
        #
        
        popup_yes_no_question = self._job_status.GetIfHasVariable( 'popup_yes_no_question' )
        
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
        
        network_job = self._job_status.GetNetworkJob()
        
        if network_job is None:
            
            if self._network_job_ctrl.HasNetworkJob():
                
                self._network_job_ctrl.ClearNetworkJob()
                
                self._time_network_job_disappeared = HydrusTime.GetNow()
                
            
            if not self._network_job_ctrl.isHidden() and HydrusTime.TimeHasPassed( self._time_network_job_disappeared + 10 ):
                
                self._network_job_ctrl.hide()
                
            
        else:
            
            self._network_job_ctrl.SetNetworkJob( network_job )
            
            self._network_job_ctrl.show()
            
        
        #
        
        popup_clipboard = self._job_status.GetIfHasVariable( 'popup_clipboard' )
        
        if popup_clipboard is not None:
            
            ( title, text ) = popup_clipboard
            
            if self._copy_to_clipboard_button.text() != title:
                
                self._copy_to_clipboard_button.setText( title )
                
            
            self._copy_to_clipboard_button.show()
            
        else:
            
            self._copy_to_clipboard_button.hide()
            
        
        #
        
        result = self._job_status.GetFiles()
        
        if result is not None:
            
            ( hashes, attached_files_label ) = result
            
            text = '{} - show {} files'.format( attached_files_label, HydrusNumbers.ToHumanInt( len( hashes ) ) )
            
            if self._show_files_button.text() != text:
                
                self._show_files_button.setText( text )
                
            
            self._show_files_button.show()
            
        else:
            
            self._show_files_button.hide()
            
        
        #
        
        user_callable = self._job_status.GetUserCallable()
        
        if user_callable is None:
            
            self._user_callable_button.hide()
            
        else:
            
            self._user_callable_button.setText( user_callable.GetLabel() )
            
            self._user_callable_button.show()
            
        
        #
        
        popup_traceback = self._job_status.GetTraceback()
        
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
        
        if self._job_status.IsPausable():
            
            self._pause_button.show()
            
        else:
            
            self._pause_button.hide()
            
        
        if self._job_status.IsCancellable():
            
            self._cancel_button.show()
            
        else:
            
            self._cancel_button.hide()
            
        
    

class JobStatusPopupQueue( object ):
    
    def __init__( self ):
        
        self._job_status_ordered_dict_queue: typing.OrderedDict[ bytes, ClientThreading.JobStatus ] = collections.OrderedDict()
        
        self._job_statuses_in_view: set[ ClientThreading.JobStatus ] = set()
        
        self._lock = threading.Lock()
        
    
    def AddJobStatus( self, job_status: ClientThreading.JobStatus ):
        
        with self._lock:
            
            self._job_status_ordered_dict_queue[ job_status.GetKey() ] = job_status
            
        
    
    def ClearAllDeleted( self ):
        
        with self._lock:
            
            removees = [ job_status.GetKey() for job_status in self._job_status_ordered_dict_queue.values() if job_status.IsDismissed() ]
            
            for job_status_key in removees:
                
                del self._job_status_ordered_dict_queue[ job_status_key ]
                
            
            self._job_statuses_in_view = { job_status for job_status in self._job_statuses_in_view if not job_status.IsDismissed() }
            
        
    
    def DeleteAllPossible( self ):
        
        with self._lock:
            
            for job_status in self._job_status_ordered_dict_queue.values():
                
                if job_status.IsDone():
                    
                    job_status.FinishAndDismiss()
                    
                
            
        
    
    def GetCount( self ) -> int:
        
        with self._lock:
                
            return len( self._job_status_ordered_dict_queue )
            
        
    
    def GetInViewCount( self ) -> int:
        
        with self._lock:
            
            return len( self._job_statuses_in_view )
            
        
    
    def GetJobStatus( self, job_status_key: bytes ) -> ClientThreading.JobStatus | None:
        
        with self._lock:
            
            return self._job_status_ordered_dict_queue.get( job_status_key, None )
            
        
    
    def GetJobStatuses( self, only_in_view = False ) -> list[ ClientThreading.JobStatus ]:
        
        with self._lock:
            
            if only_in_view:
                
                return [ job_status for job_status in self._job_status_ordered_dict_queue.values() if job_status in self._job_statuses_in_view ]
                
            else:
                
                return list( self._job_status_ordered_dict_queue.values() )
                
            
        
    
    def GetNextJobStatusToShow( self ) -> ClientThreading.JobStatus | None:
        
        with self._lock:
            
            for job_status in self._job_status_ordered_dict_queue.values():
                
                if job_status not in self._job_statuses_in_view:
                    
                    return job_status
                    
                
            
            return None
            
        
    
    def HavePendingToShow( self ):
        
        with self._lock:
            
            return len( self._job_status_ordered_dict_queue ) > len( self._job_statuses_in_view )
            
        
    
    def PutJobStatusInView( self, job_status ):
        
        with self._lock:
            
            self._job_statuses_in_view.add( job_status )
            
        
    
    def TryToMergeJobStatus( self, job_status: ClientThreading.JobStatus ) -> bool:
        
        if not job_status.GetIfHasVariable( 'attached_files_mergable' ):
            
            return False
            
        
        result = job_status.GetFiles()
        
        if result is not None:
            
            ( hashes, label ) = result
            
            for existing_job_status in self._job_status_ordered_dict_queue.values():
                
                if existing_job_status.GetIfHasVariable( 'attached_files_mergable' ):
                    
                    result = existing_job_status.GetFiles()
                    
                    if result is not None:
                        
                        ( existing_hashes, existing_label ) = result
                        
                        if existing_label == label:
                            
                            # could extend it in place, but let's be safe and make and set back a new one to catch errant sets and other list-tracking weirdness
                            new_hashes = list( existing_hashes )
                            
                            new_hashes.extend( hashes )
                            
                            new_hashes = HydrusLists.DedupeList( new_hashes )
                            
                            existing_job_status.SetFiles( new_hashes, existing_label )
                            
                            return True
                            
                        
                    
                
            
        
        return False
        
    

class PopupMessageManager( QW.QFrame ):
    
    def __init__( self, parent, job_status_queue: JobStatusPopupQueue ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Raised )
        self.setLineWidth( 1 )
        
        # We need this, or else if the QSS does not define a Widget background color (the default), these 'raised' windows are transparent lmao
        self.setAutoFillBackground( True )
        
        self._last_best_size_i_fit_on = ( 0, 0 )
        
        self._max_messages_to_display = 10
        self._current_num_messages = 0
        
        vbox = QP.VBoxLayout()
        
        self._message_panel = QW.QWidget( self )
        
        self._message_vbox = QP.VBoxLayout( margin = 0 )
        
        #vbox.setSizeConstraint( QW.QLayout.SetFixedSize )
        
        self._message_panel.setLayout( self._message_vbox )
        
        self._summary_bar = PopupMessageSummaryBar( self )
        
        QP.AddToLayout( vbox, self._message_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._summary_bar, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._job_status_queue = job_status_queue
        
        parent.installEventFilter( self )
        
        CG.client_controller.sub( self, 'AddMessage', 'message' )
        
        self._old_excepthook = sys.excepthook
        self._old_show_exception = HydrusData.ShowException
        self._old_show_exception_tuple = HydrusData.ShowExceptionTuple
        self._old_show_text = HydrusData.ShowText
        
        sys.excepthook = ClientData.CatchExceptionClient
        HydrusData.ShowException = ClientData.ShowExceptionClient
        HydrusData.ShowExceptionTuple = ClientData.ShowExceptionTupleClient
        HydrusData.ShowText = ClientData.ShowTextClient
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( 'initialising popup message manager' + HC.UNICODE_ELLIPSIS )
        
        self._update_job = CG.client_controller.CallRepeatingQtSafe( self, 0.25, 0.25, 'repeating popup message update', self.REPEATINGUpdate )
        
        self._summary_bar.dismissAll.connect( self.DismissAll )
        self._summary_bar.expandCollapse.connect( self.ExpandCollapse )
        
        CG.client_controller.CallLaterQtSafe( self, 0.5, 'initialise message', self.AddMessage, job_status )
        
        CG.client_controller.CallLaterQtSafe( self, 1.0, 'delete initial message', job_status.FinishAndDismiss )
        
    
    def _CheckPending( self ):
        
        we_added_some = False
        
        self._job_status_queue.ClearAllDeleted()
        
        while self._job_status_queue.GetInViewCount() < self._max_messages_to_display:
            
            job_status = self._job_status_queue.GetNextJobStatusToShow()
            
            if job_status is None:
                
                break
                
            
            we_added_some = True
            
            window = PopupMessage( self._message_panel, job_status )
            
            window.dismiss.connect( self.Dismiss )
            window.iJustChangedSize.connect( self.MakeSureEverythingFits )
            
            window.UpdateMessage()
            
            QP.AddToLayout( self._message_vbox, window, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._job_status_queue.PutJobStatusInView( job_status )
            
        
        total_messages = self._job_status_queue.GetCount()
        
        if total_messages != self._current_num_messages:
            
            self._current_num_messages = total_messages
            
            self._summary_bar.SetNumMessages( self._current_num_messages )
            
        
        if we_added_some:
            
            # for whatever reason, self._message_vbox.activate does not cause the vbox.sizeHint to be recalculated at this point. it just sits at the last value unless original was (0,0)?!?
            # so we'll do it callafter. it works
            
            CG.client_controller.CallAfterQtSafe( self, self.MakeSureEverythingFits )
            
        
    
    def _DisplayingError( self ):
        
        # this was used when we didn't update if the mouse wasn't on the same screen
        # we wouldn't be annoying unless there was a good reason such as this
        # let's hang on to this for a while, just in case
        
        for i in range( self._message_vbox.count() ):
            
            sizer_item = self._message_vbox.itemAt( i )
            
            message_window: PopupMessage | None = sizer_item.widget()
            
            if not message_window:
                
                continue
                
            
            job_status = message_window.GetJobStatus()
            
            if job_status.HadError():
                
                return True
                
            
        
        return False
        
    
    def _SizeAndPositionAndShow( self ):
        
        gui_frame = self.window()
        
        try:
            
            gui_is_hidden = gui_frame.isHidden()
            
            going_to_bug_out_at_hide_or_show = gui_is_hidden
            
            num_messages_displayed = self._message_vbox.count()
            
            there_is_stuff_to_display = num_messages_displayed > 0
            
            if there_is_stuff_to_display:
                
                if self.isHidden() and not going_to_bug_out_at_hide_or_show:
                    
                    self.show()
                    
                
                self.raise_()
                
                #
                
                my_ideal_size = self.sizeHint()
                
                if my_ideal_size != self.size():
                    
                    self.resize( my_ideal_size )
                    
                
                parent_size = gui_frame.size()
                
                my_x = ( parent_size.width() - my_ideal_size.width() ) - 20
                my_y = ( parent_size.height() - my_ideal_size.height() ) - 25
                
                my_ideal_position = QC.QPoint( my_x, my_y )
                
                if my_ideal_position != self.pos():
                    
                    self.move( my_ideal_position )
                    
                
                self.layout()
                
            else:
                
                if not self.isHidden() and not going_to_bug_out_at_hide_or_show:
                    
                    self.hide()
                    
                
            
        except:
            
            text = 'The popup message manager experienced a fatal error and will now stop working! Please restart the client as soon as possible! If this keeps happening, please email the details and your client.log to the hydrus developer.'
            
            HydrusData.Print( text )
            
            HydrusData.Print( traceback.format_exc() )
            
            ClientGUIDialogsMessage.ShowCritical( gui_frame, 'Popup Message Manager failure!', text )
            
            self._update_job.Cancel()
            
            self.CleanBeforeDestroy()
            
        
    
    def _OKToAlterUI( self ):
        
        main_gui = self.window()
        
        if main_gui.isHidden():
            
            return False
            
        
        if CG.client_controller.new_options.GetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor' ):
            
            on_my_monitor = ClientGUIFunctions.MouseIsOnMyDisplay( main_gui )
            
            if not on_my_monitor:
                
                return False
                
            
        
        if CG.client_controller.new_options.GetBoolean( 'freeze_message_manager_when_main_gui_minimised' ):
            
            main_gui_up = not main_gui.isMinimized()
            
            if not main_gui_up:
                
                return False
                
            
        
        return True
        
    
    def _Update( self ):
        
        if HG.started_shutdown:
            
            self._update_job.Cancel()
            
            self.CleanBeforeDestroy()
            
        
        for i in range( self._message_vbox.count() ):
            
            sizer_item = self._message_vbox.itemAt( i )
            
            message_window: PopupMessage | None = sizer_item.widget()
            
            if message_window:
                
                if message_window.IsDismissed():
                    
                    self._RemovePopupWindow( message_window )
                    
                    break
                    
                else:
                    
                    message_window.UpdateMessage()
                    
                
            
        
    
    def AddMessage( self, job_status ):
        
        try:
            
            was_merged = self._job_status_queue.TryToMergeJobStatus( job_status )
            
            if was_merged:
                
                return
                
            
            self._job_status_queue.AddJobStatus( job_status )
            
            if self._OKToAlterUI():
                
                self._CheckPending()
                
            
        except:
            
            HydrusData.Print( traceback.format_exc() )
            
        
    
    def CleanBeforeDestroy( self ):
        
        for job_status in self._job_status_queue.GetJobStatuses():
            
            if job_status.IsCancellable():
                
                job_status.Cancel()
                
            
        
        for i in range( self._message_vbox.count() ):
            
            message_window: PopupMessage | None = self._message_vbox.itemAt( i ).widget()
            
            if not message_window:
                
                continue
                
            
            job_status = message_window.GetJobStatus()
            
            if job_status.IsCancellable():
                
                job_status.Cancel()
                
            
        
        sys.excepthook = self._old_excepthook
        
        HydrusData.ShowException = self._old_show_exception
        HydrusData.ShowExceptionTuple = self._old_show_exception_tuple
        HydrusData.ShowText = self._old_show_text
        
    
    def _RemovePopupWindow( self, window: PopupMessage ):
        
        job_status = window.GetJobStatus()
        
        if not job_status.IsDone():
            
            return
            
        
        job_status.FinishAndDismiss()
        
        self._message_vbox.removeWidget( window )
        
        window.hide()
        
        # sizeHints are not immediately updated without this, lmao
        # note we have to do it on the sub vbox, not the self.layout() wew, so I guess it doesn't propagate down
        self._message_vbox.activate()
        
        window.deleteLater()
        
    
    def Dismiss( self, window: PopupMessage ):
        
        self._RemovePopupWindow( window )
        
        if self._OKToAlterUI():
            
            self._CheckPending()
            
            self._SizeAndPositionAndShow()
            
        
    
    def DismissAll( self ):
        
        self._job_status_queue.DeleteAllPossible()
        
        removees = []
        
        for i in range( self._message_vbox.count() ):
            
            item = self._message_vbox.itemAt( i )
            
            message_window: PopupMessage | None = item.widget()
            
            if not message_window:
                
                continue
                
            
            if message_window.GetJobStatus().IsDismissed():
                
                removees.append( message_window )
                
            
        
        for message_window in removees:
            
            self._RemovePopupWindow( message_window )
            
        
        if self._OKToAlterUI():
            
            self._CheckPending()
            
            self._SizeAndPositionAndShow()
            
        
    
    def ExpandCollapse( self ):
        
        self._message_panel.setVisible( self._message_panel.isHidden() )
        
        self.MakeSureEverythingFits()
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if watched == self.parentWidget():
                
                if event.type() in ( QC.QEvent.Type.Resize, QC.QEvent.Type.Move, QC.QEvent.Type.WindowStateChange ):
                    
                    if self._OKToAlterUI():
                        
                        self._SizeAndPositionAndShow()
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def MakeSureEverythingFits( self ):
        
        if self._OKToAlterUI():
            
            self._SizeAndPositionAndShow()
            
        
    
    def REPEATINGUpdate( self ):
        
        try:
            
            if self._OKToAlterUI():
                
                self._Update()
                
                self._CheckPending()
                
                self._SizeAndPositionAndShow()
                
            
        except:
            
            self._update_job.Cancel()
            
            raise
            
        
    

# This was originally a reviewpanel subclass which is a scroll area subclass, but having it in a scroll area didn't work out with dynamically updating size as the widget contents change.
class PopupMessageDialogPanel( QW.QWidget ):
    
    okSignal = QC.Signal()
    
    def __init__( self, parent, job_status, hide_main_gui = False ):
        
        super().__init__( parent )
        
        self._yesno_open = False
        
        self._hide_main_gui = hide_main_gui
        
        self._job_status = job_status
        
        self._message_window = PopupMessage( self, self._job_status )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._message_window, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._windows_hidden = []
        
        self._HideOtherWindows()
        
        self._message_pubbed = False
        
        self._update_job = CG.client_controller.CallRepeatingQtSafe( self, 0.25, 0.5, 'repeating popup dialog update', self.REPEATINGUpdate )
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        

    def _HideOtherWindows( self ):
        
        from hydrus.client.gui import ClientGUI
        
        for tlw in list( QW.QApplication.topLevelWidgets() ):
            
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
            
            CG.client_controller.pub( 'message', self._job_status )
            
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
        
    
    def CheckValid( self ):
        
        return True
        
    
    def UserIsOKToOK( self ):
        
        return self.UserIsOKToCancel()
        
    
    def UserIsOKToCancel( self ):
        
        if self._job_status.IsDone():
            
            self._ReleaseMessage()
            
        elif self._job_status.IsCancellable():
            
            text = 'Cancel/stop job?'
            
            self._yesno_open = True
            
            try:
                
                result = ClientGUIDialogsQuick.GetYesNo( self, text )
                
            finally:
                
                self._yesno_open = False
                
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._job_status.Cancel()
                
                self._ReleaseMessage()
                
            else:
                
                return False
                
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Unfortunately, this job cannot be cancelled. If it really is taking too long, please kill the client through task manager.' )
            
            return False
            
        
        return True
        
    
    def REPEATINGUpdate( self ):
        
        try:
            
            if self._job_status.IsDone():
                
                if not self._yesno_open: # don't close while a child dialog open m8
                    
                    parent = self.parentWidget()
                    
                    if parent.isModal(): # event sometimes fires after modal done
                        
                        self.okSignal.emit()
                        
                    
                
            else:
                
                self._Update()
                
            
        except:
            
            self._update_job.Cancel()
            
            raise
            
        

class PopupMessageSummaryBar( QW.QFrame ):
    
    dismissAll = QC.Signal()
    expandCollapse = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Plain )
        
        hbox = QP.HBoxLayout()
        
        self._text = ClientGUICommon.BetterStaticText( self )
        self._text.setAlignment( QC.Qt.AlignmentFlag.AlignLeft | QC.Qt.AlignmentFlag.AlignVCenter )
        
        self._expand_collapse = ClientGUICommon.BetterButton( self, '\u25bc', self.ExpandCollapse )
        
        dismiss_all = ClientGUICommon.BetterButton( self, 'dismiss all', self.dismissAll.emit )
        
        QP.AddToLayout( hbox, self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
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
        
    
    def SetNumMessages( self, num_messages_pending ):
        
        if num_messages_pending == 1:
            
            self._text.setText( '1 message' )
            
        else:
            
            self._text.setText( HydrusNumbers.ToHumanInt(num_messages_pending)+' messages' )
            
        
