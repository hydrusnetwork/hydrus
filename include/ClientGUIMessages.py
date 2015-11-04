import HydrusConstants as HC
import ClientConstants as CC
import ClientCaches
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMedia
import cStringIO
import hashlib
import os
import random
import threading
import traceback
import webbrowser
import wx
import wx.html
import wx.richtext
import wx.lib.scrolledpanel
import yaml
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.mixins.listctrl import ColumnSorterMixin
import HydrusData
import HydrusGlobals
'''
class ConversationsListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin ):
    
    def __init__( self, parent, page_key, identity, conversations ):
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT | wx.LC_SINGLE_SEL )
        ListCtrlAutoWidthMixin.__init__( self )
        ColumnSorterMixin.__init__( self, 8 )
        
        self._page_key = page_key
        self._identity = identity
        
        image_list = wx.ImageList( 16, 16, True, 2 )
        
        image_list.Add( CC.GlobalBMPs.transparent )
        image_list.Add( CC.GlobalBMPs.inbox )
        
        self.AssignImageList( image_list, wx.IMAGE_LIST_SMALL )
        
        self.InsertColumn( 0, 'inbox', width = 30 )
        self.InsertColumn( 1, 'subject' )
        self.InsertColumn( 2, 'creator', width = 90 )
        self.InsertColumn( 3, 'to', width = 100 )
        self.InsertColumn( 4, 'messages', width = 60 )
        self.InsertColumn( 5, 'unread', width = 60 )
        self.InsertColumn( 6, 'created', width = 130 )
        self.InsertColumn( 7, 'updated', width = 130 )
        
        self.setResizeColumn( 2 ) # subject
        
        self._SetConversations( conversations )
        
        self.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelected )
        self.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelected )
        self.Bind( wx.EVT_LIST_ITEM_RIGHT_CLICK, self.EventShowMenu )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        HydrusGlobals.client_controller.sub( self, 'SetConversations', 'set_conversations' )
        HydrusGlobals.client_controller.sub( self, 'ArchiveConversation', 'archive_conversation_gui' )
        HydrusGlobals.client_controller.sub( self, 'InboxConversation', 'inbox_conversation_gui' )
        HydrusGlobals.client_controller.sub( self, 'DeleteConversation', 'delete_conversation_gui' )
        HydrusGlobals.client_controller.sub( self, 'UpdateMessageStatuses', 'message_statuses_gui' )
        HydrusGlobals.client_controller.sub( self, 'RefreshAcceleratorTable', 'notify_new_options' )
        
    
    def RefreshAcceleratorTable( self ):
        
        entries = [
        ( wx.ACCEL_NORMAL, wx.WXK_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete' ) )
        ]
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def _GetIndexFromConversationKey( self, conversation_key ):
        
        for i in range( self.GetItemCount() ):
            
            data_index = self.GetItemData( i )
            
            conversation = self._data_indices_to_conversations[ data_index ]
            
            if conversation.GetConversationKey() == conversation_key: return i
            
        
        return None
        
    
    def _GetPrettyStatus( self ):
        
        if len( self._conversations ) == 1: return '1 conversation'
        else: return str( len( self._conversations ) ) + ' conversations'
        
    
    def _SetConversations( self, conversations ):
        
        self._conversations = list( conversations )
        
        self.DeleteAllItems()
        
        self.itemDataMap = {}
        self._data_indices_to_conversations = {}
        
        i = 0
        
        cmp_conversations = lambda c1, c2: cmp( c1.GetUpdated(), c2.GetUpdated() )
        
        self._conversations.sort( cmp = cmp_conversations, reverse = True ) # order by newest change first
        
        for conversation in self._conversations:
            
            ( conversation_key, inbox, subject, name_from, participants, message_count, unread_count, created, updated ) = conversation.GetListCtrlTuple()
            
            if created is None:
                
                created_string = ''
                updated_string = ''
                
            else:
                
                created_string = HydrusData.ConvertTimestampToHumanPrettyTime( created )
                updated_string = HydrusData.ConvertTimestampToHumanPrettyTime( updated )
                
            
            self.Append( ( '', subject, name_from, ', '.join( [ contact.GetName() for contact in participants if contact.GetName() != name_from ] ), str( message_count ), str( unread_count ), created_string, updated_string ) )
            
            data_index = i
            
            self.SetItemData( i, data_index )
            
            if inbox: self.SetItemImage( i, 1 ) # inbox
            else: self.SetItemImage( i, 0 ) # transparent
            
            self.itemDataMap[ data_index ] = ( inbox, subject, name_from, len( participants ), message_count, unread_count, created, updated )
            
            self._data_indices_to_conversations[ data_index ] = conversation
            
            i += 1
            
        
        HydrusGlobals.client_controller.pub( 'conversation_focus', self._page_key, None )
        HydrusGlobals.client_controller.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
        
    
    def _UpdateConversationItem( self, conversation_key ):
        
        selection = self._GetIndexFromConversationKey( conversation_key )
        
        if selection is not None:
            
            conversation = self._data_indices_to_conversations[ self.GetItemData( selection ) ]
            
            ( conversation_key, inbox, subject, name_from, participants, message_count, unread_count, created, updated ) = conversation.GetListCtrlTuple()
            
            selection = self._GetIndexFromConversationKey( conversation_key )
            
            data_index = self.GetItemData( selection )
            
            self.itemDataMap[ data_index ] = ( inbox, subject, name_from, len( participants ), message_count, unread_count, created, updated )
            
            if inbox: self.SetItemImage( selection, 1 )
            else: self.SetItemImage( selection, 0 )
            
            self.SetStringItem( selection, 4, str( message_count ) )
            self.SetStringItem( selection, 5, str( unread_count ) )
            
            if created is None:
                
                created_string = ''
                updated_string = ''
                
            else:
                
                created_string = HydrusData.ConvertTimestampToHumanPrettyTime( created )
                
                updated_string = HydrusData.ConvertTimestampToHumanPrettyTime( updated )
                
            
            self.SetStringItem( selection, 6, created_string )
            self.SetStringItem( selection, 7, updated_string )
            
        
    
    def ArchiveConversation( self, conversation_key ): self._UpdateConversationItem( conversation_key )
    
    def DeleteConversation( self, conversation_key ):
        
        selection = self._GetIndexFromConversationKey( conversation_key )
        
        if selection is not None:
            
            conversation = self._data_indices_to_conversations[ self.GetItemData( selection ) ]
            
            self._conversations.remove( conversation )
            
            self.DeleteItem( selection )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            selection = self.GetFirstSelected()
            
            conversation = self._data_indices_to_conversations[ self.GetItemData( selection ) ]
            
            conversation_key = conversation.GetConversationKey()
            
            identity_contact_key = self._identity.GetContactKey()
            
            if command == 'archive': HydrusGlobals.client_controller.Write( 'archive_conversation', conversation_key )
            elif command == 'inbox': HydrusGlobals.client_controller.Write( 'inbox_conversation', conversation_key )
            elif command == 'read':
                
                message_keys = conversation.GetMessageKeysWithDestination( ( self._identity, 'sent' ) )
                
                for message_key in message_keys: HydrusGlobals.client_controller.Write( 'message_statuses', message_key, [ ( identity_contact_key, 'read' ) ] )
                
            elif command == 'unread':
                
                message_keys = conversation.GetMessageKeysWithDestination( ( self._identity, 'read' ) )
                
                for message_key in message_keys: HydrusGlobals.client_controller.Write( 'message_statuses', message_key, [ ( identity_contact_key, 'sent' ) ] )
                
            elif command == 'delete':
                
                with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete this conversation?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES: HydrusGlobals.client_controller.Write( 'delete_conversation', conversation_key )
                    
                
            else: event.Skip()
            
        
    
    def EventSelected( self, event ):
        
        selection = self.GetFirstSelected()
        
        if selection == wx.NOT_FOUND: HydrusGlobals.client_controller.pub( 'conversation_focus', self._page_key, None )
        else: HydrusGlobals.client_controller.pub( 'conversation_focus', self._page_key, self._data_indices_to_conversations[ self.GetItemData( selection ) ] )
        
    
    def EventShowMenu( self, event ):
        
        conversation = self._data_indices_to_conversations[ self.GetItemData( event.GetIndex() ) ]
        
        menu = wx.Menu()
        
        if conversation.IsInbox(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'archive' ), 'archive' )
        else: menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'inbox' ), 'return to inbox' )
        
        if conversation.HasUnread(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'read' ), 'set all as read' )
        if conversation.HasRead(): menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'unread' ), 'set all as unread' )
        
        menu.AppendSeparator()
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete' ), 'delete' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def GetListCtrl( self ): return self
    
    def InboxConversation( self, conversation_key ): self._UpdateConversationItem( conversation_key )
    
    def SetConversations( self, page_key, conversations ):
        
        if page_key == self._page_key:
            
            try: self._SetConversations( conversations )
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def UpdateMessageStatuses( self, message_key, updates ):
        
        for conversation in self._data_indices_to_conversations.values():
            
            if conversation.HasMessageKey( message_key ):
                
                conversation_key = conversation.GetConversationKey()
                
                self._UpdateConversationItem( conversation_key )
                
            
        
    
class ConversationPanel( wx.Panel ):
    
    def __init__( self, parent, page_key, identity, conversation ):
        
        wx.Panel.__init__( self, parent, style = wx.SIMPLE_BORDER )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self._identity = identity
        self._page_key = page_key
        self._conversation = conversation
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._message_keys_to_message_panels = {}
        self._draft_keys_to_draft_panels = {}
        
        self._scrolling_messages_window = wx.lib.scrolledpanel.ScrolledPanel( self )
        self._scrolling_messages_window.SetupScrolling()
        self._scrolling_messages_window.SetScrollRate( 0, 50 )
        
        self._window_vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._messages_vbox = wx.BoxSizer( wx.VERTICAL )
        self._drafts_vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._window_vbox.AddF( self._messages_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._window_vbox.AddF( self._drafts_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._DrawConversation()
        
        self.SetSizer( self._vbox )
        
        HydrusGlobals.client_controller.sub( self, 'DeleteDraft', 'delete_draft_gui' )
        HydrusGlobals.client_controller.sub( self, 'NewMessage', 'new_message' )
        
    
    def _DrawConversation( self ):
        
        # fix it so this stuff is reusable?
        
        self._messages_vbox.DeleteWindows()
        self._drafts_vbox.DeleteWindows()
        
        self._convo_frame = wx.Panel( self )
        
        convo_vbox = wx.BoxSizer( wx.VERTICAL )
        
        subject_static_text = wx.StaticText( self._convo_frame, label = self._conversation.GetSubject() )
        
        f = subject_static_text.GetFont()
        
        f.SetWeight( wx.BOLD )
        
        subject_static_text.SetFont( f )
        
        convo_vbox.AddF( subject_static_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        convo_vbox.AddF( wx.StaticText( self._convo_frame, label = ', '.join( contact.GetName() for contact in self._conversation.GetParticipants() ) ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._convo_frame.SetSizer( convo_vbox )
        
        # archive_all
        # set all as read
        # delete all button, eventually
        
        ( messages, drafts ) = self._conversation.GetMessages()
        
        for message in messages:
            
            message_panel = MessagePanel( self._scrolling_messages_window, message, self._identity )
            
            self._message_keys_to_message_panels[ message.GetMessageKey() ] = message_panel
            
            self._messages_vbox.AddF( message_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        for draft in drafts:
            
            draft_panel = DraftPanel( self._scrolling_messages_window, draft )
            
            self._draft_keys_to_draft_panels[ draft.GetDraftKey() ] = draft_panel
            
            self._drafts_vbox.AddF( draft_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._reply_button = wx.Button( self._scrolling_messages_window, label = 'reply' )
        self._reply_button.Bind( wx.EVT_BUTTON, self.EventReply )
        self._reply_button.Disable()
        
        if len( messages ) > 0 and self._conversation.GetStartedBy().GetName() != 'Anonymous': self._reply_button.Enable()
        
        if self._conversation.GetStartedBy() == self._identity: self._reply_button.Enable()
        
        self._window_vbox.AddF( self._reply_button, CC.FLAGS_LONE_BUTTON )
        
        self._scrolling_messages_window.SetSizer( self._window_vbox )
        
        self._vbox.AddF( self._convo_frame, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._vbox.AddF( self._scrolling_messages_window, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( self._vbox )
        
    
    def DeleteDraft( self, draft_key ):
        
        if draft_key in self._draft_keys_to_draft_panels:
            
            draft_panel = self._draft_keys_to_draft_panels[ draft_key ]
            
            del self._draft_keys_to_draft_panels[ draft_key ]
            
            self._drafts_vbox.Detach( draft_panel )
            
            wx.CallAfter( draft_panel.Destroy )
            
            self._scrolling_messages_window.FitInside()
            
        
    
    def EventReply( self, event ):
        
        draft_key = HydrusData.GenerateKey()
        conversation_key = self._conversation.GetConversationKey()
        subject = self._conversation.GetSubject()
        contact_from = self._identity
        participants = self._conversation.GetParticipants()
        contact_names_to = [ contact.GetName() for contact in participants if contact is not None and contact.GetName() != 'Anonymous' and contact != contact_from ]
        recipients_visible = True
        body = ''
        attachment_hashes = []
        
        draft = ClientConstantsMessages.DraftMessage( draft_key, conversation_key, subject, contact_from, contact_names_to, recipients_visible, body, attachment_hashes, is_new = True )
        
        self._conversation.AddDraft( draft )
        
        draft_panel = DraftPanel( self._scrolling_messages_window, draft )
        
        self._draft_keys_to_draft_panels[ draft_key ] = draft_panel
        
        self._drafts_vbox.AddF( draft_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._scrolling_messages_window.FitInside()
        
    
    def NewMessage( self, conversation_key, message ):
        
        if self._conversation is not None and conversation_key == self._conversation.GetConversationKey():
            
            message_key = message.GetMessageKey()
            
            if message_key not in self._message_keys_to_message_panels: # if not already here!
                
                message_panel = MessagePanel( self._scrolling_messages_window, message, self._identity )
                
                self._message_keys_to_message_panels[ message_key ] = message_panel
                
                self._messages_vbox.AddF( message_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._conversation.AddMessage( message )
                
                self._scrolling_messages_window.FitInside()
                
            
        
    
class ConversationSplitter( wx.SplitterWindow ):
    
    def __init__( self, parent, page_key, identity, conversations = None ):
        
        if conversations is None: conversations = []
        
        wx.SplitterWindow.__init__( self, parent )
        
        self._page_key = page_key
        self._identity = identity
        self._conversations = conversations
        
        self.SetMinimumPaneSize( 180 )
        self.SetSashGravity( 0.0 )
        
        self._InitConversationsPanel()
        self._InitConversationPanel()
        
        wx.CallAfter( self.SplitHorizontally, self._conversations_panel, self._conversation_panel, 180 )
        wx.CallAfter( self._conversation_panel.Refresh )
        
        HydrusGlobals.client_controller.sub( self, 'SetConversationFocus', 'conversation_focus' )
        
    
    def _InitConversationsPanel( self ): self._conversations_panel = ConversationsListCtrl( self, self._page_key, self._identity, self._conversations )
    
    def _InitConversationPanel( self ): self._conversation_panel = wx.Window( self )
    
    def SetConversationFocus( self, page_key, conversation ):
        
        if page_key == self._page_key:
            
            with wx.FrozenWindow( self ):
                
                if conversation is None: new_panel = wx.Window( self )
                else: new_panel = ConversationPanel( self, self._page_key, self._identity, conversation )
                
                self.ReplaceWindow( self._conversation_panel, new_panel )
                
                self._conversation_panel.Close()
                
                self._conversation_panel = new_panel
                
            
        
    
class DestinationPanel( wx.Panel ):
    
    def __init__( self, parent, message_key, contact, status, identity ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( CC.COLOUR_MESSAGE )
        
        self._message_key = message_key
        self._contact = contact
        self._contact_key = contact.GetContactKey()
        self._identity = identity
        self._status = status
        
        name = contact.GetName()
        
        name_static_text = wx.StaticText( self, label = name )
        
        if self._contact == self._identity:
            
            f = name_static_text.GetFont()
            
            f.SetWeight( wx.BOLD )
            
            name_static_text.SetFont( f )
            
            if self._status == 'sent': self._status = 'unread'
            
        
        self._status_panel = self._CreateStatusPanel()
        
        self._hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._hbox.AddF( name_static_text, CC.FLAGS_MIXED )
        self._hbox.AddF( self._status_panel, CC.FLAGS_MIXED )
        
        self.SetSizer( self._hbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _CreateStatusPanel( self ):
        
        if self._status == 'failed':
            
            status_text = wx.StaticText( self, label = self._status )
            
            status_text.SetForegroundColour( ( 128, 0, 0 ) )
            
            status_text.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
            
            status_text.Bind( wx.EVT_LEFT_DOWN, self.EventRetryMenu )
            
        elif self._status == 'unread':
            
            status_text = wx.StaticText( self, label = self._status )
            
            status_text.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )
            
            status_text.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
            
            status_text.Bind( wx.EVT_LEFT_DOWN, self.EventReadMenu )
            
        elif self._status == 'read':
            
            status_text = wx.StaticText( self, label = self._status )
            
            status_text.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )
            
            status_text.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
            
            status_text.Bind( wx.EVT_LEFT_DOWN, self.EventUnreadMenu )
            
        else:
            
            status_text = wx.StaticText( self, label = self._status )
            
            status_text.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )
            
        
        return status_text
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command in ( 'retry', 'read', 'unread' ):
                
                if command == 'retry': status = 'pending'
                elif command == 'read': status = 'read'
                elif command == 'unread': status = 'sent'
                
                my_message_depot = HydrusGlobals.client_controller.GetServicesManager().GetService( self._identity.GetServiceKey() )
                
                connection = my_message_depot.GetConnection()
                
                my_public_key = self._identity.GetPublicKey()
                my_contact_key = self._identity.GetContactKey()
                
                contacts_contact_key = self._contact.GetContactKey()
                
                status_updates = []
                
                status_key = hashlib.sha256( contacts_contact_key + self._message_key ).digest()
                
                packaged_status = HydrusMessageHandling.PackageStatusForDelivery( ( self._message_key, contacts_contact_key, status ), my_public_key )
                
                status_updates = ( ( status_key, packaged_status ), )
                
                connection.Post( 'message_statuses', contact_key = my_contact_key, statuses = status_updates )
                
                HydrusGlobals.client_controller.Write( 'message_statuses', self._message_key, [ ( self._contact_key, status ) ] )
                
            else: event.Skip()
            
        
    
    def EventReadMenu( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'read' ), 'read' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def EventRetryMenu( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'retry' ), 'retry' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def EventUnreadMenu( self, event ):
        
        menu = wx.Menu()
        
        menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'unread' ), 'unread' )
        
        self.PopupMenu( menu )
        
        wx.CallAfter( menu.Destroy )
        
    
    def SetStatus( self, status ):
        
        if self._contact == self._identity and status == 'sent': status = 'unread'
        
        self._status = status
        
        new_status_panel = self._CreateStatusPanel()
        
        self._hbox.Replace( self._status_panel, new_status_panel )
        
        self._status_panel.Close()
        
        self._status_panel = new_status_panel
        
    
class DestinationsPanel( wx.Panel ):
    
    def __init__( self, parent, message_key, destinations, identity ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( CC.COLOUR_MESSAGE )
        
        self._message_key = message_key
        self._my_panels = {}
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for ( contact, status ) in destinations:
            
            destination_panel = DestinationPanel( self, message_key, contact, status, identity )
            
            vbox.AddF( destination_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._my_panels[ contact.GetContactKey() ] = destination_panel
            
        
        self.SetSizer( vbox )
        
        HydrusGlobals.client_controller.sub( self, 'UpdateMessageStatuses', 'message_statuses_gui' )
        
    
    def UpdateMessageStatuses( self, message_key, updates ):
        
        if message_key == self._message_key:
            
            with wx.FrozenWindow( self ):
                
                for ( contact_key, status ) in updates:
                    
                    if contact_key in self._my_panels: self._my_panels[ contact_key ].SetStatus( status )
                    
                
                # doing replace on the destpanels' tricky sizer is a huge pain, hence the size event
                # has to be postevent, not processevent
                wx.PostEvent( self.GetParent(), wx.SizeEvent() )
                
            
        
    
# A whole bunch of this is cribbed from/inspired by the excellent rtc example in the wxPython Demo
class DraftBodyPanel( wx.Panel ):
    
    ID_BOLD = 0
    ID_ITALIC = 1
    ID_UNDERLINE = 2
    
    ID_ALIGN_LEFT = 3
    ID_ALIGN_CENTER = 4
    ID_ALIGN_RIGHT = 5
    ID_ALIGN_JUSTIFY = 6 # rtc doesn't yet support this, sadly
    
    ID_INDENT_LESS = 7
    ID_INDENT_MORE = 8
    
    ID_FONT = 9
    ID_FONT_COLOUR = 10
    
    ID_LINK = 11
    ID_LINK_BREAK = 12
    
    def __init__( self, parent, xml ):
        
        wx.Panel.__init__( self, parent )
        
        self._CreateToolBar()
        
        self._CreateRTC( xml )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._toolbar, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._rtc, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( [
        ( wx.ACCEL_CTRL, ord( 'b' ), self.ID_BOLD ),
        ( wx.ACCEL_CTRL, ord( 'i' ), self.ID_ITALIC ),
        ( wx.ACCEL_CTRL, ord( 'u' ), self.ID_UNDERLINE )
        ] ) )
        
        self.Bind( wx.EVT_TOOL, self.EventToolBar )
        
        self.Bind( wx.EVT_UPDATE_UI, self.EventUpdateUI )
        
    
    def _CreateToolBar( self ):
        
        self._toolbar = wx.ToolBar( self )
        
        self._toolbar.SetToolBitmapSize( ( 16, 16 ) )
        
        self._toolbar.AddCheckTool( self.ID_BOLD, CC.GlobalBMPs.bold )
        self._toolbar.AddCheckTool( self.ID_ITALIC, CC.GlobalBMPs.italic )
        self._toolbar.AddCheckTool( self.ID_UNDERLINE, CC.GlobalBMPs.underline )
        
        self._toolbar.AddSeparator()
        
        self._toolbar.AddRadioTool( self.ID_ALIGN_LEFT, CC.GlobalBMPs.align_left )
        self._toolbar.AddRadioTool( self.ID_ALIGN_CENTER, CC.GlobalBMPs.align_center )
        self._toolbar.AddRadioTool( self.ID_ALIGN_RIGHT, CC.GlobalBMPs.align_right )
        
        self._toolbar.AddSeparator()
        
        self._toolbar.AddLabelTool( self.ID_INDENT_LESS, 'indent less', CC.GlobalBMPs.indent_less )
        self._toolbar.AddLabelTool( self.ID_INDENT_MORE, 'indent more', CC.GlobalBMPs.indent_more )
        
        self._toolbar.AddSeparator()
        
        self._toolbar.AddLabelTool( self.ID_FONT, 'font', CC.GlobalBMPs.font )
        self._toolbar.AddLabelTool( self.ID_FONT_COLOUR, 'font colour', CC.GlobalBMPs.colour, shortHelp = 'font colour' )
        
        # font background
        # message background?
        
        self._toolbar.AddSeparator()
        
        self._toolbar.AddLabelTool( self.ID_LINK, 'link', CC.GlobalBMPs.link )
        self._toolbar.AddLabelTool( self.ID_LINK_BREAK, 'break link', CC.GlobalBMPs.link_break )
        
        self._toolbar.Realize()
        
    
    def _CreateRTC( self, xml ):
        
        self._rtc = wx.richtext.RichTextCtrl( self, size = ( -1, 300 ), style = wx.WANTS_CHARS | wx.richtext.RE_MULTILINE )
        
        if len( xml ) > 0:
            
            xml_handler = wx.richtext.RichTextXMLHandler()
            
            stream = cStringIO.StringIO( xml )
            
            xml_handler.LoadStream( self._rtc.GetBuffer(), stream )
            
        
    
    def EventUpdateUI( self, event ):
        
        self._toolbar.ToggleTool( self.ID_BOLD, self._rtc.IsSelectionBold() )
        self._toolbar.ToggleTool( self.ID_ITALIC, self._rtc.IsSelectionItalics() )
        self._toolbar.ToggleTool( self.ID_UNDERLINE, self._rtc.IsSelectionUnderlined() )
        
        if self._rtc.IsSelectionAligned( wx.TEXT_ALIGNMENT_LEFT ): self._toolbar.ToggleTool( self.ID_ALIGN_LEFT, True )
        elif self._rtc.IsSelectionAligned( wx.TEXT_ALIGNMENT_CENTER ): self._toolbar.ToggleTool( self.ID_ALIGN_CENTER, True )
        elif self._rtc.IsSelectionAligned( wx.TEXT_ALIGNMENT_RIGHT ): self._toolbar.ToggleTool( self.ID_ALIGN_RIGHT, True )
        
        event.Skip()
        
    
    def EventToolBar( self, event ):
        
        id = event.GetId()
        
        if id == self.ID_BOLD: self._rtc.ApplyBoldToSelection()
        elif id == self.ID_ITALIC: self._rtc.ApplyItalicToSelection()
        elif id == self.ID_UNDERLINE: self._rtc.ApplyUnderlineToSelection()
        elif id == self.ID_ALIGN_LEFT: self._rtc.ApplyAlignmentToSelection( wx.TEXT_ALIGNMENT_LEFT )
        elif id == self.ID_ALIGN_CENTER: self._rtc.ApplyAlignmentToSelection( wx.TEXT_ALIGNMENT_CENTRE )
        elif id == self.ID_ALIGN_RIGHT: self._rtc.ApplyAlignmentToSelection( wx.TEXT_ALIGNMENT_RIGHT )
        elif id == self.ID_INDENT_LESS:
            
            text_attribute = wx.TEXTAttrEx()
            
            text_attribute.SetFlags( wx.TEXT_ATTR_LEFT_INDENT )
            
            ip = self._rtc.GetInsertionPoint()
            
            if self._rtc.GetStyle( ip, text_attribute ): # this copies the current style into text_attribute, returning true if successful
                
                if self._rtc.HasSelection(): selection_range = self._rtc.GetSelectionRange()
                else: selection_range = wx.richtext.RichTextRange( ip, ip )
                
                if text_attribute.GetLeftIndent() >= 100:
                    
                    text_attribute.SetLeftIndent( text_attribute.GetLeftIndent() - 100 )
                    text_attribute.SetFlags( wx.TEXT_ATTR_LEFT_INDENT )
                    
                    self._rtc.SetStyle( selection_range, text_attribute )
                    
                
            
        elif id == self.ID_INDENT_MORE:
            
            text_attribute = wx.richtext.TextAttrEx()
            
            text_attribute.SetFlags( wx.TEXT_ATTR_LEFT_INDENT )
            
            ip = self._rtc.GetInsertionPoint()
            
            if self._rtc.GetStyle( ip, text_attribute ): # this copies the current style into text_attribute, returning true if successful
                
                if self._rtc.HasSelection(): selection_range = self._rtc.GetSelectionRange()
                else: selection_range = wx.richtext.RichTextRange( ip, ip )
                
                text_attribute.SetLeftIndent( text_attribute.GetLeftIndent() + 100 )
                text_attribute.SetFlags( wx.TEXT_ATTR_LEFT_INDENT )
                
                self._rtc.SetStyle( selection_range, text_attribute )
                
            
        elif id == self.ID_FONT:
            
            font_data = wx.FontData()
            font_data.EnableEffects( False )
            
            text_attribute = wx.richtext.TextAttrEx()
            text_attribute.SetFlags( wx.TEXT_ATTR_FONT )
            
            if self._rtc.GetStyle( self._rtc.GetInsertionPoint(), text_attribute ): font_data.SetInitialFont( text_attribute.GetFont() )
            
            with wx.FontDialog( self, font_data ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    font_data = dlg.GetFontData()
                    
                    font = font_data.GetChosenFont()
                    
                    if not self._rtc.HasSelection(): self._rtc.BeginFont( font )
                    else:
                        
                        selection_range = self._rtc.GetSelectionRange()
                        
                        text_attribute.SetFlags( wx.TEXT_ATTR_FONT )
                        text_attribute.SetFont( font )
                        
                        self._rtc.SetStyle( selection_range, text_attribute )
                        
                    
                
            
        elif id == self.ID_FONT_COLOUR:
            
            colour_data = wx.ColourData()
            
            text_attribute = wx.richtext.TextAttrEx()
            text_attribute.SetFlags( wx.TEXT_ATTR_TEXT_COLOUR )
            
            if self._rtc.GetStyle( self._rtc.GetInsertionPoint(), text_attribute ): colour_data.SetColour( text_attribute.GetTextColour() )
            
            with wx.ColourDialog( self, colour_data ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    colour_data = dlg.GetColourData()
                    colour = colour_data.GetColour()
                    
                    if colour:
                        
                        if not self._rtc.HasSelection(): self._rtc.BeginTextColour( colour )
                        else:
                            
                            selection_range = self._rtc.GetSelectionRange()
                            
                            text_attribute.SetFlags( wx.TEXT_ATTR_TEXT_COLOUR )
                            text_attribute.SetTextColour( colour )
                            
                            self._rtc.SetStyle( selection_range, text_attribute )
                            
                        
                    
                
            
        elif id == self.ID_LINK:
            
            text_attribute = wx.richtext.TextAttrEx()
            
            text_attribute.SetFlags( wx.TEXT_ATTR_URL )
            
            ip = self._rtc.GetInsertionPoint()
            
            self._rtc.GetStyle( self._rtc.GetInsertionPoint(), text_attribute )
            
            if text_attribute.HasURL(): initial_url = text_attribute.GetURL()
            else: initial_url = 'http://'
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter url.', default = initial_url ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    url = dlg.GetValue()
                    
                    if self._rtc.HasSelection(): selection_range = self._rtc.GetSelectionRange()
                    else: selection_range = wx.richtext.RichTextRange( ip, ip )
                    
                    text_attribute.SetFlags( wx.TEXT_ATTR_TEXT_COLOUR )
                    text_attribute.SetTextColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )
                    
                    text_attribute.SetFontUnderlined( True )
                    
                    text_attribute.SetURL( url )
                    
                    self._rtc.SetStyle( selection_range, text_attribute )
                    
                
            
        elif id == self.ID_LINK_BREAK:
            
            if self._rtc.HasSelection(): selection_range = self._rtc.GetSelectionRange()
            else: selection_range = wx.richtext.RichTextRange( ip, ip )
            
            text_attribute = wx.richtext.TextAttrEx()
            
            text_attribute.SetFlags( wx.TEXT_ATTR_TEXT_COLOUR )
            text_attribute.SetTextColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWTEXT ) )
            
            text_attribute.SetFontUnderlined( False )
            
            self._rtc.SetStyle( selection_range, text_attribute )
            
            text_attribute = wx.richtext.TextAttrEx()
            
            text_attribute.SetFlags( wx.TEXT_ATTR_URL )
            
            self._rtc.SetStyleEx( selection_range, text_attribute, wx.richtext.RICHTEXT_SETSTYLE_REMOVE )
            
        
    
    def GetXMLHTML( self ):
        
        xml_handler = wx.richtext.RichTextXMLHandler()
        
        stream = cStringIO.StringIO()
        
        xml_handler.SaveStream( self._rtc.GetBuffer(), stream )
        
        stream.seek( 0 )
        
        xml = stream.read()
        
        html_handler = wx.richtext.RichTextHTMLHandler()
        html_handler.SetFlags( wx.richtext.RICHTEXT_HANDLER_SAVE_IMAGES_TO_MEMORY )
        html_handler.SetFontSizeMapping( [7,9,11,12,14,22,100] )
        
        stream = cStringIO.StringIO()
        
        html_handler.SaveStream( self._rtc.GetBuffer(), stream )
        
        stream.seek( 0 )
        
        html = stream.read()
        
        return yaml.safe_dump( ( xml, html ) )
        

    
class DraftPanel( wx.Panel ):
    
    def __init__( self, parent, draft_message ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( CC.COLOUR_MESSAGE )
        
        self._compose_key = HydrusData.GenerateKey()
        
        self._draft_message = draft_message
        
        ( self._draft_key, self._conversation_key, subject, self._contact_from, contacts_to, recipients_visible, body, attachment_hashes ) = self._draft_message.GetInfo()
        
        is_new = self._draft_message.IsNew()
        
        self._from = wx.StaticText( self, label = self._contact_from.GetName() )
        
        if not self._draft_message.IsReply():
            
            self._to_panel = ClientGUICommon.StaticBox( self, 'to' )
            
            self._recipients_list = wx.ListCtrl( self._to_panel, style = wx.LC_LIST | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL )
            self._recipients_list.InsertColumn( 0, 'contacts' )
            for name in contacts_to: self._recipients_list.Append( ( name, ) )
            self._recipients_list.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventRemove )
            
            self._new_recipient = ClientGUICommon.AutoCompleteDropdownContacts( self._to_panel, self._compose_key, self._contact_from )
            
            self._recipients_visible = wx.CheckBox( self._to_panel )
            self._recipients_visible.SetValue( recipients_visible )
            self._recipients_visible.Bind( wx.EVT_CHECKBOX, self.EventChanged )
            
            self._subject_panel = ClientGUICommon.StaticBox( self, 'subject' )
            
            self._subject = wx.TextCtrl( self._subject_panel, value = subject )
            self._subject.Bind( wx.EVT_KEY_DOWN, self.EventChanged )
            
        
        if body == '': xml = ''
        else: ( xml, html ) = yaml.safe_load( body )
        
        self._body = DraftBodyPanel( self, xml )
        self.Bind( wx.richtext.EVT_RICHTEXT_STYLE_CHANGED, self.EventChanged )
        self.Bind( wx.richtext.EVT_RICHTEXT_CHARACTER, self.EventChanged )
        self.Bind( wx.richtext.EVT_RICHTEXT_RETURN, self.EventChanged )
        self.Bind( wx.richtext.EVT_RICHTEXT_DELETE, self.EventChanged )
        
        self._attachments = wx.TextCtrl( self, value = os.linesep.join( [ hash.encode( 'hex' ) for hash in attachment_hashes ] ), style = wx.TE_MULTILINE )
        self._attachments.Bind( wx.EVT_KEY_DOWN, self.EventChanged )
        # do thumbnails later! for now, do a listbox or whatever
        
        self._send = wx.Button( self, label = 'send' )
        self._send.Bind( wx.EVT_BUTTON, self.EventSend )
        self._send.SetForegroundColour( ( 0, 128, 0 ) )
        if len( contacts_to ) == 0: self._send.Disable()
        
        self._delete_draft = wx.Button( self, label = 'delete' )
        self._delete_draft.Bind( wx.EVT_BUTTON, self.EventDeleteDraft )
        self._delete_draft.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._save_draft = wx.Button( self, label = 'save' )
        self._save_draft.Bind( wx.EVT_BUTTON, self.EventSaveDraft )
        
        if is_new:
            
            self._draft_changed = True
            self._delete_draft.SetLabel( 'discard' )
            
        else:
            
            self._draft_changed = False
            self._save_draft.SetLabel( 'saved' )
            self._save_draft.Disable()
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._from, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not self._draft_message.IsReply():
            
            recipients_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            recipients_hbox.AddF( wx.StaticText( self._to_panel, label = 'recipients can see each other' ), CC.FLAGS_MIXED )
            recipients_hbox.AddF( self._recipients_visible, CC.FLAGS_MIXED )
            
            self._to_panel.AddF( self._recipients_list, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._to_panel.AddF( self._new_recipient, CC.FLAGS_LONE_BUTTON )
            self._to_panel.AddF( recipients_hbox, CC.FLAGS_BUTTON_SIZER )
            
            self._subject_panel.AddF( self._subject, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( self._to_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._subject_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.AddF( self._body, CC.FLAGS_EXPAND_BOTH_WAYS )
        #vbox.AddF( wx.StaticText( self, label = 'attachment hashes:' ), CC.FLAGS_MIXED )
        #vbox.AddF( self._attachments, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._attachments.Hide()
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        button_hbox.AddF( self._send, CC.FLAGS_MIXED )
        button_hbox.AddF( self._delete_draft, CC.FLAGS_MIXED )
        button_hbox.AddF( self._save_draft, CC.FLAGS_MIXED )
        
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        HydrusGlobals.client_controller.sub( self, 'AddContact', 'add_contact' )
        HydrusGlobals.client_controller.sub( self, 'DraftSaved', 'draft_saved' )
        
        if not self._draft_message.IsReply(): wx.CallAfter( self._new_recipient.SetFocus )
        
    
    def _GetDraftMessage( self ):
        
        ( self._draft_key, self._conversation_key, subject, self._contact_from, contacts_to, recipients_visible, body, attachment_hashes ) = self._draft_message.GetInfo()
        
        if not self._draft_message.IsReply():
            
            subject = self._subject.GetValue()
            contacts_to = [ self._recipients_list.GetItemText( i ) for i in range( self._recipients_list.GetItemCount() ) ]
            recipients_visible = self._recipients_visible.GetValue()
            
        
        body = self._body.GetXMLHTML()
        
        try:
            
            raw_attachments = self._attachments.GetValue()
            
            attachment_hashes = [ hash.decode( 'hex' ) for hash in raw_attachments.split( os.linesep ) if hash != '' ]
            
        except:
            
            attachment_hashes = []
            
            wx.MessageBox( 'Could not parse attachments!' )
            
        
        return ClientConstantsMessages.DraftMessage( self._draft_key, self._conversation_key, subject, self._contact_from, contacts_to, recipients_visible, body, attachment_hashes )
        
    
    def AddContact( self, compose_key, name ):
        
        if compose_key == self._compose_key:
            
            index = self._recipients_list.FindItem( -1, name )
            
            if index == -1: self._recipients_list.Append( ( name, ) )
            else: self._recipients_list.DeleteItem( index )
            
            self.EventChanged( None )
            
        
    
    def DraftSaved( self, draft_key, draft_message ):
        
        if draft_key == self._draft_key:
            
            self._draft_changed = False
            
            self._save_draft.SetLabel( 'saved' )
            self._save_draft.Disable()
            
            self._delete_draft.SetLabel( 'delete' )
            
            self._draft_message.Saved()
            
        
    
    def EventChanged( self, event ):
        
        if not self._draft_changed:
            
            self._draft_changed = True
            
            self._send.Enable()
            self._save_draft.Enable()
            
        
        if event is not None: event.Skip()
        
    
    def EventDeleteDraft( self, event ): HydrusGlobals.client_controller.Write( 'delete_draft', self._draft_key )
    
    def EventSend( self, event ):
        
        draft_message = self._GetDraftMessage()
        
        transport_messages = HydrusGlobals.client_controller.Read( 'transport_messages_from_draft', draft_message )
        
        if self._contact_from.GetName() != 'Anonymous':
            
            try:
                
                my_message_depot = HydrusGlobals.client_controller.GetServicesManager().GetService( self._contact_from.GetServiceKey() )
                
                connection = my_message_depot.GetConnection()
                
                my_public_key = self._contact_from.GetPublicKey()
                my_contact_key = self._contact_from.GetContactKey()
                
                for transport_message in transport_messages:
                    
                    packaged_message = HydrusMessageHandling.PackageMessageForDelivery( transport_message, my_public_key )
                    
                    connection.Post( 'message', contact_key = my_contact_key, message = packaged_message )
                    
                    message_key = transport_message.GetMessageKey()
                    
                    status_updates = []
                    
                    for contact_to in transport_message.GetContactsTo():
                        
                        contact_to_key = contact_to.GetContactKey()
                        
                        status_key = hashlib.sha256( contact_to_key + message_key ).digest()
                        
                        status = HydrusMessageHandling.PackageStatusForDelivery( ( message_key, contact_to_key, 'pending' ), my_public_key )
                        
                        status_updates.append( ( status_key, status ) )
                        
                    
                    connection.Post( 'message_statuses', contact_key = my_contact_key, statuses = status_updates )
                    
                
            except:
                
                HydrusData.ShowText( 'The hydrus client could not connect to your message depot, so the message could not be sent!' )
                
                return
                
            
        
        for transport_message in transport_messages: HydrusGlobals.client_controller.Write( 'message', transport_message, forced_status = 'pending' )
        
        draft_key = draft_message.GetDraftKey()
        
        HydrusGlobals.client_controller.Write( 'delete_draft', draft_key )
        
    
    def EventSaveDraft( self, event ):
        
        draft_message = self._GetDraftMessage()
        
        HydrusGlobals.client_controller.Write( 'draft_message', draft_message )
        
    
    def EventRemove( self, event ):
        
        selection = self._recipients_list.GetFirstSelected()
        
        if selection != wx.NOT_FOUND:
            
            self._recipients_list.DeleteItem( selection )
            
            self.EventChanged( None )
            
        
    
    def GetConversationKey( self ): return self._conversation_key
    
    def GetDraftKey( self ): return self._draft_key
    
class MessageHTML( wx.html.HtmlWindow ):
    
    def __init__( self, *args, **kwargs ):
        
        kwargs[ 'style' ] = wx.html.HW_SCROLLBAR_NEVER
        
        wx.html.HtmlWindow.__init__( self, *args, **kwargs )
        
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventScroll )
        
        self.SetRelatedFrame( wx.GetTopLevelParent( self ), '%s' )
        self.SetRelatedStatusBar( 0 )
        
    
    def EventScroll( self, event ):
        
        sw = self.GetParent().GetParent()
        
        sw.GetEventHandler().ProcessEvent( event )
        
    
    def GetClientSize( self ): return self.GetSize()
    
    def OnLinkClicked( self, link ): webbrowser.open( link.GetHref() )
    
    def OnOpeningURL( self, url_type, url, redirect ): return wx.html.HTML_BLOCK
    
class MessagePanel( wx.Panel ):
    
    def __init__( self, parent, message, identity ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( CC.COLOUR_MESSAGE )
        
        self._message = message
        self._identity = identity
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        contact_from = self._message.GetContactFrom()
        
        if contact_from is None: name = 'Anonymous'
        else: name = self._message.GetContactFrom().GetName()
        
        #vbox.AddF( wx.StaticText( self, label = name + ', ' + HC.ConvertTimestampToPrettyAgo( self._message.GetTimestamp() ) ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( ClientGUICommon.AnimatedStaticTextTimestamp( self, name + ', ', HydrusData.ConvertTimestampToPrettyAgo, self._message.GetTimestamp(), '' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        body = self._message.GetBody()
        
        display_body = not ( body is None or body == '' )
        
        if display_body:
            
            self._body_panel = wx.Panel( self )
            
            wx.CallAfter( self.SetBody, body )
            
        else: self._body_panel = wx.StaticText( self, label = 'no body' )
        
        self._message_key = self._message.GetMessageKey()
        destinations = self._message.GetDestinations()
        
        self._destinations_panel = DestinationsPanel( self, self._message_key, destinations, identity )
        
        self._hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._hbox.AddF( self._body_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._hbox.AddF( self._destinations_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.AddF( self._hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        # vbox.AddF( some kind of attachment window! )
        
        self.SetSizer( vbox )
        
    
    def SetBody( self, body ):
        
        with wx.FrozenWindow( self ):
            
            ( width, height ) = self._body_panel.GetClientSize()
            
            body_panel = MessageHTML( self, size = ( width, -1 ) )
            body_panel.SetPage( body )
            
            internal = body_panel.GetInternalRepresentation()
            
            body_panel.SetSize( ( -1, internal.GetHeight() ) )
            
            self._hbox.Replace( self._body_panel, body_panel )
            
            self._body_panel.Close()
            
            self._body_panel = body_panel
            
        
        self.Layout()
        self.GetParent().FitInside()
        
        
    
# here starts the message reboot code

class IMFrame( ClientGUICommon.Frame ):
    
    def __init__( self, parent, me_account, them_account, context ):
        
        def InitialiseControls():
            
            self._me_label = MeLabel( self, me_account ) # maybe these two should be the same, and infer me/them status itself
            self._them_label = ThemLabel( self, them_account )
            self._convo_box = ConvoBox( self, context_key ) # something like this
            self._text_input = ConvoTextInput( self, callable ) # callable should be private method of this, or similar!
            
        
        def PopulateControls():
            
            # could introduce last convo here, or whatever.
            
            pass
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._me_label, CC.FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self, label = ' talking to ' ), CC.FLAGS_MIXED )
            hbox.AddF( self._them_label, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._convo_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._text_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 400, 600 ) ) # this should be remembered, stuck in options
            
        
        me_name = me_account.GetNameBlah()
        them_name = them_account.GetNameBlah()
        
        ClientGUICommon.Frame.__init__( self, parent, title = me_name + ' talking to ' + them_name )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Show( True )
        
    
    def TextInputCallable( self, text ):
        
        pass
        
        # send it to the context, which will report it
        
    '''