import Crypto.PublicKey.RSA
import HydrusConstants as HC
import HydrusEncryption
import HydrusExceptions
import HydrusTags
import ClientConstants as CC
import ClientConstantsMessages
import ClientGUICommon
import ClientGUIDialogs
import collections
import HydrusNATPunch
import itertools
import os
import random
import re
import string
import subprocess
import time
import traceback
import urllib
import wx
import yaml

# Option Enums

ID_NULL = wx.NewId()

ID_TIMER_UPDATE = wx.NewId()

# Hue is generally 200, Sat and Lum changes based on need

COLOUR_SELECTED = wx.Colour( 217, 242, 255 )
COLOUR_SELECTED_DARK = wx.Colour( 1, 17, 26 )
COLOUR_UNSELECTED = wx.Colour( 223, 227, 230 )

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )
FLAGS_BIG_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 8 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

class DialogManage4chanPass( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._token = wx.TextCtrl( self )
            self._pin = wx.TextCtrl( self )
            
            self._status = wx.StaticText( self )
            
            self._SetStatus()
            
            self._reauthenticate = wx.Button( self, label = 'reauthenticate' )
            self._reauthenticate.Bind( wx.EVT_BUTTON, self.EventReauthenticate )
            
            self._ok = wx.Button( self, label = 'Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._token.SetValue( token )
            self._pin.SetValue( pin )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'token' ), FLAGS_MIXED )
            gridbox.AddF( self._token, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'pin' ), FLAGS_MIXED )
            gridbox.AddF( self._pin, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._status, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._reauthenticate, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage 4chan pass' )
        
        ( token, pin, self._timeout ) = HC.app.Read( '4chan_pass' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 240 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _SetStatus( self ):
        
        if self._timeout == 0: label = 'not authenticated'
        elif self._timeout < HC.GetNow(): label = 'timed out'
        else: label = 'authenticated - ' + HC.ConvertTimestampToPrettyExpiry( self._timeout )
        
        self._status.SetLabel( label )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        token = self._token.GetValue()
        pin = self._pin.GetValue()
        
        HC.app.Write( '4chan_pass', token, pin, self._timeout )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventReauthenticate( self, event ):
        
        token = self._token.GetValue()
        pin = self._pin.GetValue()
        
        if token == '' and pin == '':
            
            self._timeout = 0
            
        else:
            
            form_fields = {}
            
            form_fields[ 'act' ] = 'do_login'
            form_fields[ 'id' ] = token
            form_fields[ 'pin' ] = pin
            form_fields[ 'long_login' ] = 'yes'
            
            ( ct, body ) = CC.GenerateMultipartFormDataCTAndBodyFromDict( form_fields )
            
            request_headers = {}
            request_headers[ 'Content-Type' ] = ct
            
            response = HC.http.Request( HC.POST, 'https://sys.4chan.org/auth', request_headers = request_headers, body = body )
            
            self._timeout = HC.GetNow() + 365 * 24 * 3600
            
        
        HC.app.Write( '4chan_pass', token, pin, self._timeout )
        
        self._SetStatus()
        
    
class DialogManageAccountTypes( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
            
            self._ctrl_account_types = ClientGUICommon.SaneListCtrl( self._account_types_panel, 350, [ ( 'title', 120 ), ( 'permissions', -1 ), ( 'max monthly bytes', 120 ), ( 'max monthly requests', 120 ) ] )
            
            self._add = wx.Button( self._account_types_panel, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self._account_types_panel, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete = wx.Button( self._account_types_panel, label = 'delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            self._apply = wx.Button( self, label = 'apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            service = HC.app.Read( 'service', service_identifier )
            
            response = service.Request( HC.GET, 'account_types' )
            
            account_types = response[ 'account_types' ]
            
            self._titles_to_account_types = {}
            
            for account_type in account_types:
                
                title = account_type.GetTitle()
                
                self._titles_to_account_types[ title ] = account_type
                
                permissions = account_type.GetPermissions()
                
                permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                
                ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                
                ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                
                self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                
            
        
        def ArrangeControls():
            
            h_b_box = wx.BoxSizer( wx.HORIZONTAL )
            
            h_b_box.AddF( self._add, FLAGS_MIXED )
            h_b_box.AddF( self._edit, FLAGS_MIXED )
            h_b_box.AddF( self._delete, FLAGS_MIXED )
            
            self._account_types_panel.AddF( self._ctrl_account_types, FLAGS_EXPAND_BOTH_WAYS )
            self._account_types_panel.AddF( h_b_box, FLAGS_BUTTON_SIZERS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._apply, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._account_types_panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage account types' )
        
        self._service_identifier = service_identifier
        
        self._edit_log = []
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        wx.CallAfter( self._apply.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogInputNewAccountType( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                account_type = dlg.GetAccountType()
                
                title = account_type.GetTitle()
                
                permissions = account_type.GetPermissions()
                
                permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                
                ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                
                ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                
                if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                
                self._titles_to_account_types[ title ] = account_type
                
                self._edit_log.append( ( HC.ADD, account_type ) )
                
                self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventDelete( self, event ):
        
        indices = self._ctrl_account_types.GetAllSelected()
        
        titles_about_to_delete = { self._ctrl_account_types.GetClientData( index )[0] for index in indices }
        
        all_titles = set( self._titles_to_account_types.keys() )
        
        titles_can_move_to = list( all_titles - titles_about_to_delete )
        
        if len( titles_can_move_to ) == 0:
            
            wx.MessageBox( 'You cannot delete every account type!' )
            
            return
            
        
        for title in titles_about_to_delete:
            
            with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'what should deleted ' + title + ' accounts become?', titles_can_move_to ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK: title_to_move_to = dlg.GetString()
                else: return
                
            
            self._edit_log.append( ( HC.DELETE, ( title, title_to_move_to ) ) )
            
        
        self._ctrl_account_types.RemoveAllSelected()
        
    
    def EventEdit( self, event ):
        
        indices = self._ctrl_account_types.GetAllSelected()
        
        for index in indices:
            
            title = self._ctrl_account_types.GetClientData( index )[0]
            
            account_type = self._titles_to_account_types[ title ]
            
            with ClientGUIDialogs.DialogInputNewAccountType( self, account_type ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    old_title = title
                    
                    account_type = dlg.GetAccountType()
                    
                    title = account_type.GetTitle()
                    
                    permissions = account_type.GetPermissions()
                    
                    permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                    
                    ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                    
                    ( max_num_bytes_string, max_num_requests_string ) = account_type.GetMaxMonthlyDataString()
                    
                    if old_title != title:
                        
                        if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                        
                        del self._titles_to_account_types[ old_title ]
                        
                    
                    self._titles_to_account_types[ title ] = account_type
                    
                    self._edit_log.append( ( HC.EDIT, ( old_title, account_type ) ) )
                    
                    self._ctrl_account_types.UpdateRow( index, ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        service = HC.app.Read( 'service', self._service_identifier )
        
        service.Request( HC.POST, 'account_types', { 'edit_log' : self._edit_log } )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageBoorus( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._boorus = ClientGUICommon.ListBook( self )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            boorus = HC.app.Read( 'boorus' )
            
            for booru in boorus:
                
                name = booru.GetName()
                
                page_info = ( self._Panel, ( self._boorus, booru ), {} )
                
                self._boorus.AddPage( page_info, name )
                
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._boorus, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage boorus' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new booru\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._boorus.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    booru = CC.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                    
                    self._edit_log.append( ( HC.ADD, name ) )
                    
                    page = self._Panel( self._boorus, booru )
                    
                    self._boorus.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( HC.u( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            booru = booru_panel.GetBooru()
            
            with wx.FileDialog( self, 'select where to export booru', defaultFile = 'booru.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( booru ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        for ( name, page ) in self._boorus.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( name, page.GetBooru() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: HC.app.Write( 'update_boorus', self._edit_log )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            self._edit_log.append( ( HC.DELETE, name ) )
            
            self._boorus.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == CC.Booru:
                    
                    booru = thing
                    
                    name = booru.GetName()
                    
                    if not self._boorus.NameExists( name ):
                        
                        new_booru = CC.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                        
                        self._edit_log.append( ( HC.ADD, name ) )
                        
                        page = self._Panel( self._boorus, new_booru )
                        
                        self._boorus.AddPage( page, name, select = True )
                        
                    
                    page = self._boorus.GetNameToPageDict()[ name ]
                    
                    page.Update( booru )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, booru ):
            
            wx.Panel.__init__( self, parent )
            
            self._booru = booru
            
            ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
            
            def InitialiseControls():
                
                self._booru_panel = ClientGUICommon.StaticBox( self, 'booru' )
                
                #
                
                self._search_panel = ClientGUICommon.StaticBox( self._booru_panel, 'search' )
                
                self._search_url = wx.TextCtrl( self._search_panel )
                self._search_url.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._search_separator = wx.Choice( self._search_panel, choices = [ '+', '&', '%20' ] )
                self._search_separator.Bind( wx.EVT_CHOICE, self.EventHTML )
                
                self._advance_by_page_num = wx.CheckBox( self._search_panel )
                
                self._thumb_classname = wx.TextCtrl( self._search_panel )
                self._thumb_classname.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._example_html_search = wx.StaticText( self._search_panel, style = wx.ST_NO_AUTORESIZE )
                
                #
                
                self._image_panel = ClientGUICommon.StaticBox( self._booru_panel, 'image' )
                
                self._image_info = wx.TextCtrl( self._image_panel )
                self._image_info.Bind( wx.EVT_TEXT, self.EventHTML )
                
                self._image_id = wx.RadioButton( self._image_panel, style = wx.RB_GROUP )
                self._image_id.Bind( wx.EVT_RADIOBUTTON, self.EventHTML )
                
                self._image_data = wx.RadioButton( self._image_panel )
                self._image_data.Bind( wx.EVT_RADIOBUTTON, self.EventHTML )
                
                self._example_html_image = wx.StaticText( self._image_panel, style = wx.ST_NO_AUTORESIZE )
                
                #
                
                self._tag_panel = ClientGUICommon.StaticBox( self._booru_panel, 'tags' )
                
                self._tag_classnames_to_namespaces = wx.ListBox( self._tag_panel, style = wx.LB_SORT )
                self._tag_classnames_to_namespaces.Bind( wx.EVT_LEFT_DCLICK, self.EventRemove )
                
                self._tag_classname = wx.TextCtrl( self._tag_panel )
                self._namespace = wx.TextCtrl( self._tag_panel )
                
                self._add = wx.Button( self._tag_panel, label = 'add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                
                self._example_html_tags = wx.StaticText( self._tag_panel, style = wx.ST_NO_AUTORESIZE )
                
            
            def PopulateControls():
                
                self._search_url.SetValue( search_url )
                
                self._search_separator.Select( self._search_separator.FindString( search_separator ) )
                
                self._advance_by_page_num.SetValue( advance_by_page_num )
                
                self._thumb_classname.SetValue( thumb_classname )
                
                #
                
                if image_id is None:
                    
                    self._image_info.SetValue( image_data )
                    self._image_data.SetValue( True )
                    
                else:
                    
                    self._image_info.SetValue( image_id )
                    self._image_id.SetValue( True )
                    
                
                #
                
                for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items(): self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'search url' ), FLAGS_MIXED )
                gridbox.AddF( self._search_url, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'search tag separator' ), FLAGS_MIXED )
                gridbox.AddF( self._search_separator, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'advance by page num' ), FLAGS_MIXED )
                gridbox.AddF( self._advance_by_page_num, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'thumbnail classname' ), FLAGS_MIXED )
                gridbox.AddF( self._thumb_classname, FLAGS_EXPAND_BOTH_WAYS )
                
                self._search_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._search_panel.AddF( self._example_html_search, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'text' ), FLAGS_MIXED )
                gridbox.AddF( self._image_info, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'id of <img>' ), FLAGS_MIXED )
                gridbox.AddF( self._image_id, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'text of <a>' ), FLAGS_MIXED )
                gridbox.AddF( self._image_data, FLAGS_EXPAND_BOTH_WAYS )
                
                self._image_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._image_panel.AddF( self._example_html_image, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._tag_classname, FLAGS_MIXED )
                hbox.AddF( self._namespace, FLAGS_MIXED )
                hbox.AddF( self._add, FLAGS_MIXED )
                
                self._tag_panel.AddF( self._tag_classnames_to_namespaces, FLAGS_EXPAND_BOTH_WAYS )
                self._tag_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._tag_panel.AddF( self._example_html_tags, FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                self._booru_panel.AddF( self._search_panel, FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._image_panel, FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._tag_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._booru_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
                
            PopulateControls()
            
            ArrangeControls()
            
        
        def _GetInfo( self ):
            
            booru_name = self._booru.GetName()
            
            search_url = self._search_url.GetValue()
            
            search_separator = self._search_separator.GetStringSelection()
            
            advance_by_page_num = self._advance_by_page_num.GetValue()
            
            thumb_classname = self._thumb_classname.GetValue()
            
            if self._image_id.GetValue():
                
                image_id = self._image_info.GetValue()
                image_data = None
                
            else:
                
                image_id = None
                image_data = self._image_info.GetValue()
                
            
            tag_classnames_to_namespaces = { tag_classname : namespace for ( tag_classname, namespace ) in [ self._tag_classnames_to_namespaces.GetClientData( i ) for i in range( self._tag_classnames_to_namespaces.GetCount() ) ] }
            
            return ( booru_name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
        
        def EventAdd( self, event ):
            
            tag_classname = self._tag_classname.GetValue()
            namespace = self._namespace.GetValue()
            
            if tag_classname != '':
                
                self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
                
                self._tag_classname.SetValue( '' )
                self._namespace.SetValue( '' )
                
                self.EventHTML( event )
                
            
        
        def EventHTML( self, event ):
            
            pass
            
        
        def EventRemove( self, event ):
            
            selection = self._tag_classnames_to_namespaces.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                self._tag_classnames_to_namespaces.Delete( selection )
                
                self.EventHTML( event )
                
            
        
        def GetBooru( self ):
            
            ( booru_name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._GetInfo()
            
            return CC.Booru( booru_name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
        
        def HasChanges( self ):
            
            ( booru_name, my_search_url, my_search_separator, my_advance_by_page_num, my_thumb_classname, my_image_id, my_image_data, my_tag_classnames_to_namespaces ) = self._GetInfo()
            
            ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = self._booru.GetData()
            
            if search_url != my_search_url: return True
            
            if search_separator != my_search_separator: return True
            
            if advance_by_page_num != my_advance_by_page_num: return True
            
            if thumb_classname != my_thumb_classname: return True
            
            if image_id != my_image_id: return True
            
            if image_data != my_image_data: return True
            
            if tag_classnames_to_namespaces != my_tag_classnames_to_namespaces: return True
            
            return False
            
        
        def Update( self, booru ):
            
            ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
            
            self._search_url.SetValue( search_url )
            
            self._search_separator.Select( self._search_separator.FindString( search_separator ) )
            
            self._advance_by_page_num.SetValue( advance_by_page_num )
            
            self._thumb_classname.SetValue( thumb_classname )
            
            if image_id is None:
                
                self._image_info.SetValue( image_data )
                self._image_data.SetValue( True )
                
            else:
                
                self._image_info.SetValue( image_id )
                self._image_id.SetValue( True )
                
            
            self._tag_classnames_to_namespaces.Clear()
            
            for ( tag_classname, namespace ) in tag_classnames_to_namespaces.items(): self._tag_classnames_to_namespaces.Append( tag_classname + ' : ' + namespace, ( tag_classname, namespace ) )
            
        
    
class DialogManageContacts( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._contacts = ClientGUICommon.ListBook( self )
            
            self._contacts.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventContactChanging )
            self._contacts.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventContactChanged )
            
            self._add_contact_address = wx.Button( self, label = 'add by contact address' )
            self._add_contact_address.Bind( wx.EVT_BUTTON, self.EventAddByContactAddress )
            self._add_contact_address.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._add_manually = wx.Button( self, label = 'add manually' )
            self._add_manually.Bind( wx.EVT_BUTTON, self.EventAddManually )
            self._add_manually.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._edit_log = []
            
            ( identities, contacts, deletable_names ) = HC.app.Read( 'identities_and_contacts' )
            
            self._deletable_names = deletable_names
            
            for identity in identities:
                
                name = identity.GetName()
                
                page_info = ( self._Panel, ( self._contacts, identity ), { 'is_identity' : True } )
                
                self._contacts.AddPage( page_info, ' identity - ' + name )
                
            
            for contact in contacts:
                
                name = contact.GetName()
                
                page_info = ( self._Panel, ( self._contacts, contact ), { 'is_identity' : False } )
                
                self._contacts.AddPage( page_info, name )
                
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add_manually, FLAGS_MIXED )
            add_remove_hbox.AddF( self._add_contact_address, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._contacts, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage contacts' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
        self.EventContactChanged( None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentContactIsValid( self ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            contact = contact_panel.GetContact()
            
            old_name = self._contacts.GetCurrentName()
            name = contact.GetName()
            
            if name != old_name and ' identity - ' + name != old_name:
                
                if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identity - ' + name ) or name == 'Anonymous': raise Exception( 'That name is already in use!' )
                
                if old_name.startswith( ' identity - ' ): self._contacts.RenamePage( old_name, ' identity - ' + name )
                else: self._contacts.RenamePage( old_name, name )
                
            
        
    
    def EventAddByContactAddress( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        with wx.TextEntryDialog( self, 'Enter contact\'s address in the form contact_key@hostname:port' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                contact_address = dlg.GetValue()
                
                try:
                    
                    ( contact_key_encoded, address ) = contact_address.split( '@' )
                    
                    contact_key = contact_key_encoded.decode( 'hex' )
                    
                    ( host, port ) = address.split( ':' )
                    
                    port = int( port )
                    
                except: raise Exception( 'Could not parse the address!' )
                
                name = contact_key_encoded
                
                contact = ClientConstantsMessages.Contact( None, name, host, port )
                
                try:
                    
                    connection = contact.GetConnection()
                    
                    public_key = connection.Get( 'public_key', contact_key = contact_key.encode( 'hex' ) )
                    
                except: raise Exception( 'Could not fetch the contact\'s public key from the address:' + os.linesep + traceback.format_exc() )
                
                contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                
                self._edit_log.append( ( HC.ADD, contact ) )
                
                page = self._Panel( self._contacts, contact, is_identity = False )
                
                self._deletable_names.add( name )
                
                self._contacts.AddPage( page, name, select = True )
                
            
        
    
    def EventAddManually( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        with wx.TextEntryDialog( self, 'Enter new contact\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                name = dlg.GetValue()
                
                if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identity - ' + name ) or name == 'Anonymous': raise Exception( 'That name is already in use!' )
                
                if name == '': raise Exception( 'Please enter a nickname for the service.' )
                
                public_key = None
                host = 'hostname'
                port = 45871
                
                contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                
                self._edit_log.append( ( HC.ADD, contact ) )
                
                page = self._Panel( self._contacts, contact, is_identity = False )
                
                self._deletable_names.add( name )
                
                self._contacts.AddPage( page, name, select = True )
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventContactChanged( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            old_name = contact_panel.GetOriginalName()
            
            if old_name in self._deletable_names: self._remove.Enable()
            else: self._remove.Disable()
            
        
    
    def EventContactChanging( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            event.Veto()
            
        
    
    def EventExport( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            name = self._contacts.GetCurrentName()
            
            contact = contact_panel.GetContact()
            
            try:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = 'contact.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        for ( name, page ) in self._contacts.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( page.GetOriginalName(), page.GetContact() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: HC.app.Write( 'update_contacts', self._edit_log )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    # this isn't used yet!
    def EventRemove( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            name = contact_panel.GetOriginalName()
            
            self._edit_log.append( ( HC.DELETE, name ) )
            
            self._contacts.DeleteCurrentPage()
            
            self._deletable_names.discard( name )
            
        
    
    def Import( self, paths ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                obj = yaml.safe_load( file )
                
                if type( obj ) == ClientConstantsMessages.Contact:
                    
                    contact = obj
                    
                    name = contact.GetName()
                    
                    if self._contacts.NameExists( name ) or self._contacts.NameExists( ' identities - ' + name ) or name == 'Anonymous':
                        
                        message = 'There already exists a contact or identity with the name ' + name + '. Do you want to overwrite, or make a new contact?'
                        
                        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'overwrite', no_label = 'make new' ) as dlg:
                            
                            if True:
                                
                                name_to_page_dict = self._contacts.GetNameToPageDict()
                                
                                if name in name_to_page_dict: page = name_to_page_dict[ name ]
                                else: page = name_to_page_dict[ ' identities - ' + name ]
                                
                                page.Update( contact )
                                
                            else:
                                
                                while self._contacts.NameExists( name ) or self._contacts.NameExists( ' identities - ' + name ) or name == 'Anonymous': name = name + HC.u( random.randint( 0, 9 ) )
                                
                                ( public_key, old_name, host, port ) = contact.GetInfo()
                                
                                new_contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                                
                                self._edit_log.append( ( HC.ADD, contact ) )
                                
                                self._deletable_names.add( name )
                                
                                page = self._Panel( self._contacts, contact, False )
                                
                                self._contacts.AddPage( page, name, select = True )
                                
                            
                        
                    else:
                        
                        ( public_key, old_name, host, port ) = contact.GetInfo()
                        
                        new_contact = ClientConstantsMessages.Contact( public_key, name, host, port )
                        
                        self._edit_log.append( ( HC.ADD, contact ) )
                        
                        self._deletable_names.add( name )
                        
                        page = self._Panel( self._contacts, contact, False )
                        
                        self._contacts.AddPage( page, name, select = True )
                        
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, contact, is_identity ):
            
            wx.Panel.__init__( self, parent )
            
            self._contact = contact
            self._is_identity = is_identity
            
            ( public_key, name, host, port ) = contact.GetInfo()
            
            contact_key = contact.GetContactKey()
            
            def InitialiseControls():
                
                self._contact_panel = ClientGUICommon.StaticBox( self, 'contact' )
                
                self._name = wx.TextCtrl( self._contact_panel )
                
                self._contact_address = wx.TextCtrl( self._contact_panel )
                
                self._public_key = wx.TextCtrl( self._contact_panel, style = wx.TE_MULTILINE )
                
            
            def PopulateControls():
                
                self._name.SetValue( name )
                
                contact_address = host + ':' + HC.u( port )
                
                if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
                
                self._contact_address.SetValue( contact_address )
                
                if public_key is not None: self._public_key.SetValue( public_key )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'name' ), FLAGS_MIXED )
                gridbox.AddF( self._name, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'contact address' ), FLAGS_MIXED )
                gridbox.AddF( self._contact_address, FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'public key' ), FLAGS_MIXED )
                gridbox.AddF( self._public_key, FLAGS_EXPAND_BOTH_WAYS )
                
                self._contact_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._contact_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def _GetInfo( self ):
            
            public_key = self._public_key.GetValue()
            
            if public_key == '': public_key = None
            
            name = self._name.GetValue()
            
            contact_address = self._contact_address.GetValue()
            
            try:
                
                if '@' in contact_address: ( contact_key, address ) = contact_address.split( '@' )
                else: address = contact_address
                
                ( host, port ) = address.split( ':' )
                
                try: port = int( port )
                except:
                    
                    port = 45871
                    
                    wx.MessageBox( 'Could not parse the port!' )
                    
                
            except:
                
                host = 'hostname'
                port = 45871
                
                wx.MessageBox( 'Could not parse the contact\'s address!' )
                
            
            return [ public_key, name, host, port ]
            
        
        def GetContact( self ):
            
            [ public_key, name, host, port ] = self._GetInfo()
            
            return ClientConstantsMessages.Contact( public_key, name, host, port )
            
        
        def GetOriginalName( self ): return self._contact.GetName()
        
        def HasChanges( self ):
            
            [ my_public_key, my_name, my_host, my_port ] = self._GetInfo()
            
            [ public_key, name, host, port ] = self._contact.GetInfo()
            
            if my_public_key != public_key: return True
            
            if my_name != name: return True
            
            if my_host != host: return True
            
            if my_port != port: return True
            
            return False
            
        
        def Update( self, contact ):
            
            ( public_key, name, host, port ) = contact.GetInfo()
            
            contact_key = contact.GetContactKey()
            
            self._name.SetValue( name )
            
            contact_address = host + ':' + HC.u( port )
            
            if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
            
            self._contact_address.SetValue( contact_address )
            
            if public_key is None: public_key = ''
            
            self._public_key.SetValue( public_key )
            
        
    
class DialogManageImageboards( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._sites = ClientGUICommon.ListBook( self )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._edit_log = []
            
            sites = HC.app.Read( 'imageboards' )
            
            for ( name, imageboards ) in sites:
                
                page_info = ( self._Panel, ( self._sites, imageboards ), {} )
                
                self._sites.AddPage( page_info, name )
                
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._sites, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage imageboards' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new site\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._sites.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    self._edit_log.append( ( HC.ADD, name ) )
                    
                    page = self._Panel( self._sites, [] )
                    
                    self._sites.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( HC.u( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            imageboards = site_panel.GetImageboards()
            
            dict = { name : imageboards }
            
            with wx.FileDialog( self, 'select where to export site', defaultFile = 'site.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( dict ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        for ( name, page ) in self._sites.GetNameToPageDict().items():
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( name, page.GetChanges() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: HC.app.Write( 'update_imageboards', self._edit_log )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            self._edit_log.append( ( HC.DELETE, name ) )
            
            self._sites.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == dict:
                    
                    ( name, imageboards ) = thing.items()[0]
                    
                    if not self._sites.NameExists( name ):
                        
                        self._edit_log.append( ( HC.ADD, name ) )
                        
                        page = self._Panel( self._sites, [] )
                        
                        self._sites.AddPage( page, name, select = True )
                        
                    
                    page = self._sites.GetNameToPageDict()[ name ]
                    
                    for imageboard in imageboards:
                        
                        if type( imageboard ) == CC.Imageboard: page.UpdateImageboard( imageboard )
                        
                    
                elif type( thing ) == CC.Imageboard:
                    
                    imageboard = thing
                    
                    page = self._sites.GetCurrentPage()
                    
                    page.UpdateImageboard( imageboard )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, imageboards ):
            
            wx.Panel.__init__( self, parent )
            
            def InitialiseControls():
                
                self._site_panel = ClientGUICommon.StaticBox( self, 'site' )
                
                self._imageboards = ClientGUICommon.ListBook( self._site_panel )
                
                self._add = wx.Button( self._site_panel, label = 'add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                self._add.SetForegroundColour( ( 0, 128, 0 ) )
                
                self._remove = wx.Button( self._site_panel, label = 'remove' )
                self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
                self._remove.SetForegroundColour( ( 128, 0, 0 ) )
                
                self._export = wx.Button( self._site_panel, label = 'export' )
                self._export.Bind( wx.EVT_BUTTON, self.EventExport )
                
            
            def PopulateControls():
                
                self._edit_log = []
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    page_info = ( self._Panel, ( self._imageboards, imageboard ), {} )
                    
                    self._imageboards.AddPage( page_info, name )
                    
                
            
            def ArrangeControls():
                
                add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
                add_remove_hbox.AddF( self._add, FLAGS_MIXED )
                add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
                add_remove_hbox.AddF( self._export, FLAGS_MIXED )
                
                self._site_panel.AddF( self._imageboards, FLAGS_EXPAND_BOTH_WAYS )
                self._site_panel.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._site_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        def EventAdd( self, event ):
            
            with wx.TextEntryDialog( self, 'Enter new imageboard\'s name' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try:
                        
                        name = dlg.GetValue()
                        
                        if self._imageboards.NameExists( name ): raise Exception( 'That name is already in use!' )
                        
                        if name == '': raise Exception( 'Please enter a nickname for the service.' )
                        
                        imageboard = CC.Imageboard( name, '', 60, [], {} )
                        
                        self._edit_log.append( ( HC.ADD, name ) )
                        
                        page = self._Panel( self._imageboards, imageboard )
                        
                        self._imageboards.AddPage( page, name, select = True )
                        
                    except Exception as e:
                        
                        wx.MessageBox( HC.u( e ) )
                        
                        self.EventAdd( event )
                        
                    
                
            
        
        def EventExport( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                imageboard = imageboard_panel.GetImageboard()
                
                with wx.FileDialog( self, 'select where to export imageboard', defaultFile = 'imageboard.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( imageboard ) )
                        
                    
                
            
        
        def EventRemove( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                name = self._imageboards.GetCurrentName()
                
                self._edit_log.append( ( HC.DELETE, name ) )
                
                self._imageboards.DeleteCurrentPage()
                
            
        
        def GetChanges( self ):
            
            for page in self._imageboards.GetNameToPageDict().values():
                
                if page.HasChanges(): self._edit_log.append( ( HC.EDIT, page.GetImageboard() ) )
                
            
            return self._edit_log
            
        
        def GetImageboards( self ): return [ page.GetImageboard() for page in self._imageboards.GetNameToPageDict().values() ]
        
        def HasChanges( self ): return len( self._edit_log ) > 0 or True in ( page.HasChanges() for page in self._imageboards.GetNameToPageDict().values() )
        
        def UpdateImageboard( self, imageboard ):
            
            name = imageboard.GetName()
            
            if not self._imageboards.NameExists( name ):
                
                new_imageboard = CC.Imageboard( name, '', 60, [], {} )
                
                self._edit_log.append( ( HC.ADD, name ) )
                
                page = self._Panel( self._imageboards, new_imageboard )
                
                self._imageboards.AddPage( page, name, select = True )
                
            
            page = self._imageboards.GetNameToPageDict()[ name ]
            
            page.Update( imageboard )
            
        
        class _Panel( wx.Panel ):
            
            def __init__( self, parent, imageboard ):
                
                wx.Panel.__init__( self, parent )
                
                self._imageboard = imageboard
                
                ( post_url, flood_time, form_fields, restrictions ) = self._imageboard.GetBoardInfo()
                
                def InitialiseControls():
                    
                    self._imageboard_panel = ClientGUICommon.StaticBox( self, 'imageboard' )
                    
                    #
                    
                    self._basic_info_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'basic info' )
                    
                    self._post_url = wx.TextCtrl( self._basic_info_panel )
                    
                    self._flood_time = wx.SpinCtrl( self._basic_info_panel, min = 5, max = 1200 )
                    
                    #
                    
                    self._form_fields_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'form fields' )
                    
                    self._form_fields = ClientGUICommon.SaneListCtrl( self._form_fields_panel, 350, [ ( 'name', 120 ), ( 'type', 120 ), ( 'default', -1 ), ( 'editable', 120 ) ] )
                    
                    self._add = wx.Button( self._form_fields_panel, label = 'add' )
                    self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
                    
                    self._edit = wx.Button( self._form_fields_panel, label = 'edit' )
                    self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
                    
                    self._delete = wx.Button( self._form_fields_panel, label = 'delete' )
                    self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
                    
                    #
                    
                    self._restrictions_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'restrictions' )
                    
                    self._min_resolution = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'min resolution', num_dimensions = 2 )
                    
                    self._max_resolution = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'max resolution', num_dimensions = 2 )
                    
                    self._max_file_size = ClientGUICommon.NoneableSpinCtrl( self._restrictions_panel, 'max file size (KB)', multiplier = 1024 )
                    
                    self._allowed_mimes_panel = ClientGUICommon.StaticBox( self._restrictions_panel, 'allowed mimes' )
                    
                    self._mimes = wx.ListBox( self._allowed_mimes_panel )
                    
                    self._mime_choice = wx.Choice( self._allowed_mimes_panel )
                    
                    self._add_mime = wx.Button( self._allowed_mimes_panel, label = 'add' )
                    self._add_mime.Bind( wx.EVT_BUTTON, self.EventAddMime )
                    
                    self._remove_mime = wx.Button( self._allowed_mimes_panel, label = 'remove' )
                    self._remove_mime.Bind( wx.EVT_BUTTON, self.EventRemoveMime )
                    
                
                def PopulateControls():
                    
                    #
                    
                    self._post_url.SetValue( post_url )
                    
                    self._flood_time.SetRange( 5, 1200 )
                    self._flood_time.SetValue( flood_time )
                    
                    #
                    
                    for ( name, type, default, editable ) in form_fields:
                        
                        self._form_fields.Append( ( name, CC.field_string_lookup[ type ], HC.u( default ), HC.u( editable ) ), ( name, type, default, editable ) )
                        
                    
                    #
                    
                    if CC.RESTRICTION_MIN_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MIN_RESOLUTION ]
                    else: value = None
                    
                    self._min_resolution.SetValue( value )
                    
                    if CC.RESTRICTION_MAX_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MAX_RESOLUTION ]
                    else: value = None
                    
                    self._max_resolution.SetValue( value )
                    
                    if CC.RESTRICTION_MAX_FILE_SIZE in restrictions: value = restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ]
                    else: value = None
                    
                    self._max_file_size.SetValue( value )
                    
                    if CC.RESTRICTION_ALLOWED_MIMES in restrictions: mimes = restrictions[ CC.RESTRICTION_ALLOWED_MIMES ]
                    else: mimes = []
                    
                    for mime in mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                    
                    for mime in HC.ALLOWED_MIMES: self._mime_choice.Append( HC.mime_string_lookup[ mime ], mime )
                    
                    self._mime_choice.SetSelection( 0 )
                    
                
                def ArrangeControls():
                    
                    self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                    
                    #
                    
                    gridbox = wx.FlexGridSizer( 0, 2 )
                    
                    gridbox.AddGrowableCol( 1, 1 )
                    
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label = 'POST URL' ), FLAGS_MIXED )
                    gridbox.AddF( self._post_url, FLAGS_EXPAND_BOTH_WAYS )
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label = 'flood time' ), FLAGS_MIXED )
                    gridbox.AddF( self._flood_time, FLAGS_EXPAND_BOTH_WAYS )
                    
                    self._basic_info_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    #
                    
                    h_b_box = wx.BoxSizer( wx.HORIZONTAL )
                    h_b_box.AddF( self._add, FLAGS_MIXED )
                    h_b_box.AddF( self._edit, FLAGS_MIXED )
                    h_b_box.AddF( self._delete, FLAGS_MIXED )
                    
                    self._form_fields_panel.AddF( self._form_fields, FLAGS_EXPAND_BOTH_WAYS )
                    self._form_fields_panel.AddF( h_b_box, FLAGS_BUTTON_SIZERS )
                    
                    #
                    
                    mime_buttons_box = wx.BoxSizer( wx.HORIZONTAL )
                    mime_buttons_box.AddF( self._mime_choice, FLAGS_MIXED )
                    mime_buttons_box.AddF( self._add_mime, FLAGS_MIXED )
                    mime_buttons_box.AddF( self._remove_mime, FLAGS_MIXED )
                    
                    self._allowed_mimes_panel.AddF( self._mimes, FLAGS_EXPAND_BOTH_WAYS )
                    self._allowed_mimes_panel.AddF( mime_buttons_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    self._restrictions_panel.AddF( self._min_resolution, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_resolution, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_file_size, FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._allowed_mimes_panel, FLAGS_EXPAND_BOTH_WAYS )
                    
                    #
                    
                    self._imageboard_panel.AddF( self._basic_info_panel, FLAGS_EXPAND_PERPENDICULAR )
                    self._imageboard_panel.AddF( self._form_fields_panel, FLAGS_EXPAND_BOTH_WAYS )
                    self._imageboard_panel.AddF( self._restrictions_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                    vbox = wx.BoxSizer( wx.VERTICAL )
                    
                    vbox.AddF( self._imageboard_panel, FLAGS_EXPAND_BOTH_WAYS )
                    
                    self.SetSizer( vbox )
                    
                
                InitialiseControls()
                
                PopulateControls()
                
                ArrangeControls()
                
            
            def _GetInfo( self ):
                
                imageboard_name = self._imageboard.GetName()
                
                post_url = self._post_url.GetValue()
                
                flood_time = self._flood_time.GetValue()
                
                form_fields = self._form_fields.GetClientData()
                
                restrictions = {}
                
                value = self._min_resolution.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MIN_RESOLUTION ] = value
                
                value = self._max_resolution.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MAX_RESOLUTION ] = value
                
                value = self._max_file_size.GetValue()
                if value is not None: restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ] = value
                
                mimes = [ self._mimes.GetClientData( i ) for i in range( self._mimes.GetCount() ) ]
                
                if len( mimes ) > 0: restrictions[ CC.RESTRICTION_ALLOWED_MIMES ] = mimes
                
                return ( imageboard_name, post_url, flood_time, form_fields, restrictions )
                
            
            def EventAdd( self, event ):
                
                with ClientGUIDialogs.DialogInputNewFormField( self ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( name, type, default, editable ) = dlg.GetFormField()
                        
                        if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]:
                            
                            wx.MessageBox( 'There is already a field named ' + name )
                            
                            self.EventAdd( event )
                            
                            return
                            
                        
                        self._form_fields.Append( ( name, CC.field_string_lookup[ type ], HC.u( default ), HC.u( editable ) ), ( name, type, default, editable ) )
                        
                    
                
            
            def EventAddMime( self, event ):
                
                selection = self._mime_choice.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    mime = self._mime_choice.GetClientData( selection )
                    
                    existing_mimes = [ self._mimes.GetClientData( i ) for i in range( self._mimes.GetCount() ) ]
                    
                    if mime not in existing_mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                    
                
            
            def EventDelete( self, event ): self._form_fields.RemoveAllSelected()
            
            def EventRemoveMime( self, event ):
                
                selection = self._mimes.GetSelection()
                
                if selection != wx.NOT_FOUND: self._mimes.Delete( selection )
                
            
            def EventEdit( self, event ):
                
                indices = self._form_fields.GetAllSelected()
                
                for index in indices:
                    
                    ( name, type, default, editable ) = self._form_fields.GetClientData( index )
                    
                    form_field = ( name, type, default, editable )
                    
                    with ClientGUIDialogs.DialogInputNewFormField( self, form_field ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            old_name = name
                            
                            ( name, type, default, editable ) = dlg.GetFormField()
                            
                            if old_name != name:
                                
                                if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]: raise Exception( 'You already have a form field called ' + name + '; delete or edit that one first' )
                                
                            
                            self._form_fields.UpdateRow( index, ( name, CC.field_string_lookup[ type ], HC.u( default ), HC.u( editable ) ), ( name, type, default, editable ) )
                            
                        
                    
                
            
            def GetImageboard( self ):
                
                ( name, post_url, flood_time, form_fields, restrictions ) = self._GetInfo()
                
                return CC.Imageboard( name, post_url, flood_time, form_fields, restrictions )
                
            
            def HasChanges( self ):
                
                ( my_name, my_post_url, my_flood_time, my_form_fields, my_restrictions ) = self._GetInfo()
                
                ( post_url, flood_time, form_fields, restrictions ) = self._imageboard.GetBoardInfo()
                
                if post_url != my_post_url: return True
                
                if flood_time != my_flood_time: return True
                
                if set( [ tuple( item ) for item in form_fields ] ) != set( [ tuple( item ) for item in my_form_fields ] ): return True
                
                if restrictions != my_restrictions: return True
                
                return False
                
            
            def Update( self, imageboard ):
                
                ( post_url, flood_time, form_fields, restrictions ) = imageboard.GetBoardInfo()
                
                self._post_url.SetValue( post_url )
                self._flood_time.SetValue( flood_time )
                
                self._form_fields.ClearAll()
                
                self._form_fields.InsertColumn( 0, 'name', width = 120 )
                self._form_fields.InsertColumn( 1, 'type', width = 120 )
                self._form_fields.InsertColumn( 2, 'default' )
                self._form_fields.InsertColumn( 3, 'editable', width = 120 )
                
                self._form_fields.setResizeColumn( 3 ) # default
                
                for ( name, type, default, editable ) in form_fields:
                    
                    self._form_fields.Append( ( name, CC.field_string_lookup[ type ], HC.u( default ), HC.u( editable ) ), ( name, type, default, editable ) )
                    
                
                if CC.RESTRICTION_MIN_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MIN_RESOLUTION ]
                else: value = None
                
                self._min_resolution.SetValue( value )
                
                if CC.RESTRICTION_MAX_RESOLUTION in restrictions: value = restrictions[ CC.RESTRICTION_MAX_RESOLUTION ]
                else: value = None
                
                self._max_resolution.SetValue( value )
                
                if CC.RESTRICTION_MAX_FILE_SIZE in restrictions: value = restrictions[ CC.RESTRICTION_MAX_FILE_SIZE ]
                else: value = None
                
                self._max_file_size.SetValue( value )
                
                self._mimes.Clear()
                
                if CC.RESTRICTION_ALLOWED_MIMES in restrictions: mimes = restrictions[ CC.RESTRICTION_ALLOWED_MIMES ]
                else: mimes = []
                
                for mime in mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                
            
        
    
class DialogManageImportFolders( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._import_folders = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'path', -1 ), ( 'type', 120 ), ( 'check period', 120 ), ( 'local tag', 120 ) ] )
            
            self._import_folders.SetMinSize( ( 780, 360 ) )
            
            self._add_button = wx.Button( self, label = 'add' )
            self._add_button.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit_button = wx.Button( self, label = 'edit' )
            self._edit_button.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete_button = wx.Button( self, label = 'delete' )
            self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._original_import_folders = HC.app.Read( 'import_folders' )
            
            for ( path, details ) in self._original_import_folders:
                
                type = details[ 'type' ]
                check_period = details[ 'check_period' ]
                local_tag = details[ 'local_tag' ]
                
                ( pretty_type, pretty_check_period, pretty_local_tag ) = self._GetPrettyVariables( type, check_period, local_tag )
                
                self._import_folders.Append( ( path, pretty_type, pretty_check_period, pretty_local_tag ), ( path, type, check_period, local_tag ) )
                
            
        
        def ArrangeControls():
            
            file_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            file_buttons.AddF( self._add_button, FLAGS_MIXED )
            file_buttons.AddF( self._edit_button, FLAGS_MIXED )
            file_buttons.AddF( self._delete_button, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_MIXED )
            buttons.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._import_folders, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( file_buttons, FLAGS_BUTTON_SIZERS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage import folders' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self._AddFolders ) )
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _AddFolder( self, path ):
        
        all_existing_client_data = self._import_folders.GetClientData()
        
        if path not in ( existing_path for ( existing_path, type, check_period, local_tag ) in all_existing_client_data ):
            
            type = HC.IMPORT_FOLDER_TYPE_SYNCHRONISE
            check_period = 15 * 60
            local_tag = None
            
            with DialogManageImportFoldersEdit( self, path, type, check_period, local_tag ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( path, type, check_period, local_tag ) = dlg.GetInfo()
                    
                    ( pretty_type, pretty_check_period, pretty_local_tag ) = self._GetPrettyVariables( type, check_period, local_tag )
                    
                    self._import_folders.Append( ( path, pretty_type, pretty_check_period, pretty_local_tag ), ( path, type, check_period, local_tag ) )
                    
                
            
        
    
    def _AddFolders( self, paths ):
        
        for path in paths:
            
            if os.path.isdir( path ): self._AddFolder( path )
            
        
    
    def _GetPrettyVariables( self, type, check_period, local_tag ):
        
        if type == HC.IMPORT_FOLDER_TYPE_DELETE: pretty_type = 'delete'
        elif type == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: pretty_type = 'synchronise'
        
        pretty_check_period = HC.u( check_period / 60 ) + ' minutes'
        
        if local_tag == None: pretty_local_tag = ''
        else: pretty_local_tag = local_tag
        
        return ( pretty_type, pretty_check_period, pretty_local_tag )
        
    
    def EventAdd( self, event ):
        
        with wx.DirDialog( self, 'Select a folder to add.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._AddFolder( path )
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventDelete( self, event ): self._import_folders.RemoveAllSelected()
    
    def EventEdit( self, event ):
        
        indices = self._import_folders.GetAllSelected()
        
        for index in indices:
            
            ( path, type, check_period, local_tag ) = self._import_folders.GetClientData( index )
            
            with DialogManageImportFoldersEdit( self, path, type, check_period, local_tag ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( path, type, check_period, local_tag ) = dlg.GetInfo()
                    
                    ( pretty_type, pretty_check_period, pretty_local_tag ) = self._GetPrettyVariables( type, check_period, local_tag )
                    
                    self._import_folders.UpdateRow( index, ( path, pretty_type, pretty_check_period, pretty_local_tag ), ( path, type, check_period, local_tag ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        client_data = self._import_folders.GetClientData()
        
        original_paths_to_details = dict( self._original_import_folders )
        
        import_folders = []
        
        for ( path, type, check_period, local_tag ) in client_data:
            
            if path in original_paths_to_details: details = original_paths_to_details[ path ]
            else: details = { 'last_checked' : 0, 'cached_imported_paths' : set(), 'failed_imported_paths' : set() }
            
            details[ 'type' ] = type
            details[ 'check_period' ] = check_period
            details[ 'local_tag'] = local_tag
            
            import_folders.append( ( path, details ) )
            
        
        HC.app.Write( 'import_folders', import_folders )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageImportFoldersEdit( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, path, type, check_period, local_tag ):
        
        def InitialiseControls():
            
            self._path = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            self._type = ClientGUICommon.BetterChoice( self )
            self._type.Append( 'delete', HC.IMPORT_FOLDER_TYPE_DELETE )
            self._type.Append( 'synchronise', HC.IMPORT_FOLDER_TYPE_SYNCHRONISE )
            message = '''delete - try to import all files in folder and delete them if they succeed

synchronise - try to import all new files in folder'''
            self._type.SetToolTipString( message )
            
            self._check_period = wx.SpinCtrl( self )
            
            self._local_tag = wx.TextCtrl( self )
            self._local_tag.SetToolTipString( 'add this tag on the local tag service to anything imported from the folder' )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._path.SetPath( path )
            
            self._type.Select( type )
            
            self._check_period.SetRange( 3, 180 )
            
            self._check_period.SetValue( check_period / 60 )
            
            if local_tag is not None: self._local_tag.SetValue( local_tag )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'path:' ), FLAGS_MIXED )
            gridbox.AddF( self._path, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'type:' ), FLAGS_MIXED )
            gridbox.AddF( self._type, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'check period (minutes):' ), FLAGS_MIXED )
            gridbox.AddF( self._check_period, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'local tag:' ), FLAGS_MIXED )
            gridbox.AddF( self._local_tag, FLAGS_EXPAND_BOTH_WAYS )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_MIXED )
            buttons.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 640, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'edit import folder' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetInfo( self ):
        
        path = self._path.GetPath()
        
        type = self._type.GetChoice()
        
        check_period = self._check_period.GetValue() * 60
        
        local_tag = self._local_tag.GetValue()
        
        return ( path, type, check_period, local_tag )
        
    
class DialogManageNamespaceBlacklists( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._tag_services = ClientGUICommon.ListBook( self )
            self._tag_services.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            service_identifiers = HC.app.Read( 'service_identifiers', ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
            
            for service_identifier in service_identifiers:
                
                page = self._Panel( self._tag_services, service_identifier )
                
                name = service_identifier.GetName()
                
                self._tag_services.AddPage( page, name )
                
            
            default_tag_repository = HC.options[ 'default_tag_repository' ]
            
            self._tag_services.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_services, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 550, 680 ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'namespace blacklists' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        try:
            
            info = [ page.GetInfo() for page in self._tag_services.GetNameToPageDict().values() if page.HasInfo() ]
            
            HC.app.Write( 'namespace_blacklists', info )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_services.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier ):
            
            def InitialiseControls():
                
                choice_pairs = [ ( 'blacklist', True ), ( 'whitelist', False ) ]
                
                self._blacklist = ClientGUICommon.RadioBox( self, 'type', choice_pairs )
                
                self._namespaces = ClientGUICommon.TagsBoxNamespaces( self )
                
                self._namespace_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
                self._namespace_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
                
            
            def PopulateControls():
                
                ( blacklist, namespaces ) = HC.app.Read( 'namespace_blacklists', self._service_identifier )
                
                if blacklist: self._blacklist.SetSelection( 0 )
                else: self._blacklist.SetSelection( 1 )
                
                for namespace in namespaces: self._namespaces.AddNamespace( namespace )
                
            
            def ArrangeControls():
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._blacklist, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( self._namespaces, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( self._namespace_input, FLAGS_EXPAND_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def EventKeyDownNamespace( self, event ):
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                namespace = self._namespace_input.GetValue()
                
                self._namespaces.AddNamespace( namespace )
                
                self._namespace_input.SetValue( '' )
                
            else: event.Skip()
            
        
        def GetInfo( self ):
            
            blacklist = self._blacklist.GetSelectedClientData()
            
            namespaces = self._namespaces.GetClientData()
            
            return ( self._service_identifier, blacklist, namespaces )
            
        
        def HasInfo( self ):
            
            ( service_identifier, blacklist, namespaces ) = self.GetInfo()
            
            return len( namespaces ) > 0
            
        
        def SetTagBoxFocus( self ): self._namespace_input.SetFocus()
        
    
class DialogManageOptions( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._listbook = ClientGUICommon.ListBook( self )
            
            # files and memory
            
            self._file_page = wx.Panel( self._listbook )
            self._file_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._export_location = wx.DirPickerCtrl( self._file_page, style = wx.DIRP_USE_TEXTCTRL )
            
            self._exclude_deleted_files = wx.CheckBox( self._file_page, label = '' )
            
            self._thumbnail_cache_size = wx.SpinCtrl( self._file_page, min = 10, max = 3000 )
            self._thumbnail_cache_size.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = wx.StaticText( self._file_page, label = '' )
            
            self._preview_cache_size = wx.SpinCtrl( self._file_page, min = 20, max = 3000 )
            self._preview_cache_size.Bind( wx.EVT_SPINCTRL, self.EventPreviewsUpdate )
            
            self._estimated_number_previews = wx.StaticText( self._file_page, label = '' )
            
            self._fullscreen_cache_size = wx.SpinCtrl( self._file_page, min = 100, max = 3000 )
            self._fullscreen_cache_size.Bind( wx.EVT_SPINCTRL, self.EventFullscreensUpdate )
            
            self._estimated_number_fullscreens = wx.StaticText( self._file_page, label = '' )
            
            self._thumbnail_width = wx.SpinCtrl( self._file_page, min=20, max=200 )
            self._thumbnail_width.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_height = wx.SpinCtrl( self._file_page, min=20, max=200 )
            self._thumbnail_height.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._num_autocomplete_chars = wx.SpinCtrl( self._file_page, min = 1, max = 100 )
            self._num_autocomplete_chars.SetToolTipString( 'how many characters you enter before the gui fetches autocomplete results from the db' + os.linesep + 'increase this if you find autocomplete results are slow' )
            
            self._listbook.AddPage( self._file_page, 'files and memory' )
            
            # gui
            
            self._gui_page = wx.Panel( self._listbook )
            self._gui_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._default_gui_session = wx.Choice( self._gui_page )
            
            self._confirm_client_exit = wx.CheckBox( self._gui_page )
            
            self._gui_capitalisation = wx.CheckBox( self._gui_page )
            
            self._gui_show_all_tags_in_autocomplete = wx.CheckBox( self._gui_page )
            
            self._default_tag_sort = wx.Choice( self._gui_page )
            
            self._default_tag_sort.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
            self._default_tag_sort.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
            self._default_tag_sort.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
            self._default_tag_sort.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
            
            self._default_tag_repository = wx.Choice( self._gui_page )
            
            self._fullscreen_borderless = wx.CheckBox( self._gui_page )
            
            self._listbook.AddPage( self._gui_page, 'gui' )
            
            # sound
            
            self._sound_page = wx.Panel( self._listbook )
            self._sound_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._play_dumper_noises = wx.CheckBox( self._sound_page, label = 'play success/fail noises when dumping' )
            
            self._listbook.AddPage( self._sound_page, 'sound' )
            
            # default file system predicates
            
            self._file_system_predicates_page = wx.Panel( self._listbook )
            self._file_system_predicates_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._file_system_predicate_age_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '>' ] )
            
            self._file_system_predicate_age_years = wx.SpinCtrl( self._file_system_predicates_page, max = 30 )
            
            self._file_system_predicate_age_months = wx.SpinCtrl( self._file_system_predicates_page, max = 60 )
            
            self._file_system_predicate_age_days = wx.SpinCtrl( self._file_system_predicates_page, max = 90 )
            
            self._file_system_predicate_duration_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            
            self._file_system_predicate_duration_s = wx.SpinCtrl( self._file_system_predicates_page, max = 3599 )
            
            self._file_system_predicate_duration_ms = wx.SpinCtrl( self._file_system_predicates_page, max = 999 )
            
            self._file_system_predicate_height_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            
            self._file_system_predicate_height = wx.SpinCtrl( self._file_system_predicates_page, max = 200000 )
            
            self._file_system_predicate_limit = wx.SpinCtrl( self._file_system_predicates_page, max = 1000000 )
            
            self._file_system_predicate_mime_media = wx.Choice( self._file_system_predicates_page, choices=[ 'image', 'application' ] )
            self._file_system_predicate_mime_media.Bind( wx.EVT_CHOICE, self.EventFileSystemPredicateMime )
            
            self._file_system_predicate_mime_type = wx.Choice( self._file_system_predicates_page, choices=[], size = ( 120, -1 ) )
            
            self._file_system_predicate_num_tags_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', '=', '>' ] )
            
            self._file_system_predicate_num_tags = wx.SpinCtrl( self._file_system_predicates_page, max = 2000 )
            
            self._file_system_predicate_local_rating_numerical_sign = wx.Choice( self._file_system_predicates_page, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
            
            self._file_system_predicate_local_rating_numerical_value = wx.SpinCtrl( self._file_system_predicates_page, min = 0, max = 50000 )
            
            self._file_system_predicate_local_rating_like_value = wx.Choice( self._file_system_predicates_page, choices=[ 'like', 'dislike', 'rated', 'not rated' ] )
            
            self._file_system_predicate_ratio_sign = wx.Choice( self._file_system_predicates_page, choices=[ '=', u'\u2248' ] )
            
            self._file_system_predicate_ratio_width = wx.SpinCtrl( self._file_system_predicates_page, max = 50000 )
            
            self._file_system_predicate_ratio_height = wx.SpinCtrl( self._file_system_predicates_page, max = 50000 )
            
            self._file_system_predicate_size_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            
            self._file_system_predicate_size = wx.SpinCtrl( self._file_system_predicates_page, max = 1048576 )
            
            self._file_system_predicate_size_unit = wx.Choice( self._file_system_predicates_page, choices=[ 'B', 'KB', 'MB', 'GB' ] )
            
            self._file_system_predicate_width_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            
            self._file_system_predicate_width = wx.SpinCtrl( self._file_system_predicates_page, max = 200000 )
            
            self._file_system_predicate_num_words_sign = wx.Choice( self._file_system_predicates_page, choices=[ '<', u'\u2248', '=', '>' ] )
            
            self._file_system_predicate_num_words = wx.SpinCtrl( self._file_system_predicates_page, max = 1000000 )
            
            self._listbook.AddPage( self._file_system_predicates_page, 'default file system predicates' )
            
            # colours
            
            self._colour_page = wx.Panel( self._listbook )
            self._colour_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._namespace_colours = ClientGUICommon.TagsBoxColourOptions( self._colour_page, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = wx.Button( self._colour_page, label = 'edit selected' )
            self._edit_namespace_colour.Bind( wx.EVT_BUTTON, self.EventEditNamespaceColour )
            
            self._new_namespace_colour = wx.TextCtrl( self._colour_page, style = wx.TE_PROCESS_ENTER )
            self._new_namespace_colour.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
            
            self._listbook.AddPage( self._colour_page, 'colours' )
            
            # server
            
            self._server_page = wx.Panel( self._listbook )
            self._server_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._local_port = wx.SpinCtrl( self._server_page, min = 0, max = 65535 )
            
            self._listbook.AddPage( self._server_page, 'local server' )
            
            # sort/collect
            
            self._sort_by_page = wx.Panel( self._listbook )
            self._sort_by_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._default_sort = ClientGUICommon.ChoiceSort( self._sort_by_page, sort_by = HC.options[ 'sort_by' ] )
            
            self._default_collect = ClientGUICommon.CheckboxCollect( self._sort_by_page )
            
            self._sort_by = wx.ListBox( self._sort_by_page )
            self._sort_by.Bind( wx.EVT_LEFT_DCLICK, self.EventRemoveSortBy )
            
            self._new_sort_by = wx.TextCtrl( self._sort_by_page, style = wx.TE_PROCESS_ENTER )
            self._new_sort_by.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownSortBy )
            
            self._listbook.AddPage( self._sort_by_page, 'sort/collect' )
            
            # shortcuts
            
            self._shortcuts_page = wx.Panel( self._listbook )
            self._shortcuts_page.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._shortcuts = ClientGUICommon.SaneListCtrl( self._shortcuts_page, 480, [ ( 'modifier', 120 ), ( 'key', 120 ), ( 'action', -1 ) ] )
            
            self._shortcuts_add = wx.Button( self._shortcuts_page, label = 'add' )
            self._shortcuts_add.Bind( wx.EVT_BUTTON, self.EventShortcutsAdd )
            
            self._shortcuts_edit = wx.Button( self._shortcuts_page, label = 'edit' )
            self._shortcuts_edit.Bind( wx.EVT_BUTTON, self.EventShortcutsEdit )
            
            self._shortcuts_delete = wx.Button( self._shortcuts_page, label = 'delete' )
            self._shortcuts_delete.Bind( wx.EVT_BUTTON, self.EventShortcutsDelete )
            
            self._listbook.AddPage( self._shortcuts_page, 'shortcuts' )
            
            #
            
            self._ok = wx.Button( self, label = 'Save' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HC.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None: self._export_location.SetPath( abs_path )
                
            
            self._exclude_deleted_files.SetValue( HC.options[ 'exclude_deleted_files' ] )
            
            self._thumbnail_cache_size.SetValue( int( HC.options[ 'thumbnail_cache_size' ] / 1048576 ) )
            
            self._preview_cache_size.SetValue( int( HC.options[ 'preview_cache_size' ] / 1048576 ) )
            
            self._fullscreen_cache_size.SetValue( int( HC.options[ 'fullscreen_cache_size' ] / 1048576 ) )
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.SetValue( thumbnail_width )
            
            self._thumbnail_height.SetValue( thumbnail_height )
            
            self._num_autocomplete_chars.SetValue( HC.options[ 'num_autocomplete_chars' ] )
            
            #
            
            gui_session_names = HC.app.Read( 'gui_sessions', name_only = True )
            
            if 'last session' not in gui_session_names: gui_session_names.insert( 0, 'last session' )
            
            self._default_gui_session.Append( 'just a blank page', None )
            
            for name in gui_session_names: self._default_gui_session.Append( name, name )
            
            try: self._default_gui_session.SetStringSelection( HC.options[ 'default_gui_session' ] )
            except: self._default_gui_session.SetSelection( 0 )
            
            self._confirm_client_exit.SetValue( HC.options[ 'confirm_client_exit' ] )
            
            self._gui_capitalisation.SetValue( HC.options[ 'gui_capitalisation' ] )
            
            self._gui_show_all_tags_in_autocomplete.SetValue( HC.options[ 'show_all_tags_in_autocomplete' ] )
            
            if HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._default_tag_sort.Select( 0 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._default_tag_sort.Select( 1 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._default_tag_sort.Select( 2 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._default_tag_sort.Select( 3 )
            
            service_identifiers = HC.app.Read( 'service_identifiers', ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
            
            for service_identifier in service_identifiers: self._default_tag_repository.Append( service_identifier.GetName(), service_identifier )
            
            self._default_tag_repository.SetStringSelection( HC.options[ 'default_tag_repository' ].GetName() )
            
            self._fullscreen_borderless.SetValue( HC.options[ 'fullscreen_borderless' ] )
            
            #
            
            self._play_dumper_noises.SetValue( HC.options[ 'play_dumper_noises' ] )
            
            #
            
            system_predicates = HC.options[ 'file_system_predicates' ]
            
            ( sign, years, months, days ) = system_predicates[ 'age' ]
            
            self._file_system_predicate_age_sign.SetSelection( sign )
            self._file_system_predicate_age_years.SetValue( years )
            self._file_system_predicate_age_months.SetValue( months )
            self._file_system_predicate_age_days.SetValue( days )
            
            ( sign, s, ms ) = system_predicates[ 'duration' ]
            
            self._file_system_predicate_duration_sign.SetSelection( sign )
            self._file_system_predicate_duration_s.SetValue( s )
            self._file_system_predicate_duration_ms.SetValue( ms )
            
            ( sign, height ) = system_predicates[ 'height' ]
            
            self._file_system_predicate_height_sign.SetSelection( sign )
            self._file_system_predicate_height.SetValue( height )
            
            limit = system_predicates[ 'limit' ]
            
            self._file_system_predicate_limit.SetValue( limit )
            
            ( media, type ) = system_predicates[ 'mime' ]
            
            self._file_system_predicate_mime_media.SetSelection( media )
            
            self.EventFileSystemPredicateMime( None )
            
            self._file_system_predicate_mime_type.SetSelection( type )
            
            ( sign, num_tags ) = system_predicates[ 'num_tags' ]
            
            self._file_system_predicate_num_tags_sign.SetSelection( sign )
            self._file_system_predicate_num_tags.SetValue( num_tags )
            
            ( sign, value ) = system_predicates[ 'local_rating_numerical' ]
            
            self._file_system_predicate_local_rating_numerical_sign.SetSelection( sign )
            self._file_system_predicate_local_rating_numerical_value.SetValue( value )
            
            value = system_predicates[ 'local_rating_like' ]
            
            self._file_system_predicate_local_rating_like_value.SetSelection( value )
            
            ( sign, width, height ) = system_predicates[ 'ratio' ]
            
            self._file_system_predicate_ratio_sign.SetSelection( sign )
            self._file_system_predicate_ratio_width.SetValue( width )
            self._file_system_predicate_ratio_height.SetValue( height )
            
            ( sign, size, unit ) = system_predicates[ 'size' ]
            
            self._file_system_predicate_size_sign.SetSelection( sign )
            self._file_system_predicate_size.SetValue( size )
            self._file_system_predicate_size_unit.SetSelection( unit )
            
            ( sign, width ) = system_predicates[ 'width' ]
            
            self._file_system_predicate_width_sign.SetSelection( sign )
            self._file_system_predicate_width.SetValue( width )
            
            ( sign, num_words ) = system_predicates[ 'num_words' ]
            
            self._file_system_predicate_num_words_sign.SetSelection( sign )
            self._file_system_predicate_num_words.SetValue( num_words )
            
            #
            
            self._local_port.SetValue( HC.options[ 'local_port' ] )
            
            #
            
            for ( sort_by_type, sort_by ) in HC.options[ 'sort_by' ]: self._sort_by.Append( '-'.join( sort_by ), sort_by )
            
            #
            
            for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
                
                for ( key, action ) in key_dict.items():
                    
                    ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                
            
            self._SortListCtrl()
            
        
        def ArrangeControls():
            
            thumbnails_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            thumbnails_sizer.AddF( self._thumbnail_cache_size, FLAGS_MIXED )
            thumbnails_sizer.AddF( self._estimated_number_thumbnails, FLAGS_MIXED )
            
            previews_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            previews_sizer.AddF( self._preview_cache_size, FLAGS_MIXED )
            previews_sizer.AddF( self._estimated_number_previews, FLAGS_MIXED )
            
            fullscreens_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            fullscreens_sizer.AddF( self._fullscreen_cache_size, FLAGS_MIXED )
            fullscreens_sizer.AddF( self._estimated_number_fullscreens, FLAGS_MIXED )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'Default export directory: ' ), FLAGS_MIXED )
            gridbox.AddF( self._export_location, FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'Exclude deleted files from new imports and remote searches: ' ), FLAGS_MIXED )
            gridbox.AddF( self._exclude_deleted_files, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'MB memory reserved for thumbnail cache: ' ), FLAGS_MIXED )
            gridbox.AddF( thumbnails_sizer, FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'MB memory reserved for preview cache: ' ), FLAGS_MIXED )
            gridbox.AddF( previews_sizer, FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'MB memory reserved for fullscreen cache: ' ), FLAGS_MIXED )
            gridbox.AddF( fullscreens_sizer, FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'Thumbnail width: ' ), FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_width, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'Thumbnail height: ' ), FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_height, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._file_page, label = 'Autocomplete character threshold: ' ), FLAGS_MIXED )
            gridbox.AddF( self._num_autocomplete_chars, FLAGS_MIXED )
            
            self._file_page.SetSizer( gridbox )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Default session on startup:' ), FLAGS_MIXED )
            gridbox.AddF( self._default_gui_session, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Confirm client exit:' ), FLAGS_MIXED )
            gridbox.AddF( self._confirm_client_exit, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Default tag service in manage tag dialogs:' ), FLAGS_MIXED )
            gridbox.AddF( self._default_tag_repository, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Default tag sort on management panel:' ), FLAGS_MIXED )
            gridbox.AddF( self._default_tag_sort, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'Capitalise gui: ' ), FLAGS_MIXED )
            gridbox.AddF( self._gui_capitalisation, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'By default, search non-local tags in write-autocomplete: ' ), FLAGS_MIXED )
            gridbox.AddF( self._gui_show_all_tags_in_autocomplete, FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._gui_page, label = 'By default, show fullscreen without borders: ' ), FLAGS_MIXED )
            gridbox.AddF( self._fullscreen_borderless, FLAGS_MIXED )
            
            self._gui_page.SetSizer( gridbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:age' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_years, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'years' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_months, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'months' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_age_days, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'days' ), FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:duration' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_s, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 's' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_duration_ms, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'ms' ), FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:height' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_height_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_height, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:limit=' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_limit, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:mime' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_mime_media, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = '/' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_mime_type, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:num_tags' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_tags_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_tags, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:local_rating_like' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_like_value, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:local_rating_numerical' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_numerical_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_local_rating_numerical_value, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:ratio' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_width, FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = ':' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_ratio_height, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:size' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_size_unit, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:width' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_width_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_width, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._file_system_predicates_page, label = 'system:num_words' ), FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_words_sign, FLAGS_MIXED )
            hbox.AddF( self._file_system_predicate_num_words, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._file_system_predicates_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._server_page, label = 'local server port: ' ), FLAGS_MIXED )
            hbox.AddF( self._local_port, FLAGS_MIXED )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._server_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._play_dumper_noises, FLAGS_EXPAND_PERPENDICULAR )
            
            self._sound_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._namespace_colours, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_namespace_colour, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._edit_namespace_colour, FLAGS_EXPAND_PERPENDICULAR )
            
            self._colour_page.SetSizer( vbox )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._sort_by_page, label = 'default sort: ' ), FLAGS_MIXED )
            gridbox.AddF( self._default_sort, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self._sort_by_page, label = 'default collect: ' ), FLAGS_MIXED )
            gridbox.AddF( self._default_collect, FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._sort_by, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_sort_by, FLAGS_EXPAND_PERPENDICULAR )
            
            self._sort_by_page.SetSizer( vbox )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self._shortcuts_page, label = 'These shortcuts are global to the main gui! You probably want to stick to function keys or ctrl + something!' ), FLAGS_MIXED )
            vbox.AddF( self._shortcuts, FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcuts_add, FLAGS_BUTTON_SIZERS )
            hbox.AddF( self._shortcuts_edit, FLAGS_BUTTON_SIZERS )
            hbox.AddF( self._shortcuts_delete, FLAGS_BUTTON_SIZERS )
            
            vbox.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._shortcuts_page.SetSizer( vbox )
            
            #
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 800: x = 800
            if y < 600: y = 600
            
            self.SetInitialSize( ( x, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'hydrus client options' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.EventFullscreensUpdate( None )
        self.EventPreviewsUpdate( None )
        self.EventThumbnailsUpdate( None )
        
        wx.CallAfter( self._file_page.Layout ) # draws the static texts correctly
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _SortListCtrl( self ): self._shortcuts.SortListItems( 2 )
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventEditNamespaceColour( self, event ):
        
        result = self._namespace_colours.GetSelectedNamespaceColour()
        
        if result is not None:
            
            ( namespace, colour ) = result
            
            colour_data = wx.ColourData()
            
            colour_data.SetColour( colour )
            colour_data.SetChooseFull( True )
            
            with wx.ColourDialog( self, data = colour_data ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    colour_data = dlg.GetColourData()
                    
                    colour = colour_data.GetColour()
                    
                    self._namespace_colours.SetNamespaceColour( namespace, colour )
                    
                
            
        
    
    def EventFileSystemPredicateMime( self, event ):
        
        media = self._file_system_predicate_mime_media.GetStringSelection()
        
        self._file_system_predicate_mime_type.Clear()
        
        if media == 'image':
            
            self._file_system_predicate_mime_type.Append( 'any', HC.IMAGES )
            self._file_system_predicate_mime_type.Append( 'jpeg', HC.IMAGE_JPEG )
            self._file_system_predicate_mime_type.Append( 'png', HC.IMAGE_PNG )
            self._file_system_predicate_mime_type.Append( 'gif', HC.IMAGE_GIF )
            
        elif media == 'application':
            
            self._file_system_predicate_mime_type.Append( 'any', HC.APPLICATIONS )
            self._file_system_predicate_mime_type.Append( 'pdf', HC.APPLICATION_PDF )
            self._file_system_predicate_mime_type.Append( 'x-shockwave-flash', HC.APPLICATION_FLASH )
            
        elif media == 'video':
            
            self._file_system_predicate_mime_type.Append( 'any', HC.VIDEO )
            self._file_system_predicate_mime_type.Append( 'mp4', HC.VIDEO_MP4 )
            self._file_system_predicate_mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._file_system_predicate_mime_type.SetSelection( 0 )
        
    
    def EventFullscreensUpdate( self, event ):
        
        ( width, height ) = wx.GetDisplaySize()
        
        estimated_bytes_per_fullscreen = 3 * width * height
        
        self._estimated_number_fullscreens.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_fullscreen ) + '-' + HC.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / ( estimated_bytes_per_fullscreen / 4 ) ) + ' images)' )
        
    
    def EventKeyDownNamespace( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            namespace = self._new_namespace_colour.GetValue()
            
            if namespace != '':
                
                self._namespace_colours.SetNamespaceColour( namespace, wx.Colour( random.randint( 0, 255 ), random.randint( 0, 255 ), random.randint( 0, 255 ) ) )
                
                self._new_namespace_colour.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventKeyDownSortBy( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            sort_by_string = self._new_sort_by.GetValue()
            
            if sort_by_string != '':
                
                try: sort_by = sort_by_string.split( '-' )
                except:
                    
                    wx.MessageBox( 'Could not parse that sort by string!' )
                    
                    return
                    
                
                self._sort_by.Append( sort_by_string, sort_by )
                
                self._new_sort_by.SetValue( '' )
                
            
        else: event.Skip()
        
    
    def EventOK( self, event ):
        
        HC.options[ 'play_dumper_noises' ] = self._play_dumper_noises.GetValue()
        
        HC.options[ 'default_gui_session' ] = self._default_gui_session.GetStringSelection()
        HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.GetValue()
        HC.options[ 'gui_capitalisation' ] = self._gui_capitalisation.GetValue()
        HC.options[ 'show_all_tags_in_autocomplete' ] = self._gui_show_all_tags_in_autocomplete.GetValue()
        HC.options[ 'fullscreen_borderless' ] = self._fullscreen_borderless.GetValue()
        
        HC.options[ 'export_path' ] = HC.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
        HC.options[ 'default_sort' ] = self._default_sort.GetSelection() 
        HC.options[ 'default_collect' ] = self._default_collect.GetChoice()
        
        HC.options[ 'exclude_deleted_files' ] = self._exclude_deleted_files.GetValue()
        
        HC.options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.GetValue() * 1048576
        HC.options[ 'preview_cache_size' ] = self._preview_cache_size.GetValue() * 1048576
        HC.options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.GetValue() * 1048576
        
        HC.options[ 'thumbnail_dimensions' ] = [ self._thumbnail_width.GetValue(), self._thumbnail_height.GetValue() ]
        
        HC.options[ 'num_autocomplete_chars' ] = self._num_autocomplete_chars.GetValue()
        
        HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
        
        sort_by_choices = []
        
        for sort_by in [ self._sort_by.GetClientData( i ) for i in range( self._sort_by.GetCount() ) ]: sort_by_choices.append( ( 'namespaces', sort_by ) )
        
        HC.options[ 'sort_by' ] = sort_by_choices
        
        system_predicates = {}
        
        system_predicates[ 'age' ] = ( self._file_system_predicate_age_sign.GetSelection(), self._file_system_predicate_age_years.GetValue(), self._file_system_predicate_age_months.GetValue(), self._file_system_predicate_age_days.GetValue() )
        system_predicates[ 'duration' ] = ( self._file_system_predicate_duration_sign.GetSelection(), self._file_system_predicate_duration_s.GetValue(), self._file_system_predicate_duration_ms.GetValue() )
        system_predicates[ 'height' ] = ( self._file_system_predicate_height_sign.GetSelection(), self._file_system_predicate_height.GetValue() )
        system_predicates[ 'limit' ] = self._file_system_predicate_limit.GetValue()
        system_predicates[ 'mime' ] = ( self._file_system_predicate_mime_media.GetSelection(), self._file_system_predicate_mime_type.GetSelection() )
        system_predicates[ 'num_tags' ] = ( self._file_system_predicate_num_tags_sign.GetSelection(), self._file_system_predicate_num_tags.GetValue() )
        system_predicates[ 'local_rating_like' ] = self._file_system_predicate_local_rating_like_value.GetSelection()
        system_predicates[ 'local_rating_numerical' ] = ( self._file_system_predicate_local_rating_numerical_sign.GetSelection(), self._file_system_predicate_local_rating_numerical_value.GetValue() )
        system_predicates[ 'ratio' ] = ( self._file_system_predicate_ratio_sign.GetSelection(), self._file_system_predicate_ratio_width.GetValue(), self._file_system_predicate_ratio_height.GetValue() )
        system_predicates[ 'size' ] = ( self._file_system_predicate_size_sign.GetSelection(), self._file_system_predicate_size.GetValue(), self._file_system_predicate_size_unit.GetSelection() )
        system_predicates[ 'width' ] = ( self._file_system_predicate_width_sign.GetSelection(), self._file_system_predicate_width.GetValue() )
        system_predicates[ 'num_words' ] = ( self._file_system_predicate_num_words_sign.GetSelection(), self._file_system_predicate_num_words.GetValue() )
        
        HC.options[ 'file_system_predicates' ] = system_predicates
        
        shortcuts = {}
        
        shortcuts[ wx.ACCEL_NORMAL ] = {}
        shortcuts[ wx.ACCEL_CTRL ] = {}
        shortcuts[ wx.ACCEL_ALT ] = {}
        shortcuts[ wx.ACCEL_SHIFT ] = {}
        
        for ( modifier, key, action ) in self._shortcuts.GetClientData(): shortcuts[ modifier ][ key ] = action
        
        HC.options[ 'shortcuts' ] = shortcuts
        
        HC.options[ 'default_tag_repository' ] = self._default_tag_repository.GetClientData( self._default_tag_repository.GetSelection() )
        HC.options[ 'default_tag_sort' ] = self._default_tag_sort.GetClientData( self._default_tag_sort.GetSelection() )
        
        new_local_port = self._local_port.GetValue()
        
        if new_local_port != HC.options[ 'local_port' ]: HC.pubsub.pub( 'restart_server' )
        
        HC.options[ 'local_port' ] = new_local_port
        
        try: HC.app.Write( 'save_options' )
        except: wx.MessageBox( traceback.format_exc() )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemoveSortBy( self, event ):
        
        selection = self._sort_by.GetSelection()
        
        if selection != wx.NOT_FOUND: self._sort_by.Delete( selection )
        
    
    def EventPreviewsUpdate( self, event ):
        
        estimated_bytes_per_preview = 3 * 400 * 400
        
        self._estimated_number_previews.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._preview_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_preview ) + ' previews)' )
        
    
    def EventShortcutsAdd( self, event ):
        
        with ClientGUIDialogs.DialogInputShortcut( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( modifier, key, action ) = dlg.GetInfo()
                
                ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                
                self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                
                self._SortListCtrl()
                
            
        
    
    def EventShortcutsDelete( self, event ): self._shortcuts.RemoveAllSelected()
    
    def EventShortcutsEdit( self, event ):
        
        indices = self._shortcuts.GetAllSelected()
        
        for index in indices:
            
            ( modifier, key, action ) = self._shortcuts.GetClientData( index )
            
            with ClientGUIDialogs.DialogInputShortcut( self, modifier, key, action ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( modifier, key, action ) = dlg.GetInfo()
                    
                    ( pretty_modifier, pretty_key, pretty_action ) = HC.ConvertShortcutToPrettyShortcut( modifier, key, action )
                    
                    self._shortcuts.UpdateRow( index, ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                    self._SortListCtrl()
                    
                
            
        
    
    def EventThumbnailsUpdate( self, event ):
        
        estimated_bytes_per_thumb = 3 * self._thumbnail_height.GetValue() * self._thumbnail_width.GetValue()
        
        self._estimated_number_thumbnails.SetLabel( '(about ' + HC.ConvertIntToPrettyString( ( self._thumbnail_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_thumb ) + ' thumbnails)' )
        
    
class DialogManagePixivAccount( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._id = wx.TextCtrl( self )
            self._password = wx.TextCtrl( self )
            
            self._status = wx.StaticText( self )
            
            self._test = wx.Button( self, label = 'test' )
            self._test.Bind( wx.EVT_BUTTON, self.EventTest )
            
            self._ok = wx.Button( self, label = 'Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            ( id, password ) = HC.app.Read( 'pixiv_account' )
            
            self._id.SetValue( id )
            self._password.SetValue( password )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'id/email' ), FLAGS_MIXED )
            gridbox.AddF( self._id, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'password' ), FLAGS_MIXED )
            gridbox.AddF( self._password, FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._status, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._test, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 240 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage pixiv account' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        id = self._id.GetValue()
        password = self._password.GetValue()
        
        HC.app.Write( 'pixiv_account', id, password )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventTest( self, event ):
        
        id = self._id.GetValue()
        password = self._password.GetValue()
        
        form_fields = {}
        
        form_fields[ 'mode' ] = 'login'
        form_fields[ 'pixiv_id' ] = id
        form_fields[ 'pass' ] = password
        
        body = urllib.urlencode( form_fields )
        
        headers = {}
        headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
        
        ( response_gumpf, cookies ) = HC.http.Request( HC.POST, 'http://www.pixiv.net/login.php', request_headers = headers, body = body, return_cookies = True )
        
        # _ only given to logged in php sessions
        if 'PHPSESSID' in cookies and '_' in cookies[ 'PHPSESSID' ]: self._status.SetLabel( 'OK!' )
        else: self._status.SetLabel( 'Did not work!' )
        
        wx.CallLater( 2000, self._status.SetLabel, '' )
        
    
class DialogManageRatings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, media ):
        
        def InitialiseControls():
            
            service_identifiers = HC.app.Read( 'service_identifiers', HC.RATINGS_SERVICES )
            
            # sort according to local/remote, I guess
            # and maybe sub-sort according to name?
            # maybe just do two get s_i queries
            
            self._panels = []
            
            for service_identifier in service_identifiers: self._panels.append( self._Panel( self, service_identifier, media ) )
            
            self._apply = wx.Button( self, label = 'Apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._apply, FLAGS_MIXED )
            buttonbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for panel in self._panels: vbox.AddF( panel, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, y ) )
            
        
        self._hashes = set()
        
        for m in media: self._hashes.update( m.GetHashes() )
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ratings for ' + HC.ConvertIntToPrettyString( len( self._hashes ) ) + ' files' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_ratings': self.EventCancel( event )
            elif command == 'ok': self.EventOK( event )
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        try:
            
            service_identifiers_to_content_updates = {}
            
            for panel in self._panels:
                
                if panel.HasChanges():
                    
                    ( service_identifier, content_updates ) = panel.GetContentUpdates()
                    
                    service_identifiers_to_content_updates[ service_identifier ] = content_updates
                    
                
            
            HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_ratings' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, media ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._service = HC.app.Read( 'service', service_identifier )
            
            self._media = media
            
            service_type = service_identifier.GetType()
            
            def InitialiseControls():
                
                self._ratings_panel = ClientGUICommon.StaticBox( self, self._service_identifier.GetName() )
                
                self._current_score = wx.StaticText( self._ratings_panel, style = wx.ALIGN_CENTER )
                
                score_font = self._GetScoreFont()
                
                self._current_score.SetFont( score_font )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): all_rating_services = [ local_ratings for ( local_ratings, remote_ratings ) in [ media.GetRatings() for media in self._media ] ]
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ): all_rating_services = [ remote_ratings for ( local_ratings, remote_ratings ) in [ media.GetRatings() for media in self._media ] ]
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.RATING_LIKE_REPOSITORY ):
                    
                    ( like, dislike ) = self._service.GetLikeDislike()
                    
                    if service_type == HC.LOCAL_RATING_LIKE:
                        
                        ratings = [ rating_services.GetRating( self._service_identifier ) for rating_services in all_rating_services ]
                        
                        if all( ( i is None for i in ratings ) ):
                            
                            choices = [ like, dislike, 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'none rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        elif None in ratings:
                            
                            choices = [ like, dislike, 'remove rating', 'make no changes' ]
                            
                            self._current_score.SetLabel( 'not all rated' )
                            
                        else:
                            
                            if all( ( i == 1 for i in ratings ) ):
                                
                                choices = [ dislike, 'remove rating', 'make no changes' ]
                                
                                if len( self._media ) > 1: self._current_score.SetLabel( 'all ' + like )
                                else: self._current_score.SetLabel( like )
                                
                            elif all( ( i == 0 for i in ratings ) ):
                                
                                choices = [ like, 'remove rating', 'make no changes' ]
                                
                                if len( self._media ) > 1: self._current_score.SetLabel( 'all ' + dislike )
                                else: self._current_score.SetLabel( dislike )
                                
                            else:
                                
                                choices = [ like, dislike, 'remove rating', 'make no changes' ]
                                
                            
                            overall_rating = float( sum( ratings ) ) / float( len( ratings ) )
                            
                            self._current_score.SetLabel( HC.u( '%.2f' % overall_rating ) )
                            
                        
                        if len( self._media ) > 1:
                            
                            ratings_counter = collections.Counter( ratings )
                            
                            likes = ratings_counter[ 1 ]
                            dislikes = ratings_counter[ 0 ]
                            nones = ratings_counter[ None ]
                            
                            scores = []
                            
                            if likes > 0: scores.append( HC.u( likes ) + ' likes' )
                            if dislikes > 0: scores.append( HC.u( dislikes ) + ' dislikes' )
                            if nones > 0: scores.append( HC.u( nones ) + ' not rated' )
                            
                            self._current_score.SetLabel( ', '.join( scores ) )
                            
                        else:
                            
                            ( rating, ) = ratings
                            
                            if rating is None: self._current_score.SetLabel( 'not rated' )
                            elif rating == 1: self._current_score.SetLabel( like )
                            elif rating == 0: self._current_score.SetLabel( dislike )
                            
                        
                    else:
                        
                        self._current_score.SetLabel( '23 ' + like + 's, 44 ' + dislike + 's' )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_NUMERICAL, HC.RATING_NUMERICAL_REPOSITORY ):
                    
                    if service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        ( min, max ) = self._service.GetLowerUpper()
                        
                        self._slider = wx.Slider( self._ratings_panel, minValue = min, maxValue = max, style = wx.SL_AUTOTICKS | wx.SL_LABELS )
                        self._slider.Bind( wx.EVT_SLIDER, self.EventSlider )
                        
                        ratings = [ rating_services.GetRating( self._service_identifier ) for rating_services in all_rating_services ]
                        
                        if all( ( i is None for i in ratings ) ):
                            
                            choices = [ 'set rating', 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'none rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        elif None in ratings:
                            
                            choices = [ 'set rating', 'remove rating', 'make no changes' ]
                            
                            if len( self._media ) > 1: self._current_score.SetLabel( 'not all rated' )
                            else: self._current_score.SetLabel( 'not rated' )
                            
                        else:
                            
                            # you know what? this should really be a bargraph or something!
                            #                               *     
                            #                               *     
                            #                               *     
                            #                          *    *     
                            #    *      *              *    *     
                            #   None    0    1    2    3    4    5
                            # but we can't rely on integers, so just think about it
                            # some kind of sense of distribution would be helpful though
                            
                            choices = [ 'set rating', 'remove rating', 'make no changes' ]
                            
                            overall_rating = float( sum( ratings ) ) / float( len( ratings ) )
                            
                            overall_rating_converted = ( overall_rating * ( max - min ) ) + min
                            
                            self._slider.SetValue( int( overall_rating_converted + 0.5 ) )
                            
                            str_overall_rating = HC.u( '%.2f' % overall_rating_converted )
                            
                            if min in ( 0, 1 ): str_overall_rating += '/' + HC.u( '%.2f' % max )
                            
                            self._current_score.SetLabel( str_overall_rating )
                            
                        
                    else:
                        
                        self._current_score.SetLabel( '3.82/5' )
                        
                    
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    initial_index = choices.index( 'make no changes' )
                    
                    choice_pairs = [ ( choice, choice ) for choice in choices ]
                    
                    self._choices = ClientGUICommon.RadioBox( self._ratings_panel, 'actions', choice_pairs, initial_index )
                    
                
            
            def PopulateControls():
                
                pass
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ): label = 'local rating'
                elif service_type in ( HC.RATING_LIKE_REPOSITORY, HC.RATING_NUMERICAL_REPOSITORY ): label = 'remote rating'
                
                self._ratings_panel.AddF( self._current_score, FLAGS_EXPAND_PERPENDICULAR )
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    if service_type == HC.LOCAL_RATING_LIKE:
                        
                        self._ratings_panel.AddF( self._choices, FLAGS_EXPAND_PERPENDICULAR )
                        
                    elif service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        self._ratings_panel.AddF( self._slider, FLAGS_EXPAND_PERPENDICULAR )
                        self._ratings_panel.AddF( self._choices, FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._ratings_panel, FLAGS_EXPAND_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def _GetScoreFont( self ):
            
            normal_font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
            
            normal_font_size = normal_font.GetPointSize()
            normal_font_family = normal_font.GetFamily()
            
            return wx.Font( normal_font_size * 2, normal_font_family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD )
            
        
        def EventSlider( self, event ):
            
            rating = self._slider.GetValue()
            
            self._choices.SetSelection( 0 )
            
            self._choices.SetString( 0, 'set rating to ' + HC.u( rating ) )
            
            event.Skip()
            
        
        def GetContentUpdates( self ):
            
            service_type = self._service_identifier.GetType()
            
            choice_text = self._choices.GetSelectedClientData()
            
            if choice_text == 'remove rating': rating = None
            else:
                
                if service_type == HC.LOCAL_RATING_LIKE:
                    
                    ( like, dislike ) = self._service.GetLikeDislike()
                    
                    if choice_text == like: rating = 1
                    elif choice_text == dislike: rating = 0
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL: rating = float( self._slider.GetValue() - self._slider.GetMin() ) / float( self._slider.GetMax() - self._slider.GetMin() )
                
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
            
            return ( self._service_identifier, [ content_update ] )
            
        
        def HasChanges( self ):
            
            choice_text = self._choices.GetSelectedClientData()
            
            if choice_text == 'make no changes': return False
            else: return True
            
        
        def GetServiceIdentifier( self ): return self._service_identifier
        
    
class DialogManageServer( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._services_listbook = ClientGUICommon.ListBook( self )
            self._services_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            self._services_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._service_types = wx.Choice( self )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )        
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            for service_type in [ HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.MESSAGE_DEPOT ]: self._service_types.Append( HC.service_string_lookup[ service_type ], service_type )
            
            self._service_types.SetSelection( 0 )
            
            response = self._service.Request( HC.GET, 'services' )
            
            services_info = response[ 'services_info' ]
            
            for ( service_identifier, options ) in services_info:
                
                page = self._Panel( self._services_listbook, service_identifier, options )
                
                name = HC.service_string_lookup[ service_identifier.GetType() ] + '@' + HC.u( options[ 'port' ] )
                
                self._services_listbook.AddPage( page, name )
                
            
        
        def ArrangeControls():
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, FLAGS_MIXED )
            b_box.AddF( self._cancel, FLAGS_MIXED )
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._service_types, FLAGS_MIXED )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._services_listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( b_box, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if y < 400: y = 400 # listbook's setsize ( -1, 400 ) is buggy
            
            self.SetInitialSize( ( 680, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ' + service_identifier.GetName() + ' services' )
        
        self._service_identifier = service_identifier
        
        self._service = HC.app.Read( 'service', self._service_identifier )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.EventServiceChanged( None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            ( service_identifier, options ) = service_panel.GetInfo()
            
            for ( existing_service_identifier, existing_options ) in [ page.GetInfo() for page in self._services_listbook.GetNameToPageDict().values() if page != service_panel ]:
                
                if options[ 'port' ] == existing_options[ 'port' ]: raise Exception( 'That port is already in use!' )
                
            
            name = self._services_listbook.GetCurrentName()
            
            new_name = HC.service_string_lookup[ service_identifier.GetType() ] + '@' + HC.u( options[ 'port' ] )
            
            if name != new_name: self._services_listbook.RenamePage( name, new_name )
            
        
    
    def EventAdd( self, event ):
        
        self._CheckCurrentServiceIsValid()
        
        service_key = os.urandom( 32 )
        
        service_type = self._service_types.GetClientData( self._service_types.GetSelection() )
        
        service_identifier = HC.ServerServiceIdentifier( service_key, service_type )

        port = HC.DEFAULT_SERVICE_PORT
        
        existing_ports = set()
        
        for ( existing_service_identifier, existing_options ) in [ page.GetInfo() for page in self._services_listbook.GetNameToPageDict().values() ]: existing_ports.add( existing_options[ 'port' ] )
        
        while port in existing_ports: port += 1
        
        options = dict( HC.DEFAULT_OPTIONS[ service_type ] )
        
        options[ 'port' ] = port
        
        self._edit_log.append( ( HC.ADD, ( service_identifier, options ) ) )
        
        page = self._Panel( self._services_listbook, service_identifier, options )
        
        name = HC.service_string_lookup[ service_type ] + '@' + HC.u( port )
        
        self._services_listbook.AddPage( page, name, select = True )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        for ( name, page ) in self._services_listbook.GetNameToPageDict().items():
            
            if page.HasChanges():
                
                ( service_identifier, options ) = page.GetInfo()
                
                self._edit_log.append( ( HC.EDIT, ( service_identifier, options ) ) )
                
            
        
        try:
            
            if len( self._edit_log ) > 0:
                
                response = self._service.Request( HC.POST, 'services', { 'edit_log' : self._edit_log } )
                
                service_identifiers_to_access_keys = dict( response[ 'service_identifiers_to_access_keys' ] )
                
                HC.app.Write( 'update_server_services', self._service_identifier, self._edit_log, service_identifiers_to_access_keys )
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            ( service_identifier, options ) = service_panel.GetInfo()
            
            self._edit_log.append( ( HC.DELETE, service_identifier ) )
            
            self._services_listbook.DeleteCurrentPage()
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._services_listbook.GetCurrentPage()
        
        ( service_identifier, options ) = page.GetInfo()
        
        if service_identifier.GetType() == HC.SERVER_ADMIN: self._remove.Disable()
        else: self._remove.Enable()
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            event.Veto()
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, options ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._options = options
            
            def InitialiseControls():
                
                self._options_panel = ClientGUICommon.StaticBox( self, 'options' )
                
                if 'port' in self._options: self._port = wx.SpinCtrl( self._options_panel, min = 1, max = 65535 )
                if 'max_monthly_data' in self._options: self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._options_panel, 'max monthly data (MB)', multiplier = 1048576 )
                if 'max_storage' in self._options: self._max_storage = ClientGUICommon.NoneableSpinCtrl( self._options_panel, 'max storage (MB)', multiplier = 1048576 )
                if 'log_uploader_ips' in self._options: self._log_uploader_ips = wx.CheckBox( self._options_panel, label = '' )
                if 'message' in self._options: self._message = wx.TextCtrl( self._options_panel )
                if 'upnp' in self._options: self._upnp = ClientGUICommon.NoneableSpinCtrl( self._options_panel, 'external port', none_phrase = 'do not forward port', max = 65535 )
                
            
            def PopulateControls():
                
                if 'port' in self._options: self._port.SetValue( self._options[ 'port' ] )
                if 'max_monthly_data' in self._options: self._max_monthly_data.SetValue( self._options[ 'max_monthly_data' ] )
                if 'max_storage' in self._options: self._max_storage.SetValue( self._options[ 'max_storage' ] )
                if 'log_uploader_ips' in self._options: self._log_uploader_ips.SetValue( self._options[ 'log_uploader_ips' ] )
                if 'message' in self._options: self._message.SetValue( self._options[ 'message' ] )
                if 'upnp' in self._options: self._upnp.SetValue( self._options[ 'upnp' ] )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                if 'port' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'port' ), FLAGS_MIXED )
                    gridbox.AddF( self._port, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'max_monthly_data' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'max monthly data' ), FLAGS_MIXED )
                    gridbox.AddF( self._max_monthly_data, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'max_storage' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'max storage' ), FLAGS_MIXED )
                    gridbox.AddF( self._max_storage, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'log_uploader_ips' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'log uploader IPs' ), FLAGS_MIXED )
                    gridbox.AddF( self._log_uploader_ips, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'message' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'message' ), FLAGS_MIXED )
                    gridbox.AddF( self._message, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'upnp' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'UPnP' ), FLAGS_MIXED )
                    gridbox.AddF( self._upnp, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                self._options_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                vbox.AddF( self._options_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def GetInfo( self ):
            
            options = {}
        
            if 'port' in self._options: options[ 'port' ] = self._port.GetValue()
            if 'max_monthly_data' in self._options: options[ 'max_monthly_data' ] = self._max_monthly_data.GetValue()
            if 'max_storage' in self._options: options[ 'max_storage' ] = self._max_storage.GetValue()
            if 'log_uploader_ips' in self._options: options[ 'log_uploader_ips' ] = self._log_uploader_ips.GetValue()
            if 'message' in self._options: options[ 'message' ] = self._message.GetValue()
            if 'upnp' in self._options: options[ 'upnp' ] = self._upnp.GetValue()
            
            return ( self._service_identifier, options )
            
        
        def HasChanges( self ):
            
            ( service_identifier, options ) = self.GetInfo()
            
            if options != self._options: return True
            
            return False
            
        
    
class DialogManageServices( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._listbook = ClientGUICommon.ListBook( self )
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._listbook )
            
            self._local_ratings_like = ClientGUICommon.ListBook( self._listbook )
            self._local_ratings_like.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._local_ratings_numerical = ClientGUICommon.ListBook( self._listbook )
            self._local_ratings_numerical.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._tag_repositories = ClientGUICommon.ListBook( self._listbook )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._file_repositories = ClientGUICommon.ListBook( self._listbook )
            self._file_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._message_depots = ClientGUICommon.ListBook( self._listbook )
            self._message_depots.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._servers_admin = ClientGUICommon.ListBook( self._listbook )
            self._servers_admin.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HC.app.Read( 'services', HC.RESTRICTED_SERVICES + [ HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ] )
            
            for service in services:
                
                service_identifier = service.GetServiceIdentifier()
                
                service_type = service_identifier.GetType()
                name = service_identifier.GetName()
                
                info = service.GetInfo()
                
                if service_type == HC.LOCAL_RATING_LIKE: listbook = self._local_ratings_like
                elif service_type == HC.LOCAL_RATING_NUMERICAL: listbook = self._local_ratings_numerical
                elif service_type == HC.TAG_REPOSITORY: listbook = self._tag_repositories
                elif service_type == HC.FILE_REPOSITORY: listbook = self._file_repositories
                elif service_type == HC.MESSAGE_DEPOT: listbook = self._message_depots
                elif service_type == HC.SERVER_ADMIN: listbook = self._servers_admin
                else: continue
                
                page_info = ( self._Panel, ( listbook, service_identifier, info ), {} )
                
                listbook.AddPage( page_info, name )
                
            
            self._listbook.AddPage( self._local_ratings_like, 'local ratings like' )
            self._listbook.AddPage( self._local_ratings_numerical, 'local ratings numerical' )
            self._listbook.AddPage( self._tag_repositories, 'tags' )
            self._listbook.AddPage( self._file_repositories, 'files' )
            self._listbook.AddPage( self._message_depots, 'message depots' )
            self._listbook.AddPage( self._servers_admin, 'servers admin' )
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage services' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 880, y + 220 ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        services_listbook = self._listbook.GetCurrentPage()
        
        if services_listbook is not None:
            
            service_panel = services_listbook.GetCurrentPage()
            
            if service_panel is not None:
                
                ( service_identifier, info ) = service_panel.GetInfo()
                
                old_name = services_listbook.GetCurrentName()
                name = service_identifier.GetName()
                
                if old_name is not None and name != old_name:
                    
                    if services_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    services_listbook.RenamePage( old_name, name )
                    
                
            
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter new service\'s name' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    services_listbook = self._listbook.GetCurrentPage()
                    
                    if services_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the service.' )
                    
                    if services_listbook == self._local_ratings_like: service_type = HC.LOCAL_RATING_LIKE
                    elif services_listbook == self._local_ratings_numerical: service_type = HC.LOCAL_RATING_NUMERICAL
                    elif services_listbook == self._tag_repositories: service_type = HC.TAG_REPOSITORY
                    elif services_listbook == self._file_repositories: service_type = HC.FILE_REPOSITORY
                    elif services_listbook == self._message_depots: service_type = HC.MESSAGE_DEPOT
                    elif services_listbook == self._servers_admin: service_type = HC.SERVER_ADMIN
                    
                    service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), service_type, name )
                    
                    info = {}
                    
                    if service_type in HC.REMOTE_SERVICES:
                        
                        if service_type == HC.SERVER_ADMIN: ( host, port ) = ( 'hostname', 45870 )
                        elif service_type in HC.RESTRICTED_SERVICES:
                            
                            with ClientGUIDialogs.DialogChooseNewServiceMethod( self ) as dlg:
                                
                                if dlg.ShowModal() != wx.ID_OK: return
                                
                                register = dlg.GetRegister()
                                
                                if register:
                                    
                                    with ClientGUIDialogs.DialogRegisterService( self, service_type ) as dlg:
                                        
                                        if dlg.ShowModal() != wx.ID_OK: return
                                        
                                        credentials = dlg.GetCredentials()
                                        
                                        ( host, port ) = credentials.GetAddress()
                                        
                                        if credentials.HasAccessKey(): info[ 'access_key' ] = credentials.GetAccessKey()
                                        
                                    
                                else: ( host, port ) = ( 'hostname', 45871 )
                                
                            
                            account = HC.GetUnknownAccount()
                            
                            account.MakeStale()
                            
                            info[ 'account' ] = account
                            
                        else: ( host, port ) = ( 'hostname', 45871 )
                        
                        info[ 'host' ] = host
                        info[ 'port' ] = port
                        
                    
                    if service_type == HC.LOCAL_RATING_LIKE:
                        
                        info[ 'like' ] = 'like'
                        info[ 'dislike' ] = 'dislike'
                        
                    elif service_type == HC.LOCAL_RATING_NUMERICAL:

                        info[ 'lower' ] = 0
                        info[ 'upper' ] = 5
                        
                    
                    self._edit_log.append( ( HC.ADD, ( service_identifier, info ) ) )
                    
                    page = self._Panel( services_listbook, service_identifier, info )
                    
                    services_listbook.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( traceback.format_exc() )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        services_listbook = self._listbook.GetCurrentPage()
        
        if services_listbook is not None:
            
            service_panel = services_listbook.GetCurrentPage()
            
            ( service_identifier, info ) = service_panel.GetInfo()
            
            name = service_identifier.GetName()
            
            try:
                
                with wx.FileDialog( self, 'select where to export service', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( ( service_identifier, info ) ) )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export service', defaultFile = 'service.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( ( service_identifier, info ) ) )
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            HC.ShowException( e )
            
            return
            
        
        all_pages = []
        
        all_pages.extend( self._local_ratings_like.GetNameToPageDict().values() )
        all_pages.extend( self._local_ratings_numerical.GetNameToPageDict().values() )
        all_pages.extend( self._tag_repositories.GetNameToPageDict().values() )
        all_pages.extend( self._file_repositories.GetNameToPageDict().values() )
        all_pages.extend( self._message_depots.GetNameToPageDict().values() )
        all_pages.extend( self._servers_admin.GetNameToPageDict().values() )
        
        for page in all_pages:
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( page.GetOriginalServiceIdentifier(), page.GetInfo() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: HC.app.Write( 'update_services', self._edit_log )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventPageChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            HC.ShowException( e )
            
            event.Veto()
            
        
    
    def EventRemove( self, event ):
        
        services_listbook = self._listbook.GetCurrentPage()
        
        service_panel = services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            service_identifier = service_panel.GetOriginalServiceIdentifier()
            
            self._edit_log.append( ( HC.DELETE, service_identifier ) )
            
            services_listbook.DeleteCurrentPage()
            
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            HC.ShowException( e )
            
            event.Veto()
            
        
    
    def Import( self, paths ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                ( service_identifier, info ) = yaml.safe_load( file )
                
                name = service_identifier.GetName()
                
                service_type = service_identifier.GetType()
                
                if service_type == HC.TAG_REPOSITORY: services_listbook = self._tag_repositories
                elif service_type == HC.FILE_REPOSITORY: services_listbook = self._file_repositories
                elif service_type == HC.MESSAGE_DEPOT: services_listbook = self._message_depots
                elif service_type == HC.SERVER_ADMIN: services_listbook = self._servers_admin
                
                self._listbook.SelectPage( services_listbook )
                
                if services_listbook.NameExists( name ):
                    
                    message = 'A service already exists with that name. Overwrite it?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            page = services_listbook.GetNameToPageDict()[ name ]
                            
                            page.Update( service_identifier, info )
                            
                        
                    
                else:
                    
                    self._edit_log.append( ( HC.ADD, ( service_identifier, info ) ) )
                    
                    page = self._Panel( services_listbook, service_identifier, info )
                    
                    services_listbook.AddPage( page, name, select = True )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, info ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            self._info = info
            
            service_type = service_identifier.GetType()
            
            def InitialiseControls():
                
                self._service_panel = ClientGUICommon.StaticBox( self, 'service' )
                
                self._service_name = wx.TextCtrl( self._service_panel )
                
                if service_type in HC.REMOTE_SERVICES:
                    
                    host = self._info[ 'host' ]
                    port = self._info[ 'port' ]
                    
                    if 'access_key' in self._info: access_key = self._info[ 'access_key' ]
                    else: access_key = None
                    
                    credentials = CC.Credentials( host, port, access_key )
                    
                    self._service_credentials = wx.TextCtrl( self._service_panel, value = credentials.GetConnectionString() )
                    
                    self._check_service = wx.Button( self._service_panel, label = 'test credentials' )
                    self._check_service.Bind( wx.EVT_BUTTON, self.EventCheckService )
                    
                
                if service_identifier.GetType() == HC.LOCAL_RATING_LIKE:
                    
                    like = self._info[ 'like' ]
                    dislike = self._info[ 'dislike' ]
                    
                    self._like = wx.TextCtrl( self._service_panel, value = like )
                    self._dislike = wx.TextCtrl( self._service_panel, value = dislike )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL:
                    
                    lower = self._info[ 'lower' ]
                    upper = self._info[ 'upper' ]
                    
                    self._lower = wx.SpinCtrl( self._service_panel, min = -2000, max = 2000 )
                    self._lower.SetValue( lower )
                    self._upper = wx.SpinCtrl( self._service_panel, min = -2000, max = 2000 )
                    self._upper.SetValue( upper )
                
            
            def PopulateControls():
                
                self._service_name.SetValue( self._service_identifier.GetName() )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._service_panel, label = 'name' ), FLAGS_MIXED )
                gridbox.AddF( self._service_name, FLAGS_EXPAND_BOTH_WAYS )
                
                if service_type in HC.REMOTE_SERVICES:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label = 'credentials' ), FLAGS_MIXED )
                    gridbox.AddF( self._service_credentials, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( ( 20, 20 ), FLAGS_MIXED )
                    gridbox.AddF( self._check_service, FLAGS_LONE_BUTTON )
                    
                
                if service_identifier.GetType() == HC.LOCAL_RATING_LIKE:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label = 'like' ), FLAGS_MIXED )
                    gridbox.AddF( self._like, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label = 'dislike' ), FLAGS_MIXED )
                    gridbox.AddF( self._dislike, FLAGS_EXPAND_BOTH_WAYS )
                    
                elif service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL:
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label = 'lower limit' ), FLAGS_MIXED )
                    gridbox.AddF( self._lower, FLAGS_EXPAND_BOTH_WAYS )
                    
                    gridbox.AddF( wx.StaticText( self._service_panel, label = 'upper limit' ), FLAGS_MIXED )
                    gridbox.AddF( self._upper, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                self._service_panel.AddF( gridbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                vbox.AddF( self._service_panel, FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def EventCheckService( self, event ):
            
            ( service_identifier, info ) = self.GetInfo()
        
            service_type = service_identifier.GetType()
            
            service = CC.Service( service_identifier, info )
            
            try: root = service.Request( HC.GET, '' )
            except HydrusExceptions.WrongServiceTypeException:
                
                wx.MessageBox( 'Connection was made, but the service was not a ' + HC.service_string_lookup[ service_type ] + '.' )
                
                return
                
            except:
                
                wx.MessageBox( 'Could not connect!' )
                
                return
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                if 'access_key' not in info or info[ 'access_key' ] is None:
                    
                    wx.MessageBox( 'No access key!' )
                    
                    return
                    
                
                response = service.Request( HC.GET, 'access_key_verification' )
                
                if not response[ 'verified' ]:
                    
                    wx.MessageBox( 'That access key was not recognised!' )
                    
                    return
                    
                
            
            wx.MessageBox( 'Everything looks ok!' )
            
        
        def GetInfo( self ):
            
            service_key = self._service_identifier.GetServiceKey()
            
            service_type = self._service_identifier.GetType()
            
            name = self._service_name.GetValue()
            
            if name == '': raise Exception( 'Please enter a name' )
            
            service_identifier = HC.ClientServiceIdentifier( service_key, service_type, name )
            
            info = {}
            
            if service_type in HC.REMOTE_SERVICES:
                
                connection_string = self._service_credentials.GetValue()
                
                if connection_string == '': raise Exception( 'Please enter some credentials' )
                
                if '@' in connection_string:
                    
                    try: ( access_key, address ) = connection_string.split( '@' )
                    except: raise Exception( 'Could not parse those credentials - no \'@\' symbol!' )
                    
                    try: access_key = access_key.decode( 'hex' )
                    except: raise Exception( 'Could not parse those credentials - could not understand access key!' )
                    
                    if access_key == '': access_key = None
                    
                    info[ 'access_key' ] = access_key
                    
                    connection_string = address
                    
                
                try: ( host, port ) = connection_string.split( ':' )
                except: raise Exception( 'Could not parse those credentials - no \':\' symbol!' )
                
                try: port = int( port )
                except: raise Exception( 'Could not parse those credentials - could not understand the port!' )
                
                info[ 'host' ] = host
                info[ 'port' ] = port
                
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                info[ 'like' ] = self._like.GetValue()
                info[ 'dislike' ] = self._dislike.GetValue()
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                ( lower, upper ) = ( self._lower.GetValue(), self._upper.GetValue() )
                
                if upper < lower: upper = lower + 1
                
                info[ 'lower' ] = lower
                info[ 'upper' ] = upper
                
            
            return ( service_identifier, info )
            
        
        def HasChanges( self ):
            
            ( service_identifier, info ) = self.GetInfo()
            
            if service_identifier != self._service_identifier: return True
            
            if info != self._info: return True
            
            return False
            
        
        def GetOriginalServiceIdentifier( self ): return self._service_identifier
        
        def Update( self, service_identifier, info ):
            
            service_type = service_identifier.GetType()
            
            self._service_name.SetValue( service_identifier.GetName() )
            
            if service_type in HC.REMOTE_SERVICES:
                
                host = info[ 'host' ]
                port = info[ 'port' ]
                
                if service_type in HC.RESTRICTED_SERVICES: access_key = info[ 'access_key' ]
                else: access_key = None
                
                credentials = CC.Credentials( host, port, access_key )
                
                self._service_credentials.SetValue( credentials.GetConnectionString() )
                
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                like = info[ 'like' ]
                dislike = info[ 'dislike' ]
                
                self._like.SetValue( like )
                self._dislike.SetValue( dislike )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                lower = info[ 'lower' ]
                upper = info[ 'upper' ]
                
                self._lower.SetValue( lower )
                self._upper.SetValue( upper )
                
            
        
    
class DialogManageSubscriptions( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._listbook = ClientGUICommon.ListBook( self )
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            self._listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._listbook )
            
            self._deviant_art = ClientGUICommon.ListBook( self._listbook )
            self._deviant_art.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._hentai_foundry = ClientGUICommon.ListBook( self._listbook )
            self._hentai_foundry.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._giphy = ClientGUICommon.ListBook( self._listbook )
            self._giphy.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._newgrounds = ClientGUICommon.ListBook( self._listbook )
            self._newgrounds.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._pixiv = ClientGUICommon.ListBook( self._listbook )
            self._pixiv.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._booru = ClientGUICommon.ListBook( self._listbook )
            self._booru.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._tumblr = ClientGUICommon.ListBook( self._listbook )
            self._tumblr.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            types_to_listbooks = {}
            
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART ] = self._deviant_art
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY ] = self._hentai_foundry
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_GIPHY ] = self._giphy
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_PIXIV ] = self._pixiv
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_BOORU ] = self._booru
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_TUMBLR ] = self._tumblr
            types_to_listbooks[ HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS ] = self._newgrounds
            
            for ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ) in self._original_subscriptions:
                
                listbook = types_to_listbooks[ site_download_type ]
                
                page = self._Panel( listbook, site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused )
                
                listbook.AddPage( page, name )
                
            
            self._listbook.AddPage( self._deviant_art, 'deviant art' )
            self._listbook.AddPage( self._hentai_foundry, 'hentai foundry' )
            self._listbook.AddPage( self._giphy, 'giphy' )
            self._listbook.AddPage( self._newgrounds, 'newgrounds' )
            self._listbook.AddPage( self._pixiv, 'pixiv' )
            self._listbook.AddPage( self._booru, 'booru' )
            self._listbook.AddPage( self._tumblr, 'tumblr' )
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage subscriptions' )
        
        self._original_subscriptions = HC.app.Read( 'subscriptions' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 680, max( 720, y ) ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentSubscriptionIsValid( self ):
        
        subs_listbook = self._listbook.GetCurrentPage()
        
        if subs_listbook is not None:
            
            sub_panel = subs_listbook.GetCurrentPage()
            
            if sub_panel is not None:
                
                name = sub_panel.GetName()
                old_name = subs_listbook.GetCurrentName()
                
                if old_name is not None and name != old_name:
                    
                    if subs_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    subs_listbook.RenamePage( old_name, name )
                    
                
            
        
    
    def EventAdd( self, event ):
        
        with wx.TextEntryDialog( self, 'Enter name for subscription' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    subscription_listbook = self._listbook.GetCurrentPage()
                    
                    if subscription_listbook.NameExists( name ): raise Exception( 'That name is already in use!' )
                    
                    if name == '': raise Exception( 'Please enter a nickname for the subscription.' )
                    
                    if subscription_listbook == self._deviant_art: site_download_type = HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART
                    elif subscription_listbook == self._hentai_foundry: site_download_type = HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY
                    elif subscription_listbook == self._giphy: site_download_type = HC.SITE_DOWNLOAD_TYPE_GIPHY
                    elif subscription_listbook == self._pixiv: site_download_type = HC.SITE_DOWNLOAD_TYPE_PIXIV
                    elif subscription_listbook == self._booru: site_download_type = HC.SITE_DOWNLOAD_TYPE_BOORU
                    elif subscription_listbook == self._tumblr: site_download_type = HC.SITE_DOWNLOAD_TYPE_TUMBLR
                    elif subscription_listbook == self._newgrounds: site_download_type = HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS
                    
                    if site_download_type == HC.SITE_DOWNLOAD_TYPE_PIXIV:
                        
                        ( id, password ) = HC.app.Read( 'pixiv_account' )
                        
                        if id == '' and password == '':
                            
                            wx.MessageBox( 'You need to set up your pixiv credentials before you can add a pixiv subscription!' )
                            
                            return
                            
                        
                    
                    if site_download_type in ( HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART, HC.SITE_DOWNLOAD_TYPE_TUMBLR, HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS ): query_type = 'artist'
                    else: query_type = 'tags'
                    
                    if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU: query_type = ( '', query_type )
                    
                    query = ''
                    
                    frequency_type = 86400
                    frequency_number = 7
                    
                    advanced_tag_options = {}
                    advanced_import_options = {} # blaaah not sure
                    
                    last_checked = None
                    url_cache = set()
                    
                    paused = False
                    
                    page = self._Panel( subscription_listbook, site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused )
                    
                    subscription_listbook.AddPage( page, name, select = True )
                    
                except Exception as e:
                    
                    wx.MessageBox( HC.u( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventExport( self, event ):
        
        try: self._CheckCurrentSubscriptionIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        subscription_listbook = self._listbook.GetCurrentPage()
        
        if subscription_listbook is not None:
            
            sub_panel = subscription_listbook.GetCurrentPage()
            
            if sub_panel is not None:
                
                name = subscription_listbook.GetCurrentName()
                
                info = sub_panel.GetInfo()
                
                ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache ) = info
                
                advanced_tag_options = advanced_tag_options.items() # yaml parsing bug
                
                info = ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache )
                
                try:
                    
                    with wx.FileDialog( self, 'select where to export subscription', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( info ) )
                            
                        
                    
                except:
                    
                    with wx.FileDialog( self, 'select where to export subscription', defaultFile = 'subscription.yaml', style = wx.FD_SAVE ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            with open( dlg.GetPath(), 'wb' ) as f: f.write( yaml.safe_dump( info ) )
                            
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentSubscriptionIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        all_pages = []
        
        all_pages.extend( self._deviant_art.GetNameToPageDict().values() )
        all_pages.extend( self._hentai_foundry.GetNameToPageDict().values() )
        all_pages.extend( self._giphy.GetNameToPageDict().values() )
        all_pages.extend( self._pixiv.GetNameToPageDict().values() )
        all_pages.extend( self._booru.GetNameToPageDict().values() )
        all_pages.extend( self._tumblr.GetNameToPageDict().values() )
        all_pages.extend( self._newgrounds.GetNameToPageDict().values() )
        
        subscriptions = [ page.GetInfo() for page in all_pages ]
        
        try: HC.app.Write( 'subscriptions', subscriptions )
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventPageChanging( self, event ):
        
        try: self._CheckCurrentSubscriptionIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            event.Veto()
            
        
    
    def EventRemove( self, event ):
        
        subscription_listbook = self._listbook.GetCurrentPage()
        
        sub_panel = subscription_listbook.GetCurrentPage()
        
        if sub_panel is not None: subscription_listbook.DeleteCurrentPage()
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentSubscriptionIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            event.Veto()
            
        
    
    def Import( self, paths ):
        
        try: self._CheckCurrentSubscriptionIsValid()
        except Exception as e:
            
            wx.MessageBox( HC.u( e ) )
            
            return
            
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache ) = yaml.safe_load( file )
                
                advanced_tag_options = dict( advanced_tag_options ) # yaml parsing bug
                
                if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU: services_listbook = self._booru
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART: services_listbook = self._deviant_art
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_GIPHY: services_listbook = self._giphy
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY: services_listbook = self._hentai_foundry
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_PIXIV: services_listbook = self._pixiv
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_TUMBLR: services_listbook = self._tumblr
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS: services_listbook = self._newgrounds
                
                self._listbook.SelectPage( services_listbook )
                
                if services_listbook.NameExists( name ):
                    
                    message = 'A service already exists with that name. Overwrite it?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            page = services_listbook.GetNameToPageDict()[ name ]
                            
                            page.Update( query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache )
                            
                        
                    
                else:
                    
                    page = self._Panel( services_listbook, site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache )
                    
                    services_listbook.AddPage( page, name, select = True )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.ScrolledWindow ):
        
        def __init__( self, parent, site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ):
            
            def InitialiseControls():
                
                self._name_panel = ClientGUICommon.StaticBox( self, 'name' )
                
                self._name = wx.TextCtrl( self._name_panel )
                
                self._query_panel = ClientGUICommon.StaticBox( self, 'query' )
                
                self._query = wx.TextCtrl( self._query_panel )
                
                self._booru_selector = wx.ListBox( self._query_panel )
                
                self._query_type = ClientGUICommon.RadioBox( self._query_panel, 'query type', ( ( 'artist', 'artist' ), ( 'tags', 'tags' ) ) )
                
                if site_download_type in ( HC.SITE_DOWNLOAD_TYPE_BOORU, HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART, HC.SITE_DOWNLOAD_TYPE_GIPHY, HC.SITE_DOWNLOAD_TYPE_TUMBLR, HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS ): self._query_type.Hide()
                
                self._frequency_number = wx.SpinCtrl( self._query_panel )
                
                self._frequency_type = wx.Choice( self._query_panel )
                
                for ( title, timespan ) in ( ( 'days', 86400 ), ( 'weeks', 86400 * 7 ), ( 'months', 86400 * 30 ) ): self._frequency_type.Append( title, timespan )
                
                self._info_panel = ClientGUICommon.StaticBox( self, 'info' )
                
                self._paused = wx.CheckBox( self._info_panel, label = 'paused' )
                
                self._reset_cache_button = wx.Button( self._info_panel, label = '     reset cache on dialog ok     ' )
                self._reset_cache_button.Bind( wx.EVT_BUTTON, self.EventResetCache )
                
                if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU: namespaces = [ 'creator', 'series', 'character', '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART: namespaces = [ 'creator', 'title', '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_GIPHY: namespaces = [ '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY: namespaces = [ 'creator', 'title', '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_PIXIV: namespaces = [ 'creator', 'title', '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_TUMBLR: namespaces = [ '' ]
                elif site_download_type == HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS: namespaces = [ 'creator', 'title', '' ]
                
                self._advanced_tag_options = ClientGUICommon.AdvancedTagOptions( self, 'send tags to ', namespaces )
                
                self._advanced_import_options = ClientGUICommon.AdvancedImportOptions( self )
                
            
            def PopulateControls():
                
                if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU:
                    
                    boorus = HC.app.Read( 'boorus' )
                    
                    for booru in boorus: self._booru_selector.Append( booru.GetName(), booru )
                    
                else: self._booru_selector.Hide()
                
                #
                
                self._original_info = ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused )
                
                self._SetControls( *self._original_info )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                self._name_panel.AddF( self._name, FLAGS_EXPAND_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._query_panel, label = 'Check subscription every ' ), FLAGS_MIXED )
                hbox.AddF( self._frequency_number, FLAGS_MIXED )
                hbox.AddF( self._frequency_type, FLAGS_MIXED )
                
                self._query_panel.AddF( self._query, FLAGS_EXPAND_PERPENDICULAR )
                self._query_panel.AddF( self._query_type, FLAGS_EXPAND_PERPENDICULAR )
                self._query_panel.AddF( self._booru_selector, FLAGS_EXPAND_PERPENDICULAR )
                self._query_panel.AddF( hbox, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                if last_checked is None: last_checked_message = 'not yet initialised'
                else:
                    
                    now = HC.GetNow()
                    
                    if last_checked < now: last_checked_message = HC.ConvertTimestampToPrettySync( last_checked )
                    else: last_checked_message = 'due to error, update is delayed. next check in ' + HC.ConvertTimestampToPrettyPending( last_checked )
                    
                
                self._info_panel.AddF( wx.StaticText( self._info_panel, label = last_checked_message ), FLAGS_EXPAND_PERPENDICULAR )
                self._info_panel.AddF( wx.StaticText( self._info_panel, label = HC.u( len( url_cache ) ) + ' urls in cache' ), FLAGS_EXPAND_PERPENDICULAR )
                self._info_panel.AddF( self._paused, FLAGS_LONE_BUTTON )
                self._info_panel.AddF( self._reset_cache_button, FLAGS_LONE_BUTTON )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._name_panel, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( self._query_panel, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( self._info_panel, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( self._advanced_tag_options, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( self._advanced_import_options, FLAGS_EXPAND_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            wx.ScrolledWindow.__init__( self, parent )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
            self._reset_cache = False
            
            self.SetScrollRate( 0, 20 )
            
            self.SetMinSize( ( 540, 620 ) )
            
        
        def _SetControls( self, site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ):
            
            self._name.SetValue( name )
            
            self._query.SetValue( query )
            
            if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU:
                
                ( booru_name, query_type ) = query_type
                
                index = self._booru_selector.FindString( booru_name )
                
                if index != wx.NOT_FOUND: self._booru_selector.Select( index )
                
                initial_index = 1
                
            else:
                
                self._booru_selector.Hide()
                
                if query_type == 'artist': initial_index = 0
                elif query_type == 'tags': initial_index = 1
                
            
            self._query_type.SetSelection( initial_index )
            
            if site_download_type in ( HC.SITE_DOWNLOAD_TYPE_BOORU, HC.SITE_DOWNLOAD_TYPE_DEVIANT_ART, HC.SITE_DOWNLOAD_TYPE_GIPHY, HC.SITE_DOWNLOAD_TYPE_TUMBLR, HC.SITE_DOWNLOAD_TYPE_NEWGROUNDS ): self._query_type.Hide()
            
            self._frequency_number.SetValue( frequency_number )
            
            index_to_select = None
            i = 0
            
            for ( title, timespan ) in ( ( 'days', 86400 ), ( 'weeks', 86400 * 7 ), ( 'months', 86400 * 30 ) ):
                
                if frequency_type == timespan: index_to_select = i
                
                i += 1
                
            
            if index_to_select is not None: self._frequency_type.Select( index_to_select )
            
            self._paused.SetValue( paused )
            
            self._reset_cache_button.SetLabel( '     reset cache on dialog ok     ' )
            
            self._advanced_tag_options.SetInfo( advanced_tag_options )
            
            self._advanced_import_options.SetInfo( advanced_import_options )
            
        
        def EventResetCache( self, event ):
            
            self._reset_cache = True
            
            self._reset_cache_button.SetLabel( 'cache will be reset on dialog ok' )
            self._reset_cache_button.Disable()
            
        
        def GetInfo( self ):
            
            ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ) = self._original_info
            
            name = self._name.GetValue()
            
            query_type = self._query_type.GetSelectedClientData()
            
            if site_download_type == HC.SITE_DOWNLOAD_TYPE_BOORU:
                
                booru_name = self._booru_selector.GetStringSelection()
                
                query_type = ( booru_name, query_type )
                
            
            query = self._query.GetValue()
            
            frequency_number = self._frequency_number.GetValue()
            frequency_type = self._frequency_type.GetClientData( self._frequency_type.GetSelection() )
            
            advanced_tag_options = self._advanced_tag_options.GetInfo()
            
            advanced_import_options = self._advanced_import_options.GetInfo()
            
            if self._reset_cache:
                
                last_checked = None
                url_cache = set()
                
            
            paused = self._paused.GetValue()
            
            return ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused )
            
        
        def GetName( self ): return self._name.GetValue()
        
        def Update( self, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused ):
            
            site_download_type = self._original_info[0]
            name = self._original_info[1]
            
            self._original_info = ( site_download_type, name, query_type, query, frequency_type, frequency_number, advanced_tag_options, advanced_import_options, last_checked, url_cache, paused )
            
            self._SetControls( *self._original_info )
            
        
    
class DialogManageTagParents( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, tag = None ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HC.app.Read( 'services', ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetAccount()
                
                if account.HasPermission( HC.POST_DATA ):
                    
                    service_identifier = service.GetServiceIdentifier()
                    
                    page_info = ( self._Panel, ( self._tag_repositories, service_identifier, tag ), {} )
                    
                    name = service_identifier.GetName()
                    
                    self._tag_repositories.AddPage( page_info, name )
                    
                
            
            page = self._Panel( self._tag_repositories, HC.LOCAL_TAG_SERVICE_IDENTIFIER, tag )
            
            name = HC.LOCAL_TAG_SERVICE_IDENTIFIER.GetName()
            
            self._tag_repositories.AddPage( page, name )
            
            default_tag_repository = HC.options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 550, 680 ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'tag parents' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus': self._SetSearchFocus()
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        service_identifiers_to_content_updates = {}
        
        try:
            
            for page in self._tag_repositories.GetNameToPageDict().values():
                
                ( service_identifier, content_updates ) = page.GetContentUpdates()
                
                service_identifiers_to_content_updates[ service_identifier ] = content_updates
                
            
            HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, tag = None ):
            
            def InitialiseControls():
                
                self._tag_parents = ClientGUICommon.SaneListCtrl( self, 250, [ ( '', 30 ), ( 'child', 160 ), ( 'parent', -1 ) ] )
                self._tag_parents.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventActivated )
                self._tag_parents.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
                self._tag_parents.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
                
                self._child_text = wx.StaticText( self )
                self._parent_text = wx.StaticText( self )
                
                self._child_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.SetChild, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                self._parent_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.SetParent, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                
                self._add = wx.Button( self, label = 'add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
                self._add.Disable()
                
            
            def PopulateControls():
                
                for ( status, pairs ) in self._original_statuses_to_pairs.items():
                    
                    sign = HC.ConvertStatusToPrefix( status )
                    
                    for ( child, parent ) in pairs: self._tag_parents.Append( ( sign, child, parent ), ( status, child, parent ) )
                    
                
                self._tag_parents.SortListItems( 2 )
                
                if tag is not None: self.SetChild( tag )
                
            
            def ArrangeControls():
                
                text_box = wx.BoxSizer( wx.HORIZONTAL )
                
                text_box.AddF( self._child_text, FLAGS_EXPAND_BOTH_WAYS )
                text_box.AddF( self._parent_text, FLAGS_EXPAND_BOTH_WAYS )
                
                input_box = wx.BoxSizer( wx.HORIZONTAL )
                
                input_box.AddF( self._child_input, FLAGS_EXPAND_BOTH_WAYS )
                input_box.AddF( self._parent_input, FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._tag_parents, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( self._add, FLAGS_LONE_BUTTON )
                vbox.AddF( text_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                vbox.AddF( input_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            
            if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                
                service = HC.app.Read( 'service', service_identifier )
                
                self._account = service.GetAccount()
                
            
            self._original_statuses_to_pairs = HC.app.Read( 'tag_parents', service_identifier )
            
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in self._original_statuses_to_pairs.items() } )
            
            self._pairs_to_reasons = {}
            
            self._current_parent = None
            self._current_child = None
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def _AddPair( self, child, parent ):
            
            old_status = None
            new_status = None
            
            pair = ( child, parent )
            
            pair_string = child + '->' + parent
            
            if pair in self._current_statuses_to_pairs[ HC.CURRENT ]:
                
                message = pair_string + ' already exists.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'petition it', no_label = 'do nothing' ) as dlg:
                    
                    if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                            else:
                                
                                message = 'Enter a reason for this pair to be removed. A janitor will review your petition.'
                                
                                with wx.TextEntryDialog( self, message ) as dlg:
                                    
                                    if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                                    else: return
                                    
                                
                            
                            self._pairs_to_reasons[ pair ] = reason
                            
                        else: return
                        
                    
                    old_status = HC.CURRENT
                    new_status = HC.PETITIONED
                    
                
            elif pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                
                message = pair_string + ' is pending.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        old_status = HC.PENDING
                        
                        if pair in self._current_statuses_to_pairs[ HC.DELETED ]: new_status = HC.DELETED
                        
                    else: return
                    
                
            elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                
                message = pair_string + ' is petitioned.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        old_status = HC.PETITIONED
                        new_status = HC.CURRENT
                        
                    else: return
                    
                
            else:
                
                if self._CanAdd( child, parent ):
                    
                    if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                        
                        if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                        else:
                            
                            message = 'Enter a reason for ' + pair_string + ' to be added. A janitor will review your petition.'
                            
                            with wx.TextEntryDialog( self, message ) as dlg:
                                
                                if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                                else: return
                                
                            
                        
                        self._pairs_to_reasons[ pair ] = reason
                        
                    
                    if pair in self._current_statuses_to_pairs[ HC.DELETED ]: old_status = HC.DELETED
                    
                    new_status = HC.PENDING
                    
                
            
            if old_status is not None:
                
                self._current_statuses_to_pairs[ old_status ].discard( pair )
                
                index = self._tag_parents.GetIndexFromClientData( ( old_status, child, parent ) )
                
                self._tag_parents.DeleteItem( index )
                
            
            if new_status is not None:
                
                self._current_statuses_to_pairs[ new_status ].add( pair )
                
                sign = HC.ConvertStatusToPrefix( new_status )
                
                self._tag_parents.Append( ( sign, child, parent ), ( new_status, child, parent ) )
                
            
        
        def _CanAdd( self, potential_child, potential_parent ):
            
            if potential_child == potential_parent: return False
            
            current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
            
            current_children = { child for ( child, parent ) in current_pairs }
            
            # test for loops
            
            if potential_parent in current_children:
                
                simple_children_to_parents = HydrusTags.BuildSimpleChildrenToParents( current_pairs )
                
                if HydrusTags.LoopInSimpleChildrenToParents( simple_children_to_parents, potential_child, potential_parent ):
                    
                    wx.MessageBox( 'Adding that pair would create a loop!' )
                    
                    return False
                    
                
            
            return True
            
        
        def _SetButtonStatus( self ):
            
            if self._current_parent is None or self._current_child is None: self._add.Disable()
            else: self._add.Enable()
            
        
        def EventActivated( self, event ):
            
            all_selected = self._tag_parents.GetAllSelected()
            
            if len( all_selected ) > 0:
                
                selection = all_selected[0]
                
                ( status, child, parent ) = self._tag_parents.GetClientData( selection )
                
                self._AddPair( child, parent )
                
            
        
        def EventAddButton( self, event ):
            
            if self._current_child is not None and self._current_parent is not None:
                
                self._AddPair( self._current_child, self._current_parent )
                
                self.SetChild( None )
                self.SetParent( None )
                
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            content_updates = []
            
            if self._service_identifier == HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                
                for pair in self._current_statuses_to_pairs[ HC.PENDING ]: content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) )
                for pair in self._current_statuses_to_pairs[ HC.PETITIONED ]: content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, pair ) )
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PENDING, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_pends ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PENDING, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_petitions ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_identifier, content_updates )
            
        
        def SetChild( self, tag, parents = [] ):
            
            if tag is not None and tag == self._current_parent: self.SetParent( None )
            
            self._current_child = tag
            
            if tag is None: self._child_text.SetLabel( '' )
            else: self._child_text.SetLabel( tag )
            
            self._SetButtonStatus()
            
        
        def SetParent( self, tag, parents = [] ):
            
            if tag is not None and tag == self._current_child: self.SetChild( None )
            
            self._current_parent = tag
            
            if tag is None: self._parent_text.SetLabel( '' )
            else: self._parent_text.SetLabel( tag )
            
            self._SetButtonStatus()
            
        
        def SetTagBoxFocus( self ):
            
            if self._current_child is None: self._child_input.SetFocus()
            else: self._parent_input.SetFocus()
            
        
    
class DialogManageTagSiblings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, tag = None ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            page = self._Panel( self._tag_repositories, HC.LOCAL_TAG_SERVICE_IDENTIFIER, tag )
            
            name = HC.LOCAL_TAG_SERVICE_IDENTIFIER.GetName()
            
            self._tag_repositories.AddPage( page, name )
            
            services = HC.app.Read( 'services', ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetAccount()
                
                if account.HasPermission( HC.POST_DATA ):
                    
                    service_identifier = service.GetServiceIdentifier()
                    
                    page_info = ( self._Panel, ( self._tag_repositories, service_identifier, tag ), {} )
                    
                    name = service_identifier.GetName()
                    
                    self._tag_repositories.AddPage( page_info, name )
                    
                
            
            default_tag_repository = HC.options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 550, 680 ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'tag siblings' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus': self._SetSearchFocus()
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        service_identifiers_to_content_updates = {}
        
        try:
            
            for page in self._tag_repositories.GetNameToPageDict().values():
                
                ( service_identifier, content_updates ) = page.GetContentUpdates()
                
                service_identifiers_to_content_updates[ service_identifier ] = content_updates
                
            
            HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_identifier, tag = None ):
            
            def InitialiseControls():
                
                self._tag_siblings = ClientGUICommon.SaneListCtrl( self, 250, [ ( '', 30 ), ( 'old', 160 ), ( 'new', -1 ) ] )
                self._tag_siblings.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventActivated )
                self._tag_siblings.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
                self._tag_siblings.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
                
                self._old_text = wx.StaticText( self )
                self._new_text = wx.StaticText( self )
                
                self._old_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.SetOld, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                self._new_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.SetNew, HC.LOCAL_FILE_SERVICE_IDENTIFIER, service_identifier )
                
                self._add = wx.Button( self, label = 'add' )
                self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
                self._add.Disable()
                
                
            def PopulateControls():
                
                for ( status, pairs ) in self._original_statuses_to_pairs.items():
                    
                    sign = HC.ConvertStatusToPrefix( status )
                    
                    for ( old, new ) in pairs: self._tag_siblings.Append( ( sign, old, new ), ( status, old, new ) )
                    
                
                self._tag_siblings.SortListItems( 2 )
                
                if tag is not None: self.SetOld( tag )
                
            
            def ArrangeControls():
                
                text_box = wx.BoxSizer( wx.HORIZONTAL )
                
                text_box.AddF( self._old_text, FLAGS_EXPAND_BOTH_WAYS )
                text_box.AddF( self._new_text, FLAGS_EXPAND_BOTH_WAYS )
                
                input_box = wx.BoxSizer( wx.HORIZONTAL )
                
                input_box.AddF( self._old_input, FLAGS_EXPAND_BOTH_WAYS )
                input_box.AddF( self._new_input, FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._tag_siblings, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( self._add, FLAGS_LONE_BUTTON )
                vbox.AddF( text_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                vbox.AddF( input_box, FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._service_identifier = service_identifier
            
            if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                
                service = HC.app.Read( 'service', service_identifier )
                
                self._account = service.GetAccount()
                
            
            self._original_statuses_to_pairs = HC.app.Read( 'tag_siblings', service_identifier )
            
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in self._original_statuses_to_pairs.items() } )
            
            self._pairs_to_reasons = {}
            
            self._current_old = None
            self._current_new = None
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
            if tag is not None: self.SetOld( tag )
            
        
        def _AddPair( self, old, new ):
            
            old_status = None
            new_status = None
            
            pair = ( old, new )
            
            pair_string = old + '->' + new
            
            if pair in self._current_statuses_to_pairs[ HC.CURRENT ]:
                
                message = pair_string + ' already exists.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'petition it', no_label = 'do nothing' ) as dlg:
                    
                    if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                            else:
                                
                                message = 'Enter a reason for this pair to be removed. A janitor will review your petition.'
                                
                                with wx.TextEntryDialog( self, message ) as dlg:
                                    
                                    if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                                    else: return
                                    
                                
                            
                            self._pairs_to_reasons[ pair ] = reason
                            
                        else: return
                        
                    
                    old_status = HC.CURRENT
                    new_status = HC.PETITIONED
                    
                
            elif pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                
                message = pair_string + ' is pending.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        old_status = HC.PENDING
                        
                        if pair in self._current_statuses_to_pairs[ HC.DELETED ]: new_status = HC.DELETED
                        
                    else: return
                    
                
            elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                
                message = pair_string + ' is petitioned.'
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        old_status = HC.PETITIONED
                        new_status = HC.CURRENT
                        
                    else: return
                    
                
            else:
                
                if self._CanAdd( old, new ):
                    
                    if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                        
                        if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                        else:
                            
                            message = 'Enter a reason for ' + pair_string + ' to be added. A janitor will review your petition.'
                            
                            with wx.TextEntryDialog( self, message ) as dlg:
                                
                                if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                                else: return
                                
                            
                        
                        self._pairs_to_reasons[ pair ] = reason
                        
                    
                    if pair in self._current_statuses_to_pairs[ HC.DELETED ]: old_status = HC.DELETED
                    
                    new_status = HC.PENDING
                    
                
            
            if old_status is not None:
                
                self._current_statuses_to_pairs[ old_status ].discard( pair )
                
                index = self._tag_siblings.GetIndexFromClientData( ( old_status, old, new ) )
                
                self._tag_siblings.DeleteItem( index )
                
            
            if new_status is not None:
                
                self._current_statuses_to_pairs[ new_status ].add( pair )
                
                sign = HC.ConvertStatusToPrefix( new_status )
                
                self._tag_siblings.Append( ( sign, old, new ), ( new_status, old, new ) )
                
            
        
        def _CanAdd( self, potential_old, potential_new ):
            
            current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
            
            current_olds = { old for ( old, new ) in current_pairs }
            
            # test for ambiguity
            
            if potential_old in current_olds:
                
                wx.MessageBox( 'There already is a relationship set for the tag ' + potential_old + '.' )
                
                return False
                
            
            # test for loops
            
            if potential_new in current_olds:
                
                d = dict( current_pairs )
                
                next_new = potential_new
                
                while next_new in d:
                    
                    next_new = d[ next_new ]
                    
                    if next_new == potential_old:
                        
                        wx.MessageBox( 'Adding that pair would create a loop!' )
                        
                        return False
                        
                    
                
            
            return True
            
        
        def _SetButtonStatus( self ):
            
            if self._current_new is None or self._current_old is None: self._add.Disable()
            else: self._add.Enable()
            
        
        def EventActivated( self, event ):
            
            all_selected = self._tag_siblings.GetAllSelected()
            
            if len( all_selected ) > 0:
                
                selection = all_selected[0]
                
                ( status, old, new ) = self._tag_siblings.GetClientData( selection )
                
                self._AddPair( old, new )
                
            
        
        def EventAddButton( self, event ):
            
            if self._current_old is not None and self._current_new is not None:
                
                self._AddPair( self._current_old, self._current_new )
                
                self.SetOld( None )
                self.SetNew( None )
                
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            # actually, we don't do this for siblings, but we do for parents, and let's have them be the same
            
            content_updates = []
            
            if self._service_identifier == HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                
                for pair in self._current_statuses_to_pairs[ HC.PENDING ]: content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) )
                for pair in self._current_statuses_to_pairs[ HC.PETITIONED ]: content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, pair ) )
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PENDING, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_pends ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PENDING, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_petitions ) )
                content_updates.extend( ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_identifier, content_updates )
            
        
        def SetNew( self, new, parents = [] ):
            
            if new is not None and new == self._current_old: self.SetOld( None )
            
            self._current_new = new
            
            if new is None: self._new_text.SetLabel( '' )
            else: self._new_text.SetLabel( new )
            
            self._SetButtonStatus()
            
        
        def SetOld( self, old, parents = [] ):
            
            if old is not None:
                
                current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
                
                current_olds = { current_old for ( current_old, current_new ) in current_pairs }
                
                # test for ambiguity
                
                while old in current_olds:
                    
                    olds_to_news = dict( current_pairs )
                    
                    new = olds_to_news[ old ]
                    
                    message = 'There already is a relationship set for ' + old + '! It goes to ' + new + '.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'I want to overwrite it', no_label = 'do nothing' ) as dlg:
                        
                        if self._service_identifier != HC.LOCAL_TAG_SERVICE_IDENTIFIER:
                            
                            if dlg.ShowModal() != wx.ID_YES: return
                            
                            self._AddPair( old, new )
                            
                        
                    
                    current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
                    
                    current_olds = { current_old for ( current_old, current_new ) in current_pairs }
                    
                
            
            #
            
            if old is not None and old == self._current_new: self.SetNew( None )
            
            self._current_old = old
            
            if old is None: self._old_text.SetLabel( '' )
            else: self._old_text.SetLabel( old )
            
            self._SetButtonStatus()
            
        
        def SetTagBoxFocus( self ):
            
            if self._current_old is None: self._old_input.SetFocus()
            else: self._new_input.SetFocus()
            
        
    
