import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP

class ResizingEventFilter( QC.QObject ):
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.Resize:
                
                event = typing.cast( QG.QResizeEvent, event )
                
                parent = self.parent()
                
                if isinstance( parent, ResizingScrolledPanel ):
                    
                    # weird hack fix for a guy who was getting QPaintEvents in here
                    if not hasattr( event, 'oldSize' ):
                        
                        return False
                        
                    
                    old_size = event.oldSize()
                    size = event.size()
                    
                    width_larger = size.width() > old_size.width() and size.height() >= old_size.height()
                    height_larger = size.width() >= old_size.width() and size.height() > old_size.height()
                    
                    if width_larger or height_larger:
                        
                        CG.client_controller.CallAfter( parent, parent.WidgetJustSized, width_larger, height_larger )
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

class ResizingScrolledPanel( QW.QScrollArea ):
    
    okSignal = QC.Signal()
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self.setWidget( QW.QWidget( self ) )
        
        self.setWidgetResizable( True )
        
        self.widget().installEventFilter( ResizingEventFilter( self ) )
        
        self._last_just_sized_cascade_start_time = 0.0
        self._number_of_just_sizedes = 0
        
    
    def _OKParent( self ):
        
        self.okSignal.emit()
        
    
    def CheckValid( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def sizeHint( self ):
        
        if self.widget():
            
            # just as a fun note, QScrollArea does a 12 x 8 character height sizeHint on its own here due to as-yet invalid widget size, wew lad
            
            frame_width = self.frameWidth()
            
            frame_size = QC.QSize( frame_width * 2, frame_width * 2 )
            
            size_hint = self.widget().sizeHint() + frame_size
            
            #visible_size = self.widget().visibleRegion().boundingRect().size()
            #size_hint = self.widget().sizeHint() + self.size() - visible_size
            
            available_screen_size = self.screen().availableGeometry().size()
            
            screen_fill_factor = 0.85 # don't let size hint be bigger than this percentage of the available screen width/height
            
            if size_hint.width() > screen_fill_factor * available_screen_size.width():
                
                size_hint.setWidth( int( screen_fill_factor * available_screen_size.width() ) )
                
            if size_hint.height() > screen_fill_factor * available_screen_size.height():
                
                size_hint.setHeight( int( screen_fill_factor * available_screen_size.height() ) )
                
            
            return size_hint
            
        else:
            
            return QW.QScrollArea.sizeHint( self )
            
        
    
    def UserIsOKToOK( self ):
        
        return True
        
    
    def UserIsOKToCancel( self ):
        
        return True
        
    
    def WidgetJustSized( self, width_larger, height_larger ):
        
        if width_larger or height_larger:
            
            # ok this is a stupid sizing hack to stop the ever-growing window that has a sizeHint three pixels bigger than its current size causing a resize growth loop
            # if we get a bunch of resizes real quick, we cut them off, hopefully breaking the cycle
            if not HydrusTime.TimeHasPassedFloat( self._last_just_sized_cascade_start_time + 1.0 ):
                
                self._number_of_just_sizedes += 1
                
                if self._number_of_just_sizedes >= 5:
                    
                    return
                    
                
            else:
                
                self._last_just_sized_cascade_start_time = HydrusTime.GetNowFloat()
                
                self._number_of_just_sizedes = 1
                
            
        
        widget_minimum_size_hint = self.widget().minimumSizeHint()
        widget_normal_size_hint = self.widget().sizeHint()
        
        widget_size_hint = QC.QSize( max( widget_minimum_size_hint.width(), widget_normal_size_hint.width() ), max( widget_minimum_size_hint.height(), widget_normal_size_hint.height() ) )
        
        my_size = self.size()
        
        width_increase = 0
        height_increase = 0
        
        if width_larger:
            
            width_increase = max( 0, widget_size_hint.width() - my_size.width() )
            
        
        if height_larger:
            
            height_increase = max( 0, widget_size_hint.height() - my_size.height() )
            
        
        if width_increase > 0 or height_increase > 0:
            
            window = self.window()
            
            if isinstance( window, ( ClientGUITopLevelWindows.DialogThatResizes, ClientGUITopLevelWindows.FrameThatResizes ) ):
                
                desired_size_delta = QC.QSize( width_increase, height_increase )
                
                ClientGUITopLevelWindows.ExpandTLWIfPossible( window, window._frame_key, desired_size_delta )
                
            
        
    
class EditPanel( ResizingScrolledPanel ):
    
    def GetValue( self ):
        
        raise NotImplementedError()
        
    
    def CheckValid( self ):
        
        # raises veto if not valid
        self.GetValue()
        
    
class EditSingleCtrlPanel( CAC.ApplicationCommandProcessorMixin, EditPanel ):
    
    def __init__( self, parent, ok_on_these_commands = None, message = None ):
        
        super().__init__( parent )
        
        self._control = None
        
        if ok_on_these_commands is None:
            
            ok_on_these_commands = set()
            
        
        self._ok_on_these_commands = set( ok_on_these_commands )
        
        #
        
        self._vbox = QP.VBoxLayout( margin = 0 )
        
        if message is not None:
            
            from hydrus.client.gui.widgets import ClientGUICommon
            
            st = ClientGUICommon.BetterStaticText( self, label = message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( self._vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.widget().setLayout( self._vbox )
        
        self._my_shortcuts_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'media' ] )
        
    
    def GetValue( self ):
        
        if hasattr( self._control, 'GetValue' ):
            
            return self._control.GetValue()
            
        elif hasattr( self._control, 'toPlainText' ):
            
            return self._control.toPlainText()
            
        
        return self._control.value()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action in self._ok_on_these_commands:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetControl( self, control, perpendicular = False ):
        
        self._control = control
        
        self.setFocusProxy( self._control )
        
        if perpendicular:
            
            flag = CC.FLAGS_EXPAND_PERPENDICULAR
            
        else:
            
            flag = CC.FLAGS_EXPAND_BOTH_WAYS
            
        
        QP.AddToLayout( self._vbox, control, flag )
        
        if perpendicular:
            
            self._vbox.addStretch( 0 )
            
        
    

class ManagePanel( ResizingScrolledPanel ):
    
    def CommitChanges( self ):
        
        raise NotImplementedError()
        
    

class ReviewPanel( ResizingScrolledPanel ):
    
    pass
    
