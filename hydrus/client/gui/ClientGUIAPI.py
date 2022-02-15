import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class CaptureAPIAccessPermissionsRequestPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._time_started = HydrusData.GetNow()
        
        self._api_permissions = None
        
        self._st = ClientGUICommon.BetterStaticText( self, label = 'waiting for request\u2026' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._repeating_job = HG.client_controller.CallRepeatingQtSafe( self, 0.0, 0.5, 'repeating client api permissions check', self.REPEATINGUpdate )
        
    
    def GetAPIAccessPermissions( self ):
        
        return self._api_permissions
        
    
    def REPEATINGUpdate( self ):
        
        api_permissions_request = ClientAPI.last_api_permissions_request
        
        if api_permissions_request is not None:
            
            self._api_permissions = api_permissions_request
            
            QW.QMessageBox.information( self, 'Information', 'Got request!' )
            
            ClientAPI.last_api_permissions_request = None
            self._repeating_job.Cancel()
            
            parent = self.parentWidget()
            
            if parent.isModal(): # event sometimes fires after modal done
                
                parent.DoOK()
                
            
        
    
class EditAPIPermissionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, api_permissions ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_api_permissions = api_permissions
        
        self._access_key = QW.QLineEdit()
        
        self._access_key.setReadOnly( True )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._access_key, 66 )
        
        self.setMinimumWidth( width )
        
        self._name = QW.QLineEdit( self )
        
        self._basic_permissions = ClientGUICommon.BetterCheckBoxList( self )
        
        for permission in ClientAPI.ALLOWED_PERMISSIONS:
            
            self._basic_permissions.Append( ClientAPI.basic_permission_to_str_lookup[ permission ], permission )
            
        
        search_tag_filter = api_permissions.GetSearchTagFilter()
        
        message = 'The API will only permit searching for tags that pass through this filter.'
        message += os.linesep * 2
        message += 'If you want to allow all tags, just leave it as is, permitting everything. If you want to limit it to just one tag, such as "do waifu2x on this", set up a whitelist with only that tag allowed.'
        
        self._search_tag_filter = ClientGUITags.TagFilterButton( self, message, search_tag_filter, label_prefix = 'permitted tags: ' )
        
        #
        
        access_key = api_permissions.GetAccessKey()
        
        self._access_key.setText( access_key.hex() )
        
        name = api_permissions.GetName()
        
        self._name.setText( name )
        
        basic_permissions = api_permissions.GetBasicPermissions()
        
        self._basic_permissions.SetValue( basic_permissions )
        
        #
        
        rows = []
        
        rows.append( ( 'access key: ', self._access_key ) )
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'permissions: ', self._basic_permissions) )
        rows.append( ( 'tag search permissions: ', self._search_tag_filter ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateEnabled()
        
        self._basic_permissions.checkBoxListChanged.connect( self._UpdateEnabled )
        
    
    def _UpdateEnabled( self ):
        
        can_search = ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES in self._basic_permissions.GetValue()
        
        self._search_tag_filter.setEnabled( can_search )
        
    
    def _GetValue( self ):
        
        name = self._name.text()
        access_key = bytes.fromhex( self._access_key.text() )
        
        basic_permissions = self._basic_permissions.GetValue()
        search_tag_filter = self._search_tag_filter.GetValue()
        
        api_permissions = ClientAPI.APIPermissions( name = name, access_key = access_key, basic_permissions = basic_permissions, search_tag_filter = search_tag_filter )
        
        return api_permissions
        
    
    def GetValue( self ):
        
        api_permissions = self._GetValue()
        
        return api_permissions
        
    