class DialogManageTagServicePrecedence( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            message = 'When services dispute over a file\'s tags,' + os.linesep + 'higher services will overrule those below.'
            
            self._explain = wx.StaticText( self, label = message )
            
            self._tag_services = wx.ListBox( self )
            
            self._up = wx.Button( self, label = u'\u2191' )
            self._up.Bind( wx.EVT_BUTTON, self.EventUp )
            
            self._down = wx.Button( self, label = u'\u2193' )
            self._down.Bind( wx.EVT_BUTTON, self.EventDown )
            
            self._apply = wx.Button( self, label = 'apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            tag_service_precedence = HC.app.Read( 'tag_service_precedence' )
            
            for service_identifier in tag_service_precedence:
                
                name = service_identifier.GetName()
                
                self._tag_services.Append( name, service_identifier )
                
            
        
        def ArrangeControls():
            
            updown_vbox = wx.BoxSizer( wx.VERTICAL )
            
            updown_vbox.AddF( self._up, FLAGS_MIXED )
            updown_vbox.AddF( self._down, FLAGS_MIXED )
            
            main_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            main_hbox.AddF( self._tag_services, FLAGS_EXPAND_BOTH_WAYS )
            main_hbox.AddF( updown_vbox, FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._apply, FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._explain, FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( main_hbox, FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( buttons, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if y < 400: y = 400
            
            self.SetInitialSize( ( x, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage tag service precedence' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._apply.SetFocus )
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventOK( self, event ):
        
        message = 'This operation may take several minutes to complete. Are you sure?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                try:
                    
                    service_identifiers = [ self._tag_services.GetClientData( i ) for i in range( self._tag_services.GetCount() ) ]
                    
                    HC.app.Write( 'set_tag_service_precedence', service_identifiers )
                    
                except Exception as e: wx.MessageBox( 'Something went wrong when trying to save tag service precedence to the database: ' + HC.u( e ) )
                
            
        
        self.EndModal( wx.ID_OK )
        
    
    def EventUp( self, event ):
        
        selection = self._tag_services.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection > 0:
                
                service_identifier = self._tag_services.GetClientData( selection )
                
                name = service_identifier.GetName()
                
                self._tag_services.Delete( selection )
                
                self._tag_services.Insert( name, selection - 1, service_identifier )
                
                self._tag_services.Select( selection - 1 )
                
            
        
    
    def EventDown( self, event ):
        
        selection = self._tag_services.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection + 1 < self._tag_services.GetCount():
                
                service_identifier = self._tag_services.GetClientData( selection )
                
                name = service_identifier.GetName()
                
                self._tag_services.Delete( selection )
                
                self._tag_services.Insert( name, selection + 1, service_identifier )
                
                self._tag_services.Select( selection + 1 )
                
            
        
    
class DialogManageTags( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, file_service_identifier, media ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._apply = wx.Button( self, label = 'Apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            service_identifiers = HC.app.Read( 'service_identifiers', ( HC.TAG_REPOSITORY, ) )
            
            for service_identifier in list( service_identifiers ) + [ HC.LOCAL_TAG_SERVICE_IDENTIFIER ]:
                
                service_type = service_identifier.GetType()
                
                page_info = ( self._Panel, ( self._tag_repositories, self._file_service_identifier, service_identifier, media ), {} )
                
                name = service_identifier.GetName()
                
                self._tag_repositories.AddPage( page_info, name )
                
            
            default_tag_repository = HC.options[ 'default_tag_repository' ]
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._apply, FLAGS_MIXED )
            buttonbox.AddF( self._cancel, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttonbox, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, 500 ) )
            
        
        self._file_service_identifier = file_service_identifier
        
        self._hashes = set()
        
        for m in media: self._hashes.update( m.GetHashes() )
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage tags for ' + HC.ConvertIntToPrettyString( len( self._hashes ) ) + ' files' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventCancel( self, event ): self.EndModal( wx.ID_CANCEL )
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_tags': self.EventCancel( event )
            elif command == 'set_search_focus': self._SetSearchFocus()
            elif command == 'ok': self.EventOK( event )
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        try:
            
            service_identifiers_to_content_updates = {}
            
            for page in self._tag_repositories.GetNameToPageDict().values():
                
                ( service_identifier, content_updates ) = page.GetContentUpdates()
                
                service_identifiers_to_content_updates[ service_identifier ] = content_updates
                
            
            if len( service_identifiers_to_content_updates ) > 0: HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_tags', 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_identifier, tag_service_identifier, media ):
            
            def InitialiseControls():
                
                self._tags_box = ClientGUICommon.TagsBoxManage( self, self.AddTag, self._current_tags, self._deleted_tags, self._pending_tags, self._petitioned_tags )
                
                self._add_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.AddTag, self._file_service_identifier, self._tag_service_identifier )
                
                self._modify_mappers = wx.Button( self, label = 'Modify mappers' )
                self._modify_mappers.Bind( wx.EVT_BUTTON, self.EventModify )
                
                self._copy_tags = wx.Button( self, label = 'copy tags' )
                self._copy_tags.Bind( wx.EVT_BUTTON, self.EventCopyTags )
                
                self._paste_tags = wx.Button( self, label = 'paste tags' )
                self._paste_tags.Bind( wx.EVT_BUTTON, self.EventPasteTags )
                
            
            def PopulateControls():
                
                pass
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                if self._i_am_local_tag_service: self._modify_mappers.Hide()
                else:
                    
                    if not self._account.HasPermission( HC.POST_DATA ): self._add_tag_box.Hide()
                    if not self._account.HasPermission( HC.MANAGE_USERS ): self._modify_mappers.Hide()
                    
                
                copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                copy_paste_hbox.AddF( self._copy_tags, FLAGS_MIXED )
                copy_paste_hbox.AddF( self._paste_tags, FLAGS_MIXED )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._tags_box, FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( self._add_tag_box, FLAGS_EXPAND_PERPENDICULAR )
                vbox.AddF( copy_paste_hbox, FLAGS_BUTTON_SIZERS )
                vbox.AddF( self._modify_mappers, FLAGS_BUTTON_SIZERS )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_identifier = file_service_identifier
            self._tag_service_identifier = tag_service_identifier
            
            self._i_am_local_tag_service = self._tag_service_identifier.GetType() == HC.LOCAL_TAG
            
            self._hashes = { hash for hash in itertools.chain.from_iterable( ( m.GetHashes() for m in media ) ) }
            
            self._content_updates = []
            
            if not self._i_am_local_tag_service:
                
                service = HC.app.Read( 'service', tag_service_identifier )
                
                self._account = service.GetAccount()
                
            
            tags_managers = [ m.GetTagsManager() for m in media ]
            
            ( self._current_tags, self._deleted_tags, self._pending_tags, self._petitioned_tags ) = CC.IntersectTags( tags_managers, tag_service_identifier )
            
            self._current_tags.sort()
            self._pending_tags.sort()
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def _AddTag( self, tag, only_add = False ):
            
            if self._i_am_local_tag_service:
                
                if tag in self._pending_tags:
                    
                    if only_add: return
                    
                    self._pending_tags.remove( tag )
                    
                    self._tags_box.RescindPend( tag )
                    
                elif tag in self._petitioned_tags:
                    
                    self._petitioned_tags.remove( tag )
                    
                    self._tags_box.RescindPetition( tag )
                    
                elif tag in self._current_tags:
                    
                    if only_add: return
                    
                    self._petitioned_tags.append( tag )
                    
                    self._tags_box.PetitionTag( tag )
                    
                else:
                    
                    self._pending_tags.append( tag )
                    
                    self._tags_box.PendTag( tag )
                    
                
                self._content_updates = []
                
                self._content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, self._hashes ) ) for tag in self._pending_tags ] )
                self._content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, self._hashes ) ) for tag in self._petitioned_tags ] )
                
            else:
                
                if tag in self._pending_tags:
                    
                    if only_add: return
                    
                    self._pending_tags.remove( tag )
                    
                    self._tags_box.RescindPend( tag )
                    
                    self._content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PENDING, ( tag, self._hashes ) ) )
                    
                elif tag in self._petitioned_tags:
                    
                    self._petitioned_tags.remove( tag )
                    
                    self._tags_box.RescindPetition( tag )
                    
                    self._content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, ( tag, self._hashes ) ) )
                    
                elif tag in self._current_tags:
                    
                    if only_add: return
                    
                    if self._account.HasPermission( HC.RESOLVE_PETITIONS ):
                        
                        self._content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( tag, self._hashes, 'admin' ) ) )
                        
                        self._petitioned_tags.append( tag )
                        
                        self._tags_box.PetitionTag( tag )
                        
                    elif self._account.HasPermission( HC.POST_PETITIONS ):
                        
                        message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                        
                        with wx.TextEntryDialog( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                self._content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( tag, self._hashes, dlg.GetValue() ) ) )
                                
                                self._petitioned_tags.append( tag )
                                
                                self._tags_box.PetitionTag( tag )
                                
                            
                        
                    
                else:
                    
                    self._content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( tag, self._hashes ) ) )
                    
                    self._pending_tags.append( tag )
                    
                    self._tags_box.PendTag( tag )
                    
                
            
        
        def AddTag( self, tag, parents = [] ):
            
            if tag is None: wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'ok' ) ) )
            else:
                
                self._AddTag( tag )
                
                for parent in parents: self._AddTag( parent, only_add = True )
                
            
        
        def EventCopyTags( self, event ):
            
            if wx.TheClipboard.Open():
                
                tags = self._current_tags + self._pending_tags
                
                text = yaml.safe_dump( tags )
                
                data = wx.TextDataObject( text )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventModify( self, event ):
            
            tag = self._tags_box.GetSelectedTag()
            
            if tag is not None and tag in self._current_tags or tag in self._petitioned_tags:
                
                subject_identifiers = [ HC.AccountIdentifier( hash = hash, tag = tag ) for hash in self._hashes ]
                
                with ClientGUIDialogs.DialogModifyAccounts( self, self._tag_service_identifier, subject_identifiers ) as dlg: dlg.ShowModal()
                
            
        
        def EventPasteTags( self, event ):
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject()
                
                wx.TheClipboard.GetData( data )
                
                wx.TheClipboard.Close()
                
                text = data.GetText()
                
                try:
                    
                    tags = yaml.safe_load( text )
                    
                    tags = [ tag for tag in tags if tag not in self._current_tags and tag not in self._pending_tags ]
                    
                    for tag in tags: self.AddTag( tag )
                    
                except: wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventTagsBoxAction( self, event ):
            
            tag = self._tags_box.GetSelectedTag()
            
            if tag is not None: self.AddTag( tag )
            
        
        def GetContentUpdates( self ): return ( self._tag_service_identifier, self._content_updates )
        
        def GetServiceIdentifier( self ): return self._tag_service_identifier
        
        def HasChanges( self ): return len( self._content_updates ) > 0
        
        def SetTagBoxFocus( self ):
            
            if self._i_am_local_tag_service or self._account.HasPermission( HC.POST_DATA ): self._add_tag_box.SetFocus()
            
        
    
