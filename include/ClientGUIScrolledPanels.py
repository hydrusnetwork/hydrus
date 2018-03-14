import ClientConstants as CC
import ClientGUIShortcuts
import ClientGUITopLevelWindows
import wx
import wx.lib.scrolledpanel

class ResizingScrolledPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent )
        
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventSizeChanged )
        
    
    def _OKParent( self ):
        
        wx.QueueEvent( self.GetEventHandler(), ClientGUITopLevelWindows.OKEvent( -1 ) )
        
    
    def EventSizeChanged( self, event ):
        
        self.SetVirtualSize( self.GetBestVirtualSize() )
        
        event.Skip()
        
    
class EditPanel( ResizingScrolledPanel ):
    
    def CanCancel( self ):
        
        return True
        
    
    def GetValue( self ):
        
        raise NotImplementedError()
        
    
class EditSingleCtrlPanel( EditPanel ):
    
    def __init__( self, parent, ok_on_these_commands = None ):
        
        EditPanel.__init__( self, parent )
        
        self._control = None
        
        if ok_on_these_commands is None:
            
            ok_on_these_commands = set()
            
        
        self._ok_on_these_commands = set( ok_on_these_commands )
        
        #
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self.SetSizer( self._vbox )
        
        self._my_shortcuts_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media' ] )
        
    
    def GetValue( self ):
        
        return self._control.GetValue()
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action in self._ok_on_these_commands:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def SetControl( self, control ):
        
        self._control = control
        
        self._vbox.Add( control, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
class ManagePanel( ResizingScrolledPanel ):
    
    def CanCancel( self ):
        
        return True
        
    
    def CommitChanges( self ):
        
        raise NotImplementedError()
        
    
class ReviewPanel( ResizingScrolledPanel ):
    
    pass
    

class ReviewPanelVetoable( ResizingScrolledPanel ):
    
    def TryToClose( self ):
        
        return
        
    
