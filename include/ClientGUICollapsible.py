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
        
    
    def ExpandCollapse( self ): self._collapsible_panel.ExpandCollapse()
    
    def GetInfo( self ): return self._options_panel.GetInfo()
    
    def SetInfo( self, info ): self._options_panel.SetInfo( info )
    
class CollapsibleOptionsHentaiFoundry( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelHentaiFoundry
    staticbox_title = 'advanced hentai foundry options'
    
class CollapsibleOptionsImport( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelImport
    staticbox_title = 'advanced import options'
    
class CollapsibleOptionsTags( CollapsibleOptions ):
    
    options_panel_class = ClientGUIOptionsPanels.OptionsPanelTags
    staticbox_title = 'advanced tag options'
    
    def __init__( self, parent, namespaces = None ):
        
        CollapsibleOptions.__init__( self, parent )
        
        if namespaces is None: namespaces = []
        
        self.SetNamespaces( namespaces )
        
    
    def SetNamespaces( self, namespaces ):
        
        self._options_panel.SetNamespaces( namespaces )
        
        if self._collapsible_panel.IsExpanded(): self._collapsible_panel.EventChange( None )
        
    
class CollapsiblePanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._expanded = False
        self._panel = None
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._button = wx.Button( self, label = 'expand' )
        self._button.Bind( wx.EVT_BUTTON, self.EventChange )
        
        line = wx.StaticLine( self, style = wx.LI_HORIZONTAL )
        
        hbox.AddF( self._button, CC.FLAGS_MIXED )
        hbox.AddF( line, CC.FLAGS_EXPAND_DEPTH_ONLY )
        
        self._vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( self._vbox )
        
    
    def _Change( self ):
        
        if self._expanded:
            
            self._button.SetLabel( 'expand' )
            
            self._panel.Hide()
            
            self._expanded = False
            
        else:
            
            self._button.SetLabel( 'collapse' )
            
            self._panel.Show()
            
            self._expanded = True
            
        
        parent_of_container = self.GetParent().GetParent()
        
        parent_of_container.Layout()
        
        if isinstance( parent_of_container, wx.ScrolledWindow ):
            
            # fitinside is like fit, but it does the virtual size!
            parent_of_container.FitInside()
            
        
    
    def ExpandCollapse( self ): self._Change()
    
    def EventChange( self, event ): self._Change()
    
    def IsExpanded( self ): return self._expanded
    
    def SetPanel( self, panel ):
        
        self._panel = panel
        
        self._vbox.AddF( self._panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._panel.Hide()
        
    