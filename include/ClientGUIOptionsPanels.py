import ClientConstants as CC
import ClientGUICommon
import ClientCaches
import ClientData
import ClientDefaults
import ClientGUIDialogs
import ClientImporting
import ClientTags
import collections
import HydrusConstants as HC
import HydrusData
import os
import wx
import wx.lib.masked.timectrl
import HydrusGlobals as HG

class OptionsPanel( wx.Panel ):
    
    def GetOptions( self ): raise NotImplementedError()
    
    def SetOptions( self, options ): raise NotImplementedError()
    
    def GetValue( self ): raise NotImplementedError()
    
    def SetValue( self, info ): raise NotImplementedError()
    
class OptionsPanelMimes( OptionsPanel ):
    
    def __init__( self, parent, selectable_mimes ):
        
        OptionsPanel.__init__( self, parent )
        
        self._mimes_to_checkboxes = {}
        self._mime_groups_to_checkboxes = {}
        self._mime_groups_to_values = {}
        
        mime_groups = [ HC.APPLICATIONS, HC.AUDIO, HC.IMAGES, HC.VIDEO ]
        
        mime_groups_to_mimes = collections.defaultdict( list )
        
        for mime in selectable_mimes:
            
            for mime_group in mime_groups:
                
                if mime in mime_group:
                    
                    mime_groups_to_mimes[ mime_group ].append( mime )
                    
                    break
                    
                
            
        
        gridbox = wx.FlexGridSizer( 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for mime_group in mime_groups:
            
            mimes = mime_groups_to_mimes[ mime_group ]
            
            mg_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime_group ] )
            mg_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeGroupCheckbox )
            
            self._mime_groups_to_checkboxes[ mime_group ] = mg_checkbox
            self._mime_groups_to_values[ mime_group ] = mg_checkbox.GetValue()
            
            gridbox.Add( mg_checkbox, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for mime in mimes:
                
                m_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime ] )
                m_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeCheckbox )
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                vbox.Add( m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            gridbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        self.SetSizer( gridbox )
        
    
    def _UpdateMimeGroupCheckboxes( self ):
        
        for ( mime_group, mg_checkbox ) in self._mime_groups_to_checkboxes.items():
            
            respective_checkbox_values = [ m_checkbox.GetValue() for ( mime, m_checkbox ) in self._mimes_to_checkboxes.items() if mime in mime_group ]
            
            all_true = False not in respective_checkbox_values
            
            mg_checkbox.SetValue( all_true )
            self._mime_groups_to_values[ mime_group ] = all_true
            
        
    
    def EventMimeCheckbox( self, event ):
        
        self._UpdateMimeGroupCheckboxes()
        
    
    def EventMimeGroupCheckbox( self, event ):
        
        # this is a commandevent, which won't give up the checkbox object, so we have to do some jiggery pokery
        
        for ( mime_group, mg_checkbox ) in self._mime_groups_to_checkboxes.items():
            
            expected_value = self._mime_groups_to_values[ mime_group ]
            actual_value = mg_checkbox.GetValue()
            
            if actual_value != expected_value:
                
                for ( mime, m_checkbox ) in self._mimes_to_checkboxes.items():
                    
                    if mime in mime_group:
                        
                        m_checkbox.SetValue( actual_value )
                        
                    
                
                self._mime_groups_to_values[ mime_group ] = actual_value
                
            
        
    
    def GetValue( self ):
        
        mimes = tuple( [ mime for ( mime, checkbox ) in self._mimes_to_checkboxes.items() if checkbox.GetValue() == True ] )
        
        return mimes
        
    
    def SetValue( self, mimes ):
        
        for ( mime, checkbox ) in self._mimes_to_checkboxes.items():
            
            if mime in mimes:
                
                checkbox.SetValue( True )
                
            else:
                
                checkbox.SetValue( False )
                
            
        
        self._UpdateMimeGroupCheckboxes()
        
    
class OptionsPanelTags( OptionsPanel ):
    
    def __init__( self, parent ):
        
        OptionsPanel.__init__( self, parent )
        
        self._service_keys_to_checkbox_info = {}
        self._service_keys_to_explicit_button_info = {}
        self._button_ids_to_service_keys = {}
        
        #
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowHelp )
        help_button.SetToolTip( 'Show help regarding these tag options.' )
        
        self._services_vbox = wx.BoxSizer( wx.VERTICAL )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_button, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._services_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ShowHelp( self ):
        
        message = 'Here you can select which kinds of tags you would like applied to the files that are imported.'
        message += os.linesep * 2
        message += 'If this import context can parse tags (such as a gallery downloader, which may provide \'creator\' or \'series\' tags, amongst others), then the namespaces it provides will be listed here with checkboxes--simply check which ones you are interested in for the tag services you want them to be applied to and it will all occur as the importer processes its files.'
        message += os.linesep * 2
        message += 'You can also set some fixed \'explicit\' tags to be applied to all successful files. For instance, you might want to add something like \'read later\' or \'from my unsorted folder\' or \'pixiv subscription\'.'
        
        wx.MessageBox( message )
        
    
    def EventChecked( self, event ):
        
        wx.PostEvent( self, wx.CommandEvent( commandEventType = wx.wxEVT_COMMAND_MENU_SELECTED, id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'tag_import_options_changed' ) ) )
        
        event.Skip()
        
    
    def EventExplicitTags( self, event ):
        
        button_id = event.GetId()
        
        service_key = self._button_ids_to_service_keys[ button_id ]
        
        ( explicit_tags, explicit_button ) = self._service_keys_to_explicit_button_info[ service_key ]
        
        with ClientGUIDialogs.DialogInputTags( self, service_key, explicit_tags ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                explicit_tags = dlg.GetTags()
                
            
        
        button_label = HydrusData.ConvertIntToPrettyString( len( explicit_tags ) ) + ' explicit tags'
        
        explicit_button.SetLabelText( button_label )
        
        self._service_keys_to_explicit_button_info[ service_key ] = ( explicit_tags, explicit_button )
        
        wx.PostEvent( self, wx.CommandEvent( commandEventType = wx.wxEVT_COMMAND_MENU_SELECTED, id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'tag_import_options_changed' ) ) )
        
    
    def GetOptions( self ):
        
        service_keys_to_namespaces = {}
        
        for ( service_key, checkbox_info ) in self._service_keys_to_checkbox_info.items():
            
            namespaces = [ namespace for ( namespace, checkbox ) in checkbox_info if checkbox.GetValue() == True ]
            
            service_keys_to_namespaces[ service_key ] = namespaces
            
        
        service_keys_to_explicit_tags = { service_key : explicit_tags for ( service_key, ( explicit_tags, explicit_button ) ) in self._service_keys_to_explicit_button_info.items() }
        
        tag_import_options = ClientImporting.TagImportOptions( service_keys_to_namespaces = service_keys_to_namespaces, service_keys_to_explicit_tags = service_keys_to_explicit_tags )
        
        return tag_import_options
        
    
    def SetNamespaces( self, namespaces ):
        
        self._service_keys_to_checkbox_info = {}
        self._service_keys_to_explicit_button_info = {}
        self._button_ids_to_service_keys = {}
        
        self._services_vbox.Clear( True )
        
        services = HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES, randomised = False )
        
        button_id = 1
        
        if len( services ) > 0:
            
            outer_gridbox = wx.FlexGridSizer( 2 )
            
            outer_gridbox.AddGrowableCol( 1, 1 )
            
            for service in services:
                
                service_key = service.GetServiceKey()
                
                self._service_keys_to_checkbox_info[ service_key ] = []
                
                outer_gridbox.Add( ClientGUICommon.BetterStaticText( self, service.GetName() ), CC.FLAGS_VCENTER )
            
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                for namespace in namespaces:
                    
                    label = ClientTags.RenderNamespaceForUser( namespace )
                    
                    namespace_checkbox = wx.CheckBox( self, label = label )
                    
                    namespace_checkbox.Bind( wx.EVT_CHECKBOX, self.EventChecked )
                    
                    self._service_keys_to_checkbox_info[ service_key ].append( ( namespace, namespace_checkbox ) )
                    
                    vbox.Add( namespace_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                explicit_tags = set()
                
                button_label = HydrusData.ConvertIntToPrettyString( len( explicit_tags ) ) + ' explicit tags'
                
                explicit_button = wx.Button( self, label = button_label, id = button_id )
                explicit_button.Bind( wx.EVT_BUTTON, self.EventExplicitTags )
                
                self._service_keys_to_explicit_button_info[ service_key ] = ( explicit_tags, explicit_button )
                self._button_ids_to_service_keys[ button_id ] = service_key
                
                button_id += 1
                
                vbox.Add( explicit_button, CC.FLAGS_VCENTER )
                
                outer_gridbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
            
            self._services_vbox.Add( outer_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
    
    def SetOptions( self, tag_import_options ):
        
        service_keys_to_namespaces = tag_import_options.GetServiceKeysToNamespaces()
        
        for ( service_key, checkbox_info ) in self._service_keys_to_checkbox_info.items():
            
            if service_key in service_keys_to_namespaces:
                
                namespaces_to_set = service_keys_to_namespaces[ service_key ]
                
            else:
                
                namespaces_to_set = set()
                
            
            for ( namespace, checkbox ) in checkbox_info:
                
                if namespace in namespaces_to_set:
                    
                    checkbox.SetValue( True )
                    
                else:
                    
                    checkbox.SetValue( False )
                    
                
            
        
        service_keys_to_explicit_tags = tag_import_options.GetServiceKeysToExplicitTags()
        
        new_service_keys_to_explicit_button_info = {}
        
        for ( service_key, button_info ) in self._service_keys_to_explicit_button_info.items():
            
            if service_key in service_keys_to_explicit_tags:
                
                explicit_tags = service_keys_to_explicit_tags[ service_key ]
                
            else:
                
                explicit_tags = set()
                
            
            ( old_explicit_tags, explicit_button ) = button_info
            
            button_label = HydrusData.ConvertIntToPrettyString( len( explicit_tags ) ) + ' explicit tags'
            
            explicit_button.SetLabelText( button_label )
            
            new_service_keys_to_explicit_button_info[ service_key ] = ( explicit_tags, explicit_button )
            
        
        self._service_keys_to_explicit_button_info = new_service_keys_to_explicit_button_info
        
    
