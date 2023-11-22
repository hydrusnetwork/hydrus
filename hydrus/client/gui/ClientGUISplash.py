import os
import threading

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class FrameSplashPanel( QW.QWidget ):
    
    def __init__( self, parent, controller, frame_splash_status ):
        
        QW.QWidget.__init__( self, parent )
        
        self._controller = controller
        
        self._my_status = frame_splash_status
        
        self._my_status.SetWindow( self )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 64 )
        
        self.setMinimumWidth( width )
        
        self.setMaximumWidth( width * 2 )
        
        self._drag_last_pos = None
        self._initial_position = self.parentWidget().pos()
        
        # this is 124 x 166
        self._hydrus_pixmap = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'hydrus_splash.png' ) )
        
        self._image_label = QW.QLabel( self )
        
        self._image_label.setPixmap( self._hydrus_pixmap )
        
        self._image_label.setAlignment( QC.Qt.AlignCenter )
        
        self._title_label = ClientGUICommon.BetterStaticText( self, label = ' ' )
        self._status_label = ClientGUICommon.BetterStaticText( self, label = ' ' )
        self._status_sub_label = ClientGUICommon.BetterStaticText( self, label = ' ' )
        
        self._title_label.setAlignment( QC.Qt.AlignCenter )
        self._status_label.setAlignment( QC.Qt.AlignCenter )
        self._status_sub_label.setAlignment( QC.Qt.AlignCenter )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._image_label, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._title_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._status_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._status_sub_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        margin = ClientGUIFunctions.ConvertTextToPixelWidth( self, 3 )
        
        self._image_label.setMargin( margin )
        
        self.setLayout( vbox )
        
    
    def mouseMoveEvent( self, event ):
        
        if ( event.buttons() & QC.Qt.LeftButton ) and self._drag_last_pos is not None:
            
            mouse_pos = QG.QCursor.pos()
            
            delta = mouse_pos - self._drag_last_pos
            
            win = self.window()
            
            win.move( win.pos() + delta )
            
            self._drag_last_pos = QC.QPoint( mouse_pos )
            
            event.accept()
            
            return
            
        
        QW.QWidget.mouseMoveEvent( self, event )
        
    
    def mousePressEvent( self, event ):
        
        if event.button() == QC.Qt.LeftButton:
            
            self._drag_last_pos = QG.QCursor.pos()
            
            event.accept()
            
            return
            
        
        QW.QWidget.mousePressEvent( self, event )
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() == QC.Qt.LeftButton:
            
            self._drag_last_pos = None
            
            event.accept()
            
            return
            
        
        QW.QWidget.mouseReleaseEvent( self, event )
        
    
    def SetDirty( self ):
        
        ( title_text, status_text, status_subtext ) = self._my_status.GetTexts()
        
        self._title_label.setText( title_text )
        self._status_label.setText( status_text )
        self._status_sub_label.setText( status_subtext )
        
    
# We have this to be an off-Qt-thread-happy container for this info, as the framesplash has to deal with messages in the fuzzy time of shutdown
# all of a sudden, pubsubs are processed in non Qt-thread time, so this handles that safely and lets the gui know if the Qt controller is still running
class FrameSplashStatus( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self._updater = None
        
        self._title_text = ''
        self._status_text = ''
        self._status_subtext = ''
        
    
    def _NotifyUI( self ):
        
        updater = self._updater
        
        if updater is not None:
            
            updater.Update()
            
        
    
    def GetTexts( self ):
        
        with self._lock:
            
            return ( self._title_text, self._status_text, self._status_subtext )
            
        
    
    def Reset( self ):
        
        with self._lock:
            
            self._title_text = ''
            self._status_text = ''
            self._status_subtext = ''
            
            self._updater = None
            
        
    
    def SetText( self, text, print_to_log = True ):
        
        if self._updater is not None and print_to_log and len( text ) > 0:
            
            HydrusData.Print( text )
            
        
        with self._lock:
            
            self._status_text = text
            self._status_subtext = ''
            
        
        self._NotifyUI()
        
    
    def SetSubtext( self, text ):
        
        if HG.boot_debug and self._updater is not None and len( text ) > 0:
            
            HydrusData.Print( text )
            
        
        with self._lock:
            
            self._status_subtext = text
            
        
        self._NotifyUI()
        
    
    def SetTitleText( self, text, clear_undertexts = True, print_to_log = True ):
        
        if self._updater is not None and print_to_log:
            
            HydrusData.DebugPrint( text )
            
        
        with self._lock:
            
            self._title_text = text
            
            if clear_undertexts:
                
                self._status_text = ''
                self._status_subtext = ''
                
            
        
        self._NotifyUI()
        
    
    def SetWindow( self, ui: FrameSplashPanel ):
        
        self._updater = ClientGUIAsync.FastThreadToGUIUpdater( ui, ui.SetDirty )
        
    
class FrameSplash( QW.QWidget ):
    
    def __init__( self, controller, title, frame_splash_status: FrameSplashStatus ):
        
        self._controller = controller
        
        QW.QWidget.__init__( self, None )
        
        self.setWindowFlag( QC.Qt.CustomizeWindowHint )
        self.setWindowFlag( QC.Qt.WindowContextHelpButtonHint, on = False )
        self.setWindowFlag( QC.Qt.WindowCloseButtonHint, on = False )
        self.setWindowFlag( QC.Qt.WindowMaximizeButtonHint, on = False )
        self.setAttribute( QC.Qt.WA_DeleteOnClose )
        
        self.setWindowTitle( title )
        
        self.setWindowIcon( QG.QIcon( self._controller.frame_icon_pixmap ) )
        
        self._my_panel = FrameSplashPanel( self, self._controller, frame_splash_status )
        
        self._cancel_shutdown_maintenance = ClientGUICommon.BetterButton( self, 'stop shutdown maintenance', self.CancelShutdownMaintenance )
        
        self._cancel_shutdown_maintenance.hide()
        
        #
        
        self._vbox = QP.VBoxLayout()
        
        QP.AddToLayout( self._vbox, self._cancel_shutdown_maintenance, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( self._vbox, self._my_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( self._vbox )
        
        screen = ClientGUIFunctions.GetMouseScreen()
        
        if screen is not None:
            
            self.move( screen.availableGeometry().center() - self.rect().center() )
            
        
        self.show()
        
        self.raise_()
        
    
    def CancelShutdownMaintenance( self ):
        
        self._cancel_shutdown_maintenance.setText( 'stopping' + HC.UNICODE_ELLIPSIS )
        self._cancel_shutdown_maintenance.setEnabled( False )
        
        HG.do_idle_shutdown_work = False
        
    
    def ShowCancelShutdownButton( self ):
        
        self._cancel_shutdown_maintenance.show()
        
    
