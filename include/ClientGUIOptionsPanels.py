import ClientGUICollapsible
import ClientConstants as CC
import ClientGUICommon
import ClientCaches
import ClientData
import ClientDefaults
import ClientGUIDialogs
import collections
import HydrusConstants as HC
import HydrusData
import wx
import wx.lib.masked.timectrl
import HydrusGlobals

class OptionsPanel( wx.Panel ):
    
    def GetInfo( self ): raise NotImplementedError()
    
    def SetInfo( self, info ): raise NotImplementedError()
    
    def GetOptions( self ): raise NotImplementedError()
    
    def SetOptions( self, options ): raise NotImplementedError()
    
class OptionsPanelHentaiFoundry( OptionsPanel ):
    
    def __init__( self, parent ):
        
        OptionsPanel.__init__( self, parent )
        
        def offensive_choice():
            
            c = wx.Choice( self )
            
            c.Append( 'none', 0 )
            c.Append( 'mild', 1 )
            c.Append( 'moderate', 2 )
            c.Append( 'strong', 3 )
            
            c.SetSelection( 3 )
            
            return c
            
        
        self._rating_nudity = offensive_choice()
        self._rating_violence = offensive_choice()
        self._rating_profanity = offensive_choice()
        self._rating_racism = offensive_choice()
        self._rating_sex = offensive_choice()
        self._rating_spoilers = offensive_choice()
        
        self._rating_yaoi = wx.CheckBox( self )
        self._rating_yuri = wx.CheckBox( self )
        self._rating_teen = wx.CheckBox( self )
        self._rating_guro = wx.CheckBox( self )
        self._rating_furry = wx.CheckBox( self )
        self._rating_beast = wx.CheckBox( self )
        self._rating_male = wx.CheckBox( self )
        self._rating_female = wx.CheckBox( self )
        self._rating_futa = wx.CheckBox( self )
        self._rating_other = wx.CheckBox( self )
        
        self._rating_yaoi.SetValue( True )
        self._rating_yuri.SetValue( True )
        self._rating_teen.SetValue( True )
        self._rating_guro.SetValue( True )
        self._rating_furry.SetValue( True )
        self._rating_beast.SetValue( True )
        self._rating_male.SetValue( True )
        self._rating_female.SetValue( True )
        self._rating_futa.SetValue( True )
        self._rating_other.SetValue( True )
        
        self._filter_order = wx.Choice( self )
        
        self._filter_order.Append( 'newest first', 'date_new' )
        self._filter_order.Append( 'oldest first', 'date_old' )
        self._filter_order.Append( 'most views first', 'views most' ) # no underscore
        self._filter_order.Append( 'highest rating first', 'rating highest' ) # no underscore
        self._filter_order.Append( 'most favourites first', 'faves most' ) # no underscore
        self._filter_order.Append( 'most popular first', 'popularity most' ) # no underscore
        
        self._filter_order.SetSelection( 0 )
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( wx.StaticText( self, label = 'nudity' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_nudity, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'violence' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_violence, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'profanity' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_profanity, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'racism' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_racism, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'sex' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_sex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'spoilers' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_spoilers, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'yaoi' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_yaoi, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'yuri' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_yuri, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'teen' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_teen, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'guro' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_guro, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'furry' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_furry, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'beast' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_beast, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'male' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_male, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'female' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_female, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'futa' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_futa, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'other' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._rating_other, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self, label = 'order' ), CC.FLAGS_VCENTER )
        gridbox.AddF( self._filter_order, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( gridbox )
        
    
    def GetInfo( self ):
        
        info = {}
        
        info[ 'rating_nudity' ] = self._rating_nudity.GetClientData( self._rating_nudity.GetSelection() )
        info[ 'rating_violence' ] = self._rating_violence.GetClientData( self._rating_violence.GetSelection() )
        info[ 'rating_profanity' ] = self._rating_profanity.GetClientData( self._rating_profanity.GetSelection() )
        info[ 'rating_racism' ] = self._rating_racism.GetClientData( self._rating_racism.GetSelection() )
        info[ 'rating_sex' ] = self._rating_sex.GetClientData( self._rating_sex.GetSelection() )
        info[ 'rating_spoilers' ] = self._rating_spoilers.GetClientData( self._rating_spoilers.GetSelection() )
        
        info[ 'rating_yaoi' ] = int( self._rating_yaoi.GetValue() )
        info[ 'rating_yuri' ] = int( self._rating_yuri.GetValue() )
        info[ 'rating_teen' ] = int( self._rating_teen.GetValue() )
        info[ 'rating_guro' ] = int( self._rating_guro.GetValue() )
        info[ 'rating_furry' ] = int( self._rating_furry.GetValue() )
        info[ 'rating_beast' ] = int( self._rating_beast.GetValue() )
        info[ 'rating_male' ] = int( self._rating_male.GetValue() )
        info[ 'rating_female' ] = int( self._rating_female.GetValue() )
        info[ 'rating_futa' ] = int( self._rating_futa.GetValue() )
        info[ 'rating_other' ] = int( self._rating_other.GetValue() )
        
        info[ 'filter_media' ] = 'A'
        info[ 'filter_order' ] = self._filter_order.GetClientData( self._filter_order.GetSelection() )
        info[ 'filter_type' ] = 0
        
        return info
        
    
    def SetInfo( self, info ):
        
        self._rating_nudity.SetSelection( info[ 'rating_nudity' ] )
        self._rating_violence.SetSelection( info[ 'rating_violence' ] )
        self._rating_profanity.SetSelection( info[ 'rating_profanity' ] )
        self._rating_racism.SetSelection( info[ 'rating_racism' ] )
        self._rating_sex.SetSelection( info[ 'rating_sex' ] )
        self._rating_spoilers.SetSelection( info[ 'rating_spoilers' ] )
        
        self._rating_yaoi.SetValue( bool( info[ 'rating_yaoi' ] ) )
        self._rating_yuri.SetValue( bool( info[ 'rating_yuri' ] ) )
        self._rating_teen.SetValue( bool( info[ 'rating_teen' ] ) )
        self._rating_guro.SetValue( bool( info[ 'rating_guro' ] ) )
        self._rating_furry.SetValue( bool( info[ 'rating_furry' ] ) )
        self._rating_beast.SetValue( bool( info[ 'rating_beast' ] ) )
        self._rating_male.SetValue( bool( info[ 'rating_male' ] ) )
        self._rating_female.SetValue( bool( info[ 'rating_female' ] ) )
        self._rating_futa.SetValue( bool( info[ 'rating_futa' ] ) )
        self._rating_other.SetValue( bool( info[ 'rating_other' ] ) )
        
        #info[ 'filter_media' ] = 'A'
        self._filter_order.SetSelection( info[ 'filter_order' ] )
        #info[ 'filter_type' ] = 0
        
    
class OptionsPanelImportFiles( OptionsPanel ):
    
    def __init__( self, parent ):
        
        OptionsPanel.__init__( self, parent )
        
        self._auto_archive = wx.CheckBox( self, label = 'archive all imports' )
        self._auto_archive.Bind( wx.EVT_CHECKBOX, self.EventChanged )
        self._auto_archive.SetToolTipString( 'If this is set, all successful imports will be automatically archived rather than sent to the inbox.' )
        
        self._exclude_deleted = wx.CheckBox( self, label = 'exclude previously deleted files' )
        self._exclude_deleted.Bind( wx.EVT_CHECKBOX, self.EventChanged )
        self._exclude_deleted.SetToolTipString( 'If this is set and an incoming file has already been seen and deleted before by this client, the import will be abandoned. This is useful to make sure you do not keep importing and deleting the same bad files over and over. Files currently in the trash count as deleted.' )
        
        self._min_size = ClientGUICommon.NoneableSpinCtrl( self, 'size', unit = 'KB', multiplier = 1024 )
        self._min_size.SetValue( 5120 )
        self._min_size.Bind( wx.EVT_SPINCTRL, self.EventChanged )
        
        self._min_resolution = ClientGUICommon.NoneableSpinCtrl( self, 'resolution', num_dimensions = 2 )
        self._min_resolution.SetValue( ( 50, 50 ) )
        self._min_resolution.Bind( wx.EVT_SPINCTRL, self.EventChanged )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._auto_archive, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._exclude_deleted, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( wx.StaticText( self, label = 'minimum:' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._min_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._min_resolution, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self.SetOptions( ClientDefaults.GetDefaultImportFileOptions() )
        
    
    def EventChanged( self, event ):
        
        wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'import_file_options_changed' ) ) )
        
        event.Skip()
        
    
    def GetOptions( self ):
        
        automatic_archive = self._auto_archive.GetValue()
        exclude_deleted = self._exclude_deleted.GetValue()
        min_size = self._min_size.GetValue()
        min_resolution = self._min_resolution.GetValue()
        
        return ClientData.ImportFileOptions( automatic_archive = automatic_archive, exclude_deleted = exclude_deleted, min_size = min_size, min_resolution = min_resolution )
        
    
    def SetOptions( self, import_file_options ):
        
        ( automatic_archive, exclude_deleted, min_size, min_resolution ) = import_file_options.ToTuple()
        
        self._auto_archive.SetValue( automatic_archive )
        self._exclude_deleted.SetValue( exclude_deleted )
        self._min_size.SetValue( min_size )
        self._min_resolution.SetValue( min_resolution )
        
    
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
                    
                
            
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for mime_group in mime_groups:
            
            mimes = mime_groups_to_mimes[ mime_group ]
            
            mg_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime_group ] )
            mg_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeGroupCheckbox )
            
            self._mime_groups_to_checkboxes[ mime_group ] = mg_checkbox
            self._mime_groups_to_values[ mime_group ] = mg_checkbox.GetValue()
            
            gridbox.AddF( mg_checkbox, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for mime in mimes:
                
                m_checkbox = wx.CheckBox( self, label = HC.mime_string_lookup[ mime ] )
                m_checkbox.Bind( wx.EVT_CHECKBOX, self.EventMimeCheckbox )
                
                self._mimes_to_checkboxes[ mime ] = m_checkbox
                
                vbox.AddF( m_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            gridbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
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
                
            
        
    
    def GetInfo( self ):
        
        mimes = tuple( [ mime for ( mime, checkbox ) in self._mimes_to_checkboxes.items() if checkbox.GetValue() == True ] )
        
        return mimes
        
    
    def SetInfo( self, mimes ):
        
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
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self.SetSizer( self._vbox )
        
    
    def EventChecked( self, event ):
        
        wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'import_tag_options_changed' ) ) )
        
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
        
        wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'import_tag_options_changed' ) ) )
        
    
    def GetInfo( self ):
        
        result = {}
        
        return result
        
    
    def GetOptions( self ):
        
        service_keys_to_namespaces = {}
        
        for ( service_key, checkbox_info ) in self._service_keys_to_checkbox_info.items():
            
            namespaces = [ namespace for ( namespace, checkbox ) in checkbox_info if checkbox.GetValue() == True ]
            
            service_keys_to_namespaces[ service_key ] = namespaces
            
        
        service_keys_to_explicit_tags = { service_key : explicit_tags for ( service_key, ( explicit_tags, explicit_button ) ) in self._service_keys_to_explicit_button_info.items() }
        
        import_tag_options = ClientData.ImportTagOptions( service_keys_to_namespaces = service_keys_to_namespaces, service_keys_to_explicit_tags = service_keys_to_explicit_tags )
        
        return import_tag_options
        
    
    def SetNamespaces( self, namespaces ):
        
        self._service_keys_to_checkbox_info = {}
        self._service_keys_to_explicit_button_info = {}
        self._button_ids_to_service_keys = {}
        
        self._vbox.Clear( True )
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES, randomised = False )
        
        button_id = 1
        
        if len( services ) > 0:
            
            outer_gridbox = wx.FlexGridSizer( 0, 2 )
            
            outer_gridbox.AddGrowableCol( 1, 1 )
            
            for service in services:
                
                service_key = service.GetServiceKey()
                
                self._service_keys_to_checkbox_info[ service_key ] = []
                
                outer_gridbox.AddF( wx.StaticText( self, label = service.GetName() ), CC.FLAGS_VCENTER )
            
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                for namespace in namespaces:
                    
                    if namespace == '': label = 'no namespace'
                    else: label = namespace
                    
                    namespace_checkbox = wx.CheckBox( self, label = label )
                    
                    namespace_checkbox.Bind( wx.EVT_CHECKBOX, self.EventChecked )
                    
                    self._service_keys_to_checkbox_info[ service_key ].append( ( namespace, namespace_checkbox ) )
                    
                    vbox.AddF( namespace_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                explicit_tags = set()
                
                button_label = HydrusData.ConvertIntToPrettyString( len( explicit_tags ) ) + ' explicit tags'
                
                explicit_button = wx.Button( self, label = button_label, id = button_id )
                explicit_button.Bind( wx.EVT_BUTTON, self.EventExplicitTags )
                
                self._service_keys_to_explicit_button_info[ service_key ] = ( explicit_tags, explicit_button )
                self._button_ids_to_service_keys[ button_id ] = service_key
                
                button_id += 1
                
                vbox.AddF( explicit_button, CC.FLAGS_VCENTER )
                
                outer_gridbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
            
            self._vbox.AddF( outer_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
    
    def SetOptions( self, import_tag_options ):
        
        service_keys_to_namespaces = import_tag_options.GetServiceKeysToNamespaces()
        
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
                    
                
            
        
        service_keys_to_explicit_tags = import_tag_options.GetServiceKeysToExplicitTags()
        
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
        
    
