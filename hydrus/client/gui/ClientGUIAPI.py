from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTime

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class CaptureAPIAccessPermissionsRequestPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._time_started = HydrusTime.GetNow()
        
        self._api_permissions = None
        
        self._st = ClientGUICommon.BetterStaticText( self, label = 'waiting for request' + HC.UNICODE_ELLIPSIS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._repeating_job = CG.client_controller.CallRepeatingQtSafe( self, 0.0, 0.5, 'repeating client api permissions check', self.REPEATINGUpdate )
        
    
    def GetAPIAccessPermissions( self ):
        
        return self._api_permissions
        
    
    def REPEATINGUpdate( self ):
        
        api_permissions_request = ClientAPI.last_api_permissions_request
        
        if api_permissions_request is not None:
            
            self._api_permissions = api_permissions_request
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Got request!' )
            
            ClientAPI.last_api_permissions_request = None
            self._repeating_job.Cancel()
            
            parent = self.parentWidget()
            
            if parent.isModal(): # event sometimes fires after modal done
                
                self._OKParent()
                
            
        
    
class EditAPIPermissionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, api_permissions: ClientAPI.APIPermissions ):
        
        super().__init__( parent )
        
        self._original_api_permissions = api_permissions
        
        self._access_key = QW.QLineEdit()
        
        self._access_key.setReadOnly( True )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._access_key, 66 )
        
        self.setMinimumWidth( width )
        
        self._name = QW.QLineEdit( self )
        
        self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
        
        self._permits_everything = QW.QCheckBox( self._permissions_panel )
        
        self._basic_permissions = ClientGUICommon.BetterCheckBoxList( self._permissions_panel )
        
        for permission in ClientAPI.ALLOWED_PERMISSIONS:
            
            self._basic_permissions.Append( ClientAPI.basic_permission_to_str_lookup[ permission ], permission )
            
        
        self._basic_permissions.sortItems()
        
        self._check_all_permissions_button = ClientGUICommon.BetterButton( self._permissions_panel, 'check all permissions', self._CheckAllPermissions )
        
        search_tag_filter = api_permissions.GetSearchTagFilter()
        
        message = 'The API will only permit searching for tags that pass through this filter.'
        message += '\n' * 2
        message += 'If you want to allow all tags, just leave it as is, permitting everything. If you want to limit it to just one tag, such as "do waifu2x on this", set up a whitelist with only that tag allowed.'
        
        self._search_tag_filter = ClientGUITags.TagFilterButton( self._permissions_panel, message, search_tag_filter, label_prefix = 'permitted tags: ' )
        
        #
        
        access_key = api_permissions.GetAccessKey()
        
        self._access_key.setText( access_key.hex() )
        
        name = api_permissions.GetName()
        
        self._name.setText( name )
        
        self._permits_everything.setChecked( api_permissions.PermitsEverything() )
        
        basic_permissions = api_permissions.GetBasicPermissions()
        
        self._basic_permissions.SetValue( basic_permissions )
        
        #
        
        rows = []
        
        rows.append( ( 'access key: ', self._access_key ) )
        rows.append( ( 'name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._permissions_panel.Add( ClientGUICommon.WrapInText( self._permits_everything, self._permissions_panel, 'permits everything: ' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._permissions_panel.Add( self._basic_permissions, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._permissions_panel.Add( self._check_all_permissions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._permissions_panel.Add( ClientGUICommon.WrapInText( self._search_tag_filter, self._permissions_panel, 'tag search permissions: ' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._permissions_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateEnabled()
        
        self._permits_everything.clicked.connect( self._UpdateEnabled )
        self._basic_permissions.checkBoxListChanged.connect( self._UpdateEnabled )
        
    
    def _CheckAllPermissions( self ):
        
        for i in range( self._basic_permissions.count() ):
            
            self._basic_permissions.Check( i )
            
        
    
    def _UpdateEnabled( self ):
        
        if self._permits_everything.isChecked():
            
            self._basic_permissions.setEnabled( False )
            self._check_all_permissions_button.setEnabled( False )
            self._search_tag_filter.setEnabled( False )
            
        else:
            
            self._basic_permissions.setEnabled( True )
            self._check_all_permissions_button.setEnabled( True )
            self._search_tag_filter.setEnabled( True )
            
            can_search = ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES in self._basic_permissions.GetValue()
            
            self._search_tag_filter.setEnabled( can_search )
            
            self._check_all_permissions_button.setEnabled( False )
            
            for i in range( self._basic_permissions.count() ):
                
                if not self._basic_permissions.IsChecked( i ):
                    
                    self._check_all_permissions_button.setEnabled( True )
                    
                
            
        
    
    def _GetValue( self ):
        
        name = self._name.text()
        access_key = bytes.fromhex( self._access_key.text() )
        
        permits_everything = self._permits_everything.isChecked()
        basic_permissions = self._basic_permissions.GetValue()
        search_tag_filter = self._search_tag_filter.GetValue()
        
        api_permissions = ClientAPI.APIPermissions( name = name, access_key = access_key, permits_everything = permits_everything, basic_permissions = basic_permissions, search_tag_filter = search_tag_filter )
        
        return api_permissions
        
    
    def GetValue( self ):
        
        api_permissions = self._GetValue()
        
        return api_permissions
        
    
