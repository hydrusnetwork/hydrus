from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientDownloading
from . import ClientDuplicates
from . import ClientImporting
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUIFileSeedCache
from . import ClientGUIGallerySeedLog
from . import ClientGUITags
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientImportSubscriptions
from . import ClientMedia
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientParsing
from . import ClientPaths
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusText
import os
import wx

class QuestionCommitInterstitialFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.GetParent().EndModal, wx.ID_YES )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.GetParent().EndModal, wx.ID_NO )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class QuestionFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.GetParent().EndModal, wx.ID_YES )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.GetParent().EndModal, wx.ID_NO )
        self._forget.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', self.GetParent().EndModal, wx.ID_CANCEL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class QuestionYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.GetParent().EndModal, wx.ID_YES )
        self._yes.SetForegroundColour( ( 0, 128, 0 ) )
        self._yes.SetLabelText( yes_label )
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.GetParent().EndModal, wx.ID_NO )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        self._no.SetLabelText( no_label )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._yes, CC.FLAGS_VCENTER )
        hbox.Add( self._no, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.SetWrapWidth( 480 )
        
        vbox.Add( text, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._yes.SetFocus )
        
    
