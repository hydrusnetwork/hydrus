import ClientCaches
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientMedia
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusSerialisable
import HydrusTags
import itertools
import os
import string
import time
import traceback
import wx
import wx.lib.scrolledpanel

class ManageTagsPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent, file_service_key, media, immediate_commit = False, canvas_key = None ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent )
        
        self._file_service_key = file_service_key
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        self._tag_repositories = ClientGUICommon.ListBook( self )
        self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
        
        #
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_repositories, self._file_service_key, service.GetServiceKey(), self._current_media, self._immediate_commit )
            
            self._tag_repositories.AddPage( name, service_key, page )
            
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        self._tag_repositories.Select( default_tag_repository_key )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        self.RefreshAcceleratorTable()
        
        if self._canvas_key is not None:
            
            HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = ( new_media_singleton.Duplicate(), )
            
            for page in self._tag_repositories.GetActivePages():
                
                page.SetMedia( self._current_media )
                
            
        
    
    def CommitChanges( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetActivePages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventCharHook( self, event ):
        
        if not HC.PLATFORM_LINUX:
            
            # If I let this go uncaught, it propagates to the media viewer above, so an Enter or a '+' closes the window or zooms in!
            # The DoAllowNextEvent tells wx to gen regular key_down/char events so our text box gets them like normal, despite catching the event here
            
            event.DoAllowNextEvent()
            
        else:
            
            # Top jej, the events weren't being generated after all in Linux, so here's a possibly borked patch for that:
            
            HydrusGlobals.do_not_catch_char_hook = True
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_tags':
                
                wx.PostEvent( self.GetParent(), wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'ok' ) ) )
                
            elif command == 'set_search_focus':
                
                self._SetSearchFocus()
                
            elif command == 'canvas_show_next':
                
                if self._canvas_key is not None:
                    
                    HydrusGlobals.client_controller.pub( 'canvas_show_next', self._canvas_key )
                    
                
            elif command == 'canvas_show_previous':
                
                if self._canvas_key is not None:
                    
                    HydrusGlobals.client_controller.pub( 'canvas_show_previous', self._canvas_key )
                    
                
            else:
                
                event.Skip()
                
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_tags', 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
            
            entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
            
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_key, tag_service_key, media, immediate_commit ):
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_key = file_service_key
            self._tag_service_key = tag_service_key
            self._immediate_commit = immediate_commit
            
            self._content_updates = []
            
            self._i_am_local_tag_service = self._tag_service_key == CC.LOCAL_TAG_SERVICE_KEY
            
            if not self._i_am_local_tag_service:
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( tag_service_key )
                
                try: self._account = service.GetInfo( 'account' )
                except: self._account = HydrusData.GetUnknownAccount()
                
            
            self._tags_box_sorter = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'tags' )
            
            self._tags_box = ClientGUICommon.ListBoxTagsSelectionTagsDialog( self._tags_box_sorter, self.AddTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            self._collapse_siblings_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'auto-replace entered siblings' )
            self._collapse_siblings_checkbox.SetValue( self._new_options.GetBoolean( 'replace_siblings_on_manage_tags' ) )
            self._collapse_siblings_checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckCollapseSiblings )
            
            self._show_deleted_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'show deleted' )
            self._show_deleted_checkbox.Bind( wx.EVT_CHECKBOX, self.EventShowDeleted )
            
            self._tags_box_sorter.AddF( self._collapse_siblings_checkbox, CC.FLAGS_LONE_BUTTON )
            self._tags_box_sorter.AddF( self._show_deleted_checkbox, CC.FLAGS_LONE_BUTTON )
            
            expand_parents = True
            
            self._add_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.AddTags, expand_parents, self._file_service_key, self._tag_service_key, null_entry_callable = self.Ok )
            
            self._advanced_content_update_button = wx.Button( self, label = 'advanced operation' )
            self._advanced_content_update_button.Bind( wx.EVT_BUTTON, self.EventAdvancedContentUpdate )
            
            self._modify_mappers = wx.Button( self, label = 'modify mappers' )
            self._modify_mappers.Bind( wx.EVT_BUTTON, self.EventModify )
            
            self._copy_tags = wx.Button( self, label = 'copy tags' )
            self._copy_tags.Bind( wx.EVT_BUTTON, self.EventCopyTags )
            
            self._paste_tags = wx.Button( self, label = 'paste tags' )
            self._paste_tags.Bind( wx.EVT_BUTTON, self.EventPasteTags )
            
            if self._i_am_local_tag_service:
                
                text = 'remove all tags'
                
            else:
                
                text = 'petition all tags'
                
            
            self._remove_tags = wx.Button( self, label = text )
            self._remove_tags.Bind( wx.EVT_BUTTON, self.EventRemoveTags )
            
            self._tags_box.ChangeTagService( self._tag_service_key )
            
            self.SetMedia( media )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            if self._i_am_local_tag_service:
                
                self._modify_mappers.Hide()
                
            else:
                
                if not self._account.HasPermission( HC.MANAGE_USERS ):
                    
                    self._modify_mappers.Hide()
                    
                
            
            copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            copy_paste_hbox.AddF( self._copy_tags, CC.FLAGS_MIXED )
            copy_paste_hbox.AddF( self._paste_tags, CC.FLAGS_MIXED )
            copy_paste_hbox.AddF( self._remove_tags, CC.FLAGS_MIXED )
            copy_paste_hbox.AddF( self._advanced_content_update_button, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( copy_paste_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( self._modify_mappers, CC.FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
        
        def _AddTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            if not self._i_am_local_tag_service and self._account.HasPermission( HC.RESOLVE_PETITIONS ):
                
                forced_reason = 'admin'
                
            
            collapse_siblings = self._collapse_siblings_checkbox.GetValue()
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            num_files = len( self._media )
            
            sets_of_choices = []
            
            potential_num_reasons_needed = 0
            
            for tag in tags:
                
                if collapse_siblings:
                    
                    sibling_tag = HydrusGlobals.client_controller.GetManager( 'tag_siblings' ).GetSibling( tag )
                    
                    if sibling_tag is not None:
                        
                        tag = sibling_tag
                        
                    
                
                num_current = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetCurrent( self._tag_service_key ) ] )
                
                choices = []
                
                if self._i_am_local_tag_service:
                    
                    if not only_remove:
                        
                        if num_current < num_files:
                            
                            choices.append( ( 'add ' + tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - num_current ) + ' files', ( HC.CONTENT_UPDATE_ADD, tag ) ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > 0:
                            
                            choices.append( ( 'delete ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_current ) + ' files', ( HC.CONTENT_UPDATE_DELETE, tag ) ) )
                            
                        
                    
                else:
                    
                    num_pending = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPending( self._tag_service_key ) ] )
                    num_petitioned = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPetitioned( self._tag_service_key ) ] )
                    
                    if not only_remove:
                        
                        if num_current + num_pending < num_files: choices.append( ( 'pend ' + tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - ( num_current + num_pending ) ) + ' files', ( HC.CONTENT_UPDATE_PEND, tag ) ) )
                        
                    
                    if not only_add:
                        
                        if num_current > num_petitioned and not only_add:
                            
                            choices.append( ( 'petition ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_current - num_petitioned ) + ' files', ( HC.CONTENT_UPDATE_PETITION, tag ) ) )
                            
                            potential_num_reasons_needed += 1
                            
                        
                        if num_pending > 0 and not only_add:
                            
                            choices.append( ( 'rescind pending ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_pending ) + ' files', ( HC.CONTENT_UPDATE_RESCIND_PEND, tag ) ) )
                            
                        
                    
                    if not only_remove:
                        
                        if num_petitioned > 0:
                            
                            choices.append( ( 'rescind petitioned ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_petitioned ) + ' files', ( HC.CONTENT_UPDATE_RESCIND_PETITION, tag ) ) )
                            
                        
                    
                
                if len( choices ) == 0:
                    
                    continue
                    
                
                sets_of_choices.append( choices )
                
            
            if forced_reason is None and potential_num_reasons_needed > 1:
                
                no_user_choices = True not in ( len( choices ) > 1 for choices in sets_of_choices )
                
                if no_user_choices:
                    
                    message = 'You are about to petition more than one tag.'
                    
                else:
                    
                    message = 'You might be about to petition more than one tag.'
                    
                
                message += os.linesep * 2
                message += 'To save you time, would you like to use the same reason for all the petitions?'
                
                with ClientGUIDialogs.DialogYesNo( self, message, title = 'Many petitions found' ) as yn_dlg:
                    
                    if yn_dlg.ShowModal() == wx.ID_YES:
                        
                        message = 'Please enter your common petition reason here:'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message ) as text_dlg:
                            
                            if text_dlg.ShowModal() == wx.ID_OK:
                                
                                forced_reason = text_dlg.GetValue()
                                
                            
                        
                    
                
            
            forced_choice_actions = []
            
            for choices in sets_of_choices:
                
                always_do = False
                
                if len( choices ) == 1:
                    
                    [ ( text_gumpf, choice ) ] = choices
                    
                else:
                    
                    choice = None
                    
                    for forced_choice_action in forced_choice_actions:
                        
                        for possible_choice in choices:
                            
                            ( text_gumpf, ( choice_action, choice_tag ) ) = possible_choice
                            
                            if choice_action == forced_choice_action:
                                
                                choice = ( choice_action, choice_tag )
                                
                                break
                                
                            
                        
                        if choice is not None:
                            
                            break
                            
                        
                    
                    if choice is None:
                        
                        intro = 'What would you like to do?'
                        
                        show_always_checkbox = len( sets_of_choices ) > 1
                        
                        with ClientGUIDialogs.DialogButtonChoice( self, intro, choices, show_always_checkbox = show_always_checkbox ) as dlg:
                            
                            result = dlg.ShowModal()
                            
                            if result == wx.ID_OK:
                                
                                ( always_do, choice ) = dlg.GetData()
                                
                            else:
                                
                                break
                                
                            
                        
                    
                
                if choice is None:
                    
                    continue
                    
                
                ( choice_action, choice_tag ) = choice
                
                if always_do:
                    
                    forced_choice_actions.append( choice_action )
                    
                
                if choice_action == HC.CONTENT_UPDATE_ADD: media_to_affect = ( m for m in self._media if choice_tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_DELETE: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_PEND: media_to_affect = ( m for m in self._media if choice_tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) and choice_tag not in m.GetTagsManager().GetPending( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_PETITION: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) and choice_tag not in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetPending( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                content_updates = []
                
                if choice_action == HC.CONTENT_UPDATE_PETITION:
                    
                    if forced_reason is None:
                        
                        message = 'Enter a reason for ' + choice_tag + ' to be removed. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                reason = dlg.GetValue()
                                
                            else:
                                
                                continue
                                
                            
                        
                        
                    else:
                        
                        reason = forced_reason
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( choice_tag, hashes, reason ) ) )
                    
                else:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( choice_tag, hashes ) ) )
                    
                
                if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                    
                    tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                    
                    parents = tag_parents_manager.GetParents( self._tag_service_key, choice_tag )
                    
                    content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( parent, hashes ) ) for parent in parents ) )
                    
                
                for m in self._media:
                    
                    for content_update in content_updates:
                        
                        m.GetMediaResult().ProcessContentUpdate( self._tag_service_key, content_update )
                        
                    
                
                if self._immediate_commit:
                    
                    if len( content_updates ) > 0:
                        
                        service_keys_to_content_updates = { self._tag_service_key : content_updates }
                        
                        HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                else:
                    
                    self._content_updates.extend( content_updates )
                    
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def AddTags( self, tags ):
            
            if len( tags ) > 0:
                
                self._AddTags( tags )
                
            
        
        def EventAdvancedContentUpdate( self, event ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            self.Ok()
        
            parent = self.GetTopLevelParent().GetParent()
            
            def do_it():
                
                with ClientGUIDialogs.DialogAdvancedContentUpdate( parent, self._tag_service_key, hashes ) as dlg:
                    
                    dlg.ShowModal()
                    
                
            
            wx.CallAfter( do_it )
            
        
        def EventCheckCollapseSiblings( self, event ):
            
            self._new_options.SetBoolean( 'replace_siblings_on_manage_tags', self._collapse_siblings_checkbox.GetValue() )
            
        
        def EventCopyTags( self, event ):
        
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._tag_service_key, collapse_siblings = False )
            
            tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
            
            text = os.linesep.join( tags )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
        def EventModify( self, event ):
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in self._media ) ) )
            
            for tag in tags:
                
                contents.extend( [ HydrusData.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in hashes ] )
                
            
            if len( contents ) > 0:
                
                subject_identifiers = [ HydrusData.AccountIdentifier( content = content ) for content in contents ]
                
                with ClientGUIDialogs.DialogModifyAccounts( self, self._tag_service_key, subject_identifiers ) as dlg: dlg.ShowModal()
                
            
        
        def EventPasteTags( self, event ):
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject()
                
                wx.TheClipboard.GetData( data )
                
                wx.TheClipboard.Close()
                
                text = data.GetText()
                
                try:
                    
                    tags = HydrusData.DeserialisePrettyTags( text )
                    
                    tags = HydrusTags.CleanTags( tags )
                    
                    self._AddTags( tags, only_add = True )
                    
                except: wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventRemoveTags( self, event ):
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tag_manager in tag_managers:
                
                removable_tags.update( tag_manager.GetCurrent( self._tag_service_key ) )
                removable_tags.update( tag_manager.GetPending( self._tag_service_key ) )
                
            
            self._AddTags( removable_tags, only_remove = True )
            
        
        def EventShowDeleted( self, event ):
            
            self._tags_box.SetShow( 'deleted', self._show_deleted_checkbox.GetValue() )
            
        
        def GetContentUpdates( self ): return ( self._tag_service_key, self._content_updates )
        
        def HasChanges( self ):
            
            return len( self._content_updates ) > 0
            
        
        def Ok( self ):
            
            wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'ok' ) ) )
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = []
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.SetFocus()
            
        
    