import ClientConstants as CC
import ClientGUICommon
import ClientGUIOptionsPanels
import wx

class CollapsibleOptions( ClientGUICommon.StaticBox ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanel
    staticbox_title = 'not implemented'
    
    def __init__( self, parent ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, self.staticbox_title )
        
        self._collapsible_panel = CollapsiblePanel( self )
        
        self._options_panel = self.options_panel_class( self._collapsible_panel )
        
        self._collapsible_panel.SetPanel( self._options_panel )
        
        self.AddF( self._collapsible_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def ExpandCollapse( self ):
        
        self._collapsible_panel.ExpandCollapse()
        
    
    def GetInfo( self ):
        
        return self._options_panel.GetInfo()
        
    
    def GetOptions( self ):
        
        return self._options_panel.GetOptions()
        
    
    def SetInfo( self, info ):
        
        self._options_panel.SetInfo( info )
        
    
    def SetOptions( self, options ):
        
        self._options_panel.SetOptions( options )
        
    
class CollapsibleOptionsHentaiFoundry( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelHentaiFoundry
    staticbox_title = 'import options - hentai foundry'
    
class CollapsibleOptionsImportFiles( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelImportFiles
    staticbox_title = 'import options - files'
    
class CollapsibleOptionsTags( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelTags
    staticbox_title = 'import options - tags'
    
    def __init__( self, parent, namespaces = None ):
        
        CollapsibleOptions.__init__( self, parent )
        
        if namespaces is None: namespaces = []
        
        self.SetNamespaces( namespaces )
        
    
    def SetNamespaces( self, namespaces ):
        
        self._options_panel.SetNamespaces( namespaces )
        
        if self._collapsible_panel.IsExpanded():
            
            self._collapsible_panel.ExpandCollapse()
            
        
    
class CollapsiblePanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._expanded = False
        self._panel = None
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._button = ClientGUICommon.BetterButton( self, 'expand', self.ExpandCollapse )
        
        line = wx.StaticLine( self, style = wx.LI_HORIZONTAL )
        
        hbox.AddF( self._button, CC.FLAGS_VCENTER )
        hbox.AddF( line, CC.FLAGS_EXPAND_DEPTH_ONLY )
        
        self._vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( self._vbox )
        
    
    def ExpandCollapse( self ):
        
        if self._expanded:
            
            self._button.SetLabelText( 'expand' )
            
            self._panel.Hide()
            
            self._expanded = False
            
        else:
            
            self._button.SetLabelText( 'collapse' )
            
            self._panel.Show()
            
            self._expanded = True
            
        
        parent = self
        
        while not isinstance( parent, wx.ScrolledWindow ) and not isinstance( parent, wx.TopLevelWindow ):
            
            parent = parent.GetParent()
            
        
        if isinstance( parent, wx.ScrolledWindow ):
            
            parent.FitInside()
            
        else:
            
            parent.Layout()
            
        
        event = CC.SizeChangedEvent( -1 )
        
        wx.CallAfter( self.ProcessEvent, event )
        
    
    def IsExpanded( self ):
        
        return self._expanded
        
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        self._vbox.AddF( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._panel.Hide()
        
    
