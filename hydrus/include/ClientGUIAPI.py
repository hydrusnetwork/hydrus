from . import ClientAPI
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIListCtrl
from . import ClientGUIScrolledPanels
from . import ClientGUITags
from . import ClientGUITopLevelWindows
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
import os
import time
import traceback
import wx

class CaptureAPIAccessPermissionsRequestPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._time_started = HydrusData.GetNow()
        
        self._api_permissions = None
        
        self._st = ClientGUICommon.BetterStaticText( self, label = 'waiting for request\u2026' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._repeating_job = HG.client_controller.CallRepeatingWXSafe( self, 0.0, 0.5, self.REPEATINGUpdate )
        
    
    def GetAPIAccessPermissions( self ):
        
        return self._api_permissions
        
    
    def REPEATINGUpdate( self ):
        
        api_permissions_request = ClientAPI.last_api_permissions_request
        
        if api_permissions_request is not None:
            
            self._api_permissions = api_permissions_request
            
            wx.MessageBox( 'Got request!' )
            
            ClientAPI.last_api_permissions_request = None
            self._repeating_job.Cancel()
            
            parent = self.GetParent()
            
            if parent.IsModal(): # event sometimes fires after modal done
                
                parent.DoOK()
                
            
        
    
class EditAPIPermissionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, api_permissions ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_api_permissions = api_permissions
        
        self._access_key = wx.TextCtrl( self, style = wx.TE_READONLY )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._access_key, 66 )
        
        self._access_key.SetMinClientSize( ( width, -1 ) )
        
        self._name = wx.TextCtrl( self )
        
        self._basic_permissions = ClientGUICommon.BetterCheckListBox( self )
        
        for permission in ClientAPI.ALLOWED_PERMISSIONS:
            
            self._basic_permissions.Append( ClientAPI.basic_permission_to_str_lookup[ permission ], permission )
            
        
        search_tag_filter = api_permissions.GetSearchTagFilter()
        
        message = 'The API will only permit searching for tags that pass through this filter.'
        message += os.linesep * 2
        message += 'If you want to allow all tags, just leave it as is, permitting everything. If you want to limit it to just one tag, such as "do waifu2x on this", set up a whitelist with only that tag allowed.'
        
        self._search_tag_filter = ClientGUITags.TagFilterButton( self, message, search_tag_filter )
        
        #
        
        access_key = api_permissions.GetAccessKey()
        
        self._access_key.SetValue( access_key.hex() )
        
        name = api_permissions.GetName()
        
        self._name.SetValue( name )
        
        basic_permissions = api_permissions.GetBasicPermissions()
        
        self._basic_permissions.SetCheckedData( basic_permissions )
        
        #
        
        rows = []
        
        rows.append( ( 'access key: ', self._access_key ) )
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'permissions: ', self._basic_permissions) )
        rows.append( ( 'tag search permissions: ', self._search_tag_filter ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._UpdateEnabled()
        
        self._basic_permissions.Bind( wx.EVT_CHECKLISTBOX, self.EventCheckList )
        
    
    def _UpdateEnabled( self ):
        
        can_search = ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES in self._basic_permissions.GetChecked()
        
        self._search_tag_filter.Enable( can_search )
        
    
    def _GetValue( self ):
        
        name = self._name.GetValue()
        access_key = bytes.fromhex( self._access_key.GetValue() )
        
        basic_permissions = self._basic_permissions.GetChecked()
        search_tag_filter = self._search_tag_filter.GetValue()
        
        api_permissions = ClientAPI.APIPermissions( name = name, access_key = access_key, basic_permissions = basic_permissions, search_tag_filter = search_tag_filter )
        
        return api_permissions
        
    
    def EventCheckList( self, event ):
        
        self._UpdateEnabled()
        
    
    def GetValue( self ):
        
        api_permissions = self._GetValue()
        
        return api_permissions
        
    
