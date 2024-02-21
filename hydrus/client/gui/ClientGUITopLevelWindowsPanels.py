from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import QtPorting as QP

class DialogThatTakesScrollablePanel( ClientGUITopLevelWindows.DialogThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False, do_not_activate = False ):
        
        self._panel = None
        self._hide_buttons = hide_buttons
        
        ClientGUITopLevelWindows.DialogThatResizes.__init__( self, parent, title, frame_key, do_not_activate = do_not_activate )
        
        self._InitialiseButtons()
        
    
    def _GetButtonBox( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseButtons( self ):
        
        raise NotImplementedError()
        
    
    def _UserIsOKToClose( self, value ):
        
        if value == QW.QDialog.Accepted:
            
            return self._panel.UserIsOKToOK()
            
        else:
            
            return self._panel.UserIsOKToCancel()
            
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUITopLevelWindows.DialogThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def SetPanel( self, panel: ClientGUIScrolledPanels.ResizingScrolledPanel ):
        
        self._panel = panel
        
        if hasattr( self._panel, 'okSignal'): self._panel.okSignal.connect( self.DoOK )
        
        buttonbox = self._GetButtonBox()
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if buttonbox is not None:
            
            QP.AddToLayout( vbox, buttonbox, CC.FLAGS_ON_RIGHT )
            
        
        self.setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
    
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
            
        
    
    def _TestValidityAndPresentVetoMessage( self, value ):
        
        if value != QW.QDialog.Accepted:
            
            return True
            
        
        try:
            
            value = self._panel.CheckValid()
            
            return True
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            return False
            
        
    

class DialogEdit( DialogApplyCancel ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog', hide_buttons = False ):
        
        DialogApplyCancel.__init__( self, parent, title, frame_key = frame_key, hide_buttons = hide_buttons )
        
    

class DialogManage( DialogApplyCancel ):
    
    def _DoClose( self, value ):
        
        if value == QW.QDialog.Accepted:
            
            try:
                
                self._panel.CommitChanges()
                
            except HydrusExceptions.VetoException as e:
                
                message = str( e )
                
                if len( message ) > 0:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, message )
                    
                
            
        
    

class DialogCustomButtonQuestion( DialogThatTakesScrollablePanel ):
    
    def __init__( self, parent, title, frame_key = 'regular_center_dialog' ):
        
        DialogThatTakesScrollablePanel.__init__( self, parent, title, frame_key = frame_key )
        
    
    def _GetButtonBox( self ):
        
        return None
        
    
    def _InitialiseButtons( self ):
        
        pass
        
    

class FrameThatTakesScrollablePanel( ClientGUITopLevelWindows.FrameThatResizes ):
    
    def __init__( self, parent, title, frame_key = 'regular_dialog' ):
        
        self._panel = None
        
        ClientGUITopLevelWindows.FrameThatResizes.__init__( self, parent, title, frame_key )
        
        self._ok = QW.QPushButton( 'close', self )
        self._ok.clicked.connect( self.close )
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUITopLevelWindows.FrameThatResizes.CleanBeforeDestroy( self )
        
        if hasattr( self._panel, 'CleanBeforeDestroy' ):
            
            self._panel.CleanBeforeDestroy()
            
        
    
    def keyPressEvent( self, event ):
        
        shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event )
        
        escape_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        command_w_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'W' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        
        if shortcut == escape_shortcut or ( HC.PLATFORM_MACOS and shortcut == command_w_shortcut ):
            
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
        
        QP.AddToLayout( vbox, self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._ok, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        ClientGUITopLevelWindows.SetInitialTLWSizeAndPosition( self, self._frame_key )
        
        self.show()
        
    
