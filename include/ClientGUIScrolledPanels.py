import ClientConstants as CC
import wx
import wx.lib.scrolledpanel

class ResizingScrolledPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent )
        
        self.Bind( CC.EVT_SIZE_CHANGED, self.EventSizeChanged )
        
    
    def EventSizeChanged( self, event ):
        
        self.SetVirtualSize( self.GetBestVirtualSize() )
        
        event.Skip()
        
    
class EditPanel( ResizingScrolledPanel ):
    
    def GetValue( self ):
        
        raise NotImplementedError()
        
    
class ManagePanel( ResizingScrolledPanel ):
    
    def CommitChanges( self ):
        
        raise NotImplementedError()
        
    
class ReviewPanel( ResizingScrolledPanel ):
    
    pass
    
