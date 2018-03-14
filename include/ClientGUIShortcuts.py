import ClientData
import ClientGUICommon
import HydrusConstants as HC
import HydrusGlobals as HG
import wx

FLASHWIN_OK = False

if HC.PLATFORM_WINDOWS:
    
    try:
        
        import wx.lib.flashwin
        
        FLASHWIN_OK = True
        
    except Exception as e:
        
        pass
        
    
def IShouldCatchCharHook( evt_handler ):
    
    if HC.PLATFORM_WINDOWS and FLASHWIN_OK:
        
        window = wx.FindWindowAtPointer()
        
        if window is not None and isinstance( window, wx.lib.flashwin.FlashWindow ):
            
            return False
            
        
    
    if HG.client_controller.MenuIsOpen():
        
        return False
        
    
    if not ClientGUICommon.WindowOrSameTLPChildHasFocus( evt_handler ):
        
        return False
        
    
    return True
    
class ShortcutsHandler( object ):
    
    def __init__( self, parent, initial_shortcuts_names = None ):
        
        if initial_shortcuts_names is None:
            
            initial_shortcuts_names = []
            
        
        self._parent = parent
        self._shortcuts_names = list( initial_shortcuts_names )
        
        self._parent.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        #self._parent.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse ) # let's not mess with this until we are doing something clever with it
        
    
    def _ProcessShortcut( self, shortcut ):
        
        shortcut_processed = False
        
        command = HG.client_controller.GetCommandFromShortcut( self._shortcuts_names, shortcut )
        
        if command is not None:
            
            command_processed = self._parent.ProcessApplicationCommand( command )
            
            if command_processed:
                
                shortcut_processed = True
                
            
        
        return shortcut_processed
        
    
    def EventCharHook( self, event ):
        
        if IShouldCatchCharHook( self._parent ):
            
            shortcut = ClientData.ConvertKeyEventToShortcut( event )
            
            if shortcut is not None:
                
                shortcut_processed = self._ProcessShortcut( shortcut )
                
                if shortcut_processed:
                    
                    return
                    
                
            
        
        event.Skip()
        
    
    def EventMouse( self, event ):
        
        shortcut = ClientData.ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            shortcut_processed = self._ProcessShortcut( shortcut )
            
            if shortcut_processed:
                
                return
                
            
        
        event.Skip()
        
    
    def AddShortcuts( self, shortcuts_name ):
        
        if shortcuts_name not in self._shortcuts_names:
            
            self._shortcuts_names.append( shortcuts_name )
            
        
    
    def RemoveShortcuts( self, shortcuts_name ):
        
        if shortcuts_name in self._shortcuts_names:
            
            self._shortcuts_names.remove( shortcuts_name )
            
        