class DialogManageUPnP( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, service_identifier ):
        
        def InitialiseControls():
            
            self._mappings_list_ctrl = ClientGUICommon.SaneListCtrl( self, 760, [ ( 'description', -1 ), ( 'internal ip', 100 ), ( 'internal port', 80 ), ( 'external ip', 100 ), ( 'external port', 80 ), ( 'protocol', 80 ), ( 'enabled', 80 ) ] )
            
            self._mappings_list_ctrl.SetMinSize( ( 760, 660 ) )
            
            self._add_local = wx.Button( self, label = 'add service mapping' )
            self._add_local.Bind( wx.EVT_BUTTON, self.EventAddServiceMapping )
            
            self._add_custom = wx.Button( self, label = 'add custom mapping' )
            self._add_custom.Bind( wx.EVT_BUTTON, self.EventAddCustomMapping )
            
            self._edit = wx.Button( self, label = 'edit mapping' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEditMapping )
            
            self._remove = wx.Button( self, label = 'remove mapping' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemoveMapping )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            self._RefreshMappings()
            
        
        def ArrangeControls():
            
            edit_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            if self._service_identifier == HC.LOCAL_FILE_SERVICE_IDENTIFIER: self._add_local.Hide()
            
            edit_buttons.AddF( self._add_local, FLAGS_MIXED )
            edit_buttons.AddF( self._add_custom, FLAGS_MIXED )
            edit_buttons.AddF( self._edit, FLAGS_MIXED )
            edit_buttons.AddF( self._remove, FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._mappings_list_ctrl, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( edit_buttons, FLAGS_BUTTON_SIZERS )
            vbox.AddF( self._ok, FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        if service_identifier == HC.LOCAL_FILE_SERVICE_IDENTIFIER: title = 'manage local upnp'
        else:
            
            # fetch self._service
            
            title = 'manage upnp for ' + service_identifier.GetName()
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, title )
        
        self._service_identifier = service_identifier
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _AddMapping( self, description, internal_ip, internal_port, external_ip, external_port, protocol, enabled ):
        
        # tell service to add it
        
        pass
        
    
    def _RemoveMapping( self, internal_ip, internal_port ):
        
        # tell service to remove it
        
        pass
        
    
    def _RefreshMappings( self ):
    
        self._mappings_list_ctrl.DeleteAllItems()
        
        if self._service_identifier == HC.LOCAL_FILE_SERVICE_IDENTIFIER: self._mappings = HydrusNATPunch.GetUPnPMappings()
        else:
            
            wx.MessageBox( 'get mappings from service' )
            
        
        for mapping in self._mappings: self._mappings_list_ctrl.Append( mapping, mapping )
        
        self._mappings_list_ctrl.SortListItems( 1 )
        
    
    def EventAddCustomMapping( self, event ):
        
        external_port = HC.DEFAULT_SERVICE_PORT
        protocol = 'TCP'
        internal_port = HC.DEFAULT_SERVICE_PORT
        description = 'hydrus service'
        
        with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( external_port, protocol, internal_port, description ) = dlg.GetInfo()
                
                for ( existing_description, existing_internal_ip, existing_internal_port, existing_external_ip, existing_external_port, existing_protocol, existing_enabled ) in self._mappings:
                    
                    if external_port == existing_external_port and protocol == existing_protocol:
                        
                        wx.MessageBox( 'That external port already exists!' )
                        
                        return
                        
                    
                
                HydrusNATPunch.AddUPnPMapping( external_port, protocol, internal_port, description )
                
            
        
        self._RefreshMappings()
        
    
    def EventAddServiceMapping( self, event ):
        
        # start dialog with helpful default values
        # attempt to add mapping via service
        # add to listctrl
        
        pass
        
    
    def EventEditMapping( self, event ):
        
        for index in self._mappings_list_ctrl.GetAllSelected():
            
            ( description, internal_ip, internal_port, external_ip, external_port, protocol, enabled ) = self._mappings_list_ctrl.GetClientData( index )
            
            with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( external_port, protocol, internal_port, description ) = dlg.GetInfo()
                    
                    HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                    
                    HydrusNATPunch.AddUPnPMapping( external_port, protocol, internal_port, description )
                    
                
            
        
        self._RefreshMappings()
        
    
    def EventOK( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemoveMapping( self, event ):
        
        for index in self._mappings_list_ctrl.GetAllSelected():
            
            ( description, internal_ip, internal_port, external_ip, external_port, protocol, enabled ) = self._mappings_list_ctrl.GetClientData( index )
            
            HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
            
        
        self._RefreshMappings()
        
    