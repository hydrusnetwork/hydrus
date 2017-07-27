import ClientCaches
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientImporting
import ClientGUICollapsible
import ClientGUICommon
import ClientGUIControls
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusNetwork
import HydrusSerialisable
import os
import wx

class EditAccountTypePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_type, account_type ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( self._account_type_key, title, permissions, bandwidth_rules ) = account_type.ToTuple()
        
        self._title = wx.TextCtrl( self )
        
        permission_choices = self._GeneratePermissionChoices( service_type )
        
        self._permission_controls = []
        
        self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
        
        gridbox_rows = []
        
        for ( content_type, action_rows ) in permission_choices:
            
            choice_control = ClientGUICommon.BetterChoice( self._permissions_panel )
            
            for ( label, action ) in action_rows:
                
                choice_control.Append( label, ( content_type, action ) )
                
            
            if content_type in permissions:
                
                selection_row = ( content_type, permissions[ content_type ] )
                
            else:
                
                selection_row = ( content_type, None )
                
            
            try:
                
                choice_control.SelectClientData( selection_row )
                
            except:
                
                choice_control.SelectClientData( ( content_type, None ) )
                
            
            self._permission_controls.append( choice_control )
            
            gridbox_label = HC.content_type_string_lookup[ content_type ]
            
            gridbox_rows.append( ( gridbox_label, choice_control ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self._permissions_panel, gridbox_rows )
        
        self._bandwidth_rules_control = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
        
        #
        
        self._title.SetValue( title )
        
        #
        
        t_hbox = ClientGUICommon.WrapInText( self._title, self, 'title: ' )
        
        self._permissions_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( t_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._permissions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._bandwidth_rules_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def _GeneratePermissionChoices( self, service_type ):
        
        possible_permissions = HydrusNetwork.GetPossiblePermissions( service_type )
        
        permission_choices = []
        
        for ( content_type, possible_actions ) in possible_permissions:
            
            choices = []
            
            for action in possible_actions:
                
                choices.append( ( HC.permission_pair_string_lookup[ ( content_type, action ) ], action ) )
                
            
            permission_choices.append( ( content_type, choices ) )
            
        
        return permission_choices
        
    
    def GetValue( self ):
        
        title = self._title.GetValue()
        
        permissions = {}
        
        for permission_control in self._permission_controls:
            
            ( content_type, action ) = permission_control.GetChoice()
            
            if action is not None:
                
                permissions[ content_type ] = action
                
            
        
        bandwidth_rules = self._bandwidth_rules_control.GetValue()
        
        return HydrusNetwork.AccountType.GenerateAccountTypeFromParameters( self._account_type_key, title, permissions, bandwidth_rules )
        
    
class EditBandwidthRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._bandwidth_rules_ctrl = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._bandwidth_rules_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        return self._bandwidth_rules_ctrl.GetValue()
        
    
class EditDuplicateActionOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicate_action, duplicate_action_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._duplicate_action = duplicate_action
        
        #
        
        tag_services_panel = ClientGUICommon.StaticBox( self, 'tag services' )
        
        self._tag_service_actions = ClientGUICommon.SaneListCtrl( tag_services_panel, 120, [ ( 'service name', 120 ), ( 'action', 240 ), ( 'tags merged', -1 ) ], delete_key_callback = self._DeleteTag, activation_callback = self._EditTag )
        
        self._tag_service_actions.SetMinSize( ( 560, 120 ) )
        
        add_tag_button = ClientGUICommon.BetterButton( tag_services_panel, 'add', self._AddTag )
        edit_tag_button = ClientGUICommon.BetterButton( tag_services_panel, 'edit', self._EditTag )
        delete_tag_button = ClientGUICommon.BetterButton( tag_services_panel, 'delete', self._DeleteTag )
        
        #
        
        rating_services_panel = ClientGUICommon.StaticBox( self, 'rating services' )
        
        self._rating_service_actions = ClientGUICommon.SaneListCtrl( rating_services_panel, 120, [ ( 'service name', -1 ), ( 'action', 240 ) ], delete_key_callback = self._DeleteRating, activation_callback = self._EditRating )
        
        self._rating_service_actions.SetMinSize( ( 380, 120 ) )
        
        add_rating_button = ClientGUICommon.BetterButton( rating_services_panel, 'add', self._AddRating )
        edit_rating_button = ClientGUICommon.BetterButton( rating_services_panel, 'edit', self._EditRating )
        delete_rating_button = ClientGUICommon.BetterButton( rating_services_panel, 'delete', self._DeleteRating )
        
        #
        
        self._delete_second_file = wx.CheckBox( self, label = 'delete worse file' )
        self._sync_archive = wx.CheckBox( self, label = 'if one file is archived, archive the other as well' )
        self._delete_both_files = wx.CheckBox( self, label = 'delete both files' )
        
        #
        
        ( tag_service_options, rating_service_options, delete_second_file, sync_archive, delete_both_files ) = duplicate_action_options.ToTuple()
        
        services_manager = HG.client_controller.services_manager
        
        for ( service_key, action, tag_censor ) in tag_service_options:
            
            if services_manager.ServiceExists( service_key ):
                
                sort_tuple = ( service_key, action, tag_censor )
                
                display_tuple = self._GetTagDisplayTuple( sort_tuple )
                
                self._tag_service_actions.Append( display_tuple, sort_tuple )
                
            
        
        for ( service_key, action ) in rating_service_options:
            
            if services_manager.ServiceExists( service_key ):
                
                sort_tuple = ( service_key, action )
                
                display_tuple = self._GetRatingDisplayTuple( sort_tuple )
                
                self._rating_service_actions.Append( display_tuple, sort_tuple )
                
            
        
        self._delete_second_file.SetValue( delete_second_file )
        self._sync_archive.SetValue( sync_archive )
        self._delete_both_files.SetValue( delete_both_files )
        
        #
        
        if self._duplicate_action == HC.DUPLICATE_BETTER:
            
            self._delete_both_files.Hide()
            
        else:
            
            self._delete_second_file.Hide()
            edit_rating_button.Hide() # because there is only one valid action in this case, and no tag censor to edit
            
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( add_tag_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( edit_tag_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( delete_tag_button, CC.FLAGS_VCENTER )
        
        tag_services_panel.AddF( self._tag_service_actions, CC.FLAGS_EXPAND_BOTH_WAYS )
        tag_services_panel.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( add_rating_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( edit_rating_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( delete_rating_button, CC.FLAGS_VCENTER )
        
        rating_services_panel.AddF( self._rating_service_actions, CC.FLAGS_EXPAND_BOTH_WAYS )
        rating_services_panel.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( tag_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( rating_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._delete_second_file, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._sync_archive, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._delete_both_files, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
    
    def _AddRating( self ):
        
        existing_service_keys = set()
        
        for ( service_key, action ) in self._rating_service_actions.GetClientData():
            
            existing_service_keys.add( service_key )
            
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( [ HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ] ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in existing_service_keys:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            wx.MessageBox( 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            with ClientGUIDialogs.DialogSelectFromList( self, 'select service', choice_tuples ) as dlg_1:
                
                if dlg_1.ShowModal() == wx.ID_OK:
                    
                    service_key = dlg_1.GetChoice()
                    
                    if self._duplicate_action == HC.DUPLICATE_BETTER:
                        
                        service = services_manager.GetService( service_key )
                        
                        if service.GetServiceType() == HC.TAG_REPOSITORY:
                            
                            possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                            
                        else:
                            
                            possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                            
                        
                        choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                        
                        with ClientGUIDialogs.DialogSelectFromList( self, 'select action', choice_tuples ) as dlg_2:
                            
                            if dlg_2.ShowModal() == wx.ID_OK:
                                
                                action = dlg_2.GetChoice()
                                
                            else:
                                
                                return
                                
                            
                        
                    else:
                        
                        action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                        
                    
                    sort_tuple = ( service_key, action )
                    
                    display_tuple = self._GetRatingDisplayTuple( sort_tuple )
                    
                    self._rating_service_actions.Append( display_tuple, sort_tuple )
                    
                
            
        
    
    def _AddTag( self ):
        
        existing_service_keys = set()
        
        for ( service_key, action, tag_censor ) in self._tag_service_actions.GetClientData():
            
            existing_service_keys.add( service_key )
            
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( [ HC.LOCAL_TAG, HC.TAG_REPOSITORY ] ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in existing_service_keys:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            wx.MessageBox( 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            with ClientGUIDialogs.DialogSelectFromList( self, 'select service', choice_tuples ) as dlg_1:
                
                if dlg_1.ShowModal() == wx.ID_OK:
                    
                    service_key = dlg_1.GetChoice()
                    
                    if self._duplicate_action == HC.DUPLICATE_BETTER:
                        
                        service = services_manager.GetService( service_key )
                        
                        if service.GetServiceType() == HC.TAG_REPOSITORY:
                            
                            possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                            
                        else:
                            
                            possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                            
                        
                        choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                        
                        with ClientGUIDialogs.DialogSelectFromList( self, 'select action', choice_tuples ) as dlg_2:
                            
                            if dlg_2.ShowModal() == wx.ID_OK:
                                
                                action = dlg_2.GetChoice()
                                
                            else:
                                
                                return
                                
                            
                        
                    else:
                        
                        action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                        
                    
                    tag_censor = ClientData.TagCensor()
                    
                    with ClientGUITopLevelWindows.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                        
                        panel = EditTagCensorPanel( dlg_3, tag_censor )
                        
                        dlg_3.SetPanel( panel )
                        
                        if dlg_3.ShowModal() == wx.ID_OK:
                            
                            tag_censor = panel.GetValue()
                            
                            sort_tuple = ( service_key, action, tag_censor )
                            
                            display_tuple = self._GetTagDisplayTuple( sort_tuple )
                            
                            self._tag_service_actions.Append( display_tuple, sort_tuple )
                            
                        
                    
                
            
        
    
    def _DeleteRating( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._rating_service_actions.RemoveAllSelected()
                
            
        
    
    def _DeleteTag( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._tag_service_actions.RemoveAllSelected()
                
            
        
    
    def _EditRating( self ):
        
        all_selected = self._rating_service_actions.GetAllSelected()
        
        for index in all_selected:
            
            ( service_key, action ) = self._rating_service_actions.GetClientData( index )
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                with ClientGUIDialogs.DialogSelectFromList( self, 'select action', choice_tuples ) as dlg_2:
                    
                    if dlg_2.ShowModal() == wx.ID_OK:
                        
                        action = dlg_2.GetChoice()
                        
                    else:
                        
                        break
                        
                    
                
            else: # This shouldn't get fired because the edit button is hidden, but w/e
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            sort_tuple = ( service_key, action )
            
            display_tuple = self._GetRatingDisplayTuple( sort_tuple )
            
            self._rating_service_actions.UpdateRow( index, display_tuple, sort_tuple )
            
        
    
    def _EditTag( self ):
        
        all_selected = self._tag_service_actions.GetAllSelected()
        
        for index in all_selected:
            
            ( service_key, action, tag_censor ) = self._tag_service_actions.GetClientData( index )
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                with ClientGUIDialogs.DialogSelectFromList( self, 'select action', choice_tuples ) as dlg_2:
                    
                    if dlg_2.ShowModal() == wx.ID_OK:
                        
                        action = dlg_2.GetChoice()
                        
                    else:
                        
                        break
                        
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                panel = EditTagCensorPanel( dlg_3, tag_censor )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.ShowModal() == wx.ID_OK:
                    
                    tag_censor = panel.GetValue()
                    
                    sort_tuple = ( service_key, action, tag_censor )
                    
                    display_tuple = self._GetTagDisplayTuple( sort_tuple )
                    
                    self._tag_service_actions.UpdateRow( index, display_tuple, sort_tuple )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _GetRatingDisplayTuple( self, sort_tuple ):
        
        ( service_key, action ) = sort_tuple
        
        services_manager = HG.client_controller.services_manager
        
        service = services_manager.GetService( service_key )
        
        name = service.GetName()
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        
        return ( name, pretty_action )
        
    
    def _GetTagDisplayTuple( self, sort_tuple ):
        
        ( service_key, action, tag_censor ) = sort_tuple
        
        services_manager = HG.client_controller.services_manager
        
        service = services_manager.GetService( service_key )
        
        name = service.GetName()
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        
        pretty_tag_censor = tag_censor.ToPermittedString()
        
        return ( name, pretty_action, pretty_tag_censor )
        
    
    def GetValue( self ):
        
        tag_service_actions = self._tag_service_actions.GetClientData()
        rating_service_actions = self._rating_service_actions.GetClientData()
        delete_second_file = self._delete_second_file.GetValue()
        sync_archive = self._sync_archive.GetValue()
        delete_both_files = self._delete_both_files.GetValue()
        
        duplicate_action_options = ClientData.DuplicateActionOptions( tag_service_actions, rating_service_actions, delete_second_file, sync_archive, delete_both_files )
        
        return duplicate_action_options
        
    
class EditFrameLocationPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        self._remember_size = wx.CheckBox( self, label = 'remember size' )
        self._remember_position = wx.CheckBox( self, label = 'remember position' )
        
        self._last_size = ClientGUICommon.NoneableSpinCtrl( self, 'last size', none_phrase = 'none set', min = 100, max = 1000000, unit = None, num_dimensions = 2 )
        self._last_position = ClientGUICommon.NoneableSpinCtrl( self, 'last position', none_phrase = 'none set', min = -1000000, max = 1000000, unit = None, num_dimensions = 2 )
        
        self._default_gravity_x = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_x.Append( 'by default, expand to width of parent', 1 )
        self._default_gravity_x.Append( 'by default, expand width as much as needed', -1 )
        
        self._default_gravity_y = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_y.Append( 'by default, expand to height of parent', 1 )
        self._default_gravity_y.Append( 'by default, expand height as much as needed', -1 )
        
        self._default_position = ClientGUICommon.BetterChoice( self )
        
        self._default_position.Append( 'by default, position off the top-left corner of parent', 'topleft' )
        self._default_position.Append( 'by default, position centered on the parent', 'center' )
        
        self._maximised = wx.CheckBox( self, label = 'start maximised' )
        self._fullscreen = wx.CheckBox( self, label = 'start fullscreen' )
        
        #
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        self._remember_size.SetValue( remember_size )
        self._remember_position.SetValue( remember_position )
        
        self._last_size.SetValue( last_size )
        self._last_position.SetValue( last_position )
        
        ( x, y ) = default_gravity
        
        self._default_gravity_x.SelectClientData( x )
        self._default_gravity_y.SelectClientData( y )
        
        self._default_position.SelectClientData( default_position )
        
        self._maximised.SetValue( maximised )
        self._fullscreen.SetValue( fullscreen )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = 'Setting frame location info for ' + name + '.'
        
        vbox.AddF( ClientGUICommon.BetterStaticText( self, text ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._remember_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._remember_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._last_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._last_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._default_gravity_x, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._default_gravity_y, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._default_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._maximised, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._fullscreen, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        remember_size = self._remember_size.GetValue()
        remember_position = self._remember_position.GetValue()
        
        last_size = self._last_size.GetValue()
        last_position = self._last_position.GetValue()
        
        x = self._default_gravity_x.GetChoice()
        y = self._default_gravity_y.GetChoice()
        
        default_gravity = [ x, y ]
        
        default_position = self._default_position.GetChoice()
        
        maximised = self._maximised.GetValue()
        fullscreen = self._fullscreen.GetValue()
        
        return ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
        
    
class EditMediaViewOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        ( self._mime, media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._original_info
        
        possible_actions = CC.media_viewer_capabilities[ self._mime ]
        
        self._media_show_action = ClientGUICommon.BetterChoice( self )
        self._preview_show_action = ClientGUICommon.BetterChoice( self )
        
        for action in possible_actions:
            
            self._media_show_action.Append( CC.media_viewer_action_string_lookup[ action ], action )
            
            if action != CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                self._preview_show_action.Append( CC.media_viewer_action_string_lookup[ action ], action )
                
            
        
        self._media_show_action.Bind( wx.EVT_CHOICE, self.EventActionChange )
        self._preview_show_action.Bind( wx.EVT_CHOICE, self.EventActionChange )
        
        self._media_scale_up = ClientGUICommon.BetterChoice( self )
        self._media_scale_down = ClientGUICommon.BetterChoice( self )
        self._preview_scale_up = ClientGUICommon.BetterChoice( self )
        self._preview_scale_down = ClientGUICommon.BetterChoice( self )
        
        for scale_action in ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS ):
            
            text = CC.media_viewer_scale_string_lookup[ scale_action ]
            
            self._media_scale_up.Append( text, scale_action )
            self._preview_scale_up.Append( text, scale_action )
            
            if scale_action != CC.MEDIA_VIEWER_SCALE_100:
                
                self._media_scale_down.Append( text, scale_action )
                self._preview_scale_down.Append( text, scale_action )
                
            
        
        self._exact_zooms_only = wx.CheckBox( self, label = 'only permit half and double zooms' )
        self._exact_zooms_only.SetToolTipString( 'This limits zooms to 25%, 50%, 100%, 200%, 400%, and so on. It makes for fast resize and is useful for files that often have flat colours and hard edges, which often scale badly otherwise. The \'canvas fit\' zoom will still be inserted.' )
        
        self._scale_up_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_CUBIC, CC.ZOOM_LANCZOS4 ):
            
            self._scale_up_quality.Append( CC.zoom_string_lookup[ zoom ], zoom )
            
        
        self._scale_down_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_AREA ):
            
            self._scale_down_quality.Append( CC.zoom_string_lookup[ zoom ], zoom )
            
        
        #
        
        self._media_show_action.SelectClientData( media_show_action )
        self._preview_show_action.SelectClientData( preview_show_action )
        
        self._media_scale_up.SelectClientData( media_scale_up )
        self._media_scale_down.SelectClientData( media_scale_down )
        self._preview_scale_up.SelectClientData( preview_scale_up )
        self._preview_scale_down.SelectClientData( preview_scale_down )
        
        self._exact_zooms_only.SetValue( exact_zooms_only )
        
        self._scale_up_quality.SelectClientData( scale_up_quality )
        self._scale_down_quality.SelectClientData( scale_down_quality )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = 'Setting media view options for ' + HC.mime_string_lookup[ self._mime ] + '.'
        
        vbox.AddF( ClientGUICommon.BetterStaticText( self, text ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( ClientGUICommon.WrapInText( self._media_show_action, self, 'media viewer show action:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( ClientGUICommon.WrapInText( self._preview_show_action, self, 'preview show action:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if possible_actions == CC.no_support:
            
            self._media_scale_up.Hide()
            self._media_scale_down.Hide()
            self._preview_scale_up.Hide()
            self._preview_scale_down.Hide()
            
            self._exact_zooms_only.Hide()
            
            self._scale_up_quality.Hide()
            self._scale_down_quality.Hide()
            
        else:
            
            rows = []
            
            rows.append( ( 'if the media is smaller than the media viewer canvas: ', self._media_scale_up ) )
            rows.append( ( 'if the media is larger than the media viewer canvas: ', self._media_scale_down ) )
            rows.append( ( 'if the media is smaller than the preview canvas: ', self._preview_scale_up) )
            rows.append( ( 'if the media is larger than the preview canvas: ', self._preview_scale_down ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox.AddF( self._exact_zooms_only, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( ClientGUICommon.BetterStaticText( self, 'Nearest neighbour is fast and ugly, 8x8 lanczos and area resampling are slower but beautiful.' ), CC.FLAGS_VCENTER )
            
            vbox.AddF( ClientGUICommon.WrapInText( self._scale_up_quality, self, '>100% (interpolation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( ClientGUICommon.WrapInText( self._scale_down_quality, self, '<100% (decimation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        if self._mime == HC.APPLICATION_FLASH:
            
            self._scale_up_quality.Disable()
            self._scale_down_quality.Disable()
            
        
        self.SetSizer( vbox )
        
    
    def EventActionChange( self, event ):
        
        if self._media_show_action.GetChoice() in CC.no_support and self._preview_show_action.GetChoice() in CC.no_support:
            
            self._media_scale_up.Disable()
            self._media_scale_down.Disable()
            self._preview_scale_up.Disable()
            self._preview_scale_down.Disable()
            
            self._exact_zooms_only.Disable()
            
            self._scale_up_quality.Disable()
            self._scale_down_quality.Disable()
            
        else:
            
            self._media_scale_up.Enable()
            self._media_scale_down.Enable()
            self._preview_scale_up.Enable()
            self._preview_scale_down.Enable()
            
            self._exact_zooms_only.Enable()
            
            self._scale_up_quality.Enable()
            self._scale_down_quality.Enable()
            
        
        if self._mime == HC.APPLICATION_FLASH:
            
            self._scale_up_quality.Disable()
            self._scale_down_quality.Disable()
            
        
    
    def GetValue( self ):
        
        media_show_action = self._media_show_action.GetChoice()
        preview_show_action = self._preview_show_action.GetChoice()
        
        media_scale_up = self._media_scale_up.GetChoice()
        media_scale_down = self._media_scale_down.GetChoice()
        preview_scale_up = self._preview_scale_up.GetChoice()
        preview_scale_down = self._preview_scale_down.GetChoice()
        
        exact_zooms_only = self._exact_zooms_only.GetValue()
        
        scale_up_quality = self._scale_up_quality.GetChoice()
        scale_down_quality = self._scale_down_quality.GetChoice()
        
        return ( self._mime, media_show_action, preview_show_action, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) )
        
    
class EditNoneableIntegerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, value, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._value = ClientGUICommon.NoneableSpinCtrl( self, message = message, none_phrase = none_phrase, min = min, max = max, unit = unit, multiplier = multiplier, num_dimensions = num_dimensions )
        
        self._value.SetValue( value )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        return self._value.GetValue()
        
    
class EditServersideService( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, serverside_service ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        duplicate_serverside_service = serverside_service.Duplicate()
        
        ( self._service_key, self._service_type, name, port, self._dictionary ) = duplicate_serverside_service.ToTuple()
        
        self._service_panel = self._ServicePanel( self, name, port, self._dictionary )
        
        self._panels = []
        
        if self._service_type in HC.RESTRICTED_SERVICES:
            
            self._panels.append( self._ServiceRestrictedPanel( self, self._dictionary ) )
            
            if self._service_type == HC.FILE_REPOSITORY:
                
                self._panels.append( self._ServiceFileRepositoryPanel( self, self._dictionary ) )
                
            
            if self._service_type == HC.SERVER_ADMIN:
                
                self._panels.append( self._ServiceServerAdminPanel( self, self._dictionary ) )
                
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for panel in self._panels:
            
            vbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        ( name, port, dictionary_part ) = self._service_panel.GetValue()
        
        dictionary = self._dictionary.Duplicate()
        
        dictionary.update( dictionary_part )
        
        for panel in self._panels:
            
            dictionary_part = panel.GetValue()
            
            dictionary.update( dictionary_part )
            
        
        return HydrusNetwork.GenerateService( self._service_key, self._service_type, name, port, dictionary )
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, name, port, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'basic information' )
            
            self._name = wx.TextCtrl( self )
            self._port = wx.SpinCtrl( self, min = 1, max = 65535 )
            self._upnp_port = ClientGUICommon.NoneableSpinCtrl( self, 'external upnp port', none_phrase = 'do not forward port', min = 1, max = 65535 )
            
            self._bandwidth_tracker_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._name.SetValue( name )
            self._port.SetValue( port )
            
            upnp_port = dictionary[ 'upnp_port' ]
            
            self._upnp_port.SetValue( upnp_port )
            
            bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
            
            bandwidth_text = bandwidth_tracker.GetCurrentMonthSummary()
            
            self._bandwidth_tracker_st.SetLabelText( bandwidth_text )
            
            #
            
            rows = []
            
            rows.append( ( 'name: ', self._name ) )
            rows.append( ( 'port: ', self._port ) )
            rows.append( ( 'upnp port: ', self._upnp_port ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self.AddF( self._bandwidth_tracker_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            name = self._name.GetValue()
            port = self._port.GetValue()
            
            upnp_port = self._upnp_port.GetValue()
            
            dictionary_part[ 'upnp_port' ] = upnp_port
            
            return ( name, port, dictionary_part )
            
        
    
    class _ServiceRestrictedPanel( wx.Panel ):
        
        def __init__( self, parent, dictionary ):
            
            wx.Panel.__init__( self, parent )
            
            bandwidth_rules = dictionary[ 'bandwidth_rules' ]
            
            self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._bandwidth_rules, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            dictionary_part[ 'bandwidth_rules' ] = self._bandwidth_rules.GetValue()
            
            return dictionary_part
            
        
    
    class _ServiceFileRepositoryPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'file repository' )
            
            self._log_uploader_ips = wx.CheckBox( self )
            self._max_storage = ClientGUICommon.NoneableSpinCtrl( self, unit = 'MB', multiplier = 1024 * 1024 )
            
            #
            
            log_uploader_ips = dictionary[ 'log_uploader_ips' ]
            max_storage = dictionary[ 'max_storage' ]
            
            self._log_uploader_ips.SetValue( log_uploader_ips )
            self._max_storage.SetValue( max_storage )
            
            #
            
            rows = []
            
            rows.append( ( 'log file uploader IP addresses?: ', self._log_uploader_ips ) )
            rows.append( ( 'max file storage: ', self._max_storage ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            log_uploader_ips = self._log_uploader_ips.GetValue()
            max_storage = self._max_storage.GetValue()
            
            dictionary_part[ 'log_uploader_ips' ] = log_uploader_ips
            dictionary_part[ 'max_storage' ] = max_storage
            
            return dictionary_part
            
        
    
    class _ServiceServerAdminPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'server-wide bandwidth' )
            
            self._bandwidth_tracker_st = ClientGUICommon.BetterStaticText( self )
            
            bandwidth_rules = dictionary[ 'server_bandwidth_rules' ]
            
            self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
            
            #
            
            bandwidth_tracker = dictionary[ 'server_bandwidth_tracker' ]
            
            bandwidth_text = bandwidth_tracker.GetCurrentMonthSummary()
            
            self._bandwidth_tracker_st.SetLabelText( bandwidth_text )
            
            #
            
            self.AddF( self._bandwidth_tracker_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._bandwidth_rules, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            bandwidth_rules = self._bandwidth_rules.GetValue()
            
            dictionary_part[ 'server_bandwidth_rules' ] = bandwidth_rules
            
            return dictionary_part
            
        
    
class EditChooseMultiple( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, choice_tuples ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._checkboxes = wx.CheckListBox( self )
        
        self._checkboxes.SetMinSize( ( 320, 420 ) )
        
        for ( i, ( label, data, selected ) ) in enumerate( choice_tuples ):
            
            self._checkboxes.Append( label, data )
            
            if selected:
                
                self._checkboxes.Check( i )
                
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        datas = []
        
        for index in self._checkboxes.GetChecked():
            
            datas.append( self._checkboxes.GetClientData( index ) )
            
        
        return datas
        
    
class EditSubscriptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, subscription ):
        
        subscription = subscription.Duplicate()
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_subscription = subscription
        
        #
        
        self._name = wx.TextCtrl( self )
        
        #
        
        self._info_panel = ClientGUICommon.StaticBox( self, 'info' )
        
        self._last_checked_st = wx.StaticText( self._info_panel )
        self._next_check_st = wx.StaticText( self._info_panel )
        self._seed_info_st = wx.StaticText( self._info_panel )
        
        #
        
        self._query_panel = ClientGUICommon.StaticBox( self, 'site and query' )
        
        self._site_type = ClientGUICommon.BetterChoice( self._query_panel )
        
        site_types = []
        site_types.append( HC.SITE_TYPE_BOORU )
        site_types.append( HC.SITE_TYPE_DEVIANT_ART )
        site_types.append( HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST )
        site_types.append( HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS )
        site_types.append( HC.SITE_TYPE_NEWGROUNDS )
        site_types.append( HC.SITE_TYPE_PIXIV_ARTIST_ID )
        site_types.append( HC.SITE_TYPE_PIXIV_TAG )
        site_types.append( HC.SITE_TYPE_TUMBLR )
        
        for site_type in site_types:
            
            self._site_type.Append( HC.site_type_string_lookup[ site_type ], site_type )
            
        
        self._site_type.Bind( wx.EVT_CHOICE, self.EventSiteChanged )
        
        self._query = wx.TextCtrl( self._query_panel )
        
        self._booru_selector = wx.ListBox( self._query_panel )
        self._booru_selector.Bind( wx.EVT_LISTBOX, self.EventBooruSelected )
        
        self._period = ClientGUICommon.TimeDeltaButton( self._query_panel, min = 3600 * 4, days = True, hours = True )
        self._period.Bind( ClientGUICommon.EVT_TIME_DELTA, self.EventPeriodChanged )
        
        #
        
        self._options_panel = ClientGUICommon.StaticBox( self, 'options' )
        
        menu_items = []
        
        invert_call = self._InvertGetTagsIfURLKnownAndFileRedundant
        value_call = self._GetTagsIfURLKnownAndFileRedundant
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( invert_call, value_call )
        
        menu_items.append( ( 'check', 'get tags even if url is known and file is already in db (this downloader)', 'If this is selected, the client will fetch the tags from a file\'s page even if it has the file and already previously downloaded it from that location.', check_manager ) )
        
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'get_tags_if_url_known_and_file_redundant' )
        
        menu_items.append( ( 'check', 'get tags even if url is known and file is already in db (default)', 'Set the default for this value.', check_manager ) )
        
        cog_button = ClientGUICommon.MenuBitmapButton( self._options_panel, CC.GlobalBMPs.cog, menu_items )
        
        self._initial_file_limit = ClientGUICommon.NoneableSpinCtrl( self._options_panel, '', none_phrase = 'get everything', min = 1, max = 1000000 )
        self._initial_file_limit.SetToolTipString( 'If set, the first sync will add no more than this many files. Otherwise, it will get everything the gallery has.' )
        
        self._periodic_file_limit = ClientGUICommon.NoneableSpinCtrl( self._options_panel, '', none_phrase = 'get everything', min = 1, max = 1000000 )
        self._periodic_file_limit.SetToolTipString( 'If set, normal syncs will add no more than this many files. Otherwise, they will get everything up until they find a file they have seen before.' )
        
        #
        
        self._control_panel = ClientGUICommon.StaticBox( self, 'control' )
        
        self._paused = wx.CheckBox( self._control_panel )
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._control_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed url cache status' )
        
        self._retry_failed = ClientGUICommon.BetterButton( self._control_panel, 'retry failed', self.RetryFailed )
        
        self._check_now_button = ClientGUICommon.BetterButton( self._control_panel, 'force check on dialog ok', self.CheckNow )
        
        self._reset_cache_button = ClientGUICommon.BetterButton( self._control_panel, 'reset url cache', self.ResetCache )
        
        #
        
        self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self )
        
        #
        
        ( name, gallery_identifier, gallery_stream_identifiers, query, period, self._get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options, self._last_checked, self._last_error, self._check_now, self._seed_cache ) = subscription.ToTuple()
        
        self._name.SetValue( name )
        
        site_type = gallery_identifier.GetSiteType()
        
        self._site_type.SelectClientData( site_type )
        
        self._PresentForSiteType()
        
        if site_type == HC.SITE_TYPE_BOORU:
            
            booru_name = gallery_identifier.GetAdditionalInfo()
            
            index = self._booru_selector.FindString( booru_name )
            
            if index != wx.NOT_FOUND:
                
                self._booru_selector.Select( index )
                
            
        
        # set gallery_stream_identifiers selection here--some kind of list of checkboxes or whatever
        
        self._query.SetValue( query )
        
        self._period.SetValue( period )
        
        self._initial_file_limit.SetValue( initial_file_limit )
        self._periodic_file_limit.SetValue( periodic_file_limit )
        
        self._paused.SetValue( paused )
        
        self._import_file_options.SetOptions( import_file_options )
        
        self._import_tag_options.SetOptions( import_tag_options )
        
        if self._last_checked == 0:
            
            self._reset_cache_button.Disable()
            
        
        if self._check_now:
            
            self._check_now_button.Disable()
            
        
        self._UpdateCommandButtons()
        self._UpdateLastNextCheck()
        self._UpdateSeedInfo()
        
        #
        
        self._info_panel.AddF( self._last_checked_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._info_panel.AddF( self._next_check_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._info_panel.AddF( self._seed_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'search text: ', self._query ) )
        rows.append( ( 'check for new files every: ', self._period ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._query_panel, rows )
        
        self._query_panel.AddF( self._site_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._query_panel.AddF( self._booru_selector, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._query_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'on first check, get at most this many files: ', self._initial_file_limit ) )
        rows.append( ( 'on normal checks, get at most this many newer files: ', self._periodic_file_limit ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._options_panel, rows )
        
        self._options_panel.AddF( cog_button, CC.FLAGS_LONE_BUTTON )
        self._options_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._control_panel.AddF( self._seed_cache_button, CC.FLAGS_LONE_BUTTON )
        
        rows = []
        
        rows.append( ( 'currently paused: ', self._paused ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._control_panel, rows )
        
        self._control_panel.AddF( gridbox, CC.FLAGS_LONE_BUTTON )
        self._control_panel.AddF( self._retry_failed, CC.FLAGS_LONE_BUTTON )
        self._control_panel.AddF( self._check_now_button, CC.FLAGS_LONE_BUTTON )
        self._control_panel.AddF( self._reset_cache_button, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( ClientGUICommon.WrapInText( self._name, self, 'name: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._query_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._control_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def _ConfigureImportTagOptions( self ):
        
        gallery_identifier = self._GetGalleryIdentifier()
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
        
        new_options = HG.client_controller.GetNewOptions()
        
        import_tag_options = new_options.GetDefaultImportTagOptions( gallery_identifier )
        
        if gallery_identifier == self._original_subscription.GetGalleryIdentifier():
            
            search_value = self._original_subscription.GetQuery()
            import_tag_options = self._original_subscription.GetImportTagOptions()
            
        
        self._query.SetValue( search_value )
        self._import_tag_options.SetNamespaces( namespaces )
        self._import_tag_options.SetOptions( import_tag_options )
        
    
    def _GetGalleryIdentifier( self ):
        
        site_type = self._site_type.GetChoice()
        
        if site_type == HC.SITE_TYPE_BOORU:
            
            booru_name = self._booru_selector.GetStringSelection()
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( site_type, additional_info = booru_name )
            
        else:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( site_type )
            
        
        return gallery_identifier
        
    
    def _GetTagsIfURLKnownAndFileRedundant( self ):
        
        return self._get_tags_if_url_known_and_file_redundant
        
    
    def _InvertGetTagsIfURLKnownAndFileRedundant( self ):
        
        self._get_tags_if_url_known_and_file_redundant = not self._get_tags_if_url_known_and_file_redundant
        
    
    def _UpdateCommandButtons( self ):
        
        on_initial_sync = self._last_checked == 0
        no_failures = self._seed_cache.GetSeedCount( CC.STATUS_FAILED ) == 0
        
        can_check = not ( self._check_now or on_initial_sync )
        
        if no_failures:
            
            self._retry_failed.Disable()
            
        else:
            
            self._retry_failed.Enable()
            
        
        if can_check:
            
            self._check_now_button.Enable()
            
        else:
            
            self._check_now_button.Disable()
            
        
        if on_initial_sync:
            
            self._reset_cache_button.Disable()
            
        else:
            
            self._reset_cache_button.Enable()
            
        
    
    def _UpdateLastNextCheck( self ):
        
        if self._last_checked == 0:
            
            last_checked_text = 'initial check has not yet occured'
            
        else:
            
            last_checked_text = 'last checked ' + HydrusData.ConvertTimestampToPrettySync( self._last_checked )
            
        
        self._last_checked_st.SetLabelText( last_checked_text )
        
        periodic_next_check_time = self._last_checked + self._period.GetValue()
        error_next_check_time = self._last_error + HC.UPDATE_DURATION
        
        if self._check_now:
            
            next_check_text = 'next check as soon as manage subscriptions dialog is closed'
            
        elif error_next_check_time > periodic_next_check_time:
            
            next_check_text = 'due to an error, next check ' + HydrusData.ConvertTimestampToPrettyPending( error_next_check_time )
            
        else:
            
            next_check_text = 'next check ' + HydrusData.ConvertTimestampToPrettyPending( periodic_next_check_time )
            
        
        self._next_check_st.SetLabelText( next_check_text )
        
    
    def _UpdateSeedInfo( self ):
        
        seed_cache_text = HydrusData.ConvertIntToPrettyString( self._seed_cache.GetSeedCount() ) + ' urls in cache'
        
        num_failed = self._seed_cache.GetSeedCount( CC.STATUS_FAILED )
        
        if num_failed > 0:
            
            seed_cache_text += ', ' + HydrusData.ConvertIntToPrettyString( num_failed ) + ' failed'
            
        
        self._seed_info_st.SetLabelText( seed_cache_text )
        
    
    def _PresentForSiteType( self ):
        
        site_type = self._site_type.GetChoice()
        
        if site_type == HC.SITE_TYPE_BOORU:
            
            if self._booru_selector.GetCount() == 0:
                
                boorus = HG.client_controller.Read( 'remote_boorus' )
                
                for ( name, booru ) in boorus.items(): self._booru_selector.Append( name, booru )
                
                self._booru_selector.Select( 0 )
                
            
            self._booru_selector.Show()
            
        else:
            
            self._booru_selector.Hide()
            
        
        wx.CallAfter( self._ConfigureImportTagOptions )
        
        ClientGUITopLevelWindows.PostSizeChangedEvent( self )
        
    
    def _SeedCache( self ):
        
        dupe_seed_cache = self._seed_cache.Duplicate()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'file import status' ) as dlg:
            
            import ClientGUISeedCache
            
            panel = ClientGUISeedCache.EditSeedCachePanel( dlg, HG.client_controller, dupe_seed_cache )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._seed_cache = panel.GetValue()
                
                self._UpdateCommandButtons()
                self._UpdateSeedInfo()
                
            
        
    
    def CheckNow( self ):
        
        self._check_now = True
        
        self._UpdateCommandButtons()
        self._UpdateLastNextCheck()
        
    
    def EventBooruSelected( self, event ):
        
        self._ConfigureImportTagOptions()
        
    
    def EventPeriodChanged( self, event ):
        
        self._UpdateLastNextCheck()
        
    
    def EventSiteChanged( self, event ):
        
        self._PresentForSiteType()
        
    
    def GetValue( self ):
        
        name = self._name.GetValue()
        
        subscription = ClientImporting.Subscription( name )
        
        gallery_identifier = self._GetGalleryIdentifier()
        
        # in future, this can be harvested from some checkboxes or whatever for stream selection
        gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( gallery_identifier )
        
        query = self._query.GetValue()
        
        period = self._period.GetValue()
        
        initial_file_limit = self._initial_file_limit.GetValue()
        periodic_file_limit = self._periodic_file_limit.GetValue()
        
        paused = self._paused.GetValue()
        
        import_file_options = self._import_file_options.GetOptions()
        
        import_tag_options = self._import_tag_options.GetOptions()
        
        subscription.SetTuple( gallery_identifier, gallery_stream_identifiers, query, period, self._get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options, self._last_checked, self._last_error, self._check_now, self._seed_cache )
        
        return subscription
        
    
    def ResetCache( self ):
        
        message = '''Resetting this subscription's cache will delete ''' + HydrusData.ConvertIntToPrettyString( self._original_subscription.GetSeedCache().GetSeedCount() ) + ''' remembered urls, meaning when the subscription next runs, it will try to download those all over again. This may be expensive in time and data. Only do it if you are willing to wait. Do you want to do it?'''
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._last_checked = 0
                self._last_error = 0
                self._seed_cache = ClientImporting.SeedCache()
                
                self._UpdateCommandButtons()
                self._UpdateLastNextCheck()
                self._UpdateSeedInfo()
                
            
        
    
    def RetryFailed( self ):
        
        failed_seeds = self._seed_cache.GetSeeds( CC.STATUS_FAILED )
        
        self._seed_cache.UpdateSeedsStatus( failed_seeds, CC.STATUS_UNKNOWN )
        
        self._last_error = 0
        
        self._UpdateCommandButtons()
        self._UpdateLastNextCheck()
        self._UpdateSeedInfo()
        
    

class EditTagCensorPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_censor ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowHelp )
        
        #
        
        blacklist_panel = ClientGUICommon.StaticBox( self, 'exclude these' )
        
        self._blacklist = ClientGUIListBoxes.ListBoxTagsCensorship( blacklist_panel )
        
        self._blacklist_input = wx.TextCtrl( blacklist_panel, style = wx.TE_PROCESS_ENTER )
        self._blacklist_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownBlacklist )
        
        add_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'add', self._AddBlacklist )
        delete_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'delete', self._DeleteBlacklist )
        blacklist_everything_button = ClientGUICommon.BetterButton( blacklist_panel, 'block everything', self._BlacklistEverything )
        
        #
        
        whitelist_panel = ClientGUICommon.StaticBox( self, 'except for these' )
        
        self._whitelist = ClientGUIListBoxes.ListBoxTagsCensorship( whitelist_panel )
        
        self._whitelist_input = wx.TextCtrl( whitelist_panel, style = wx.TE_PROCESS_ENTER )
        self._whitelist_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownWhitelist )
        
        add_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'add', self._AddWhitelist )
        delete_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'delete', self._DeleteWhitelist )
        
        #
        
        self._status_st = ClientGUICommon.BetterStaticText( self, 'current: ' )
        
        #
        
        blacklist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_censor.GetTagSlicesToRules().items() if rule == CC.CENSOR_BLACKLIST ]
        whitelist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_censor.GetTagSlicesToRules().items() if rule == CC.CENSOR_WHITELIST ]
        
        self._blacklist.AddTags( blacklist_tag_slices )
        self._whitelist.AddTags( whitelist_tag_slices )
        
        self._UpdateStatus()
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.AddF( add_blacklist_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( delete_blacklist_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( blacklist_everything_button, CC.FLAGS_VCENTER )
        
        blacklist_panel.AddF( self._blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        blacklist_panel.AddF( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox.AddF( add_whitelist_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( delete_whitelist_button, CC.FLAGS_VCENTER )
        
        whitelist_panel.AddF( self._whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        whitelist_panel.AddF( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        help_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st = ClientGUICommon.BetterStaticText( self, 'help for this panel -->' )
        
        st.SetForegroundColour( wx.Colour( 0, 0, 255 ) )
        
        help_hbox.AddF( st, CC.FLAGS_VCENTER )
        help_hbox.AddF( help_button, CC.FLAGS_VCENTER )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
    
    def _AddBlacklist( self ):
        
        tag_slice = self._blacklist_input.GetValue()
        
        self._blacklist.EnterTags( ( tag_slice, ) )
        
        self._whitelist.RemoveTags( ( tag_slice, ) )
        
        self._blacklist_input.SetValue( '' )
        
        self._UpdateStatus()
        
    
    def _AddWhitelist( self ):
        
        tag_slice = self._whitelist_input.GetValue()
        
        self._whitelist.EnterTags( ( tag_slice, ) )
        
        self._blacklist.RemoveTags( ( tag_slice, ) )
        
        self._whitelist_input.SetValue( '' )
        
        self._UpdateStatus()
        
    
    def _BlacklistEverything( self ):
        
        tag_slices = self._blacklist.GetClientData()
        
        self._blacklist.RemoveTags( tag_slices )
        
        self._blacklist.AddTags( ( '', ':' ) )
        
        self._UpdateStatus()
        
    
    def _DeleteBlacklist( self ):
        
        selected_tag_slices = self._blacklist.GetSelectedTags()
        
        if len( selected_tag_slices ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._blacklist.RemoveTags( selected_tag_slices )
                    
                
            
        
        self._UpdateStatus()
        
    
    def _DeleteWhitelist( self ):
        
        selected_tag_slices = self._whitelist.GetSelectedTags()
        
        if len( selected_tag_slices ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._whitelist.RemoveTags( selected_tag_slices )
                    
                
            
        
        self._UpdateStatus()
        
    
    def _ShowHelp( self ):
        
        help = 'Here you can set rules to filter tags. By default, all tags will be allowed.'
        help += os.linesep * 2
        help += 'Add tags or classes of tag to the left to exclude them. Here are the formats accepted:'
        help += os.linesep * 2
        help += '"tag" or "namespace:tag" - just a single tag'
        help += os.linesep
        help += '"namespace:" - all instances of that namespace'
        help += os.linesep
        help += '":" - all namespaced tags'
        help += os.linesep
        help += '"" (i.e. an empty string) - all unnamespaced tags'
        help += os.linesep * 2
        help += 'If you want to ban all of a class of tag except for some specific cases, add those specifics on the right to create exceptions for them.'
        help += os.linesep * 2
        help += 'If you want to make this work like a whitelist, hit \'block everything\' (to block everything on the left) and then add what you do want on the right.'
        
        wx.MessageBox( help )
        
    
    def _UpdateStatus( self ):
        
        tag_censor = self.GetValue()
        
        pretty_tag_censor = tag_censor.ToPermittedString()
        
        self._status_st.SetLabelText( 'current: ' + pretty_tag_censor )
        
    
    def EventKeyDownBlacklist( self, event ):
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            self._AddBlacklist()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDownWhitelist( self, event ):
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            self._AddWhitelist()
            
        else:
            
            event.Skip()
            
        
    
    def GetValue( self ):
        
        tag_censor = ClientData.TagCensor()
        
        for tag_slice in self._blacklist.GetClientData():
            
            tag_censor.SetRule( tag_slice, CC.CENSOR_BLACKLIST )
            
        
        for tag_slice in self._whitelist.GetClientData():
            
            tag_censor.SetRule( tag_slice, CC.CENSOR_WHITELIST )
            
        
        return tag_censor
        
    
