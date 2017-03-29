import wx

class ShortcutsHandler( object ):
    
    def __init__( self, parent, initial_shortcuts = None ):
        
        if initial_shortcuts is None:
            
            initial_shortcuts = []
            
        
        self._parent = parent
        self._all_shortcuts = {}
        
        for shortcuts in initial_shortcuts:
            
            self._all_shortcuts[ shortcuts.GetName() ] = shortcuts
            
        
        self._parent.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        self._parent.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        
    
    def EventCharHook( self, event ):
        
        # determine if the event came from a textctrl or a different tlp than my parent, in which case we want to skip it
        
        # fetch the event details, convert to modifier and key
        # check with all my shortcuts for an action
        
        # if action exists, post it to parent
        # else:
        
        event.Skip()
        
    
    def EventMouse( self, event ):
        
        # fetch the event details, convert to modifier and key
        # check with all my shortcuts for an action
        
        # if action exists, post it to parent
        # else:
        
        event.Skip()
        
    
    def AddShortcuts( self, shortcuts ):
        
        self._all_shortcuts[ shortcuts.GetName() ] = shortcuts
        
    
    def RemoveShortcuts( self, shortcuts_name ):
        
        if shortcuts_name in self._all_shortcuts:
            
            del self._all_shortcuts[ shortcuts_name ]
            
        
